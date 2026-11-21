/**
 * MANUAL — LegendasEstacao.tsx
 * ===========================
 * O que faz
 * ---------
 * Mostra a legenda sincronizada da fala atual e o chip do nome da estação no
 * alto do quadro. A legenda entra com fade + subida curta, fica legível e sai
 * antes da próxima linha, sem competir com a xícara no canto inferior direito.
 *
 * Como anima
 * ----------
 * `useCurrentFrame()` + `interpolate()`. Cada linha recebe `inicio` e `duracao`
 * em frames locais (calculados em `timelineQuatroEstacoes.ts` proporcionais ao
 * texto), então a legenda acompanha o ritmo real da narração.
 *
 * Tipografia
 * ----------
 * Playfair Display itálico para a fala (voz narrativa) e Space Grotesk para o
 * chip — as duas famílias já vêm empacotadas com o compositor, sem rede.
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";  // 1. frame e interpolação
import { loadPlayfair, loadSpaceGrotesk } from "../lib/localFonts";  // 2. fontes locais (sem download)
import type { LegendaCronometrada, PaletaEstacao } from "./timelineQuatroEstacoes";

const vozNarradora = loadPlayfair("italic", ["400"]);  // 3. itálico da narração
const rotuloEstacao = loadSpaceGrotesk(["500", "700"]); // 4. fonte do chip

export const LegendasEstacao: React.FC<{
  legenda: LegendaCronometrada;
  titulo: string;
  indice: number;
  totalCenas: number;
  paleta: PaletaEstacao;
}> = ({ legenda, titulo, indice, totalCenas, paleta }) => {
  const frame = useCurrentFrame();                                   // 5. frame local da cena

  // --- janela de vida da legenda -------------------------------------------
  const inicio = legenda.inicio;                                     // 6. frame em que entra
  const fim = legenda.inicio + legenda.duracao;                      // 7. frame em que sai
  const opacidade = interpolate(frame, [inicio - 4, inicio + 8, fim - 8, fim], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                // 8. fade curto nas duas pontas
  const deslocamento = interpolate(frame, [inicio - 4, inicio + 12], [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                // 9. sobe 16 px ao entrar

  // --- chip do título entra uma vez no começo da cena ----------------------
  const entradaChip = interpolate(frame, [6, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }); // 10. chip aparece
  const saidaChip = interpolate(frame, [150, 186], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });  // 11. e se retira

  return (
    <>
      {/* chip: estação atual + contador */}
      <div
        style={{
          position: "absolute",
          top: 140,
          left: 250,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "12px 22px",
          borderRadius: 999,
          background: "rgba(20, 12, 8, 0.55)",
          border: `1px solid ${paleta.destaque}66`,
          backdropFilter: "blur(6px)",
          opacity: entradaChip * saidaChip,
          transform: `translateY(${(1 - entradaChip) * 12}px)`,
          ...rotuloEstacao,
          fontSize: 26,
          letterSpacing: 4,
          textTransform: "uppercase",
          color: "#fdf6ec",
          fontWeight: 500,
        }}
      >
        <span style={{ width: 10, height: 10, borderRadius: 999, background: paleta.destaque, display: "block" }} />
        {titulo}
        <span style={{ opacity: 0.55, fontSize: 20, letterSpacing: 2 }}>
          {String(indice + 1).padStart(2, "0")} / {String(totalCenas).padStart(2, "0")}
        </span>
      </div>

      {/* legenda da fala atual */}
      <div
        style={{
          position: "absolute",
          bottom: 44,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: opacidade,
          transform: `translateY(${deslocamento}px)`,
          padding: "0 120px",
        }}
      >
        <div
          style={{
            maxWidth: 1180,
            textAlign: "center",
            padding: "18px 44px",
            borderRadius: 20,
            background: "linear-gradient(180deg, rgba(16, 10, 6, 0.10), rgba(16, 10, 6, 0.42))",
            boxShadow: "0 18px 50px rgba(0,0,0,0.35)",
          }}
        >
          <div
            style={{
              ...vozNarradora,
              fontSize: legenda.texto.length > 78 ? 40 : 46,
              lineHeight: 1.28,
              color: "#fff8ef",
              textShadow: "0 2px 14px rgba(0,0,0,0.65)",
            }}
          >
            {legenda.texto}
          </div>
        </div>
      </div>
    </>
  );
};
