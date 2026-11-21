/**
 * MANUAL — AvatarEstilizadoQuatroEstacoes.tsx
 * ===========================================
 * O que faz
 * ---------
 * Desenha a apresentadora do vídeo "Quatro Estações na Janela do Trem" como
 * mascote flat 2D (cartoon), em SVG puro: rosto redondo, chapéu redondo, cachecol
 * mostarda, casaco verde-azulado e um passarinhho pousado na aba do chapéu.
 *
 * Por que vetor e não IA
 * ----------------------
 * A GTX 1060 (6 GB) e a CPU não precisam renderizar 163 s de vídeo por IA para um
 * boneco simples. SVG é resolvido pelo Chromium no próprio Remotion: custo quase
 * zero de GPU/VRAM, nitidez total em 1080p e controle exato de boca e olhos.
 *
 * Como anima
 * ----------
 * Tudo sai de `useCurrentFrame()` + `interpolate()` (sem relógio de parede, sem
 * `useFrame()` de Three.js):
 * - piscada a cada ~3,5 s (fecha e abre em 6 frames)
 * - boca falando por sincronização labial real (energia da narração, ver
 *   SincronizacaoLabial.ts), com aberturas e pausas que seguem a voz
 * - olhos olham de leve para os lados, sobrancelhas reagem à fala
 * - cabeça balança e respira; cachecol e chapéu acompanham o movimento
 *
 * Props
 * -----
 * - `falar`: quando false, a boca fica fechada (usado em respiro/transição).
 * - `escala`: multiplicador de tamanho aplicado no wrapper (1 = 600x704 px).
 * - `mostrarCartao`: desenha o cartão creme arredondado atrás do mascote.
 *
 * Saída
 * -----
 * Um `<div>` posicionado em `absolute` no canto inferior esquerdo, com entrada
 * suave e saída em fade. Consumido por `QuatroEstacoesJanelaTrem.tsx`.
 */

import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";  // 1. frame atual + interpolação determinística
import { aberturaBocaNoFrame } from "./SincronizacaoLabial";  // 1b. motor de sincronização labial real
import { VALORES_BECA_SINCRONIZACAO_LABIAL_CENA_05 } from "./dados/sincronizacao-labial-cena-05";  // 1c. aberturas por frame da cena 05

/** Paleta fixa do mascote, alinhada ao Grand Budapest do restante do vídeo. */
const COR = {
  cartao: "#F4E9D8",        // 2. creme do cartão de fundo
  cartaoBorda: "#2F6F6A",   // 3. contorno verde-azulado
  pele: "#E8B4A0",          // 4. pele quente
  peleSombra: "#D79A86",    // 5. sombra do queixo/pescoço
  traco: "#2B2118",         // 6. marrom quase preto (nunca preto puro)
  casaco: "#2F6F6A",        // 7. casaco verde-azulado
  casacoSombra: "#245550",  // 8. sombra do casaco
  cachecol: "#D9A441",      // 9. mostarda do cachecol
  cachecolSombra: "#B5532E",// 10. ferrugem da ponta do cachecol
  chapeu: "#B5532E",        // 11. terracota do chapéu
  faixa: "#2F6F6A",         // 12. faixa do chapéu
  bochecha: "#C4664F",      // 13. rubor das bochechas
  boca: "#5B2B23",          // 14. interior da boca
  lingua: "#C4695B",        // 15. língua
  passaro: "#F2C14E",       // 16. amarelo do passarinho
} as const;

