/**
 * MANUAL — timelineQuatroEstacoes.ts
 * ==================================
 * O que faz
 * ---------
 * Fonte única de verdade da timeline do vídeo "Quatro Estações na Janela do
 * Trem": durações medidas da narração real, frames de entrada/saída de cada
 * sequência, paleta de cada estação, títulos e legendas com tempo calculado
 * proporcionalmente ao texto falado.
 *
 * Por que existe
 * --------------
 * Se os números ficam espalhados pelo .tsx, o áudio e a imagem desalinham a cada
 * ajuste. Aqui qualquer mudança de duração da narração é refeita em um lugar só.
 *
 * Regra de frame
 * --------------
 * Tudo é calculado com FPS fixo de 30. Qualquer animação usa `useCurrentFrame()`
 * e `interpolate()`; nada depende de relógio de parede (render determinístico).
 *
 * Saída
 * -----
 * - `ESTACOES`: array tipado consumido por `QuatroEstacoesJanelaTrem.tsx`
 * - `LARGURA_VIDEO`, `ALTURA_VIDEO`, `FPS_VIDEO`, `TOTAL_FRAMES`
 */

// --- constantes de formato ---------------------------------------------------
export const FPS_VIDEO = 30;        // 1. 30 fps: leve para 1080p e natural para narração
export const LARGURA_VIDEO = 1920;  // 2. largura Full HD
export const ALTURA_VIDEO = 1080;   // 3. altura Full HD

// --- base de tempo oficial (decisão do usuário, v2) ---------------------------
// Fronteiras v2 do tempos-narracao.json (ffprobe: 163,415 s = 4.902 frames @30),
// voz FranciscaNeural a ritmo -38%. Os cinco mp3 de cena são a mesma locução
// fatiada: a soma deles = master, sem respiro extra. Frames vêm da fronteira
// medida, nunca de ceil(segundos) acumulado — o arredondamento não vaza de uma
// cena para outra.
const FRONTEIRAS_SEGUNDOS = [0, 30.864, 67.584, 104.28, 140.4, 163.415] as const;  // 4. início de cada cena + fim da última

// --- tipos -------------------------------------------------------------------
export interface Estacao {
  id: string;               // 5. identificador estável (nome do MP3)
  titulo: string;           // 6. rótulo exibido no canto superior
  arquivoAudio: string;     // 7. caminho relativo dentro de public/ do compositor
  duracaoNarracao: number;  // 8. segundos medidos por ffprobe
  inicioFrames: number;     // 9. frame absoluto em que a cena começa
  duracaoFrames: number;    // 10. tamanho da sequência em frames
  falas: string[];          // 11. falas usadas nas legendas
  paleta: PaletaEstacao;    // 12. cores da estação
  particula: "petala" | "poeira" | "folha" | "neve" | "brilho";  // 13. tipo de partícula do ar
}

export interface PaletaEstacao {
  ceuTopo: string;      // 14. topo do gradiente de céu
  ceuBase: string;      // 15. base do gradiente (horizonte)
  sol: string;          // 16. disco solar / halo
  colinaLonge: string;  // 17. primeira camada de relevo (mais clara)
  colinaMeio: string;   // 18. segunda camada
  arvores: string;      // 19. silhueta de árvores
  chao: string;         // 20. faixa de chão/trilho
  destaque: string;     // 21. cor de acento (legenda e chip)
  luzJanela: string;    // 22. cor do reflexo no vidro
}

// --- paletas por estação (Grand Budapest: rosa empoeirado, mostarda, esmeralda,
// creme; saturação baixa, nenhum preto puro) -----------------------------------
const PALETA_PRIMAVERA: PaletaEstacao = {
  ceuTopo: "#b9d3c4", ceuBase: "#f3d9dc", sol: "#f7e6bd",
  colinaLonge: "#c3d8b4", colinaMeio: "#a8c79a", arvores: "#6f9463",
  chao: "#8fae84", destaque: "#D9A441", luzJanela: "#fde9ee",
};

