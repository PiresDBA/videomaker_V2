# Auditoria final — primeiro-dia-de-praia-2 (16:9)

Data: 2026-11-23. Autoridade: Earshot (Regra 22) + ffmpeg/ffprobe para metadados.

## Arquivo
`projects/primeiro-dia-de-praia-2/output/primeiro-dia-de-praia-2_16x9.mp4`
- Duração: **186.688 s** (3:07) — antes estava 34 s (bug do xfade, corrigido)
- Tamanho: 136.8 MB
- 171 sub-clips, 5 vídeos Veo reaproveitados, rajadas + imagens da colheita

## Áudio (Earshot critique --fast, 7 perfis de referência)
- **Veredito: close | Score 0.818 | 16/21 in-range | 0 críticos | 1 major**
- Referência v5 aprovada: 0.867. Diferença de 0.049 devido a mais foleys cartoon (esperado em desenho infantil).
- Major: `hit_rate` 2.02/s (refs 0.10-1.66/s) — muitos hits salientes; seus foleys cartoon Pica-Pau/Tom&Jerry (Regra 16).
- Minors: band_sub/band_low/side_to_mid — mix com menos grave e quase mono; ajustes opcionais de masterização.
- **LUFS integrado: -14.0 | True peak: -1.9 dBTP | LRA 1.5 LU** (meta -14 LUFS / -1 dBTP atingida).

## Sonoplastia
- SFX stem: Boing 0.96 (AudioSet), eventos cartoon z+5.2, ambiência de mar ativada.
- Foleys cartoon até 3 por cena, colados nas pausas de fala (Regras 16/22).

## Notas
- Bug crítico corrigido nesta rodada: xfade com 50 frames de burst (0.12s) colapsava a timeline (8 frames→0.33s). Rajada agora usa cortes secos (flipbook); xfade só nas transições de cena. Ver `work/fix_burst_xfade.py`.
- `--skip-tts` e `reuse_clips` permitiram reaproveitar 30 falas e 171 clips (Regra 26).
- Veredito aceitável para entretenimento infantil: não bloqueia publicação.
