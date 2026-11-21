/**
 * MANUAL — ParticulasEstacao.tsx
 * ==============================
 * O que faz
 * ---------
 * Camada de partículas do ar, uma para cada estação: pétalas de primavera,
 * poeira dourada de verão, folhas de outono, neve de inverno e brilhos do
 * retorno. Cada partícula tem posição, tamanho e velocidade determinísticos,
 * então o render é idêntico ao preview.
 *
 * Como anima
 * ----------
 * `useCurrentFrame()` + `interpolate()` sobre o módulo do tempo de vida: cada
 * partícula cai (ou sobe), gira e reinicia com loop suave.
 *
 * Performance
 * -----------
 * Máximo de 90 elementos SVG por cena. Acima disso o custo de pintura passa a
 * competir com o resto da composição na GTX 1060.
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";  // 1. frame + interpolação
import type { PaletaEstacao } from "./timelineQuatroEstacoes";

/** Hash determinístico: mesma semente sempre devolve o mesmo número 0..1. */
const semente = (valor: number): number => {
  const bruto = Math.sin(valor * 91.7 + 47.3) * 21783.5453;  // 2. hash trigonométrico
  return bruto - Math.floor(bruto);                          // 3. normaliza para 0..1
};

export const ParticulasEstacao: React.FC<{
  tipo: "petala" | "poeira" | "folha" | "neve" | "brilho";
  paleta: PaletaEstacao;
}> = ({ tipo }) => {   // paleta segue no tipo (quem chama passa), mas nenhuma cor dela depende aqui
  const frame = useCurrentFrame();                                   // 4. frame atual

  // --- configuração por tipo de partícula -----------------------------------
  const configuracao = {
    petala: { quantidade: 70, cor: "#f3b6c4", largura: 13, altura: 8, queda: 1.1 },           // 5. flor de cerejeira (spec 5); destaque e mostarda e nao serve para petala
    poeira: { quantidade: 80, cor: "#fff3c4", largura: 4, altura: 4, queda: -0.35 },        // 6. poeira sobe com o calor
    folha: { quantidade: 62, cor: "#d9822b", largura: 17, altura: 9, queda: 1.6 },          // 7. folhas caem rápido
    neve: { quantidade: 90, cor: "#f2efe9", largura: 7, altura: 7, queda: 0.85 },           // 8. branco sujo: nunca #ffffff puro
    brilho: { quantidade: 54, cor: "#ffe6b0", largura: 5, altura: 5, queda: -0.25 },        // 9. brilhos sobem
  }[tipo];

  return (
    <g>
      {Array.from({ length: configuracao.quantidade }, (_, indice) => {
        const baseX = semente(indice + 1) * 1980;                                  // 10. coluna fixa da partícula
        const desvio = Math.sin((frame + indice * 13) / 38 + indice) * 34;         // 11. balanço lateral
        const vida = 300 + semente(indice + 5) * 320;                              // 12. tempo de vida em frames
        const ciclo = (frame * configuracao.queda + semente(indice + 9) * vida) % vida;  // 13. posição no ciclo
        const progresso = ciclo / vida;                                            // 14. 0..1 dentro da vida
        const y = configuracao.queda > 0
          ? interpolate(progresso, [0, 1], [-80, 1160])                            // 15. caindo
          : interpolate(progresso, [0, 1], [1160, -80]);                           // 16. subindo
        const opacidade = interpolate(progresso, [0, 0.12, 0.85, 1], [0, 0.85, 0.8, 0]);  // 17. surge e some
        const giro = (frame + indice * 9) * (configuracao.queda > 0 ? 1.4 : 0.5);  // 18. rotação contínua
        const escala = 0.7 + semente(indice + 3) * 0.9;                            // 19. tamanho variado
        return (
          <ellipse
            key={`particula-${tipo}-${indice}`}
            cx={baseX + desvio}
            cy={y}
            rx={(configuracao.largura / 2) * escala}
            ry={(configuracao.altura / 2) * escala}
            fill={configuracao.cor}
            opacity={opacidade}
            transform={`rotate(${giro} ${baseX + desvio} ${y})`}                   // 20. gira em torno de si
          />
        );
      })}
    </g>
  );
};
