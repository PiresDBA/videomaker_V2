/**
 * MANUAL — fundamentosCenaTrem.ts
 * ---------------------------------------------------------------------------
 * O QUE FAZ
 *   Base de dados e funções puras das cenas 3D do vídeo "Quatro Estações na
 *   Janela do Trem", seguindo a especificação técnica do Diretor-Arte
 *   (public/assets/especificacao-tecnica-quatro-estacoes.md, seções 3 a 6):
 *   câmera FOV 38 em (0, 1.55, 3.2) mirando (0, 1.45, 0), paleta Grand Budapest,
 *   luz exterior por estação, partículas por estação e texturas do ComfyUI.
 *
 * COMO USAR
 *   const est = PALETAS_EXTERIOR.inverno;        // cores do mundo lá fora
 *   const x = deslizarPassagem(frame, 1.2, 90);  // parallax de uma camada
 *   const mapa = useTexturaOpcional("assets/texturas/campo-inverno.png");
 *
 * ENTRADA / SAÍDA
 *   Entrada: frame (sempre por argumento) e nomes de textura.
 *   Saída: constantes tipadas + números determinísticos + textura opcional.
 *
 * REGRAS RESPEITADAS
 *   - Zero useFrame(): nenhuma função aqui usa relógio; tudo recebe frame.
 *   - Textura ausente = fallback para cor sólida; o render nunca pendura.
 *   - Nomes de arquivo batem com o que o bot 3 grava em public/assets/texturas/.
 */

// delayRender/continueRender: seguram o frame até a textura carregar (ou falhar).
import { continueRender, delayRender, staticFile } from "remotion";
// useEffect/useState controlam o ciclo de vida do carregamento.
import { useEffect, useState } from "react";
// Loader e tipo de textura do Three.js.
import * as THREE from "three";

// ---------------------------------------------------------------------------
// Chaves de estação usadas em todo o kit 3D.
// ---------------------------------------------------------------------------
export type EstacaoTrem = "primavera" | "verao" | "outono" | "inverno" | "retorno";

// Tipo de partícula do ar — espelha a tabela 6.4 da especificação.
export type ParticulaEstacao = "petala" | "polen" | "folha" | "neve" | "brilho";

// ---------------------------------------------------------------------------
// Paleta fixa do vagão (seção 5): rosa empoeirado + mogno + esmeralda + latão.
// Nenhum preto puro: sombra é ameixa escura.
// ---------------------------------------------------------------------------
export const CORES_VAGAO = {
  parede: "#E3A9A6", // rosa empoeirado das paredes
  madeira: "#8C5A3C", // mogno quente (mesa, rodapé, caixilho)
  estofado: "#1F5C4D", // esmeralda profundo do banco
  latao: "#D9A441", // mostarda latão — assinatura em todo plano
  creme: "#F5E9DC", // creme papel (xícara, textos)
  sombra: "#3B1F2B", // ameixa escura (nunca #000)
  vidro: "#DCEBDA", // tinta neutra do vidro
} as const;

// ---------------------------------------------------------------------------
// Paleta e luz do MUNDO EXTERIOR por estação (seção 4 e 5 da especificação).
// ---------------------------------------------------------------------------
export interface PaletaExterior {
  /** Cor do topo do céu. */
  ceuTopo: string;
  /** Cor do céu junto ao horizonte. */
  ceuBase: string;
  /** Disco solar. */
  sol: string;
  /** Halo em volta do sol. */
  halo: string;
  /** Silhueta de montanhas distantes (z ≈ -90). */
  montanha: string;
  /** Colinas médias (z ≈ -45). */
  colina: string;
  /** Fileira de árvores (z ≈ -16). */
  arvores: string;
  /** Campo/textura de chão (z ≈ -90, plano largo). */
  campo: string;
  /** Cor da luz que atravessa o vidro (rim light da mesa/xícara). */
  luzJanela: string;
  /** Cor da luz ambiente que entra. */
  luzAmbiente: string;
  /** Intensidade da luz direcional externa. */
  intensidadeLuz: number;
  /** Partícula característica da estação. */
  particula: ParticulaEstacao;
  /** Textura de campo tileável gerada pelo bot 3. */
  texturaCampo: string;
}

