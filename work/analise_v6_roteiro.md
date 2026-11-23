# Análise v6 — Roteiro × Mídia (`primeiro-dia-de-praia-v6`)

Leitura-only. Fontes: `projects/primeiro-dia-de-praia-v6/artifacts/script_v2.json`,
`.../tts_timings_v2.json`, `.../pacing_plan_v2.json`, `.../veo_generation_ledger.json`,
`.../scene_audit_report.json`, `projects/primeiro-dia-de-praia-v5/artifacts/final_audit_report.json`,
`assets/reference/primeiro-dia-de-praia/analise_v2_all.json` + `flow_all/harvest_manifest.json`.
Durações medidas com `bin/ffprobe.exe`. Nenhum pipeline/render foi executado.

## Resumo executivo

| Métrica | Valor |
|---|---|
| Roteiro v6 | 30 cenas, 513 palavras, `target_minutes=3.5`, 3 atos (1:5 / 2:14 / 3:11) |
| Narração (30 WAVs, `tts_timings_v2.json`) | **179,19 s** (~3 min) |
| Vídeos Veo no projeto | **16 arquivos**, 15 × 7,93 s + `sc_30` 22,80 s = **141,7 s brutos** |
| Cenas com vídeo próprio | **13 de 30** |
| Cenas só com imagem/estático | **17 de 30** |
| Imagens no projeto v6 | **24**, todas em `sc_01..sc_06` (zero em `sc_07..sc_30`) |
| Referência aprovada v5 | 25 cenas, 508 palavras, **10 vídeos**, 52 clipes visuais, output **188,5 s**, `approved: true`, Earshot 0.939 "launch-grade" |

Conclusão-antecipada: **não estender para 15 min.** O material real sustenta ~3–4 min (o v5 aprovado tinhas 188 s com 10 vídeos; o v6 tem 16 vídeos → teto realista ~230 s ≈ 3:50).

---

## 1. Os 16 vídeos da v6: duração × cena × `aria`

`tabela`: arquivo em `projects/primeiro-dia-de-praia-v6/assets/videos/`; "cena" = nome base do arquivo (remove `_v2/_v3`), que é o mapeamento autoritativo para o roteiro novo; `aria/classe` vem de `analise_v2_all.json` **quando o SHA bate**.

| Arquivo | Duração | Cena v6 (fala) | `aria` / classe no `analise_v2_all.json` |
|---|---|---|---|
| `sc_01.mp4` | 7,93 s | sc_01 – "salsicha tentar domar o mar… corre, Luna!" | "Puppies looking at approaching wave" — `fora_tema` (rótulo do roteiro antigo; visual bate com a onda) |
| `sc_02.mp4` | 7,93 s | sc_02 – "a areia me mordeu… cócegas" | sem match no análise |
| `sc_03.mp4` | 7,93 s | sc_03 – "areia fofinha como tapete de açúcar" | "Bulldog puppy walking on beach" — `fora_tema` |
| `sc_04.mp4` | 7,93 s | sc_04 – "lambe a areia… gosto de terra salgada" | "Puppy licks sand making face" — `fora_tema` |
| `sc_04_v2.mp4` | 7,93 s | sc_04 (variante) | "Puppy licking sand on beach" — **`usado`** |
| `sc_05.mp4` | 7,92 s | sc_05 – "passar o protetor solar" | sem match |
| `sc_05_v2.mp4` | 7,93 s | sc_05 (variante) | sem match |
| `sc_05_v3.mp4` | 7,93 s | sc_05 (variante) | sem match |
| `sc_06.mp4` | 7,93 s | sc_06 – "tubo de creme liso… patinando" | "Dachshund puppy jumping on beach" — **`usado`** (cena antiga sc_01) |
| `sc_11.mp4` | 7,93 s | sc_11 – "só vejo seu rabinho" | "Puppy running in circles" — **`usado`** (antigo sc_03) |
| `sc_15.mp4` | 7,93 s | sc_15 – "gaivota vai levar o biscoito" | "Bulldog pointing at ocean" — **`usado`** (antigo sc_02) |
| `sc_21.mp4` | 7,93 s | sc_21 – "mar chegando… ondas de trovão" | "Puppies reacting to ocean wave" — **`usado`** (antigo sc_05) |
| `sc_23.mp4` | 7,93 s | sc_23 – "corre para o morrinho!" | "Puppy posing before ocean wave" — **`usado`** (antigo sc_06) |
| `sc_24.mp4` | 7,93 s | sc_24 – "estou flutuando, sou um barquinho" | "Puppy getting wet by wave" — **`usado`** (antigo sc_07) |
| `sc_26.mp4` | 7,93 s | sc_26 – "que aventura… adorei a onda" | sem match |
| `sc_30.mp4` | **22,80 s** | sc_30 – despedida + SUBSCRIBE | sem match (3× a duração dos demais; é o vídeo-CTA) |

