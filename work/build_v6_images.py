# -*- coding: utf-8 -*-
"""Reconstrói as imagens do v6 APENAS com o pool aprovado (v5 + v6 tematico).

Regra 26 (pipeline redondo) sem o erro da Regra 9: nenhuma imagem vem da colheita
velha. Cada cena recebe imagens DISTINCTAS (rajada de verdade, sem micro-zoom),
escolhidas por similaridade tematica com a narração.

Uso: python work/build_v6_images.py [slug]
"""
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.delivery_audit import INDEX_PATH, build_approved_index, sha256  # noqa: E402

STOP = set("a as o os e em de da do das dos que com um uma para no na por se ao".split())
THEMES = {
    "agua": "onda mar agua molh afund flutu banho glub surf respingo barco nadar praia ondas".split(),
    "areia": "areia cocegas pepada cavar buraco lambe terra salgada castelo poeira maos".split(),
    "creme": "protetor creme escorrega patina branco fantasma sabao tubo escorregadio".split(),
    "concha": "concha cantar sereia brilhante som cantiga".split(),
    "gaivota": "gaivota biscoito sombra aviao ladra voa penas passarinho pira".split(),
    "balde": "balde bola vitoria pedacinho tesouro".split(),
    "final": "final amigos despedida inscreva melhor aventura divertida obrigado ate".split(),
}


def tokens(text: str) -> set[str]:
    out = set()
    for w in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split():
        if len(w) > 2 and w not in STOP:
            out.add(w)
    return out


def theme_of(text: str) -> str:
    t = tokens(text)
    best, best_n = "geral", 0
    for name, words in THEMES.items():
        n = len(t & set(words))
        if n > best_n:
            best, best_n = name, n
    return best


def v5_scene_texts() -> dict[str, str]:
    p = ROOT / "projects" / "primeiro-dia-de-praia-v5" / "artifacts" / "script_v2.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data) if isinstance(data, dict) else data
    return {s["scene_id"]: str(s.get("text", "")) for s in scenes}


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v6"
    proj = ROOT / "projects" / slug
    pacing_path = proj / "artifacts" / "pacing_plan_v2.json"
    images_dir = proj / "assets" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not INDEX_PATH.exists():
        build_approved_index()
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    sources = [Path(r["path"]) for r in index["images"] if Path(r.get("path", "")).exists()]
    # Estagia FORA da pasta de destino: o pool inclui imagens do proprio projeto v6,
    # que serao apagadas na limpeza abaixo (foi isso que gerou o FileNotFoundError).
    staging = ROOT / "work" / "approved_pool"
    staging.mkdir(parents=True, exist_ok=True)
    pool = []
    for src in sources:
        dst = staging / src.name
        shutil.copy2(src, dst)
        pool.append(dst)
    print(f"[v6-images] pool aprovado estagiado: {len(pool)} imagens", flush=True)

    v5texts = v5_scene_texts()
    # tema de cada imagem do pool (pelo texto da cena v5 de origem)
    img_theme: dict[str, str] = {}
    for p in pool:
        sid = p.stem.split("_p")[0]
        img_theme[str(p)] = theme_of(v5texts.get(sid, "")) if sid in v5texts else "geral"

    pacing = json.loads(pacing_path.read_text(encoding="utf-8"))
    by_scene: dict[str, list[dict]] = defaultdict(list)
    for c in pacing:
        by_scene[c["scene_id"]].append(c)

    # limpa imagens antigas do projeto (todas serao reescritas do pool aprovado)
    for old in images_dir.glob("*.jpg"):
        old.unlink()

    created = 0
    used_by_scene: dict[str, set[str]] = {}
    for sid in sorted(by_scene):
        clips = by_scene[sid]
        sample = " ".join(str(c.get("text", "")) + " " + str(c.get("visual_action", "")) for c in clips[:2])
        want = theme_of(sample)
        st = tokens(sample)

        def score(p: Path) -> float:
            s = 0.0
            if img_theme[str(p)] == want:
                s += 3.0
            pt = tokens(p.stem)
            s += len(st & pt) * 0.15
            return s

        ranked = sorted(pool, key=lambda p: (-score(p), p.name))
        n = len(clips)
        chosen: list[str] = []
        for p in ranked:
            if len(chosen) >= n:
                break
            # evita repetir a mesma imagem dentro da cena (rajada de verdade)
            if p.name in chosen:
                continue
            chosen.append(p.name)
        # se nao houver imagens suficientes, completa rotacionando
        i = 0
        while len(chosen) < n:
            cand = ranked[i % len(ranked)].name
            if cand not in chosen:
                chosen.append(cand)
            i += 1

        used_by_scene[sid] = set(chosen)
        for clip, name in zip(clips, chosen):
            src = next(p for p in pool if p.name == name)
            shutil.copy2(src, images_dir / f"{clip['clip_id']}.jpg")
            created += 1
        print(f"  {sid}: {n} imagens | tema={want} | distinctas={len(set(chosen))}", flush=True)

    # Rajada = cortes secos (sem xfade curto que colapsa a timeline no ffmpeg).
    fixed = 0
    for c in pacing:
        if ("_b_" in c["clip_id"] or c.get("burst_from")) and float(c.get("xfade_duration") or 0) > 0:
            c["xfade_duration"] = 0.0
            fixed += 1
    pacing_path.write_text(json.dumps(pacing, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[v6-images] {created} jpgs criados em {images_dir}", flush=True)
    print(f"[v6-images] {fixed} clips de burst com xfade zerado (cortes secos)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
