# -*- coding: utf-8 -*-
"""Prepara projeto v6: copia projeto 2 e injeta TODOS os videos de tema (v5 + novos do Flow).

Regra: so entram videos classificados como 'usado' ou 'candidato' pela analise de tema
(primeiro-dia-de-praia); descarta 'fora_tema' (parque, outros episodios). Dedupe por SHA.
Distribui multiplos videos por cena para montagem rica (render_multi_video_montage_subclip).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SRC = ROOT / "projects" / "primeiro-dia-de-praia-2"
DST = ROOT / "projects" / "primeiro-dia-de-praia-v6"
V5 = ROOT / "projects" / "primeiro-dia-de-praia-v5" / "assets" / "videos"
REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
ANALISE = REF / "analise_v2_all.json"


def sha(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _concat_goodbyes(parts: list[Path], out: Path) -> None:
    """Junta despedidas com xfade suave de 0.5s (settb=AVTB evita EINVAL de timebase)."""
    ff = ROOT / "bin" / "ffmpeg.exe"
    xf = 0.5
    cmd = [str(ff), "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", str(p)]
    filters = [f"[{i}:v]fps=30,settb=AVTB,format=yuv420p,setpts=PTS-STARTPTS[s{i}]" for i in range(len(parts))]

    def _dur(p: Path) -> float:
        fp = ROOT / "bin" / "ffprobe.exe"
        r = subprocess.run([str(fp), "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except Exception:
            return 7.93

    durs = [_dur(p) for p in parts]
    prev = "[s0]"
    cum = durs[0]
    for i in range(1, len(parts)):
        nxt = "[vout]" if i == len(parts) - 1 else f"[x{i}]"
        filters.append(f"{prev}[s{i}]xfade=transition=fade:duration={xf}:offset={cum - xf:.3f}{nxt}")
        prev = nxt
        cum = cum + durs[i] - xf
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True)


def main() -> None:
    # 1. Reanalisa a colheita nova (gera analise_v2_all.json atualizado)
    print("[v6] Reanalisando colheita...", flush=True)
    subprocess.run(
        [sys.executable, str(ROOT / "work" / "analyze_v2.py")],
        cwd=str(ROOT), check=True,
    )

    rows = json.loads(ANALISE.read_text(encoding="utf-8"))
    theme = [
        r for r in rows
        if r.get("kind") == "video" and r.get("class") in ("usado", "candidato")
        and Path(r["path"]).exists()
    ]
    print(f"[v6] Videos de tema na colheita: {len(theme)}", flush=True)

    # 2. Copia projeto 2 -> v6
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    for sub in ("artifacts", "assets", "output", "work"):
        shutil.copytree(SRC / sub, DST / sub, dirs_exist_ok=True)

    vdir = DST / "assets" / "videos"
    vdir.mkdir(parents=True, exist_ok=True)

    # 3. Video ja presentes no projeto 2 (novos da rodada) + v5
    #    Mapeamento explicito por aria -> cena do ROTEIRO NOVO (30 cenas), para distribuir
    #    os 15 videos unicos sem colidir todos em sc_01..sc_05.
    P2_MAP = {"sc_01": "sc_01", "sc_02": "sc_02", "sc_03": "sc_03", "sc_04": "sc_04", "sc_05": "sc_05"}
    V5_MAP = {
        "sc_01": "sc_06", "sc_02": "sc_15", "sc_03": "sc_11", "sc_04": "sc_04_v2",
        "sc_05": "sc_21", "sc_06": "sc_23", "sc_07": "sc_24", "sc_08": "sc_26",
        "sc_09": "sc_05_v2", "sc_10": "sc_05_v3",
    }
    seen: set[str] = set()
    by_scene: dict[str, list[Path]] = {}
    for p in sorted(vdir.glob("*.mp4")):
        h = sha(p)
        if h in seen:
            continue
        seen.add(h)
        base = p.stem.split("_p")[0].split("_v")[0]
        base = P2_MAP.get(base, base)  # p2: sc_01..05 -> mesma cena do roteiro novo
        by_scene.setdefault(base, []).append(p)
    for p in sorted(V5.glob("*.mp4")):
        h = sha(p)
        if h in seen:
            continue
        seen.add(h)
        by_scene.setdefault(V5_MAP.get(p.stem, p.stem), []).append(p)

    # 4. Injeta videos de tema da colheita (novos do Flow), dedupe
    for r in theme:
        p = Path(r["path"])
        h = r.get("sha") or sha(p)
        if h in seen:
            continue
        seen.add(h)
        scene = str(r.get("scene") or "sc_99").split("_p")[0].split("_v")[0]
        by_scene.setdefault(scene, []).append(p)

    # 5. VIDEO DE DESPEDIDA COMPOSTO (sc_30): junta 3 despedidas boas com crossfade.
    #    ORDEM: (1) confetti acc_3, (2) living-room com confete acc_1,
    #    (3) ULTIMA = "perfeitinha" com botao YouTube + SUBSCRIBE (acc_3 vid_10).
    #    REPROVADO: acc_1 vid_12 "Two dogs waving at camera" (5 patas / patinha fantasma).
    vids_dir = REF / "flow_all"
    goodbye_parts = [
        vids_dir / "acc_3" / "videos" / "acc_3_225a8b1e_vid_11_ae84f4b6a0.mp4",  # confetti
        vids_dir / "acc_1" / "videos" / "acc_1_2700c141_vid_08_f901f98df7.mp4",  # living room confete
        vids_dir / "acc_3" / "videos" / "acc_3_225a8b1e_vid_10_f3c7928cd5.mp4",  # SUBSCRIBE (ultima)
    ]
    available = [p for p in goodbye_parts if p.exists()]
    if len(available) >= 2:
        merged = DST / "assets" / "videos" / "sc_30.mp4"
        _concat_goodbyes(available, merged)
        if merged.exists():
            seen.add(sha(merged))
            by_scene.setdefault("sc_30", []).append(merged)
            print(f"[v6] Despedida composta ({len(available)} videos) -> sc_30", flush=True)
    elif available:
        by_scene.setdefault("sc_30", []).append(available[-1])
        print("[v6] Despedida unica -> sc_30", flush=True)
    else:
        print("[v6] AVISO: nenhum video de despedida encontrado.", flush=True)

    # 6. Materializa com nomes sequenciais por cena: sc_XX.mp4, sc_XX_v2.mp4 ...
    total = 0
    for scene, paths in by_scene.items():
        for i, p in enumerate(paths):
            name = scene if i == 0 else f"{scene}_v{i + 1}"
            dst = vdir / f"{name}.mp4"
            if dst.exists() and sha(dst) == sha(p):
                continue
            shutil.copy2(p, dst)
            total += 1

    print(f"[v6] Prepare done: {total} videos, {len(by_scene)} cenas, {len(seen)} unicos", flush=True)
    print(f"[v6] Projeto: {DST}", flush=True)
    for scene in sorted(by_scene):
        print(f"  {scene}: {len(by_scene[scene])} video(s)", flush=True)


if __name__ == "__main__":
    main()