const PALETA_VERAO: PaletaEstacao = {
  ceuTopo: "#9ec6c0", ceuBase: "#f6dfae", sol: "#ffd98a",
  colinaLonge: "#d8c489", colinaMeio: "#c0a765", arvores: "#6d8557",
  chao: "#a08a55", destaque: "#D9A441", luzJanela: "#ffe6b8",
};

const PALETA_OUTONO: PaletaEstacao = {
  ceuTopo: "#d9a58c", ceuBase: "#f0d2ae", sol: "#efc08a",
  colinaLonge: "#c98f5e", colinaMeio: "#a86c44", arvores: "#7d4a33",
  chao: "#8a5b3c", destaque: "#D9A441", luzJanela: "#ffdcb4",
};

const PALETA_INVERNO: PaletaEstacao = {
  ceuTopo: "#a9bfd0", ceuBase: "#e8e6ea", sol: "#fbf7ef",
  colinaLonge: "#cdd8e0", colinaMeio: "#b4c3d0", arvores: "#5f7285",
  chao: "#dcdad8", destaque: "#D9A441", luzJanela: "#e6eef7",
};

const PALETA_RETORNO: PaletaEstacao = {
  ceuTopo: "#a9c2cc", ceuBase: "#fbdcb6", sol: "#ffe0a6",
  colinaLonge: "#c6cfa9", colinaMeio: "#a6b98c", arvores: "#6b8763",
  chao: "#8c9a76", destaque: "#D9A441", luzJanela: "#ffe8cd",
};

// --- durações reais da narração (medidas no master com ffprobe) --------------
// Derivadas das fronteiras acima, não digitadas à mão: 926 / 1102 / 1100 / 1084 / 690.
const FRAMES_FRONTEIRA = FRONTEIRAS_SEGUNDOS.map((segundos) => Math.round(segundos * FPS_VIDEO));  // 23. segundos -> frame global
const NARRACAO_SEGUNDOS = FRONTEIRAS_SEGUNDOS.slice(1).map((fim, indice) =>  // 24. duração falada de cada cena
  Number((fim - FRONTEIRAS_SEGUNDOS[indice]).toFixed(3)),
);

// --- falas usadas nas legendas (mesmas do MP3, sem emoji) --------------------
const FALAS_POR_CENA: string[][] = [
  [ // 24. primavera
    "Olha só... o trem acabou de partir.",
    "E pela janela, o mundo começa a dançar.",
    "A primavera chega primeiro, florescendo em tons de rosa e verde,",
    "como se a própria natureza tivesse acordado sorrindo.",
    "Você sente esse cheirinho de terra molhada e flores novas?",
    "É a vida dizendo: bem-vindo, a viagem começou!",
  ],
  [ // 25. verão
    "E de repente... o verão!",
    "O sol doura os campos, as árvores ficam cheias,",
    "e a luz entra pela janela fazendo brilhar o vapor da sua xícara de café.",
    "Você dá um gole... e sente o calor bom no peito.",
    "Lá fora, as crianças correm descalças,",
    "e você sorri só de ver. Porque a felicidade às vezes é só isso:",
    "um trem, uma janela, um café quente e o mundo passando devagar.",
  ],
  [ // 26. outono
    "Agora as folhas mudam de cor.",
    "Amarelo, laranja, vermelho...",
    "como se a floresta tivesse se vestido para uma festa.",
    "As folhas dançam no vento, girando como confetes dourados.",
    "Você envolve as mãos na xícara,",
    "e pensa em como é bonito mudar.",
    "Como cada estação tem sua beleza, seu tempo, sua música.",
    "E o trem segue, tranquilo, carregando você e suas memórias.",
  ],
  [ // 27. inverno
    "E chega o inverno, quietinho, pintando tudo de branco e silêncio.",
    "Os pinheiros usam chapéus de neve,",
    "e a fumaça das chaminés sobe reta no ar gelado.",
    "Mas lá dentro... lá dentro está quentinho.",
    "Seu café ainda fuma. Seu coração está cheio.",
    "Porque você sabe: depois do inverno, a primavera sempre volta.",
    "E o trem... o trem nunca para de sonhar.",
  ],
  [ // 28. fechamento
    "Quatro estações. Uma viagem.",
    "E você... você fez parte de cada uma delas.",
    "Obrigado por viajar comigo.",
    "Até a próxima estação...",
    "onde o sol nasce de novo,",
    "e a janela continua aberta para o mundo inteiro.",
  ],
];

