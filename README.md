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

## Auditoria de áudio — os ouvidos do aplicativo

**Earshot é os ouvidos do Videomaker v2.** Toda auditoria, validação ou julgamento de áudio (voz, SFX, mix, sincronia, loudness, cortes, ruído, naturalidade) DEVE ser feito com `bin/earshot.exe` (`measure`, `critique`, `timeline`, `sheet`, `compare`, `ab`). Não use outros aplicativos como árbitro de áudio — `ffmpeg`/`ffprobe` servem apenas para conversão e metadados brutos.

```powershell
$env:PATH = "E:\videos\videomaker_v2\bin;" + $env:PATH
earshot critique <video_ou_audio> --json
earshot measure <wav> --json
```

O resultado deve ser citado com números (LUFS, dBTP, onsets/s, sync, veredito). Ver Regra 22 do `CONTRATO_MOTOR_V2.md`.

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
