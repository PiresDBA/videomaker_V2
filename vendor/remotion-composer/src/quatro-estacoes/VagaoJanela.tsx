/* ============================================================================
 * MANUAL — VagaoJanela.tsx
 * ----------------------------------------------------------------------------
 * O cenário do vídeo: o interior de um vagão de trem visto de frente, com uma
 * janela central por onde passa a paisagem da estação. Estilo Grand Budapest
 * Hotel: composição simétrica, marfim, rosa, mostarda e latão.
 *
 * POR QUE UM CENÁRIO SÓ
 *   O filme inteiro é um plano fixo. A paisagem muda, a luz muda, o mundo passa
 *   — o vagão não. Isso dá a unidade que o Wes Anderson usa: o quadro é um
 *   palco, e a estação é o espetáculo.
 *
 * O QUE ELE DESENHA (de trás para frente)
 *   1. céu em gradiente da estação
 *   2. sol com halo
 *   3. três colinas em parallax (longe, meio, perto)
 *   4. partículas da estação (ParticulasEstacao)
 *   5. vidro: reflexo diagonal que atravessa a janela
 *   6. parede do vagão, moldura de latão e cortinas
 *   7. mesa, toalha, xícara e vapor
 *   8. vinheta e vibração do trem
 *
 * MOVIMENTO
 *   Tudo sai de useCurrentFrame(): a paisagem corre à direita→esquerda em
 *   px/segundo, ajustada por `fatorVelocidade` para cenas curtas não ficarem
 *   paradas. O trem vibra 1 px num ciclo de 6 frames.
 *
 * CONTRATO COM O DEV-3D-CRAFT
 *   Este componente é o piso, não o teto. O 3D entra como camada opcional no
 *   lugar do grupo "paisagem" (ver handoffs/HANDOFF-dev-3d-craft.md). Enquanto
 *   não houver cena 3D, este desenho em CSS/SVG renderiza sozinho.
 * ========================================================================== */

import { Img, interpolate, useCurrentFrame } from "remotion";
import { useState } from "react";

import { PALETA_BASE, PALETAS, type Estacao } from "./roteiro";
import { ParticulasEstacao, type TipoParticula } from "./ParticulasEstacao";

type Props = {
  /** Estação que define céu, colinas e partículas. */
  estacao: Estacao;
  /** Etiqueta da cena ("A PARTIDA"). */
  titulo: string;
  /** Numeral romano da cena ("I"). */
  numeral: string;
  /** Duração da cena em segundos: normaliza a velocidade do trem. */
  segundos: number;
  /** Segundos já decorridos da cena (frame / fps). */
  decorridoSegundos: number;
  /** 0..1 do progresso da cena. */
  progresso: number;
  /** Fundo pintado pelo ComfyUI. Sem ele, o céu é gradiente puro. */
  texturaSrc?: string;
};

/** Geometria fixa do quadro (px). Mexer aqui mexe no filme inteiro. */
const GEO = {
  janelaX: 500,
  janelaY: 190,
  janelaL: 920,
  janelaA: 560,
  moldura: 14,
  trilhoY: 158,
  mesaY: 772,
} as const;

/** Velocidade do trem por banda de profundidade, em px por segundo. */
const VELOCIDADES = { longe: 26, meio: 58, perto: 112 } as const;

/** Partícula que cada estação usa. */
const PARTICULA_POR_ESTACAO: Record<Estacao, TipoParticula> = {
  primavera: "petala",
  verao: "poeira",
  outono: "folha",
  inverno: "neve",
  retorno: "petala",
};

/** Densidade de partículas por estação (0..1). */
const DENSIDADE: Record<Estacao, number> = {
  primavera: 0.8,
  verao: 0.35,
  outono: 0.95,
  inverno: 1,
  retorno: 0.6,
};

/**
 * Gera uma crista de colina como caminho SVG fechado, preenchido até a base.
 * Soma de senos com sementes diferentes por banda: nenhuma colina se repete e
 * o resultado é determinístico (nada de random em render).
 */
function caminhoColina(
  semente: number,
  largura: number,
  base: number,
  alturaMedia: number,
  amplitude: number
): string {
  const passo = 40;
  const pontos: string[] = [`M0,${base}`];
  for (let x = 0; x <= largura; x += passo) {
    const onda =
      Math.sin(x / (180 + semente * 37) + semente) * amplitude +
      Math.sin(x / (90 + semente * 13) + semente * 2.3) * (amplitude * 0.45);
    const y = base - alturaMedia + onda;
    pontos.push(`L${x},${y.toFixed(1)}`);
  }
  pontos.push(`L${largura},${base}`, "Z");
  return pontos.join(" ");
}

