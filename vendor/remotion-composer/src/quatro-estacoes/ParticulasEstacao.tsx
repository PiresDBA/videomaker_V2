/* ============================================================================
 * MANUAL — ParticulasEstacao.tsx
 * ----------------------------------------------------------------------------
 * Partículas da paisagem: pétalas de primavera, poeira de calor do verão,
 * folhas do outono e neve do inverno. Tudo desenhado em CSS, sem imagem e sem
 * canvas, para o vídeo não depender de asset do ComfyUI nem custar VRAM.
 *
 * REGRA DE MOVIMENTO
 *   Nada de Math.random() em tempo de render: o mesmo frame tem de produzir
 *   sempre a mesma posição, senão o Remotion grava frames diferentes a cada
 *   passada e o render falha. As posições vêm de um hash da semente + índice.
 *   O tempo vem de useCurrentFrame(), nunca de Date.now().
 *
 * CONTRATO
 *   Recebe `progresso` (0..1 da cena) e `intensidade` (0..1, densidade).
 *   Não conhece áudio, texto ou paleta de cena: só cor e partícula.
 * ========================================================================== */

/** Tipo de partícula por estação. */
export type TipoParticula = "petala" | "poeira" | "folha" | "neve";

type Props = {
  /** Cor da partícula. */
  cor: string;
  /** Tipo de movimento e forma. */
  tipo: TipoParticula;
  /** 0 a 1: quanto da cena já passou. */
  progresso: number;
  /** 0 a 1: quantas partículas aparecem. */
  intensidade?: number;
};

/** Hash determinístico: mesma semente, mesmo número, em qualquer render. */
function aleatorio(semente: number): number {
  const x = Math.sin(semente * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/** Quantidade máxima de partículas na tela. */
const TOTAL = 54;

export const ParticulasEstacao: React.FC<Props> = ({
  cor,
  tipo,
  progresso,
  intensidade = 1,
}) => {
  const visiveis = Math.round(TOTAL * Math.max(0, Math.min(1, intensidade)));

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      {Array.from({ length: visiveis }).map((_, i) => {
        // Cada partícula tem uma velocidade e um deslocamento próprios.
        const base = aleatorio(i + 1);
        const velocidade = 0.25 + aleatorio(i + 77) * 0.55;
        const deriva = aleatorio(i + 133) * Math.PI * 2;
        const tamanho = 5 + aleatorio(i + 201) * 11;
        // A neve cai; a poeira sobe devagar; pétala e folha descem girando.
        const sentido = tipo === "poeira" ? -1 : 1;
        const ciclo = (base + progresso * velocidade * sentido * 3 + 10) % 1;
        const y = sentido === 1 ? ciclo * 108 : (1 - ciclo) * 108;
        // Deriva lateral em seno, para não cair em linha reta.
        const x =
          aleatorio(i + 307) * 100 +
          Math.sin(progresso * 6.2 + deriva) * (tipo === "neve" ? 2.5 : 6);
        const giro =
          tipo === "folha" || tipo === "petala"
            ? progresso * 220 * (aleatorio(i + 401) > 0.5 ? 1 : -1) + deriva * 20
            : 0;
        // A neve é um círculo; a pétala é uma pílula; a folha é um losango.
        const borderRadius =
          tipo === "neve" ? "50%" : tipo === "poeira" ? "50%" : "60% 40% 55% 45%";
        const altura = tipo === "neve" ? tamanho * 0.7 : tamanho * 1.5;
        const opacidade =
          tipo === "poeira" ? 0.35 : 0.55 + aleatorio(i + 509) * 0.4;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: tamanho,
              height: altura,
              backgroundColor: cor,
              borderRadius,
              opacity: opacidade,
              transform: `rotate(${giro}deg)`,
              // Pétala e folha ficam levemente desfocadas por serem menores.
              filter: tipo === "petala" ? "blur(0.4px)" : undefined,
            }}
          />
        );
      })}
    </div>
  );
};
