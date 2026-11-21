/**
 * MANUAL - CatalogoAvatares.tsx
 * =============================
 * O que faz
 * ---------
 * Composição de prévia com TODOS os avatares do catálogo falando ao mesmo tempo,
 * cada um com nome e id visíveis. É a "lista" para o usuário escolher qual
 * boneco quer usar na historinha.
 *
 * Por que existe
 * --------------
 * Sem uma prévia, escolher um avatar exigiria renderizar o vídeo inteiro.
 * Aqui bastam 12 s de narração: a boca de todos usa a mesma energia real da voz.
 *
 * Como usar
 * ---------
 * npx remotion studio  -> composição "CatalogoAvatares"
 * ou: npx remotion still src/index.tsx CatalogoAvatares out.png --frame=120
 *
 * Regra
 * -----
 * Só `useCurrentFrame()` + interpolação pura; nenhum vídeo gerado por IA,
 * nenhum uso de GPU além do render normal do Remotion.
 */

import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";  // 1. base do Remotion
import { aberturaBocaNoFrame } from "./SincronizacaoLabial";  // 2. motor de lip-sync (RMS real)
import { VALORES_BECA_SINCRONIZACAO_LABIAL_NARRACAO_COMPLETA } from "./dados/sincronizacao-labial-narracao-completa";  // 3. trilha por frame
import { CATALOGO_AVATARES } from "./avatares/registroAvatares";  // 4. lista de bonecos
import { AvatarSelecionavel } from "./avatares/AvatarSelecionavel";  // 5. cartão selecionável

export const CatalogoAvatares: React.FC = () => {
  const frame = useCurrentFrame();                                            // 6. frame absoluto
  const aberturaBoca = aberturaBocaNoFrame(                                   // 7. boca de verdade
    VALORES_BECA_SINCRONIZACAO_LABIAL_NARRACAO_COMPLETA,
    frame,
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#1b120c", fontFamily: "sans-serif" }}>
      {/* 8. narração real de 12 s para conferir o movimento da boca */}
      <Audio src={staticFile("audio-quatro-estacoes/narracao_quatro_estacoes_completa.mp3")} trimAfter={360} />

      {/* 9. título e instrução */}
      <div style={{ position: "absolute", top: 34, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ color: "#F4E9D8", fontSize: 42, fontWeight: 700, letterSpacing: 1 }}>
          Escolha quem vai contar a historinha
        </div>
        <div style={{ color: "#D9A441", fontSize: 19, marginTop: 8 }}>
          Todos falam com a mesma narração real. Escolha pelo id em --props ou na aba Props do Studio.
        </div>
      </div>

      {/* 10. os cinco avatares lado a lado */}
      <div
        style={{
          position: "absolute",
          top: 138,
          left: 30,
          right: 30,
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        {CATALOGO_AVATARES.map((avatar) => (
          <div key={avatar.id} style={{ flex: 1, minWidth: 0 }}>
            <AvatarSelecionavel
              idAvatar={avatar.id}
              aberturaBoca={aberturaBoca}
              frameLocal={frame + 30}
              estiloPosicao="centro"
              mostrarNome
            />
            <div style={{ color: "#9FC9C2", fontSize: 16, textAlign: "center", marginTop: 10, wordBreak: "break-all" }}>
              {avatar.id}
            </div>
          </div>
        ))}
      </div>

      {/* 11. rodapé com o comando de seleção */}
      <div style={{ position: "absolute", bottom: 26, left: 0, right: 0, textAlign: "center", color: "rgba(244,233,216,0.7)", fontSize: 18 }}>
        Exemplo: --props={'{"idAvatar":"buldogue-ingles"}'} na composição QuatroEstacoesJanelaTrem
      </div>
    </AbsoluteFill>
  );
};
