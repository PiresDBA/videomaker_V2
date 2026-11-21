/* ============================================================================
 * MANUAL — CartoesQuatroEstacoes.tsx
 * ----------------------------------------------------------------------------
 * As duas placas tipográficas do filme: a de abertura (sobre a primeira paisagem)
 * e a de fecho (depois da última fala). São o único lugar com texto grande.
 *
 * ESTILO
 *   Grand Budapest Hotel: placa centrada, filete duplo, marfim sobre bordô,
 *   caixa-alta espaçada em Space Grotesk; a linha poética em Playfair itálico.
 *   Nada de sombra difusa, nada de gradiente colorido: é papelaria, não é app.
 *
 * MOVIMENTO
 *   Entrada por fade + 8 px de subida em 0,5 s; saída em 0,6 s. O tempo vem de
 *   useCurrentFrame() dentro da Sequence de cada cartão, então o frame 0 aqui é
 *   o começo do cartão, não o do filme.
 * ========================================================================== */

import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

import { PALETA_BASE } from "./roteiro";

type PlacaProps = {
  /** Título principal, em caixa-alta automática. */
  titulo: string;
  /** Linha de apoio. */
  subtitulo: string;
  /** Texto pequeno acima do título (crédito ou capítulo). */
  sobretitulo?: string;
  /** Duração do cartão em frames, para calcular a saída. */
  duracaoFrames: number;
};

/** Placa de abertura: "AS QUATRO ESTAÇÕES". */
export const PlacaTitulo: React.FC<PlacaProps> = ({
  titulo,
  subtitulo,
  sobretitulo,
  duracaoFrames,
}) => {
  const frame = useCurrentFrame();

  // Entrada: 0 a 15 frames (0,5 s). Saída: últimos 18 frames (0,6 s).
  const entrada = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const saida = interpolate(frame, [duracaoFrames - 18, duracaoFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacidade = entrada * (1 - saida);
  const subida = interpolate(entrada, [0, 1], [8, 0]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        // Véu bordô translúcido: separa a placa da paisagem sem apagá-la.
        background: "rgba(58,42,33,0.28)",
        opacity: opacidade,
      }}
    >
      <div
        style={{
          transform: `translateY(${subida}px)`,
          padding: "54px 88px 46px",
          backgroundColor: PALETA_BASE.neve,
          border: `3px solid ${PALETA_BASE.bordo}`,
          outline: `9px solid ${PALETA_BASE.neve}`,
          boxShadow: "0 0 0 11px rgba(110,43,51,0.55), 0 24px 60px rgba(58,42,33,0.35)",
          textAlign: "center",
          minWidth: 900,
        }}
      >
        {sobretitulo && (
          <div
            style={{
              fontFamily: "Space Grotesk, system-ui, sans-serif",
              fontSize: 18,
              letterSpacing: "0.5em",
              color: PALETA_BASE.madeira,
              marginBottom: 22,
              textTransform: "uppercase",
            }}
          >
            {sobretitulo}
          </div>
        )}
        <div
          style={{
            fontFamily: "Space Grotesk, system-ui, sans-serif",
            fontSize: 82,
            fontWeight: 700,
            letterSpacing: "0.14em",
            color: PALETA_BASE.bordo,
            lineHeight: 1.08,
            textTransform: "uppercase",
          }}
        >
          {titulo}
        </div>
        <div
          style={{
            margin: "26px auto 24px",
            width: 320,
            height: 2,
            backgroundColor: PALETA_BASE.latao,
          }}
        />
        <div
          style={{
            fontFamily: "Playfair Display, Georgia, serif",
            fontStyle: "italic",
            fontSize: 34,
            color: PALETA_BASE.madeira,
          }}
        >
          {subtitulo}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Cartão de fecho: depois do inverno, a primavera. */
export const CartaoFinal: React.FC<{ duracaoFrames: number }> = ({
  duracaoFrames,
}) => {
  const frame = useCurrentFrame();
  const entrada = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // O fundo escurece até quase preto no último segundo.
  const escurecer = interpolate(frame, [duracaoFrames - 30, duracaoFrames], [0.55, 0.92], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background: `rgba(26,18,14,${escurecer})`,
      }}
    >
      <div style={{ textAlign: "center", opacity: entrada }}>
        <div
          style={{
            fontFamily: "Space Grotesk, system-ui, sans-serif",
            fontSize: 20,
            letterSpacing: "0.5em",
            color: PALETA_BASE.latao,
            textTransform: "uppercase",
            marginBottom: 28,
          }}
        >
          As Quatro Estações
        </div>
        <div
          style={{
            fontFamily: "Space Grotesk, system-ui, sans-serif",
            fontSize: 64,
            fontWeight: 700,
            letterSpacing: "0.12em",
            color: PALETA_BASE.neve,
            textTransform: "uppercase",
          }}
        >
          Até a próxima estação
        </div>
        <div
          style={{
            margin: "30px auto 26px",
            width: 260,
            height: 2,
            backgroundColor: PALETA_BASE.rosa,
          }}
        />
        <div
          style={{
            fontFamily: "Playfair Display, Georgia, serif",
            fontStyle: "italic",
            fontSize: 36,
            color: PALETA_BASE.marfim,
          }}
        >
          a janela continua aberta
        </div>
      </div>
    </AbsoluteFill>
  );
};
