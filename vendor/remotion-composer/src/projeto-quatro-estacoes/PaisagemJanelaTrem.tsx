/**
 * MANUAL — PaisagemJanelaTrem.tsx
 * ===============================
 * O que faz
 * ---------
 * Desenha a paisagem vista pela janela do trem em cada estação, cem por cento em
 * SVG/CSS: céu em gradiente, sol com halo, nuvens, relevo em duas camadas, linha
 * de árvores, postes de telégrafo, leito do trilho e detalhes sazonais (flores,
 * folhas no chão, vilarejo com neve e fumaça).
 *
 * Como anima
 * ----------
 * Só `useCurrentFrame()` + `interpolate()` (regra de ouro do projeto). Nada de
 * `useFrame()` do React Three Fiber e nada de `Date.now()`: o mesmo frame gera
 * sempre o mesmo pixel, então preview e render batem.
 *
 * Parallax
 * --------
 * Cada camada anda com velocidade própria e volta ao início com módulo do
 * período de 1920 px, o que dá sensação de trem em movimento sem emenda visível.
 *
 * Props
 * -----
 * `paleta`    cores da estação
 * `particula` tipo de partícula do ar (delegada para ParticulasEstacao)
 * `saida`     0..1 progresso de saída da cena (escurece no fim)
 * `idCena`    sufixo dos ids de gradiente, para não colidir entre cenas
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";  // 1. frame atual + mapeamento linear
import type { PaletaEstacao } from "./timelineQuatroEstacoes";
import { ParticulasEstacao } from "./ParticulasEstacao";

/** Pseudoaleatório determinístico: mesma semente, mesmo resultado no render. */
const ruido = (semente: number): number => {
  const valor = Math.sin(semente * 127.1 + 311.7) * 43758.5453;  // 2. hash trigonométrico clássico
  return valor - Math.floor(valor);                               // 3. normaliza para 0..1
};

/** Gera o path de uma colina com período exato para o loop de parallax. */
const caminhoColina = (largura: number, base: number, altura: number, semente: number): string => {
  const passos = 8;                                              // 4. ondulações dentro do período
  const passo = largura / passos;                                // 5. largura de cada ondulação
  let d = `M 0 ${base}`;                                         // 6. começa na borda esquerda
  for (let i = 0; i < passos; i += 1) {                          // 7. percorre as ondulações
    const topo = base - altura * (0.45 + ruido(semente + i) * 0.55);  // 8. altura variável
    d += ` Q ${i * passo + passo / 2} ${topo} ${(i + 1) * passo} ${base}`;  // 9. curva quadrática
  }
  return `${d} L ${largura} 1080 L 0 1080 Z`;                    // 10. fecha no rodapé do quadro
};

/** Árvore simples (tronco + três copas) usada nas estações sem neve. */
const arvore = (x: number, base: number, tamanho: number, cor: string) => (
  <g key={`arvore-${x}`} transform={`translate(${x} ${base})`}>
    <rect x={-tamanho * 0.035} y={-tamanho * 0.42} width={tamanho * 0.07} height={tamanho * 0.42} fill={cor} opacity={0.9} />
    <ellipse cx={0} cy={-tamanho * 0.62} rx={tamanho * 0.28} ry={tamanho * 0.34} fill={cor} opacity={0.95} />
    <ellipse cx={-tamanho * 0.18} cy={-tamanho * 0.5} rx={tamanho * 0.2} ry={tamanho * 0.24} fill={cor} />
    <ellipse cx={tamanho * 0.18} cy={-tamanho * 0.52} rx={tamanho * 0.19} ry={tamanho * 0.22} fill={cor} />
  </g>
);

