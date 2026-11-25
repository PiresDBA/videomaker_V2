# Videomaker v2 — Motor Único e Autocontido ("Frida & Luna")

Pipeline completo e independente dentro de `E:\videos\videomaker_v2`, sem dependências externas em tempo de execução e sem alterar o repositório `PiresDBA/videomaker`.

## Estrutura Integrada

- `config.py` — Bíblia Visual (`VISUAL_BIBLE`), casting emocional multi-voz (`SPEAKER_VOICE_PROFILES`), limiares acústicos (`PROSODY_LIMITS`) e perfis dos avatares (`AVATAR_PROFILES`).
- `core/script_engine.py` — Roteiros de 3 atos (450–550 palavras), gancho nos primeiros 5s, diálogo dinâmico **Frida × Luna**, direção emocional por cena (`emotion_direction`) e CTA nos últimos 10s.
- `core/voice_studio.py` — Motor embutido de voz emocional (Gemini 2.5 Flash TTS com rotação de chaves no `.env`), normalização fonética PT-BR pré-TTS, **Portão Acústico de Prosódia** (F0 >= 8 semitons, dinâmica >= 0.25, velocidade 10.6–19.5 car/s) e **Whisper QA**.
- `core/avatar_studio.py` — Studio Dual-PiP **Frida & Luna** (`assets/avatars/frida` e `assets/avatars/luna`) com indexação de boca em 3 níveis por RMS + gerador automático do pacote Luna (`--build-avatar luna`).
- `core/media_studio.py` — Prompts travados na Bíblia Visual + sanitizador anti-vazamento + detector de colagens + gerador de **3 Thumbnails A/B (1280×720)** de alto CTR.
- `core/flow_continuity.py` — Automação direta no Google Flow via Chrome CDP (`Nano Banana 2.1` 16:9 a 0 créditos e `Veo 3.1 - Lite` x1 8s a 10 créditos) com trava de continuidade de personagens (`Frida`/`Luna`) e cenário por fase de luz.
- `core/flow_accounts.py` — Pool multi-conta (até 5 contas Google, portas `18800..18804`, limite 50 créditos/dia por conta) com failover automático e replicação de personagens/frames de continuidade entre contas (`--flow-accounts-status`, `--setup-flow-account`).
- `core/audio_fx.py` — Sonoplastia híbrida (`Earshot` + `Freesound` via `vendor/gerenciador_efeitos_sonoros.py` atenuada <= 0.35), trilha por Ato e mastering via `SoundCraft CLI` + `-14 LUFS`.
- `core/motion_shorts.py` — Gerador de Shorts 9:16 (30–40s) com barra de progresso, Hook animado, legendas Pop coloridas por personagem e suporte opcional ao `Remotion` (`--short-engine remotion`).
- `core/legacy_auditor.py` — Auditoria e importação em lote dos projetos legados (`--batch-scan`, `--legacy-dir`) reaproveitando imagens limpas e recriando apenas o necessário.
- `core/self_audit.py` — Auto-auditoria final obrigatória (`artifacts/final_audit_report.json`) validando roteiro, áudio, imagens, proporções e sincronia A/V (com suporte a Gemini Vision `--vision-audit`).
- `core/delivery_audit.py` — **Porta de entrega obrigatória** (Regras 9, 13 e 27–30): auditoria visual LOCAL e determinística dos frames renderizados — whitelist/blacklist por SHA, frame×cena, tema, anti-repetição (cota + vizinhança), slow-motion sem estrobo, despedida/CTA. Reprova o vídeo antes de qualquer entrega, inclusive pelo atalho `assemble_only`.
- `core/fine_audit.py` — **Auditoria fina clip-a-clip** (Regra 30): compara 2–3 frames de CADA sub-clip renderizado com o material designado (imagem do clip ou frames do vídeo da cena) e com a blacklist visual; fail-closed, gera `artifacts/fine_audit_report.json` + folha dos piores clips.
- `core/image_assignment.py` — Atribuição determinística de imagens (Regra 27): uma base por cena, cota global `MAX_SCENE_REUSE`, nunca em cenas vizinhas, casamento por tema/palavras e bloqueio da blacklist.
- `core/pacing_planner.py` — Ritmo por fala com **slow-motion de imagem parada** (Regra 28): mesma imagem base, Ken Burns suave e dissolve `SLOWMO_XFADE_SECONDS`; proibido flipbook de quadros curtos.
- `core/cta_video_overlay.py` — **CTA em vídeo** (Regra 25 revisada): `like-sem-som.mp4` no meio e `like-com-som.mp4` nos últimos 10s, chroma key `colorkey=0x00FF00:0.28:0.12`, 35% da largura no terço inferior, fade 0,2s e áudio do sino a -13 dB. O overlay `.mov` antigo está vetado.

## Auditoria de áudio — os ouvidos do aplicativo

**Earshot é os ouvidos do Videomaker v2.** Toda auditoria, validação ou julgamento de áudio (voz, SFX, mix, sincronia, loudness, cortes, ruído, naturalidade) DEVE ser feito com `bin/earshot.exe` (`measure`, `critique`, `timeline`, `sheet`, `compare`, `ab`). Não use outros aplicativos como árbitro de áudio — `ffmpeg`/`ffprobe` servem apenas para conversão e metadados brutos.

