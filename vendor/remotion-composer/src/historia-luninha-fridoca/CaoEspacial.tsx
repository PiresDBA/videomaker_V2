/**
 * MANUAL - CaoEspacial.tsx
 * ========================
 * O que faz
 * ---------
 * Cachorrinho astronauta em recorte 2D (Luninha = salsicha; Fridóca = buldogue),
 * com roupa branca, capacete de vidro, orelhas balançando, rabo abanando,
 * flutuação e giros. É o personagem das cenas da historinha.
 *
 * Por que vetor
 * -------------
 * Animação de recorte/maquete pedida pelo usuário: camadas simples, movimento
 * por código, zero GPU. Combina com os avatares do catálogo (mesmas raças).
 *
 * Props
 * -----
 * - `especie`: "luninha" (LUNA, salsicha marrom) | "fridoca" (FRIDA, buldogue inglês)
 * - `x`, `y`, `escala`: posição e tamanho no quadro 1280x720
 * - `frame`: frame local da cena (piscada, flutuação)
 * - `girar`: giro contínuo (cena das estrelas)
 * - `deCabecaParaBaixo`: pose de gravidade zero
 * - `atraso`: dessincroniza o balanço entre os dois cães
 * - `biscoito`: desenha um biscoito na boca (cena dos biscoitos)
 */

import React from "react";
import { calcularPiscar } from "../projeto-quatro-estacoes/avatares/elementosComunsAvatar";  // 1. piscada compartilhada

/* 1b. Cores canônicas da ficha FICHA-PERSONAGENS-HISTORINHA.md — não inventar.
 * Luna: salsicha marrom de TOM ÚNICO (sem barriga/focinho claro).
 * Frida: buldogue fawn/branco com colarinho Union Jack. */
const COR_LUNA = "#8B5A3C";         // 2. marrom único de Luna (tom único)
const COR_FRIDA = "#C9A06A";        // 4. fawn de Frida
const COR_FRIDA_CLARA = "#F6EDE0";  // 5. branco de Frida (focinho/peito)
const COR_ORRELHA_FRIDA = "#A97F50";// 5b. orelha dobrada de Frida
const COR_UNIAO = "#2F6F6A";        // 5c. fundo do colarinho Union Jack
const COR_CRUZ = "#B5532E";         // 5d. cruz do Union Jack
const COR_TRAJE = "#F4F1EA";        // 6. traje branco quente
const COR_TRAJE_SOMBRA = "#CFC8BA"; // 7. sombra do traje
const COR_VIDRO = "#BFE3FF";        // 8. vidro do capacete
const COR_TRACO = "#2B2118";        // 9. contorno

