/**
 * MANUAL - CenasHistoria.tsx
 * ==========================
 * O que faz
 * ---------
 * Desenhos de recorte 2D da historinha "Luninha e Fridóca no Espaço Sideral":
 * fundo estrelado, cabine da nave, biscoitos voadores, giro espacial, festa de
 * luzes, Terra, pouso e despedida.
 *
 * Por que existe
 * --------------
 * A versão original parecia slides. Aqui cada cena tem camadas com parallax,
 * personagens flutuando, luzes piscando, orelhas e rabos em movimento — tudo
 * por `useCurrentFrame()`, sem vídeo gerado por IA.
 *
 * Regra
 * -----
 * Nada de `useFrame()`: cada componente recebe `frame` (já vem de
 * `useCurrentFrame()` no pai) e calcula tudo de forma determinística.
 */

import React from "react";
import { interpolate } from "remotion";                       // 1. mapeamento determinístico
import { loadSpaceGrotesk } from "../lib/localFonts";          // 2. fonte local (sem rede)
import type { PaletaCena, TipoCena } from "./roteiroCenasHistoria";   // 3. tipos do roteiro
import { CaoEspacial } from "./CaoEspacial";                   // 4. personagens

const rotulo = loadSpaceGrotesk(["500", "700"]);               // 5. fonte dos títulos

/** Estrela determinística: mesma posição em todo render. */
const estrela = (indice: number): number => {
  const valor = Math.sin(indice * 127.1 + 311.7) * 43758.5453;  // 6. hash
  return valor - Math.floor(valor);                            // 7. 0..1
};

/** Campo de estrelas com brilho piscando. */
const CampoDeEstrelas: React.FC<{ frame: number; largura?: number; altura?: number; quantidade?: number }> = ({
  frame,
  largura = 1280,
  altura = 720,
  quantidade = 90,
}) => (
  <g>
    {Array.from({ length: quantidade }, (_, i) => {             // 8. estrelas fixas
      const x = estrela(i) * largura;                          // 9. posição X
      const y = estrela(i + 1000) * altura;                    // 10. posição Y
      const raio = 1.2 + estrela(i + 2000) * 3.2;              // 11. tamanho
      const brilho = 0.35 + 0.65 * Math.abs(Math.sin(frame / 26 + i));  // 12. pisca
      return <circle key={`estrela-${i}`} cx={x} cy={y} r={raio} fill="#FFF6D8" opacity={brilho} />;
    })}
  </g>
);

