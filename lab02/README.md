# Laboratorul 2 – Model Literacy, Prompt Engineering, Structured Outputs & Tool Calling

Enunț: <https://gdt050579.github.io/agenticai_course_fii/labs/lab-2.html>

Laboratorul construiește cei trei piloni ai unui **harness agentic**:

1. system prompts proiectate, cu exemple few-shot;
2. răspunsuri structurate, validate de o schemă (*constrained decoding*);
3. apeluri de unelte (*tool calling*).

Model folosit: `gemini-3.5-flash-lite`. Se poate schimba din `.env` cu variabila `GEMINI_MODEL`.

## Fișiere

| Partea | Fișier | Ce face | Rezultat |
|---|---|---|---|
| Part 0 | [`RASPUNSURI.md`](RASPUNSURI.md) | Estimarea VRAM și alegerea între Base și Instruct | 70B la INT4 ≈ 42 GB, nu încape pe 24 GB |
| Part 1 | [`smoke_test.py`](smoke_test.py) | Primul apel către Gemini; cheia e citită din `.env` | `Telemetry online.` |
| – | [`list_models.py`](list_models.py) | Listează modelele Gemini disponibile pentru cheie | – |
| Ex. 1 | [`module1_prompting.py`](module1_prompting.py) | System prompt cu 4 piloni (rol, context și few-shot, constrângeri, format) și protecție la injecții de prompt | 3 bullets fixe; injecția e blocată |
| Ex. 2 | [`test_module2_structured.py`](test_module2_structured.py) | Analiza unui log SSH cu ieșire JSON validată de o schemă Pydantic | `pytest`: 1 passed |
| Ex. 3 | [`module3_tools.py`](module3_tools.py) | Ciclul complet de tool calling, implementat manual | Răspuns cu CVSS 10.0 și xz-utils 5.6.x |
| Bonus | [`bonus_react.py`](bonus_react.py) | Agent ReAct: 2 unelte, cel mult 5 iterații, feedback de eroare și reîncercare automată | db-prod-01 e afectat de CVE-2024-3094 |
| Temă | [`homework_david_vs_goliath.py`](homework_david_vs_goliath.py) | Un model mic decodează hex și detectează o injecție (`reasoning_trace` și few-shot) | Toate cele 3 asserturi trec |

## Rulare

Comenzile se dau din rădăcina repository-ului, cu `.venv` activ:

```powershell
python lab02/smoke_test.py
python lab02/module1_prompting.py
pytest lab02/test_module2_structured.py -v
python lab02/module3_tools.py
python lab02/bonus_react.py
python lab02/homework_david_vs_goliath.py
```

## Observații tehnice

- **`role="user"` în loc de `role="tool"`.** Enunțul trimite rezultatul uneltei cu `role="tool"`, dar API-ul Gemini răspunde cu `400 INVALID_ARGUMENT: Role 'tool' is not supported`. Pentru `function_response`, Gemini acceptă doar `role="user"`.
- **Numele modelului pentru temă.** Enunțul cere `gemini-3.5-flash-lite-lite`, care pare o greșeală de tipar. S-a folosit `gemini-3.5-flash-lite`, configurabil prin `HOMEWORK_MODEL`.
- **Feedback de eroare (bonus).** Dacă modelul cere o unealtă care nu există, primește înapoi lista uneltelor valide (`' '.join(TOOLS.keys())`) și se poate corecta la iterația următoare. Excepțiile din unelte ajung la model ca rezultat; programul nu se oprește.
- **Reîncercare automată (bonus).** La erorile temporare 429, 500 și 503 („model is experiencing high demand”), `call_llm` reîncearcă după 5 s, 10 s și 20 s (*exponential backoff*).
- **Răspunsuri bazate pe date.** În Ex. 3, răspunsul final poate include și cunoștințe proprii ale modelului, nu doar rezultatul uneltei. În bonus, system prompt-ul cere explicit „based only on tool results”.
