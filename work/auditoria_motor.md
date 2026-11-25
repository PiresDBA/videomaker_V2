# Auditoria do Motor Videomaker v2 — causa-raiz do bug da Parte 2 e correções

Data: 2026-11-25. Escopo: descobrir por que a Parte 2 da praia saiu com narração
desconectada do visual e a auditoria não pegou, e corrigir o motor para não repetir.

## O que aconteceu (cadeia de causas)

1. A mídia foi atribuída às cenas por **rodízio mecânico** (`video = ordem[i % total]`),
   sem casar com a narração. Ex.: sc_04 fala "apareceu uma gaivota branca" e mostra
   "Puppies jumping on sunny beach".
2. A gaivota (Guga) é falada em 26 cenas e **não aparece nenhuma vez**, porque:
   - os 6 vídeos de gaivota do Flow são os **corrompidos** (0,00s);
   - as 6 **imagens** de gaivota existem mas **nunca foram copiadas** para o projeto.
3. As imagens não foram intercaladas: como **todas** as cenas viraram "cena de vídeo"
   (`assets/videos/sc_XX.mp4` presente), o motor renderiza todos os sub-clips do vídeo e
   ignora as imagens — não há como intercalar imagem dentro de uma cena de vídeo.
4. A auditoria **aprovou** porque a porta de entrega (`delivery_audit` + `fine_audit`)
   compara cada sub-clip **com o material que ele próprio foi gerado** (similaridade
   ~0,9 trivial). Ela não compara o conteúdo do vídeo com o **texto da narração**.
   A única checagem que faz isso (scene_auditor com Vision) só roda para mídia
   **gerada** — e o render usou `--skip-images --skip-veo`, pulando exatamente essa porta.

## Bugs encontrados (ordenados por gravidade)

| # | Bug | Onde | Status |
| --- | --- | --- | --- |
| 1 | **Sem auditoria narração×visual no caminho de reuso.** `--skip-images/--skip-veo` desliga a única checagem semântica (Vision) sem substituto. | `core/self_audit.py`, `pipeline_v2.py` | **Corrigido** (novo `core/sync_audit.py`) |
| 2 | **Atribuição de mídia por nome de arquivo, sem descrição.** Roteiro↔mídia é implícita (`scene_id` → arquivo); não existe vínculo semântico nem manifesto de mídia. | `core/video_assembler.py` `_resolve_scene_videos` | **Mitigado** (manifesto + auditoria) |
| 3 | **`normalize_script_records` descarta campos desconhecidos** (`video`, `image`) em silêncio — a dica de mídia por cena era perdida. | `core/script_engine.py` | **Corrigido** |
| 4 | **Cena com vídeo "engole" as imagens** — todos os sub-clips renderizam do MP4; imagem estática não pode ser intercalada na mesma cena. | `core/pacing_planner.py` + `assembler` | Documentado; contorno na montagem |
| 5 | **Bug no cache de voz:** `timings` gravava `locked:Puck` (voz Gemini) em vez da voz real do Voice Studio (Simone-feliz), disparando "trocou de voz". | `core/voice_studio.py` `synthesize_all_scenes` | **Corrigido** |
| 6 | **Sem checagem de cobertura de personagem secundário** — Guga narrado 26 vezes, aparece 0, e nada reclamava. | (ausente) | **Corrigido** via `sync_audit` |
| 7 | **`video_ok` (ffprobe) falsos positivos** — stream vazio com duração >0 marcava vídeo bom como corrompido. | `work/preparar_selecao.py` | Corrigido anteriormente (dur ≤ 1,0s) |

## Correções aplicadas ao motor (este commit)

1. **`core/sync_audit.py` (novo):** auditoria de sincronia narração×visual **sem Vision**.
   - Exige `artifacts/media_assignment.json` (cena → vídeo/imagem + descrição).
   - **Cobertura de personagem:** secundário narrado em N cenas precisa aparecer ≥ 1 vez.
   - **Alinhamento de âncora:** fala cita gaivota/biscoito/castelo/concha/balde/toalha/
     protetor → a mídia designada precisa conter a âncora (ou sinônimo PT/EN).
2. **`run_final_audit`** ganha `require_media_manifest` e chama `audit_narration_sync`
   quando o episódio reusa mídia (ou quando o manifesto existe).
3. **`pipeline_v2.py`** passa `require_media_manifest=True` quando `--skip-images` ou `--skip-veo`.
4. **`normalize_script_records`** preserva os campos `video` e `image`.
5. **`voice_studio.py`** corrige o metadata de voz no cache (bug `locked:Puck`).

### Validação da correção

Rodei `audit_narration_sync` sobre a Parte 2 (atribuição antiga) e ele detectou **29
problemas**, incluindo exatamente:
- "personagem 'Guga' é narrado em 26 cena(s) mas NÃO aparece em nenhuma mídia (cobertura zero)"
- "cena sc_04: a fala cita 'gaivota' mas a mídia designada ('Puppies jumping on sunny beach') não contém essa âncora"

## O que falta fazer (construir a Parte 2 corretamente)

1. Reescrever a atribuição de mídia **semanticamente** (cada fala → vídeo/imagem correta),
   intercalando as **imagens da Guga** e as demais fotos **entre** os vídeos (alternar
   cenas de vídeo e cenas de imagem).
2. Gerar `artifacts/media_assignment.json` com as descrições.
3. Re-renderizar e confirmar que `audit_narration_sync` passa com **0 issues**.
