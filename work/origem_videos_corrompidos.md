# Origem dos 6 vídeos corrompidos (Flow)

Fonte: `assets/reference/primeiro-dia-de-praia/flow_all/harvest_manifest.json`
(colhido em **2026-11-23 21:28 UTC**) + `flow_accounts.json`.

**Todos os 6 vieram da mesma conta e do mesmo projeto:**

- Conta: **acc_5** — `xan.pires10@gmail.com`
- Projeto: **Frida e Luna na Praia**
- URL: https://flow.google.com/project/7b9ec48e-9900-453f-98d9-47c2dbf8093c
- O número do tile é a posição da geração na grade do projeto (a ordem em que aparece no histórico do Flow).

| # | Arquivo | Tile | Descrição original no Flow | Tamanho | É praia? |
| ---: | --- | ---: | --- | ---: | --- |
| 1 | `acc_5_7b9ec48e_vid_01_6a9e6af36c.mp4` | 1 | Puppy watching sunscreen tube vi… | 474 KB | talvez (protetor) |
| 2 | `acc_5_7b9ec48e_vid_04_b88e4ae3e4.mp4` | 4 | Puppy shaking water on friend | 402 KB | sim — **já existe versão boa**: `acc_5_7b9ec48e_vid_03_b88e4ae3e4.mp4` (7,93s) |
| 3 | `acc_5_7b9ec48e_vid_09_dfbf643e8e.mp4` | 9 | Puppies gesturing in sunny park | 667 KB | não (parque) |
| 4 | `acc_5_7b9ec48e_vid_10_b0356f7f66.mp4` | 10 | Puppy emerging from pink pillow | 419 KB | não (almofada) |
| 5 | `acc_5_7b9ec48e_vid_13_25a17d41a6.mp4` | 13 | Puppy jumping toward pink pillow | 403 KB | não (almofada) |
| 6 | `acc_5_7b9ec48e_vid_14_1ab0d26708.mp4` | 14 | Dog walking and smiling | 668 KB | genérico |

## Como baixar de novo no Flow

1. Abra a URL do projeto acima com a conta `acc_5` (perfil Chrome `E:\videos\videomaker_v2\.chrome-flow-accounts\acc_5`, porta CDP 18804).
2. Na grade de vídeos, localize os tiles **1, 4, 9, 10, 13 e 14**.
3. Use o botão de download de cada tile e substitua os arquivos em
   `assets/reference/primeiro-dia-de-praia/flow_all/acc_5/videos/`.

## Observação importante

Mesmo que você recupere os 6, **apenas 1 ou 2 são realmente da praia** — os outros eram parque/almofada e
foram parar na seleção por causa da classificação visual antiga. O único que vale a pena recuperar
é o tile 4 ("Puppy shaking water on friend"), e ele **já tem uma cópia válida** (`vid_03`, 7,93s),
então não é necessário baixar de novo para a Parte 2.
