# -*- coding: utf-8 -*-
"""Restaura os textos completos (versao 568 palavras, aprovada pelo usuario) e ajusta limite."""
import json, re
from pathlib import Path
sp = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo/artifacts/script_v2.json")
data = json.loads(sp.read_text(encoding="utf-8"))
COMPLETOS = {
 "sc_01": "Eeeei, atletas de quatro patas! Olha só... o cronômetro tá correndo! O Campeonato de Patinhas começou — e essa vai ser a corrida mais engraçada que vocês viram! Tô feliz demais!",
 "sc_03": "Ei, Frida aqui! Segura essa patinha, viu? Calma, calma... pra ganhar esse campeonato maluco não basta correr, não! Precisa de equilíbrio e inteligência — com estilo!",
 "sc_13": "Agora o clima esquenta! Olha só a Ponte de Biscoito! Um passo em falso e os competidores acabam devorando o próprio caminho! Ai, que tensão!",
 "sc_25": "A vitória é o sorriso que a gente compartilha! Olha só... deixa seu like e se inscreve pra mais aventuras! Tchau, tchau!",
}
for sc in data["scenes"]:
    if sc["scene_id"] in COMPLETOS:
        sc["text"] = COMPLETOS[sc["scene_id"]]
n = sum(len(re.findall(r"\S+", s["text"])) for s in data["scenes"])
sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("palavras:", n)
