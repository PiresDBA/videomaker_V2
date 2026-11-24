# -*- coding: utf-8 -*-
"""Rajada de imagens (burst): prompt detalhado para o Agente do Flow e derivação local."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


def build_burst_prompt(scene: dict[str, Any], n: int = 10) -> str:
    """Monta um prompt explícito, um por imagem, para o Agente do Flow gerar a rajada."""
    action = str(scene.get("visual_action") or scene.get("text") or "a cena").strip()
    chars = ", ".join(str(c) for c in (scene.get("characters") or ["Frida", "Luna"]))
    loc = str(scene.get("location") or "praia").strip()
    lines = [
        f"Gere exatamente {n} imagens em sequência, no estilo rajada de câmera (burst): "
        f"são {n} FOTOS SEGUIDAS DO MESMO INSTANTE, em câmera lenta (slow motion).",
        "REGRA MAIS IMPORTANTE: as 10 imagens DEVEM ter EXATAMENTE o MESMO enquadramento, "
        "a MESMA posição de câmera, o MESMO ângulo e o MESMO fundo da imagem de referência. "
        "NÃO troque de plano, NÃO mude de cenário, NÃO aproxime ou afaste a câmera, NÃO gire. "
        "A única coisa que muda de uma imagem para a seguinte é o MOVIMENTO MÍNIMO da ação.",
        f"Use a IMAGEM DE REFERÊNCIA anexada e mantenha IDÊNTICOS em TODAS as {n}: {chars}, "
        f"raças, acessórios, figurino, cenário ({loc}), iluminação, cores e enquadramento 16:9 "
        "em estilo 3D Disney-Pixar. Não invente personagem novo.",
        "Pense numa sequência de frames de vídeo: só um ou dois centímetros de diferença na posição "
        "da parte do corpo/objeto que se move. Todo o resto permanece pixel a pixel igual.",
    ]
    for i in range(1, n + 1):
        pct = round((i - 1) / max(1, n - 1) * 100)
        lines.append(
            f"Imagem {i:02d}: exatamente o mesmo quadro da referência, estágio {pct}% da ação — {action}. "
            "Mude apenas o mínimo necessário da posição para sugerir movimento."
        )
    lines.append("Sem texto, sem legenda, sem marca d'água, sem colagem, sem split screen.")
    return "\n".join(lines)


def derive_burst_frames(src: Path, out_dir: Path, n: int = 10, base_name: str = "burst") -> list[Path]:
    """Fallback sem custo: deriva N quadros QUASE IDÊNTICOS de uma única imagem aprovada.

    Regra 28 (correção do "tremendo dos lados"): variação de zoom de apenas 4%,
    sempre centralizada — os quadros precisam parecer o MESMO enquadramento com um
    mínimo de movimento. Nunca usar deslocamento lateral/zoom forte: aquilo virava
    trepidação quando o pacing encadeava 10 quadros de 0,14s.
    """
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return []
    im = Image.open(src).convert("RGB")
    w, h = im.size
    out: list[Path] = []
    for i in range(n):
        t = i / max(1, n - 1)
        zoom = 1.0 + 0.04 * t
        cw, ch = int(w / zoom), int(h / zoom)
        cx = max(0, min(w - cw, (w - cw) // 2))
        cy = max(0, min(h - ch, (h - ch) // 2))
        frame = im.crop((cx, cy, cx + cw, cy + ch)).resize((w, h), Image.Resampling.LANCZOS)
        p = out_dir / f"{base_name}_{i + 1:02d}.jpg"
        frame.save(p, "JPEG", quality=93)
        out.append(p)
    return out