/** Fundo com gradiente, estrelas e um planeta. */
const FundoEspacial: React.FC<{ paleta: PaletaCena; frame: number; planeta?: boolean }> = ({ paleta, frame, planeta = true }) => (
  <g>
    <defs>
      <linearGradient id={`ceu-${paleta.ceuTopo}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={paleta.ceuTopo} />
        <stop offset="100%" stopColor={paleta.ceuBase} />
      </linearGradient>
    </defs>
    <rect width="1280" height="720" fill={`url(#ceu-${paleta.ceuTopo})`} />
    <CampoDeEstrelas frame={frame} />
    {planeta && (
      <g transform={`translate(1080 160) rotate(${Math.sin(frame / 90) * 6})`}>
        <circle r="74" fill="#3E7CB1" />
        <path d="M-74 0 A 74 74 0 0 0 74 0 Z" fill="#2A5B87" opacity="0.7" />
        <path d="M-50 -20 Q -20 -46 12 -28 Q 44 -12 52 12" stroke="#8FD3A0" strokeWidth="10" strokeLinecap="round" fill="none" opacity="0.8" />
        <circle cx="-24" cy="-34" r="12" fill="#FFFFFF" opacity="0.25" />
      </g>
    )}
  </g>
);

/** Painel da nave com luzinhas piscando. */
const PainelNave: React.FC<{ paleta: PaletaCena; frame: number; x: number; y: number }> = ({ paleta, frame, x, y }) => {
  const cores = ["#FF6B6B", "#FFD166", "#6BCB77", "#4DC9FF"];     // 13. luzes coloridas
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="300" height="150" rx="22" fill={paleta.painel} stroke="#8A7A63" strokeWidth="4" />
      {cores.map((cor, i) => (
        <circle
          key={`luz-${i}`}
          cx={40 + i * 56}
          cy={44}
          r="13"
          fill={cor}
          opacity={0.35 + 0.65 * Math.abs(Math.sin(frame / 12 + i * 1.4))}
        />
      ))}
      <rect x="30" y="82" width="110" height="34" rx="8" fill="#2B2118" opacity="0.85" />
      <path d="M40 110 L60 92 L80 104 L100 88 L130 110" stroke="#6BCB77" strokeWidth="4" fill="none" />
      <circle cx="205" cy="100" r="20" fill="#FFD166" stroke="#2B2118" strokeWidth="4" />
      <circle cx="205" cy="100" r="9" fill="#B5532E" />
    </g>
  );
};

/** Foguete simples para a abertura e o pouso. */
const Foguete: React.FC<{ x: number; y: number; escala?: number; frame: number; flame?: boolean }> = ({ x, y, escala = 1, frame, flame = true }) => {
  const chama = 26 + Math.sin(frame / 4) * 10;                    // 14. chama tremulando
  return (
    <g transform={`translate(${x} ${y}) scale(${escala})`}>
      {flame && (
        <path d={`M-22 96 Q 0 ${96 + chama * 2.4} 22 96 Q 0 ${96 + chama} -22 96 Z`} fill="#FFB347" />
      )}
      <path d="M-34 96 L-34 -60 Q 0 -120 34 -60 L34 96 Z" fill="#F4F1EA" stroke="#CFC8BA" strokeWidth="5" />
      <path d="M-34 20 L34 20" stroke="#B5532E" strokeWidth="10" />
      <circle cx="0" cy="-24" r="20" fill="#BFE3FF" stroke="#2F6F6A" strokeWidth="6" />
      <path d="M-34 96 L-62 128 L-34 118 Z" fill="#B5532E" />
      <path d="M34 96 L62 128 L34 118 Z" fill="#B5532E" />
    </g>
  );
};

/** Corações flutuando para a cena final. */
const Coracoes: React.FC<{ frame: number }> = ({ frame }) => (
  <g fill="#FFD166">
    {Array.from({ length: 12 }, (_, i) => {
      const x = 80 + estrela(i + 50) * 1120;
      const y = 90 + ((frame * 0.7 + i * 60) % 620);
      return (
        <path
          key={`coracao-${i}`}
          d="M0 6 C -10 -4 -24 4 -12 14 L0 22 L12 14 C24 4 10 -4 0 6 Z"
          transform={`translate(${x} ${y}) scale(${0.7 + estrela(i) * 0.8}) rotate(${Math.sin(frame / 20 + i) * 14})`}
          opacity={0.5 + 0.4 * Math.abs(Math.sin(frame / 24 + i))}
        />
      );
    })}
  </g>
);

/** Uma cena completa da historinha, conforme o tipo do roteiro. */
export const CenaHistoria: React.FC<{
  tipo: TipoCena;
  paleta: PaletaCena;
  frame: number;
}> = ({ tipo, paleta, frame }) => {
  const deriva = Math.sin(frame / 70) * 10;                       // 15. parallax suave

  return (
    <svg width="100%" height="100%" viewBox="0 0 1280 720" style={{ display: "block" }} preserveAspectRatio="xMidYMid slice">
      {tipo === "abertura" && (
        <>
          <FundoEspacial paleta={paleta} frame={frame} />
          <Foguete x={1080} y={260} escala={0.9} frame={frame} />
          <CaoEspacial especie="luninha" x={250} y={220} frame={frame} atraso={0} />
          <CaoEspacial especie="fridoca" x={760} y={190} escala={0.9} frame={frame} atraso={40} />
          <text x={640} y={470} textAnchor="middle" fill="#FFF6E8" fontSize={64} fontWeight={700} style={rotulo}>
            Luninha e Fridóca
          </text>
          <text x={640} y={530} textAnchor="middle" fill="#FFD166" fontSize={42} fontWeight={500} style={rotulo}>
            no espaço sideral
          </text>
        </>
      )}

      {(tipo === "cabine" || tipo === "cabine-flutuar" || tipo === "biscoitos" || tipo === "festa" || tipo === "terra") && (
        <>
          {/* 16. parede da cabine */}
          <rect width="1280" height="720" fill={paleta.painel} />
          <rect width="1280" height="720" fill={paleta.ceuBase} opacity="0.08" />
          {/* 17. janela grande com o espaço lá fora */}
          <defs>
            <clipPath id={`janela-${tipo}`}>
              <rect x="120" y="70" width="1040" height="500" rx="46" />
            </clipPath>
          </defs>
          <rect x="120" y="70" width="1040" height="500" rx="46" fill="#0B1030" stroke="#8A7A63" strokeWidth="16" />
          <g clipPath={`url(#janela-${tipo})`}>
            <FundoEspacial paleta={paleta} frame={frame} />
            {tipo === "terra" && (
              <g transform={`translate(640 320) scale(${1 + Math.sin(frame / 60) * 0.02})`}>
                <circle r="150" fill="#3E7CB1" />
                <path d="M-150 0 A 150 150 0 0 0 150 0 Z" fill="#2A5B87" opacity="0.7" />
                <path d="M-110 -50 Q -60 -100 20 -70 Q 90 -42 108 10" stroke="#8FD3A0" strokeWidth="22" strokeLinecap="round" fill="none" opacity="0.85" />
                <path d="M-90 60 Q -20 20 40 70" stroke="#8FD3A0" strokeWidth="14" strokeLinecap="round" fill="none" opacity="0.7" />
              </g>
            )}
          </g>
          {/* 18. painel e luzes */}
          <PainelNave paleta={paleta} frame={frame} x={930} y={600} />
          <rect x={80} y={600} width={330} height={100} rx={22} fill={paleta.painel} stroke="#8A7A63" strokeWidth={4} />
          <text x={245} y={664} textAnchor="middle" fill="#2B2118" fontSize={28} fontWeight={700} style={rotulo}>
            {tipo === "festa" ? "MUSICA!" : "PAINEL"}
          </text>

          {/* 19. personagens flutuando */}
          <g transform={`translate(${deriva} 0)`}>
            {tipo === "cabine" && (
              <>
                <CaoEspacial especie="luninha" x={330} y={330} frame={frame} />
                <CaoEspacial especie="fridoca" x={900} y={330} frame={frame} atraso={30} />
              </>
            )}
            {tipo === "cabine-flutuar" && (
              <>
                <CaoEspacial especie="luninha" x={380} y={270} frame={frame} deCabecaParaBaixo atraso={0} />
                <CaoEspacial especie="fridoca" x={820} y={340} frame={frame} deCabecaParaBaixo atraso={50} />
              </>
            )}
            {tipo === "biscoitos" && (
              <>
                <CaoEspacial especie="luninha" x={430} y={320} frame={frame} biscoito />
                <CaoEspacial especie="fridoca" x={820} y={360} frame={frame} atraso={45} />
                {Array.from({ length: 7 }, (_, i) => {
                  const x = 250 + estrela(i + 30) * 800;
                  const y = 150 + ((frame * 1.1 + i * 55) % 380);
                  return (
                    <path
                      key={`biscoito-${i}`}
                      d="M0 -14 Q -12 -22 -18 -12 Q -22 -2 -12 2 L 12 2 Q 22 -2 18 -12 Q 12 -22 0 -14 Z"
                      fill="#E0B26A"
                      stroke="#B5532E"
                      strokeWidth="3"
                      transform={`translate(${x} ${y}) rotate(${Math.sin(frame / 18 + i) * 30}) scale(${0.8 + estrela(i) * 0.5})`}
                    />
                  );
                })}
              </>
            )}
            {tipo === "festa" && (
              <>
                <CaoEspacial especie="luninha" x={420} y={330} frame={frame} girar />
                <CaoEspacial especie="fridoca" x={840} y={330} frame={frame} atraso={25} />
                {Array.from({ length: 16 }, (_, i) => {
                  const x = 180 + estrela(i + 70) * 920;
                  const y = 100 + ((frame * 1.4 + i * 48) % 460);
                  const cor = ["#FFD166", "#FFB3D9", "#8FE3FF", "#6BCB77"][i % 4];
                  return <circle key={`confete-${i}`} cx={x} cy={y} r={5 + estrela(i) * 5} fill={cor} opacity={0.85} />;
                })}
              </>
            )}
            {tipo === "terra" && (
              <>
                <CaoEspacial especie="luninha" x={470} y={330} frame={frame} atraso={0} />
                <CaoEspacial especie="fridoca" x={640} y={340} escala={1.05} frame={frame} atraso={20} />
              </>
            )}
          </g>
        </>
      )}

      {tipo === "estrelas" && (
        <>
          <FundoEspacial paleta={paleta} frame={frame} />
          <CaoEspacial especie="luninha" x={420} y={300} frame={frame} girar />
          <CaoEspacial especie="fridoca" x={820} y={320} frame={frame} girar atraso={30} />
          <text x={640} y={640} textAnchor="middle" fill="#FFF6E8" fontSize={46} fontWeight={700} style={rotulo}>
            girando entre as estrelas
          </text>
        </>
      )}

      {tipo === "pouso" && (
        <>
          <rect width="1280" height="720" fill={`url(#ceu-${paleta.ceuTopo})`} />
          <ellipse cx="220" cy="180" rx="180" ry="70" fill="#FFFFFF" opacity="0.9" />
          <ellipse cx="1020" cy="140" rx="220" ry="80" fill="#FFFFFF" opacity="0.85" />
          <ellipse cx="640" cy="700" rx="900" ry="180" fill="#6FBF73" />
          <ellipse cx="200" cy="720" rx="500" ry="140" fill="#5AA861" />
          <Foguete x={640} y={430} escala={1.1} frame={frame} flame={false} />
          <CaoEspacial especie="luninha" x={380} y={520} frame={frame} />
          <CaoEspacial especie="fridoca" x={900} y={520} frame={frame} atraso={35} />
          <text x={640} y={120} textAnchor="middle" fill="#0B3B2E" fontSize={46} fontWeight={700} style={rotulo}>
            pouso suave no gramado
          </text>
        </>
      )}

      {tipo === "final" && (
        <>
          <rect width="1280" height="720" fill={`url(#ceu-${paleta.ceuTopo})`} />
          <Coracoes frame={frame} />
          <CaoEspacial especie="luninha" x={420} y={330} frame={frame} />
          <CaoEspacial especie="fridoca" x={860} y={330} frame={frame} atraso={20} />
          <text x={640} y={560} textAnchor="middle" fill="#FFF6E8" fontSize={58} fontWeight={700} style={rotulo}>
            até a próxima aventura!
          </text>
          <text x={640} y={620} textAnchor="middle" fill="#FFD166" fontSize={36} fontWeight={500} style={rotulo}>
            tchau, tchau
          </text>
        </>
      )}
    </svg>
  );
};
