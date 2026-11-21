/**
 * MANUAL — CenasHistoriaEspaco.tsx
 * ================================
 * O que faz
 * ---------
 * As 10 cenas visuais da historinha (C0..C9), uma coreografia de recorte por
 * trecho: decolagem com trepidação, gravidade zero, biscoitos voadores,
 * cambalhotas, bailarina espacial, botão amarelo da caixinha de música,
 * abraço vendo a Terra e o pouso no gramado. Nada fica parado.
 *
 * Por que existe
 * --------------
 * A crítica ao vídeo original: "parece slides". Cada componente aqui garante
 * movimento contínuo (corpos, cenário, biscoitos, luzes) ligado ao frame.
 *
 * Como usa
 * ---------
 * Cada cena recebe { duracao } (frames da Sequence) e calcula tudo com
 * interpolate() sobre o frame LOCAL — nunca relógio de parede.
 *
 * Regra de frame
 * --------------
 * useCurrentFrame() + interpolate()/spring(); proibido useFrame().
 */

import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";
import { PALETA_ESPACO } from "./roteiroHistoriaEspaco";
import {
  LuninhaSalsicha,
  FridocaBuldogue,
  OsoBiscoito,
  NotaMusical,
} from "./PersonagensEspaco";
import {
  EspacoEstrelado,
  JanelaNave,
  PainelNave,
  Foguete,
  GramadoPouso,
  BalaoGrito,
  entradaBalao,
} from "./CenarioHistoriaEspaco";

/** Camada base: 1920x1080, sem cortes. */
const Quadro: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ backgroundColor: PALETA_ESPACO.ceuEspaco, overflow: "hidden" }}>{children}</AbsoluteFill>
);

/** Cabine simples: janela no alto, painel embaixo (reuso do cenário). */
const Cabine: React.FC<{ janelaLargura?: number; botaoBrilhando?: boolean }> = ({
  janelaLargura = 520,
  botaoBrilhando = false,
}) => (
  <>
    <EspacoEstrelado velocidade={0.35} />
    <div style={{ position: "absolute", top: 40, left: "50%", transform: "translateX(-50%)" }}>
      <JanelaNave largura={janelaLargura} />
    </div>
    <PainelNave botaoBrilhando={botaoBrilhando} />
  </>
);

/* ===================== C0 — TÍTULO ===================== */
const CenaTitulo: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  const pop = spring({ frame, fps: 30, config: { damping: 9, stiffness: 120 } });
  const balanco = interpolate(Math.sin(frame / 14), [-1, 1], [-3, 3]);
  return (
    <Quadro>
      <EspacoEstrelado velocidade={0.8} />
      <div
        style={{
          position: "absolute",
          top: 250,
          width: "100%",
          textAlign: "center",
          transform: `scale(${pop}) rotate(${balanco}deg)`,
        }}
      >
        <div style={{ fontSize: 120, fontWeight: 900, color: PALETA_ESPACO.tituloRosa, textShadow: "6px 6px 0 #6b1f3e", fontFamily: "sans-serif" }}>
          Luninha &amp; Fridóca
        </div>
        <div style={{ fontSize: 86, fontWeight: 800, color: PALETA_ESPACO.tituloDourado, textShadow: "5px 5px 0 #7a4a00", fontFamily: "sans-serif", marginTop: 20 }}>
          no Espaço Sideral!
        </div>
      </div>
      {/* as duas espiando dos cantos, dançando */}
      <div style={{ position: "absolute", bottom: 40, left: 160 }}>
        <LuninhaSalsicha modo="flutuar" escala={1.4} />
      </div>
      <div style={{ position: "absolute", bottom: 40, right: 140 }}>
        <FridocaBuldogue ancorarDireita modo="flutuar" escala={1.4} />
      </div>
    </Quadro>
  );
};

/* ===================== C1 — O CONVITE ===================== */
const CenaConvite: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  void duracao;
  // o foguete espera ao fundo e as duas se apresentam saltitando
  const chegadaFoguete = interpolate(frame, [0, 40], [-500, 40], { extrapolateRight: "clamp" });
  return (
    <Quadro>
      <EspacoEstrelado velocidade={0.5} />
      <div style={{ position: "absolute", left: 1180, bottom: 120, transform: `translateY(${chegadaFoguete}px)` }}>
        <Foguete escala={0.85} fogo />
      </div>
      <div style={{ position: "absolute", bottom: 150, left: 220 }}>
        <LuninhaSalsicha modo="pousado" escala={1.6} />
      </div>
      <div style={{ position: "absolute", bottom: 150, right: 480 }}>
        <FridocaBuldogue modo="pousado" escala={1.6} />
      </div>
      <BalaoGrito texto="Olá, amiguinhos!" x={760} y={140} entrada={entradaBalao(frame, 30)} />
    </Quadro>
  );
};

