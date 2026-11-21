/**
 * MANUAL — QuatroEstacoesJanelaTrem.tsx
 * =====================================
 * O que faz
 * ---------
 * É a timeline final do vídeo "Quatro Estações na Janela do Trem": coloca em
 * sequência as cinco cenas (primavera, verão, outono, inverno, retorno), com a
 * narração real medida, legenda sincronizada, abertura com título, cartão final,
 * grão de filme e transições de imagem suaves.
 *
 * De onde vêm os dados
 * --------------------
 * `timelineQuatroEstacoes.ts`: frames, paletas, falas e o caminho de cada MP3.
 * Os MP3 ficam em `remotion-composer/public/audio-quatro-estacoes/` e são lidos
 * por `staticFile()` — obrigatório para o Remotion achar o arquivo no render.
 *
 * Efeitos aplicados
 * -----------------
 * - parallax de sete camadas (paisagem + moldura + partículas)
 * - steam e reflexo animados no primeiro plano
 * - transições de fade curto na entrada/saída de cada cena
 * - grão de filme em tile PNG deslocado por frame (5 % de opacidade)
 * - título de abertura e cartão de encerramento com tipografia local
 *
 * Regra respeitada: nenhuma animação usa `useFrame()` de Three.js nem relógio de
 * parede; todo movimento sai de `useCurrentFrame()` + `interpolate()`.
 */

import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";  // 1. peças base do Remotion
import { loadPlayfair, loadSpaceGrotesk } from "../lib/localFonts";  // 2. fontes empacotadas
import {
  ESTACOES,
  FPS_VIDEO,
  FRAMES_CARTAO_FINAL,
  INICIO_CARTAO_FINAL,
  LARGURA_VIDEO,
  ALTURA_VIDEO,
  TOTAL_FRAMES,
  legendasDaEstacao,
  type Estacao,
} from "./timelineQuatroEstacoes";
import { PaisagemJanelaTrem } from "./PaisagemJanelaTrem";
import { JanelaTremPremium } from "./JanelaTremPremium";
import { LegendasEstacao } from "./LegendasEstacao";
import { aberturaBocaNoFrame } from "./SincronizacaoLabial";  // lip-sync: energia real da voz, por frame
import { VALORES_BECA_SINCRONIZACAO_LABIAL_NARRACAO_COMPLETA } from "./dados/sincronizacao-labial-narracao-completa";  // trilha 0..1
import { AvatarSelecionavel } from "./avatares/AvatarSelecionavel";  // avatar escolhido pelo usuário
import { AVATAR_PADRAO } from "./avatares/registroAvatares";  // padrão: buldogue inglês

const titulo = loadPlayfair("normal", ["700"]);          // 3. título em serifa forte
const tituloItalico = loadPlayfair("italic", ["400"]);    // 4. subtítulo em itálico
const rotulo = loadSpaceGrotesk(["500", "700"]);          // 5. rótulos em grotesca

/** Uma cena completa: paisagem + moldura + legenda + áudio da narração. */
const CenaEstacao: React.FC<{ estacao: Estacao; indice: number }> = ({ estacao, indice }) => {
  const frame = useCurrentFrame();                                                  // 6. frame local da cena
  const saida = interpolate(frame, [estacao.duracaoFrames - 26, estacao.duracaoFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });                                                                               // 7. fecha nos últimos 26 frames
  const legendas = legendasDaEstacao(estacao);                                      // 8. cronometragem do texto
  const legendaAtual = legendas.reduce<typeof legendas[number] | null>((atual, legenda) => {
    const dentro = frame >= legenda.inicio - 4 && frame < legenda.inicio + legenda.duracao + 2;  // 9. janela da linha
    return dentro ? legenda : atual;
  }, null);

  return (
    <AbsoluteFill style={{ backgroundColor: "#120c08" }}>
      {/* 10. O áudio da cena não entra aqui: o vídeo usa UM bed contínuo (voz +
          trilha + SFX) no topo da composição, para não duplicar a voz. */}
      <PaisagemJanelaTrem paleta={estacao.paleta} particula={estacao.particula} saida={saida} idCena={estacao.id} />
      <JanelaTremPremium paleta={estacao.paleta} idCena={estacao.id} />
      {legendaAtual && (
        <LegendasEstacao
          legenda={legendaAtual}
          titulo={estacao.titulo}
          indice={indice}
          totalCenas={ESTACOES.length}
          paleta={estacao.paleta}
        />
      )}
    </AbsoluteFill>
  );
};

