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
├── .credentials/                     # (local/gitignore) client_secret*.json, youtube_token*.json, client_secret_tts.json, cloud_tts_token.json, chirp3_usage.json
├── .chrome-flow-accounts/            # (local/gitignore) perfis dedicados acc_1..acc_5
├── .githooks/pre-commit              # Hook automático que bloqueia commits fora do contrato ou com segredos
├── scripts/
│   └── verify_contract_guard.py      # Validador automático das regras imutáveis
├── core/
│   ├── script_engine.py              # Roteiro viral 3 atos, gancho imediato, emoção e personagens secundários
│   ├── voice_studio.py               # Gemini 3.8 Flash TTS + Google Cloud Chirp 3 HD (1M/mês OAuth2) + Whisper QA
│   ├── pacing_planner.py             # Divisão estrita <= 5s por sub-clip e alternância de Ken Burns
│   ├── media_studio.py               # Prompts travados na Bíblia Visual, anti-colagem, Veo 3.1 Lite e 3 thumbs A/B/C
│   ├── flow_continuity.py            # Google Flow CDP direto (Nano Banana 2.1 0-cred + Veo 3.1 Lite 8s)
│   ├── flow_accounts.py              # Pool de 5 contas + failover automático + clone Frida/Luna/Secundários
│   ├── audio_fx.py                   # SFX semântico (Earshot + Freesound normalizado -6dBFS), BGM e Critique
│   ├── avatar_studio.py              # Dual-Avatar Frida & Luna PiP alinhado, cantos vazios e crossfade 9 frames
│   ├── motion_shorts.py              # Pack 3 Shorts 9:16 Split 70/30 infantil alegre + sincronia labial estrita
│   ├── video_assembler.py            # Render paralelo CPU/GPU, overlays dinâmicos (zzz/hearts/etc.) e -14 LUFS
│   ├── scene_auditor.py              # Auditoria obrigatória cena-a-cena fail-closed (Narração x Imagem/Veo, @Personagens, Objetos e Vozes)
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

## 2. As 13 Regras Imutáveis do Contrato