/** Pinheiro em três triângulos com neve no topo, usado no inverno. */
const pinheiro = (x: number, base: number, tamanho: number, cor: string, neve: string) => (
  <g key={`pinheiro-${x}`} transform={`translate(${x} ${base})`}>
    <polygon points={`0,${-tamanho} ${tamanho * 0.24},${-tamanho * 0.55} ${-tamanho * 0.24},${-tamanho * 0.55}`} fill={cor} />
    <polygon points={`0,${-tamanho * 0.78} ${tamanho * 0.29},${-tamanho * 0.32} ${-tamanho * 0.29},${-tamanho * 0.32}`} fill={cor} />
    <polygon points={`0,${-tamanho * 0.58} ${tamanho * 0.34},${-tamanho * 0.1} ${-tamanho * 0.34},${-tamanho * 0.1}`} fill={cor} />
    <polygon points={`0,${-tamanho} ${tamanho * 0.13},${-tamanho * 0.7} ${-tamanho * 0.13},${-tamanho * 0.7}`} fill={neve} opacity={0.85} />
    <polygon points={`0,${-tamanho * 0.78} ${tamanho * 0.16},${-tamanho * 0.5} ${-tamanho * 0.16},${-tamanho * 0.5}`} fill={neve} opacity={0.7} />
  </g>
);

