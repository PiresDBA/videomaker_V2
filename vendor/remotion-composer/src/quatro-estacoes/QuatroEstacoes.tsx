/* ============================================================================
 * MANUAL — QuatroEstacoes.tsx
 * ----------------------------------------------------------------------------
 * Composição principal do vídeo "As Quatro Estações" (Grand Budapest Hotel,
 * janela do trem). É o alvo de render do Dev-Motion-QA e o contrato que os
 * outros bots preenchem.
 *
 * ESTRUTURA (uma <Sequence> por cena, sem cortes dentro da cena)
 *   <Sequence from=0                       duracao=72f>   PlacaTitulo
 *   <Sequence from=0                       duracao=764f>  Cena I   — Primavera
 *   <Sequence from=815                     duracao=1173f> Cena II  — Verão
 *   <Sequence from=2036                    duracao=719f>  Cena III — Outono
 *   <Sequence from=2804                    duracao=707f>  Cena IV  — Inverno
 *   <Sequence from=3561                    duracao=450f>  Cena V   — Retorno
 *   <Sequence from=4146                    duracao=135f>  CartaoFinal
 *   Os números acima são a tabela de 2026-11-16; a autoridade é
 *   timeline.generated.ts, que o gerador reescreve quando o áudio muda.
 *
 * ÁUDIO
 *   Cada cena toca seu próprio mp3 (cena-01..05) dentro da Sequence, então o
 *   áudio acompanha a imagem sem offset manual. O silêncio de 0,5 s entre cenas
 *   está embutido na linha de tempo.
 *
 * O QUE AINDA NÃO ESTÁ LIGADO (de propósito)
 *   - Texturas do ComfyUI: entram por `usarTexturas` (desligado até existirem).
 *   - Cena Three.js do Dev-3D-Craft: substitui o grupo de paisagem quando
 *     estiver pronto; hoje o CSS/SVG segura o plano.
 *   - Trilha/SFX: entram como camada de áudio opcional no Dev-Motion-QA.
 * ========================================================================== */

import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { loadPlayfair, loadSpaceGrotesk } from "../lib/localFonts";
import { resolveAsset } from "../lib/resolveAsset";
import { CartaoFinal, PlacaTitulo } from "./CartoesQuatroEstacoes";
import {
  CENAS,
  QUADRO,
  TEXTURAS,
  type FalaNaTimeline,
} from "./roteiro";
import { TIMELINE } from "./timeline.generated";
import { VagaoJanela } from "./VagaoJanela";

/** Fontes empacotadas no compositor; carregadas uma vez por bundle. */
const { fontFamily: familiaTitulo } = loadSpaceGrotesk(["400", "700"]);
const { fontFamily: familiaPoetica } = loadPlayfair("italic", ["400"]);

export type QuatroEstacoesProps = {
  /** Usa os fundos pintados do ComfyUI (public/assets/texturas). */
  usarTexturas?: boolean;
  /** Mostra a fala atual em legenda. Desligado: a narração já carrega o texto. */
  mostrarLegendas?: boolean;
};

/** Frames dos cartões derivados da timeline, não escritos à mão. */
const FRAMES_CARTAO_TITULO = Math.round(
  QUADRO.cartaoTituloSegundos * QUADRO.fps
);
const FRAMES_CARTAO_FINAL = Math.round(QUADRO.cartaoFinalSegundos * QUADRO.fps);

/**
 * Legenda opcional: mostra a fala cujo intervalo contém o instante atual.
 * O instante é absoluto (início da cena + frame local), porque a Sequence
 * reinicia o frame em zero.
 */
const LegendaCena: React.FC<{
  falas: FalaNaTimeline[];
  inicioCenaSegundos: number;
}> = ({ falas, inicioCenaSegundos }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const instante = inicioCenaSegundos + frame / fps;

  // A última fala que já começou é a que está sendo dita.
  const atual = [...falas]
    .reverse()
    .find((fala) => instante >= fala.inicioSegundos - 0.15);

  if (!atual) return null;

  // Fade curto na troca de fala, para não piscar.
  const opacidade = interpolate(
    instante,
    [atual.inicioSegundos - 0.15, atual.inicioSegundos + 0.15],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 96,
        display: "flex",
        justifyContent: "center",
        opacity: opacidade,
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          padding: "14px 26px",
          backgroundColor: "rgba(26,18,14,0.62)",
          borderRadius: 4,
          fontFamily: familiaPoetica,
          fontStyle: "italic",
          fontSize: 38,
          lineHeight: 1.3,
          color: "#F8F5ED",
          textAlign: "center",
        }}
      >
        {atual.texto}
      </div>
    </div>
  );
};

