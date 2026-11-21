/**
 * MANUAL — roteiroHistoriaEspaco.ts
 * =================================
 * O que faz
 * ---------
 * Fonte única de verdade narrativa e visual da historinha refeita
 * "Luninha e Fridóca no Espaço Sideral" (base: vídeo do canal, seq 383).
 * Nenhum texto, cor ou tempo deste vídeo deve ser escrito em outro arquivo.
 *
 * Por que existe
 * --------------
 * O vídeo original parecia slides: cena parada, só texto passando. A refação
 * precisa de RECOTE: cada parágrafo é um trecho animado de verdade — os
 * bichinhos se movem, flutuam, saltam e a narração sai de um avatar no canto.
 *
 * Regra de frame
 * --------------
 * Todo movimento usa useCurrentFrame() + interpolate()/spring(); proibido
 * useFrame() do Three.js. Render determinístico (AGENTS.md do projeto).
 *
 * Saída
 * -----
 * - `CENAS_HISTORIA`: 10 trechos (C0..C9) com id, rótulo, texto e fala exibida
 * - `PALETA_ESPACO`: cores da historinha (brilho alto, criança)
 */

/** Um trecho narrado da historinha (uma cena visual). */
export interface CenaHistoria {
  /** Identificador estável (nome do MP3 sem extensão). */
  id: string;
  /** Rótulo curto para relatórios. */
  rotulo: string;
  /** Texto EXATO que o áudio desta cena narra (contrato com o áudio-avatar). */
  texto: string;
}

/** História recontada — textos EXATOS da narração entregue (metadados-voz.json,
 * Gemini Aoede infantil com emoção). Legendas sempre iguais ao áudio. */
export const CENAS_HISTORIA: CenaHistoria[] = [
  {
    id: "cena-00",
    rotulo: "Título",
    texto: "Luninha e Fridóca no Espaço Sideral!",
  },
  {
    id: "cena-01",
    rotulo: "O convite",
    texto:
      "E se duas cachorrinhas muito sapecas viajassem num foguete de verdade? Olá, amiguinhos! Hoje é Luninha e Fridóca no espaço sideral!",
  },
  {
    id: "cena-02",
    rotulo: "Decolando",
    texto:
      "Elas vestiram o traje branquinho de astronauta e entraram na nave gigante. Tchim, pum... lá foram as duas, com as orelhas voando!",
  },
  {
    id: "cena-03",
    rotulo: "Sem gravidade",
    texto:
      "De repente, a gravidade sumiu! A Luninha flutuou alto e a Fridóca virou de ponta-cabeça. Que bagunça deliciosa!",
  },
  {
    id: "cena-04",
    rotulo: "Biscoitos voadores",
    texto:
      "Flutuar dá fome, não dá? A Fridóca abriu a caixa de biscoitos e eles saíram voando! A Luninha pegou um direto na boca: nhaque!",
  },
  {
    id: "cena-05",
    rotulo: "Bailarinas do espaço",
    texto:
      "Milhares de estrelas piscando lá fora. A Luninha girou como uma bailarina espacial e a Fridóca tentou imitar... ops, trombada carinhosa!",
  },
  {
    id: "cena-06",
    rotulo: "O botão amarelo",
    texto:
      "A Fridóca encostou num botão grandão e amarelo. A nave tocou uma musiquinha alegre, as luzes piscaram em rosa e dourado, e a Luninha abanou o rabo sem parar.",
  },
  {
    id: "cena-07",
    rotulo: "Abraço espacial",
    texto:
      "As duas se abraçaram, flutuando baixinho, e ficaram olhando a Terra azulzinha lá longe. Que viagem cheia de amor!",
  },
  {
    id: "cena-08",
    rotulo: "Hora de voltar",
    texto:
      "Cinto afivelado, foguete deslizando pelas nuvens... pouso suave no gramado verde. As cãzinhas mais corajosas do planeta!",
  },
  {
    id: "cena-09",
    rotulo: "Até a próxima",
    texto:
      "Muito obrigado por assistir! Um beijo grande no seu coração. Até a próxima aventura! Tchau, tchau!",
  },
];

/** Paleta da historinha: saturação alta, nada de preto puro, cara de criança. */
export const PALETA_ESPACO = {
  ceuEspaco: "#1b2a6b",       // azul escuro do espaço (não preto)
  ceuEspacoClaro: "#3d5bd9",  // brilho do espaço
  estrela: "#ffe9a8",         // dourado quente das estrelas
  naveCorpo: "#f2efe6",       // casco da nave (branco quente)
  naveDetalhe: "#ff7bb1",     // rosa Mendl's das luzes
  naveDourado: "#ffb43d",     // latão/amarelo do botão
  chaoTerra: "#8fce6a",       // grama do pouso
  lunaCorpo: "#8a5a33",       // salsicha MARROM tom único (Luna, ficha do Diretor-Arte)
  lunaBarriga: "#8a5a33",     // mesmo tom: sem manchas (ficha)
  fridaCorpo: "#e8c78f",      // buldogue fawn (Fridóca)
  fridaRoupa: "#f5f2ea",      // traje de astronauta branco quente
  roupaDetalhe: "#d94f6e",    // detalhes do traje
  legendaFundo: "rgba(20,14,40,0.72)",
  legendaTexto: "#fff4d8",
  tituloRosa: "#ff7bb1",
  tituloDourado: "#ffd24d",
} as const;

/** Tempo de leitura estimado para o gerador de timeline placeholder. */
export const SEGUNDOS_POR_CARACTERE = 0.075;  // 1. ~13 caracteres/s narrados