/** Um cachorrinho astronauta pronto para flutuar na cena. */
export const CaoEspacial: React.FC<{
  especie: "luninha" | "fridoca";
  x: number;
  y: number;
  escala?: number;
  frame: number;
  girar?: boolean;
  deCabecaParaBaixo?: boolean;
  atraso?: number;
  biscoito?: boolean;
}> = ({
  especie,
  x,
  y,
  escala = 1,
  frame,
  girar = false,
  deCabecaParaBaixo = false,
  atraso = 0,
  biscoito = false,
}) => {
  const pelo = especie === "luninha" ? COR_LUNA : COR_FRIDA;             // 10. cor base
  const claro = especie === "luninha" ? COR_LUNA : COR_FRIDA_CLARA;      // 11. Luna sem tom claro (tom único)
  const quadro = frame + atraso;                                           // 12. relógio do cão
  const flutuacao = Math.sin(quadro / 34) * 12;                            // 13. sobe e desce
  const inclinacao = girar                                                // 14. giro contínuo ou balanço
    ? (quadro * 1.6) % 360
    : deCabecaParaBaixo
      ? 160 + Math.sin(quadro / 28) * 8
      : Math.sin(quadro / 46) * 7;
  const piscar = calcularPiscar(quadro, 100);                              // 15. piscada
  const orelha = Math.sin(quadro / 9) * (especie === "luninha" ? 14 : 9);  // 16. orelhas voando
  const rabo = Math.sin(quadro / 6) * 24;                                  // 17. rabo abanando
  const braco = Math.sin(quadro / 22) * 8;                                 // 18. patinha nadando

  return (
    <g transform={`translate(${x} ${y + flutuacao}) scale(${escala}) rotate(${inclinacao} 0 0)`}>
      {/* 19. rabo atrás do corpo */}
      <g transform={`translate(58 62) rotate(${rabo})`}>
        <path d="M0 0 Q 34 -10 40 -38" stroke={pelo} strokeWidth="16" strokeLinecap="round" fill="none" />
      </g>

      {/* 20. corpo do traje */}
      <ellipse cx="0" cy="72" rx="86" ry="72" fill={COR_TRAJE} />
      <path d="M0 4 C 62 4 86 36 86 72 C 86 118 52 142 0 142 C -52 142 -86 118 -86 72 C -86 36 -62 4 0 4 Z" fill={COR_TRAJE} />
      <path d="M-86 72 C -86 118 -52 142 0 142 L 0 4 C -62 4 -86 36 -86 72 Z" fill={COR_TRAJE_SOMBRA} opacity="0.5" />
      {/* 21. gola, botões, remendo de pata e colarinho Union Jack da Frida */}
      <ellipse cx="0" cy="16" rx="52" ry="16" fill={COR_TRAJE_SOMBRA} />
      <ellipse cx="0" cy="18" rx="46" ry="12" fill="#FFFFFF" />
      <circle cx="0" cy="70" r="7" fill={COR_UNIAO} />
      <path d="M58 84 l10 10 l-16 10 l-10 -10 Z" fill={COR_UNIAO} />
      <circle cx="62" cy="89" r="5" fill="#F4E9D8" />
      <circle cx="58" cy="94" r="2.4" fill="#F4E9D8" />
      <circle cx="66" cy="94" r="2.4" fill="#F4E9D8" />
      {especie === "fridoca" && (
        <g transform="translate(-64 60)">
          <rect width="30" height="20" rx="4" fill={COR_UNIAO} />
          <path d="M15 0 V20 M0 10 H30" stroke="#FFFFFF" strokeWidth="6" />
          <path d="M15 0 V20 M0 10 H30" stroke={COR_CRUZ} strokeWidth="3" />
          <path d="M0 0 L30 20 M30 0 L0 20" stroke="#FFFFFF" strokeWidth="3" opacity="0.7" />
        </g>
      )}

      {/* 22. patinhas */}
      <g transform={`translate(-58 58) rotate(${-braco})`}>
        <ellipse cx="0" cy="0" rx="18" ry="24" fill={COR_TRAJE} />
        <ellipse cx="0" cy="8" rx="14" ry="12" fill={claro} />
      </g>
      <g transform={`translate(58 58) rotate(${braco})`}>
        <ellipse cx="0" cy="0" rx="18" ry="24" fill={COR_TRAJE} />
        <ellipse cx="0" cy="8" rx="14" ry="12" fill={claro} />
      </g>

      {/* 23. cabeça dentro do capacete (Luna marrom único; Frida fawn) */}
      <g transform="translate(0 -22)">
        {/* orelhas: compridas na salsicha, dobradas no buldogue */}
        {especie === "luninha" ? (
          <>
            <g transform={`translate(-40 -34) rotate(${-18 + orelha})`}>
              <path d="M0 0 C -26 22 -26 92 -8 118 C 10 96 12 40 0 0 Z" fill={pelo} />
            </g>
            <g transform={`translate(40 -34) rotate(${18 - orelha})`}>
              <path d="M0 0 C 26 22 26 92 8 118 C -10 96 -12 40 0 0 Z" fill={pelo} />
            </g>
          </>
        ) : (
          <>
            <path d="M-56 -56 Q -86 -86 -50 -78 Q -36 -62 -44 -40 Z" fill={COR_ORRELHA_FRIDA} />
            <path d="M56 -56 Q 86 -86 50 -78 Q 36 -62 44 -40 Z" fill={COR_ORRELHA_FRIDA} />
          </>
        )}

        {/* 24. rosto */}
        <ellipse cx="0" cy="0" rx={especie === "luninha" ? 56 : 62} ry={especie === "luninha" ? 58 : 52} fill={pelo} />
        {especie === "fridoca" && (
          <>
            <path d="M-38 -30 Q -20 -40 -4 -30" stroke={COR_ORRELHA_FRIDA} strokeWidth="6" strokeLinecap="round" fill="none" />
            <path d="M4 -30 Q 20 -40 38 -30" stroke={COR_ORRELHA_FRIDA} strokeWidth="6" strokeLinecap="round" fill="none" />
          </>
        )}
        <ellipse cx="0" cy="20" rx={especie === "luninha" ? 32 : 40} ry={especie === "luninha" ? 24 : 28} fill={claro} />

        {/* 25. olhos que piscam */}
        <g transform={`translate(-22 -8) scale(1 ${piscar})`}>
          <ellipse cx="0" cy="0" rx="8" ry="10" fill={COR_TRACO} />
          <circle cx="3" cy="-4" r="3" fill="#FFFFFF" />
        </g>
        <g transform={`translate(22 -8) scale(1 ${piscar})`}>
          <ellipse cx="0" cy="0" rx="8" ry="10" fill={COR_TRACO} />
          <circle cx="3" cy="-4" r="3" fill="#FFFFFF" />
        </g>

        {/* 26. nariz e sorriso */}
        <ellipse cx="0" cy="12" rx="13" ry="9" fill={COR_TRACO} />
        <path d="M-12 28 Q 0 38 12 28" stroke={COR_TRACO} strokeWidth="4" strokeLinecap="round" fill="none" />

        {/* 27. biscoito na boca */}
        {biscoito && (
          <g transform="translate(0 34)">
            <path d="M-16 -6 Q -22 -14 -14 -16 Q -8 -18 -6 -12 L 6 -12 Q 8 -18 14 -16 Q 22 -14 16 -6 L 14 8 Q 22 10 14 14 Q 6 18 0 10 Q -6 18 -14 14 Q -22 10 -14 8 Z" fill="#E0B26A" />
          </g>
        )}
      </g>

      {/* 28. capacete: aro, vidro e brilho */}
      <circle cx="0" cy="-22" r="88" fill="none" stroke="#FFFFFF" strokeWidth="14" />
      <circle cx="0" cy="-22" r="80" fill={COR_VIDRO} opacity="0.22" />
      <path d="M-46 -74 A 62 62 0 0 1 22 -92" stroke="#FFFFFF" strokeWidth="9" strokeLinecap="round" fill="none" opacity="0.75" />
      <circle cx="0" cy="-22" r="88" fill="none" stroke={COR_TRACO} strokeOpacity="0.25" strokeWidth="3" />
    </g>
  );
};
