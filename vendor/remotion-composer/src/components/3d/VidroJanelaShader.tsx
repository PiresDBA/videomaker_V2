/**
 * MANUAL — VidroJanelaShader.tsx
 * ---------------------------------------------------------------------------
 * O QUE FAZ
 *   Vidro da janela do vagão (módulo 6.1 da especificação): reflexo fraco do
 *   interior, micro-sujeira e leve dispersão cromática nas bordas. Não é um
 *   vidro "limpo": é vidro de trem antigo, sujo na medida certa.
 *
 * COMO USAR
 *   <VidroJanelaShader largura={2.42} altura={1.34} corTinta="#DCEBDA" />
 *
 * ENTRADA / SAÍDA
 *   Entrada: dimensões da abertura, cor de tinta da estação e intensidade.
 *   Saída: plano com ShaderMaterial transparente (não escreve profundidade).
 *
 * REGRAS RESPEITADAS
 *   - Animação só por uniform `uFrame` vindo de useCurrentFrame(); sem useFrame.
 *   - Sem textura externa: ruído calculado no fragment shader.
 *   - depthWrite desligado: o vidro nunca esconde o cenário atrás dele.
 */

import { useCurrentFrame } from "remotion";
import * as THREE from "three";
// carrega os tipos JSX do @react-three/fiber (mesh, planeGeometry, shaderMaterial)
import "@react-three/fiber";

// Vertex shader mínimo: passa a UV e projeta a posição normalmente.
const VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;                 // coordenada 0..1 do plano
  void main() {
    vUv = uv;                       // repassa para o fragment
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// Fragment shader do vidro, derivado do código da especificação (6.1).
const FRAGMENT_SHADER = /* glsl */ `
  varying vec2 vUv;
  uniform float uFrame;             // frame atual (animação determinística)
  uniform vec3 uTint;               // tinta da estação
  uniform float uReflexo;           // 0..1 força do reflexo do interior
  uniform float uSujeira;           // 0..1 quantidade de micro-sujeira

  // Hash barato: ruído determinístico sem textura.
  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }

  // Ruído suave em duas oitavas: manchas de sujeira, nunca nítidas.
  float ruido(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    vec2 u = f * f * (3.0 - 2.0 * f);
    float n = mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
    return n * 0.65 + ruidoOctava(p * 2.3) * 0.35;
  }

  // Segunda oitava isolada para evitar recursão.
  float ruidoOctava(vec2 p) {
    return hash(floor(p) + 7.31);
  }

  void main() {
    vec2 uv = vUv;

    // Micro-sujeira: manchas lentas que respiram com o frame.
    float sujeira = ruido(uv * 6.0 + uFrame * 0.0004) * 0.06 * uSujeira;

    // Reflexo do interior: faixa vertical desfocada à direita do vidro.
    float reflexo = smoothstep(0.58, 1.0, uv.x) * 0.10 * uReflexo;

    // Dispersão cromática de ~2 px nas bordas.
    float borda = smoothstep(0.0, 0.05, min(uv.x, 1.0 - uv.x));
    vec3 base = uTint * 0.10;            // tinta bem fraca: o mundo manda
    vec3 crom = vec3(base.r * (1.0 + borda * 0.02), base.g, base.b * (1.0 - borda * 0.02));

    // Alpha baixo: vidro quase invisível, só o brilho aparece.
    float alpha = 0.16 + reflexo + sujeira;
    gl_FragColor = vec4(crom + reflexo, clamp(alpha, 0.0, 0.45));
  }
`;

export interface VidroJanelaShaderProps {
  /** Largura da abertura em unidades de mundo. */
  largura: number;
  /** Altura da abertura em unidades de mundo. */
  altura: number;
  /** Cor de tinta do vidro (luz da estação). */
  corTinta?: string;
  /** Intensidade do reflexo do interior, 0..2 (padrão 1). */
  reflexo?: number;
  /** Intensidade da sujeira, 0..2 (padrão 1). */
  sujeira?: number;
  /** Posição do plano no mundo. */
  posicao?: [number, number, number];
}

export const VidroJanelaShader: React.FC<VidroJanelaShaderProps> = ({
  largura,
  altura,
  corTinta = "#DCEBDA",
  reflexo = 1,
  sujeira = 1,
  posicao = [0, 1.45, 0],
}) => {
  const frame = useCurrentFrame(); // único relógio permitido

  return (
    <mesh position={posicao}>
      <planeGeometry args={[largura, altura]} />
      <shaderMaterial
        transparent // deixa o mundo aparecer
        depthWrite={false} // não oclui o que está atrás
        vertexShader={VERTEX_SHADER}
        fragmentShader={FRAGMENT_SHADER}
        uniforms={{
          uFrame: { value: frame },
          uTint: { value: new THREE.Color(corTinta) },
          uReflexo: { value: reflexo },
          uSujeira: { value: sujeira },
        }}
      />
    </mesh>
  );
};
