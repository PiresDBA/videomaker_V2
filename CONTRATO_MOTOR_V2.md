# CONTRATO DO MOTOR VIDEOMAKER V2 (PORTÁTIL E AUTOCONTIDO)

Este documento define a arquitetura, a estrutura de pastas autocontida e as **10 Regras Imutáveis** do motor **Videomaker v2** (`Frida & Luna`), garantindo portabilidade total entre máquinas e zero regressões por agentes ou edições manuais.

---

## 1. Estrutura Autocontida (Portável ao Copiar a Pasta Inteira)

Ao copiar `videomaker_v2/` para outro computador Windows, toda a infraestrutura operacional acompanha a pasta (mantendo credenciais e mídias fora do Git via `.gitignore`):

```text
videomaker_v2/
├── config.py                         # Hardware (CPU/NVENC), Cânone Visual, Casting TTS, Caminhos Relativos
├── pipeline_v2.py                    # Orquestrador único totalmente parametrizado via CLI
├── conectar_contas_flow.bat          # Lançador 1-clique do aprendizado de contas Google Flow
├── flow_accounts.example.json        # Template limpo das 5 contas (sem dados pessoais)
├── CONTRATO_MOTOR_V2.md              # Este contrato operacional e arquitetural
├── AGENTS.md                         # Regras obrigatórias de SFX, continuidade e publicação para agentes IA
├── bin/                              # (local/gitignore) ffmpeg.exe, ffprobe.exe, earshot.exe
├── .credentials/                     # (local/gitignore) client_secret*.json e youtube_token*.json
├── .chrome-flow-accounts/            # (local/gitignore) perfis dedicados acc_1..acc_5
├── .githooks/pre-commit              # Hook automático que bloqueia commits fora do contrato ou com segredos
├── scripts/
│   └── verify_contract_guard.py      # Validador automático das regras imutáveis
├── core/
│   ├── script_engine.py              # Roteiro viral 3 atos, gancho imediato, emoção e personagens secundários
│   ├── voice_studio.py               # Gemini 3.8 Flash TTS + normalização fonética PT + Whisper QA (CUDA/CPU)
│   ├── pacing_planner.py             # Divisão estrita <= 5s por sub-clip e alternância de Ken Burns
│   ├── media_studio.py               # Prompts travados na Bíblia Visual, anti-colagem e 3 thumbnails A/B/C
│   ├── flow_continuity.py            # Google Flow CDP direto (Nano Banana 2.1 0-cred + Veo 3.1 Lite 8s)
│   ├── flow_accounts.py              # Pool de 5 contas + failover automático + clone Frida/Luna/Secundários
│   ├── audio_fx.py                   # SFX semântico (Earshot + Freesound normalizado -6dBFS), BGM e Critique
│   ├── avatar_studio.py              # Dual-Avatar Frida & Luna PiP alinhado, cantos vazios e crossfade 9 frames
│   ├── motion_shorts.py              # Pack 3 Shorts 9:16 Split 70/30 infantil alegre + sincronia labial estrita
│   ├── video_assembler.py            # Render paralelo CPU/GPU, overlays dinâmicos (zzz/hearts/etc.) e -14 LUFS
│   ├── legacy_auditor.py             # Auditoria em lote e migração de vídeos/projetos legados para o motor v2
│   ├── self_audit.py                 # Auto-auditoria final obrigatória antes da entrega/publicação
│   └── youtube_publisher.py          # Publicador PT-BR todo público (MadeForKids=False) + thumb viral + SRT
├── vendor/
│   ├── env_keys.py                   # Rotação multi-chave Google/Freesound lida do .env local
│   ├── gerenciador_efeitos_sonoros.py# Única porta de entrada SFX (Earshot local/CLI + Freesound CC0)
│   ├── chrome_cdp_daemon.py          # Lançador Chrome visível em portas CDP dedicadas
│   ├── earshot-sfx/                  # (local/gitignore) pacote forge bank local
│   ├── soundcraft/                   # (local/gitignore) SoundCraft CLI local
│   └── remotion-composer/            # Código Remotion autocontido (sem node_modules no Git)
└── tests/
    └── test_pipeline_v2.py           # Bateria de testes unitários e ponta-a-ponta
```

---

## 2. As 10 Regras Imutáveis do Contrato

