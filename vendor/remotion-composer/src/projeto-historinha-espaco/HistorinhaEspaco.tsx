/**
 * MANUAL — HistorinhaEspaco.tsx
 * =============================
 * O que faz
 * ---------
 * Composição raiz da historinha refeita "Luninha e Fridóca no Espaço Sideral":
 * encadeia as 10 cenas animadas com o áudio narrado por cena, mostra legendas
 * coloridas por frase e mantém um AVATAR NARRADOR no canto inferior esquerdo
 * contando a história com a boca sincronizada pela energia real da voz (RMS).
 *
 * Por que existe
 * --------------
 * Refazer o vídeo do canal que "parecia slides": agora toda a história é
 * animada (recorte), os bichinhos se movem o tempo todo e há um contador
 * falando — é isso que prende a atenção de criança.
 *
 * Como usa
 * --------
 *   Composição "HistorinhaEspaco" registrada em Root.tsx.
 *   Trocar o narrador: prop idAvatar (mesmo catálogo dos 5 bonecos).
 *
 * Regra de frame
 * --------------
 * useCurrentFrame() + interpolate(); proibido useFrame(). Render determinístico.
 */

import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { CENAS_HISTORIA, PALETA_ESPACO } from "./roteiroHistoriaEspaco";
import { TIMELINE_HISTORIA } from "./timelineHistoriaEspaco.generated";
import { BOCA_HISTORIA } from "./dadosBocaHistoriaEspaco.generated";
import { cenaHistoriaPorId } from "./CenasHistoriaEspaco";
import { NarradorLunaDetalhada } from "./PersonagensEspaco";
import { aberturaBocaNoFrame } from "../projeto-quatro-estacoes/SincronizacaoLabial";

/** Props da composição (troca de narrador pela aba Props ou --props). */
export type HistorinhaEspacoProps = {
  /** id do catálogo registroAvatares.ts para o NARRADOR do canto. */
  idAvatar?: string;
};

/** Divide o texto da cena em frases e distribui a tela da cena por caracteres. */
const frasesDaCena = (texto: string, duracaoFrames: number) => {
  const frases = texto.split(/(?<=[.!?…])\s+/).filter(Boolean);
  const totalCaracteres = frases.reduce((s, f) => s + f.length, 0);
  let cursor = 0;
  return frases.map((textoFrase) => {
    const fatia = Math.max(30, Math.round((textoFrase.length / totalCaracteres) * duracaoFrames));
    const frase = { texto: textoFrase, inicio: cursor, duracao: fatia };
    cursor += fatia;
    return frase;
  });
};

/** Legenda colorida da frase atual da cena. */
const LegendaCena: React.FC<{ id: string; duracao: number }> = ({ id, duracao }) => {
  const frame = useCurrentFrame();
  const cena = CENAS_HISTORIA.find((c) => c.id === id);
  if (!cena) return null;
  const frases = frasesDaCena(cena.texto, duracao);
  const atual = [...frases].reverse().find((f) => frame >= f.inicio);
  if (!atual) return null;
  const opacidade = interpolate(
    frame,
    [atual.inicio, atual.inicio + 8, atual.inicio + atual.duracao - 8, atual.inicio + atual.duracao],
    [0, 1, 1, 0.35],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <div
      style={{
        position: "absolute",
        left: 380,
        right: 60,
        bottom: 70,
        opacity: opacidade,
        background: PALETA_ESPACO.legendaFundo,
        borderRadius: 26,
        padding: "20px 36px",
        fontFamily: "sans-serif",
        fontWeight: 700,
        fontSize: 44,
        lineHeight: 1.25,
        color: PALETA_ESPACO.legendaTexto,
        boxShadow: "0 8px 30px rgba(0,0,0,0.35)",
      }}
    >
      {atual.texto}
    </div>
  );
};

/** Narradora do canto: Luna redesenhada com corpo e pescoço, boca lê o RMS absoluto. */
const NarradorHistoria: React.FC<{ idAvatar: string }> = ({ idAvatar }) => {
  void idAvatar;  // narradora é a Luna por ficha; a prop fica para variações futuras
  const frame = useCurrentFrame();  // frame ABSOLUTO do vídeo
  const valores = BOCA_HISTORIA["cena-00"]?.length ? Object.values(BOCA_HISTORIA).flat() : [];
  const abertura = aberturaBocaNoFrame(valores, frame);
  const balanco = interpolate(Math.sin(frame / 30), [-1, 1], [-1.5, 1.5]);
  return (
    <div style={{ position: "absolute", left: 26, bottom: 24, transform: `rotate(${balanco}deg)` }}>
      <div
        style={{
          padding: "10px 8px 2px",
          background: "linear-gradient(180deg, #fdf6e8, #f4e6cc)",
          borderRadius: 34,
          border: "5px solid #ffb43d",
          boxShadow: "0 18px 44px rgba(10,8,30,0.45)",
        }}
      >
        <NarradorLunaDetalhada aberturaBoca={abertura} frameLocal={frame} />
      </div>
    </div>
  );
};

/** Composição raiz registrada em Root.tsx. */
export const HistorinhaEspaco: React.FC<HistorinhaEspacoProps> = ({ idAvatar = "salsicha-marrom" }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: PALETA_ESPACO.ceuEspaco }}>
      {/* narração completa como bed único (evita drift entre cenas) */}
      <Audio src={staticFile("historinha-espaco/audio/historinha-espaco-completa.mp3")} />
      {TIMELINE_HISTORIA.cenas.map((cena) => {
        const CenaVisual = cenaHistoriaPorId(cena.id);
        return (
          <Sequence
            key={cena.id}
            from={cena.inicioFrame}
            durationInFrames={cena.duracaoFrames}
            name={cena.id}
            layout="none"
          >
            <CenaVisual duracao={cena.duracaoFrames} />
            <LegendaCena id={cena.id} duracao={cena.duracaoFrames} />
          </Sequence>
        );
      })}
      {/* narrador contando a história lá embaixo, durante tudo */}
      <NarradorHistoria idAvatar={idAvatar} />
    </AbsoluteFill>
  );
};

/** Metadados para o registro da Composition em Root.tsx. */
export const HISTORINHA_ESPACO_METADADOS = {
  fps: TIMELINE_HISTORIA.fps,
  width: 1920,
  height: 1080,
  durationInFrames: TIMELINE_HISTORIA.totalFrames,
} as const;
