/**
 * MANUAL - AvataresCriancas.tsx
 * =============================
 * O que faz
 * ---------
 * Dois avatares cartoon 2D de criança para o catálogo:
 * - menina de cabelo escuro (tranças laterais e presilha mostarda)
 * - menino de cabelo loiro (franja lateral e sardas)
 *
 * Por que existe
 * --------------
 * O pedido é um elenco de contadores de historinha: pequenos no canto da tela,
 * com boca sincronizada com a voz e expressão simpática, sem realismo pesado.
 *
 * Contrato
 * --------
 * Recebem `aberturaBoca` (0..1) e `frame`; devolvem só a arte no viewBox
 * 600x704. Cartão, posição e entrada ficam com `AvatarSelecionavel`.
 */

import React from "react";
import { OlhoCartoon, BocaFalante, calcularPiscar } from "./elementosComunsAvatar";  // 1. peças compartilhadas

/** Menina de cabelo escuro: tranças, presilha e vestido mostarda. */
export const AvatarMeninaCabeloEscuro: React.FC<{ aberturaBoca: number; frame: number }> = ({ aberturaBoca, frame }) => {
  const piscar = calcularPiscar(frame, 99);                                  // 2. piscada
  const olharX = Math.sin(frame / 64 + 0.5) * 3;                             // 3. olhar
  const balanco = Math.sin(frame / 47) * 1.6;                                // 4. balanço da cabeça

  return (
    <svg width="100%" height="100%" viewBox="0 0 600 704" style={{ display: "block" }}>
      {/* 5. cabelo de trás e tranças laterais */}
      <ellipse cx="300" cy="300" rx="160" ry="172" fill="#3A2A22" />
      <circle cx="148" cy="322" r="56" fill="#3A2A22" />
      <circle cx="452" cy="322" r="56" fill="#3A2A22" />
      <rect x="126" y="374" width="44" height="26" rx="13" fill="#D9A441" />
      <rect x="430" y="374" width="44" height="26" rx="13" fill="#D9A441" />

      {/* 6. vestido mostarda e golinha creme */}
      <path d="M116 704 C116 552 196 482 300 482 C404 482 484 552 484 704 Z" fill="#D9A441" />
      <path d="M300 482 C404 482 484 552 484 704 L396 704 C396 596 360 520 300 482 Z" fill="#B5532E" opacity="0.3" />
      <path d="M258 486 Q300 540 342 486 L362 502 Q300 572 238 502 Z" fill="#F4E9D8" />
      <circle cx="300" cy="548" r="12" fill="#2F6F6A" />

      {/* 7. rosto */}
      <g transform={`translate(0 ${balanco})`}>
        <ellipse cx="300" cy="312" rx="138" ry="152" fill="#E8B4A0" />
        <path d="M300 172 C376 172 432 234 438 312 C432 240 374 194 300 194 Z" fill="#D79A86" opacity="0.35" />

        {/* 8. franja em arco e presilha estrelinha */}
        <path d="M162 286 Q300 142 438 286 Q402 242 360 258 Q300 216 240 258 Q198 242 162 286 Z" fill="#3A2A22" />
        <path d="M400 214 L408 232 L428 234 L413 248 L417 268 L400 257 L383 268 L387 248 L372 234 L392 232 Z" fill="#D9A441" />

        {/* 9. olhos com cílios */}
        <OlhoCartoon cx={250} cy={322} raio={17} olharX={olharX} piscar={piscar} />
        <OlhoCartoon cx={350} cy={322} raio={17} olharX={olharX} piscar={piscar} />
        <path d="M232 304 L222 294 M250 302 L248 290 M368 304 L378 294 M350 302 L352 290" stroke="#2B2118" strokeWidth="4" strokeLinecap="round" />

        {/* 10. sobrancelhas, nariz e bochechas */}
        <path d="M226 288 Q250 274 274 288" stroke="#3A2A22" strokeWidth="7" strokeLinecap="round" fill="none" />
        <path d="M326 288 Q350 274 374 288" stroke="#3A2A22" strokeWidth="7" strokeLinecap="round" fill="none" />
        <path d="M300 342 Q292 360 306 364" stroke="#D79A86" strokeWidth="6" strokeLinecap="round" fill="none" />
        <circle cx="212" cy="374" r="22" fill="#C4664F" opacity="0.32" />
        <circle cx="388" cy="374" r="22" fill="#C4664F" opacity="0.32" />

        {/* 11. boca falante */}
        <BocaFalante x={300} y={402} largura={32} abertura={aberturaBoca} />
      </g>
    </svg>
  );
};

