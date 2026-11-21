// Kinetic typography overlay for BitcoinShort — regenerated narration (196 words, 61.01 s).
// Every cue is anchored to the REAL word start in words.json. Screen zones are strictly reserved:
//   top 0-30%    -> ONE main cue at a time (y ~ 300px of 1920)
//   middle 30-75% -> objects/events only (no text here)
//   bottom 75-100% -> secondary text (y ~ 1520px)
import React, { useEffect, useMemo, useState } from "react";
import { AbsoluteFill, cancelRender, continueRender, delayRender, Easing, interpolate, useCurrentFrame } from "remotion";
import antonUrl from "./fonts/Anton-latin.woff2";
import { at } from "./words";

const LATIN = "U+0000-00FF, U+0131, U+0152-0153, U+2000-206F, U+20AC, U+2191, U+2193, U+2212, U+2215";
let registered = false;
const useAnton = () => {
  const [handle] = useState(() => delayRender("bitcoin Anton font"));
  useEffect(() => {
    if (typeof FontFace === "undefined" || registered) { continueRender(handle); return; }
    registered = true;
    const face = new FontFace("Anton", `url(${antonUrl}) format('woff2')`, { weight: "400", style: "normal", unicodeRange: LATIN });
    face.load().then(() => { document.fonts.add(face); continueRender(handle); })
      .catch((err) => cancelRender(new Error(`Anton font failed: ${err}`)));
  }, [handle]);
  return "Anton, 'Arial Narrow', Impact, sans-serif";
};

type Cue = {
  a: number; d: number; text: string; size: number; color: string; sub?: string;
  accent?: string; zone?: "main" | "sub"; x?: number;
};
const MAIN_Y = 300;   // 15.6% — top zone
const SUB_Y = 1520;   // 79.2% — bottom zone

