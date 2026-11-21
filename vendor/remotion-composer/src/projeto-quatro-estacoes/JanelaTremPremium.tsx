/**
 * MANUAL — JanelaTremPremium.tsx
 * ==============================
 * O que faz
 * ---------
 * Desenha a "camera" do vídeo: a moldura da janela do trem, o interior do vagão
 * (parede quente, cortina, reflexo no vidro) e a xícara de café com vapor no
 * primeiro plano. Fica por cima da paisagem, criando profundidade.
 *
 * Como anima
 * ----------
 * `useCurrentFrame()` + `interpolate()`: o vapor sobe em ciclos, o reflexo do
 * vidro desliza devagar, a cortina balança de leve e a xícara tem uma micro
 * respiração (0,5 % de escala) para não parecer imagem colada.
 *
 * Props
 * -----
 * `paleta`  cores da estação (tinge o reflexo e a luz do vagão)
 * `quadro`  frame local da cena (para animar sem depender do frame global)
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";  // 1. frame atual e mapeamento
import type { PaletaEstacao } from "./timelineQuatroEstacoes";

export const JanelaTremPremium: React.FC<{
  paleta: PaletaEstacao;
  idCena: string;
}> = ({ paleta, idCena }) => {
  const frame = useCurrentFrame();                                          // 2. frame da cena (Sequence local)

  // --- animações do primeiro plano ----------------------------------------
  const balancoCortina = Math.sin(frame / 54) * 6;                          // 3. cortina oscila 6 px
  const brilhoVidro = interpolate((frame * 1.6) % 900, [0, 900], [-320, 1980]);  // 4. reflexo varre o vidro
  const respiracaoXicara = interpolate(Math.sin(frame / 72), [-1, 1], [0.995, 1.005]); // 5. micro vida na xícara

  // --- vapor: três colunas com fases distintas ----------------------------
  const colunasVapor = [0, 1, 2].map((indice) => {
    const ciclo = (frame * 0.9 + indice * 34) % 120;                        // 6. ciclo de 120 frames
    const subida = interpolate(ciclo, [0, 120], [0, -120]);                 // 7. sobe 120 px
    const opacidade = interpolate(ciclo, [0, 30, 90, 120], [0, 0.5, 0.35, 0]); // 8. aparece e dissolve
    const curva = Math.sin((frame + indice * 40) / 26) * 12;                // 9. serpenteia
    return (
      <path
        key={`vapor-${indice}`}
        d={`M ${-26 + indice * 26} 2 q ${curva} -34 ${curva * 0.4} -64 q ${-curva} -32 ${curva * 0.6} -66`}
        stroke="#ffffff"
        strokeWidth={8}
        strokeLinecap="round"
        fill="none"
        opacity={opacidade}
        transform={`translate(0 ${subida})`}                                // 10. deslocamento vertical do ciclo
      />
    );
  });

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 1920 1080"
      preserveAspectRatio="xMidYMid slice"
      style={{ position: "absolute", inset: 0, display: "block" }}
    >
      <defs>
        {/* parede interna do vagão: madeira quente com luz vinda da janela */}
        <linearGradient id={`parede-${idCena}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2a1a12" />
          <stop offset="45%" stopColor="#4a2f1f" />
          <stop offset="100%" stopColor="#22140e" />
        </linearGradient>
        {/* moldura metálica com brilho */}
        <linearGradient id={`moldura-${idCena}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#d9c39a" />
          <stop offset="28%" stopColor="#8d6f47" />
          <stop offset="60%" stopColor="#c9ab7e" />
          <stop offset="100%" stopColor="#6b5232" />
        </linearGradient>
        {/* reflexo diagonal do vidro */}
        <linearGradient id={`reflexo-${idCena}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={paleta.luzJanela} stopOpacity={0} />
          <stop offset="50%" stopColor={paleta.luzJanela} stopOpacity={0.14} />
          <stop offset="100%" stopColor={paleta.luzJanela} stopOpacity={0} />
        </linearGradient>
        {/* vinheta interna do vagão */}
        <radialGradient id={`vinheta-${idCena}`} cx="50%" cy="46%" r="72%">
          <stop offset="55%" stopColor="#000000" stopOpacity={0} />
          <stop offset="100%" stopColor="#000000" stopOpacity={0.55} />
        </radialGradient>
      </defs>

      {/* parede do vagão (fora da janela) */}
      <path
        d="M0 0 H1920 V1080 H0 Z M180 96 H1740 V888 H180 Z"
        fill={`url(#parede-${idCena})`}
        fillRule="evenodd"                                                   // 11. recorta o buraco da janela
      />

      {/* brilho quente na parede, vindo da janela */}
      <rect x={0} y={0} width={1920} height={1080} fill={paleta.luzJanela} opacity={0.06} />

      {/* moldura da janela: anel vazado, o vidro fica livre para a paisagem */}
      <path
        d="M164 80 H1756 V904 H164 Z M196 112 H1724 V872 H196 Z"
        fill={`url(#moldura-${idCena})`}
        fillRule="evenodd"
      />
      <path
        d="M196 112 H1724 V872 H196 Z"
        fill="none"
        stroke="#000000"
        strokeOpacity={0.35}
        strokeWidth={6}
      />
      <path
        d="M164 80 H1756 V904 H164 Z"
        fill="none"
        stroke="#000000"
        strokeOpacity={0.28}
        strokeWidth={4}
      />

      {/* montante central fino, marca de janela de trem */}
      <rect x={950} y={112} width={14} height={760} fill={`url(#moldura-${idCena})`} opacity={0.9} />
      <rect x={950} y={112} width={4} height={760} fill="#000000" opacity={0.22} />

      {/* puxador metálico sobre a moldura lateral direita */}
      <rect x={1726} y={470} width={20} height={90} rx={10} fill="#c9ab7e" />
      <rect x={1730} y={478} width={5} height={74} rx={2} fill="#ffffff" opacity={0.5} />

      {/* reflexo que varre o vidro */}
      <g clipPath={`url(#recorte-vidro-${idCena})`}>
        <rect x={brilhoVidro} y={-200} width={170} height={1300} fill={`url(#reflexo-${idCena})`} transform="rotate(18)" />
      </g>
      <clipPath id={`recorte-vidro-${idCena}`}>
        <rect x={196} y={112} width={1528} height={760} rx={18} />
      </clipPath>

      {/* cortina da esquerda balançando */}
      <g transform={`translate(${balancoCortina} 0)`}>
        <path
          d="M120 -20 C 210 180, 150 360, 250 520 C 300 700, 200 860, 300 1100 L -40 1100 L -40 -20 Z"
          fill="#7a2f28"
          opacity={0.92}
        />
        <path d="M150 -20 C 230 220, 170 420, 255 560 C 300 720, 215 880, 300 1100 L 200 1100 C 140 880, 210 700, 140 520 C 90 360, 120 180, 60 -20 Z" fill="#8f3a31" opacity={0.85} />
      </g>

      {/* xícara de café no primeiro plano */}
      <g transform={`translate(1658 966) scale(${respiracaoXicara})`}>
        {colunasVapor}
        <ellipse cx={0} cy={34} rx={132} ry={22} fill="#000000" opacity={0.4} />            {/* 12. sombra da xícara */}
        <ellipse cx={0} cy={24} rx={118} ry={28} fill="#efe1cb" />                          {/* 13. pires */}
        <ellipse cx={0} cy={20} rx={82} ry={18} fill="#dccbb0" opacity={0.7} />             {/* 14. covinha do pires */}
        <path d="M-70 0 L-56 74 Q 0 100 56 74 L 70 0 Z" fill="#fbf6ee" />                    {/* 15. corpo da xícara */}
        <path d="M-70 0 L-56 74 Q -20 88 0 90 L 0 0 Z" fill="#ffffff" opacity={0.45} />      {/* 16. luz lateral */}
        <ellipse cx={0} cy={0} rx={70} ry={18} fill="#5b3721" />                             {/* 17. café */}
        <ellipse cx={-16} cy={-4} rx={24} ry={6} fill="#8a5a34" opacity={0.7} />             {/* 18. brilho no café */}
        <path d="M68 14 q 42 6 34 34 q -8 28 -46 20" stroke="#fbf6ee" strokeWidth={13} fill="none" strokeLinecap="round" />  {/* 19. alça */}
        <path d="M-70 0 q 70 22 140 0" stroke="#ffffff" strokeOpacity={0.55} strokeWidth={5} fill="none" />                 {/* 20. borda iluminada */}
      </g>

      {/* vinheta final: fecha as bordas do quadro */}
      <rect width={1920} height={1080} fill={`url(#vinheta-${idCena})`} />
    </svg>
  );
};