```powershell
$env:PATH = "E:\videos\videomaker_v2\bin;" + $env:PATH
earshot critique <video_ou_audio> --json
earshot measure <wav> --json
```

O resultado deve ser citado com números (LUFS, dBTP, onsets/s, sync, veredito). Ver Regra 22 do `CONTRATO_MOTOR_V2.md`.

## Porta de entrega obrigatória (visual)

Nenhum vídeo é entregue sem passar por `core/delivery_audit.py`, acionado dentro de `run_final_audit` tanto no `pipeline_v2.py` quanto no atalho `work/assemble_only.py`. Se reprovar, o MP4 é movido para `output/_rejected/`:

```powershell
python core/delivery_audit.py primeiro-dia-de-praia-v7
python core/delivery_audit.py --build-index   # regera o pool aprovado (v5 + v6)
python work/build_v7.py                        # roteiro narrado + vozes locais + pacing + imagens
```

Evidência: `artifacts/delivery_audit_report.json` + `artifacts/fine_audit_report.json` + folhas de contato em `work/delivery_audit/` e `work/fine_audit/`.

O que a porta reprova hoje (todas as regras são bloqueantes):

| Regra | Reprova quando |
| --- | --- |
| 27 | imagem fora do pool aprovado/na blacklist, mesma imagem em cenas vizinhas ou em mais de `MAX_SCENE_REUSE` cenas, tema forte divergente (concha/creme/gaivota/balde) |
| 28 | slow-motion com imagens diferentes na cena, quadro < 0,60s, dissolve < 0,35s, variações com sim < 0,90 |
| 29 | menos de 55% de cenas narradas ou > 2 cenas seguidas só de personagens |
| 30 | qualquer sub-clip cujo frame não corresponda ao material designado, ou que se pareça com material vetado |
| 25 | plano de CTA ausente, overlay do meio fora de 35–65% da duração, overlay final a mais de 10s do fim, ou voz do CTA final não silenciada |

A despedida canônica fica em `assets/reference/goodbye/despedida_subscribe.mp4` (sem áudio). O CTA usa os arquivos em `assets/reference/overlays/` (cópia local dos `.mp4` baixados; nunca versionados). Ver `core/cta_video_overlay.py` e o teste `python -m unittest tests.test_pipeline_v2 -k cta_video_overlay`.

## Exemplos de Uso

```powershell
# 1) Escanear e auditar todos os vídeos existentes em E:\videos
python E:\videos\videomaker_v2\pipeline_v2.py --batch-scan E:\videos

# 2) Importar e refazer um vídeo legado no motor v2 (reaproveitando o que prestar)
python E:\videos\videomaker_v2\pipeline_v2.py --legacy-dir E:\videos\e-se-os-cachorros-pudessem-falar-por-um-dia --burn-captions

# 3) Gerar apenas o pacote de Avatar da Luna (base + 4 vídeos via Flow Veo)
python E:\videos\videomaker_v2\pipeline_v2.py --build-avatar luna --stage avatar-only

# 4) Aprender e conectar contas Google Flow passo a passo (50 creditos/dia por conta)
python E:\videos\videomaker_v2\pipeline_v2.py --learn-flow-accounts
python E:\videos\videomaker_v2\pipeline_v2.py --flow-accounts-status

# 5) Rodar todos os testes automatizados
python E:\videos\videomaker_v2\tests\test_pipeline_v2.py
```

## Ferramentas catalogadas nesta revisão (Regras 25–30)

| Ferramenta | O que faz |
| --- | --- |
| `python work/build_v7.py --stage all` | Roteiro narrado, vozes locais, pacing slow-motion e imagens curadas do pool. |
| `python work/finalize_v7.py` | Fecha o episódio: pacing → imagens → montagem com auditoria → folhas de contato. |
| `python work/resume_v7_tts.py` | Retoma TTS interrompido, refazendo só o que falta e insistindo na voz local travada. |
| `python work/reaudit_v7.py` | Reexecuta a auditoria final sem re-renderizar (após corrigir metadado). |
| `python work/assemble_only.py <slug>` | Montagem 16:9 com a mesma porta de entrega obrigatória do pipeline. |
| `python work/check_xfade_duration.py` | Prova que o dissolve não encurta a timeline (não atrasa a narração). |
| `python work/audit_fino_sheets.py <slug>` | Folhas de contato: 1 frame por cena com a fala correspondente. |
| `python work/flow_video_contact.py` | Catálogo visual de todos os vídeos já gerados no Flow. |
| `python -m unittest tests.test_pipeline_v2 -k cta_video_overlay` | Teste do CTA em vídeo (chroma key, tempo e silêncio da voz). |
| `python -m unittest tests.test_pipeline_v2 -k image_assignment` | Teste anti-repetição/blacklist de imagens. |
| `python -m unittest tests.test_pipeline_v2 -k slowmo` | Teste do slow-motion sem estrobo. |
| `python -m unittest tests.test_pipeline_v2 -k narration` | Teste da narração dominante. |
| `python work/publish_v7.py` | Publica no YouTube PT-BR só se a auditoria aprovou (todo público). |
| `python work/upload_thumb_v7.py` | Envia a thumbnail viral do episódio já publicado. |
| `python work/relatorio_aproveitamento_v7.py` | Inventário: gerados × usados, com descrição dos descartados. |
