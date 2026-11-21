---
name: videomaker-v2-montage-and-qa
description: >-
  Runbook for rendering, inspecting, and validating Videomaker v2 16:9 episodes and
  9:16 Shorts using montage plans, FFmpeg frame inspection, and contract tests.
  Use when rendering episodes, applying plano_montagem_direcao_v2.json, or
  verifying Shorts/16:9 visual quality before publishing or committing.
---

# Videomaker v2 — Montagem, Inspeção Visual e QA

## 1. Ambiente e Binários
- Python: `C:\Docling\venv\Scripts\python.exe`
- FFmpeg: `E:\videos\videomaker_v2\bin\ffmpeg.exe`

## 2. Re-render 16:9 com Plano de Montagem
1. Validar invariantes antes de rodar:
   `& "C:\Docling\venv\Scripts\python.exe" E:\videos\videomaker_v2\scripts\verify_contract_guard.py`
2. Executar o pipeline preservando assets já gerados:
   `& "C:\Docling\venv\Scripts\python.exe" E:\videos\videomaker_v2\pipeline_v2.py --slug <slug> --skip-images --skip-short --skip-thumbs --skip-whisper-qa --skip-prosody-gate`
   (O arquivo `projects/<slug>/artifacts/plano_montagem_direcao_v2.json` é carregado automaticamente, ou via `--montage-plan <caminho>`.)

## 3. Inspeção Visual Obrigatória (Nunca pular)
- **Para 16:9:** Extrair frames com `ffmpeg.exe -ss <t> -i <video_16x9.mp4> -frames:v 1 <frame.jpg>` cobrindo:
  1. Cena com PiP OFF em close (sem duplicação visual);
  2. Cena com PiP ON pontual em `TL`/`TR` (`250x250`, sem cobrir ação/objetos);
  3. Cenas com objetos específicos da narração;
  4. Cenas finais/objetos-chave (ex.: zíper livre do PiP).
  Inspecionar cada `.jpg` com `read_file`.
- **Para Shorts 9:16:** Verificar com `read_file` no `.mp4` ou frames que o avatar está fluido a 30fps sem trepidação, respeita `speaker == "frida"` / `"luna"` e encerra em fronteira limpa de cena (`outro_guard`) sem cortar falas.

## 4. Verificação Final Pré-Commit
1. `& "C:\Docling\venv\Scripts\python.exe" E:\videos\videomaker_v2\scripts\verify_contract_guard.py`
2. `& "C:\Docling\venv\Scripts\python.exe" E:\videos\videomaker_v2\tests\test_pipeline_v2.py`