/** Abertura: título sobre a primeira cena, entra e sai em 4,3 s. */
const AberturaTitulo: React.FC = () => {
  const frame = useCurrentFrame();                                                   // 11. frame local da abertura
  const entrada = interpolate(frame, [12, 46], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });  // 12. entra
  const saida = interpolate(frame, [112, 148], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });  // 13. sai
  const subida = interpolate(frame, [12, 60], [26, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });  // 14. sobe
  const brilho = interpolate(Math.sin(frame / 20), [-1, 1], [0.75, 1]);              // 15. brilho respirando

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: entrada * saida }}>
      <div style={{ textAlign: "center", transform: `translateY(${subida}px)` }}>
        <div style={{ ...rotulo, fontSize: 24, letterSpacing: 10, color: "rgba(255,246,232,0.85)", marginBottom: 18 }}>
          UMA VIAGEM EM CINCO ESTAÇÕES
        </div>
        <div style={{ ...titulo, fontSize: 132, lineHeight: 1.02, color: "#fff7ec", textShadow: "0 12px 40px rgba(0,0,0,0.55)", opacity: brilho }}>
          Quatro Estações
        </div>
        <div style={{ ...tituloItalico, fontSize: 62, color: "#ffe6c7", marginTop: 6, textShadow: "0 8px 28px rgba(0,0,0,0.5)" }}>
          na janela do trem
        </div>
        <div style={{ width: 220, height: 2, background: "rgba(255,240,220,0.55)", margin: "30px auto 0" }} />
      </div>
    </AbsoluteFill>
  );
};

/** Cartão final: despedida, sol nascendo e assinatura técnica discreta. */
const CartaoFinal: React.FC = () => {
  const frame = useCurrentFrame();                                                    // 16. frame local do cartão
  const entrada = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }); // 17. fade de entrada
  const subidaSol = interpolate(frame, [0, FRAMES_CARTAO_FINAL], [40, -40]);           // 18. sol subindo
  const arco = interpolate(frame, [0, FRAMES_CARTAO_FINAL], [0.2, 1]);                 // 19. arco dourado cresce

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0906", opacity: entrada, justifyContent: "center", alignItems: "center" }}>
      <svg width={LARGURA_VIDEO} height={ALTURA_VIDEO} style={{ position: "absolute" }} viewBox="0 0 1920 1080">
        <defs>
          <radialGradient id="amanhecer-final">
            <stop offset="0%" stopColor="#ffd79a" stopOpacity={0.55} />
            <stop offset="100%" stopColor="#ffd79a" stopOpacity={0} />
          </radialGradient>
        </defs>
        <circle cx={960} cy={700 + subidaSol} r={420 * arco} fill="url(#amanhecer-final)" />
        <circle cx={960} cy={720 + subidaSol} r={70} fill="#ffe3ad" opacity={0.9} />
        <path d="M0 900 Q 480 780 960 900 T 1920 880 L 1920 1080 L 0 1080 Z" fill="#1b120c" />
      </svg>
      <div style={{ textAlign: "center", zIndex: 2 }}>
        <div style={{ ...titulo, fontSize: 96, color: "#fff6e8" }}>Até a próxima estação</div>
        <div style={{ ...tituloItalico, fontSize: 44, color: "#ffdcb0", marginTop: 14 }}>
          onde o sol nasce de novo
        </div>
        <div style={{ ...rotulo, fontSize: 20, letterSpacing: 5, color: "rgba(255,240,225,0.6)", marginTop: 70 }}>
          NARRAÇÃO EDGE NEURAL · IMAGENS E MOTION REMOTION · MIX -14 LUFS
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Grão de filme: tile de ruído fixo, deslocado a cada frame.
 *   Antes era um feTurbulence de 3 oitavas sobre os 1920x1080 inteiros,
 *   recalculado nos 4.902 frames: caro o bastante para o Chromium derrubar a
 *   aba ("Page crashed!") em render longo. O tile Pronto em PNG (public/grao/)
 *   dá a mesma textura, e mover o `backgroundPosition` por frame mantém o grão
 *   vivo em vez de congelado. Determinístico: o deslocamento vem do frame. */
