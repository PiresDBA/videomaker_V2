/* ============================================================================
 * MANUAL — roteiro.ts
 * ----------------------------------------------------------------------------
 * Fonte única de verdade narrativa e visual do vídeo "As Quatro Estações".
 * Nenhum frame, cor ou texto deste vídeo deve ser escrito em outro arquivo:
 * quem precisar de qualquer um desses dados importa daqui.
 *
 * O QUE ESTE ARQUIVO DEFINE
 *   1. PALETA ............ cores GBH (Grand Budapest Hotel) por estação.
 *   2. ROTEIRO ........... 5 cenas de narração + 1 cena de retorno/fecho,
 *                          com as falas exatas que o áudio já pronuncia.
 *   3. CONTRATOS ......... caminhos de asset que os bots 3 (ComfyUI),
 *                          4 (áudio/avatar) e 5 (3D) devem entregar.
 *
 * O QUE ELE NÃO FAZ
 *   - Não mede áudio. Isso é feito por
 *     D:\CRAFT\video-orquestracao\tools\gerar_timeline_quatro_estacoes.mjs,
 *     que escreve timeline.generated.ts a partir dos mp3 reais.
 *   - Não desenha nada. O desenho do vagão está em VagaoJanela.tsx.
 *
 * REGRA DE OURO DO PROJETO
 *   Todo movimento usa useCurrentFrame() + interpolate()/spring().
 *   Proibido useFrame() do React Three Fiber (ver AGENTS.md do projeto).
 *
 * COMO MUDAR O VÍDEO
 *   Texto novo aqui -> rode o gerador de timeline -> confira o still:
 *     npx remotion still src/index.tsx QuatroEstacoes out/check.png --frame=120
 * ========================================================================== */

/** Identificador de estação usado por todos os componentes e pelos handoffs. */
export type Estacao = "primavera" | "verao" | "outono" | "inverno" | "retorno";

/** Cores de uma cena. Todos os valores são hex para poderem ser interpolados. */
export type PaletaEstacao = {
  /** Cor dominante do céu visto pela janela. */
  ceuTopo: string;
  /** Cor do céu junto ao horizonte (segunda parada do gradiente). */
  ceuBase: string;
  /** Cor das colinas/vegetação mais próxima. */
  terra: string;
  /** Cor da silhueta distante (montanhas, arvoredo). */
  longe: string;
  /** Cor da partícula da estação (pétala, poeira, folha, neve). */
  particula: string;
  /** Cor de destaque tipográfico (etiqueta da cena, sublinhado). */
  acento: string;
  /** Luz do sol/lua dentro do quadro da janela. */
  sol: string;
};

/* ---------------------------------------------------------------------------
 * PALETA GLOBAL — Grand Budapest Hotel.
 * Marfim, rosa Mendl's, bordo, mostarda e latão: a base do vagão é sempre a
 * mesma; só a paisagem muda de estação. É isso que faz a janela parecer um
 * palco fixo e o mundo, o que gira.
 * ------------------------------------------------------------------------- */
export const PALETA_BASE = {
  /** Marfim das paredes do vagão. */
  marfim: "#F3E6CC",
  /** Marfim sombreado (moldura interna, cortina em dobra). */
  marfimSombra: "#E4D3B2",
  /** Bordô dos estofados e do filete da moldura. */
  bordo: "#6E2B33",
  /** Rosa Mendl's — a assinatura cromática do filme. */
  rosa: "#E8A0A8",
  /** Mostarda das cortinas e do tapete. */
  mostarda: "#D9A231",
  /** Latão polido das ferragens da janela. */
  latao: "#C99A3F",
  /** Madeira escura da mesa e do piso. */
  madeira: "#6B4A33",
  /** Chocolate quase preto para texto e sombras profundas. */
  chocolate: "#3A2A21",
  /** Branco de neve / papel do cartão de título. */
  neve: "#F8F5ED",
  /** Vidro: branco leitoso para reflexos. */
  vidro: "#EAF2F5",
} as const;