/* ===================== C2 — DECOLANDO ===================== */
const CenaDecolagem: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  // 0..55%: dentro da nave apertada; 55..100%: foguete voa no céu
  const pontoVoo = duracao * 0.55;
  if (frame < pontoVoo) {
    return (
      <Quadro>
        <PainelNave />
        <div style={{ position: "absolute", bottom: 360, left: 480 }}>
          <LuninhaSalsicha modo="decolagem" escala={1.7} />
        </div>
        <div style={{ position: "absolute", bottom: 360, right: 420 }}>
          <FridocaBuldogue ancorarDireita modo="decolagem" escala={1.7} />
        </div>
        <BalaoGrito texto="Tchim... pum!" x={1150} y={170} entrada={entradaBalao(frame, 20)} />
      </Quadro>
    );
  }
  const f = frame - pontoVoo;
  const subida = interpolate(f, [0, duracao - pontoVoo], [500, -750], { extrapolateRight: "clamp" });
  const inclinacao = interpolate(f, [0, duracao - pontoVoo], [0, 12]);
  return (
    <Quadro>
      <GramadoPouso />
      <div style={{ position: "absolute", left: "50%", bottom: 260, transform: `translate(-50%, ${subida}px) rotate(${inclinacao}deg)` }}>
        <Foguete fogo />
      </div>
      <BalaoGrito texto="Voou alto!" x={1180} y={140} entrada={entradaBalao(f, 10)} />
    </Quadro>
  );
};

/* ===================== C3 — SEM GRAVIDADE ===================== */
const CenaGravidadeSumiu: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  void duracao;
  // Luninha gira devagar de cabeça pra cima e pra baixo; Fridóca vira de ponta-cabeça
  const rotacaoLuna = interpolate(frame, [0, 240, duracao || 600], [0, -180, -360], { extrapolateRight: "clamp" });
  const rotacaoFrida = interpolate(frame, [60, duracao || 600], [0, 160], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const baloes = Array.from({ length: 6 }, (_, i) => ({
    x: 260 + i * 280 + Math.sin(frame / 40 + i) * 40,
    y: 220 + ((i % 3) * 240) + Math.cos(frame / 50 + i * 2) * 30,
    r: 26 + (i % 3) * 8,
  }));
  return (
    <Quadro>
      <Cabine />
      {/* bolhas de sabão flutuando */}
      {baloes.map((b, i) => (
        <svg key={i} width={b.r * 2} height={b.r * 2} viewBox="0 0 100 100" style={{ position: "absolute", left: b.x, top: b.y }}>
          <circle cx={50} cy={50} r={46} fill="#bfe8ff" opacity={0.5} />
          <circle cx={50} cy={50} r={46} fill="none" stroke="#e6f8ff" strokeWidth={4} />
          <circle cx={36} cy={34} r={12} fill="#ffffff" opacity={0.7} />
        </svg>
      ))}
      <div style={{ position: "absolute", bottom: 400, left: 300, transform: `rotate(${rotacaoLuna}deg)` }}>
        <LuninhaSalsicha modo="flutuar" escala={1.6} />
      </div>
      <div style={{ position: "absolute", bottom: 400, right: 260, transform: `rotate(${rotacaoFrida}deg)` }}>
        <FridocaBuldogue ancorarDireita modo="flutuar" escala={1.6} />
      </div>
      <BalaoGrito texto="Uau!!!" x={1300} y={150} entrada={entradaBalao(frame, 30)} />
    </Quadro>
  );
};

