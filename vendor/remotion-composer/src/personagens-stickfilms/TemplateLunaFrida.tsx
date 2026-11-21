/**
 * MANUAL - TemplateLunaFrida.tsx
 * ==============================
 * O que faz
 * ---------
 * DEMO do template das personagens principais: Luna e Frida (sprites oficiais
 * do StickFilms) executando os movimentos do catálogo — correr, andar, pular,
 * dançar, rolar, parado, deitada, brincando — lado a lado, com rótulos.
 *
 * Por que existe
 * --------------
 * O usuário pediu um TEMPLATE pronto: "sempre que usá-las, pode usar esse
 * template". Esta composição serve de vitrine e de teste visual do
 * `SpritePersonagem`, e também mostra os avatares SVG do catálogo falando
 * (lip-sync RMS) para lembrar que a boca sincronizada vive lá.
 *
 * Como usar
 * ---------
 * - Studio: composição `TemplateLunaFrida` (1280x720, 30 fps).
 * - Para renderizar: --scale=0.5 (640x360) e upscale lanczos para 1280x720.
 *
 * Regra
 * -----
 * Sem IA, sem GPU; todo movimento vem das sprite sheets oficiais e do frame.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";        // 1. base
import { loadSpaceGrotesk } from "../lib/localFonts";            // 2. fonte local
import { SpritePersonagem, movimentosDe } from "./SpritePersonagem";  // 3. template

const fonte = loadSpaceGrotesk(["500", "700"]);                  // 4. rótulos

/** Movimentos que a vitrine exibe (mesmo nome do SEQUENCIAS). */
const MOVIMENTOS_VITRINE = ["correr", "andar", "pular", "dancar", "divertir", "parado", "rolar", "deitada"] as const;

export const TemplateLunaFrida: React.FC = () => {
  const frame = useCurrentFrame();                               // 5. frame global (ciclos correm juntos)

  return (
    <AbsoluteFill style={{ backgroundColor: "#F6F2E9", fontFamily: "sans-serif" }}>
      {/* 6. título */}
      <div style={{ position: "absolute", top: 24, left: 0, right: 0, textAlign: "center", color: "#050403" }}>
        <div style={{ fontSize: 40, fontWeight: 700, ...fonte }}>
          Template de movimentos — Luna e Frida
        </div>
        <div style={{ fontSize: 18, opacity: 0.7, marginTop: 4, ...fonte }}>
          Sprites oficiais do StickFilms · use &lt;SpritePersonagem&gt; em qualquer cena nova
        </div>
      </div>

      {/* 7. linhas: um movimento por linha, Luna à esquerda e Frida à direita */}
      <div style={{ position: "absolute", top: 108, left: 40, right: 40, bottom: 60 }}>
        {MOVIMENTOS_VITRINE.map((movimento, indice) => {
          const y = indice * 62;                                 // 8. linha vertical
          const rotulo = `${movimento}`;                         // 9. rótulo do movimento
          return (
            <div key={movimento} style={{ position: "absolute", top: y, left: 0, right: 0, height: 62 }}>
              {/* 10. rótulo */}
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 18,
                  width: 130,
                  textAlign: "right",
                  color: "#050403",
                  fontSize: 20,
                  fontWeight: 700,
                  ...fonte,
                }}
              >
                {rotulo}
              </div>
              {/* 11. Luna se mexendo para um lado... */}
              <SpritePersonagem personagem="luna" movimento={movimento} lado="direita" frame={frame} x={150} altura={64} />
              {/* 12. ...e Frida se mexendo para o outro */}
              <SpritePersonagem personagem="frida" movimento={movimento} lado="esquerda" frame={frame} x={640} altura={64} />
              {/* 13. segundo par: mesmo movimento no lado oposto, defasado */}
              <SpritePersonagem personagem="luna" movimento={movimento} lado="esquerda" frame={frame + 15} x={950} altura={64} />
              <SpritePersonagem personagem="frida" movimento={movimento} lado="direita" frame={frame + 15} x={1140} altura={64} />
            </div>
          );
        })}
      </div>

      {/* 14. rodapé com a origem */}
      <div style={{ position: "absolute", bottom: 16, left: 0, right: 0, textAlign: "center", color: "#6b4423", fontSize: 16, ...fonte }}>
        Fonte das poses: C:/Users/Pires/StickFilms/characters (cópia em public/personagens-stickfilms/) · catálogo em sequenciasMovimento.ts
      </div>
    </AbsoluteFill>
  );
};

/** Metadados para o registro em Root.tsx. */
export const TEMPLATE_LUNA_FRIDA_METADADOS = {
  fps: 30,
  width: 1280,
  height: 720,
} as const;
