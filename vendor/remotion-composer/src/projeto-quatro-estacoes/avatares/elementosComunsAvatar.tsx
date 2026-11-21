/**
 * MANUAL - elementosComunsAvatar.tsx
 * ===================================
 * O que faz
 * ---------
 * Peças reutilizadas por todos os avatares cartoon 2D: olho que pisca, boca
 * que abre de acordo com a amplitude real da voz e cálculo da piscada.
 *
 * Por que existe
 * --------------
 * Um único olho/boca compartilhado garante que todos os avatares do catálogo
 * tenham o mesmo comportamento de lip-sync e a mesma cadência de piscada.
 *
 * Regra
 * -----
 * Sem `useFrame()`, sem relógio: a animação inteira vem do frame recebido por
 * prop (que veio de `useCurrentFrame()` no componente pai).
 */

import React from "react";
import { interpolate } from "remotion";  // 1. mapeamento determinístico de valores

/** Calcula a escala vertical do olho: 1 aberto, 0,08 fechado. */
export const calcularPiscar = (frame: number, periodo = 105): number => {
  const posicao = ((frame % periodo) + periodo) % periodo;                  // 2. posição no ciclo
  return interpolate(posicao, [0, periodo - 9, periodo - 5, periodo - 2, periodo], [1, 1, 0.08, 0.08, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                       // 3. piscada de ~6 frames
};

/** Olho cartoon: íris escura, brilho e pálpebra quando pisca. */
export const OlhoCartoon: React.FC<{
  cx: number;                 // centro X
  cy: number;                 // centro Y
  raio?: number;              // raio da íris
  olharX?: number;            // desvio horizontal da pupila
  olharY?: number;            // desvio vertical da pupila
  piscar?: number;            // 1 aberto, 0,08 fechado
  corIris?: string;
  corBrilho?: string;
}> = ({ cx, cy, raio = 16, olharX = 0, olharY = 0, piscar = 1, corIris = "#2B2118", corBrilho = "#FFF8EF" }) => {
  const raioEfetivo = raio;                                                 // 4. tamanho base
  return (
    <g transform={`translate(${olharX} ${olharY})`}>
      {/* 5. escala vertical simula a pálpebra fechando */}
      <g transform={`translate(${cx} ${cy}) scale(1 ${piscar}) translate(${-cx} ${-cy})`}>
        <ellipse cx={cx} cy={cy} rx={raioEfetivo} ry={raioEfetivo * 1.15} fill={corIris} />
        <circle cx={cx + raioEfetivo * 0.34} cy={cy - raioEfetivo * 0.38} r={raioEfetivo * 0.27} fill={corBrilho} />
        <circle cx={cx - raioEfetivo * 0.38} cy={cy + raioEfetivo * 0.42} r={raioEfetivo * 0.1} fill={corBrilho} opacity={0.5} />
      </g>
      {/* 6. risco da pálpebra aparece quando o olho fecha */}
      {piscar < 0.2 && (
        <path d={`M ${cx - raioEfetivo} ${cy} Q ${cx} ${cy + 4} ${cx + raioEfetivo} ${cy}`} stroke={corIris} strokeWidth={4} strokeLinecap="round" fill="none" />
      )}
    </g>
  );
};

/** Boca que abre com a amplitude da voz e sorri quando está fechada. */
export const BocaFalante: React.FC<{
  x: number;                  // centro X da boca
  y: number;                  // centro Y da boca
  largura?: number;           // largura em repouso
  abertura?: number;          // 0..1, vem do lipsync
  corInterior?: string;
  corLingua?: string;
  corContorno?: string;
  estilo?: "humana" | "focinho";
}> = ({ x, y, largura = 34, abertura = 0, corInterior = "#5B2B23", corLingua = "#C4695B", corContorno = "#2B2118", estilo = "humana" }) => {
  const a = Math.max(0, Math.min(1, abertura));                             // 7. normaliza
  const larguraEfetiva = largura * (0.92 + 0.08 * a);                       // 8. abre um pouco na lateral
  const alturaMaxima = estilo === "focinho" ? 26 : 30;                      // 9. focinho abre menos
  const altura = 3 + a * alturaMaxima * (largura / 34);                     // 10. altura da abertura
  const opacidadeSorriso = interpolate(a, [0, 0.18], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                       // 11. sorriso some ao falar

  return (
    <g>
      {/* 12. cavidade escura: é o que realmente abre e fecha */}
      <path
        d={`M ${x - larguraEfetiva} ${y} Q ${x} ${y - 3 * a} ${x + larguraEfetiva} ${y} Q ${x} ${y + altura} ${x - larguraEfetiva} ${y} Z`}
        fill={corInterior}
      />
      {/* 13. língua só aparece quando a boca está bem aberta */}
      {a > 0.25 && (
        <ellipse cx={x} cy={y + altura * 0.64} rx={larguraEfetiva * 0.52} ry={Math.max(1.5, altura * 0.18)} fill={corLingua} />
      )}
      {/* 14. lábio superior */}
      <path
        d={`M ${x - larguraEfetiva} ${y} Q ${x} ${y - 4 - 2 * a} ${x + larguraEfetiva} ${y}`}
        stroke={corContorno}
        strokeWidth={estilo === "focinho" ? 4 : 5}
        strokeLinecap="round"
        fill="none"
      />
      {/* 15. sorriso de repouso (não é lip-sync, é expressão) */}
      {opacidadeSorriso > 0 && (
        <path
          d={`M ${x - largura * 1.12} ${y - 1} Q ${x} ${y + largura * 0.34} ${x + largura * 1.12} ${y - 1}`}
          stroke={corContorno}
          strokeWidth={estilo === "focinho" ? 5 : 7}
          strokeLinecap="round"
          fill="none"
          opacity={opacidadeSorriso}
        />
      )}
    </g>
  );
};
