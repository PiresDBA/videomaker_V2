import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.script_engine import generate_script, count_total_words, validate_script_schema  # noqa: E402

TEMA = (
    "O Primeiro Dia de Praia da Frida e Luna — VERSÃO GANCHO DE YOUTUBER. "
    "ABERTURA OBRIGATORIA: cena 1 com cold-open de 2 a 3 segundos, Frida e Luna olhando DIRETO para a camera "
    "com olhos arregalados e sorriso, uma pergunta engraçada e curta tipo 'Voce ja viu uma salsicha tentar domar o mar?' "
    "e um flash rapido da onda e da gaivota roubando o biscoito. So depois entre na acao. "
    "E PROIBIDO comecar com oi, bom dia ou bem-vindos. "
    "Use 28 a 32 cenas curtas com MUITOS gags: areia grudando no focinho, protetor solar saindo do tubo e virando "
    "patinagem, concha cantora com fanfarra, gaivota Guga em 3 planos (chegando, mergulhando, fugindo com o biscoito), "
    "onda molhando as duas, castelo de areia destruido, Luna enterrada na areia rindo. "
    "Interjecoes, piadas curtas no meio das falas e catchphrase repetida. Naracao muito alegre e risonha. "
    "CENA FINAL obrigatoria: as duas acenando e dizendo tchau para a camera com CTA de inscreva-se e logotipo do "
    "YouTube visivel (SUBSCRIBE). CTA apenas na ultima cena. 3 atos, 450 a 550 palavras."
)

out = ROOT / "projects" / "primeiro-dia-de-praia-2" / "artifacts" / "script_v2.json"
data = generate_script(TEMA, out, min_words=450, max_words=550)
print("cenas:", len(data["scenes"]), "palavras:", count_total_words(data))
print("erros:", validate_script_schema(data, 450, 550))
print("cena1:", data["scenes"][0]["text"][:160])
print("cena_final:", data["scenes"][-1]["text"][:160])