/** Menino de cabelo loiro: franja lateral, sardas e suéter verde-azulado. */
export const AvatarMeninoCabeloLoiro: React.FC<{ aberturaBoca: number; frame: number }> = ({ aberturaBoca, frame }) => {
  const piscar = calcularPiscar(frame, 107);                                  // 12. piscada
  const olharX = Math.sin(frame / 69 + 2.1) * 3;                              // 13. olhar
  const balanco = Math.sin(frame / 51 + 0.4) * 1.5;                           // 14. balanço

  return (
    <svg width="100%" height="100%" viewBox="0 0 600 704" style={{ display: "block" }}>
      {/* 15. suéter e gola creme */}
      <path d="M112 704 C112 550 194 482 300 482 C406 482 488 550 488 704 Z" fill="#2F6F6A" />
      <path d="M300 482 C406 482 488 550 488 704 L398 704 C398 594 360 518 300 482 Z" fill="#245550" opacity="0.5" />
      <path d="M256 486 Q300 542 344 486 L366 502 Q300 574 234 502 Z" fill="#F4E9D8" />
      <rect x="120" y="616" width="360" height="14" fill="#D9A441" opacity="0.8" />

      {/* 16. rosto */}
      <g transform={`translate(0 ${balanco})`}>
        <ellipse cx="300" cy="312" rx="138" ry="152" fill="#E8B4A0" />
        <path d="M300 172 C376 172 432 234 438 312 C432 240 374 194 300 194 Z" fill="#D79A86" opacity="0.3" />

        {/* 17. cabelo loiro com franja de lado e topete */}
        <path d="M160 292 Q164 158 300 158 Q436 158 440 292 Q404 248 364 262 Q318 232 244 268 Q196 256 160 292 Z" fill="#E8C46A" />
        <path d="M300 158 Q366 160 404 208 Q360 184 318 196 Z" fill="#F2D98E" opacity="0.8" />
        <path d="M244 268 Q302 232 364 262 Q318 250 268 282 Z" fill="#D9AC50" opacity="0.7" />

        {/* 18. olhos */}
        <OlhoCartoon cx={250} cy={324} raio={17} olharX={olharX} piscar={piscar} />
        <OlhoCartoon cx={350} cy={324} raio={17} olharX={olharX} piscar={piscar} />

        {/* 19. sobrancelhas, nariz, sardas */}
        <path d="M226 290 Q250 276 274 290" stroke="#C79A3F" strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M326 290 Q350 276 374 290" stroke="#C79A3F" strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M300 346 Q294 362 306 366" stroke="#D79A86" strokeWidth="6" strokeLinecap="round" fill="none" />
        {[212, 228, 244, 356, 372, 388].map((x, i) => (
          <circle key={`sarda-${i}`} cx={x} cy={i < 3 ? 380 + (i % 2) * 10 : 380 + ((i - 3) % 2) * 10} r="4" fill="#B5532E" opacity="0.45" />
        ))}
        <circle cx="204" cy="374" r="18" fill="#C4664F" opacity="0.26" />
        <circle cx="396" cy="374" r="18" fill="#C4664F" opacity="0.26" />

        {/* 20. boca falante */}
        <BocaFalante x={300} y={404} largura={32} abertura={aberturaBoca} />
      </g>
    </svg>
  );
};
