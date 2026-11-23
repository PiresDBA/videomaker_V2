# Auditoria de Sonoplastia (Earshot) — Referência v5 e v6

Autoridade: `bin/earshot.exe` (Regra 22). Executado com `bin/` no PATH (ffmpeg). Data: 2026-11-23.

## Referência aprovada (v5)

Arquivo: `projects/primeiro-dia-de-praia-v5/work/narration_soundcraft.wav` (188,5 s) + `sfx_master.wav`.

### Mix final (earshot critique --fast)
- **Veredito:** `close` | **Score: 0,867** | 17/20 métricas in-range | 0 críticos, 1 major.
- **Major:** LUFS integrado ~-16,2 → earshot sugere subir +2,2 dB para -14 LUFS com limiter a -1 dBTP.
- **Minor:** side/mid -70 dB (quase mono) → usar música/ambiência estéreo e panear SFX com o movimento.
- **Minor:** bottom fino → adicionar camada sub (sub drop/kick) nos reveals.

### SFX stem (earshot describe)
- **AudioSet: Boing 0,96**, Ding 0,26 → sonoplastia cartoon confirmada.
- Tags: "glass ting", "plastic toy snapping", "mouth pop", "finger tapping on glass", "rubber stretch".
- Loudness range 11 LU, pico -16,4 dBFS, -28,5 LUFS, brightness 2,5 kHz, side/mid -12 dB.

### Eventos cartoon localizados (earshot find)
`cartoon boing, water splash bucket, cartoon fall tumble`:
- 0:07.92-0:08.53 (evento 0,61 s, **z +5,2 forte**)
- 0:22.58-0:22.84 (z +3,6), 1:16.29-1:16.54 (z +3,6)
- 1:42.10-1:42.35 (z +3,4), 2:18.46-2:18.71 (z +3,4)

## Motor de foleys cartoon (core/audio_fx.py)

Regra 16: até **3 foleys cartoon por cena**, colados na piada. Banco semanticamente mapeado:
- `boing` → cartoon boing; `giggle`/`risadinha` → cartoon giggle
- `fanfare` → cartoon fanfare; `whistle`/`apito` → slide whistle
- `crunch` → cartoon crunch bite; `splash` → cartoon splash
- `sneeze` → cartoon sneeze; `celesta`/`spark` → mallet/celesta; `glock`/`bloom` → mallet/glock
- Regras semânticas (Pica-Pau / Tom & Jerry / Snoopy) ligam o som ao verbo da narração.

## Conclusão
A sonoplastia infantil/cartoon já está presente e auditada: boing 0,96, eventos fortes, foleys colados na ação. Ajuste pendente para o mix final: garantir -14 LUFS / -1 dBTP (o `mix_audio_master` já usa `target_lufs=-14` nos renders v2/v6). Próxima auditoria: rodar `earshot critique` no MP4 final de cada episódio e citar os números antes de publicar.