export const QuatroEstacoes: React.FC<QuatroEstacoesProps> = ({
  usarTexturas = false,
  mostrarLegendas = false,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Fade final de 24 frames (0,8 s), por cima de tudo, inclusive do cartão.
  const fadeFinal = interpolate(
    frame,
    [durationInFrames - 24, durationInFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#1A120E", fontFamily: familiaTitulo }}>
      {/* Uma Sequence por cena: imagem + áudio + legenda opcional. */}
      {TIMELINE.cenas.map((cenaTimeline) => {
        // A descrição narrativa (título, numeral, estação) vem do roteiro.
        const roteiro = CENAS.find((cena) => cena.id === cenaTimeline.id);
        if (!roteiro) {
          throw new Error(
            `timeline.generated.ts tem ${cenaTimeline.id}, mas roteiro.ts não. Rode o gerador.`
          );
        }
        const segundos = cenaTimeline.duracaoSegundos;

        return (
          <Sequence
            key={cenaTimeline.id}
            from={cenaTimeline.inicioFrame}
            durationInFrames={cenaTimeline.duracaoFrames}
            name={`${roteiro.numeral} ${roteiro.titulo}`}
          >
            <CenaComAudio
              id={cenaTimeline.id}
              audio={cenaTimeline.audio}
              estacao={roteiro.estacao}
              titulo={roteiro.titulo}
              numeral={roteiro.numeral}
              segundos={segundos}
              duracaoFrames={cenaTimeline.duracaoFrames}
              falas={cenaTimeline.falas}
              inicioCenaSegundos={cenaTimeline.inicioSegundos}
              usarTexturas={usarTexturas}
              mostrarLegendas={mostrarLegendas}
            />
          </Sequence>
        );
      })}

      {/* Placa de abertura, sobre a primeira paisagem. */}
      <Sequence
        from={0}
        durationInFrames={FRAMES_CARTAO_TITULO}
        name="Placa de título"
      >
        <PlacaTitulo
          titulo="As Quatro Estações"
          subtitulo="uma viagem pela janela do trem"
          sobretitulo="um filme de bolso"
          duracaoFrames={FRAMES_CARTAO_TITULO}
        />
      </Sequence>

      {/* Cartão de fecho, depois da última fala. */}
      <Sequence
        from={TIMELINE.totalFrames - FRAMES_CARTAO_FINAL}
        durationInFrames={FRAMES_CARTAO_FINAL}
        name="Cartão final"
      >
        <CartaoFinal duracaoFrames={FRAMES_CARTAO_FINAL} />
      </Sequence>

      {/* Fade final. */}
      <AbsoluteFill
        style={{ backgroundColor: "#000", opacity: fadeFinal, pointerEvents: "none" }}
      />
    </AbsoluteFill>
  );
};

/** Cena completa: cenário, áudio da narração e legenda opcional. */
const CenaComAudio: React.FC<{
  id: string;
  audio: string;
  estacao: Parameters<typeof VagaoJanela>[0]["estacao"];
  titulo: string;
  numeral: string;
  segundos: number;
  duracaoFrames: number;
  falas: FalaNaTimeline[];
  inicioCenaSegundos: number;
  usarTexturas: boolean;
  mostrarLegendas: boolean;
}> = ({
  id,
  audio,
  estacao,
  titulo,
  numeral,
  segundos,
  duracaoFrames,
  falas,
  inicioCenaSegundos,
  usarTexturas,
  mostrarLegendas,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Progresso 0..1 dentro da cena, usado por todos os movimentos.
  const progresso = Math.min(1, frame / Math.max(1, duracaoFrames - 1));

  return (
    <AbsoluteFill>
      <VagaoJanela
        estacao={estacao}
        titulo={titulo}
        numeral={numeral}
        segundos={segundos}
        decorridoSegundos={frame / fps}
        progresso={progresso}
        texturaSrc={usarTexturas ? TEXTURAS[estacao] : undefined}
      />
      {/* Áudio da cena: caminho absoluto convertido para file:// por resolveAsset. */}
      <Audio src={resolveAsset(audio)} />
      {mostrarLegendas && (
        <LegendaCena falas={falas} inicioCenaSegundos={inicioCenaSegundos} />
      )}
      {/* `id` fica no DOM como âncora de depuração no Studio. */}
      <div style={{ display: "none" }} data-cena={id} />
    </AbsoluteFill>
  );
};
