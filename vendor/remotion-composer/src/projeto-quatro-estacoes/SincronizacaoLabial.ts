/**
 * MANUAL — SincronizacaoLabial.ts
 * ================================
 * O que faz
 * ---------
 * Motor de sincronização labial para avatares 2D. Converte um array de
 * aberturas de boca (um valor por frame, gerado pela energia da narração real)
 * no valor de abertura do frame atual, com interpolação entre frames.
 *
 * Por que existe
 * --------------
 * Senoides fixas ("pseudo-fala") não acompanham a voz — o avatar parece não
 * falar. Aqui a boca abre e fecha exatamente quando a narração tem energia.
 * Serve para QUALQUER avatar cuja boca seja um grupo animável (buldogue,
 * salsicha, menina, menino, mascote...), desde que se passe o array correto.
 *
 * Como usa
 * --------
 *   const abertura = aberturaBocaNoFrame(VALORES_BECA_CENA_05, frame);
 *   const abertura = useAberturaBoca(VALORES_BECA_CENA_05); // dentro de <Sequence>
 *
 * Regra de frame
 * --------------
 * Só matemática pura sobre `useCurrentFrame()`; sem relógio de parede, sem
 * `useFrame()` de Three.js. Render determinístico.
 */

import { useCurrentFrame } from "remotion";  // 1. frame local da Sequence

/**
 * Devolve a abertura da boca (0..1) no frame local informado, interpolando
 * linearmente entre os dois frames vizinhos para um movimento suave.
 * Fora do intervalo, devolve 0 (boca fechada).
 */
export function aberturaBocaNoFrame(valores: number[], frameLocal: number): number {
  // 2. sem dados, boca fechada
  if (!valores || valores.length === 0) {
    return 0;
  }
  // 3. ignora frames negativos ou além do fim
  if (frameLocal < 0 || frameLocal >= valores.length) {
    return 0;
  }
  // 4. frame inteiro à esquerda e seu vizinho à direita
  const indiceEsquerdo = Math.floor(frameLocal);
  const indiceDireito = Math.min(valores.length - 1, indiceEsquerdo + 1);
  // 5. fração entre os dois frames (0..1)
  const fracao = frameLocal - indiceEsquerdo;
  // 6. valores nos dois frames
  const valorEsquerdo = valores[indiceEsquerdo] ?? 0;
  const valorDireito = valores[indiceDireito] ?? valorEsquerdo;
  // 7. interpolação linear
  return valorEsquerdo + (valorDireito - valorEsquerdo) * fracao;
}

/**
 * Versão em hook: lê o frame atual da Sequence e devolve a abertura da boca.
 * Use dentro de um componente Remotion (ex.: dentro da <Sequence> do avatar).
 */
export function useAberturaBoca(valores: number[]): number {
  // 8. frame local da Sequence onde o avatar está montado
  const frame = useCurrentFrame();
  // 9. abertura já interpolada no frame atual
  return aberturaBocaNoFrame(valores, frame);
}