/* ===================== C4 — BISCOITOS VOADORES (com o salto da Luninha) ==== */
const CenaBiscoitosVoando: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  // a caixa abre no meio da cena e os ossos escapam
  const inicioCaixa = duracao * 0.25;
  const aberturaCaixa = interpolate(frame, [inicioCaixa, inicioCaixa + 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ossos = Array.from({ length: 6 }, (_, i) => ({
    x: 800 + (i % 3) * 260,
    y: 140 + (i % 2) * 220,
    rot: Math.sin(frame / 26 + i * 2) * 22,
    flutua: Math.sin(frame / 34 + i) * 24,
    sai: frame > inicioCaixa + i * 6,
  }));
  // salto final da Luninha pega um biscoito direto na boca (últimos 40%)
  const inicioSalto = duracao * 0.55;
  const fimSalto = duracao * 0.92;
  const tSalto = interpolate(frame, [inicioSalto, fimSalto], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const alturaSalto = -Math.sin(tSalto * Math.PI) * 320;
  const avanco = tSalto * 380;
  const yOssoAlvo = interpolate(tSalto, [0, 0.5, 0.52], [120, 210, 999], { extrapolateRight: "clamp" });
  return (
    <Quadro>
      <Cabine />
      {ossos.map((o, i) =>
        o.sai ? (
          <div key={i} style={{ position: "absolute", left: o.x, top: o.y + o.flutua }}>
            <OsoBiscoito x={0} y={0} rotacao={o.rot} />
          </div>
        ) : null
      )}
      {/* osso alvo do salto */}
      <OsoBiscoito x={1120} y={yOssoAlvo} rotacao={frame * 2} escala={1.1} />
      {/* caixa de biscoitos caninos com tampa abrindo */}
      <svg width={340} height={240} viewBox="0 0 340 240" style={{ position: "absolute", left: 480, bottom: 330 }}>
        <rect x={20} y={110} width={300} height={110} rx={18} fill="#c97b3d" />
        <rect x={20} y={110} width={300} height={26} fill="#a35d24" />
        <g transform={`rotate(${-aberturaCaixa * 70} 20 110)`}>
          <rect x={20} y={78} width={300} height={34} rx={16} fill="#e0925a" />
        </g>
        <text x={170} y={180} textAnchor="middle" fontSize={30} fontWeight={800} fill="#fff3dd" fontFamily="sans-serif">
          BISCOITOS
        </text>
      </svg>
      <div style={{ position: "absolute", bottom: 400 + alturaSalto, left: 240 + avanco }}>
        <LuninhaSalsicha modo={tSalto > 0 && tSalto < 1 ? "flutuar" : "nadar"} escala={1.5} />
      </div>
      <div style={{ position: "absolute", bottom: 400, right: 140 }}>
        <FridocaBuldogue modo="nadar" escala={1.5} />
      </div>
      <BalaoGrito texto="Nhaque!" x={1020} y={140} entrada={entradaBalao(frame, Math.round(inicioSalto + (fimSalto - inicioSalto) * 0.5))} />
    </Quadro>
  );
};

/* ===================== C7 — ABRAÇO ESPACIAL ===================== */
const CenaAbracoEspacial: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  void duracao;
  // a Terra gira devagar na janela; as duas flutuam abraçadas no centro
  const juntam = interpolate(frame, [0, 45], [0, 1], { extrapolateRight: "clamp" });
  const vaiLuna = juntam * 300;
  const vaiFrida = juntam * -300;
  const balancoAbaco = Math.sin(frame / 40) * 4;
  return (
    <Quadro>
      <EspacoEstrelado velocidade={0.4} />
      <div style={{ position: "absolute", top: 30, left: "50%", transform: "translateX(-50%)" }}>
        <JanelaNave largura={950} mostrarTerra />
      </div>
      <div style={{ position: "absolute", bottom: 400, left: 660 + vaiLuna, transform: `rotate(${balancoAbaco}deg)` }}>
        <LuninhaSalsicha modo="flutuar" escala={1.6} />
      </div>
      <div style={{ position: "absolute", bottom: 400, left: 760 + vaiFrida, transform: `rotate(${-balancoAbaco}deg)` }}>
        <FridocaBuldogue modo="flutuar" escala={1.6} />
      </div>
      {/* corações subindo */}
      {Array.from({ length: 6 }, (_, i) => {
        const t = ((frame + i * 25) % 150) / 150;
        return (
          <svg key={i} width={60} height={60} viewBox="0 0 60 60" style={{ position: "absolute", left: 820 + i * 55, top: 320 - t * 260, opacity: 1 - t }}>
            <path d="M30 52 C 8 34 2 18 14 10 C 24 4 30 14 30 18 C 30 14 36 4 46 10 C 58 18 52 34 30 52 Z" fill={PALETA_ESPACO.tituloRosa} />
          </svg>
        );
      })}
    </Quadro>
  );
};

/* ===================== C9 — ATÉ A PRÓXIMA ===================== */
const CenaDespedida: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  void duracao;
  const pop = spring({ frame, fps: 30, config: { damping: 10, stiffness: 110 } });
  const balanco = Math.sin(frame / 12) * 3;
  return (
    <Quadro>
      <GramadoPouso />
      <div style={{ position: "absolute", left: 1180, bottom: 120 }}>
        <Foguete escala={0.7} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 140,
          width: "100%",
          textAlign: "center",
          transform: `scale(${pop}) rotate(${balanco}deg)`,
        }}
      >
        <div style={{ fontSize: 96, fontWeight: 900, color: "#ff7bb1", textShadow: "5px 5px 0 #6b1f3e", fontFamily: "sans-serif" }}>
          Até a próxima aventura!
        </div>
        <div style={{ fontSize: 54, fontWeight: 800, color: "#ffd24d", textShadow: "4px 4px 0 #7a4a00", fontFamily: "sans-serif", marginTop: 16 }}>
          Tchau, tchau!
        </div>
      </div>
      {/* as duas acenando na grama */}
      <div style={{ position: "absolute", bottom: 60, left: 300 }}>
        <LuninhaSalsicha modo="pousado" escala={1.7} />
      </div>
      <div style={{ position: "absolute", bottom: 60, right: 300 }}>
        <FridocaBuldogue modo="pousado" escala={1.7} />
      </div>
    </Quadro>
  );
};

