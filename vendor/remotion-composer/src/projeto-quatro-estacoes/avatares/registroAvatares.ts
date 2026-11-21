/**
 * MANUAL - registroAvatares.ts
 * ============================
 * O que faz
 * ---------
 * Catálogo único de avatares cartoon 2D do projeto. Aqui está a LISTA de onde
 * o usuário escolhe qual boneco aparece no vídeo.
 *
 * Por que existe
 * --------------
 * O avatar não pode ser fixo: o usuário quer trocar entre buldogue inglês,
 * salsicha marrom, menina de cabelo escuro, menino loiro e o mascote original,
 * além de adicionar outros depois.
 *
 * Como escolher
 * -------------
 * - No render: --props='{"idAvatar":"buldogue-ingles"}'
 * - No Studio: aba Props da composição QuatroEstacoesJanelaTrem.
 * - Em código: troque AVATAR_PADRAO abaixo.
 *
 * Regra para adicionar
 * ---------------------
 * Desenhe um componente que receba { aberturaBoca, frame }, devolva um SVG no
 * viewBox 600x704 e registre aqui com id, nome e descrição.
 */

import type { ComponentType } from "react";                       // 1. tipo do componente de arte
import { AvatarBuldogueIngles, AvatarSalsichaMarrom } from "./AvataresCaes";  // 2. cães
import { AvatarMeninaCabeloEscuro, AvatarMeninoCabeloLoiro } from "./AvataresCriancas";  // 3. crianças
import { AvatarMascoteCartoon } from "./AvatarMascoteCartoon";    // 4. mascote original

/** Identificadores estáveis, usados na prop idAvatar e nos arquivos de prévia. */
export type IdAvatar =
  | "buldogue-ingles"
  | "salsicha-marrom"
  | "menina-cabelo-escuro"
  | "menino-cabelo-loiro"
  | "mascote-quatro-estacoes";

/** Um boneco do catálogo. */
export interface DefinicaoAvatar {
  id: IdAvatar;                                                   // 5. chave de seleção
  nome: string;                                                   // 6. nome amigável
  categoria: "cao" | "crianca" | "mascote";                       // 7. agrupamento na lista
  descricao: string;                                              // 8. como é
  /** Personagem canônico da ficha FICHA-PERSONAGENS-HISTORINHA.md (null = não é protagonista). */
  personagem: "luna" | "frida" | null;                            // 8b. consistência de personagem
  /** Voz/idioma canônico da ficha (null = sem voz definida). */
  voz?: string | null;                                            // 8c. voz oficial
  Componente: ComponentType<{ aberturaBoca: number; frame: number }>;  // 9. arte SVG
}

/** LISTA OFICIAL DE AVATARES — ordem de exibição no catálogo.
 *  Luna e Frida são as protagonistas da historinha (ficha
 *  FICHA-PERSONAGENS-HISTORINHA.md): nunca trocar raça, cor ou voz delas. */
export const CATALOGO_AVATARES: DefinicaoAvatar[] = [
  {
    id: "salsicha-marrom",                                        // 11. LUNA - protagonista
    nome: "Luna (Luninha) - salsicha marrom",
    categoria: "cao",
    descricao: "Dachshund marrom tom único, orelhas compridas e rabo comprido. Narradora padrão. Voz pt-BR infantil.",
    personagem: "luna",
    voz: "pt-BR infantil, emocional",
    Componente: AvatarSalsichaMarrom,
  },
  {
    id: "buldogue-ingles",                                        // 10. FRIDA - protagonista
    nome: "Frida (Fridóca) - buldogue inglês",
    categoria: "cao",
    descricao: "Buldogue fawn/branco, focinho curto, rugas e colarinho com Union Jack. Voz en-US.",
    personagem: "frida",
    voz: "en-US, emocional",
    Componente: AvatarBuldogueIngles,
  },
  {
    id: "menina-cabelo-escuro",                                   // 12. pedido novo
    nome: "Menina de cabelo escuro",
    categoria: "crianca",
    descricao: "Tranças laterais, presilha estrelinha e vestido mostarda.",
    personagem: null,
    Componente: AvatarMeninaCabeloEscuro,
  },
  {
    id: "menino-cabelo-loiro",                                    // 13. pedido novo
    nome: "Menino de cabelo loiro",
    categoria: "crianca",
    descricao: "Franja lateral, sardas e suéter verde-azulado.",
    personagem: null,
    Componente: AvatarMeninoCabeloLoiro,
  },
  {
    id: "mascote-quatro-estacoes",                                // 14. avatar anterior
    nome: "Mascote Quatro Estações",
    categoria: "mascote",
    descricao: "Chapéu terracota, cachecol mostarda e passarinho. O original do vídeo.",
    personagem: null,
    Componente: AvatarMascoteCartoon,
  },
];

/** Avatar usado quando nada é escolhido — ficha de consistência manda LUNA
 *  (salsicha-marrom) como narradora padrão do canto. */
export const AVATAR_PADRAO: IdAvatar = "salsicha-marrom";          // 15. padrão (Luna)

/** Resolve um id para a definição; id desconhecido cai no padrão. */
export const obterDefinicaoAvatar = (id?: string): DefinicaoAvatar => {
  return CATALOGO_AVATARES.find((avatar) => avatar.id === id)     // 16. procura
    ?? CATALOGO_AVATARES.find((avatar) => avatar.id === AVATAR_PADRAO)  // 17. fallback
    ?? CATALOGO_AVATARES[0];                                       // 18. segurança
};
