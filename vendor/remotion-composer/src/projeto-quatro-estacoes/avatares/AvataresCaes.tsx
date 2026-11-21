/**
 * MANUAL - AvataresCaes.tsx
 * =========================
 * O que faz
 * ---------
 * Dois avatares cartoon 2D de cachorro para o catálogo:
 * - buldogue inglês (focinho curto, rugas, orelhas pequenas e bandeira britânica)
 * - salsicha marrom (dachshund: focinho alongado e orelhas compridas)
 *
 * Por que desenho vetorial
 * ------------------------
 * São poucos caminhos SVG: cabem num cantinho da tela, não usam VRAM e a boca
 * é um componente compartilhado, ligado ao RMS real da narração.
 *
 * Contrato
 * --------
 * Recebem `aberturaBoca` (0..1) e `frame`; devolvem só a arte no viewBox
 * 600x704. Cartão, posição e entrada ficam com `AvatarSelecionavel`.
 */

import React from "react";
import { OlhoCartoon, BocaFalante, calcularPiscar } from "./elementosComunsAvatar";  // 1. peças compartilhadas

/** Fridóca (Frida) — buldogue inglês fawn/branco, colarinho Union Jack, ficha de consistência. */
export const AvatarBuldogueIngles: React.FC<{ aberturaBoca: number; frame: number }> = ({ aberturaBoca, frame }) => {
  const piscar = calcularPiscar(frame, 112);                                 // 2. piscada do cão
  const olharX = Math.sin(frame / 71) * 3;                                   // 3. olhar lateral discreto
  const balanco = Math.sin(frame / 52) * 1.5;                                // 4. balanço da cabeça

  return (
    <svg width="100%" height="100%" viewBox="0 0 600 704" style={{ display: "block" }}>
      {/* 5. corpo robusto e peito branco */}
      <path d="M104 704 C104 556 190 484 300 484 C410 484 496 556 496 704 Z" fill="#C9A06A" />
      <path d="M300 484 C410 484 496 556 496 704 L402 704 C402 596 360 518 300 484 Z" fill="#A97F50" opacity="0.5" />
      <path d="M244 502 Q300 596 356 502 Q352 632 300 690 Q248 632 244 502 Z" fill="#F6EDE0" />

      {/* 6. colarinho verde-azulado com distintivo britânico */}
      <rect x="206" y="496" width="188" height="38" rx="19" fill="#2F6F6A" />
      <g transform="translate(300 515)">
        <rect x="-14" y="-10" width="28" height="20" rx="3" fill="#F6EDE0" />
        <path d="M0 -10 V10 M-14 0 H14" stroke="#B5532E" strokeWidth="5" />
        <path d="M-14 -10 L14 10 M14 -10 L-14 10" stroke="#B5532E" strokeWidth="2.5" opacity="0.8" />
      </g>

      {/* 7. orelhas pequenas e dobradas (ficam atrás da cabeça) */}
      <path d="M176 244 Q140 168 210 180 Q232 202 210 250 Z" fill="#A97F50" />
      <path d="M190 232 Q168 190 208 196 Q218 210 204 240 Z" fill="#B5532E" opacity="0.65" />
      <path d="M424 244 Q460 168 390 180 Q368 202 390 250 Z" fill="#A97F50" />
      <path d="M410 232 Q432 190 392 196 Q382 210 396 240 Z" fill="#B5532E" opacity="0.65" />

      {/* 8. cabeça larga e baixa, típica de buldogue */}
      <g transform={`translate(0 ${balanco}) rotate(0 300 315)`}>
        <ellipse cx="300" cy="315" rx="158" ry="142" fill="#C9A06A" />
        <path d="M300 182 C382 182 448 232 458 315 C452 250 388 204 300 204 Z" fill="#A97F50" opacity="0.4" />

        {/* 9. rugas da testa */}
        <path d="M206 272 Q232 250 258 270" stroke="#A97F50" strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M342 270 Q368 250 394 272" stroke="#A97F50" strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M276 246 Q300 232 324 246" stroke="#A97F50" strokeWidth="7" strokeLinecap="round" fill="none" />

        {/* 10. olhos */}
        <OlhoCartoon cx={246} cy={310} raio={16} olharX={olharX} piscar={piscar} />
        <OlhoCartoon cx={354} cy={310} raio={16} olharX={olharX} piscar={piscar} />

        {/* 11. focinho curto, branco, com queixudos */}
        <ellipse cx="300" cy="392" rx="106" ry="66" fill="#F6EDE0" />
        <ellipse cx="250" cy="416" rx="54" ry="40" fill="#EFE2D0" />
        <ellipse cx="350" cy="416" rx="54" ry="40" fill="#EFE2D0" />

        {/* 12. nariz escuro e chanfro */}
        <path d="M266 356 Q300 342 334 356 Q340 382 300 392 Q260 382 266 356 Z" fill="#2B2118" />
        <path d="M300 392 L300 410" stroke="#2B2118" strokeWidth="6" strokeLinecap="round" />

        {/* 13. boca falante por cima dos queixudos */}
        <BocaFalante x={300} y={420} largura={56} abertura={aberturaBoca} estilo="focinho" corLingua="#D97C82" />

        {/* 14. bochechas rosadas */}
        <circle cx="196" cy="372" r="18" fill="#D98C7A" opacity="0.35" />
        <circle cx="404" cy="372" r="18" fill="#D98C7A" opacity="0.35" />
      </g>
    </svg>
  );
};

