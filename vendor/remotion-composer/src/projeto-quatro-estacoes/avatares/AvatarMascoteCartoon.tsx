/**
 * MANUAL - AvatarMascoteCartoon.tsx
 * ==================================
 * O que faz
 * ---------
 * Versão "arte pura" do mascote das Quatro Estações (mesmo boneco do componente
 * original), para entrar no catálogo selecionável ao lado dos cães e crianças.
 *
 * Por que existe
 * --------------
 * O componente antigo desenha o próprio cartão e se posiciona na composição.
 * Aqui ele só devolve o SVG dentro do viewBox 600x704; quem decide cartão,
 * posição e entrada é `AvatarSelecionavel`.
 *
 * Contrato
 * --------
 * Recebe `aberturaBoca` (0..1) e `frame`; a boca usa o mesmo desenho dos
 * outros avatares (cavidade + língua + sorriso de repouso).
 */

import React from "react";
import { interpolate } from "remotion";                          // 1. interpola sorriso/pálpebra
import { OlhoCartoon, calcularPiscar } from "./elementosComunsAvatar";  // 2. olho compartilhado

/** Mascote original (chapéu, cachecol, passarinho) em modo arte pura. */
export const AvatarMascoteCartoon: React.FC<{ aberturaBoca: number; frame: number }> = ({ aberturaBoca, frame }) => {
  const a = Math.max(0, Math.min(1, aberturaBoca));                // 3. normaliza
  const piscar = calcularPiscar(frame, 105);                       // 4. piscada
  const olharX = Math.sin(frame / 73) * 3;                         // 5. olhar
  const balanco = Math.sin(frame / 58) * 1.8;                      // 6. balanço da cabeça
  const respiracao = 1 + Math.sin(frame / 44) * 0.004;             // 7. respiração
  const balancoCachecol = Math.sin(frame / 40 + 0.6) * 5;          // 8. ponta do cachecol
  const largura = 34 + a * 4;                                      // 9. largura da boca
  const altura = 3 + a * 28;                                       // 10. altura da boca
  const sorriso = interpolate(a, [0, 0.18], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });  // 11.

  return (
    <svg width="100%" height="100%" viewBox="0 0 600 704" style={{ display: "block" }}>
      {/* 12. corpo */}
      <g transform={`translate(300 704) scale(1 ${respiracao}) translate(-300 -704)`}>
        <path d="M96 704 C96 548 180 474 300 474 C420 474 504 548 504 704 Z" fill="#2F6F6A" />
        <path d="M300 474 C420 474 504 548 504 704 L414 704 C414 590 372 520 300 474 Z" fill="#245550" opacity="0.55" />
        <path d="M232 492 L300 574 L368 492 L342 470 L300 518 L258 470 Z" fill="#F4E9D8" opacity="0.9" />
      </g>

      {/* 13. cachecol */}
      <rect x="196" y="448" width="208" height="58" rx="29" fill="#D9A441" />
      <rect x="196" y="484" width="208" height="22" rx="11" fill="#B5532E" opacity="0.25" />
      <g transform={`translate(${balancoCachecol} 0)`}>
        <rect x="330" y="470" width="42" height="116" rx="21" fill="#D9A441" />
        <rect x="330" y="548" width="42" height="20" fill="#B5532E" />
      </g>

      {/* 14. cabeça, chapéu e passarinho */}
      <g transform={`translate(300 ${Math.sin(frame / 31) * 2}) rotate(${balanco} 300 330) translate(-300 0)`}>
        <rect x="262" y="430" width="76" height="60" rx="24" fill="#D79A86" />
        <ellipse cx="300" cy="330" rx="150" ry="158" fill="#E8B4A0" />
        <path d="M170 380 C190 470 410 470 430 380 C420 440 380 470 300 470 C220 470 180 440 170 380 Z" fill="#D79A86" opacity="0.35" />
        <ellipse cx="152" cy="336" rx="20" ry="28" fill="#E8B4A0" />
        <ellipse cx="448" cy="336" rx="20" ry="28" fill="#E8B4A0" />
        <path d="M148 232 C148 112 452 112 452 232 Z" fill="#B5532E" />
        <rect x="128" y="222" width="344" height="28" rx="14" fill="#2F6F6A" />
        <g transform={`translate(438 206) rotate(${8 + Math.sin(frame / 33) * 5})`}>
          <ellipse cx="0" cy="0" rx="30" ry="26" fill="#F2C14E" />
          <circle cx="22" cy="-10" r="17" fill="#F2C14E" />
          <path d="M36 -12 L54 -4 L36 2 Z" fill="#B5532E" />
          <circle cx="27" cy="-14" r="3.2" fill="#2B2118" />
        </g>

        {/* 15. olhos, sobrancelhas e detalhes */}
        <OlhoCartoon cx={245} cy={316} raio={16} olharX={olharX} piscar={piscar} corBrilho="#F4E9D8" />
        <OlhoCartoon cx={355} cy={316} raio={16} olharX={olharX} piscar={piscar} corBrilho="#F4E9D8" />
        <path d="M212 280 Q244 262 276 282" stroke="#2B2118" strokeWidth="9" strokeLinecap="round" fill="none" />
        <path d="M324 282 Q356 262 388 280" stroke="#2B2118" strokeWidth="9" strokeLinecap="round" fill="none" />
        <path d="M300 342 Q292 360 306 364" stroke="#D79A86" strokeWidth="7" strokeLinecap="round" fill="none" />
        <circle cx="214" cy="368" r="24" fill="#C4664F" opacity="0.32" />
        <circle cx="386" cy="368" r="24" fill="#C4664F" opacity="0.32" />

        {/* 16. boca falante */}
        <path d={`M ${300 - largura} 392 Q 300 ${388 - a * 2} ${300 + largura} 392 Q 300 ${392 + altura} ${300 - largura} 392 Z`} fill="#5B2B23" />
        {a > 0.25 && <ellipse cx="300" cy={392 + altura * 0.66} rx={largura * 0.55} ry={Math.max(1.5, altura * 0.2)} fill="#C4695B" />}
        <path d={`M ${300 - largura} 392 Q 300 ${388 - a * 3} ${300 + largura} 392`} stroke="#2B2118" strokeWidth="5" strokeLinecap="round" fill="none" />
        <path d="M 262 391 Q 300 407 338 391" stroke="#2B2118" strokeWidth="7" strokeLinecap="round" fill="none" opacity={sorriso} />
      </g>
    </svg>
  );
};
