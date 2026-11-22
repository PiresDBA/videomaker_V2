# -*- coding: utf-8 -*-
"""Encurta os textos para 450-550 palavras MANTENDO pontuacao de piada e palavras-chave."""
import json, re
from pathlib import Path
sp = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo/artifacts/script_v2.json")
data = json.loads(sp.read_text(encoding="utf-8"))

CURTOS = {
 "sc_01": "Eeeei, atletas de quatro patas! Olha só... o cronômetro tá correndo! O Campeonato de Patinhas começou — e essa vai ser a corrida mais engraçada que vocês viram!",
 "sc_02": "Ai, meu coração, Frida! Olha só... eu nem consigo parar as patinhas! Tô pulando, pulando! O prêmio brilhante vai ser nosso, vai? Ansiedade pura!",
 "sc_03": "Ei, Frida aqui! Segura essa patinha! Calma... pra ganhar esse campeonato maluco não basta correr, não! Precisa de equilíbrio e inteligência!",

 "sc_04": "Gente, olha só o que vem aí! A Montanha de Almofadas Gigantes! O segredo? Pular alto sem perder o estilo! Quem tá pronto? Eu tô!",
 "sc_05": "Olha pra mim, Frida! Eu sou uma molinha saltitante atravessando essas nuvens cor de rosa! Ué, que legal, tô voando!",
 "sc_06": "Cuidado, Luna! Ei, devagar! Essas almofadas são muito mais escorregadias do que parecem nesse sol! Vai com calma, tô aqui do seu lado!",
 "sc_07": "Olha o Pipoca passando! Ui, que velocidade! E a Luna... ai, tropeçou e saiu rolando que nem bolinha de pelo marrom! Que cena!",
 "sc_08": "Eu não caí, não! Foi um giro acrobático super planejado... e muito charmoso, viu? O chão tá macio, só quiz testar! Tô de pé!",
 "sc_09": "Tudo bem, artista! Agora vem a Pista de Sabão! Olha só essas bolinhas flutuantes... elas confundem nosso faro, tá? Vamos com calma!",
 "sc_10": "Adoro bolinhas de sabão! Olha só, vou morder todas antes do Pipoca atravessar essa nuvem transparente e brilhante! Credo que é divertido!",
 "sc_11": "Gente, vocês não vão acreditar! A Frida soltou um espirro tão potente... que todas as bolinhas estouraram! Caminho livre, Luna!",
 "sc_12": "Isso foi incrível, Fridóca! Seu nariz é um superpoder secreto! Salvou a nossa pele agora mesmo! Tô impressionada, sério!",
 "sc_13": "Agora o clima esquenta! Olha só a Ponte de Biscoito! Um passo em falso e os competidores devoram o próprio caminho! Ai, que tensão!",
 "sc_14": "Concentração total, Luna! Não olha pra baixo... e não tenta lamber a ponte, senão a gente cai na grama! Confia em mim, vai!",
 "sc_15": "Impossível resistir a esse cheirinho de baunilha, Frida! Meu estômago ronca mais alto que motor de carro! Tô com fome, sério!",
 "sc_16": "Olha só... a Luna se distraiu com o aroma e saiu correndo pro lado errado! Seguiu o rastro de um biscoito perdido! Ai, para, volta!",
 "sc_17": "Volta aqui, salsichinha teimosa! O troféu tá logo ali... mas você tá indo direto pra barraca de lanches! Credo, para!",
 "sc_18": "O mistério final aguarda! Olha só... o Túnel de Lençóis! Labirinto colorido cheio de brinquedos que fazem barulhos engraçados! Tô curiosa!",
 "sc_19": "Eu não vejo nada aqui dentro, Frida! Tem alguma coisa macia cutucando minha orelha... e eu acho que tô presa! Ai, socorro!",
 "sc_20": "Mantém a calma, tô logo atrás! Usa seu faro pra encontrar a saída desse túnel de pano bagunçado! Vai, você consegue!",
 "sc_21": "Olha só quem chegou! A Frida emerge triunfante... mas com uma meia colorida pendurada na orelha! Que acessório de moda canina!",
 "sc_22": "Você tá linda com esse visual, Frida! O Pipoca chegou primeiro, mas nóis ganhamos no quesito diversão! Olha só essa meia, que engraçado!",
 "sc_23": "O juiz anunciou! Embora não tenham levado o ouro, Frida e Luna ganharam o Troféu de Maiores Palhaças! Que legal, viu?",
 "sc_24": "Viu só, Luna? O importante não é ser a mais rápida... é aproveitar cada tropeço e brincadeira com sua melhor amiga! Tô tão feliz!",
 "sc_25": "A vitória é o sorriso que a gente compartilha! Olha só... deixa seu like e se inscreve pra mais aventuras!",
}
for sc in data["scenes"]:
    if sc["scene_id"] in CURTOS:
        sc["text"] = CURTOS[sc["scene_id"]]
n = sum(len(re.findall(r"\S+", s["text"])) for s in data["scenes"])
print("palavras:", n)
sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
