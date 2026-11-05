# Lab 3 – Ex 3: Orchestrator-workers – măsurarea problemei de context

## Ce am implementat (`lab3_ex3_orchestrator.py`)

- **`_structured_worker(text)`**: un singur apel izolat, cu context nou (fără istoric, fără tool-uri),
  `response_mime_type="application/json"` și `response_schema=TriageReport`. Tokenii lui de intrare intră în `WORKER_TOKENS`.
  Răspunsul e validat cu Pydantic și se întoarce doar JSON-ul compact.
- **`delegate_log_triage(filename)`**: citește fișierul prin `safe_path()` (`ERROR: ...` la ieșire din workspace sau fișier lipsă)
  și îl dă worker-ului în `<log name='...'>...</log>`.
- **Stretch (temă) – modul `subagent`**: `delegate_log_triage_agent(filename)` pornește un sub-agent ReAct (același `run_agent`, `max_steps=10`)
  care **nu citește niciodată tot fișierul**, ci îl caută cu trei tool-uri:
  - `grep_log(pattern, max_lines)`: liniile care se potrivesc, cu numărul liniei (maxim 50);
  - `count_by_ip(pattern)`: numărul de linii potrivite, grupat pe IP;
  - `context_around(pattern, after)`: prima potrivire și ce urmează după ea (maxim 60 de linii).
  Un regex invalid devine o eroare explicabilă. Concluziile sub-agentului trec apoi prin același worker structurat, ca să iasă tot un `TriageReport`.
  **Propagarea eșecului**: dacă sub-agentul nu termină (`max_steps`, `stuck`, `provider_error`), tool-ul întoarce `ERROR: ...`,
  niciodată un raport inventat, iar orchestratorul (prin `ORCH_SYSTEM`) refuză să scrie raportul.

## Rulare

```powershell
python lab3_ex3_orchestrator.py single       --auto-approve
python lab3_ex3_orchestrator.py orchestrator --auto-approve
python lab3_ex3_orchestrator.py subagent     --auto-approve   # stretch; --verbose arată pașii sub-agentului
```

La final, fiecare rulare tipărește rândul pentru tabel.

## Tabelul (rularea mea, `gemini-3.5-flash-lite`)

| mode | orchestrator input tokens per step | orchestrator total | worker total | grand total |
|---|---|---|---|---|
| single | [296, 58501, 59369] | 118,166 | 0 | 118,166 |
| orchestrator | [316, 729, 1234] | 2,279 | 58,235 | 60,514 |
| subagent (stretch), rularea 1 | [328, 822, 1417] | 2,567 | 9,791 | 12,358 |
| subagent, rularea 2 | [328, 711, 1178] | 2,217 | 18,766 | 20,983 |
| subagent, rularea 3 (ERROR, fără raport) | [328, 418] | 746 | 61,975 | 62,721 |

- Istoricul orchestratorului: 118.166 → 2.279 tokeni (≈ 98% mai puțin).
- Totalul general: 118.166 → 60.514 (≈ 49% mai puțin) cu worker structurat; 12.358 (≈ 90% mai puțin) cu sub-agentul.
- Toate trei rulările au găsit același atac: `198.51.100.77`, root compromis, `svc-backup` cu UID=0, `curl` către `/tmp/.x`.

## Întrebarea 4: de ce scade și totalul general, deși worker-ul citește tot logul o dată?

În modul `single`, logul brut (~58k tokeni) intră în **istoricul orchestratorului** ca rezultat al lui `read_file`.
API-ul fiind stateless, el se re-trimite la **fiecare pas următor**: la pasul 2 (58.501, când modelul scrie raportul) și la
pasul 3 (59.369, răspunsul final). Logul se plătește deci de 2 ori, plus raportul lung din argumente.

În modul `orchestrator`, logul se plătește **o singură dată** (58.235), în cererea izolată a worker-ului.
În istoricul orchestratorului ajunge doar JSON-ul compact (câteva sute de tokeni), așa că pașii lui rămân mici.
Un singur drum cu logul + câțiva pași mici < același log re-trimis la mai mulți pași.
Cu cât sarcina orchestratorului are mai mulți pași, cu atât economia e mai mare.

Compromisuri: un apel în plus (worker-ul); orchestratorul știe doar ce a raportat worker-ul (dacă worker-ul greșește,
raportul final e greșit, dar sigur pe el); JSON-ul worker-ului rămâne date nesigure (a citit text controlat de atacator,
de exemplu `firewall_rules` poate conține orice), de aceea scrierea raportului rămâne sub aprobare umană.

## Stretch: cât de des are dreptate sub-agentul? Cum îi verifici ieftin afirmațiile?

**Cât de des:** am rulat modul `subagent` de 3 ori:

| rulare | sub-agent | pași | tokeni sub-agent | rezultat |
|---|---|---|---|---|
| 1 | `done` | 4 | 8.942 | raport corect: `198.51.100.77`, root compromis, evidență verbatim |
| 2 | `done` | 5 | 18.116 | raport corect, același atacator |
| 3 | `max_steps` | 10 | 61.975 | `ERROR` → orchestratorul **nu** a scris raportul și a spus ce a eșuat |

Deci **2 din 3** corecte, iar a treia a eșuat **corect**: propagarea erorii a funcționat, nu a apărut niciun raport inventat.
Costul variază mult (8.942 → 61.975 tokeni): când sub-agentul nu găsește repede pattern-urile bune, fiecare căutare
în plus se adaugă la istoric și se re-trimite la pașii următori. În cazul cel mai rău a costat cât modul `single` (62.721 vs 118.166 total, dar fără rezultat).
Concluzie: sub-agentul e cel mai ieftin când merge, dar cel mai puțin previzibil; worker-ul structurat (modul `orchestrator`) e mai scump, dar stabil.

**Verificare ieftină (fără alt LLM, în cod determinist):**
- fiecare linie din `evidence` trebuie să apară **identic** în log (o căutare de substring);
- fiecare IP din `attacker_ips` trebuie să apară pe o linie `Accepted password` sau `Accepted publickey`, altfel `is_compromised=true` nu e susținut;
- numărul de eșecuri pentru IP-ul atacatorului se poate confirma cu `count_by_ip("Failed password")`;
- comenzile din `firewall_rules` se pot verifica cu un regex (doar `ufw deny from <IP>` sau `iptables -A INPUT -s <IP> -j DROP`, cu IP-uri din listă).

Dacă o verificare pică, raportul se respinge ca `ERROR`, la fel ca un sub-agent care nu a terminat.
