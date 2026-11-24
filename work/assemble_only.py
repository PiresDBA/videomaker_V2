# -*- coding: utf-8 -*-
"""Monta o video 16:9 direto dos artifacts ja prontos (Regra 26: pipeline redondo).

Usa quando TTS, imagens, rajadas e clips ja existem e so falta concatenar + audio + overlays.
Nao toca no Flow, nao re-sintetiza, nao re-audita.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import CPU_WORKERS  # noqa: E402
from core.video_assembler import assemble_video  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-2"
    proj = ROOT / "projects" / slug
    pacing = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
    images_dir = proj / "assets" / "images"
    work_dir = proj / "work"
    output_dir = proj / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    bgm = ROOT / "assets" / "music" / "primeiro-dia-de-praia_musica.wav"
    out = output_dir / f"{slug}_16x9.mp4"
    srt = output_dir / f"{slug}.srt"

    print(f"[assemble-only] {len(pacing)} clips | bgm={bgm.exists()} | -> {out}", flush=True)
    assemble_video(
        pacing,
        images_dir,
        work_dir,
        out,
        srt,
        bgm_wav=bgm if bgm.exists() else None,
        with_avatar=True,
        burn_captions=False,
        sfx_volume=0.35,
        bgm_volume=0.22,
        target_lufs=-14.0,
        cpu_workers=CPU_WORKERS,
        reuse_clips=True,
    )
    print(f"[assemble-only] PRONTO: {out} ({out.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
