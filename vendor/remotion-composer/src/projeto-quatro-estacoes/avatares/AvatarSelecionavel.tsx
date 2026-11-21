/**
 * MANUAL - AvatarSelecionavel.tsx
 * ===============================
 * O que faz
 * ---------
 * Escolhe um avatar do catálogo pelo id e o desenha num cartão pequeno,
 * com a boca já sincronizada com a amplitude da narração recebida por prop.
 *
 * Por que existe
 * --------------
 * O usuário quer trocar de boneco sem mexer no código da cena: basta uma prop
 * `idAvatar`. O mesmo componente serve ao vídeo final e ao catálogo de prévia.
 *
 * Props
 * -----
 * - `idAvatar`: chave do catálogo (buldogue-ingles, salsicha-marrom, ...).
 * - `aberturaBoca`: 0..1, calculado do RMS da narração no frame absoluto.
 * - `frameLocal`: frame dentro da Sequence (controla piscada e entrada).
 * - `estiloPosicao`: "canto-inferior-esquerdo" no vídeo; "centro" no catálogo.
 * - `mostrarNome`: legenda com o nome, usada só no catálogo.
 *
 * Regra
 * -----
 * Nenhum áudio é lido aqui. A boca obedece ao número recebido, que vem do
 * motor de sincronização labial (energia real da voz, frame a frame).
 */

import React from "react";
import { interpolate } from "remotion";                            // 1. entrada suave
import { obterDefinicaoAvatar } from "./registroAvatares";         // 2. catálogo

/** Cartão de avatar selecionável, pronto para canto da tela ou catálogo. */
export const AvatarSelecionavel: React.FC<{
  idAvatar: string;
  aberturaBoca: number;
  frameLocal: number;
  escala?: number;
  mostrarCartao?: boolean;
  mostrarNome?: boolean;
  estiloPosicao?: "canto-inferior-esquerdo" | "centro";
}> = ({
  idAvatar,
  aberturaBoca,
  frameLocal,
  escala = 1,
  mostrarCartao = true,
  mostrarNome = false,
  estiloPosicao = "canto-inferior-esquerdo",
}) => {
  const definicao = obterDefinicaoAvatar(idAvatar);                 // 3. resolve o boneco
  const ComponenteDaArte = definicao.Componente;                    // 4. componente SVG dele
  const entrada = interpolate(frameLocal, [0, 22], [0, 1], {       // 5. fade de chegada
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const deslocamento = interpolate(frameLocal, [0, 26], [40, 0], {  // 6. sobe 40 px
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const posicao = estiloPosicao === "centro"
    ? { position: "relative" as const, width: "100%" }              // 7. célula do catálogo
    : { position: "absolute" as const, left: 92, bottom: 118, width: 270 * escala };  // 8. canto da cena

  return (
    <div style={{ ...posicao, opacity: entrada, transform: `translateY(${deslocamento}px)`, pointerEvents: "none" }}>
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "600 / 704",                                 // 9. mantém a proporção do SVG
          borderRadius: 46,
          overflow: "hidden",
          background: mostrarCartao ? "#F4E9D8" : "transparent",
          border: mostrarCartao ? "3px solid rgba(47,111,106,0.45)" : "none",
          boxShadow: mostrarCartao ? "0 16px 40px rgba(0,0,0,0.40)" : "none",
        }}
      >
        {/* 10. arte: mesma boca sincronizada para todos os avatares */}
        <ComponenteDaArte aberturaBoca={aberturaBoca} frame={frameLocal + 30} />

        {/* 11. nome só no catálogo de escolha */}
        {mostrarNome && (
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              textAlign: "center",
              padding: "6px 4px",
              background: "rgba(244,233,216,0.92)",
              color: "#2B2118",
              fontFamily: "sans-serif",
              fontSize: 19,
              fontWeight: 700,
            }}
          >
            {definicao.nome}
          </div>
        )}
      </div>
    </div>
  );
};