/** Luninha (Luna) — salsicha MARROM de tom único, ficha FICHA-PERSONAGENS-HISTORINHA.md.
 *  Narradora padrão do canto; nunca trocar cor/raça nem criar personagem novo. */
export const AvatarSalsichaMarrom: React.FC<{ aberturaBoca: number; frame: number }> = ({ aberturaBoca, frame }) => {
  const piscar = calcularPiscar(frame, 104);                                 // 15. piscada
  const olharX = Math.sin(frame / 67 + 1.2) * 3;                             // 16. olhar
  const balanco = Math.sin(frame / 49 + 0.8) * 1.4;                          // 17. balanço

  return (
    <svg width="100%" height="100%" viewBox="0 0 600 704" style={{ display: "block" }}>
      {/* 18. peito e patinhas na borda inferior — LUNA é tom único, sem barriga clara */}
      <path d="M158 704 C158 566 214 494 300 494 C386 494 442 566 442 704 Z" fill="#8B5A3C" />
      <ellipse cx="232" cy="690" rx="44" ry="24" fill="#8B5A3C" />
      <ellipse cx="368" cy="690" rx="44" ry="24" fill="#8B5A3C" />

      {/* 19. bandana mostarda */}
      <path d="M214 516 L300 560 L386 516 L372 590 L300 622 L228 590 Z" fill="#D9A441" />
      <path d="M300 560 L300 622 L228 590 Z" fill="#B5532E" opacity="0.3" />

      {/* 20. orelhas longas e caídas (atrás da cabeça) */}
      <path d="M196 232 C142 250 128 386 172 446 C206 450 220 392 222 330 Z" fill="#6E4128" />
      <path d="M404 232 C458 250 472 386 428 446 C394 450 380 392 378 330 Z" fill="#6E4128" />
      <path d="M196 252 C160 274 152 374 180 416" stroke="#8B5A3C" strokeWidth="10" strokeLinecap="round" fill="none" opacity="0.6" />
      <path d="M404 252 C440 274 448 374 420 416" stroke="#8B5A3C" strokeWidth="10" strokeLinecap="round" fill="none" opacity="0.6" />

      {/* 21. cabeça alongada */}
      <g transform={`translate(0 ${balanco})`}>
        <ellipse cx="300" cy="305" rx="122" ry="146" fill="#8B5A3C" />
        <path d="M300 166 C368 166 416 226 422 305 C414 234 364 188 300 188 Z" fill="#6E4128" opacity="0.35" />

        {/* 22. olhos grandes */}
        <OlhoCartoon cx={252} cy={306} raio={17} olharX={olharX} piscar={piscar} />
        <OlhoCartoon cx={348} cy={306} raio={17} olharX={olharX} piscar={piscar} />

        {/* 23. sobrancelhas expressivas */}
        <path d="M228 272 Q252 258 276 272" stroke="#6E4128" strokeWidth="7" strokeLinecap="round" fill="none" />
        <path d="M324 272 Q348 258 372 272" stroke="#6E4128" strokeWidth="7" strokeLinecap="round" fill="none" />

        {/* 24. focinho da LUNA: mesmo tom marrom único, só sombreado mais escuro */}
        <ellipse cx="300" cy="384" rx="88" ry="60" fill="#94683F" />
        <ellipse cx="300" cy="352" rx="26" ry="18" fill="#2B2118" />
        <path d="M300 370 L300 386" stroke="#2B2118" strokeWidth="5" strokeLinecap="round" />

        {/* 25. boca falante */}
        <BocaFalante x={300} y={414} largura={54} abertura={aberturaBoca} estilo="focinho" corLingua="#D97C82" />

        {/* 26. sardas e bochechas */}
        <circle cx="212" cy="386" r="14" fill="#B5532E" opacity="0.28" />
        <circle cx="388" cy="386" r="14" fill="#B5532E" opacity="0.28" />
      </g>
    </svg>
  );
};