/** Uma banda de colina que se repete três vezes para nunca mostrar emenda. */
const Colina: React.FC<{
  cor: string;
  semente: number;
  base: number;
  alturaMedia: number;
  amplitude: number;
  deslocamento: number;
}> = ({ cor, semente, base, alturaMedia, amplitude, deslocamento }) => {
  const largura = GEO.janelaL;
  const caminho = caminhoColina(semente, largura, base, alturaMedia, amplitude);
  return (
    <svg
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: largura * 3,
        height: GEO.janelaA,
        transform: `translateX(${-deslocamento}px)`,
      }}
      viewBox={`0 0 ${largura * 3} ${GEO.janelaA}`}
      preserveAspectRatio="none"
    >
      {[0, 1, 2].map((tile) => (
        <path
          key={tile}
          d={caminho}
          fill={cor}
          transform={`translate(${tile * largura} 0)`}
        />
      ))}
    </svg>
  );
};

export const VagaoJanela: React.FC<Props> = ({
  estacao,
  titulo,
  numeral,
  segundos,
  decorridoSegundos,
  progresso,
  texturaSrc,
}) => {
  const frame = useCurrentFrame();
  const paleta = PALETAS[estacao];

  // Cenas curtas correm um pouco mais rápido, para todas atravessarem a mesma
  // quantidade de paisagem. Faixa estreita: 0,75x a 1,35x.
  const fatorVelocidade = Math.max(0.75, Math.min(1.35, 24 / Math.max(1, segundos)));

  // Se a textura não existir (ou falhar), o desenho continua em gradiente.
  const [texturaFalhou, setTexturaFalhou] = useState(false);
  const mostrarTextura = Boolean(texturaSrc) && !texturaFalhou;

  // Vibração do trem: 1 px num ciclo de 6 frames (0,2 s a 30 fps).
  const vibracao = Math.sin(frame / 6) * 1.1;

  // Reflexo no vidro atravessa a janela uma vez por cena.
  const reflexoX = interpolate(progresso, [0, 1], [-40, 130]);

  // Vapor da xícara: sobe e oscila, com opacidade própria.
  const vaporOpacidade = 0.28 + Math.sin(frame / 9) * 0.12;
  const vaporDeslocamento = Math.sin(frame / 14) * 6;

  // Deslocamento das três bandas de paisagem.
  const deslocamentoLonge =
    (decorridoSegundos * VELOCIDADES.longe * fatorVelocidade) % GEO.janelaL;
  const deslocamentoMeio =
    (decorridoSegundos * VELOCIDADES.meio * fatorVelocidade) % GEO.janelaL;
  const deslocamentoPerto =
    (decorridoSegundos * VELOCIDADES.perto * fatorVelocidade) % GEO.janelaL;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: PALETA_BASE.marfim,
        overflow: "hidden",
      }}
    >
      {/* PAREDE: listras verticais discretas, como papel de parede.       */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `repeating-linear-gradient(90deg,
            ${PALETA_BASE.marfim} 0px,
            ${PALETA_BASE.marfim} 46px,
            ${PALETA_BASE.marfimSombra} 46px,
            ${PALETA_BASE.marfimSombra} 48px)`,
          opacity: 0.9,
        }}
      />

      {/* GRUPO DO CENÁRIO: vibra junto com o trem.                       */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translateY(${vibracao}px)`,
        }}
      >
        {/* JANELA: recorte por onde se vê o mundo. */}
        <div
          style={{
            position: "absolute",
            left: GEO.janelaX,
            top: GEO.janelaY,
            width: GEO.janelaL,
            height: GEO.janelaA,
            borderRadius: 18,
            overflow: "hidden",
            backgroundColor: paleta.ceuBase,
            boxShadow:
              "inset 0 0 0 2px rgba(58,42,33,0.18), inset 0 18px 40px rgba(58,42,33,0.16)",
          }}
        >
          {/* 1. Céu: gradiente da estação. */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `linear-gradient(180deg, ${paleta.ceuTopo} 0%, ${paleta.ceuBase} 62%, ${paleta.terra} 100%)`,
            }}
          />

          {/* Fundo pintado do ComfyUI, quando existir. Parallax lento. */}
          {mostrarTextura && (
            <Img
              src={texturaSrc as string}
              onError={() => setTexturaFalhou(true)}
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                objectFit: "cover",
                transform: `translateX(${-Math.min(
                  60,
                  decorridoSegundos * VELOCIDADES.longe * 0.6 * fatorVelocidade
                )}px) scale(1.12)`,
              }}
            />
          )}

          {/* 2. Sol com halo: desce devagar ao longo da cena. */}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: interpolate(progresso, [0, 1], [88, 128]),
              width: 150,
              height: 150,
              marginLeft: -75,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${paleta.sol} 0%, ${paleta.sol} 34%, rgba(255,255,255,0) 70%)`,
              opacity: 0.9,
            }}
          />

          {/* 3. Colinas em parallax. */}
          <Colina
            cor={paleta.longe}
            semente={1}
            base={GEO.janelaA}
            alturaMedia={150}
            amplitude={22}
            deslocamento={deslocamentoLonge}
          />
          <Colina
            cor={paleta.terra}
            semente={2}
            base={GEO.janelaA + 10}
            alturaMedia={96}
            amplitude={18}
            deslocamento={deslocamentoMeio}
          />
          <Colina
            cor={PALETA_BASE.chocolate}
            semente={3}
            base={GEO.janelaA + 26}
            alturaMedia={52}
            amplitude={12}
            deslocamento={deslocamentoPerto}
          />

          {/* 4. Partículas da estação, coladas ao vidro. */}
          <ParticulasEstacao
            cor={paleta.particula}
            tipo={PARTICULA_POR_ESTACAO[estacao]}
            progresso={progresso}
            intensidade={DENSIDADE[estacao]}
          />

          {/* 5. Reflexo do vidro: faixa branca que atravessa devagar. */}
          <div
            style={{
              position: "absolute",
              top: "-20%",
              left: `${reflexoX}%`,
              width: "46%",
              height: "140%",
              background:
                "linear-gradient(104deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.16) 42%, rgba(255,255,255,0.30) 50%, rgba(255,255,255,0) 58%)",
              transform: "rotate(2deg)",
            }}
          />
        </div>

        {/* MOLDURA DE LATÃO da janela (por fora do recorte). */}
        <div
          style={{
            position: "absolute",
            left: GEO.janelaX - GEO.moldura,
            top: GEO.janelaY - GEO.moldura,
            width: GEO.janelaL + GEO.moldura * 2,
            height: GEO.janelaA + GEO.moldura * 2,
            borderRadius: 24,
            border: `${GEO.moldura}px solid ${PALETA_BASE.latao}`,
            boxShadow:
              "inset 0 0 0 2px rgba(58,42,33,0.25), 0 10px 24px rgba(58,42,33,0.22)",
          }}
        />

        {/* PEITORIL de latão sob a janela. */}
        <div
          style={{
            position: "absolute",
            left: GEO.janelaX - 34,
            top: GEO.janelaY + GEO.janelaA + GEO.moldura - 4,
            width: GEO.janelaL + 68,
            height: 18,
            borderRadius: 6,
            backgroundColor: PALETA_BASE.latao,
            boxShadow: "0 8px 16px rgba(58,42,33,0.18)",
          }}
        />

        {/* FILETE BORDÔ em volta da moldura: o "passe-partout" do filme. */}
        <div
          style={{
            position: "absolute",
            left: GEO.janelaX - 44,
            top: GEO.janelaY - 44,
            width: GEO.janelaL + 88,
            height: GEO.janelaA + 88,
            borderRadius: 30,
            border: `2px solid ${PALETA_BASE.bordo}`,
            opacity: 0.55,
          }}
        />

        {/* CORTINAS: trilho de latão, duas cortinas mostarda, dois laços. */}
        <div
          style={{
            position: "absolute",
            left: GEO.janelaX - 40,
            top: GEO.trilhoY,
            width: GEO.janelaL + 80,
            height: 10,
            borderRadius: 6,
            backgroundColor: PALETA_BASE.latao,
          }}
        />
        {[0, 1].map((lado) => (
          <div
            key={`cortina-${lado}`}
            style={{
              position: "absolute",
              left:
                lado === 0
                  ? GEO.janelaX - 78
                  : GEO.janelaX + GEO.janelaL - 30,
              top: GEO.trilhoY + 5,
              width: 108,
              height: GEO.janelaA - 40,
              background: `repeating-linear-gradient(90deg,
                ${PALETA_BASE.mostarda} 0px,
                ${PALETA_BASE.mostarda} 16px,
                #C08E28 16px,
                #C08E28 32px)`,
              borderTopLeftRadius: 10,
              borderTopRightRadius: 10,
              boxShadow: "inset 0 0 18px rgba(58,42,33,0.30)",
              transform: `translateX(${Math.sin(frame / 30 + lado) * 1.6}px)`,
              transformOrigin: "top center",
            }}
          />
        ))}
        {[0, 1].map((lado) => (
          <div
            key={`laco-${lado}`}
            style={{
              position: "absolute",
              left:
                lado === 0
                  ? GEO.janelaX - 78
                  : GEO.janelaX + GEO.janelaL - 30,
              top: GEO.trilhoY + 300,
              width: 108,
              height: 26,
              borderRadius: 8,
              backgroundColor: PALETA_BASE.bordo,
              opacity: 0.9,
            }}
          />
        ))}

        {/* MESA, TOALHA, XÍCARA E VAPOR. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: GEO.mesaY,
            width: "100%",
            height: 1080 - GEO.mesaY,
            background: `linear-gradient(180deg, ${PALETA_BASE.madeira} 0%, rgba(85,57,38,0.35) 30%, ${PALETA_BASE.madeira} 100%)`,
            boxShadow: "inset 0 14px 26px rgba(0,0,0,0.35)",
          }}
        />
        {/* Toalha de linho sobre a mesa. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: GEO.mesaY + 26,
            width: "100%",
            height: 1080 - GEO.mesaY - 26,
            background: `linear-gradient(180deg, ${PALETA_BASE.neve} 0%, ${PALETA_BASE.marfimSombra} 100%)`,
            borderTop: `3px solid ${PALETA_BASE.rosa}`,
          }}
        />
        {/* Listra bordô da toalha. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: GEO.mesaY + 96,
            width: "100%",
            height: 6,
            backgroundColor: PALETA_BASE.bordo,
            opacity: 0.35,
          }}
        />

        {/* Vapor da xícara (desenhado antes da xícara, atrás dela). */}
        <svg
          style={{
            position: "absolute",
            left: 870,
            top: 690,
            width: 220,
            height: 200,
            transform: `translate(${vaporDeslocamento}px, ${-Math.min(
              10,
              progresso * 10
            )}px)`,
            opacity: vaporOpacidade,
          }}
          viewBox="0 0 220 200"
        >
          {[0, 1, 2].map((i) => (
            <path
              key={`vapor-${i}`}
              d={`M${70 + i * 34},180 C${52 + i * 34},140 ${94 + i * 34},120 ${
                72 + i * 34
              },78 C${56 + i * 34},48 ${90 + i * 34},34 ${76 + i * 34},4`}
              stroke={PALETA_BASE.neve}
              strokeWidth={7 - i}
              strokeLinecap="round"
              fill="none"
            />
          ))}
        </svg>

        {/* Xícara + pires. */}
        <svg
          style={{
            position: "absolute",
            left: 860,
            top: 806,
            width: 240,
            height: 160,
          }}
          viewBox="0 0 240 160"
        >
          <ellipse cx="120" cy="128" rx="96" ry="20" fill={PALETA_BASE.neve} />
          <ellipse
            cx="120"
            cy="126"
            rx="96"
            ry="20"
            fill="none"
            stroke={PALETA_BASE.latao}
            strokeWidth="3"
          />
          <path
            d="M66,74 L174,74 C170,112 148,126 120,126 C92,126 70,112 66,74 Z"
            fill={PALETA_BASE.neve}
            stroke={PALETA_BASE.latao}
            strokeWidth="3"
          />
          <path
            d="M174,84 C202,84 202,112 174,112"
            fill="none"
            stroke={PALETA_BASE.latao}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <ellipse cx="120" cy="76" rx="52" ry="9" fill="#4A2C1B" />
          <rect x="68" y="98" width="104" height="4" fill={PALETA_BASE.rosa} />
        </svg>
      </div>

      {/* ETIQUETA DA CENA, no alto, centralizada (simetria GBH). */}
      <div
        style={{
          position: "absolute",
          top: 74,
          left: 0,
          width: "100%",
          textAlign: "center",
          fontFamily: "Space Grotesk, system-ui, sans-serif",
          letterSpacing: "0.42em",
          fontSize: 24,
          fontWeight: 700,
          color: PALETA_BASE.bordo,
          opacity: interpolate(progresso, [0, 0.08], [0, 0.9], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {numeral} · {titulo.toUpperCase()}
      </div>
      <div
        style={{
          position: "absolute",
          top: 116,
          left: "50%",
          width: 260,
          height: 2,
          marginLeft: -130,
          backgroundColor: PALETA_BASE.latao,
          opacity: 0.7,
        }}
      />

      {/* VINHETA: escurece as bordas e puxa o olho para a janela. */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 46%, rgba(58,42,33,0.42) 100%)",
          pointerEvents: "none",
        }}
      />
    </div>
  );
};
