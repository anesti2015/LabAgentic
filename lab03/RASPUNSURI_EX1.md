# Lab 3 – Ex 1: bucla ReAct protejată („Which production hosts are exposed?”)

## Ce am implementat (`agent_core.py`)

- **`execute_tool()`**: orice eșec devine un rezultat, nu o excepție:
  - tool necunoscut → `ERROR: Unknown tool '<name>'. Available tools: ...`;
  - argumente greșite → `ERROR: Bad arguments for <name>: ...` + semnătura corectă (`Expected: get_installed_packages(hostname: str) -> str`) și ce a trimis modelul, ca să se poată corecta singur;
  - orice altă excepție → `ERROR: <name> failed: ...`.
- **Bucla**: execută **toate** apelurile dintr-un pas, câte un `function_response` pentru fiecare apel (cu `id`-ul lui), toate într-un **singur** mesaj `role="user"` (Gemini nu are rolul `tool`).
- **Oprire**: `done` (fără tool calls), `max_steps` (buget), `provider_error` (după retry), `stuck`.
- **Stretch – detectorul de blocaj**: perechea (nume, argumente sortate) e numărată. Al 2-lea apel identic nu se mai execută, modelul primește `NOTE: Repeated call ... Use the earlier result`. Al 3-lea apel identic oprește agentul cu `stuck`.
- `lab3_ex1_react.py` este fișierul dat, neschimbat.

Rulare: `python lab3_ex1_react.py` (sau `--thoughts` pentru rezumatul raționamentului).

## Rezultat (rularea mea)

`stop_reason=done`, 4 pași, tokeni de intrare pe pas: **[309, 402, 615, 1246]**, total **2.572**.
`list_hosts` → 3 × `get_installed_packages` (în paralel, doar producție) → 9 × `find_cves_for_package` (în paralel) → răspunsul:
- `db-prod-01`: xz-utils 5.6.1, CVE-2024-3094, CVSS 10.0
- `web-edge-01`: log4j-core 2.14.0, CVE-2021-44228, CVSS 10.0
- `mail-prod-02`: verificat, curat la CVSS ≥ 9.0
- `ci-runner-03` e vulnerabil (xz-utils 5.6.0), dar e **staging**, deci nu intră în răspuns.

## Întrebarea 1: câte apeluri API și câte apeluri de tool-uri? De ce contează diferența pentru latență?

**4 apeluri API** (câte unul pe pas) și **13 apeluri de tool-uri** (1 + 3 + 9).
Latența e dominată de drumurile dus-întors la model, nu de tool-uri (care sunt locale și instantanee).
Pentru că modelul cere apelurile independente **în paralel, în același pas**, cele 13 tool-uri costă doar 4 drumuri la model.
Dacă le-ar fi cerut pe rând, ar fi fost 14 apeluri API, adică de 3–4 ori mai lent și mai scump (fiecare apel re-trimite tot istoricul).

## Întrebarea 2: tokenii de intrare cresc la fiecare pas (la mine 309 → 402 → 615 → 1.246). Ce mesaje se re-trimit?

API-ul e **stateless**: la fiecare pas se trimite din nou **tot**:
- system instruction-ul și declarațiile celor 3 tool-uri;
- întrebarea utilizatorului;
- toate turele anterioare ale modelului (apelurile de funcții, cu thought signatures);
- toate rezultatele tool-urilor de până atunci.

Saltul mare de la ultimul pas vine din cele 9 rezultate `find_cves_for_package` adăugate în istoric.

## Întrebarea 3: openssh-server 9.6 are CVE-2024-6387. De ce nu apare în răspuns?

Pentru că are **CVSS 8.1**, sub pragul cerut (**≥ 9.0**). Tool-ul îl găsește corect (9.6 e între 8.5 și 9.7),
dar modelul îl filtrează la răspunsul final, conform întrebării.