export const AvatarEstilizadoQuatroEstacoes: React.FC<{
  falar?: boolean;
  escala?: number;
  mostrarCartao?: boolean;
}> = ({ falar = true, escala = 1, mostrarCartao = true }) => {
  const frame = useCurrentFrame();  // 17. frame local (o Sequence recorta a cena)

  // --- vida do mascote ------------------------------------------------------
  const respiracao = 1 + Math.sin(frame / 44) * 0.004;                       // 18. 0,4 % de respiração no corpo
  const balancoCabeca = Math.sin(frame / 58) * 1.8;                          // 19. ±1,8° de inclinação da cabeça
  const subidaCabeca = Math.sin(frame / 31) * 2;                             // 20. ±2 px de sobe-e-desce
  const balancoCachecol = Math.sin(frame / 40 + 0.6) * 5;                    // 21. ponta do cachecol oscila 5 px

  // --- piscada: ciclo de 105 frames, fechada por 6 frames --------------------
  const cicloPiscada = frame % 105;                                          // 22. posição no ciclo
  const aberturaOlho = interpolate(
    cicloPiscada,
    [0, 96, 100, 103, 105],
    [1, 1, 0.08, 0.08, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );                                                                          // 23. 1 aberto, 0.08 fechado

  // --- fala real: abertura dirigida pela energia da narração ----------------
  // Antes havia senoides fixas (pseudo-fala) e o boneco parecia não falar.
  // Agora a boca segue o áudio da cena 05, frame a frame, com interpolação.
  const aberturaBoca = falar
    ? aberturaBocaNoFrame(VALORES_BECA_SINCRONIZACAO_LABIAL_CENA_05, frame)   // 24. sincronização labial real
    : 0;                                                                     // 25. boca fechada quando calado

  // --- medidas da boca (variam com a abertura) ------------------------------
  const larguraBoca = 34 + aberturaBoca * 4;                                  // 27. boca alarga um pouco
  const alturaBoca = 3 + aberturaBoca * 28;                                   // 28. e abre até 31 px
  const curvaSorriso = 4 + aberturaBoca * 2;                                  // 29. canto da boca sobe
  const opacidadeSorriso = interpolate(aberturaBoca, [0, 0.18], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                          // 29b. sorriso aparece só com a boca fechada

  // --- olhar lateral discreto e sobrancelhas reativas ----------------------
  const olharX = Math.sin(frame / 73) * 3;                                    // 30. pupilas desviam ±3 px
  const olharY = Math.sin(frame / 47 + 2.1) * 1.2;                            // 31. e ±1,2 px na vertical
  const sobeSobrancelha = 1.5 + aberturaBoca * 4;                             // 32. sobrancelha acompanha a ênfase

  // --- entrada e saída do avatar na cena ------------------------------------
  const entrada = interpolate(frame, [0, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                          // 33. sobe e aparece em 22 frames
  const deslocamentoEntrada = interpolate(frame, [0, 26], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                          // 34. sobe 40 px ao entrar

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 92,                                                           // 35. canto inferior esquerdo
          bottom: 118,                                                        // 36. acima da margem da legenda
          width: 270 * escala,                                                 // 37. 270 px de largura no vídeo
          opacity: entrada,
          transform: `translateY(${deslocamentoEntrada}px)`,
        }}
      >
        <svg width="100%" viewBox="0 0 600 704" style={{ display: "block", overflow: "visible" }}>
          <defs>
            {/* sombra suave do cartão */}
            <filter id="sombra-avatar" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="16" stdDeviation="18" floodColor="#1a0f08" floodOpacity="0.38" />
            </filter>
          </defs>

          {/* 38. cartão creme arredondado (o mascote fica dentro dele) */}
          {mostrarCartao && (
            <g filter="url(#sombra-avatar)">
              <rect x="8" y="8" width="584" height="688" rx="46" fill={COR.cartao} />
              <rect x="8" y="8" width="584" height="688" rx="46" fill="none" stroke={COR.cartaoBorda} strokeOpacity="0.35" strokeWidth="4" />
            </g>
          )}

          {/* 39. grupo do corpo: respira sem mexer na cabeça */}
          <g transform={`translate(300 704) scale(1 ${respiracao}) translate(-300 -704)`}>
            {/* 40. ombros/casaco */}
            <path d="M96 704 C96 548 180 474 300 474 C420 474 504 548 504 704 Z" fill={COR.casaco} />
            <path d="M300 474 C420 474 504 548 504 704 L414 704 C414 590 372 520 300 474 Z" fill={COR.casacoSombra} opacity="0.55" />
            {/* 41. gola do casaco atrás do cachecol */}
            <path d="M232 492 L300 574 L368 492 L342 470 L300 518 L258 470 Z" fill={COR.cartao} opacity="0.9" />
          </g>

          {/* 42. cachecol mostarda com ponta solta balançando */}
          <g>
            <rect x="196" y="448" width="208" height="58" rx="29" fill={COR.cachecol} />
            <rect x="196" y="484" width="208" height="22" rx="11" fill={COR.cachecolSombra} opacity="0.25" />
            <g transform={`translate(${balancoCachecol} 0)`}>
              <rect x="330" y="470" width="42" height="116" rx="21" fill={COR.cachecol} />
              <rect x="330" y="548" width="42" height="20" fill={COR.cachecolSombra} />
              <rect x="330" y="584" width="42" height="16" rx="8" fill={COR.cachecolSombra} opacity="0.6" />
            </g>
          </g>

          {/* 43. grupo da cabeça: inclina, sobe e desce; pescoço fica parado */}
          <g transform={`translate(300 ${subidaCabeca}) rotate(${balancoCabeca} 0 330) translate(-300 0)`}>
            {/* 44. pescoço e sombra */}
            <rect x="262" y="430" width="76" height="60" rx="24" fill={COR.peleSombra} />

            {/* 45. cabeça */}
            <ellipse cx="300" cy="330" rx="150" ry="158" fill={COR.pele} />
            {/* 46. sombra inferior do rosto */}
            <path d="M170 380 C190 470 410 470 430 380 C420 440 380 470 300 470 C220 470 180 440 170 380 Z" fill={COR.peleSombra} opacity="0.35" />
            {/* 47. orelhas */}
            <ellipse cx="152" cy="336" rx="20" ry="28" fill={COR.pele} />
            <ellipse cx="448" cy="336" rx="20" ry="28" fill={COR.pele} />

            {/* 48. chapéu redondo com faixa */}
            <path d="M148 232 C148 112 452 112 452 232 Z" fill={COR.chapeu} />
            <path d="M300 126 C382 126 438 168 452 232 L414 232 C404 178 360 148 300 148 Z" fill="#9C4326" opacity="0.55" />
            <rect x="128" y="222" width="344" height="28" rx="14" fill={COR.faixa} />
            <rect x="128" y="222" width="344" height="8" rx="4" fill="#FFFFFF" opacity="0.18" />

            {/* 49. passarinho pousado na aba do chapéu */}
            <g transform={`translate(438 206) rotate(${8 + Math.sin(frame / 33) * 5})`}>
              <ellipse cx="0" cy="0" rx="30" ry="26" fill={COR.passaro} />
              <circle cx="22" cy="-10" r="17" fill={COR.passaro} />
              <path d="M36 -12 L54 -4 L36 2 Z" fill={COR.cachecolSombra} />
              <circle cx="27" cy="-14" r="3.2" fill={COR.traco} />
              <path d="M-26 4 Q -44 12 -30 24 Q -14 18 -8 8 Z" fill="#D9A441" />
            </g>

            {/* 50. sobrancelhas */}
            <path d={`M212 ${280 - sobeSobrancelha} Q 244 ${262 - sobeSobrancelha} 276 ${282 - sobeSobrancelha}`} stroke={COR.traco} strokeWidth="9" strokeLinecap="round" fill="none" />
            <path d={`M324 ${282 - sobeSobrancelha} Q 356 ${262 - sobeSobrancelha} 388 ${280 - sobeSobrancelha}`} stroke={COR.traco} strokeWidth="9" strokeLinecap="round" fill="none" />

            {/* 51. olhos com piscada por escala vertical */}
            <g transform={`translate(${olharX} ${olharY})`}>
              <g transform={`translate(245 316) scale(1 ${aberturaOlho}) translate(-245 -316)`}>
                <ellipse cx="245" cy="316" rx="15" ry="19" fill={COR.traco} />
                <circle cx="250" cy="309" r="5" fill={COR.cartao} />
              </g>
              <g transform={`translate(355 316) scale(1 ${aberturaOlho}) translate(-355 -316)`}>
                <ellipse cx="355" cy="316" rx="15" ry="19" fill={COR.traco} />
                <circle cx="360" cy="309" r="5" fill={COR.cartao} />
              </g>
            </g>

            {/* 52. nariz discreto */}
            <path d="M300 342 Q 292 360 306 364" stroke={COR.peleSombra} strokeWidth="7" strokeLinecap="round" fill="none" />

            {/* 53. bochechas */}
            <circle cx="214" cy="368" r="24" fill={COR.bochecha} opacity="0.32" />
            <circle cx="386" cy="368" r="24" fill={COR.bochecha} opacity="0.32" />

            {/* 54. boca: abre/fecha com a fala e mantém cantos sorrindo */}
            <path
              d={`M ${300 - larguraBoca} 392 Q 300 ${392 - curvaSorriso} ${300 + larguraBoca} 392 Q 300 ${392 + alturaBoca} ${300 - larguraBoca} 392 Z`}
              fill={COR.boca}
            />
            {aberturaBoca > 0.25 && (
              <ellipse cx="300" cy={392 + alturaBoca * 0.66} rx={larguraBoca * 0.55} ry={Math.max(1.5, alturaBoca * 0.2)} fill={COR.lingua} />
            )}
            {/* 55. lábio superior sempre desenhado */}
            <path d={`M ${300 - larguraBoca} 392 Q 300 ${388 - aberturaBoca * 3} ${300 + larguraBoca} 392`} stroke={COR.traco} strokeWidth="5" strokeLinecap="round" fill="none" />
            {/* 56. sorriso de repouso: some quando a boca abre para falar */}
            <path
              d="M 262 391 Q 300 407 338 391"
              stroke={COR.traco}
              strokeWidth="7"
              strokeLinecap="round"
              fill="none"
              opacity={opacidadeSorriso}
            />
          </g>
        </svg>
      </div>
    </AbsoluteFill>
  );
};