/** Paletas por estação. A ordem é a ordem do filme. */
export const PALETAS: Record<Estacao, PaletaEstacao> = {
  primavera: {
    ceuTopo: "#BFD9E8",
    ceuBase: "#F6E3D8",
    terra: "#9CC48F",
    longe: "#7FA98B",
    particula: "#F2A6B4",
    acento: "#C97B85",
    sol: "#FBE7C6",
  },
  verao: {
    ceuTopo: "#F7D98F",
    ceuBase: "#F1A65C",
    terra: "#D9A94C",
    longe: "#B07C36",
    particula: "#F6E2A8",
    acento: "#B4652C",
    sol: "#FFF3CE",
  },
  outono: {
    ceuTopo: "#E7B98B",
    ceuBase: "#D97F55",
    terra: "#B5612F",
    longe: "#7A3B2E",
    particula: "#E8A33F",
    acento: "#8F3E28",
    sol: "#FFE0B0",
  },
  inverno: {
    ceuTopo: "#9FBACD",
    ceuBase: "#DCE7EC",
    terra: "#BBD2E0",
    longe: "#7E97A8",
    particula: "#FFFFFF",
    acento: "#4E6C80",
    sol: "#F2F8FC",
  },
  retorno: {
    ceuTopo: "#E9C4C9",
    ceuBase: "#F6E7D2",
    terra: "#C9A98C",
    longe: "#9E8272",
    particula: "#F2C7CE",
    acento: "#A9555F",
    sol: "#FFF1D9",
  },
};

/** Uma cena = um trecho de narração contínuo, com sua própria janela. */
export type Cena = {
  /** Id curto e estável, usado em nomes de arquivo e relatórios. */
  id: string;
  /** Rótulo romano mostrado no canto do quadro (I, II, III...). */
  numeral: string;
  /** Título da cena, como aparece na etiqueta da tela. */
  titulo: string;
  /** Estação que define a paleta da paisagem. */
  estacao: Estacao;
  /** Falas exatas da narração, na ordem em que são pronunciadas. */
  falas: string[];
  /** O que a câmera deve fazer (texto para o Dev-3D-Craft). */
  camera: string;
  /** Pedido de textura para o Especialista-ComfyUI. */
  texturaPrompt: string;
  /** Descrição da cena 3D para o Dev-3D-Craft. */
  cena3d: string;
};

/* ---------------------------------------------------------------------------
 * ROTEIRO — 5 cenas. O áudio já existe; este texto foi conferido contra
 * manifesto-narracao.json em 2026-11-16.
 * ------------------------------------------------------------------------- */