export const PaisagemJanelaTrem: React.FC<{
  paleta: PaletaEstacao;
  particula: "petala" | "poeira" | "folha" | "neve" | "brilho";
  saida: number;
  idCena: string;
}> = ({ paleta, particula, saida, idCena }) => {
  const frame = useCurrentFrame();                                     // 11. frame atual da composição
  const idGradiente = `ceu-${idCena}`;                                 // 12. id único do gradiente
  const idHalo = `halo-${idCena}`;                                     // 13. id único do halo solar

  // --- deslocamentos de parallax (módulo 1920 fecham o loop) ----------------
  const deslocColinaLonge = -(frame * 0.6) % 1920;                     // 14. camada distante, quase parada
  const deslocColinaMeio = -(frame * 1.4) % 1920;                      // 15. camada média
  const deslocArvores = -(frame * 3.2) % 1920;                         // 16. árvores passando rápido
  const deslocTrilho = -(frame * 18) % 320;                            // 17. dormentes velozes (profundidade)

  // --- entrada e saída ------------------------------------------------------
  const entrada = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });          // 18. fade de entrada
  const escurecimento = interpolate(saida, [0, 1], [0, 0.55], { extrapolateLeft: "clamp" });   // 19. fecha a cena

  // --- sol ------------------------------------------------------------------
  const haloEscala = interpolate(Math.sin(frame / 46), [-1, 1], [0.94, 1.08]);   // 20. respiração do halo
  const posicaoSol = 260 + Math.sin(frame / 260) * 22;                           // 21. deriva lenta do sol

  // --- nuvens ---------------------------------------------------------------
  const nuvens = [0, 1, 2, 3].map((indice) => {                                  // 22. quatro nuvens
    const velocidade = 0.22 + indice * 0.06;                                     // 23. velocidades distintas
    const x = ((frame * velocidade + indice * 520) % 2300) - 190;                 // 24. loop horizontal
    const y = 110 + ruido(indice + 7) * 190;                                     // 25. altura por nuvem
    const escala = 0.7 + ruido(indice + 3) * 0.7;                                // 26. tamanho variado
    return (
      <g key={`nuvem-${indice}`} transform={`translate(${x} ${y}) scale(${escala})`} opacity={0.5}>
        <ellipse cx={0} cy={0} rx={120} ry={38} fill="#ffffff" />
        <ellipse cx={70} cy={8} rx={90} ry={28} fill="#ffffff" />
        <ellipse cx={-70} cy={10} rx={80} ry={24} fill="#ffffff" />
      </g>
    );
  });

  // --- árvores e pinheiros --------------------------------------------------
  const arvores = Array.from({ length: 16 }, (_, indice) => {                    // 27. 16 árvores no período
    const x = indice * 130 + ruido(indice + 15) * 70;                            // 28. espaçamento variado
    const tamanho = 150 + ruido(indice + 11) * 130;                              // 29. alturas diferentes
    return arvore(x, 752, tamanho, paleta.arvores);                              // 30. desenha a árvore
  });
  const pinheiros = Array.from({ length: 14 }, (_, indice) => {                  // 31. pinheiros do inverno
    const x = indice * 150 + ruido(indice + 21) * 60;
    const tamanho = 170 + ruido(indice + 31) * 130;
    return pinheiro(x, 764, tamanho, paleta.arvores, "#f4f9ff");
  });

  const ehInverno = particula === "neve";                                       // 32. detalhe sazonal: neve
  const ehOutono = particula === "folha";                                       // 33. folhas caídas
  const ehPrimavera = particula === "petala";                                   // 34. flores nos galhos

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 1920 1080"
      preserveAspectRatio="xMidYMid slice"
      style={{ position: "absolute", inset: 0, display: "block" }}
    >
      <defs>
        <linearGradient id={idGradiente} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={paleta.ceuTopo} />                        {/* 35. topo do céu */}
          <stop offset="62%" stopColor={paleta.ceuBase} opacity={0.95} />        {/* 36. meio do céu */}
          <stop offset="100%" stopColor="#ffffff" opacity={0.55} />              {/* 37. bruma no horizonte */}
        </linearGradient>
        <radialGradient id={idHalo}>
          <stop offset="0%" stopColor={paleta.sol} stopOpacity={0.95} />         {/* 38. núcleo do sol */}
          <stop offset="100%" stopColor={paleta.sol} stopOpacity={0} />          {/* 39. borda suave */}
        </radialGradient>
      </defs>

      {/* céu */}
      <rect width={1920} height={1080} fill={`url(#${idGradiente})`} />

      {/* halo + disco solar */}
      <circle cx={1420} cy={posicaoSol} r={280 * haloEscala} fill={`url(#${idHalo})`} />
      <circle cx={1420} cy={posicaoSol} r={62} fill={paleta.sol} opacity={0.92} />

      {/* nuvens */}
      {nuvens}

      {/* relevo distante */}
      <g transform={`translate(${deslocColinaLonge} 0)`}>
        <path d={caminhoColina(1920, 646, 110, 1)} fill={paleta.colinaLonge} opacity={0.75} />
        <path d={caminhoColina(1920, 646, 110, 1)} transform="translate(1920 0)" fill={paleta.colinaLonge} opacity={0.75} />
      </g>

      {/* relevo médio */}
      <g transform={`translate(${deslocColinaMeio} 0)`}>
        <path d={caminhoColina(1920, 722, 86, 5)} fill={paleta.colinaMeio} opacity={0.9} />
        <path d={caminhoColina(1920, 722, 86, 5)} transform="translate(1920 0)" fill={paleta.colinaMeio} opacity={0.9} />
      </g>

      {/* inverno: vilarejo distante antes da linha de pinheiros, com fumaça subindo */}
      {ehInverno && (
        <g transform={`translate(${deslocArvores * 0.55} 0)`} opacity={0.9}>
          {Array.from({ length: 7 }, (_, indice) => {                             // 40. casas do vilarejo
            const x = 120 + indice * 280 + ruido(indice + 12) * 60;
            const escala = 0.7 + ruido(indice + 17) * 0.35;                        // 41. tamanhos variados
            const fumaca = interpolate((frame + indice * 24) % 96, [0, 96], [0, -96]);  // 42. fumaça subindo
            return (
              <g key={`casa-${indice}`} transform={`translate(${x} 700) scale(${escala})`}>
                <rect x={-38} y={-46} width={76} height={46} fill="#5b6f85" />                     {/* 43. parede */}
                <polygon points="-48,-46 0,-86 48,-46" fill="#eef6ff" opacity={0.97} />            {/* 44. telhado com neve */}
                <rect x={22} y={-108} width={13} height={34} fill="#44566a" />                      {/* 45. chaminé */}
                <ellipse
                  cx={28}
                  cy={-112 + fumaca}
                  rx={13}
                  ry={20}
                  fill="#ffffff"
                  opacity={interpolate(fumaca, [-96, -6], [0, 0.45], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
                />
              </g>
            );
          })}
        </g>
      )}

      {/* linha de árvores / pinheiros */}
      <g transform={`translate(${deslocArvores} 0)`}>
        {ehInverno ? pinheiros : arvores}
        <g transform="translate(1920 0)">{ehInverno ? pinheiros : arvores}</g>
      </g>

      {/* primavera: flores na copa */}
      {ehPrimavera && (
        <g transform={`translate(${deslocArvores} 0)`} opacity={0.85}>
          {Array.from({ length: 70 }, (_, indice) => {                            // 46. pontos de flor
            const x = ruido(indice + 2) * 1920;
            const y = 500 + ruido(indice + 6) * 200;
            const raio = 4 + ruido(indice + 9) * 7;
            return <circle key={`flor-${indice}`} cx={x} cy={y} r={raio} fill="#f3b6c4" opacity={0.7} />;   // 47. flor de cerejeira na copa (nao mostarda)
          })}
        </g>
      )}

      {/* chão / leito do trilho */}
      <rect x={0} y={762} width={1920} height={318} fill={paleta.chao} />
      <rect x={0} y={762} width={1920} height={26} fill="#3b1f2b" opacity={0.12} />   {/* 48. sombra ameixa no leito: regra GBH e nunca #000 puro */}
      <g transform={`translate(${deslocTrilho} 0)`}>
        {Array.from({ length: 12 }, (_, indice) => (                               // 47. dormentes passando
          <rect key={`dorm-${indice}`} x={indice * 320} y={796} width={54} height={72} fill="#3b2d22" opacity={0.42} />
        ))}
      </g>
      <rect x={0} y={842} width={1920} height={9} fill="#ffffff" opacity={0.35} />
      <rect x={0} y={872} width={1920} height={16} fill="#ffffff" opacity={0.22} />

      {/* postes de telégrafo: vendem a velocidade do trem */}
      <g transform={`translate(${(deslocArvores * 1.7) % 960} 0)`} opacity={0.5}>
        {Array.from({ length: 4 }, (_, indice) => (                                  // 48. quatro postes no período
          <g key={`poste-${indice}`} transform={`translate(${indice * 960} 0)`}>
            <rect x={0} y={430} width={9} height={330} fill="#3a2c20" />              {/* 49. mastro */}
            <rect x={-34} y={452} width={78} height={7} fill="#3a2c20" />             {/* 50. travessa */}
            <path d="M0 452 Q 480 500 960 452" stroke="#3a2c20" strokeWidth={3} fill="none" opacity={0.75} />  {/* 51. fio */}
          </g>
        ))}
      </g>

      {/* outono: folhas no chão */}
      {ehOutono && (
        <g opacity={0.65}>
          {Array.from({ length: 40 }, (_, indice) => (                             // 52. tapete de folhas
            <ellipse key={`folha-chao-${indice}`} cx={ruido(indice + 4) * 1920} cy={790 + ruido(indice + 8) * 220}
              rx={11} ry={6} fill={indice % 2 === 0 ? "#c9741f" : "#e0a13a"} opacity={0.7} />
          ))}
        </g>
      )}

      {/* partículas no ar */}
      <ParticulasEstacao tipo={particula} paleta={paleta} />

      {/* tom da estação sobre a imagem, para dar unidade de cor */}
      <rect width={1920} height={1080} fill={paleta.destaque} opacity={0.07} />

      {/* escurecimento de entrada/saída */}
      <rect width={1920} height={1080} fill="#3b1f2b" opacity={escurecimento + (1 - entrada) * 0.65} />   {/* 49. escuro ameixa, nao preto puro */}
    </svg>
  );
};
