# Estudo — Voice Studio: como mandar EMOÇÃO na voz (`--instruct`)

> Estudo feito em 2026-11-26 a partir da documentação e do código instalado do
> Voice Studio (`C:\Users\Pires\AppData\Local\Programs\VoiceStudio\resources\backend\services\tts_backend.py`
> e `omnivoice/utils/voice_design.py`).

## 1. Onde a emoção entra

O CLI `voicestudio speak` tem o parâmetro **`--instruct`**:

```
voicestudio speak "texto" --voice "Simone-feliz" --instruct "..." [-o saida.wav]
```

É o `--instruct` que carrega a **direção de entrega** (emoção, tom, estilo). O texto
positional é o que será falado — NÃO coloque emoção nele (risada escrita fica robótica).

## 2. Dois vocabulários (`instruct_vocabulary`)

Cada engine do Voice Studio lê o `--instruct` de um jeito:

| Modo | Engines | O que aceita |
|---|---|---|
| **`tags`** | OmniVoice (`instruct_vocabulary = "tags"`) | Só tags do catálogo fechado abaixo; texto livre é **descartado** pelo `sanitize_instruct()` |
| **`freeform`** | padrão (`TTSBackend.instruct_vocabulary = "freeform"`) | Frase em linguagem natural — é aqui que "alegre, sorridente, risonha" funciona |

## 3. Catálogo de TAGS (modo `tags` / OmniVoice)

Tags válidas, uma por categoria (mutuamente exclusivas):

- **Gênero:** `male`, `female`
- **Idade:** `child`, `teenager`, `young adult`, `middle-aged`, `elderly`
- **Tom:** `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`
- **Estilo:** `whisper`
- **Sotaque (só EN):** `american accent`, `british accent`, `australian accent`, `chinese accent`, `canadian accent`, `indian accent`, `korean accent`, `portuguese accent`, `russian accent`, `japanese accent`

Exemplo: `--instruct "female, child, high pitch"`.

⚠️ Se você mandar prosa ("voz alegre e divertida") num engine `tags`, o `sanitize_instruct`
joga fora e a emoção some. Por isso as nossas vozes locais (Frida/Luna/Simone) devem
usar engine **freeform** quando a meta for emoção.

## 4. Modo FREEFORM — onde a emoção de verdade vive

Em engines `freeform`, o `--instruct` é uma frase de direção. Para o nosso cânone
(criança pré-adolescente, 3D Disney-Pixar), usar:

| Emoção desejada | `--instruct` sugerido (freeform) |
|---|---|
| Alegre padrão | `voz infantil alegre, sorridente e empolgada, falando com entusiasmo` |
| Risonha | `voz infantil risonha, com riso contido na voz, muito divertida` |
| Surpresa | `voz infantil com tom de espanto divertido, olhos arregalados` |
| Fofa/carinhosa | `voz infantil doce, carinhosa e fofa, tom macio` |
| Empolgada (corrida) | `voz infantil muito animada, falando depressa e sorrindo` |
| Calma (ponte) | `voz infantil calminha e aconchegante, ritmo suave` |
| Brincalhona | `voz infantil brincalhona, com tom de piada e sorriso` |

## 5. Controle de entrega por engine (`instruct_directs_delivery`)

Alguns engines (ex.: **VoxCPM2**, `instruct_directs_delivery = True`) usam o instruct
como **prefixo de controle** da fala — ele *realmente* altera a entrega (como um ator
recebendo uma direção). Outros (ex.: OmniVoice) só mudam o desenho da voz (timbre),
não a emoção da frase.

## 6. Regras do nosso motor (contrato, Regra 32 + esta)

1. **Nunca escrever risada no texto** (`hahaha` é removido por `normalize_phonetics_pt`); risada é **emoção no `--instruct`**.
2. Apelidos carinhosos (**Fridóca, Luninha**) são canônicos — nunca trocar por "correção" de QA; ajustar a **semântica/pontuação** (`Olha! Fridóca, vem cá!`).
3. **Pontuação é o diretor**: `!` sobe energia, `?!` espanto, `...`/`—` pausa de piada, frases curtas evitam modo monótono.
4. rates: Frida 1.05, Luna 1.12, narrador/Puck 1.10.
5. Para **emoção explícita** em voz local, preferir engine `freeform` + `--instruct` da tabela acima; em `tags`, usar `child/female/high pitch`.