const GraoDeFilme: React.FC = () => {
  const frame = useCurrentFrame();
  // Deslocamento em passos primos: nunca repete a mesma posição duas vezes
  // seguidas e cobre o tile de 256 px sem padrão visível.
  const offX = (frame * 71) % 256;
  const offY = (frame * 131) % 256;

  return (
    <AbsoluteFill
      style={{
        opacity: 0.055,
        mixBlendMode: "overlay",
        pointerEvents: "none",
        backgroundImage: `url(${staticFile("grao/grao-filme-256.png")})`,
        backgroundRepeat: "repeat",
        backgroundPosition: `-${offX}px -${offY}px`,
      }}
    />
  );
};

/** Composição raiz registrada em Root.tsx. */
export const QuatroEstacoesJanelaTrem: React.FC<{ idAvatar?: string }> = ({ idAvatar = AVATAR_PADRAO }) => {
  const cenaRetorno = ESTACOES[ESTACOES.length - 1];  // 19a. cena final onde a apresentadora se despede
  const frameAbsoluto = useCurrentFrame();             // 19c. frame global (a narração começa no 0)
  const aberturaBoca = aberturaBocaNoFrame(            // 19d. boca segue a voz de verdade
    VALORES_BECA_SINCRONIZACAO_LABIAL_NARRACAO_COMPLETA,
    frameAbsoluto,
  );
  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0906" }}>
      {/* 19b. Bed de áudio único: narração contínua + trilha + SFX (163,415 s, v2).
          Um só arquivo evita drift entre cenas e é o que carrega a música. */}
      <Audio src={staticFile("audio-quatro-estacoes/mix-previa-narracao-trilha-sfx.mp3")} />
      {ESTACOES.map((estacao, indice) => (                                       // 20. uma sequência por estação
        <Sequence
          key={estacao.id}
          from={estacao.inicioFrames}
          durationInFrames={estacao.duracaoFrames}
          name={`${indice + 1}-${estacao.titulo}`}
          layout="none"
        >
          <CenaEstacao estacao={estacao} indice={indice} />
        </Sequence>
      ))}

      <Sequence from={0} durationInFrames={150} name="abertura-titulo" layout="none">
        <AberturaTitulo />                                                      {/* 21. título de abertura */}
      </Sequence>

      <Sequence from={INICIO_CARTAO_FINAL} durationInFrames={FRAMES_CARTAO_FINAL} name="cartao-final" layout="none">
        <CartaoFinal />                                                         {/* 22. despedida */}
      </Sequence>

      {/* 22b. Avatar selecionável: entra na cena final e sai antes do cartão.
          Escolha pelo props idAvatar; a boca segue o RMS real da narração. */}
      <Sequence
        from={cenaRetorno.inicioFrames}
        durationInFrames={TOTAL_FRAMES - cenaRetorno.inicioFrames - FRAMES_CARTAO_FINAL}
        name={`avatar-${idAvatar}-cena-05`}
        layout="none"
      >
        <AvatarSelecionavel
          idAvatar={idAvatar}
          aberturaBoca={aberturaBoca}
          frameLocal={frameAbsoluto - cenaRetorno.inicioFrames}
        />
      </Sequence>

      <GraoDeFilme />                                                           {/* 23. grão por cima de tudo */}
    </AbsoluteFill>
  );
};

/** Metadados exportados para o registro da Composition. */
export const QUATRO_ESTACOES_METADADOS = {
  fps: FPS_VIDEO,
  width: LARGURA_VIDEO,
  height: ALTURA_VIDEO,
  durationInFrames: TOTAL_FRAMES,
} as const;