1. **100% Autocontido e Portátil:** O motor nunca depende de projetos externos para funcionar. Caminhos priorizam diretórios internos (`bin/`, `.credentials/`, `.chrome-flow-accounts/`, `assets/`, `vendor/`).
2. **Cânone Visual Criança / Pré-Adolescente 3D Disney-Pixar (`config.py`, `script_engine.py` & `flow_continuity.py`):** Frida (obrigatoriamente **Buldogue Inglesa caramelo-dourada** com colar de pérolas; nunca Golden Retriever) e Luna (obrigatoriamente **Dachshund/Salsicha marrom-chocolate** com correntinhas douradas; nunca Cocker Spaniel) possuem idade visual padrão de **até 1 ano no máximo** (equivalente a **criança de 5–10 anos** em animação 3D estilizada). `validate_script_schema` reprova raças incorretas e `build_image_prompt` injeta a Bíblia Visual seletivamente pelos personagens da cena.
3. **Continuidade Obrigatória de Personagens Secundários (`script_engine.py` & `flow_accounts.py`):** Qualquer personagem recorrente adicional (ex.: chihuahua Pipoca, gato Pingo) deve constar em `"secondary_characters"` no roteiro, ter seu retrato criado no Flow (`0 créditos`, salvo por episódio em `projects/<slug>/assets/characters/`) e cadastrado na aba `Personagens` via `ensure_story_characters_created`, sendo anexado em toda cena (imagem ou Veo).
4. **Google Flow com Continuidade e Failover de 5 Contas:** Imagens via `Nano Banana 2.1 · 16:9 · x1` (`0 créditos`), vídeos de 8s via `Veo 3.1 - Lite · Elementos · 16:9 · x1` (`10 créditos`), com alternância automática entre contas (`acc_1..acc_5`) e modo de aprendizado guiado (`--learn-flow-accounts`).
5. **Ritmo Visual (`<= 5.0s`) + Overlays Contextuais Dinâmicos:** Todo sub-clip estático respeita `MAX_IMAGE_SECONDS <= 5.0` e recebe animação contextual automática via `infer_scene_overlay_style` + `apply_contextual_particle_overlay` (`zzz`, `hearts`, `steam`, `fire`, `bees`, `birds`, `fireflies`, `sparkles`, `leaves`).
6. **Dual-Avatar PiP Inteligente:** Frida e Luna posicionadas nos cantos mais vazios da cena (`detect_emptiest_corners`), com boca sincronizada ao RMS da fala e crossfade suave.
7. **Sonoplastia Audível, Normalizada (`-6 dBFS`) e Atenuada (`<= 0.35`):** Todos os efeitos passam por `obter_efeito_sonoro`, são normalizados para pico consistente (`_normalize_sfx_to_wav`), limitados a `volume <= 0.35` na mixagem e masterizados junto à BGM com sidechain ducking em `-14 LUFS`.
8. **REGRA DE OURO — Vozes Travadas (`Kore` / `Sulafat` / `Leda`) no Gemini TTS ou Chirp 3 HD (PROIBIDO Edge TTS e Troca de Voz) + QA Whisper + Fonética PT:** É estritamente proibido usar Edge TTS ou alternar a voz de um personagem durante retries de prosódia (`VOICE_LOCK_STRICT = True`). São permitidos apenas **Gemini TTS emocional** (`gemini_emotion`, priorizando `GOOGLE_TTS_API_KEY`) e **Google Cloud Chirp 3 HD** (`chirp3_hd`, vozes `pt-BR-Chirp3-HD-Kore`, `Sulafat` e `Leda` via OAuth 2.0 `--auth-chirp3` ou Conta de Serviço), com trava local gratuita de **`CHIRP3_MONTHLY_CHAR_LIMIT = 950_000`** (< 1 milhão grátis/mês) e proibição de chamar modelos Gemini pagos via Cloud TTS.
9. **REGRA DE OURO — Sincronia Narração × Imagem/Vídeo + Auditoria Cena-a-Cena Fail-Closed (`core/scene_auditor.py`) + 10 Vídeos Veo 3.1 Lite (8s) + Trava 1 Geração/Cena:** Toda cena deve exibir visual estritamente sintonizado com o que está sendo falado na narração. `core/scene_auditor.py` opera em modo *fail-closed* (`strict_vision=True`) dentro do `pipeline_v2.py` (e em modo standalone), audita e gera inline até **10 vídeos de 8s no Veo 3.1 Lite** (`--veo-videos 10`, ~80s animados) com trava rígida `MAX_VEO_GENERATIONS_PER_SCENE = 1` em ledger persistente (`artifacts/veo_generation_ledger.json`), espera obrigatória por gerações em andamento no Flow (`_wait_for_inflight_flow_generation`) e arquivamento de vídeos rejeitados em `videos/_archive/` (proibido apagar vídeo pago ou entrar em loop). Quando já existirem múltiplos vídeos válidos para uma mesma cena, `core/video_assembler.py` (`_resolve_scene_videos`) edita todos em sequência dentro da cena. Extrai stills `_p2`/`_p3` dos vídeos aprovados e bloqueia a montagem se qualquer cena falhar (`min_veo_videos` exigido em `self_audit.py`).
10. **REGRA DE OURO — Continuidade de Personagens (`@nome`) e Objetos-Chave como Personagens (`story_props`):** Apenas Frida e Luna são personagens fixos globais. Todo personagem secundário recorrente (`secondary_characters`) e todo **objeto-chave recorrente da história (`story_props`, ex.: `@Caminha_Real`)** é cadastrado na aba `Personagens` do Google Flow via `ensure_story_characters_created` (com retrato isolado por episódio em `projects/<slug>/assets/characters/`), citado via `@Nome` nos prompts das cenas em que aparece (`_scene_matching_props`) e auditado contra o retrato-âncora no `scene_auditor.py`, zerando automaticamente ao iniciar um vídeo novo.
11. **Pack de 3 Shorts 9:16 Split-Screen 70% / 30% Infantil + Sincronia Labial Estrita + Cortes Limpos (`core/motion_shorts.py`):**
    - Todo episódio gera 3 Shorts verticais (`01_hook`, `02_storybook`, `03_final`) com **70% topo (`1080×1344`) para o filme** e **30% base (`1080×576`) para palco infantil colorido** (fontes arredondadas PIL, CTA para o vídeo completo e avatares grandes).
    - **Reprodutor Contínuo 30fps (`_SmoothAvatarPlayer`):** Avatares no Short rodam sequencialmente a 30fps com crossfade de 9 frames e posição/tamanho fixos (proibido teleporte de frames ou quique/trepidação).
    - **Sincronia Labial Estrita (`resolve_split_avatar_states`):** Frida só mexe a boca quando `speaker == "frida"`, Luna só quando `speaker == "luna"`, e quando o narrador ou personagem secundário fala **ambas permanecem de boca fechada (`reposo`)**.
    - **Fronteiras Limpas e Proteção Anti-Outro (`_snap_window_to_scenes` / `outro_guard`):** Nenhum Short pode terminar cortando fala no meio da frase; o Short 03 foca no clímax do Ato 3 e **não** captura a despedida/CTA final do vídeo longo.
