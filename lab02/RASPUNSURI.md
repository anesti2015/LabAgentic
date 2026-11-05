# Lab 2 – Part 0: Model Literacy

## Formula folosită

VRAM (GB) ≈ (P × B/8) × 1,2

- **P** = numărul de parametri, în miliarde
- **B** = biți per parametru (FP16 = 16, INT8 = 8, INT4 = 4)
- **1,2** = factor suplimentar pentru KV cache și activări

## Întrebarea 1: model de 70B la INT4 pe un GPU de 24 GB

VRAM ≈ 70 × (4/8) × 1,2 = 70 × 0,5 × 1,2 = **42 GB**

**Nu încape** pe un GPU de 24 GB, pentru că 42 GB > 24 GB. Variante posibile:
- cuantizare mai agresivă (2–3 biți/parametru), cu pierdere de calitate;
- împărțirea modelului pe mai multe GPU-uri (de exemplu 2 × 24 GB);
- descărcarea unei părți din straturi în RAM (CPU offloading), cu viteză mult mai mică;
- alegerea unui model mai mic (de exemplu 7B–14B la INT4).

## Întrebarea 2: `Mistral-7B-v0.3` vs `Mistral-7B-Instruct-v0.3` pentru JSON și tool calling

Alegem **`Mistral-7B-Instruct-v0.3`**.

- Modelul **Base** (`-v0.3`) este antrenat doar să continue text. Nu a învățat să urmeze instrucțiuni, să respecte un format cerut sau să se oprească la momentul potrivit.
- Modelul **Instruct** a primit în plus instruction-tuning: urmează un system prompt, respectă formate stricte (JSON) și generează apeluri de funcții structurate.

Pentru un agent care depinde de JSON valid și de tool calling, varianta Instruct este cea corectă.
