# -*- coding: utf-8 -*-
"""Porta de entrega obrigatoria (Regras 9 e 13 do CONTRATO_MOTOR_V2.md).

Nenhum video e entregue sem passar por aqui. A auditoria e LOCAL e deterministica:
nao depende de Vision API, entao nao pode falhar por cota/rede e nao pode ser
burlada por atalho de montagem.

Verificacoes:
  1. WHITELIST: toda imagem usada no projeto tem SHA256 igual a uma imagem aprovada
     (v5 + v6), catalogada em assets/reference/primeiro-dia-de-praia/approved_images.json.
     -> Pega na origem a contaminacao por colheita velha (astronauta, galinha, parque).
  2. FRAME x CENA: extrai 1 frame por cena do MP4 final e exige similaridade com
     alguma imagem/videos designados para aquela cena (fail-closed).
  3. RAJADA: fractions consecutivos de burst nao podem ser quasi identicos
     (0.98 = micro-zoom de uma unica foto => "tremendo dos lados").
  4. DESPEDIDA/CTA: ultimo frame deve bater com a referencia aprovada de CTA.
  5. CONTATO: salva folhas de contato para conferencia humana.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
ROOT = ROOT_DIR
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from config import FFMPEG_EXE, GOODBYE_VIDEO_PATH  # noqa: E402

REF_DIR = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
INDEX_PATH = REF_DIR / "approved_images.json"
CTA_REF_PATH = REF_DIR / "cta_final_ref.jpg"
CTA_REF_ALT = REF_DIR / "cta_final_v5_ref.jpg"  # despedida alternativa aprovada (v5)
APPROVED_SOURCES = (
    ROOT / "projects" / "primeiro-dia-de-praia-v5" / "assets" / "images",
    ROOT / "projects" / "primeiro-dia-de-praia-v6" / "assets" / "images",
)
SIM_MIN = 0.68            # abaixo disso: frame nao corresponde a cena
BURST_MAX_SIM = 0.96      # referencia de similaridade (testes de assinatura)
BURST_MIN_FRAME = 0.60    # slow-motion: cada quadro precisa durar >= 0,6s
BURST_MIN_XFADE = 0.35    # dissolve minimo entre quadros do slow-motion
BURST_MIN_BASE_SIM = 0.90 # variacoes precisam ser quase a mesma foto
CTA_MIN_SIM = 0.62        # abaixo disso: despedida/CTA ausente
# Personagem recorrente (ex.: Guga, a gaivota) reaparece legitimamente em varias
# cenas; imagem de fundo nao pode. Valor alto para nao bloquear continuidade de
# personagem, mantendo o cheque de cenas vizinhas para pegar repeticao tosca.
MAX_SCENE_REUSE = 6
BLACKLIST_PATH = REF_DIR / "blacklist.json"

_STOP = set("a as o os e em de da do das dos que com um uma para no na por se ao".split())
THEMES = {
    "agua": "onda mar agua molh afund flutu banho glub surf respingo barco nadar ondas".split(),
    "areia": "areia cocegas pepada cavar buraco lambe terra salgada castelo poeira maos torres".split(),
    "creme": "protetor creme escorrega patina branco fantasma sabao tubo escorregadio surfista".split(),
    "concha": "concha cantar sereia brilhante som cantiga tesouro".split(),
    "gaivota": "gaivota biscoito sombra aviao ladra voa penas passarinho pira guga lanche".split(),
    "balde": "balde bola vitoria pedacinho".split(),
    "descanso": "cansa descansar cochilo guarda-sol sonhar dormir barriguinha fome".split(),
    "final": "final amigos despedida inscreva melhor aventura divertida obrigado ate irma".split(),
}
# Temas com objeto concreto: se a narracao fala de concha/creme/gaivota/balde,
# a imagem precisa ser daquele objeto. Praia/areia/agua/descanso sao genericos
# entre si e nao geram falso positivo.
STRONG_THEMES = {"concha", "creme", "gaivota", "balde"}


def tokens(text: str) -> set[str]:
    out = set()
    for w in "".join(ch if ch.isalnum() else " " for ch in str(text).lower()).split():
        if len(w) > 2 and w not in _STOP:
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


def load_blacklist(path: Path | None = None) -> set[str]:
    target = Path(path) if path else BLACKLIST_PATH
    if not target.exists():
        return set()
    data = json.loads(target.read_text(encoding="utf-8"))
    return set(data.get("sha256", []))


def load_blacklist_videos(path: Path | None = None) -> set[str]:
    target = Path(path) if path else BLACKLIST_PATH
    if not target.exists():
        return set()
    data = json.loads(target.read_text(encoding="utf-8"))
    return set(data.get("video_sha256", []))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _scene_text_map(slug: str) -> dict[str, str]:
    p = ROOT / "projects" / slug / "artifacts" / "script_v2.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data) if isinstance(data, dict) else data
    out = {}
    for s in scenes:
        out[s["scene_id"]] = f"{s.get('text', '')} {s.get('visual_action', '')} {s.get('location', '')}"
    return out


def build_approved_index() -> dict[str, Any]:
    """ gere o indice de imagens aprovadas (v5 + v6), com tema por imagem. """
    texts = {"primeiro-dia-de-praia-v5": _scene_text_map("primeiro-dia-de-praia-v5"),
             "primeiro-dia-de-praia-v6": _scene_text_map("primeiro-dia-de-praia-v6")}
    overrides_path = REF_DIR / "theme_overrides.json"
    overrides = {}
    if overrides_path.exists():
        overrides = json.loads(overrides_path.read_text(encoding="utf-8")).get("themes", {})
    images: list[dict[str, str]] = []
    seen: set[str] = set()
    for base in APPROVED_SOURCES:
        if not base.exists():
            continue
        slug = base.parent.parent.name
        for p in sorted(base.glob("*.jpg")):
            h = sha256(p)
            if h in seen:
                continue
            seen.add(h)
            sid = p.stem.split("_p")[0].split("_b")[0]
            txt = texts.get(slug, {}).get(sid, "")
            images.append({
                "sha256": h,
                "name": p.name,
                "source": slug,
                "source_scene": sid,
                "path": str(p),
                "theme": overrides.get(p.name, theme_of(txt)),
                "keywords": sorted(tokens(txt)),
            })
    payload = {"version": 1, "source": "v5 aprovado + v6 tematico", "images": images}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_approved_index() -> set[str]:
    if not INDEX_PATH.exists():
        build_approved_index()
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {r["sha256"] for r in data.get("images", [])}


def signature(path: Path, size: int = 32) -> tuple[list[float], list[float]]:
    """Assinatura robusta a crop/Ken Burns: pixels normalizados + histograma HSV."""
    im = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    px = list(im.getdata())
    flat: list[float] = []
    hist = [0.0] * 25
    for r, g, b in px:
        flat += [r / 255.0, g / 255.0, b / 255.0]
        mx, mn = max(r, g, b), min(r, g, b)
        d = mx - mn
        if d == 0:
            h = 0
        elif mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        hb = min(11, int(h * 2))
        sb = min(1, int(mx / 128))
        vb = min(1, int(mx / 128))
        hist[hb * 2 + sb + vb] += 1
    n = float(len(px))
    return flat, [v / n for v in hist]


def sim(a: tuple[list[float], list[float]], b: tuple[list[float], list[float]]) -> float:
    fa, ha = a
    fb, hb = b
    ma = sum(fa) / len(fa)
    mb = sum(fb) / len(fb)
    num = sum((x - ma) * (y - mb) for x, y in zip(fa, fb))
    da = math.sqrt(sum((x - ma) ** 2 for x in fa))
    db = math.sqrt(sum((y - mb) ** 2 for y in fb))
    corr = num / (da * db) if da and db else 0.0
    hc = sum(math.sqrt(x * y) for x, y in zip(ha, hb))
    return 0.5 * max(0.0, corr) + 0.5 * hc


def _extract(video: Path, t: float, out: Path) -> Path | None:
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", str(out)],
        capture_output=True,
    )
    return out if r.returncode == 0 and out.exists() else None


def _dur(video: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run(
        [str(ffprobe), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def check_whitelist(images_dir: Path, approved: set[str]) -> list[str]:
    """Retorna os nomes de arquivos de imagem que NAO estao no pool aprovado."""
    if not images_dir.exists():
        return []
    return [p.name for p in sorted(images_dir.glob("*.jpg")) if sha256(p) not in approved]


def clip_has_video(clip: dict[str, Any], images_dir: Path) -> bool:
    """Clip sera renderizado por VIDEO (cena tem Veo ou clipe tem mp4 proprio).
    Nesse caso o .jpg do clip e so suporte de overlay — nao entra na whitelist."""
    videos_dir = images_dir.parent / "videos"
    sid = clip.get("scene_id", "")
    if videos_dir.exists():
        if (videos_dir / f"{sid}.mp4").exists():
            return True
        if list(videos_dir.glob(f"{sid}_v*.mp4")):
            return True
    if (images_dir / f"{clip.get('clip_id', '')}.mp4").exists():
        return True
    return False


def audit_delivery(
    proj_dir: Path,
    out_16_9: Path,
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    strict: bool = True,
) -> dict[str, Any]:
    """ Audita o MP4 final. Retorna {'approved','issues','scenes',...} e grava relatorio. """
    issues: list[str] = []
    details: list[dict[str, Any]] = []
    work = proj_dir / "work" / "delivery_audit"
    work.mkdir(parents=True, exist_ok=True)

    if not out_16_9.exists() or out_16_9.stat().st_size < 1000:
        return {"approved": False, "issues": [f"video final ausente: {out_16_9}"],
                "scenes": [], "report_path": ""}

    # 1. WHITELIST deterministica (apenas clips renderizados por IMAGEM) + BLACKLIST
    approved = load_approved_index()
    # Reuso de midia (media_assignment.json): o manifesto e a fonte oficial da cena —
    # nao se exige o pool aprovado antigo (colheita de outro episodio).
    reuse_mode = (proj_dir / "artifacts" / "media_assignment.json").exists()
    blocked = load_blacklist()
    index_by_sha = {}
    if INDEX_PATH.exists():
        index_by_sha = {r["sha256"]: r for r in json.loads(INDEX_PATH.read_text(encoding="utf-8"))["images"]}

    scenes: dict[str, list[dict[str, Any]]] = {}
    for c in visual_clips:
        scenes.setdefault(c["scene_id"], []).append(c)

    bad: list[str] = []
    blocked_hits: list[str] = []
    reuse: dict[str, set[str]] = {}
    theme_mismatch: list[str] = []
    scene_sha: dict[str, str] = {}
    for sid, clips in scenes.items():
        scene_theme = theme_of(" ".join(str(c.get("text", "")) + " " + str(c.get("visual_action", "")) for c in clips[:2]))
        img_themes: set[str] = set()
        for c in clips:
            if clip_has_video(c, images_dir):
                continue
            jp = images_dir / f"{c['clip_id']}.jpg"
            if not jp.exists():
                continue
            h = sha256(jp)
            if h in blocked:
                blocked_hits.append(jp.name)
            elif not reuse_mode and h not in approved:
                bad.append(jp.name)
            else:
                reuse.setdefault(h, set()).add(sid)
                scene_sha.setdefault(sid, h)
                t = index_by_sha.get(h, {}).get("theme")
                if t:
                    img_themes.add(t)
        if (scene_theme in STRONG_THEMES and img_themes
                and scene_theme not in img_themes and "geral" not in img_themes):
            theme_mismatch.append(f"{sid} (nar={scene_theme}, img={sorted(img_themes)})")
    if blocked_hits:
        issues.append(f"blacklist: {len(blocked_hits)} imagem(ns) PROIBIDA(S) em uso (ex.: {', '.join(blocked_hits[:4])})")
    if bad:
        issues.append(
            f"whitelist: {len(bad)} imagem(ns) fora do pool aprovado "
            f"(ex.: {', '.join(bad[:4])}) — colheita velha contaminada"
        )
    for h, sids in reuse.items():
        if len(sids) > MAX_SCENE_REUSE:
            nm = index_by_sha.get(h, {}).get("name", h[:10])
            issues.append(f"repeticao: imagem {nm} usada em {len(sids)} cenas ({', '.join(sorted(sids)[:5])}...) > {MAX_SCENE_REUSE}")
    if theme_mismatch:
        issues.append(f"tema x narracao: {len(theme_mismatch)} cena(s) com imagem de outro tema: {'; '.join(theme_mismatch[:6])}")
    # mesma imagem em cenas vizinhas tambem parece repeticao (mesmo dentro da cota)
    def _scene_num(s: str) -> int:
        try:
            return int(s.split("_")[-1])
        except ValueError:
            return 0

    ordered_sids = sorted(scene_sha, key=_scene_num)
    for a, b in zip(ordered_sids, ordered_sids[1:]):
        if _scene_num(b) == _scene_num(a) + 1 and scene_sha[a] == scene_sha[b]:
            nm = index_by_sha.get(scene_sha[a], {}).get("name", scene_sha[a][:10])
            issues.append(f"repeticao: mesma imagem ({nm}) nas cenas vizinhas {a} e {b}")

    videos_dir = images_dir.parent / "videos"
    blocked_videos = load_blacklist_videos()
    if videos_dir.exists():
        bad_vids = [v.name for v in sorted(videos_dir.glob("*.mp4")) if sha256(v) in blocked_videos]
        if bad_vids:
            issues.append(
                f"blacklist: {len(bad_vids)} video(s) PROIBIDO(S) (defeito de patas): "
                f"{', '.join(bad_vids[:4])}"
            )
    scene_frames: dict[str, Path] = {}

    # 2. FRAME x CENA (fail-closed)
    for sid in sorted(scenes):
        clips = scenes[sid]
        p1 = next((c for c in clips if c["clip_id"].endswith("_p1")), clips[0])
        t = (float(p1.get("start") or 0) + float(p1.get("end") or 0)) / 2
        frame = _extract(out_16_9, t, work / f"{sid}.png")
        if frame is None:
            issues.append(f"cine {sid}: nao foi possivel extrair frame em t={t:.2f}s")
            continue
        scene_frames[sid] = frame

        # referencias da cena: imagens designadas + videos da cena
        refs: list[Path] = [images_dir / f"{c['clip_id']}.jpg" for c in clips]
        refs = [p for p in refs if p.exists()]
        vids = sorted(videos_dir.glob(f"{sid}*.mp4")) if videos_dir.exists() else []
        for v in vids[:3]:
            rv = _extract(v, min(2.0, max(0.3, _dur(v) * 0.3)), work / f"ref_{sid}_{v.stem}.png")
            if rv:
                refs.append(rv)
        if not refs:
            issues.append(f"cena {sid}: sem imagens/videos de referencia")
            continue
        fsig = signature(frame)
        best = max((sim(fsig, signature(r)), r.name) for r in refs)
        details.append({"scene": sid, "t": round(t, 2), "best_sim": round(best[0], 3),
                        "ref": best[1], "n_refs": len(refs), "has_video": bool(vids)})
        if best[0] < SIM_MIN:
            issues.append(
                f"cena {sid}: frame renderizado nao bate com a cena "
                f"(sim={best[0]:.3f} < {SIM_MIN}; ref={best[1]})"
            )

    # 3. SLOW-MOTION da cena parada (especificacao do usuario):
    #    a MESMA imagem base, quadros >= 0,6s e dissolve suave entre eles.
    #    Reprova (a) flipbook de imagens DIFERENTES (metralhadora) e
    #    (b) quadros de 0,1-0,2s (trepidacao/estrobo). Vale para TODA cena
    #    parada (nao so as marcadas como burst).
    for sid, clips in scenes.items():
        if any(clip_has_video(c, images_dir) for c in clips):
            if len(clips) > 1:
                details.append({"scene": sid, "burst_source": "video", "checked": False})
            continue
        # Stop-motion (image_sequence): quadros progressivos DIFERENTES com dissolve
        # curto = efeito de movimento intencional, nao o flipbook bugado da Regra 28.
        if any(c.get("stop_motion") for c in clips):
            details.append({"scene": sid, "burst_source": "stop_motion", "checked": False})
            continue
        parts = clips
        if len(parts) < 2:
            continue

        jpgs = [images_dir / f"{c['clip_id']}.jpg" for c in parts]
        hashes = {sha256(p) for p in jpgs if p.exists()}
        frame_s = min(float(c.get("duration") or 0.0) for c in parts)
        xfade_s = min(float(c.get("xfade_duration") or 0.0) for c in parts)
        base_sim = 0.0
        if len(jpgs) >= 2 and all(p.exists() for p in jpgs):
            base_sim = sim(signature(jpgs[0]), signature(jpgs[-1]))
        details.append({"scene": sid, "burst_frame_s": round(frame_s, 3),
                        "burst_images": len(hashes), "burst_base_sim": round(base_sim, 3),
                        "burst_xfade_s": round(xfade_s, 3)})
        if len(hashes) > 1:
            issues.append(
                f"cena {sid}: slow-motion com {len(hashes)} imagens DIFERENTES — "
                f"tem que ser a mesma imagem base (variacoes sutis de enquadramento)"
            )
        if frame_s < BURST_MIN_FRAME:
            issues.append(
                f"cena {sid}: quadros de {frame_s:.2f}s < {BURST_MIN_FRAME}s — estrobo/trepidacao; "
                f"o olho humano precisa de >= 0,6s por quadro"
            )
        if xfade_s < BURST_MIN_XFADE:
            issues.append(
                f"cena {sid}: dissolve de {xfade_s:.2f}s < {BURST_MIN_XFADE}s entre quadros do slow-motion"
            )
        if hashes and base_sim and base_sim < BURST_MIN_BASE_SIM:
            issues.append(
                f"cena {sid}: variacoes do slow-motion muito diferentes "
                f"(sim={base_sim:.3f} < {BURST_MIN_BASE_SIM})"
            )

    # 4. DESPEDIDA / CTA
    total = _dur(out_16_9)
    final_frame = _extract(out_16_9, max(0.0, total - 0.5), work / "final.png")
    refs = [p for p in (CTA_REF_PATH, CTA_REF_ALT) if p.exists()]
    # Despedida canonica (Regra 25): o reference dinamico do novo video vale mais
    # que os JPGs das despedidas antigas — senao uma despedida nova e correta
    # seria reprovada por nao se parecer com a antiga.
    if GOODBYE_VIDEO_PATH.exists() and GOODBYE_VIDEO_PATH.stat().st_size > 1000:
        dyn = _extract(GOODBYE_VIDEO_PATH, max(0.0, _dur(GOODBYE_VIDEO_PATH) - 0.6),
                       work / "cta_canonical_ref.png")
        if dyn:
            refs = [dyn] + refs
    if final_frame and refs:
        fsig = signature(final_frame)
        fsim, fname = max((sim(fsig, signature(p)), p.name) for p in refs)
        details.append({"final_sim": round(fsim, 3), "final_ref": fname})
        if fsim < CTA_MIN_SIM:
            issues.append(
                f"despedida/CTA: ultimo frame nao bate com nenhuma despedida aprovada "
                f"(melhor sim={fsim:.3f} < {CTA_MIN_SIM})"
            )
    elif not refs:
        issues.append("referencias de CTA ausentes: " + str(CTA_REF_PATH))

    # 4a. CTA EM VIDEO (Regra 25 revisada): like-sem-som no meio e like-com-som no fim.
    cta_plan_path = proj_dir / "work" / "cta" / "cta_plan.json"
    if cta_plan_path.exists():
        cta = json.loads(cta_plan_path.read_text(encoding="utf-8"))
        evs = cta.get("events", [])
        mids = [e for e in evs if e.get("position") == "middle"]
        finals = [e for e in evs if e.get("position") == "final"]
        details.append({"cta_events": len(evs), "cta_mid": len(mids), "cta_final": len(finals)})
        if not mids:
            issues.append("CTA: falta o overlay like-sem-som no meio do video")
        if not finals:
            issues.append("CTA: falta o overlay like-com-som no final do video")
        for e in mids:
            ratio = float(e.get("timeline_start") or 0) / max(1.0, total)
            if not 0.35 <= ratio <= 0.65:
                issues.append(f"CTA: overlay do meio em {ratio:.0%} da duracao (alvo ~50%)")
        for e in finals:
            tail = total - float(e.get("timeline_start") or 0)
            if tail > 10.5:
                issues.append(f"CTA: overlay final começa {tail:.1f}s antes do fim (max 10s)")
        if not cta.get("audio_muted", False):
            issues.append(
                "CTA: audio do video final NAO foi silenciado — a voz do clipe briga com a narracao"
            )
        if abs(float(cta.get("similarity") or 0) - 0.28) > 0.02:
            issues.append("CTA: tolerancia do chroma key diferente de 0.28")
        for e in evs:
            t = float(e.get("timeline_start") or 0)
            f = _extract(out_16_9, t + min(1.0, float(e.get("duration") or 1.0) / 2),
                         work / f"cta_{e.get('position', 'x')}.png")
            if not f:
                issues.append(f"CTA: nao foi possivel extrair frame do overlay {e.get('position')}")
    else:
        issues.append("CTA: plano de overlays ausente (work/cta/cta_plan.json) — Regra 25")

    # 4b. AUDITORIA FINA clip-a-clip (3 frames por sub-clip) — pedido do usuario:
    #     "imagem por imagem, comparar com o que esta sendo falado". Pega clip velho
    #     reaproveitado, imagem trocada no meio da cena e material vetado.
    fine_rep: dict[str, Any] = {"approved": True, "clips_checked": 0, "issues": []}
    try:
        from core.fine_audit import audit_fine

        fine_rep = audit_fine(proj_dir, out_16_9, visual_clips, images_dir)
        issues.extend(f"fino: {e}" for e in fine_rep.get("issues", []))
    except Exception as exc:  # auditoria fina nunca pode ser silenciada
        issues.append(f"fino: falhou ao executar ({str(exc)[:140]})")

    # 5. folhas de contato (evidencia humana)
    ordered = [scene_frames[s] for s in sorted(scene_frames)]
    for page in range(0, len(ordered), 12):
        chunk = ordered[page:page + 12]
        cols, tw, th = 3, 400, 225
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), (18, 18, 22))
        for i, f in enumerate(chunk):
            im = Image.open(f).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        sheet.save(work / f"contato_{page // 12 + 1}.jpg", quality=85)

    report = {
        "approved": len(issues) == 0,
        "strict": strict,
        "issues_count": len(issues),
        "issues": issues,
        "whitelist_size": len(approved),
        "frames_checked": len(scene_frames),
        "fine_audit": fine_rep,
        "details": details,
        "contact_sheets": sorted(p.name for p in work.glob("contato_*.jpg")),
        "video": str(out_16_9),
    }
    report_path = proj_dir / "artifacts" / "delivery_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Porta de entrega obrigatoria (auditoria visual local).")
    ap.add_argument("slug", nargs="?", default="primeiro-dia-de-praia-v6")
    ap.add_argument("--build-index", action="store_true", help="regera indice de imagens aprovadas")
    args = ap.parse_args()
    if args.build_index:
        idx = build_approved_index()
        print(f"[delivery-audit] indice: {len(idx['images'])} imagens aprovadas -> {INDEX_PATH}")
        return 0
    root = ROOT
    proj = root / "projects" / args.slug
    video = proj / "output" / f"{args.slug}_16x9.mp4"
    pacing = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
    rep = audit_delivery(proj, video, pacing, proj / "assets" / "images")
    print(f"[delivery-audit] APPROVED={rep['approved']} | issues={rep['issues_count']} | frames={rep['frames_checked']}")
    for it in rep["issues"][:30]:
        print("  [FAIL]", it)
    print("[delivery-audit] relatorio:", rep.get("report_path"))
    return 0 if rep["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
