/**
 * MANUAL — entradaQuatroEstacoes.tsx
 * ================================
 * O que faz
 * ---------
 * Ponto de entrada isolado do Remotion para o vídeo "Quatro Estações na Janela
 * do Trem". Registra apenas a composição `QuatroEstacoesJanelaTrem`, sem carregar
 * o `Root.tsx` inteiro.
 *
 * Por que existe
 * --------------
 * O `Root.tsx` é compartilhado com outros bots da cadeia e, durante a montagem,
 * recebe imports de arquivos que ainda estão sendo escritos. Este arquivo
 * permite renderizar e validar o vídeo sem depender do estado do Root naquele
 * instante. A composição continua registrada também no Root, para o Studio.
 *
 * Como usar
 * ---------
 * npx remotion render src/projeto-quatro-estacoes/entradaQuatroEstacoes.tsx \
 *   QuatroEstacoesJanelaTrem out/video-quatro-estacoes.mp4
 */

import { Composition, registerRoot } from "remotion";  // 1. registro e declaração de composição
import { QuatroEstacoesJanelaTrem, QUATRO_ESTACOES_METADADOS } from "./QuatroEstacoesJanelaTrem";

/** Raiz mínima: uma única composição, com os metadados da timeline. */
const RaizQuatroEstacoes: React.FC = () => (
  <Composition
    id="QuatroEstacoesJanelaTrem"                                        // 2. id igual ao do Root
    component={QuatroEstacoesJanelaTrem}                                // 3. componente da timeline
    durationInFrames={QUATRO_ESTACOES_METADADOS.durationInFrames}       // 4. 3376 frames
    fps={QUATRO_ESTACOES_METADADOS.fps}                                 // 5. 30 fps
    width={QUATRO_ESTACOES_METADADOS.width}                             // 6. 1920
    height={QUATRO_ESTACOES_METADADOS.height}                           // 7. 1080
  />
);

registerRoot(RaizQuatroEstacoes);  // 8. entrega a raiz ao Remotion
