/**
 * MANUAL — CenarioHistoriaEspaco.tsx
 * ==================================
 * O que faz
 * ---------
 * Cenários de recorte da historinha: espaço estrelado com paralaxe, cabine
 * da nave (painel, botão amarelo, luzes rosa/douradas), janela enorme com
 * Terra, foguete com fogo animado, nuvens e gramado do pouso. Cada peça se
 * move a cada frame: estrelas deslizam, luzes pulsam, fogo dança.
 *
 * Por que existe
 * --------------
 * A crítica ao vídeo original era "parece slides". Aqui até o fundo respira:
 * nada na tela fica estático por mais de um ciclo de seno.
 *
 * Regra de frame
 * --------------
 * Tudo deriva de useCurrentFrame(); proibido useFrame(). Render determinístico.
 */

import { useCurrentFrame, interpolate } from "remotion";
import { PALETA_ESPACO } from "./roteiroHistoriaEspaco";

/** Seno oscilante reutilizável. */
const oscila = (frame: number, periodo: number, amplitude: number, fase = 0) =>
  Math.sin(((frame + fase) / periodo) * Math.PI * 2) * amplitude;

/** Semente determinística para espalhar estrelas sempre igual. */
const aleatorio = (indice: number) => {
  const x = Math.sin(indice * 127.1) * 43758.5453;
  return x - Math.floor(x);
};

/* ---------------------------------------------------------------------------
 * ESPAÇO ESTRELADO — céu azul escuro com 3 camadas de estrelas em paralaxe.
 * ------------------------------------------------------------------------- */
