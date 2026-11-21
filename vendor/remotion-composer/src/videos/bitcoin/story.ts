// BitcoinShort — 61 s vertical short, 9 shots anchored to the regenerated narration (196 words).
// Beat 7 is now a DOMINO cascade (not a swing): "Pense numa fila de dominós...".
// Every visual event is keyed to a real word start from voice/words.json (see words.ts).
//
// Reserved screen zones: top 0-30% = one main text cue; middle 30-75% = objects/events;
// bottom 75-100% = secondary text. The coin is a small fixed anchor in the lower-left corner.

export const FPS = 30;
export const TOTAL = 1830; // 61.0 s
export const D0 = 6.0;
export const PARK: V3 = [70, D0, -75]; // park plaza — now the home of the beat-7 domino row
export const COIN: V3 = [PARK[0], D0, PARK[2] + 8];
export const DOMINO5: V3 = [COIN[0], D0, COIN[2] + 2]; // beat 5 row (on the lawn, in front of the coin)
export const DOMINO7: V3 = [PARK[0], D0, PARK[2]];     // beat 7 row (the "fila de dominós")

// --- unused compatibility exports (kept so the copied world/cast modules still type-check) ---
export const HALF = 27;
export const FILES = [-1.65, -0.55, 0.55, 1.65];
export const ROW_GAP = 1.3;
export const COUNT = 74;
export type V3 = [number, number, number];

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
export const easeOut = (u: number) => 1 - (1 - clamp01(u)) ** 4;
const lin = (pts: [number, number][], x: number) => {
  if (x <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) if (x <= pts[i][0]) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
    return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
  }
  return pts[pts.length - 1][1];
};

export const front = (tau: number) => 26 - 1.6 * (tau - 4.4);
export const marchPhase = (tau: number) => ((tau % 1) + 1) % 1;
export const SNAP = 34.62, DROP0 = 36.35, DROP1 = 36.95, DROP_H = 6.6;
export const amp = (tau: number) =>
  lin([[14.85, 0], [17.8, 0.07], [21.4, 0.13], [27.4, 0.26], [33.0, 0.46], [SNAP, 0.55], [SNAP + 0.35, 0]], tau);
export const stomp = (tau: number) => lin([[21.4, 1], [27.4, 1.35], [33, 1.5]], tau);
export const shapeZ = (z: number) => (Math.abs(z) < HALF ? Math.cos((Math.PI * z) / (2 * HALF)) : 0);
export const dropW = (z: number) => smooth((20 - z) / 26);
export const dropU = (tau: number) => (tau < DROP0 ? 0 : Math.min(1, ((tau - DROP0) / (DROP1 - DROP0)) ** 2));
export type BridgeState = { bounce: number; drop: number; snap: number; collapsed: boolean };
export const deckY = (z: number, b: BridgeState) => D0 + b.bounce * shapeZ(z) - b.drop * DROP_H * dropW(z);
export const bridgeState = (_id: number, _t: number): BridgeState => ({ bounce: 0, drop: 0, snap: 0, collapsed: false });

/** the falling-price coin — now a small corner anchor, never the protagonist */
export const coinY = (t: number) =>
  COIN[1] + 11.5 - 8.0 * easeOut(t / 5.4) - 0.6 * smooth((t - 5.4) / 28) + 0.18 * Math.sin(t * 2.6);
export const coinPhase = (t: number) => (t * 0.85) % 1;

// ---------------- shots ----------------
export type Light = "day" | "golden";
export type Crowd = "none" | "parkcrowd";
export type ShotDef = { id: number; a: number; b: number; light: Light; crowd: Crowd; tau: (t: number) => number; towns?: boolean };
export const SHOTS: ShotDef[] = [
  { id: 1, a: 0, b: 273, light: "day", crowd: "none", tau: (t) => t },                     // hook
  { id: 2, a: 273, b: 501, light: "day", crowd: "none", tau: (t) => t, towns: true },      // juros
  { id: 3, a: 501, b: 735, light: "day", crowd: "none", tau: (t) => t },                   // fundos
  { id: 4, a: 735, b: 895, light: "day", crowd: "none", tau: (t) => t },                   // ações
  { id: 5, a: 895, b: 1120, light: "day", crowd: "none", tau: (t) => t },                  // dominó + liquidações
  { id: 6, a: 1120, b: 1240, light: "golden", crowd: "none", tau: (t) => t },              // boa/má notícia
  { id: 7, a: 1240, b: 1533, light: "golden", crowd: "none", tau: (t) => t },              // fila de dominós
  { id: 8, a: 1533, b: 1685, light: "day", crowd: "parkcrowd", tau: (t) => t, towns: true }, // consequência
  { id: 9, a: 1685, b: TOTAL, light: "golden", crowd: "none", tau: (t) => t, towns: true }, // fecho
];