/** Roteamento das cenas por id — batidas da narração entregue (metadados-voz.json). */
export const cenaHistoriaPorId = (id: string): React.FC<{ duracao: number }> => {
  switch (id) {
    case "cena-00": return CenaTitulo;
    case "cena-01": return CenaConvite;
    case "cena-02": return CenaDecolagem;
    case "cena-03": return CenaGravidadeSumiu;
    case "cena-04": return CenaBiscoitosVoando;
    case "cena-05": return CenaBailarinaEspacial;
    case "cena-06": return CenaBotaoAmarelo;
    case "cena-07": return CenaAbracoEspacial;
    case "cena-08": return CenaVoltaParaCasa;
    case "cena-09": return CenaDespedida;
    default: return CenaTitulo;
  }
};
const CenaBailarinaEspacial: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  // janela ENORME com milhares de estrelas
  const abreJanela = interpolate(frame, [0, 40], [0.2, 1], { extrapolateRight: "clamp" });
  // Luninha gira como bailarina; Fridóca se aproxima e dá trombada no fim
  const rotacaoLuna = frame * 3;
  const aproximacaoFrida = interpolate(frame, [0, duracao * 0.7], [0, -300], { extrapolateRight: "clamp" });
  // trombada: um tremor curto nos dois depois de 70%
  const trombada = frame > duracao * 0.7 ? Math.abs(Math.sin(frame / 2)) * 14 : 0;
  // depois rolam juntas flutuando baixinho
  const rolamJuntas = interpolate(frame, [duracao * 0.78, duracao], [0, 360], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Quadro>
      <EspacoEstrelado velocidade={0.5} />
      <div style={{ position: "absolute", top: 40, left: "50%", transform: `translateX(-50%) scale(${abreJanela})` }}>
        <JanelaNave largura={950} />
      </div>
      <div style={{ position: "absolute", bottom: 400, left: 560 + trombada, transform: `rotate(${rotacaoLuna + rolamJuntas}deg)` }}>
        <LuninhaSalsicha modo="flutuar" escala={1.6} />
      </div>
      <div style={{ position: "absolute", bottom: 400, left: 1120 + aproximacaoFrida + trombada, transform: `rotate(${-rolamJuntas}deg)` }}>
        <FridocaBuldogue modo="flutuar" escala={1.6} />
      </div>
    </Quadro>
  );
};