12. **Direção de PiP Contido (16:9), Respiro Cômico e Fidelidade Visual (`plano_montagem_direcao_v2.json`):** No vídeo 16:9, o PiP permanece discreto nos cantos superiores (`TL`/`TR`), **oculto** em closes da própria personagem falando (evita duplicação visual) e **ligado pontualmente** apenas para reações paralelas/alertas sem cobrir rostos ou ações-chave; piadas e viradas recebem pausas de respiro (`0.5s–1.1s`), brinquedos citados (ex.: patinho de borracha) são obrigatoriamente objetos inanimados e partículas seguem estritamente a função narrativa.
13. **Publicação YouTube PT-BR Para Todo Público (`selfDeclaredMadeForKids = False`) + Auto-Auditoria Final + Segurança Git:** Nenhum vídeo pode ser publicado com `selfDeclaredMadeForKids: True`. A publicação PT gera thumbnail viral `1280×720`, título viral, descrição completa (`>= 150 palavras`) com pergunta para comentários e legenda `.srt` em `pt-BR`. Nenhuma entrega passa sem `run_final_audit` retornar `approved=True` (`issues_count=0`). Hooks `.githooks/pre-commit` e `scripts/verify_contract_guard.py` impedem commits fora do contrato ou com segredos.

---

## 3. Guia Completo de Parâmetros (Uso por Linha de Comando)

### Criar e renderizar um vídeo novo do zero (Gemini TTS ou Chirp 3 HD 1M/mês)
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --prompt "Frida e Luna encontram um mapa secreto no quintal" --slug mapa-secreto --tts-provider chirp3_hd --veo-videos 10 --min-words 450 --max-words 550 --target-minutes 3.5 --max-clip-seconds 5.0 --overlay-style auto --sfx-volume 0.35 --bgm-volume 0.22 --target-lufs -14
```

### Autenticar Google Cloud Chirp 3 HD (OAuth 2.0 gratuito 1M chars/mês)
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --auth-chirp3
```

### Transformar/refazer um vídeo legado (ou rodar Auditoria Cena-a-Cena)
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --legacy-dir "E:\videos\o-campeonato-de-caes-mais-maluco-do-mundo" --tts-provider chirp3_hd --force
C:\Docling\venv\Scripts\python.exe core/scene_auditor.py --project-dir "E:\videos\videomaker_v2\projects\MEU_SLUG" --auto-fix
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --batch-scan "E:\videos"
```

### Gerar Short personalizado, controlar avatares ou velocidade de hardware
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --slug meu-episodio --avatar-mode duo --short-seconds 35 --cpu-workers 8 --disable-nvenc
```