export const PALETAS_EXTERIOR: Record<EstacaoTrem, PaletaExterior> = {
  // 01 Primavera — manhã alta, luz verde-pálida 6200 K.
  primavera: {
    ceuTopo: "#DCEBDA",
    ceuBase: "#F3B6C4",
    sol: "#FFF3C4",
    halo: "#FFE6EF",
    montanha: "#A7D8A0",
    colina: "#7CC487",
    arvores: "#3F8D5C",
    campo: "#8FBF6A",
    luzJanela: "#DCEBDA",
    luzAmbiente: "#FBE7EF",
    intensidadeLuz: 1.7,
    particula: "petala",
    texturaCampo: "assets/texturas/campo-primavera.png",
  },
  // 02 Verão — golden hour, luz #FFC061 rasante (12°).
  verao: {
    ceuTopo: "#2E7D6E",
    ceuBase: "#FFE9A8",
    sol: "#E9B44C",
    halo: "#FFD98A",
    montanha: "#C8862E",
    colina: "#E9B44C",
    arvores: "#2E7D6E",
    campo: "#E9B44C",
    luzJanela: "#FFC061",
    luzAmbiente: "#FFE9C2",
    intensidadeLuz: 2.4,
    particula: "polen",
    texturaCampo: "assets/texturas/campo-verao.png",
  },
  // 03 Outono — tarde baixa 4300 K, luz #F0A05A muito rasante (8°).
  outono: {
    ceuTopo: "#7A2E2E",
    ceuBase: "#E8C878",
    sol: "#E08A2E",
    halo: "#F2C07A",
    montanha: "#7A2E2E",
    colina: "#C75B39",
    arvores: "#E08A2E",
    campo: "#C75B39",
    luzJanela: "#F0A05A",
    luzAmbiente: "#F2C6A2",
    intensidadeLuz: 1.9,
    particula: "folha",
    texturaCampo: "assets/texturas/campo-outono.png",
  },
  // 04 Inverno — blue hour 7800 K, luz #BFD6E8 (25° plano, sombra chapada).
  inverno: {
    ceuTopo: "#BFD9E6",
    ceuBase: "#F2EFE9",
    sol: "#FFFDF6",
    halo: "#DCD3E8",
    montanha: "#7E93A6",
    colina: "#BFD9E6",
    arvores: "#456079",
    campo: "#DCD3E8",
    luzJanela: "#BFD6E8",
    luzAmbiente: "#CFE0EE", // fill extra da neve (seção 4, item 4)
    intensidadeLuz: 1.1,
    particula: "neve",
    texturaCampo: "assets/texturas/campo-inverno.png",
  },
  // 05 Retorno — amanhecer 5000→6200 K, sol mostarda voltando ao ciclo.
  retorno: {
    ceuTopo: "#EAF2E4",
    ceuBase: "#FFD9B8",
    sol: "#D9A441",
    halo: "#FFE7C2",
    montanha: "#8FB085",
    colina: "#B2C9A8",
    arvores: "#4B7A55",
    campo: "#EAF2E4",
    luzJanela: "#FFD9B8",
    luzAmbiente: "#FBE3CE",
    intensidadeLuz: 2,
    particula: "brilho",
    texturaCampo: "assets/texturas/campo-retorno.png",
  },
};

// ---------------------------------------------------------------------------
// Funções puras usadas pelas cenas (todas determinísticas).
// ---------------------------------------------------------------------------

/**
 * Deslocamento lateral cíclico de uma camada de parallax.
 * Devolve um valor em [0, intervalo): a camada "volta" pela esquerda ao sair.
 */