**Atenção importante:** `veo_generation_ledger.json` e `scene_audit_report.json` apontam para `projects/primeiro-dia-de-praia-2/...` (não v6). Os SHAs batem — a v6 **reaproveitou** os vídeos/áudios do projeto `-2`, e o `analise_v2_all.json` é uma análise **antiga** (roteiro v2/v5), com numeração de cenas diferente. Por isso os `aria` casam mal com as falas novas: use o nome do arquivo como mapa de cena, não a coluna `scene` do análise. Apenas **7 dos 16** vídeos aparecem como `usado` no análise; os outros 9 são gerações/reaproveitamentos fora daquela análise.

---

## 2. Cobertura: 13 cenas com vídeo, 17 desertas

**Com vídeo (13):** sc_01, 02, 03, 04, 05, 06, 11, 15, 21, 23, 24, 26, 30.
**Sem vídeo (17):** sc_07, 08, 09, 10, 12, 13, 14, 16, 17, 18, 19, 20, 22, 25, 27, 28, 29.

Distribuição por ato:
- Ato 1 (sc_01–05): **5/5 com vídeo** ✅
- Ato 2 (sc_06–19): só sc_06, 11, 15 → **3/14** ❌
- Ato 3 (sc_20–30): sc_21, 23, 24, 26, 30 → **5/11** ⚠️

**Lacunas de alto impacto (prioridade de correção):**
1. **sc_10 e sc_22 — a frases-título.** O gancho do título é "a areia que fugiu" e a *catchphrase* "Eu não cavei, a areia que fugiu!" aparece em **sc_10 e sc_22 — ambas sem vídeo**. O mistério que vende o episódio é contado só com imagem estática.
2. **Subtrama do Guga (sc_13–17): 0 vídeos em 7 cenas** (sc_12–19). O roubo do biscoito é o clímax dramático do ato 2 e não tem nenhum movimento.
3. **sc_09** (cavar o castelo, onde nasce o buraco) e **sc_25** (resgate na areia) — sem vídeo.
4. **sc_07/sc_08** (escorregar no protetor + virar "fantasma de creme") — sem vídeo; o ato 2 começa bem com sc_06 e depois seca.

Agrava: `assets/images/` tem **24 arquivos apenas para sc_01–sc_06**; `pacing_plan_v2.json` define **171 clips** para as 30 cenas (4–14 por cena), mas **sc_07..sc_30 não têm nenhum arquivo de imagem próprio no disco**. A montagem dessas 24 cenas dependerá das imagens da colheita (`duplicata_reencode` cobre justamente sc_11..sc_25) ou de nova geração — fato a validar antes do assemble.

---

## 3. Colheita: 287 imagens × limiar da Regra 26

`analise_v2_all.json` — 384 itens (287 imagens + 97 vídeos):

| Classe | Imagens | Vídeos |
|---|---|---|
| `usado` | **0** | **7** |
| `candidato` | **4** | 0 |
| `duplicata_reencode` | 30 | 0 |
| `fora_tema` | **253** | **90** |
| Total | 287 | 97 |

Detalhes das 4 `candidato`: `kf_8810dc_sc_02_p1.jpg` (×2, duplicata), "Puppies sliding together on sand", "Puppy shaking sand on beach". As 30 `duplicata_reencode` **são temáticas** (ex.: "Two puppies hugging on beach", "Seagull diving toward puppy biscuit", "Puppies looking up at shadow", "Puppy buried in sand smiling") — foram marcadas como duplicata, não como fora de tema. Há ainda **22 imagens `fora_tema` com `aria` praiana** (ex.: "Puppy pointing at sunscreen tube", "Puppy sliding on beach towel", "Yellow plastic bucket with handle", "Seagull diving toward biscuit").

### Veredito Regra 26 (≥10 vídeos e ≥60 imagens do tema)

| Critério | Contagem estrita (`usado`+`candidato`) | Contagem realista (v6 + duplicatas + praianas) | Limiar |
|---|---|---|---|
| Vídeos | **7** ❌ | 16 no v6 (+ ~20 com colheita) ✅ | ≥10 |
| Imagens | **4** ❌ | 24 (v6) + 30 (duplicatas) + 4 (candidatas) + 22 (praianas fora_tema) ≈ **80** ✅ (com dedup ~60–70) | ≥60 |