export const EspacoEstrelado: React.FC<{
  /** velocidade do deslize horizontal (px/frame) */
  velocidade?: number;
}> = ({ velocidade = 0.6 }) => {
  const frame = useCurrentFrame();
  const estrelas = Array.from({ length: 70 }, (_, i) => {
    const camada = i % 3;                                    // 3 profundidades
    const tamanho = 2 + camada * 1.6;
    const x = (aleatorio(i) * 2400 + frame * velocidade * (camada + 1)) % 2000 - 200;
    const y = aleatorio(i + 99) * 1080;
    const pulso = 0.55 + 0.45 * Math.abs(oscila(frame + i * 7, 40 + camada * 20, 1));
    return { x, y, tamanho, pulso };
  });
  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" preserveAspectRatio="none">
      <defs>
        <radialGradient id="ceu-espaco-historia" cx="50%" cy="30%">
          <stop offset="0%" stopColor={PALETA_ESPACO.ceuEspacoClaro} stopOpacity={0.9} />
          <stop offset="100%" stopColor={PALETA_ESPACO.ceuEspaco} />
        </radialGradient>
      </defs>
      <rect width="1920" height="1080" fill="url(#ceu-espaco-historia)" />
      {estrelas.map((e, i) => (
        <circle key={i} cx={e.x} cy={e.y} r={e.tamanho} fill={PALETA_ESPACO.estrela} opacity={e.pulso} />
      ))}
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * JANELA DA NAVE — moldura oval com a Terra (cena 08) ou estrelas (cena 07).
 * ------------------------------------------------------------------------- */
export const JanelaNave: React.FC<{
  /** mostra a Terra azulzinha dentro da janela */
  mostrarTerra?: boolean;
  largura?: number;
}> = ({ mostrarTerra = false, largura = 900 }) => {
  const frame = useCurrentFrame();
  const altura = largura * 0.62;
  const pulsoTerra = oscila(frame, 120, 4);
  return (
    <svg width={largura} height={altura} viewBox="0 0 900 560" style={{ display: "block" }}>
      <defs>
        <clipPath id="janela-oval">
          <ellipse cx="450" cy="280" rx="380" ry="240" />
        </clipPath>
      </defs>
      <g clipPath="url(#janela-oval)">
        <rect width="900" height="560" fill={PALETA_ESPACO.ceuEspaco} />
        {Array.from({ length: 80 }, (_, i) => (
          <circle
            key={i}
            cx={aleatorio(i) * 900}
            cy={aleatorio(i + 50) * 560}
            r={1.5 + aleatorio(i + 7) * 3}
            fill={PALETA_ESPACO.estrela}
            opacity={0.5 + 0.5 * Math.abs(oscila(frame + i * 11, 50, 1))}
          />
        ))}
        {mostrarTerra && (
          <g transform={`translate(${450 + pulsoTerra} 430)`}>
            <circle r={170} fill="#3f8fe0" />
            <path d="M-120 -40 Q -40 -90 30 -30 Q 90 10 20 50 Q -60 70 -120 20 Z" fill="#7ed17a" opacity={0.9} />
            <path d="M40 -120 Q 110 -100 90 -40 Q 40 -60 40 -120 Z" fill="#7ed17a" opacity={0.9} />
            <ellipse cx={-30} cy={90} rx={130} ry={26} fill="#eef6ff" opacity={0.75} />
            <ellipse cx={110} cy={-90} rx={90} ry={20} fill="#eef6ff" opacity={0.75} />
          </g>
        )}
      </g>
      {/* moldura em camadas, tipo recorte de papel */}
      <ellipse cx="450" cy="280" rx="380" ry="240" fill="none" stroke={PALETA_ESPACO.naveDourado} strokeWidth={26} />
      <ellipse cx="450" cy="280" rx="404" ry="264" fill="none" stroke={PALETA_ESPACO.naveCorpo} strokeWidth={30} />
      <ellipse cx="450" cy="280" rx="418" ry="278" fill="none" stroke={PALETA_ESPACO.naveDetalhe} strokeWidth={14} />
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * PAINEL DA NAVE — base da cabine com luzes piscando e botão amarelo grande.
 * ------------------------------------------------------------------------- */
export const PainelNave: React.FC<{
  /** o botão amarelo brilha (cena 08) */
  botaoBrilhando?: boolean;
}> = ({ botaoBrilhando = false }) => {
  const frame = useCurrentFrame();
  const pulsoBotao = botaoBrilhando
    ? 1 + Math.abs(oscila(frame, 20, 0.35))
    : 1 + Math.abs(oscila(frame, 90, 0.04));
  return (
    <svg width="100%" height={300} viewBox="0 0 1920 300" preserveAspectRatio="none" style={{ position: "absolute", bottom: 0 }}>
      <rect width="1920" height="300" fill={PALETA_ESPACO.naveCorpo} />
      <rect y={30} width="1920" height={270} fill="#e3ddd0" />
      {/* faixa rosa de detalhe */}
      <rect y={190} width="1920" height={26} fill={PALETA_ESPACO.naveDetalhe} opacity={0.85} />
      {/* luzes piscando em tons alternados */}
      {Array.from({ length: 12 }, (_, i) => {
        const cor = i % 2 === 0 ? PALETA_ESPACO.naveDetalhe : PALETA_ESPACO.naveDourado;
        const brilho = 0.4 + 0.6 * Math.abs(oscila(frame + i * 13, 24, 1));
        return <circle key={i} cx={140 + i * 150} cy={110} r={12} fill={cor} opacity={brilho} />;
      })}
      {/* botão grande e amarelo */}
      <g transform={`translate(960 120) scale(${pulsoBotao})`}>
        <circle r={46} fill="#c98a18" />
        <circle r={40} fill={PALETA_ESPACO.naveDourado} />
        <circle r={40} fill="none" stroke="#fff" strokeWidth={5} opacity={0.4} />
      </g>
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * FOGUETE — corpo de recorte com fogo que dança e trepidação de decolagem.
 * ------------------------------------------------------------------------- */
export const Foguete: React.FC<{
  /** escala geral */
  escala?: number;
  /** fogo ligado (decolagem) */
  fogo?: boolean;
}> = ({ escala = 1, fogo = false }) => {
  const frame = useCurrentFrame();
  const tremer = fogo ? oscila(frame, 4, 3) : 0;
  const tamanhoFogo = fogo ? 1 + Math.abs(oscila(frame, 6, 0.5)) : 0;
  return (
    <svg width={360 * escala} height={560 * escala} viewBox="0 0 360 560" style={{ overflow: "visible" }}>
      <g transform={`translate(${tremer} 0)`}>
        {fogo && (
          <g transform={`translate(180 560) scale(1 ${tamanhoFogo})`}>
            <path d="M-46 0 Q 0 150 46 0 Z" fill="#ff9d3d" />
            <path d="M-28 0 Q 0 110 28 0 Z" fill="#ffd24d" />
            <path d="M-12 0 Q 0 70 12 0 Z" fill="#fff6e0" />
          </g>
        )}
        {/* aletas */}
        <path d="M40 420 Q 0 480 30 520 L 60 470 Z" fill={PALETA_ESPACO.naveDetalhe} />
        <path d="M320 420 Q 360 480 330 520 L 300 470 Z" fill={PALETA_ESPACO.naveDetalhe} />
        {/* corpo */}
        <path d="M60 200 Q 60 40 180 20 Q 300 40 300 200 L 300 470 Q 300 540 180 540 Q 60 540 60 470 Z" fill={PALETA_ESPACO.naveCorpo} />
        <rect x={60} y={300} width={240} height={30} fill={PALETA_ESPACO.naveDetalhe} opacity={0.9} />
        <circle cx={180} cy={210} r={62} fill={PALETA_ESPACO.ceuEspacoClaro} />
        <circle cx={180} cy={210} r={62} fill="none" stroke={PALETA_ESPACO.naveDourado} strokeWidth={10} />
        {/* brilho que desliza no corpo */}
        <ellipse
          cx={100 + oscila(frame, 120, 30)}
          cy={140}
          rx={14}
          ry={90}
          fill="#fff"
          opacity={0.25}
        />
        {/* ponta */}
        <path d="M120 40 Q 180 -40 240 40 Z" fill={PALETA_ESPACO.naveDetalhe} />
      </g>
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * NUVENS E GRAMADO — pouso na Terra (cena 09).
 * ------------------------------------------------------------------------- */
export const GramadoPouso: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" preserveAspectRatio="none">
      <defs>
        <linearGradient id="ceu-terra-historia" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7ec8f0" />
          <stop offset="100%" stopColor="#cdf0ff" />
        </linearGradient>
      </defs>
      <rect width="1920" height="1080" fill="url(#ceu-terra-historia)" />
      {/* nuvens que deslizam devagar */}
      {[0, 1, 2, 3].map((i) => {
        const x = (aleatorio(i) * 2000 + frame * 0.8) % 2200 - 200;
        const y = 120 + i * 90;
        return (
          <g key={i} opacity={0.9}>
            <ellipse cx={x} cy={y} rx={110} ry={36} fill="#fff" />
            <ellipse cx={x + 70} cy={y - 18} rx={70} ry={28} fill="#fff" />
          </g>
        );
      })}
      {/* gramado verde */}
      <path d="M0 760 Q 480 700 960 760 T 1920 760 L 1920 1080 L 0 1080 Z" fill={PALETA_ESPACO.chaoTerra} />
      <path d="M0 810 Q 480 760 960 812 T 1920 808 L 1920 1080 L 0 1080 Z" fill="#7ab856" />
      {/* tufos de grama que balançam */}
      {Array.from({ length: 14 }, (_, i) => {
        const x = 80 + i * 140;
        const inclina = oscila(frame + i * 9, 30, 4);
        return (
          <path
            key={i}
            d={`M${x} 880 Q ${x + inclina} 850 ${x + inclina * 2} 838`}
            stroke="#5f9a3e"
            strokeWidth={5}
            fill="none"
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * BALÃO DE FALA DIVERTIDO — usado para gritos ("Tchim!", "Nhaque!").
 * ------------------------------------------------------------------------- */
export const BalaoGrito: React.FC<{
  texto: string;
  x: number;
  y: number;
  /** 0..1 de entrada (fade + pop) */
  entrada: number;
}> = ({ texto, x, y, entrada }) => {
  const escala = 0.5 + entrada * 0.5;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `scale(${escala})`,
        opacity: entrada,
        background: "#fff",
        borderRadius: 999,
        padding: "10px 30px",
        border: `6px solid ${PALETA_ESPACO.naveDourado}`,
        fontFamily: "sans-serif",
        fontWeight: 800,
        fontSize: 52,
        color: PALETA_ESPACO.ceuEspaco,
        whiteSpace: "nowrap",
      }}
    >
      {texto}
    </div>
  );
};

/** Interpolação de entrada helper para balões (usa frame LOCAL da cena). */
export const entradaBalao = (frame: number, inicio: number): number =>
  interpolate(frame, [inicio, inicio + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