export function deslizarPassagem(
  frame: number,
  velocidade: number,
  intervalo: number,
  defasagem = 0,
): number {
  const bruto = (frame * velocidade + defasagem) % intervalo; // módulo cíclico
  return bruto < 0 ? bruto + intervalo : bruto; // corrige módulo negativo do JS
}

/** Ruído determinístico em [0,1): mesma semente + índice = mesmo pixel. */
export function ruidoDeterministico(indice: number, semente: number): number {
  const bruto = Math.sin((indice + 1) * (12.9898 + semente) * 78.233) * 43758.5453;
  return bruto - Math.floor(bruto);
}

// Partícula com posição-base, raio e fase de queda.
export interface ParticulaCena {
  x: number;
  y: number;
  z: number;
  raio: number;
  fase: number;
}

/**
 * Gera a nuvem de partículas (pétalas, pólen, folhas, neve, brilho) no volume
 * visível pela janela. Quantidades seguem a tabela 6.4 da especificação.
 */
export function montarParticulas(quantidade: number, semente: number): ParticulaCena[] {
  const lista: ParticulaCena[] = [];
  for (let i = 0; i < quantidade; i += 1) {
    lista.push({
      x: -6 + ruidoDeterministico(i, semente) * 12, // coluna da janela
      y: -0.5 + ruidoDeterministico(i, semente + 1) * 4.2, // altura visível
      z: -2.2 - ruidoDeterministico(i, semente + 2) * 6, // atrás do vidro
      raio: 0.02 + ruidoDeterministico(i, semente + 3) * 0.04, // tamanho do grão
      fase: ruidoDeterministico(i, semente + 4), // defasagem da queda
    });
  }
  return lista;
}

/** Quantidade de partículas por estação (tabela 6.4, limitada a 260). */
export const PARTICULAS_POR_ESTACAO: Record<EstacaoTrem, number> = {
  primavera: 120, // pétalas
  verao: 160, // pólen (200 na spec; 160 mantém o render leve)
  outono: 150, // folhas
  inverno: 240, // neve (260 na spec; 240 mantém o render leve)
  retorno: 100, // brilho
};

/**
 * Carrega uma textura pública de forma opcional e segura para o Remotion.
 * Sem caminho, ou com arquivo ausente, devolve null e a cena usa cor sólida.
 */
export function useTexturaOpcional(caminhoPublico?: string): THREE.Texture | null {
  const [textura, setTextura] = useState<THREE.Texture | null>(null);

  useEffect(() => {
    if (!caminhoPublico) {
      setTextura(null); // sem textura: paleta manda
      return;
    }

    const handle = delayRender(`textura 3d: ${caminhoPublico}`); // segura o frame
    let liberado = false;
    const liberar = () => {
      if (!liberado) {
        liberado = true;
        continueRender(handle);
      }
    };

    const loader = new THREE.TextureLoader();
    loader.load(
      staticFile(caminhoPublico),
      (carregada) => {
        carregada.colorSpace = THREE.SRGBColorSpace; // cor correta no vídeo
        carregada.wrapS = THREE.RepeatWrapping; // campo tileável (spec 6.3)
        carregada.wrapT = THREE.ClampToEdgeWrapping;
        setTextura(carregada);
        liberar();
      },
      undefined,
      () => {
        setTextura(null); // arquivo ainda não gerado: segue com a paleta
        liberar();
      },
    );

    return () => liberar(); // desmontou antes de carregar: solta o frame
  }, [caminhoPublico]);

  return textura;
}

/** Frame -> progresso 0..1 com clamp (evita interpolação fora da sequência). */
export function progressoSuave(
  frame: number,
  duracaoEmFrames: number,
  inicio = 0,
  fim = 1,
): number {
  const total = Math.max(1, duracaoEmFrames); // nunca divide por zero
  const bruto = frame / total;
  const limitado = bruto < 0 ? 0 : bruto > 1 ? 1 : bruto;
  return inicio + (fim - inicio) * limitado;
}
