/**
 * MANUAL - cenasHistoria.ts
 * =========================
 * O que faz
 * ---------
 * Roteiro recontado de "Luninha e Fridóca no Espaço Sideral", dividido em cenas
 * com frames calculados a 30 fps a partir da narração original (244 s).
 *
 * Por que existe
 * --------------
 * A história original era contada com slides. Aqui cada cena é uma composição de
 * recorte 2D com movimento próprio: flutuar, girar, abanar rabo, luzes piscando.
 *
 * Fonte original
 * --------------
 * https://youtu.be/mLO4Ok5ahYU (244 s). Texto falado extraído das legendas
 * automáticas pt-orig e reescrito para ficar mais curto e emocionado.
 *
 * Saída
 * -----
 * `CENAS_HISTORIA` (consumida por HistoriaLuninhaFridoca.tsx) e
 * `TOTAL_FRAMES_HISTORIA` (7.320 frames = 244 s @30 fps).
 */

export type TipoCena =
  | "abertura"          // 1. gancho + título
  | "cabine"            // 2. traje, nave e lançamento
  | "cabine-flutuar"    // 3. gravidade zero
  | "biscoitos"         // 4. biscoitos voadores
  | "estrelas"          // 5. giro espacial
  | "festa"             // 6. botão amarelo e musiquinha
  | "terra"             // 7. abraço olhando a Terra
  | "pouso"             // 8. volta e pouso
  | "final";            // 9. despedida

export interface PaletaCena {
  ceuTopo: string;        // 2. topo do gradiente
  ceuBase: string;        // 3. base do gradiente
  acento: string;         // 4. cor de destaque (luzes, coração, botão)
  painel: string;         // 5. cor do painel da nave
}

export interface CenaHistoria {
  id: string;             // 6. identificador estável
  titulo: string;         // 7. título curto da cena
  tipo: TipoCena;         // 8. qual desenho de recorte usar
  inicioFrames: number;   // 9. frame de entrada
  duracaoFrames: number;  // 10. duração
  fala: string;           // 11. legenda recontada
  paleta: PaletaCena;    // 12. cores da cena
}

/** Paletas vivas de infantis: azul espacial profundo + rosa/dourado quente. */
const PALETA_ESPACO: PaletaCena = {
  ceuTopo: "#0b1030", ceuBase: "#1c2a63", acento: "#ffd166", painel: "#f2e7d5",
};
const PALETA_CABINE: PaletaCena = {
  ceuTopo: "#0e1440", ceuBase: "#27357a", acento: "#ffd166", painel: "#efe3cf",
};
const PALETA_FESTA: PaletaCena = {
  ceuTopo: "#3a1150", ceuBase: "#7a2f7a", acento: "#ffb3d9", painel: "#ffe3ef",
};
const PALETA_TERRA: PaletaCena = {
  ceuTopo: "#0a1f3d", ceuBase: "#1d5c8f", acento: "#8fe3ff", painel: "#e6f4ff",
};
const PALETA_POUSO: PaletaCena = {
  ceuTopo: "#7ec8e3", ceuBase: "#cdeffd", acento: "#ffd166", painel: "#e9e2d0",
};
const PALETA_FINAL: PaletaCena = {
  ceuTopo: "#4a1d5c", ceuBase: "#c86b9b", acento: "#ffd166", painel: "#fff0f7",
};

/** Roteiro recontado, cena a cena. Frames derivados dos tempos da narração. */
export const CENAS_HISTORIA: CenaHistoria[] = [
  {
    id: "cena-01-abertura",
    titulo: "O convite",
    tipo: "abertura",
    inicioFrames: 0,
    duracaoFrames: 690,                                                    // 23 s
    fala: "E se duas cachorrinhas muito sapecas viajassem num foguete de verdade? Olá, amiguinhos! Hoje é Luninha e Fridóca no espaço sideral!",
    paleta: PALETA_ESPACO,
  },
  {
    id: "cena-02-nave",
    titulo: "Decolando",
    tipo: "cabine",
    inicioFrames: 690,
    duracaoFrames: 666,                                                    // 22,2 s
    fala: "Elas vestiram o traje branquinho de astronauta e entraram na nave gigante. Tchim, pum... lá foram as duas, com as orelhas voando!",
    paleta: PALETA_CABINE,
  },
  {
    id: "cena-03-flutuar",
    titulo: "Sem gravidade",
    tipo: "cabine-flutuar",
    inicioFrames: 1356,
    duracaoFrames: 843,                                                    // 28,1 s
    fala: "De repente, a gravidade sumiu! A Luninha flutuou alto e a Fridóca virou de ponta-cabeça. Que bagunça deliciosa!",
    paleta: PALETA_CABINE,
  },
  {
    id: "cena-04-biscoitos",
    titulo: "Biscoitos voadores",
    tipo: "biscoitos",
    inicioFrames: 2199,
    duracaoFrames: 1311,                                                   // 43,7 s
    fala: "Flutuar dá fome, não dá? A Fridóca abriu a caixa de biscoitos e eles saíram voando! A Luninha pegou um direto na boca: nhaque!",
    paleta: PALETA_CABINE,
  },
  {
    id: "cena-05-estrelas",
    titulo: "Bailarinas do espaço",
    tipo: "estrelas",
    inicioFrames: 3510,
    duracaoFrames: 768,                                                    // 25,6 s
    fala: "Milhares de estrelas piscando lá fora. A Luninha girou como uma bailarina espacial e a Fridóca tentou imitar... ops, trombada carinhosa!",
    paleta: PALETA_ESPACO,
  },
  {
    id: "cena-06-festa",
    titulo: "O botão amarelo",
    tipo: "festa",
    inicioFrames: 4278,
    duracaoFrames: 618,                                                    // 20,6 s
    fala: "A Fridóca encostou num botão grandão e amarelo. A nave tocou uma musiquinha alegre, as luzes piscaram em rosa e dourado, e a Luninha abanou o rabo sem parar.",
    paleta: PALETA_FESTA,
  },
  {
    id: "cena-07-terra",
    titulo: "Abraço espacial",
    tipo: "terra",
    inicioFrames: 4896,
    duracaoFrames: 626,                                                    // 20,9 s
    fala: "As duas se abraçaram, flutuando baixinho, e ficaram olhando a Terra azulzinha lá longe. Que viagem cheia de amor!",
    paleta: PALETA_TERRA,
  },
  {
    id: "cena-08-pouso",
    titulo: "Hora de voltar",
    tipo: "pouso",
    inicioFrames: 5522,
    duracaoFrames: 1291,                                                   // 43 s
    fala: "Cinto afivelado, foguete deslizando pelas nuvens... pouso suave no gramado verde. As cãzinhas mais corajosas do planeta!",
    paleta: PALETA_POUSO,
  },
  {
    id: "cena-09-final",
    titulo: "Até a próxima",
    tipo: "final",
    inicioFrames: 6813,
    duracaoFrames: 507,                                                    // 16,9 s
    fala: "Muito obrigado por assistir! Um beijo grande no seu coração. Até a próxima aventura! Tchau, tchau!",
    paleta: PALETA_FINAL,
  },
];

/** 244 s @30 fps = 7.320 frames. */
export const TOTAL_FRAMES_HISTORIA = 7320;                                 // 13.