export const CENAS: Cena[] = [
  {
    id: "cena-01",
    numeral: "I",
    titulo: "A Partida",
    estacao: "primavera",
    falas: [
      "Olha só... o trem acabou de partir.",
      "E pela janela, o mundo começa a dançar.",
      "A primavera chega primeiro, florescendo em tons de rosa e verde,",
      "como se a própria natureza tivesse acordado sorrindo.",
      "Você sente esse cheirinho de terra molhada e flores novas?",
      "É a vida dizendo: bem-vindo, a viagem começou!",
    ],
    camera:
      "Plano único, câmera parada dentro do vagão; a paisagem corre da direita para a esquerda. O trem vibra 2 px em ciclo de 24 frames.",
    texturaPrompt:
      "campo de primavera visto de um trem em movimento, macieiras em flor rosa, colinas verdes, luz da manhã, pintura em guache plano estilo Wes Anderson, paleta rosa-poeira e verde-salvia, sem pessoas, sem texto, 16:9",
    cena3d:
      "Três bandas de profundidade: colinas próximas, pomar em flor no meio, serra azulada ao fundo. Cada banda desloca a velocidade diferente.",
  },
  {
    id: "cena-02",
    numeral: "II",
    titulo: "O Verão",
    estacao: "verao",
    falas: [
      "E de repente... o verão!",
      "O sol doura os campos, as árvores ficam cheias,",
      "e a luz entra pela janela fazendo brilhar o vapor da sua xícara de café.",
      "Você dá um gole... e sente o calor bom no peito.",
      "Lá fora, as crianças correm descalças,",
      "e você sorri só de ver. Porque a felicidade às vezes é só isso:",
      "um trem, uma janela, um café quente e o mundo passando devagar.",
    ],
    camera:
      "Mesmo enquadramento; a luz sobe 8% de intensidade e o vapor da xícara fica mais visível. Nenhum corte.",
    texturaPrompt:
      "campos de trigo dourado ao meio-dia vistos de um trem, árvores frondosas, ar quente tremeluzente, guache plano estilo Wes Anderson, mostarda e ocre, sem pessoas em close, sem texto, 16:9",
    cena3d:
      "Sol alto e disco de luz; ondulação de calor por shader de deslocamento vertical sutil; trigo em bandas com sway por seno do frame.",
  },
  {
    id: "cena-03",
    numeral: "III",
    titulo: "O Outono",
    estacao: "outono",
    falas: [
      "Agora as folhas mudam de cor.",
      "Amarelo, laranja, vermelho...",
      "como se a floresta tivesse se vestido para uma festa.",
      "As folhas dançam no vento, girando como confetes dourados.",
      "Você envolve as mãos na xícara,",
      "e pensa em como é bonito mudar.",
      "Como cada estação tem sua beleza, seu tempo, sua música.",
      "E o trem segue, tranquilo, carregando você e suas memórias.",
    ],
    camera:
      "Câmera recua 3% (dolly out) muito lento; partículas de folha dobram de densidade no meio da cena.",
    texturaPrompt:
      "floresta de outono vista de um trem, folhas laranja e vermelho, luz baixa dourada, guache plano estilo Wes Anderson, terracota e mostarda, sem texto, 16:9",
    cena3d:
      "Banda de árvores com copas em 3 tons (mostarda, laranja, terracota); folhas como sprites em rotação de 40°/s.",
  },
  {
    id: "cena-04",
    numeral: "IV",
    titulo: "O Inverno",
    estacao: "inverno",
    falas: [
      "E chega o inverno, quietinho, pintando tudo de branco e silêncio.",
      "Os pinheiros usam chapéus de neve,",
      "e a fumaça das chaminés sobe reta no ar gelado.",
      "Mas lá dentro... lá dentro está quentinho.",
      "Seu café ainda fuma. Seu coração está cheio.",
      "Porque você sabe: depois do inverno, a primavera sempre volta.",
      "E o trem... o trem nunca para de sonhar.",
    ],
    camera:
      "Câmera avança 2% (dolly in) sobre a janela; contraste externo cai, interior ganha 6% de luz âmbar.",
    texturaPrompt:
      "aldeia de inverno com pinheiros nevados e chaminés com fumaça reta, céu pálido, guache plano estilo Wes Anderson, azul-gelo e branco, sem texto, 16:9",
    cena3d:
      "Pinheiros triangulares com chapéu de neve; neve cai em 3 velocidades; fumaça como cilindros suaves subindo retos.",
  },
  {
    id: "cena-05",
    numeral: "V",
    titulo: "O Retorno",
    estacao: "retorno",
    falas: [
      "Quatro estações. Uma viagem.",
      "E você... você fez parte de cada uma delas.",
      "Obrigado por viajar comigo.",
      "Até a próxima estação...",
      "onde o sol nasce de novo,",
      "e a janela continua aberta para o mundo inteiro.",
    ],
    camera:
      "O vagão escurece 15%; a paisagem vira amanhecer rosa. No fim, a janela permanece acesa e o resto do quadro apaga.",
    texturaPrompt:
      "amanhecer rosa sobre colinas suaves visto de um trem, primeira luz, guache plano estilo Wes Anderson, rosa-poeira e creme, sem texto, 16:9",
    cena3d:
      "Mesma montagem da cena 1, mas com o sol nascendo no horizonte e todas as bandas 10% mais lentas.",
  },
];

