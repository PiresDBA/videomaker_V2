/**
 * MANUAL — PersonagensEspaco.tsx
 * ==============================
 * O que faz
 * ---------
 * Luna e Frida nas cenas da historinha, agora com os CORPOS OFICIAIS do
 * StickFilms (sprite sheets desenhadas pelo artista do canal — o pedido do
 * usuário depois da rejeição da versão SVG "tosca"). As antigas elipses de
 * recorte saíram: nada de desenho amador.
 *
 * Como funciona
 * --------------
 * Cada componente mantém a assinatura antiga (modo, escala, deslocX,
 * ancorarDireita) para as cenas não mudarem, e traduz o modo em um movimento
 * do catálogo de sprites:
 *   decolagem -> correr | flutuar -> divertir | nadar -> andar
 *   girar -> rolar | sentado -> parado | pousado -> pular
 * Além do ciclo de poses, cada corpo flutua no espaço (sobe/desce e gira
 * devagar por seno do frame), porque a cena é em gravidade zero.
 *
 * Narrador
 * --------
 * NarradorLunaDetalhada: Luna sentada de perfil redesenhada com pescoço
 * integrado ao corpo, sombreado por gradientes, orelha e rabo animados e boca
 * sincronizada pela energia RMS da narração (prop aberturaBoca).
 *
 * Regra de frame
 * --------------
 * Tudo deriva de useCurrentFrame() ou do frame por prop; sem useFrame().
 */

import { useCurrentFrame } from "remotion";
import { SpritePersonagem } from "../personagens-stickfilms/SpritePersonagem";
import { PALETA_ESPACO } from "./roteiroHistoriaEspaco";

export type ModoPersonagem =
  | "decolagem"
  | "flutuar"
  | "nadar"
  | "girar"
  | "sentado"
  | "pousado";

/** Propriedades comuns dos personagens (compatíveis com as cenas antigas). */
export interface PropsPersonagem {
  /** Coreografia contínua do trecho. */
  modo: ModoPersonagem;
  /** Multiplicador do tamanho (a altura base vem do sprite). */
  escala?: number;
  /** Deslocamento horizontal opcional em px. */
  deslocX?: number;
  /** Wrapper posicionado por `right`: ancora o SVG no lado direito dele. */
  ancorarDireita?: boolean;
}

/** Oscilação helper: seno entre -amplitude e +amplitude com período em frames. */
const oscila = (frame: number, periodo: number, amplitude: number, fase = 0) =>
  Math.sin(((frame + fase) / periodo) * Math.PI * 2) * amplitude;

/** Tradução do modo da cena para o movimento da sprite sheet. */
const movimentoDoModo = (modo: ModoPersonagem): string => {
  switch (modo) {
    case "decolagem": return "correr";
    case "nadar": return "andar";
    case "girar": return "rolar";
    case "sentado": return "parado";
    case "pousado": return "pular";
    case "flutuar":
    default: return "divertir";
  }
};

/** Corpo de recorte de uma personagem oficial em movimento + flutuação. */
const CorpoSprite: React.FC<{
  personagem: "luna" | "frida";
  modo: ModoPersonagem;
  escala: number;
  deslocX: number;
  ancorarDireita: boolean;
  /** altura base do sprite em px (Luna é maior que Frida) */
  alturaBase: number;
  fase: number;
}> = ({ personagem, modo, escala, deslocX, ancorarDireita, alturaBase, fase }) => {
  const frame = useCurrentFrame();
  // gravidade zero: flutuação suave sempre presente, mais forte no modo flutuar
  const forte = modo === "flutuar" || modo === "girar";
  const flutua = oscila(frame, forte ? 90 : 120, forte ? 22 : 10, fase);
  const gira = forte ? oscila(frame, 130, 7, fase) : oscila(frame, 150, 2, fase);
  const alturaCaixa = Math.round(alturaBase * escala);
  return (
    <div
      style={{
        position: "absolute",
        ...(ancorarDireita ? { right: 0 } : { left: deslocX }),
        bottom: 0,
        height: alturaCaixa,
        transform: `translateY(${flutua}px) rotate(${gira}deg)`,
        overflow: "visible",
      }}
    >
      <div style={{ position: "relative", height: "100%", overflow: "visible" }}>
        <SpritePersonagem
          personagem={personagem}
          movimento={movimentoDoModo(modo)}
          lado={personagem === "frida" ? "direita" : "esquerda"}
          frame={frame}
          altura={alturaCaixa}
        />
      </div>
    </div>
  );
};

/** Luna (salsicha marrom, sprites oficiais). */
export const LuninhaSalsicha: React.FC<PropsPersonagem> = ({
  modo,
  escala = 1,
  deslocX = 0,
  ancorarDireita = false,
}) => (
  <CorpoSprite personagem="luna" modo={modo} escala={escala} deslocX={deslocX} ancorarDireita={ancorarDireita} alturaBase={420} fase={0} />
);

