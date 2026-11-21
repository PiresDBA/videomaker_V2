/**
 * MANUAL - sequenciasMovimento.ts
 * ===============================
 * O que faz
 * ---------
 * Catalogo canonico de movimentos das personagens Luna e Frida, copiado do
 * StickFilms (C:/Users/Pires/StickFilms/characters/asterisco/poses.json). Cada entrada
 * diz quais indices da sprite sheet formam o ciclo do movimento e a velocidade.
 *
 * Por que existe
 * --------------
 * O usuario pediu um TEMPLATE reutilizavel: sempre que Luna e Frida aparecerem
 * em video novo, a cena pega o movimento daqui em vez de inventar ordem de
 * poses (que quebraria o ciclo desenhado pelo artista).
 *
 * Fonte unica
 * -----------
 * Este arquivo espelha o poses.json do StickFilms. Se o StickFilms mudar,
 * atualize aqui tambem (e comente a data).
 *
 * Saida
 * -----
 * `FICHAS_SPRITE` (metadados da sheet), `SEQUENCIAS` (movimento -> indices + fps).
 */

/** Um ciclo de movimento: indices de pose na ordem desenhada + velocidade. */
export interface SequenciaMovimento {
  poses: number[];      // 1. indices das poses, na ordem do ciclo
  fps: number;          // 2. velocidade do ciclo
  nota?: string;        // 3. observacao do artista
}

/** Metadados de cada sprite sheet (grid uniforme). */
export interface FichaSprite {
  arquivo: string;      // 4. caminho relativo a public/ do compositor
  cols: number;         // 5. colunas da grade
  rows: number;         // 6. linhas da grade
  poses: number;        // 7. total de poses validas
  larguraCelulaPx: number;  // 8. largura de UMA celula no arquivo real (px da imagem)
  alturaCelulaPx: number;   // 8b. altura de UMA celula (px da imagem)
  alturaCena: number;   // 9. altura de exibicao padrao em px de cena
}

/** Dados copiados de characters (character.json + poses.json do StickFilms, 17/11/2026).
 *  Dimensoes reais medidas: luna 3084x10422, frida 1524x4585. */
export const FICHAS_SPRITE = {
  luna: {
    arquivo: "personagens-stickfilms/luna/sheet-poses-alpha.png",
    cols: 12,
    rows: 27,
    poses: 316,
    larguraCelulaPx: 257,
    alturaCelulaPx: 386,
    alturaCena: 200,
  },
  frida: {
    arquivo: "personagens-stickfilms/frida/sheet-poses-alpha.png",
    cols: 12,
    rows: 35,
    poses: 413,
    larguraCelulaPx: 127,
    alturaCelulaPx: 131,
    alturaCena: 210,
  },
} as const;

/** Catalogo de movimentos (espelha poses.json; NAO inventar ordem). */
export const SEQUENCIAS: Record<"luna" | "frida", Record<string, SequenciaMovimento>> = {
  luna: {
    correr:    { poses: [0, 1, 2, 3, 4, 5], fps: 12, nota: "Ciclo lateral limpo (0-11 e o melhor)." },
    andar:     { poses: [48, 49, 50, 51, 52, 53], fps: 8 },
    dancar:    { poses: [0, 1, 2, 3, 6, 7, 8, 9], fps: 6, nota: "Pulando / comemorando (linha do salto)." },
    parado:    { poses: [24, 25, 26, 27], fps: 2 },
    sentada:   { poses: [122, 123, 124, 125], fps: 2 },
    deitada:   { poses: [72, 73, 74, 75, 140, 141, 142, 143], fps: 1.5, nota: "Deitada / dormindo." },
    divertir:  { poses: [288, 289, 290, 291], fps: 4, nota: "Brincando com bola (pose especial)." },
    pular:     { poses: [84, 85, 86, 87, 88, 89], fps: 12, nota: "Luna nao tem ciclo de pulo separado; usa o ciclo de correr." },
  },
  frida: {
    correr:    { poses: [84, 85, 86, 87, 88, 89], fps: 12, nota: "Contato -> passagem -> contato oposto." },
    andar:     { poses: [144, 145, 146, 147, 148, 149], fps: 8 },
    dancar:    { poses: [0, 1, 2, 3, 48, 49, 50, 57, 58, 59], fps: 6, nota: "Bracos para cima / celebrando." },
    pular:     { poses: [1, 224, 225, 226, 227, 328, 329, 330], fps: 8, nota: "Agachar -> subir -> pousar." },
    parado:    { poses: [384, 385, 386, 387, 388, 389], fps: 2, nota: "Respiracao sutil; 24-27 e alongamento." },
    sentada:   { poses: [51, 52, 53, 54], fps: 2 },
    deitada:   { poses: [221, 222, 223, 331, 332, 333], fps: 1.5 },
    rolar:     { poses: [132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143], fps: 4, nota: "Rolando de costas / cambalhota." },
    divertir:  { poses: [288, 289, 290, 291], fps: 4, nota: "Brincando (pose especial de bola/pizza)." },
  },
};

/** Indice de pose -> posicao (linha, coluna) na grid da sheet. */
export const indiceParaCelula = (indice: number, cols: number): { linha: number; coluna: number } => {
  return {
    linha: Math.floor(indice / cols),                    // 9. linha da grid
    coluna: indice % cols,                               // 10. coluna da grid
  };
};

/** Frame do ciclo -> indice de pose (loop continuo pela sequencia). */
export const poseNoFrame = (
  sequencia: SequenciaMovimento,   // 11. ciclo do movimento
  frame: number,                   // 12. frame local da cena
): number => {
  const total = sequencia.poses.length;                          // 13. tamanho do ciclo
  const passo = Math.floor(frame * (sequencia.fps / 30));        // 14. frame do ciclo (fps -> 30)
  return sequencia.poses[passo % total];                         // 15. pose da vez
};
