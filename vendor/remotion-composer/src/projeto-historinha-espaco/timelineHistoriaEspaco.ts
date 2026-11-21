/**
 * MANUAL — timelineHistoriaEspaco.ts
 * ==================================
 * O que faz
 * ---------
 * Tipos da timeline da historinha "Luninha e Fridóca no Espaço Sideral". Os
 * números reais ficam em timelineHistoriaEspaco.generated.ts, escrito pelo
 * gerador tools/gerar_timeline_historia_espaco.mjs a partir dos MP3 reais.
 *
 * Regra de frame
 * --------------
 * FPS fixo 30; fronteiras = round(segundos * 30), sem folga acumulada.
 */

/** Um trecho narrado posicionado no tempo. */
export interface CenaNaTimelineHistoria {
  /** Id igual ao de CENAS_HISTORIA. */
  id: string;
  /** Segundo em que a cena começa. */
  inicioSegundos: number;
  /** Duração do MP3 da cena, em segundos. */
  duracaoSegundos: number;
  /** Frame em que a cena começa. */
  inicioFrame: number;
  /** Duração da cena em frames. */
  duracaoFrames: number;
}

/** Linha de tempo completa da historinha. */
export interface TimelineHistoria {
  /** Frames por segundo de todo o vídeo. */
  fps: number;
  /** Duração total em frames (o número que o Remotion usa). */
  totalFrames: number;
  /** Duração total em segundos. */
  totalSegundos: number;
  /** Cenas na ordem de reprodução. */
  cenas: CenaNaTimelineHistoria[];
}