export const XFADE: Record<number, number> = { 2: 8, 4: 8, 6: 8, 7: 8, 8: 8, 9: 8 };
export const FLASH_AT = 273;

export const shotAt = (f: number) => SHOTS.find((s) => f >= s.a && f < s.b) ?? SHOTS[SHOTS.length - 1];
export const layersAt = (f: number): { id: number; alpha: number }[] => {
  for (const s of SHOTS) {
    const x = XFADE[s.id];
    if (x && f >= s.a - x / 2 && f < s.a + x / 2) return [{ id: s.id - 1, alpha: 1 }, { id: s.id, alpha: (f - (s.a - x / 2) + 1) / (x + 1) }];
  }
  return [{ id: shotAt(f).id, alpha: 1 }];
};

// ---------------- camera ----------------
export type Cam = { pos: V3; look: V3; fov: number; roll: number };
type Shot = Partial<Cam> & { pos: V3; look: V3 };
type Key = { f: number; dur?: number; cut?: boolean; s: (f: number) => Shot };
export const glide = (u: number) => { const x = clamp01(u); return x * x * x * (x * (6 * x - 15) + 10); };
const mix = (a: Cam, b: Cam, k: number): Cam => ({
  pos: a.pos.map((v, i) => v + (b.pos[i] - v) * k) as V3, look: a.look.map((v, i) => v + (b.look[i] - v) * k) as V3,
  fov: a.fov + (b.fov - a.fov) * k, roll: a.roll + (b.roll - a.roll) * k,
});
const full = (c: Shot): Cam => ({ fov: 40, roll: 0, ...c });
const run = (keys: Key[], f: number) => {
  let cur = full(keys[0].s(f));
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (f < k.f) break;
    cur = k.cut ? full(k.s(f)) : mix(cur, full(k.s(f)), glide((f - k.f) / (k.dur ?? 24)));
  }
  return cur;
};
const T = (f: number) => f / FPS;
const pushK = (f: number, f0: number, rate: number, punch = 0, n = 35) => {
  const x = Math.max(0, f - f0);
  let s = rate * x;
  if (punch > rate) for (let i = 0; i < Math.min(x, n); i++) s += (punch - rate) * Math.max(0, Math.min(1, (i + 0.5) / 8, (n - i - 0.5) / 8));
  return Math.exp(-s);
};
const dolly = (pos: V3, look: V3, k: number, rest: Partial<Cam> = {}): Shot =>
  ({ pos: [look[0] + (pos[0] - look[0]) * k, look[1] + (pos[1] - look[1]) * k, look[2] + (pos[2] - look[2]) * k], look, ...rest });
const zoom = (pos: V3, look: V3, fov: number, k: number, rest: Partial<Cam> = {}): Shot =>
  ({ pos, look, fov: (360 / Math.PI) * Math.atan(Math.tan((fov * Math.PI) / 360) * k), ...rest });
// compatibility
export const ANCHOR: V3 = [-2.7, D0 + 0.62, -37];
export const snapEnd = (snap: number): V3 => {
  const u = easeOut(snap);
  return [ANCHOR[0] - 0.6 * u, ANCHOR[1] + 5.5 * u - 2.0 * u * u, ANCHOR[2] + 4.5 * u];
};

const atCoin = (f: number): V3 => [COIN[0], coinY(T(f)), COIN[2]];

