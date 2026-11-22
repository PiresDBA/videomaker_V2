# -*- coding: utf-8 -*-
"""Reescreve os 25 textos do roteiro com pontuação de piada (Chirp 3 HD), SEM risada escrita.
Mantém scene_id, speaker, characters, visual_action, sfx e palavras-chave (auditoria narração x imagem)."""
import json, shutil
from pathlib import Path

proj = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo")
sp = proj / "artifacts/script_v2.json"
data = json.loads(sp.read_text(encoding="utf-8"))
shutil.copy2(sp, proj / "artifacts/script_v2_ORIGINAL_divertido.json")

NOVOS = {
 "sc_01": "Eeeei, atletas de quatro patas! Olha só... o cronômetro já tá correndo! O grande Campeonato de Patinhas começou — e olha que essa vai ser a corrida mais engraçada que vocês já viram! Peraí, eu tô feliz demais!",
 "sc_02": "Ai, meu coração, Frida! Olha só... eu nem consigo parar essas patinhas! Tô pulando, pulando, pulando! Aquele prêmio brilhante vai ser nosso, vai? Tô ansiosa demais!",
 "sc_03": "Ei, Frida aqui! Segura essa patinha, viu? Calma, calma... pra ganhar esse campeonato maluco não basta correr, não! Precisa de equilíbrio e inteligência — com estilo, tá? Tô relaxada, confia!",
 "sc_04": "Gente, olha só o que vem aí! O primeiro desafio é a Montanha de Almofadas Gigantes! O segredo? Pular bem alto sem perder o estilo! Quem tá pronto? Eu tô!",
 "sc_05": "Olha pra mim, Frida! Olha só! Eu sou uma molinha saltitante atravessando essas nuvens cor de rosa, fofinhas demais! Ué, que legal, tô voando!",
 "sc_06": "Cuidado, Luna! Ei, devagar! Essas almofadas são muito mais escorregadias do que parecem nesse sol! Vai com calma, que eu tô aqui do seu lado!",
 "sc_07": "Olha o Pipoca passando! Ui, que velocidade! E a Luna... ai, meu bem, tropeçou e saiu rolando que nem uma bolinha de pelo marrom! Sério, que cena!",
 "sc_08": "Eu não caí, não! Foi um giro acrobático super planejado... e muito charmoso, viu? O chão tá macio, eu só quiz testar! Tô de pé, tô ótima!",
 "sc_09": "Tudo bem, artista! Agora vem o desafio da Pista de Sabão! Olha só essas bolinhas flutuantes... elas podem confundir nosso faro, tá? Vamos com calma!",
 "sc_10": "Eu adoro bolinhas de sabão! Olha só, vou morder todas elas antes do Pipoca atravessar essa nuvem transparente e brilhante! Credo que é divertido!",
 "sc_11": "Gente, vocês não vão acreditar! A Frida respirou fundo e soltou um espirro tão potente... que todas as bolinhas estouraram! O caminho tá livre, Luna!",
 "sc_12": "Isso foi incrível, Fridóca! Seu nariz é um superpoder secreto! Salvou a nossa pele agora mesmo! Ué, tô impressionada, sério!",
 "sc_13": "Agora o clima esquenta! Olha só a Ponte de Biscoito! Um passo em falso e os competidores acabam devorando o próprio caminho! Ai, que tensão!",
 "sc_14": "Concentração total, Luna! Não olha pra baixo... e, principalmente, não tenta lamber a ponte, senão a gente cai na grama! Confia em mim, vai!",
 "sc_15": "É impossível resistir a esse cheirinho de baunilha, Frida! Meu estômago tá roncando mais alto que motor de carro! Tô com fome, sério!",
 "sc_16": "Olha só... a Luna se distraiu com o aroma e saiu correndo pro lado errado! Seguiu o rastro de um biscoito perdido! Ai, para, volta!",
 "sc_17": "Volta aqui, salsichinha teimosa! O troféu tá logo ali... mas você tá indo direto pra barraca de lanches! Credo, menina, para!",
 "sc_18": "O mistério final aguarda! Olha só... o Túnel de Lençóis! Um labirinto colorido cheio de brinquedos que fazem barulhos engraçados! Tô curiosa!",
 "sc_19": "Eu não vejo nada aqui dentro, Frida! Tem alguma coisa macia cutucando minha orelha... e eu acho que tô presa! Ai, socorro!",
 "sc_20": "Mantém a calma, tô logo atrás de você! Usa seu faro pra encontrar a saída desse túnel de pano bagunçado! Vai, você consegue!",
 "sc_21": "Olha só quem chegou! A Frida emerge triunfante... mas com uma meia colorida pendurada na orelha! Que acessório de moda canina, hein? Tô rindo!",
 "sc_22": "Você tá linda com esse visual, Frida! O Pipoca chegou primeiro, mas nóis ganhamos no quesito diversão! Olha só essa meia, que engraçado!",
 "sc_23": "O juiz anunciou! Embora não tenham levado o ouro, Frida e Luna ganharam o Troféu de Maiores Palhaças da Competição! Que legal, viu?",
 "sc_24": "Viu só, Luna? O importante não é ser a mais rápida... é aproveitar cada tropeço e brincadeira com sua melhor amiga! Tô tão feliz!",
 "sc_25": "A verdadeira vitória é o sorriso que a gente compartilha! Olha só... deixa seu like e se inscreve pra mais aventuras com a gente! Tchau, tchau!",
}
EMO = "alegre, divertida, sorridente, infantil e empolgada — ritmo leve de piada, frases curtas"
for sc in data["scenes"]:
    sid = sc["scene_id"]
    if sid in NOVOS:
        sc["text"] = NOVOS[sid]
    sc["emotion_direction"] = EMO
sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Roteiro reescrito:", len(data["scenes"]), "cenas | backup em script_v2_ORIGINAL_divertido.json")
