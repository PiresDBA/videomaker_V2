# -*- coding: utf-8 -*-
"""Preenche imagens faltantes do projeto a partir da colheita do Flow (sem gerar nada).

Para cada cena do pacing sem _p1 no disco: escolhe a melhor imagem tematica/praiana
da colheita e deriva as variantes _p2.._pN localmente (crop/zoom), evitando o Flow.
"""
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402
from core.burst_montage import derive_burst_frames  # noqa: E402

REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
ANALISE = REF / "analise_v2_all.json"


def main() -> None:
    proj = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "projects" / "primeiro-dia-de-praia-2"
    images_dir = proj / "assets" / "images"
    pacing = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
    needed: dict[str, list[str]] = defaultdict(list)
    for c in pacing:
        cid = c["clip_id"]
        if cid.endswith("_p1") or "_b_" in cid:
            continue
        scene = cid.split("_p")[0]
        needed[scene].append(cid)
    # inclui _p1 de todas as cenas (mesmo as que ja tem, para garantir)
    all_scenes = {c["clip_id"].split("_p")[0].split("_b")[0] for c in pacing}

    rows = json.loads(ANALISE.read_text(encoding="utf-8"))
    imgs = [r for r in rows if r.get("kind") == "image"]
    beach_kw = ("beach", "sand", "wave", "ocean", "seagull", "biscuit", "bucket", "sunscreen", "shore", "sea", "puppy", "dog")
    good = [
        r for r in imgs
        if r.get("class") in ("usado", "candidato", "duplicata_reencode")
        or any(k in str(r.get("aria", "")).lower() for k in beach_kw)
    ]
    by_scene: dict[str, list[Path]] = defaultdict(list)
    generic: list[Path] = []
    for r in good:
        p = Path(r["path"])
        if not p.exists():
            continue
        sc = str(r.get("scene", "")).split("_p")[0]
        if sc.startswith("sc_") and sc in all_scenes:
            by_scene[sc].append(p)
        else:
            generic.append(p)

    print(f"[fill] needed scenes: {len(needed)} | good imgs: {len(good)} | by_scene: {sum(len(v) for v in by_scene.values())} | generic: {len(generic)}", flush=True)

    created = 0
    for scene in sorted(all_scenes):
        base_p1 = images_dir / f"{scene}_p1.jpg"
        src = None
        if not base_p1.exists():
            # tenta imagem da propria cena, senao generica, senao qualquer _p1 existente
            pool = by_scene.get(scene) or generic
            if not pool:
                exist = sorted(images_dir.glob("*_p1.jpg"))
                pool = exist
            if pool:
                src = pool[0]
                shutil.copy2(src, base_p1)
                created += 1
        elif base_p1.exists():
            src = base_p1

        if not src:
            continue
        # Deriva as variantes pedidas (_p2.._pN) a partir do _p1, se faltam
        cids = needed.get(scene, [])
        variants = [c for c in cids if c not in ("",)]
        if variants:
            frames = derive_burst_frames(base_p1, images_dir, n=len(variants), base_name=scene + "_p")
            # derive_burst_frames nomeia base_p_01..; renomeia para os ids exatos do pacing
            for cid, fr in zip(sorted(variants), frames):
                dst = images_dir / f"{cid}.jpg"
                if not dst.exists():
                    shutil.copy2(fr, dst)
                    fr.unlink(missing_ok=True)
                created += 1

    print(f"[fill] criadas/derivadas: {created} imagens em {images_dir}", flush=True)
    total_needed = sum(len(v) for v in needed.values()) + len(all_scenes)
    have = len(list(images_dir.glob("*.jpg")))
    print(f"[fill] total imagens no projeto: {have} / ~{total_needed} pedidas pelo pacing", flush=True)


if __name__ == "__main__":
    main()