// --- metadados de cada estação ----------------------------------------------
const METADADOS: Array<{
  id: string; titulo: string; paleta: PaletaEstacao;
  particula: Estacao["particula"];
}> = [
  { id: "cena-01", titulo: "Primavera", paleta: PALETA_PRIMAVERA, particula: "petala" },   // 29. cena 1
  { id: "cena-02", titulo: "Verão", paleta: PALETA_VERAO, particula: "poeira" },           // 30. cena 2
  { id: "cena-03", titulo: "Outono", paleta: PALETA_OUTONO, particula: "folha" },          // 31. cena 3
  { id: "cena-04", titulo: "Inverno", paleta: PALETA_INVERNO, particula: "neve" },         // 32. cena 4
  { id: "cena-05", titulo: "O Retorno", paleta: PALETA_RETORNO, particula: "brilho" },     // 33. cena 5
];

// --- montagem: usa as fronteiras medidas, sem folga acumulada -----------------
export const ESTACOES: Estacao[] = METADADOS.map((meta, indice) => {  // 35. percorre as 5 estações
  const inicioFrames = FRAMES_FRONTEIRA[indice];                     // 36. frame global onde a cena entra
  const fimFrames = FRAMES_FRONTEIRA[indice + 1];                    // 37. frame global onde a próxima entra
  const estacao: Estacao = {
    ...meta,
    arquivoAudio: `audio-quatro-estacoes/${meta.id}.mp3`,  // 38. pasta copiada para public/ do compositor
    duracaoNarracao: NARRACAO_SEGUNDOS[indice],            // 39. segundos falados (legenda usa isso)
    inicioFrames,                                          // 40. entrada exata
    duracaoFrames: fimFrames - inicioFrames,               // 41. tamanho = diferença de fronteiras
    falas: FALAS_POR_CENA[indice],
  };
  return estacao;
});

// --- cartão final (dentro do rabo do áudio v2) --------------------------------
// O mix v2 tem exatamente 163,415 s (4.902 frames): não existe áudio além dele,
// então o cartão entra SOBRE a cauda da narração (última palavra termina no
// frame 4.856) e TOTAL_FRAMES = 4.902, igual ao áudio — sem rabo mudo.
export const FRAMES_CARTAO_FINAL = 100;                                    // 42. 3,33 s de marca final
export const TOTAL_FRAMES = 4902;                                          // 43. = narração v2 (163,415 s)
export const INICIO_CARTAO_FINAL = TOTAL_FRAMES - FRAMES_CARTAO_FINAL;     // 44. frame 4802

// --- legenda: distribui o texto proporcionalmente aos caracteres -------------
export interface LegendaCronometrada {
  texto: string;      // 43. linha exibida
  inicio: number;     // 44. frame local (dentro da cena) em que entra
  duracao: number;    // 45. frames visível
}

export const legendasDaEstacao = (estacao: Estacao): LegendaCronometrada[] => {
  const totalCaracteres = estacao.falas.reduce((soma, fala) => soma + fala.length, 0);  // 46. base de proporção
  const framesNarrados = Math.ceil(estacao.duracaoNarracao * FPS_VIDEO);               // 47. frames só da fala
  let cursorLegenda = 0;                                                              // 48. frame local inicial
  return estacao.falas.map((texto) => {                                               // 49. uma legenda por fala
    const fatia = Math.max(24, Math.round((texto.length / totalCaracteres) * framesNarrados));  // 50. mínimo legível
    const legenda: LegendaCronometrada = { texto, inicio: cursorLegenda, duracao: fatia };
    cursorLegenda += fatia;                                                            // 51. avança
    return legenda;
  });
};
