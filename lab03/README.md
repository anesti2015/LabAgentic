# Laboratorul 3 – The ReAct Loop, Human-in-the-Loop (HITL) & Orchestrator-Workers

Enunț: <https://gdt050579.github.io/agenticai_course_fii/labs/lab-3.html>

Laboratorul transformă bucla ReAct din Lab 2 într-un **harness reutilizabil** (`agent_core.py`) și îl ține sub control:

1. bucla ReAct cu condiții de oprire (răspuns final, buget de pași, agent blocat, eroare de provider) și erori care devin rezultate;
2. politica de aprobare umană (HITL) separată de unelte și un sandbox pentru căi, testat fără LLM;
3. orchestrator–workers: logul mare se citește într-un context izolat, ca să nu umfle istoricul orchestratorului.

Model folosit: `gemini-3.5-flash-lite` (se schimbă cu variabila `LAB_MODEL`, de exemplu `gemini-3.1-flash-lite`).

## Fișiere

| Partea | Fișier | Ce face | Rezultat |
|---|---|---|---|
| Harness | [`agent_core.py`](agent_core.py) | `run_agent()`: apeluri paralele, un `function_response` per apel, erori explicabile, buget, detector de blocaj (stretch), poarta de aprobare | – |
| Ex. 1 | [`lab3_ex1_react.py`](lab3_ex1_react.py) | Întrebare multi-hop: ce host-uri de producție au CVE cu CVSS ≥ 9.0 | `db-prod-01` și `web-edge-01`, 4 pași, tokeni [309, 402, 615, 1246] |
| Ex. 2 | [`lab3_ex2_hitl.py`](lab3_ex2_hitl.py) | Agent de remediere `sshd_config` cu aprobare umană și sandbox | Respins cu feedback → scrie `sshd_config.hardened`; `--attack` blocat, canary-ul nu apare |
| Ex. 2 | [`test_lab3_ex2.py`](test_lab3_ex2.py) | Teste deterministe pentru sandbox și approver | `pytest`: 11 passed |
| Ex. 3 | [`lab3_ex3_orchestrator.py`](lab3_ex3_orchestrator.py) | Moduri `single`, `orchestrator` și `subagent` (stretch, cu propagarea erorii) | istoric orchestrator −98%; sub-agent corect 2/3, a 3-a oară `ERROR` fără raport |
| Răspunsuri | [`RASPUNSURI_EX1.md`](RASPUNSURI_EX1.md), [`RASPUNSURI_EX2.md`](RASPUNSURI_EX2.md), [`RASPUNSURI_EX3.md`](RASPUNSURI_EX3.md) | Întrebările de checkpoint | – |

## Ex. 3: tokeni de intrare

| mode | orchestrator input tokens per step | orchestrator total | worker total | grand total |
|---|---|---|---|---|
| single | [296, 58501, 59369] | 118,166 | 0 | 118,166 |
| orchestrator | [316, 729, 1234] | 2,279 | 58,235 | 60,514 |
| subagent (stretch), rularea 1 | [328, 822, 1417] | 2,567 | 9,791 | 12,358 |
| subagent, rularea 2 | [328, 711, 1178] | 2,217 | 18,766 | 20,983 |
| subagent, rularea 3 (ERROR, fără raport) | [328, 418] | 746 | 61,975 | 62,721 |

## Rulare

Comenzile se dau din rădăcina repository-ului, cu `.venv` activ:

```powershell
python lab03/lab3_ex1_react.py                 # --thoughts pentru rezumatul raționamentului
pytest lab03/test_lab3_ex2.py -v
python lab03/lab3_ex2_hitl.py                  # --attack / --no-guard pentru demo
python lab03/lab3_ex3_orchestrator.py single       --auto-approve
python lab03/lab3_ex3_orchestrator.py orchestrator --auto-approve
python lab03/lab3_ex3_orchestrator.py subagent     --auto-approve
```

Fișierele generate la rulare ajung în `lab3_data/`, care este exclus prin `.gitignore`.
