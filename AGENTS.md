# AGENTS.md — Regras Operacionais do Motor Videomaker v2

Leia [CONTRATO_MOTOR_V2.md](CONTRATO_MOTOR_V2.md) antes de qualquer alteração neste repositório.

## Invariantes Protegidos por Hook (`scripts/verify_contract_guard.py`)
1. **SFX e Áudio:** Sempre usar `vendor/gerenciador_efeitos_sonoros.py` (`obter_efeito_sonoro`), com IDs completos no Earshot (`familia/variante`) e termos curtos em inglês (2–3 palavras) no Freesound; manter volume SFX `<= 0.35` na mixagem e normalização via `_normalize_sfx_to_wav`.
2. **Portabilidade Total:** Nunca criar dependências rígidas de pastas fora de `videomaker_v2/` (`bin/`, `.credentials/`, `assets/`, `vendor/`).
3. **Cânone Visual Criança/Pré-Adolescente:** Manter `1 year old max` em `config.py` (`VISUAL_BIBLE`), `core/flow_continuity.py` e `core/flow_accounts.py`. Todo personagem secundário recorrente precisa de `secondary_characters` + `ensure_story_characters_created`.
4. **Ritmo e Overlays Estáticos:** Nunca exceder `MAX_IMAGE_SECONDS = 5.0` sem divisão e manter `infer_scene_overlay_style` + `apply_contextual_particle_overlay` ativos sobre imagens estáticas.
5. **REGRA DE OURO — Voz Emocional Gemini TTS (PROIBIDO Edge TTS):** Nunca usar Edge TTS em vídeos, Shorts ou testes integrados. Sempre usar `provider="gemini_emotion"` (`Kore`, `Sulafat`, `Leda`) com direção emocional.
6. **Shorts 9:16 Split 70/30 + Fluidez 30fps + Cortes Limpos:** Manter `SHORT_SPLIT_TOP_RATIO = 0.70`, `class _SmoothAvatarPlayer`, `resolve_split_avatar_states` e `_snap_window_to_scenes` com `outro_guard` em `core/motion_shorts.py` (avatares contínuos a 30fps sem trepidação, Frida só fala quando `speaker == "frida"`, Luna só fala quando `speaker == "luna"`, e nenhum Short corta falas ou captura o encerramento/CTA final).
7. **YouTube Todo Público:** `core/youtube_publisher.py` DEVE manter `"selfDeclaredMadeForKids": False` (proibido alterar para `True`).
8. **Segurança e Hooks:** Nunca commitar `.env`, `.credentials/`, `*secret*.json`, `*token*.json`, `flow_accounts*.json`, `.chrome-*`, `projects/`, ou mídias `.mp4`/`.wav`/`.jpg`. Antes de qualquer commit, garanta que `python scripts/verify_contract_guard.py` retorne `0`.