// Main cues are sequential: each ends before the next starts. Secondary cues live only in the bottom zone.
const CUES: Cue[] = [
  // ---- hook ----
  { a: at("4") - 2, d: 45, text: "04/11", size: 150, color: "#ffffff", sub: "A DATA DO RECORDE", accent: "#4fa8ff" },
  { a: at("81") - 2, d: 78, text: "US$ 81 MIL", size: 152, color: "#fff4cf", sub: "O VALOR DO BITCOIN", accent: "#f6c445" },
  { a: at("11") - 2, d: 62, text: "11 DIAS", size: 136, color: "#ffffff", sub: "DEPOIS", zone: "sub", accent: "#4fa8ff" },
  { a: at("62.") - 2, d: 78, text: "US$ 62 MIL", size: 152, color: "#ffd7d7", sub: "ONZE DIAS DEPOIS", accent: "#ff6b6b" },
  { a: at("hacker,") - 2, d: 16, text: "NÃO FOI HACKER", size: 88, color: "#ffffff", sub: "✗", zone: "sub", accent: "#ff6b6b" },
  { a: at("proibição,") - 2, d: 44, text: "NEM PROIBIÇÃO", size: 88, color: "#ffffff", sub: "✗", zone: "sub", accent: "#ff6b6b" },
  { a: at("cadeia.") - 2, d: 21, text: "−23%", size: 196, color: "#ff8a80", sub: "REAÇÃO EM CADEIA", accent: "#ff4444" },
  // ---- 1. juros ----
  { a: at("Primeiro,") - 2, d: 38, text: "1 · JUROS", size: 124, color: "#ffffff", sub: "PRIMEIRO", accent: "#7ec8ff" },
  { a: at("Inflação") - 2, d: 64, text: "INFLAÇÃO QUENTE", size: 100, color: "#ffd166", sub: "ESTADOS UNIDOS", zone: "sub", accent: "#ff9f43" },
  { a: at("0") - 2, d: 74, text: "+0,4%", size: 178, color: "#ffe08a", sub: "NO MÊS", accent: "#ff9f43" },
  { a: at("afastam") - 2, d: 76, text: "JUROS ALTOS", size: 124, color: "#ff9f9f", sub: "DINHEIRO FORA DO RISCO", zone: "sub", accent: "#ff5555" },
  // ---- 2. fundos ----
  { a: at("Segundo,") - 2, d: 42, text: "2 · FUNDOS", size: 124, color: "#ffffff", sub: "SEGUNDO", accent: "#5fe0c0" },
  { a: at("ETFs") - 2, d: 42, text: "ETFs EM SAÍDA", size: 112, color: "#9fe0ff", sub: "OS FUNDOS", accent: "#5fe0c0" },
  { a: at("bilhão") - 2, d: 86, text: "US$ 1,91 BI", size: 150, color: "#ffe08a", sub: "SAÍDA DOS ETFs", accent: "#f6c445" },
  { a: at("7") - 2, d: 34, text: "7 DIAS", size: 138, color: "#9fe0ff", sub: "SEGUIDOS", zone: "sub", accent: "#4fa8ff" },
  { a: at("resgate") - 2, d: 36, text: "CADA RESGATE → VENDA", size: 86, color: "#ffffff", sub: "OBRIGA O FUNDO A VENDER", zone: "sub", accent: "#5fe0c0" },
  // ---- 3. ações ----
  { a: at("Terceiro,") - 2, d: 42, text: "3 · AÇÕES", size: 124, color: "#ffffff", sub: "TERCEIRO", accent: "#ff9f6b" },
  { a: at("NASDAQ") - 2, d: 66, text: "−5,5%", size: 176, color: "#ff8a80", sub: "NASDAQ", accent: "#ff4444" },
  { a: at("12.") - 2, d: 47, text: "−12%", size: 176, color: "#ff8a80", sub: "NVIDIA", accent: "#ff4444" },
  { a: at("junto.") - 2, d: 14, text: "O BITCOIN FOI JUNTO", size: 100, color: "#ffffff", sub: "", zone: "sub", accent: "#f6c445" },
  // ---- 4. dominó ----
  { a: at("Quarto,") - 2, d: 50, text: "4 · DOMINÓ", size: 124, color: "#ffffff", sub: "QUARTO", accent: "#ff6b6b" },
  { a: at("70") - 2, d: 45, text: "US$ 70 MIL", size: 150, color: "#ffe08a", sub: "A LINHA ROMPIDA", accent: "#ff6b6b" },
  { a: at("bilhões") - 2, d: 49, text: "US$ 2 BI", size: 174, color: "#ff8a80", sub: "EM 24 HORAS", accent: "#ff4444" },
  { a: at("600") - 2, d: 65, text: "600 MI", size: 150, color: "#ff8a80", sub: "SÓ QUEM APOSTAVA NA ALTA", zone: "sub", accent: "#ff4444" },
  // ---- 5. boa / má notícia (new wording) ----
  { a: at("Vou") - 2, d: 42, text: "BOA NOTÍCIA", size: 112, color: "#7CFFB2", sub: "MAIS BARATO", accent: "#22c55e" },
  { a: at("Uma") - 3, d: 70, text: "MÁ NOTÍCIA", size: 112, color: "#FF7A7A", sub: "NINGUÉM SABE O PRÓXIMO", accent: "#ef4444" },
  // ---- 6. a fila de dominós ----
  { a: at("Pense") - 2, d: 20, text: "PENSE NUM DOMINÓ", size: 100, color: "#ffffff", sub: "UMA FILA", accent: "#f6c445" },
  { a: at("dominós.") - 2, d: 18, text: "DOMINÓS EM PÉ", size: 100, color: "#ffe08a", sub: "A FILA", accent: "#f6c445" },
  { a: at("Derrube") - 2, d: 30, text: "DERRUBE O PRIMEIRO", size: 112, color: "#7CFFB2", sub: "O ESTALO", accent: "#22c55e" },
  { a: at("caem") - 2, d: 30, text: "CAEM SOZINHOS", size: 118, color: "#ffffff", sub: "SEM EMPURRO", accent: "#4fa8ff" },
  { a: at("cada", 1) - 2, d: 52, text: "CADA PEÇA DERRUBA MAIS DUAS", size: 88, color: "#ffb17a", sub: "A CASCATA", accent: "#ff9f43" },
  { a: at("Ninguém") - 2, d: 36, text: "NINGUÉM EMPURROU A ÚLTIMA", size: 88, color: "#ffffff", sub: "", accent: "#f6c445" },
  { a: at("caiu", 1) - 2, d: 60, text: "ELA CAIU PORQUE AS OUTRAS CAÍRAM", size: 82, color: "#ff9f9f", sub: "", accent: "#ff4444" },
  { a: at("preço.") - 2, d: 14, text: "FOI O QUE ACONTECEU COM O PREÇO", size: 82, color: "#ffffff", sub: "", accent: "#f6c445" },
  // ---- 7. consequência ----
  { a: at("Quando") - 2, d: 58, text: "NÃO FOI UMA NOTÍCIA", size: 100, color: "#ffffff", sub: "LEMBRE", accent: "#4fa8ff" },
  { a: at("quatro") - 2, d: 24, text: "4 FATORES", size: 136, color: "#ffe08a", sub: "SOMADOS", accent: "#f6c445" },
  { a: at("Juros,") - 2, d: 46, text: "JUROS", size: 72, color: "#8ecbff", sub: "", zone: "sub", x: 0.2, accent: "#4fa8ff" },
  { a: at("fundos,") - 2, d: 46, text: "FUNDOS", size: 72, color: "#ffe08a", sub: "", zone: "sub", x: 0.4, accent: "#f6c445" },
  { a: at("ações") - 2, d: 46, text: "AÇÕES", size: 72, color: "#ffb17a", sub: "", zone: "sub", x: 0.6, accent: "#ff9f43" },
  { a: at("alavancagem.") - 2, d: 46, text: "ALAVANCAGEM", size: 64, color: "#ff8a80", sub: "", zone: "sub", x: 0.8, accent: "#ff4444" },
  // ---- 8. fecho ----
  { a: at("A", 4) - 2, d: 72, text: "A IRONIA", size: 128, color: "#ffffff", sub: "O APOIO LEVOU AO RECORDE", accent: "#f6c445" },
  { a: at("torneira") - 2, d: 68, text: "TORNEIRA FECHADA", size: 108, color: "#ff8a80", sub: "HOJE ELA ESTÁ FECHADA", accent: "#ff4444" },
];

