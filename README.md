# LabAgentic

Laboratoarele cursului **Agentic AI** – Facultatea de Informatică Iași (FII).

Pagina cursului: <https://gdt050579.github.io/agenticai_course_fii/>

## Laboratoare

| Laborator | Tema | Folder | Stare |
|---|---|---|---|
| Lab 2 | Model Literacy, Prompt Engineering, Structured Outputs & Tool Calling | [`lab02/`](lab02/) | ✅ complet |
| Lab 3 | *în lucru* | `lab03/` | ⏳ |

Fiecare folder are propriul `README.md`, cu enunțul pe scurt, fișierele și rezultatele.

## Mediul de lucru

- Python 3.10+ (testat pe Python 3.14, Windows)
- SDK: [`google-genai`](https://pypi.org/project/google-genai/) – modele Gemini
- Toate laboratoarele folosesc un singur mediu virtual și un singur fișier `.env`, aflate în rădăcina repository-ului.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Cheia API se pune într-un fișier `.env` în rădăcină. Fișierul **nu** este urcat pe GitHub: este exclus prin `.gitignore`.

```
GEMINI_API_KEY="cheia_ta"
# opțional:
# GEMINI_MODEL="gemini-3.5-flash-lite"
```

Scripturile se rulează din rădăcina repository-ului, de exemplu:

```powershell
python lab02/smoke_test.py
```

## Structura

```
LabAgentic/
├── README.md          ← acest fișier
├── requirements.txt   ← dependențe comune
├── .gitignore         ← exclude .env, .venv, cache-uri
├── lab02/             ← Laboratorul 2
└── lab03/             ← Laboratorul 3 (în curând)
```