### Publicar no canal YouTube Português (Todo Público + Thumb Viral + Legenda)
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --slug meu-episodio --stage publish --publish-pt --publish-privacy public --thumb-hook "ELAS FALARAM?!" --thumb-badge "VOCÊ NÃO VAI ACREDITAR!"
```

### Conectar contas Google Flow no Modo de Aprendizado
```powershell
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --learn-flow-accounts
C:\Docling\venv\Scripts\python.exe pipeline_v2.py --flow-accounts-status
```

### Verificar integridade e proteções do motor (Hooks & Guard)
```powershell
C:\Docling\venv\Scripts\python.exe scripts/verify_contract_guard.py
C:\Docling\venv\Scripts\python.exe tests/test_pipeline_v2.py
```

---

## 4. Grafo de Conhecimento & Cérebro (`graphify`) — Economia de Contexto

Para evitar varreduras manuais extensas e reduzir drasticamente o consumo de contexto dos agentes:

1. **Leitura obrigatória ao entrar no repositório:**
   - Consultar primeiro `graphify-out/GRAPH_REPORT.md` (visão geral, *god nodes* e comunidades) e `graphify-out/wiki/index.md` (cérebro navegável por módulo), ou usar `graphify query "<pergunta>"` / `graphify explain "<nó>"`.
   - Caso `graphify-out/` ainda não exista localmente, gerar com `graphify update E:\videos\videomaker_v2`.
2. **Atualização obrigatória após cada commit:**
   - Sempre que alterações de código forem finalizadas e commitadas (`git commit`), rodar imediatamente:
     ```powershell
     graphify update E:\videos\videomaker_v2
     ```
   - Isso mantém `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.html` e `graphify-out/wiki/` sincronizados com o código atual sem custo de LLM para arquivos de código.

---

## 5. Lições Aprendidas & Travas Anti-Regressão (Blindagem Flow, Veo 3.1 Lite e Vision QA)

Todas as lições abaixo possuem **travas estáticas automatizadas** em `scripts/verify_contract_guard.py` e testes em `tests/test_pipeline_v2.py`:

1. **Trava Anti-Loop de Créditos Veo (`MAX_VEO_GENERATIONS_PER_SCENE = 1` + Ledger Persistente + Arquivamento `_archive/`):**
   - **Causa raiz histórica:** Vídeos reprovados na Vision QA eram apagados (`v_mp4.unlink()`), não havia ledger em disco nem espera por gerações em andamento (`N%`) no Google Flow, fazendo o pipeline gerar até 5 vezes o mesmo vídeo na mesma cena.
   - **Trava definitiva:** `generate_single_veo_video` consulta `artifacts/veo_generation_ledger.json` + arquivos em `assets/videos/_archive/{sid}_*.mp4` e `{sid}_v*.mp4` antes de disparar o Flow; `scene_auditor.py` arquiva vídeos reprovados em `_archive/` (proibido apagar `.mp4` pago) e `_wait_for_inflight_flow_generation` aguarda qualquer geração em andamento antes de submeter ou colher mídia.
2. **Trava de Montagem Multi-Vídeo por Cena (`_resolve_scene_videos` + `render_multi_video_montage_subclip`):**
   - **Causa raiz histórica:** Quando uma cena tinha múltiplos vídeos válidos gerados/resgatados (`sc_01.mp4`, `sc_01_v2..v5.mp4`), o montador usava apenas `sc_01.mp4` e as variantes `_v2..v5` roubavam vagas das 10 cenas distintas em `veo_scene_ids`.
   - **Trava definitiva:** `video_assembler.py` concatena todos os vídeos válidos da cena distribuindo o tempo da cena entre eles, e `pipeline_v2.py` normaliza `re.sub(r"_(?:v|p)\d+$", "", ep.stem)` para garantir `>= 10` cenas distintas animadas sem descartar vídeos extras.
3. **Trava Anti-Contaminação de Referências em `'Envios'` e Limite de 3 Elementos no Veo (`flow_continuity.py`):**
   - **Causa raiz histórica:** `attach_reference_from_plus` possuía um fallback cego que selecionava a 1ª mídia de `Envios` quando o arquivo buscado não era encontrado (anexando retratos antigos como `Caminha_Real`), e `generate_flow_video` tentava anexar 4+ chips quando o Veo 3.1 Lite aceita no máximo 3 Elementos (descartando o keyframe ou a Frida).
   - **Trava definitiva:** Proibido fallback cego do 1º item em `attach_reference_from_plus`; `generate_flow_image` aguarda `saw_progress` + `before_arias` (nunca baixa tile antigo); `generate_flow_video` aplica `max_elements = 3` priorizando o keyframe da cena (`Envios`) seguido de até 2 personagens principais (`Personagens`).
4. **Trava de Navegação `/character` e Seletor `button[role="radio"]` no Painel do Flow (`flow_continuity.py`):**
   - **Causa raiz histórica:** `ensure_direct_mode` buscava a pílula `Nano Banana 2.1` antes de sair da rota `/character`, clicando no dropdown de modelo da tela de personagem em vez do painel `x1`; e `configure_flow_mode` clicava no wrapper `<mat-button-toggle>` externo, falhando ao alternar de `Imagem` para `Vídeo`.
   - **Trava definitiva:** `ensure_direct_mode` sai de `/character` ou `/edit/` antes de buscar a pílula inferior; `configure_flow_mode` fecha overlays pendentes (`_dismiss_open_overlays`), prioriza `button[role="radio"]:has-text(...)` e valida a troca efetiva de modo antes de confirmar `Veo 3.1 - Lite` (`10 créditos`) ou `Nano Banana 2.1` (`0 créditos`). Erros pré-disparo de UI são marcados como `pre_dispatch_error` no ledger sem queimar a cota da cena.
5. **Trava de Escopo por Cena na Vision QA e Retratos Isolados de Objetos (`scene_auditor.py` & `flow_continuity.py`):**
   - **Causa raiz histórica:** `secondary_characters` do episódio inteiro (ex.: `Pipoca`) eram cobrados em cenas onde não atuavam (`sc_01`); cenas de corrida com `"vários cães"` eram reprovadas pela regra anti-cães extras; e prompts de `story_props` (`object_only`) recebiam sufixo de filhotes (`enforce_youthful_puppy_prompt`).
   - **Trava definitiva:** `_scene_matching_secondary_chars` e `_scene_matching_props` filtram estritamente pelos participantes da cena; `crowd_allowed` libera figurantes caninos quando o roteiro pede corrida/competidores; `enforce_youthful_puppy_prompt` isenta prompts `cartoon prop object` / `object_only`; e vídeos Veo para episódios 16:9 são validados em proporção horizontal (`largura > altura`).
6. **Trava Watchdog Multi-Processo com Fila FIFO, Heartbeat e Aviso de Término (`FlowStageWatchdog` em `core/flow_accounts.py` & `pipeline_v2.py`):**
   - **Causa raiz histórica:** Dois processos `pipeline_v2.py` executados em paralelo na mesma máquina conectavam-se simultaneamente à mesma aba Chrome CDP (`:18804`), fazendo um episódio colher o vídeo Veo que estava sendo gerado pelo outro episódio.
   - **Trava definitiva:** `FlowStageWatchdog` mantém fila FIFO persistente em `.chrome-flow-accounts/flow_watchdog_queue.json`, thread de heartbeat contínuo (`4s`), detecção automática de processos `pipeline_v2.py` pré-existentes ou encerrados (`_is_pid_alive`) e grava aviso explícito de término (`status: "finished_and_notified"`) assim que a etapa do Google Flow conclui, liberando imediatamente o próximo episódio da fila.