const env = (f: number, a: number, d: number) => {
  const rise = interpolate(f, [a, a + 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const fall = interpolate(f, [a + d - 7, a + d], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  return Math.max(0, Math.min(rise, fall));
};

const One: React.FC<{ cue: Cue; f: number; font: string }> = ({ cue, f, font }) => {
  const t = f - cue.a;
  if (t < 0 || t > cue.d) return null;
  const o = env(f, cue.a, cue.d);
  if (o <= 0.01) return null;
  const scale = 0.76 + 0.24 * interpolate(t, [0, 7], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.back(1.6)) }) - 0.06 * (1 - o);
  const dy = (1 - o) * 46;
  const sub = cue.zone === "sub";
  const long = cue.text.length > 16;
  const size = long ? Math.min(cue.size, 78) : cue.size;
  return (
    <div style={{
      position: "absolute", left: cue.x === undefined ? "50%" : `${cue.x * 100}%`,
      top: sub ? SUB_Y : MAIN_Y, width: cue.x === undefined ? 900 : 440,
      transform: `translate(-50%, -50%) translateY(${dy}px) scale(${scale})`,
      opacity: o, textAlign: "center", fontFamily: font, color: cue.color,
      textShadow: "0 7px 0 rgba(0,0,0,.55), 0 0 34px rgba(0,0,0,.4)",
    }}>
      {cue.sub ? <div style={{ fontFamily: "Arial, sans-serif", fontSize: 26, fontWeight: 800, letterSpacing: 6,
        color: cue.accent ?? "#fff", marginBottom: 10, textTransform: "uppercase" }}>{cue.sub}</div> : null}
      <div style={{ fontSize: size, lineHeight: 1.0, letterSpacing: 1, whiteSpace: long ? "normal" : "nowrap" }}>{cue.text}</div>
      <div style={{ height: 8, width: "46%", margin: "14px auto 0", borderRadius: 8, background: cue.accent ?? "#fff", opacity: 0.9 }} />
    </div>
  );
};

export const KineticText: React.FC = () => {
  const f = useCurrentFrame();
  const font = useAnton();
  const visible = useMemo(() => CUES.filter((c) => f >= c.a && f <= c.a + c.d), [f]);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {visible.map((c, i) => <One key={`${c.a}-${i}`} cue={c} f={f} font={font} />)}
    </AbsoluteFill>
  );
};