/* ---------------------------------------------------------------------------
 * CONTRATOS DE ASSET — o que cada especialista entrega e onde.
 * Caminhos absolutos de propósito: o compositor roda em outro diretório e
 * resolveAsset() converte para file:// sem precisar de cópia.
 * ------------------------------------------------------------------------- */
export const CAMINHOS = {
  /** Pasta dos mp3 por cena, já gravados pelo Especialista Áudio/Avatar. */
  audioCenas: "D:/CRAFT/video-orquestracao/public/assets/audio/quatro-estacoes",
  /** Pasta de texturas/fundos do ComfyUI. */
  texturas: "D:/CRAFT/video-orquestracao/public/assets/texturas",
  /** Pasta do áudio de ambiente/trilha/SFX. */
  audioExtra: "D:/CRAFT/video-orquestracao/public/assets/audio/sfx",
  /** Pasta das cenas Three.js. */
  cenas3d: "D:/CRAFT/video-orquestracao/src/components/3d",
} as const;

/** Fundo pintado por estação; opcional — sem ele, o vagão usa gradiente próprio. */
export const TEXTURAS: Record<Estacao, string> = {
  primavera: `${CAMINHOS.texturas}/fundo-primavera.png`,
  verao: `${CAMINHOS.texturas}/fundo-verao.png`,
  outono: `${CAMINHOS.texturas}/fundo-outono.png`,
  inverno: `${CAMINHOS.texturas}/fundo-inverno.png`,
  retorno: `${CAMINHOS.texturas}/fundo-retorno.png`,
};

/** Texturas de grão aplicadas por cima de tudo (grão de papel e sujeira de filme). */
export const GRAO = {
  papel: `${CAMINHOS.texturas}/grao-papel.png`,
  filme: `${CAMINHOS.texturas}/grao-filme.png`,
} as const;

/* ---------------------------------------------------------------------------
 * TIPOS DA TIMELINE GERADA
 * O gerador mede os mp3 e escreve timeline.generated.ts com estes tipos.
 * ------------------------------------------------------------------------- */
/** Uma fala já posicionada no tempo, em segundos absolutos do vídeo. */
export type FalaNaTimeline = {
  /** Texto da fala, igual ao de CENAS[].falas. */
  texto: string;
  /** Início estimado, em segundos absolutos. */
  inicioSegundos: number;
  /** Fim estimado, em segundos absolutos. */
  fimSegundos: number;
};

/** Uma cena com áudio já medido e posicionado na linha de tempo. */
export type CenaNaTimeline = {
  /** Id igual ao de CENAS[]. */
  id: string;
  /** Estação, para achar a paleta. */
  estacao: Estacao;
  /** Caminho absoluto do mp3, com barras normais. */
  audio: string;
  /** Segundo em que a cena começa. */
  inicioSegundos: number;
  /** Duração real do mp3, em segundos. */
  duracaoSegundos: number;
  /** Frame em que a cena começa. */
  inicioFrame: number;
  /** Duração da cena em frames. */
  duracaoFrames: number;
  /** Falas posicionadas por estimativa de caracteres. */
  falas: FalaNaTimeline[];
};

/** Linha de tempo completa do filme. */
export type Timeline = {
  /** Quadros por segundo usado por todo o vídeo. */
  fps: number;
  /** Largura do quadro. */
  largura: number;
  /** Altura do quadro. */
  altura: number;
  /** Duração total, em segundos. */
  totalSegundos: number;
  /** Duração total, em frames (o número que o Remotion usa). */
  totalFrames: number;
  /** Cenas na ordem de reprodução. */
  cenas: CenaNaTimeline[];
};

/** Medidas fixas do quadro. FPS e dimensões também aparecem na timeline gerada. */
export const QUADRO = {
  fps: 30,
  largura: 1920,
  altura: 1080,
  /** Silêncio entre o fim de uma fala e o início da próxima cena. */
  gapEntreCenasSegundos: 0.5,
  /** Duração da placa de título sobre a primeira cena. */
  cartaoTituloSegundos: 3.5,
  /** Duração do cartão final depois da última fala. */
  cartaoFinalSegundos: 4.5,
} as const;