- **Estritamente pelos rótulos do análise: reprova nos dois critérios** (7 vídeos, 4 imagens). O análise está desatualizado em relação à v6.
- **Pelo material fisicamente disponível: vídeos passam, imagens passam de forma apertada** — mas é material **concentrado em sc_01–06** e em cenas do roteiro antigo, não cobre bem sc_13–19 (Guga) nem sc_27–29.
- **Mesmo assim, NÃO estender para 15 min.** A matemática de duração é o limite real: narração atual 179 s; 15 min exigiriam ~900 s de fala (~2.500 palavras, ≈5× o roteiro), e os 141,7 s de vídeo + 171 clips de imagem esgotam-se em ~3–4 min. Regra 26 exige *material suficiente* **e** *roteiro bom*; aqui o roteiro é curto e o material é escasso fora do ato 1.

---

## 4. Recomendações acionáveis

### (a) Adaptar texto/ganchos aos 16 vídeos
- **Não reescreva as 30 falas**: 513 palavras / 179 s dá ~6 s por cena, casando bem com vídeos de 7,93 s (1 vídeo ≈ 1,3 cenas). O problema é *distribuição*, não volume.
- **Reposicione os 3 spares** — `sc_04_v2.mp4`, `sc_05_v2.mp4`, `sc_05_v3.mp4` são variantes não usadas. Regra 25 proíbe gerar novo vídeo (`should_generate_new_veo()`), então **reutilize-os** em sc_10, sc_22 e uma cena do Guga. Atenção: `scene_auditor.py` (mesmo em `light`) exige que o visual bata com a narração — `sc_04_v2` (lamber areia) serve para sc_10; as variantes de protetor servem para sc_07/sc_08. Se o emparelhamento ficar torto, prefira imagem da colheita.
- **Reforce o gancho** já presente: `thumb_hook="SALSICHA VS MAR"` e a pergunta de sc_01 estão alinhadas. Acrescente uma pausa de 0,3–0,5 s antes de "a areia que fugiu!" em sc_10 e sc_22 (SFX `cartoon boing` na pausa, conforme Regra 16) para transformar a catchphrase em *payoff* sonoro.

### (b) Dramaturgia para prender atenção
- Atos 1 e 3 estão bem servidos; **o ato 2 é o ponto de fuga** (3/14 cenas com vídeo). Coloque o melhor material do Guga (imagens "Seagull diving toward puppy biscuit", "Puppies looking up at shadow") em sc_13–17 e o spare de vídeo no roubo (sc_16).
- A sequência sc_09 → sc_10 → sc_11 (cavar → buraco → rabinho) é o arco engraçado mais forte do roteiro; hoy só sc_11 tem vídeo. Dar movimento a sc_10 resolve o maior vazamento de atenção do episódio.
- Repetição da catchphrase em sc_10, sc_22 e sc_30 é um bom motif — mantenha.

### (c) CTA (meio) e despedida composta (final) — Regra 25
- **CTA no meio:** 30 cenas → ponto médio ≈ **sc_15**, que **já tem vídeo** (`sc_15.mp4`). Aplique o overlay transparente (joinha + sininho + SUBSCRIBE, `.mov` qtrle via `core/cta_overlay.py`) centrado em sc_15 (~50% de 179 s ≈ 1:30), sobre o clímax da gaivota — é onde a atenção pica.
- **Despedida final:** âncora = **`sc_30.mp4` (22,80 s)**, cuja `visual_action` já traz "botão SUBSCRIBE aparece e brilha". Monte a despedida por crossfade entre as boas (sc_26 → sc_29 → sc_30), **terminando na que tem YouTube+SUBSCRIBE**, sem gerar vídeo novo e sem usar clipes com patinha fantasma/patas modificadas.

### (d) Estender para 15 min?
**Não, neste estado.** Roteiro 179 s de fala, 141,7 s de vídeo e imagens concentradas no ato 1 não sustentam 15 min sem virar repetição (prejudica retenção, não ajuda). Meta realista e segura: **3:30–4:00**, usando os 16 vídeos (vs. 10 do v5) — o v5 aprovado cravou 188,5 s com 10 vídeos e nota 0.939; a v6 tem +6 vídeos, o que permite ~40–50 s extras de movimento. Só reavalie 15 min se houver, antes do assemble, (i) roteiro novo de ~2.500 palavras, (ii) mais falas Voice Studio, e (iii) ≥60 imagens temáticas **dedicadas às cenas 07–30** — hoje elas não existem no disco.

---

## 5. Cheque-list antes do assemble

1. Revalidar mapeamento vídeo×fala (os `aria` do análise são do roteiro antigo).
2. Confirmar origem das imagens para sc_07..sc_30 (pacing define 171 clips, disco tem 24 em sc_01–06).
3. Auditar os 3 spares antes de reposicioná-los (`--audit-profile light` aceita, `strict` pode barrar).
4. Posicionar CTA em sc_15; compor final em sc_26→sc_29→sc_30 com `sc_30.mp4` como âncora.
5. Manter `selfDeclaredMadeForKids: False` e todas as travas do `verify_contract_guard.py`.