1. **100% Autocontido e Portátil:** O motor nunca depende de projetos externos para funcionar. Caminhos priorizam diretórios internos (`bin/`, `.credentials/`, `.chrome-flow-accounts/`, `assets/`, `vendor/`).
2. **Cânone Visual Criança / Pré-Adolescente 3D Disney-Pixar (`config.py` & `flow_continuity.py`):** Frida e Luna possuem idade visual padrão de **até 1 ano no máximo** (equivalente a **criança de 5–10 anos** em animação 3D estilizada, fiel aos avatares oficiais). É estritamente proibido gerar cães adultos/velhos ou fotorrealistas; a forma recém-nascida só pode aparecer em flashbacks explícitos (`--character-age-mode baby`).
3. **Continuidade Obrigatória de Personagens Secundários (`script_engine.py` & `flow_accounts.py`):** Qualquer personagem recorrente adicional (ex.: gato Pingo) deve constar em `"secondary_characters"` no roteiro, ter seu retrato criado no Flow (`0 créditos`) e cadastrado na aba `Personagens` via `ensure_story_characters_created`, sendo anexado em toda cena onde atuar.
4. **Google Flow com Continuidade e Failover de 5 Contas:** Imagens via `Nano Banana 2.1 · 16:9 · x1` (`0 créditos`), vídeos de 8s via `Veo 3.1 - Lite · Elementos · 16:9 · x1` (`10 créditos`), com alternância automática entre contas (`acc_1..acc_5`) e modo de aprendizado guiado (`--learn-flow-accounts`).
5. **Ritmo Visual (`<= 5.0s`) + Overlays Contextuais Dinâmicos:** Todo sub-clip estático respeita `MAX_IMAGE_SECONDS <= 5.0` e recebe animação contextual automática via `infer_scene_overlay_style` + `apply_contextual_particle_overlay` (`zzz`, `hearts`, `steam`, `fire`, `bees`, `birds`, `fireflies`, `sparkles`, `leaves`).
6. **Dual-Avatar PiP Inteligente:** Frida e Luna posicionadas nos cantos mais vazios da cena (`detect_emptiest_corners`), com boca sincronizada ao RMS da fala e crossfade suave.
7. **Sonoplastia Audível, Normalizada (`-6 dBFS`) e Atenuada (`<= 0.35`):** Todos os efeitos passam por `obter_efeito_sonoro`, são normalizados para pico consistente (`_normalize_sfx_to_wav`), limitados a `volume <= 0.35` na mixagem e masterizados junto à BGM com sidechain ducking em `-14 LUFS`.
8. **REGRA DE OURO — Voz Emocional Gemini TTS (PROIBIDO Edge TTS) + QA Whisper + Fonética PT:** É estritamente proibido usar Edge TTS (sem emoção) em vídeos, Shorts ou testes integrados. Todas as vozes usam exclusivamente **Gemini TTS emocional** — Narração dinâmica (`Kore`), Frida (`Sulafat`) e Luna (`Leda`) — com normalização fonética antes do TTS e validação Whisper (CUDA/CPU).
9. **Pack de 3 Shorts 9:16 Split-Screen 70% / 30% Infantil + Sincronia Labial Estrita + Cortes Limpos (`core/motion_shorts.py`):**
   - Todo episódio gera 3 Shorts verticais (`01_hook`, `02_storybook`, `03_final`) com **70% topo (`1080×1344`) para o filme** e **30% base (`1080×576`) para palco infantil colorido** (fontes arredondadas PIL, CTA para o vídeo completo e avatares grandes).
   - **Reprodutor Contínuo 30fps (`_SmoothAvatarPlayer`):** Avatares no Short rodam sequencialmente a 30fps com crossfade de 9 frames e posição/tamanho fixos (proibido teleporte de frames ou quique/trepidação).
   - **Sincronia Labial Estrita (`resolve_split_avatar_states`):** Frida só mexe a boca quando `speaker == "frida"`, Luna só quando `speaker == "luna"`, e quando o narrador ou personagem secundário fala **ambas permanecem de boca fechada (`reposo`)**.
   - **Fronteiras Limpas e Proteção Anti-Outro (`_snap_window_to_scenes` / `outro_guard`):** Nenhum Short pode terminar cortando fala no meio da frase; o Short 03 foca no clímax do Ato 3 e **não** captura a despedida/CTA final do vídeo longo.
10. **Direção de PiP Contido (16:9), Respiro Cômico e Fidelidade Visual (`plano_montagem_direcao_v2.json`):** No vídeo 16:9, o PiP permanece discreto nos cantos superiores (`TL`/`TR`), **oculto** em closes da própria personagem falando (evita duplicação visual) e **ligado pontualmente** apenas para reações paralelas/alertas sem cobrir rostos ou ações-chave; piadas e viradas recebem pausas de respiro (`0.5s–1.1s`), brinquedos citados (ex.: patinho de borracha) são obrigatoriamente objetos inanimados e partículas seguem estritamente a função narrativa.
11. **Publicação YouTube PT-BR Para Todo Público (`selfDeclaredMadeForKids = False`) + Auto-Auditoria Final + Segurança Git:** Nenhum vídeo pode ser publicado com `selfDeclaredMadeForKids: True`. A publicação PT gera thumbnail viral `1280×720`, título viral, descrição completa (`>= 150 palavras`) com pergunta para comentários e legenda `.srt` em `pt-BR`. Nenhuma entrega passa sem `run_final_audit` retornar `approved=True` (`issues_count=0`). Hooks `.githooks/pre-commit` e `scripts/verify_contract_guard.py` impedem commits fora do contrato ou com segredos.

---

## 3. Guia Completo de Parâmetros (Uso por Linha de Comando)

### Criar e renderizar um vídeo novo do zero
```powershell
python pipeline_v2.py --prompt "Frida e Luna encontram um mapa secreto no quintal" --slug mapa-secreto --min-words 450 --max-words 550 --target-minutes 3.5 --max-clip-seconds 5.0 --overlay-style auto --sfx-volume 0.35 --bgm-volume 0.22 --target-lufs -14
```

### Transformar/refazer um vídeo legado (ou diretório inteiro) para o padrão v2
```powershell
python pipeline_v2.py --legacy-dir "E:\videos\a-caminha-nova-que-ninguem-quer-usar" --force
python pipeline_v2.py --batch-scan "E:\videos"
```

### Gerar Short personalizado, controlar avatares ou velocidade de hardware
```powershell
python pipeline_v2.py --slug meu-episodio --avatar-mode duo --short-seconds 35 --cpu-workers 8 --disable-nvenc
```

### Publicar no canal YouTube Português (Todo Público + Thumb Viral + Legenda)
```powershell
python pipeline_v2.py --slug meu-episodio --stage publish --publish-pt --publish-privacy public --thumb-hook "ELAS FALARAM?!" --thumb-badge "VOCÊ NÃO VAI ACREDITAR!"
```

### Conectar contas Google Flow no Modo de Aprendizado
```powershell
python pipeline_v2.py --learn-flow-accounts
python pipeline_v2.py --flow-accounts-status
```

### Verificar integridade e proteções do motor (Hooks & Guard)
```powershell
python scripts/verify_contract_guard.py
python tests/test_pipeline_v2.py
```
