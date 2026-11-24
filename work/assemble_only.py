# -*- coding: utf-8 -*-
"""Monta o video 16:9 direto dos artifacts ja prontos (Regra 26: pipeline redondo).

Nao toca no Flow, nao re-sintetiza, NAO PULA A AUDITORIA: chama o mesmo
run_final_audit obrigatorio do pipeline_v2 (Regras 9 e 13). Se reprovar, o MP4
e movido para output/_rejected/ e o comando termina com exit=2.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import CPU_WORKERS, TARGET_VEO_VIDEOS  # noqa: E402
from core.self_audit import run_final_audit  # noqa: E402
from core.video_assembler import assemble_video  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v6"
    proj = ROOT / "projects" / slug
    artifacts = proj / "artifacts"
    pacing = json.loads((artifacts / "pacing_plan_v2.json").read_text(encoding="utf-8"))
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
        # Regra 28: dissolve suave OBRIGATORIO (o atalho antigo usava corte seco).
        no_xfade=False,
    )
    print(f"[assemble-only] MP4 gerado ({out.stat().st_size / 1e6:.1f} MB). Auditando...", flush=True)

    # Auditoria final obrigatoria — a mesma do pipeline_v2 (Regra 13).
    script_path = artifacts / "script_v2.json"
    timings_path = artifacts / "tts_timings_v2.json"
    script_data = json.loads(script_path.read_text(encoding="utf-8")) if script_path.exists() else {"scenes": []}
    timings = json.loads(timings_path.read_text(encoding="utf-8")) if timings_path.exists() else []
    audit = run_final_audit(
        proj_dir=proj,
        script_data=script_data,
        tts_timings=timings,
        visual_clips=pacing,
        images_dir=images_dir,
        out_16_9=out,
        out_short=None,
        thumbs_dir=output_dir / "thumbs",
        vision_check=False,
        min_veo_videos=int(TARGET_VEO_VIDEOS),
    )
    print(f"[assemble-only] AUDITORIA: APPROVED={audit['approved']} | Issues={audit['issues_count']}", flush=True)
    if not audit["approved"]:
        for it in audit["issues"][:30]:
            print("  [AUDIT-FAIL]", it, flush=True)
        rejected = output_dir / "_rejected"
        rejected.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(rejected / out.name))
        print(f"[assemble-only] MP4 REPROVADO movido para {rejected / out.name}", flush=True)
        return 2

    print(f"[assemble-only] PRONTO (aprovado): {out} ({out.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