/* ===================== C8 — BOTÃO AMARELO ===================== */
const CenaBotaoAmarelo: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  // o botão é apertado nos primeiros 15%; depois luzes rosa/douradas pulsam
  const pontoMusica = duracao * 0.15;
  const musicaLigada = frame > pontoMusica;
  // notas musicais sobem do painel
  const notas = Array.from({ length: 7 }, (_, i) => {
    const t = ((frame - pontoMusica + i * 40) % 260) / 260;
    return musicaLigada && frame > pontoMusica + i * 40
      ? { x: 480 + i * 190, y: 620 - t * 420, o: 1 - t, cor: i % 2 ? PALETA_ESPACO.tituloDourado : PALETA_ESPACO.tituloRosa }
      : null;
  });
  // flashes suaves rosa/dourado
  const flash = musicaLigada ? 0.12 + 0.12 * Math.abs(Math.sin(frame / 15)) : 0;
  // abraço no final: as duas se juntam no centro
  const vemLuna = interpolate(frame, [duracao * 0.55, duracao * 0.75], [0, 430], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const vemFrida = interpolate(frame, [duracao * 0.55, duracao * 0.75], [0, -430], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Quadro>
      <Cabine janelaLargura={700} botaoBrilhando={musicaLigada} />
      {/* halo da caixinha de música */}
      {musicaLigada && (
        <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 65%, rgba(255,123,177,${flash}), rgba(255,210,77,${flash * 0.7}) 60%, transparent 85%)` }} />
      )}
      {notas.map((n, i) =>
        n ? <NotaMusical key={i} x={n.x} y={n.y} opacidade={Math.max(0, n.o)} cor={n.cor} escala={0.9 + (i % 3) * 0.2} /> : null
      )}
      <div style={{ position: "absolute", bottom: 400, left: 520 + vemLuna }}>
        <LuninhaSalsicha modo="flutuar" escala={1.6} />
      </div>
      <div style={{ position: "absolute", bottom: 400, left: 520 + vemFrida + 480 }}>
        <FridocaBuldogue modo="flutuar" escala={1.6} />
      </div>
      {/* corações quando se abraçam */}
      {vemLuna > 200 &&
        Array.from({ length: 5 }, (_, i) => {
          const t = ((frame + i * 30) % 150) / 150;
          return (
            <svg key={i} width={60} height={60} viewBox="0 0 60 60" style={{ position: "absolute", left: 900 + i * 40, top: 300 - t * 240, opacity: 1 - t }}>
              <path d="M30 52 C 8 34 2 18 14 10 C 24 4 30 14 30 18 C 30 14 36 4 46 10 C 58 18 52 34 30 52 Z" fill={PALETA_ESPACO.tituloRosa} />
            </svg>
          );
        })}
    </Quadro>
  );
};

/* ===================== C9 — VOLTA PARA CASA ===================== */
const CenaVoltaParaCasa: React.FC<{ duracao: number }> = ({ duracao }) => {
  const frame = useCurrentFrame();
  // fase 1 (0..35%): sentadas com cinto, foguete entre nuvens
  // fase 2 (35..70%): desce devagarinho
  // fase 3 (70..100%): pousada no gramado, pula de alegria
  const pontoDescida = duracao * 0.35;
  const pontoPouso = duracao * 0.7;
  const gramado = interpolate(frame, [pontoDescida, pontoPouso], [-1080, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const nuvensSobem = interpolate(frame, [0, pontoPouso], [0, -500], { extrapolateRight: "clamp" });
  const pousoFeito = frame >= pontoPouso;
  return (
    <Quadro>
      {/* céu com nuvens que sobem (o foguete desce) */}
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${nuvensSobem}px)` }}>
        <GramadoPouso />
      </div>
      {/* gramado entra de baixo até o pouso */}
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${gramado}px)` }}>
        <GramadoPouso />
      </div>
      {/* foguete parado no gramado depois do pouso */}
      {pousoFeito && (
        <div style={{ position: "absolute", left: 1150, bottom: 60 }}>
          <Foguete escala={0.8} />
        </div>
      )}
      {/* as duas: sentadas com cinto; no pouso, pulando de orgulho */}
      <div style={{ position: "absolute", bottom: pousoFeito ? 120 : 200, left: 330 }}>
        <LuninhaSalsicha modo={pousoFeito ? "pousado" : "sentado"} escala={1.7} />
      </div>
      <div style={{ position: "absolute", bottom: pousoFeito ? 120 : 200, right: 330 }}>
        <FridocaBuldogue ancorarDireita modo={pousoFeito ? "pousado" : "sentado"} escala={1.7} />
      </div>
      {/* cinto simples enquanto voam de volta */}
      {!pousoFeito && (
        <>
          <svg width={180} height={50} viewBox="0 0 180 50" style={{ position: "absolute", bottom: 330, left: 390 }}>
            <rect x={10} y={10} width={160} height={30} rx={12} fill={PALETA_ESPACO.roupaDetalhe} />
            <rect x={70} y={2} width={40} height={46} rx={8} fill={PALETA_ESPACO.naveDourado} />
          </svg>
          <svg width={180} height={50} viewBox="0 0 180 50" style={{ position: "absolute", bottom: 330, right: 390 }}>
            <rect x={10} y={10} width={160} height={30} rx={12} fill={PALETA_ESPACO.roupaDetalhe} />
            <rect x={70} y={2} width={40} height={46} rx={8} fill={PALETA_ESPACO.naveDourado} />
          </svg>
        </>
      )}
      {pousoFeito && (
        <BalaoGrito texto="Missão cumprida!" x={1090} y={170} entrada={entradaBalao(frame, Math.round(pontoPouso + 12))} />
      )}
    </Quadro>
  );
};

/** Roteamento das cenas por id (mesma ordem de CENAS_HISTORIA). */

