# Suíte de Testes do Videomaker v2

Feature do motor: **catálogo único de testes, diagnósticos e ferramentas de reparo**. A regra é simples: antes de criar um teste novo, consulte este catálogo — provavelmente já existe um script pronto ou adaptável.

Fonte de verdade legível por máquina: `manifest.json`. Ver todos:

```powershell
C:\Docling\venv\Scripts\python.exe tests\suite\runner.py --list
```

Verificar se todos os arquivos catalogados ainda existem:

```powershell
C:\Docling\venv\Scripts\python.exe tests\suite\runner.py --check
```

Rodar um teste pelo id:

```powershell
C:\Docling\venv\Scripts\python.exe tests\suite\runner.py --run unit_all
```

## Catálogo por categoria

### Núcleo (rode sempre antes de commitar)
| Id | Script | Para que serve |
|---|---|---|
| `unit_all` | `tests/test_pipeline_v2.py` | Bateria unitária + ponta a ponta (roteiro, TTS, short, Veo, pesquisa viral, auditoria light) |
| `contract_guard` | `scripts/verify_contract_guard.py` | Invariantes, sintaxe e segurança Git do staging |
| `flow_recover` | `scripts/recover_flow_media.py` | Recupera/audita mídia das 5 contas (`--no-apply` só inspeciona) |
| `revoice_republish` | `scripts/revoice_and_republish.py` | Troca só a narração e republica sem re-render (Regra 15) |

### Voz / TTS
`voices_infantis`, `voices_emocionais`, `voices_final`, `chirp_voices`, `listar_chirp`, `diagnostico_cota`, `amostra_cena1`, `amostra_cena1_v2`, `amostra_emocao_forte`, `amostra_puck`
→ testes de casting, prosódia, cota e amostras piloto. Use `listar_chirp` para inventário grátis; `diagnostico_cota` para erro 429.

### Áudio / mixagem
`join_main_audio`, `join_main_audio_clean`, `join_short_sounds`, `fix_short_sounds`, `bgm_praia`
→ junção de falas (use a `_clean`, nunca `amix`), correção de Shorts mudos e BGM original.

### Roteiro
`encurtar_script`, `rewrite_script`, `restaurar_textos`
→ contagem de palavras, pontuação de piada e restauração da versão aprovada.

### Imagem / mídia do Flow
`check_missing_images`, `make_missing_images`, `ensure_all_images`, `harvest_flow`, `analyze_harvest`
→ conferir/derivar sub-clips, colher mídia das contas e auditar aproveitamento.

### Vídeo
`diag_lipsync`, `publicar_shorts`
→ sincronia labial e publicação PT.

## Convenções

- `mutating: true` no manifesto = o script **modifica arquivos ou publica**. Rode com cuidado.
- `credentials: true` = precisa de `.env`/credenciais locais.
- Use sempre `C:\Docling\venv\Scripts\python.exe` (Regra 12 do contrato).
- Ao criar um teste novo: coloque o arquivo, adicione uma entry em `manifest.json` e uma linha neste README, no mesmo commit.
