/**
 * MANUAL - SpritePersonagem.tsx
 * =============================
 * O que faz
 * ---------
 * Desenha a Luna ou a Frida usando a SPRITE SHEET OFICIAL do StickFilms
 * (desenhadas pelo artista do canal), executando um movimento do catálogo
 * (correr, andar, dançar, pular, rolar, parado...) num lado do quadro.
 *
 * Por que existe
 * --------------
 * É o TEMPLATE pedido pelo usuário: sempre que Luna e Frida precisarem
 * "se mexendo para um lado, para o outro, pulando, se divertindo", a cena usa
 * este componente em vez de redesenhar. A ordem das poses vem de
 * `sequenciasMovimento.ts`, que espelha o poses.json do StickFilms.
 *
 * Como usar
 * ---------
 *   <SpritePersonagem personagem="luna" movimento="correr" lado="direita" frame={f} />
 *   <SpritePersonagem personagem="frida" movimento="pular" lado="esquerda" frame={f} />
 *
 * Regra
 * -----
 * Só `useCurrentFrame()`/frame passado por prop; sem vídeo de IA, sem GPU.
 * A sheet fica em public/personagens-stickfilms/ (cópia do StickFilms).
 */

import React from "react";
import { Img, staticFile } from "remotion";                       // 1. imagem estática
import {
  FICHAS_SPRITE,
  SEQUENCIAS,
  indiceParaCelula,
  poseNoFrame,
} from "./sequenciasMovimento";                                   // 2. catálogo canônico

export type PersonagemId = "luna" | "frida";                     // 3. personagens oficiais

/** Todos os movimentos disponíveis por personagem. */
export const movimentosDe = (personagem: PersonagemId): string[] => {
  return Object.keys(SEQUENCIAS[personagem]);                    // 4. lista de movimentos
};

/** Luna ou Frida em movimento, recortada da sprite sheet oficial. */
export const SpritePersonagem: React.FC<{
  personagem: PersonagemId;
  movimento: string;
  /** Direção do movimento: a sheet é desenhada para a ESQUERDA? ver nota. */
  lado?: "esquerda" | "direita";
  /** Frame local da cena (avança o ciclo). */
  frame: number;
  /** Altura de exibição em px (default por personagem). */
  altura?: number;
  /** Deslocamento horizontal dentro do pai. */
  x?: number;
}> = ({
  personagem,
  movimento,
  lado = "esquerda",
  frame,
  altura,
  x = 0,

}) => {
  const ficha = FICHAS_SPRITE[personagem];                       // 5. metadados da sheet
  const seq = SEQUENCIAS[personagem][movimento] ?? SEQUENCIAS[personagem].parado;  // 6. fallback parado
  const indice = poseNoFrame(seq, frame);                        // 7. pose da vez
  const { linha, coluna } = indiceParaCelula(indice, ficha.cols);  // 8. celula da grid
  // 9. proporcao REAL da celula, medida na imagem (luna 257x386, frida 127x131):
  const proporcaoCelula = ficha.larguraCelulaPx / ficha.alturaCelulaPx;
  // 10. altura de EXIBICAO pedida; o recorte corta o branco da celula e
  //     e escalado para caber exatamente na caixa pedida.
  const alturaCaixa = altura ?? ficha.alturaCena;                // 11. altura visivel
  const larguraCaixa = Math.round(alturaCaixa * proporcaoCelula); // 12. largura da caixa
  const recorteH = Math.round(ficha.alturaCelulaPx * 0.82);      // 13. recorte vertical (tira branco)
  const recorteW = Math.round(recorteH * proporcaoCelula);       // 14. recorte horizontal
  const offsetY = ficha.alturaCelulaPx - recorteH - 8;           // 15. recorte encostado no chao
  const offsetX = Math.round((ficha.larguraCelulaPx - recorteW) / 2);  // 16. recorte centrado
  const escala = alturaCaixa / recorteH;                         // 17. zoom do recorte
  const espelhado = lado === 'direita';                          // 18. espelha para andar a direita

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        width: larguraCaixa,
        height: alturaCaixa,
        overflow: 'hidden',
      }}
    >
      {/* 19. sheet escalada: o recorte da celula cai exatamente dentro da caixa */}
      <Img
        src={staticFile(ficha.arquivo)}
        style={{
          position: 'absolute',
          width: ficha.larguraCelulaPx * ficha.cols * escala,
          height: ficha.alturaCelulaPx * ficha.rows * escala,
          left: -(coluna * ficha.larguraCelulaPx + offsetX) * escala,
          top: -(linha * ficha.alturaCelulaPx + offsetY) * escala,
          transform: espelhado ? 'scaleX(-1)' : undefined,
          transformOrigin: 'center',
          imageRendering: 'auto',
        }}
      />
    </div>
  );
};