/** Frida (buldogue inglesa, sprites oficiais). */
export const FridocaBuldogue: React.FC<PropsPersonagem> = ({
  modo,
  escala = 1,
  deslocX = 0,
  ancorarDireita = false,
}) => (
  <CorpoSprite personagem="frida" modo={modo} escala={escala} deslocX={deslocX} ancorarDireita={ancorarDireita} alturaBase={300} fase={45} />
);

/* ---------------------------------------------------------------------------
 * NARRADORA LUNA — redesenhada: corpo completo com pescoço integrado,
 * sombreado em gradientes, olho expressivo, orelha que balança, rabo que
 * abana e boca sincronizada pela aberturaBoca (energia RMS da narração).
 * ViewBox 320x360, sentada de perfil olhando para a direita.
 * ------------------------------------------------------------------------- */
export const NarradorLunaDetalhada: React.FC<{ aberturaBoca: number; frameLocal: number }> = ({
  aberturaBoca,
  frameLocal,
}) => {
  const frame = frameLocal;
  const abertura = Math.max(0, Math.min(1, aberturaBoca));
  // orelha balança, rabo abana rápido, respiração sobe e desce
  const orelha = oscila(frame, 14, 9);
  const rabo = oscila(frame, 8, 14);
  const respiracao = oscila(frame, 60, 2);
  // boca: elipse que abre de verdade com a voz
  const bocaAltura = 4 + abertura * 22;
  const bocaLargura = 16 - abertura * 3;

  return (
    <svg width={320} height={360} viewBox="0 0 320 360" style={{ display: "block", overflow: "visible" }}>
      <defs>
        <linearGradient id="luna-pelo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a06a3f" />
          <stop offset="55%" stopColor="#8a5a33" />
          <stop offset="100%" stopColor="#6e4522" />
        </linearGradient>
        <linearGradient id="luna-orelha" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8a5a33" />
          <stop offset="100%" stopColor="#5e3a1d" />
        </linearGradient>
        <radialGradient id="luna-brilho-olho" cx="35%" cy="35%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="60%" stopColor="#f7e6c8" />
          <stop offset="100%" stopColor="#d9c39a" />
        </radialGradient>
      </defs>

      <g transform={`translate(0 ${respiracao})`}>
        {/* rabo comprido que abana (atras do corpo) */}
        <g transform={`rotate(${rabo} 66 268)`}>
          <path d="M66 268 Q 18 250 8 196 Q 14 150 34 132 Q 26 178 40 214 Q 52 244 74 256 Z" fill="url(#luna-pelo)" stroke="#4a2c14" strokeWidth="2.5" />
        </g>

        {/* corpo sentado (perna dobrada à frente) */}
        <path d="M96 262 Q 84 220 104 192 Q 128 168 168 170 Q 212 172 226 202 Q 238 230 228 262 Q 214 292 162 294 Q 116 292 96 262 Z" fill="url(#luna-pelo)" stroke="#4a2c14" strokeWidth="2.5" />
        {/* peito com sombra clara sutil (sem "mancha" de cor diferente) */}
        <path d="M150 200 Q 176 190 196 202 Q 204 226 194 250 Q 172 258 152 248 Q 142 222 150 200 Z" fill="#96622f" opacity="0.55" />
        {/* pata dianteira apoiada */}
        <path d="M150 292 Q 150 268 168 262 Q 190 258 202 272 L 204 292 Q 178 300 150 292 Z" fill="#8a5a33" stroke="#4a2c14" strokeWidth="2.5" />
        <path d="M156 292 Q 170 296 196 292" stroke="#4a2c14" strokeWidth="2" fill="none" />
        {/* dedinhos */}
        <path d="M170 293 L 170 286 M182 293 L 182 285" stroke="#4a2c14" strokeWidth="2" strokeLinecap="round" />

        {/* PESCOÇO — integra cabeça e corpo (a crítica era "sem pescoço") */}
        <path d="M196 176 Q 200 148 208 128 L 248 132 Q 244 158 240 184 Q 220 192 196 176 Z" fill="url(#luna-pelo)" stroke="#4a2c14" strokeWidth="2.5" />

        {/* cabeça (perfil, focinho para a direita) */}
        <g transform={`translate(222 96) scale(0.85) translate(-222 -96) rotate(${oscila(frame, 120, 2)} 222 96)`}>
          {/* crânio */}
          <path d="M196 96 Q 196 48 236 42 Q 274 38 288 66 Q 296 84 292 100 L 288 118 Q 268 132 236 130 Q 206 128 196 96 Z" fill="url(#luna-pelo)" stroke="#4a2c14" strokeWidth="2.5" />
          {/* focinho */}
          <path d="M286 84 Q 306 88 308 102 Q 308 116 292 120 Q 284 122 282 112 L 282 96 Z" fill="#a06a3f" stroke="#4a2c14" strokeWidth="2.5" />
          <ellipse cx={303} cy={97} rx={6.5} ry={5.5} fill="#2a1c10" />
          <path d="M296 112 Q 304 118 310 114" stroke="#4a2c14" strokeWidth="2.2" fill="none" strokeLinecap="round" />
          {/* boca que FALA (abre com a voz) */}
          <path d={`M288 118 Q 296 ${118 + bocaAltura} 308 ${114 + bocaAltura * 0.6} Q 306 126 292 126 Q 286 124 288 118 Z`} fill="#5e2a20" stroke="#4a2c14" strokeWidth="2" />
          {abertura > 0.35 && <ellipse cx={298} cy={118 + bocaAltura * 0.55} rx={bocaLargura * 0.4} ry={bocaAltura * 0.3} fill="#c4523f" />}
          {/* orelha comprida caída que balança */}
          <g transform={`rotate(${orelha} 226 52)`}>
            <path d="M226 50 Q 194 56 186 108 Q 182 148 200 168 Q 220 158 228 116 Q 234 84 240 60 Z" fill="url(#luna-orelha)" stroke="#3d2410" strokeWidth="2.5" />
          </g>
          {/* olho grande expressivo com brilho */}
          <ellipse cx={252} cy={82} rx={13} ry={14} fill="url(#luna-brilho-olho)" stroke="#4a2c14" strokeWidth="2.5" />
          <circle cx={255} cy={84} r={6.5} fill="#2a1c10" />
          <circle cx={252} cy={79} r={2.6} fill="#ffffff" />
          <circle cx={258} cy={88} r={1.4} fill="#ffffff" opacity="0.85" />
          {/* sobrancelha */}
          <path d="M240 60 Q 252 54 264 60" stroke="#4a2c14" strokeWidth="2.5" fill="none" strokeLinecap="round" />
          {/* bandana mostarda no pescoço */}
          <path d="M204 128 Q 226 142 246 132 Q 242 148 224 152 Q 208 148 204 128 Z" fill="#d9a231" stroke="#8a5f14" strokeWidth="2" />
          <path d="M246 132 L 262 140 L 254 146 Z" fill="#c98f22" stroke="#8a5f14" strokeWidth="1.5" />
        </g>
      </g>
    </svg>
  );
};