// shots 1-4 — same grammar, new frame keys
const S1a = (f: number) => dolly([COIN[0] + 6.5, D0 + 6.2, COIN[2] - 15], atCoin(f), pushK(f, 0, 0.0024), { fov: 46 });
const S1b = (f: number) => dolly([COIN[0] + 1.4, D0 + 4.0, COIN[2] - 7.5], atCoin(f), pushK(f, 80, 0.002), { fov: 39, roll: -0.05 });
const S1c = (f: number) => dolly([COIN[0] - 1.2, D0 + 1.1, COIN[2] - 4.2], atCoin(f), pushK(f, 176, 0.0028), { fov: 36, roll: 0.045 });
const S2a = (f: number) => zoom([COIN[0] + 17, D0 + 11, COIN[2] - 24], [COIN[0], D0 + 3, COIN[2] + 7], 44, pushK(f, 271, 0.0018));
const S2b = (f: number) => zoom([COIN[0] + 9, D0 + 7, COIN[2] - 15], [COIN[0], coinY(T(f)) - 0.5, COIN[2]], 42, pushK(f, 370, 0.002));
const S2c = (f: number) => dolly([COIN[0] + 2.2, D0 + 2.6, COIN[2] - 6.5], atCoin(f), pushK(f, 448, 0.0023, 0.006, 35), { fov: 37, roll: -0.035 });
const S3a = (f: number) => dolly([COIN[0] - 3.2, D0 + 4.8, COIN[2] - 9.5], atCoin(f), pushK(f, 499, 0.002), { fov: 42 });
const S3b = (f: number) => dolly([COIN[0] - 0.6, D0 + 2.2, COIN[2] - 5.4], atCoin(f), pushK(f, 620, 0.0019), { fov: 36, roll: 0.04 });
const S4a = (f: number) => dolly([COIN[0] + 8.5, D0 + 2.3, COIN[2] + 2.5], atCoin(f), pushK(f, 733, 0.0022), { fov: 44, roll: -0.05 });
const S4b = (f: number) => dolly([COIN[0] + 5.5, D0 + 6.5, COIN[2] - 9], atCoin(f), pushK(f, 820, 0.002), { fov: 40, roll: 0.03 });

// shot 5 — look DOWN at the real domino row standing on the lawn
const S5a = (f: number) => dolly([DOMINO5[0] + 3.0, D0 + 3.0, DOMINO5[2] - 7.5], [DOMINO5[0], D0 + 0.45, DOMINO5[2]], pushK(f, 895, 0.0022), { fov: 44 });
const S5b = (f: number) => dolly([DOMINO5[0] - 0.5, D0 + 2.2, DOMINO5[2] - 5.0], [DOMINO5[0], D0 + 0.4, DOMINO5[2]], pushK(f, 1000, 0.002), { fov: 40, roll: -0.04 });
const S5c = (f: number) => dolly([DOMINO5[0] - 4.0, D0 + 4.0, DOMINO5[2] - 4.5], [DOMINO5[0], D0 + 0.4, DOMINO5[2]], pushK(f, 1060, 0.002), { fov: 43, roll: 0.045 });

// shot 6 — golden coin settle
const S6a = (f: number) => dolly([COIN[0] + 0.7, D0 + 0.85, COIN[2] - 3.6], atCoin(f), pushK(f, 1118, 0.0015), { fov: 36 });

// shot 7 — the domino cascade: a clear, slightly high front view of the row
const S7a = (f: number) => dolly([DOMINO7[0] + 0.6, D0 + 2.4, DOMINO7[2] - 6.5], [DOMINO7[0], D0 + 0.45, DOMINO7[2]], pushK(f, 1241, 0.0016), { fov: 42 });
const S7b = (f: number) => dolly([DOMINO7[0] - 2.2, D0 + 3.2, DOMINO7[2] - 8.0], [DOMINO7[0], D0 + 0.4, DOMINO7[2]], pushK(f, 1370, 0.0014), { fov: 44, roll: -0.035 });

const S8a = (f: number) => dolly([PARK[0] - 10, D0 + 3.4, PARK[2] + 3], [PARK[0] - 1, D0 + 1.6, PARK[2] - 3], pushK(f, 1531, 0.002), { fov: 44 });
const S8b = (f: number) => dolly([PARK[0] - 5.5, D0 + 2.2, PARK[2] - 1.5], [PARK[0] - 1, D0 + 1.6, PARK[2] - 3], pushK(f, 1604, 0.0022, 0.006, 32), { fov: 39, roll: -0.03 });
const S9a = (f: number) => zoom([PARK[0] + 14, D0 + 10, PARK[2] - 20], [PARK[0], D0 + 3, PARK[2] + 6], 42, pushK(f, 1683, 0.0013));
const S9b = (f: number) => zoom([PARK[0] + 20, D0 + 13, PARK[2] - 27], [PARK[0], D0 + 4, PARK[2] + 10], 44, pushK(f, 1762, 0.0011), { roll: 0.025 });

