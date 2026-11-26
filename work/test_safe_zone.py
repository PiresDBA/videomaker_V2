# -*- coding: utf-8 -*-
"""Gera um frame de inspecao do palco 1080x576 com os avatares na nova posicao.
Desenha uma linha vermelha em y=276 (limite da zona segura global 1620) — nada importante deve estar abaixo dela."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cv2, numpy as np
from core.motion_shorts import (
    _build_bottom_playful_backdrop, _make_sticker_badge_bgra, _alpha_paste_bgra,
    SHORT_SPLIT_BOT_H, SHORT_WIDTH,
)
from core.avatar_studio import _index_character_bank, _make_card_mask
from config import VIDEO_FPS

w, h = SHORT_WIDTH, SHORT_SPLIT_BOT_H
safe = h - 300  # 276
card_sz = 250
mask = _make_card_mask(card_sz)
frame = _build_bottom_playful_backdrop(w, h, "hook")

# avatares na nova posicao (cy=145)
for cx, key in ((285, "frida"), (795, "luna")):
    bank = _index_character_bank(key)
    img = bank["reposo"][0]
    in_sz = card_sz - 2 * mask["margin"]
    sq = cv2.resize(img, (in_sz, in_sz), interpolation=cv2.INTER_AREA)
    alpha = (mask["alpha"].astype(np.float32) / 255.0)[:, :, None]
    card = np.zeros((card_sz, card_sz, 3), np.uint8)
    m = mask["margin"]
    card[m:card_sz-m, m:card_sz-m] = sq
    cy = 145
    y0 = cy - card_sz // 2
    roi = frame[y0:y0+card_sz, cx-card_sz//2:cx+card_sz//2]
    frame[y0:y0+card_sz, cx-card_sz//2:cx+card_sz//2] = np.clip(
        roi.astype(np.float32)*(1-alpha) + card.astype(np.float32)*alpha, 0, 255).astype(np.uint8)

badge = _make_sticker_badge_bgra("FRIDA", (245,158,11), (120,53,15), w=180, h=44)
_alpha_paste_bgra(frame, badge, 285, 250)

cv2.line(frame, (0, safe), (w, safe), (0, 0, 255), 2)
cv2.putText(frame, f"ZONA SEGURA ABAIXO DESTE PONTO (y local {safe} = global 1620)", (20, safe+22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
out = Path("work/teste_safe_zone.png")
cv2.imwrite(str(out), frame)
print("salvo:", out, "| limite safe y local:", safe, "| card ocupa y:", 145-card_sz//2, "..", 145+card_sz//2)