/* ---------------------------------------------------------------------------
 * OSO DE BISCOITO — premio voador das cenas de biscoitos.
 * ------------------------------------------------------------------------- */
export const OsoBiscoito: React.FC<{
  x: number;
  y: number;
  rotacao?: number;
  escala?: number;
}> = ({ x, y, rotacao = 0, escala = 1 }) => (
  <svg
    width={64 * escala}
    height={36 * escala}
    viewBox="0 0 64 36"
    style={{ position: "absolute", left: x, top: y, overflow: "visible" }}
  >
    <g transform={`rotate(${rotacao} 32 18)`}>
      <rect x={20} y={12} width={24} height={12} rx={6} fill="#d9a24b" />
      <circle cx={14} cy={14} r={8} fill="#d9a24b" />
      <circle cx={14} cy={14} r={3} fill="#8a5a22" />
      <circle cx={14} cy={24} r={8} fill="#d9a24b" />
      <circle cx={14} cy={24} r={3} fill="#8a5a22" />
      <circle cx={50} cy={14} r={8} fill="#d9a24b" />
      <circle cx={50} cy={14} r={3} fill="#8a5a22" />
      <circle cx={50} cy={24} r={8} fill="#d9a24b" />
      <circle cx={50} cy={24} r={3} fill="#8a5a22" />
    </g>
  </svg>
);

/* ---------------------------------------------------------------------------
 * NOTA MUSICAL — para a caixinha de musica da cena do botao amarelo.
 * ------------------------------------------------------------------------- */
export const NotaMusical: React.FC<{
  x: number;
  y: number;
  opacidade?: number;
  cor?: string;
  escala?: number;
}> = ({ x, y, opacidade = 1, cor = "#ffd24d", escala = 1 }) => (
  <svg
    width={36 * escala}
    height={44 * escala}
    viewBox="0 0 36 44"
    style={{ position: "absolute", left: x, top: y, opacity: opacidade, overflow: "visible" }}
  >
    <ellipse cx={12} cy={36} rx={10} ry={8} fill={cor} />
    <rect x={20} y={4} width={4} height={32} rx={2} fill={cor} />
    <path d="M24 6 Q 34 10 32 20 Q 28 12 20 12 Z" fill={cor} />
  </svg>
);