const CAMS: Record<number, Key[]> = {
  1: [{ f: 0, s: S1a }, { f: 80, dur: 30, s: S1b }, { f: 176, dur: 32, s: S1c }],
  2: [{ f: 271, s: S2a }, { f: 370, dur: 22, s: S2b }, { f: 448, dur: 28, s: S2c }],
  3: [{ f: 499, s: S3a }, { f: 620, cut: true, s: S3b }],
  4: [{ f: 733, s: S4a }, { f: 820, cut: true, s: S4b }],
  5: [{ f: 895, s: S5a }, { f: 1000, cut: true, s: S5b }, { f: 1060, cut: true, s: S5c }],
  6: [{ f: 1118, s: S6a }],
  7: [{ f: 1241, s: S7a }, { f: 1370, dur: 30, s: S7b }],
  8: [{ f: 1531, s: S8a }, { f: 1604, dur: 28, s: S8b }],
  9: [{ f: 1683, s: S9a }, { f: 1762, dur: 34, s: S9b }],
};

/** kicks on "62", "liquidaram", "600" and the last domino */
const KICKS: [number, number][] = [[4.93, 1], [32.47, 1.25], [35.1, 0.7], [50.63, 0.5]];
export const kickAt = (t: number) => {
  let a = 0;
  for (const [t0, g] of KICKS) {
    const n = Math.floor((t - t0) * FPS + 1e-6);
    if (n >= 0 && n < 7) a += g * (n % 2 ? -1 : 1) * (1 - n / 7) ** 1.5;
  }
  return a;
};
export const camAt = (id: number, f: number): Cam => {
  const c = run(CAMS[id], f), a = kickAt(T(f));
  if (!a) return c;
  const d: V3 = [c.look[0] - c.pos[0], c.look[1] - c.pos[1], c.look[2] - c.pos[2]];
  const L = Math.hypot(...d), h = Math.hypot(d[0], d[2]) || 1;
  const m = (3 / 640) * Math.tan((c.fov * Math.PI) / 360) * L * a;
  return { ...c, look: [c.look[0] - (d[2] / h) * m, c.look[1] + 0.6 * m, c.look[2] + (d[0] / h) * m], roll: c.roll + a * 0.004 };
};
export const keyEnd = (id: number, f: number) => {
  let e = 0;
  for (const k of CAMS[id]) if (f >= k.f) e = k.f + (k.cut ? 0 : k.dur ?? 24);
  return Math.max(f, e);
};

// ---------------- lens ----------------
export type Dof = { f: number; dur?: number; cInf: number; focus?: (f: number) => V3 };
const coinFocus = (f: number): V3 => atCoin(f);
const dominoFocus = (): V3 => [DOMINO7[0], D0 + 0.5, DOMINO7[2]];
export const DOF: Dof[] = [
  { f: 0, cInf: 13, focus: coinFocus },
  { f: 80, dur: 30, cInf: 14, focus: coinFocus },
  { f: 176, dur: 32, cInf: 15, focus: coinFocus },
  { f: 273, cInf: 0 },
  { f: 448, dur: 28, cInf: 12, focus: coinFocus },
  { f: 501, cInf: 13, focus: coinFocus },
  { f: 735, cInf: 0 },
  { f: 902, cInf: 10, focus: () => [DOMINO5[0], D0 + 0.5, DOMINO5[2]] },
  { f: 1120, cInf: 14, focus: coinFocus },
  { f: 1240, cInf: 8, focus: dominoFocus },
  { f: 1533, cInf: 0 },
  { f: 1685, cInf: 5 },
];
export const dofAt = (f: number) => {
  let i = 0; while (i + 1 < DOF.length && f >= DOF[i + 1].f) i++;
  const d = DOF[i], p = DOF[Math.max(0, i - 1)];
  const k = d.dur ? Math.min(1, (f - d.f) / d.dur) : 1;
  return { cInf: p.cInf + (d.cInf - p.cInf) * k, focus: d.focus };
};
export const focusAt = (id: number, f: number): V3 => {
  const d = dofAt(f);
  return d.focus ? d.focus(f) : camAt(id, f).look;
};

export type Fg = { a: number; b: number; kit: string; pos: V3; s?: number; yaw?: number };
export const FOREGROUND: Fg[] = [];
