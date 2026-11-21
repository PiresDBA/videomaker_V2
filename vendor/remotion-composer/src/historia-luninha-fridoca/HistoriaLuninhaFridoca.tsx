/**
 * MANUAL - HistoriaLuninhaFridoca.tsx
 * ==================================
 * O que faz
 * ---------
 * Versão remodelada de "Luninha e Fridóca no Espaço Sideral": historinha
 * completa em recorte 2D animado, com o avatarzinho narrador no canto inferior
 * esquerdo e a legenda da fala embaixo.
 *
 * Por que existe
 * --------------
 * O vídeo original parecia slides e as crianças não prestavam atenção. Aqui a
 * cena inteira se move: gravidade zero, biscoitos voando, luzes piscando,
 * Terra, pouso. O avatar narrador acompanha a narração com lip-sync real.
 *
 * Layout
 * ------
 * - cena em tela cheia (1280x720)
 * - avatar narrador pequeno no canto inferior esquerdo
 * - legenda da fala no rodapé
 * - pontos de progresso no topo
 *
 * Áudio
 * -----
 * Por enquanto entra o áudio original do vídeo como PLACEHOLDER de timing. A
 * narração nova (vozes com emoção) entra quando o Especialista-Audio gerar.
 *
 * Regra
 * -----
 * Toda animação por `useCurrentFrame()` + interpolação; nenhum frame de IA.
 */

import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";  // 1. base
import { loadSpaceGrotesk } from "../lib/localFonts";                  // 2. fonte local
import { CENAS_HISTORIA, TOTAL_FRAMES_HISTORIA } from "./roteiroCenasHistoria";  // 3. roteiro
import { CenaHistoria } from "./CenasHistoria";                        // 4. desenhos
import { AvatarSelecionavel } from "../projeto-quatro-estacoes/avatares/AvatarSelecionavel";  // 5. narrador
import { aberturaBocaNoFrame } from "../projeto-quatro-estacoes/SincronizacaoLabial";  // 6. lip-sync
import { ABERTURAS_BOCA_HISTORIA } from "./dados/lipsyncHistoria";      // 7. trilha da historinha

const fonte = loadSpaceGrotesk(["500", "700"]);                        // 8. texto da legenda

/** Cena com frame local da Sequence (o desenho usa esse frame). */
const QuadroCena: React.FC<{ tipo: (typeof CENAS_HISTORIA)[number]["tipo"]; paleta: (typeof CENAS_HISTORIA)[number]["paleta"] }> = ({ tipo, paleta }) => {
  const frame = useCurrentFrame();                                     // 9. frame local da cena
  return <CenaHistoria tipo={tipo} paleta={paleta} frame={frame} />;    // 10. desenha
};

/** Versão remodelada da historinha, com avatar narrador no canto. */
export const HistoriaLuninhaFridoca: React.FC<{ idAvatar?: string }> = ({ idAvatar = "salsicha-marrom" }) => {
  const frameAbsoluto = useCurrentFrame();                             // 11. frame global
  const aberturaBoca = aberturaBocaNoFrame(ABERTURAS_BOCA_HISTORIA, frameAbsoluto);  // 12. boca real
  const cenaAtual = CENAS_HISTORIA.find(
    (cena) => frameAbsoluto >= cena.inicioFrames && frameAbsoluto < cena.inicioFrames + cena.duracaoFrames,
  ) ?? CENAS_HISTORIA[CENAS_HISTORIA.length - 1];                      // 13. cena do momento

  return (
    <AbsoluteFill style={{ backgroundColor: "#0B1030", fontFamily: "sans-serif" }}>
      {/* 14. uma Sequence por cena; o áudio é contínuo no topo */}
      <Audio src={staticFile("audio-historia-luninha-fridoca/narracao-original-placeholder.mp3")} />
      {CENAS_HISTORIA.map((cena) => (
        <Sequence
          key={cena.id}
          from={cena.inicioFrames}
          durationInFrames={cena.duracaoFrames}
          name={cena.id}
          layout="none"
        >
          <QuadroCena tipo={cena.tipo} paleta={cena.paleta} />
        </Sequence>
      ))}

      {/* 15. pontos de progresso das cenas */}
      <div style={{ position: "absolute", top: 18, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 10 }}>
        {CENAS_HISTORIA.map((cena, indice) => {
          const ativa = cenaAtual.id === cena.id;                        // 16. cena atual acesa
          return (
            <div
              key={`progresso-${cena.id}`}
              style={{
                width: 12,
                height: 12,
                borderRadius: 999,
                background: ativa ? "#FFD166" : "rgba(255,246,232,0.35)",
                boxShadow: ativa ? "0 0 14px #FFD166" : "none",
              }}
            />
          );
        })}
      </div>

      {/* 17. legenda da fala, recontada */}
      <div style={{ position: "absolute", left: 196, right: 30, bottom: 18, display: "flex", justifyContent: "center" }}>
        <div
          style={{
            maxWidth: 880,
            padding: "14px 28px",
            borderRadius: 18,
            background: "rgba(10, 8, 24, 0.72)",
            border: "1px solid rgba(255,209,102,0.45)",
            textAlign: "center",
            color: "#FFF6E8",
            fontSize: 27,
            lineHeight: 1.3,
            fontWeight: 500,
            ...fonte,
          }}
        >
          {cenaAtual.fala}
        </div>
      </div>

      {/* 18. avatarzinho narrador, pequeno, no canto inferior esquerdo */}
      <div style={{ position: "absolute", left: 20, bottom: 18, width: 164 }}>
        <AvatarSelecionavel
          idAvatar={idAvatar}
          aberturaBoca={aberturaBoca}
          frameLocal={frameAbsoluto}
          mostrarNome={false}
          estiloPosicao="centro"
        />
      </div>
    </AbsoluteFill>
  );
};

/** Metadados para o registro da Composition em Root.tsx. */
export const HISTORIA_METADADOS = {
  fps: 30,
  width: 1280,
  height: 720,
  durationInFrames: TOTAL_FRAMES_HISTORIA,
} as const;
