# -*- coding: utf-8 -*-
"""Constroi o episodio v7 (auditado): roteiro narrado, vozes locais, slow-motion suave.

Correcoes cirurgicas aplicadas (2026-11-24):
  * roteiro CONTA a historia com narrador (>= 55% das cenas); Frida e Luna entram
    de vez em quando (nunca 2 cenas seguidas so de personagem);
  * cada cena foi escrita PARA uma imagem real do pool (mapa PREFERRED_IMAGES):
    nada de imagem de outro assunto, e nenhuma imagem repetida;
  * personagem secundaria "Gaivota Guga" fora do roteiro e da blacklist (SHA);
  * imagens: 1 base por cena, sem repetir em cenas vizinhas, cota global <= 2;
  * despedida: confete + SUBSCRIBE (sem a parte com patinha fantasma);
  * videos Veo existentes 100% reaproveitados (Regra 25).

Uso: python work/build_v7.py [--stage script|tts|pacing|images|all] [slug]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE, TARGET_VEO_VIDEOS  # noqa: E402
from core.image_assignment import assign_images  # noqa: E402
from core.pacing_planner import build_pacing_plan  # noqa: E402
from core.script_engine import validate_script_schema  # noqa: E402
from core.voice_studio import synthesize_all_scenes  # noqa: E402

SRC_SLUG = "primeiro-dia-de-praia-v6"
REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"

# ---------------------------------------------------------------------------
# Roteiro v7: narracao conduz; personagens comentam (9 cenas de 30).
# Cada cena descreve EXATAMENTE a imagem escolhida em PREFERRED_IMAGES.
# ---------------------------------------------------------------------------
SCENES: list[dict] = [
    dict(sid="sc_01", act=1, spk="narrador", av="none",
         text="Era o primeiro dia de praia da Frida e da Luna, e elas chegaram bem animadas com toalha, baldinho e o tubo de protetor!",
         vis="Frida e Luna sentadas na toalha colorida com o tubo de protetor solar e o baldinho na areia.",
         loc="Toalha colorida na areia", sfx="cartoon fanfare",
         gag="As duas olham para a praia inteira com os olhos brilhando."),
    dict(sid="sc_02", act=1, spk="narrador", av="none",
         text="Mal pisaram na areia molhada, uma ondinha veio de mansinho e molhou as quatro patinhas de uma vez.",
         vis="Frida e Luna na beira da água, uma ondinha fina chegando nas patinhas.",
         loc="Beira do mar com areia molhada", sfx="cartoon splash",
         gag="Luna levanta uma patinha de cada vez, surpresa com a água fria."),
    dict(sid="sc_03", act=1, spk="narrador", av="none",
         text="Aí veio outra onda, bem maior, e explodiu em espuma branca na frente das duas!",
         vis="Uma onda grande estoura em espuma branca na frente de Frida e Luna.",
         loc="Ondas na beira da praia", sfx="cartoon splash",
         gag="A espuma cobre as duas e depois escorre."),
    dict(sid="sc_04", act=1, spk="luna", av="luna",
         text="Ai, ai, ai! Essa água é gelada, mas eu quero mais uma vez!",
         vis="Frida encharcada dentro da água rasa, Luna ao lado na espuma.",
         loc="Água rasa da praia", sfx="cartoon giggle",
         gag="Luna treme toda e já corre de volta para a água."),
    dict(sid="sc_05", act=1, spk="narrador", av="none",
         text="Elas voltaram correndo para a toalha colorida, deixando um rastro de patinhas molhadas na areia.",
         vis="Frida e Luna voltando para a toalha colorida, patinhas molhadas, tubo de protetor no chão.",
         loc="Toalha colorida na areia", sfx="cartoon run",
         gag="O rastro de patinhas parece uma estrada de bolinhas."),
    dict(sid="sc_06", act=1, spk="narrador", av="none",
         text="Antes de qualquer aventura, tinha uma missão muito séria: passar protetor solar em todo mundo.",
         vis="Frida segura o tubo amarelo de protetor solar perto da toalha, com os brinquedos de praia ao fundo.",
         loc="Toalha colorida na areia", sfx="cartoon boing",
         gag="Frida aperta o tubo e ele faz um barulhinho de ar."),
    dict(sid="sc_07", act=1, spk="frida", av="frida",
         text="Segura firme, Luna! Esse tubo escorrega mais do que salsicha na areia molhada!",
         vis="Frida apertando o tubo de protetor com as duas patas, Luna observando de perto.",
         loc="Toalha colorida na areia", sfx="cartoon boing",
         gag="Um fio de creme voa para o alto e some."),
    dict(sid="sc_08", act=1, spk="narrador", av="none",
         text="E foi exatamente isso que aconteceu: o creme espirrou e a Luna saiu patinando pela praia inteira.",
         vis="Luna deslizando de barriga sobre o creme branco derramado na areia, tubo caído ao lado.",
         loc="Areia lisa da praia", sfx="cartoon spin",
         gag="Luna gira como um pião e para de bumbum no chão."),
    dict(sid="sc_09", act=1, spk="narrador", av="none",
         text="A Frida tentou segurar, escorregou também, e as duas viraram dois peixinhos de creme.",
         vis="Frida e Luna escorregando juntas no creme branco, com o tubo de protetor atrás.",
         loc="Areia lisa da praia", sfx="cartoon giggle",
         gag="As duas terminam deitadas de barriga para cima."),
    dict(sid="sc_10", act=1, spk="luna", av="luna",
         text="Olha só! Eu virei um fantasminha branco e cheiroso... buuuu! Assusta não, tá?",
         vis="Luna coberta de espuma branca de protetor, só o focinho e os olhos aparecendo, Frida rindo.",
         loc="Areia da praia", sfx="cartoon giggle",
         gag="Luna faz pose de fantasma e escorrega de novo."),
    dict(sid="sc_11", act=2, spk="narrador", av="none",
         text="Depois do banho de creme, começou a obra mais importante do dia: o castelo de areia!",
         vis="Frida e Luna cavando juntas ao lado do castelo de areia, balde vermelho e pá azul.",
         loc="Areia fofa para o castelo", sfx="cartoon boing",
         gag="O balde voa para cima e cai de boca na areia."),
    dict(sid="sc_12", act=2, spk="narrador", av="none",
         text="A Luna cavou tanto que desapareceu dentro do buraco, e só o rabinho ficou de fora!",
         vis="Luna enterrada na areia até o pescoço, só a cabeça e o rabo aparecendo, balde vermelho ao lado.",
         loc="Buraco no castelo de areia", sfx="cartoon sniff",
         gag="O rabo abana e joga areia para todo lado."),
    dict(sid="sc_13", act=2, spk="luna", av="luna",
         text="Socorro! Eu tô enterrada até o pescoço e essa areia tá fazendo cócegas na barriga!",
         vis="Luna com a cabeça e o rabo para fora da areia, olhando para a câmera.",
         loc="Buraco no castelo de areia", sfx="cartoon giggle",
         gag="Luna tenta sair e afunda mais um pouquinho."),
    dict(sid="sc_14", act=2, spk="narrador", av="none",
         text="A Frida colocou torres, pontes e uma janelinha, e o castelo ficou chique de verdade.",
         vis="Castelo de areia com torres e a Frida ao lado, ajeitando uma torre com a pata.",
         loc="Castelo de areia na praia", sfx="cartoon boing",
         gag="A torre mais alta desaba e vira um montinho."),
    dict(sid="sc_15", act=2, spk="narrador", av="none",
         text="Foi aí que a Luna encontrou um tesouro: uma concha rosa que brilhava no meio das pedras.",
         vis="Concha rosa brilhante nas pedras, com Frida e Luna olhando espantadas.",
         loc="Pedras na beira da praia", sfx="cartoon fanfare",
         gag="A concha solta faíscas de luz quando a Luna chega perto."),
    dict(sid="sc_16", act=2, spk="frida", av="frida",
         text="Olha que concha linda! Parece que ela guarda o barulho do mar dentro dela.",
         vis="Frida e Luna com a concha rosa na areia, Frida encostando o ouvido na concha.",
         loc="Areia perto das pedras", sfx="cartoon fanfare",
         gag="Frida faz cara de quem está ouvindo uma orquestra."),
    dict(sid="sc_17", act=2, spk="narrador", av="none",
         text="A Luna provou a concha, fez careta e descobriu que tesouro não tem gosto de biscoito.",
         vis="Luna lambendo a concha rosa com a língua de fora, cara de surpresa.",
         loc="Areia perto das pedras", sfx="cartoon crunch bite",
         gag="Luna cospe e sacode a cabeça toda."),
    dict(sid="sc_18", act=2, spk="narrador", av="none",
         text="De repente, uma sombra grande passou por cima delas e o céu ficou escurinho.",
         vis="Frida e Luna olhando para o céu, uma sombra grande de asas passando sobre a areia.",
         loc="Areia da praia", sfx="cartoon bird whistle",
         gag="As duas se encolhem e olham para cima ao mesmo tempo."),
    dict(sid="sc_19", act=2, spk="narrador", av="none",
         text="Era só o sol se despedindo, pintando o mar de laranja e dourado.",
         vis="Frida apontando para o pôr do sol dourado no mar, Luna sentada ao lado.",
         loc="Beira do mar no fim da tarde", sfx="cartoon fanfare",
         gag="As duas ficam paradas, com o pelo brilhando na luz laranja."),
    dict(sid="sc_20", act=3, spk="luna", av="luna",
         text="O sol tá derretendo no mar! Corre, Frida, senão ele vira geleia de laranja!",
         vis="Luna falando animada ao lado da Frida, o mar dourado atrás.",
         loc="Beira do mar no fim da tarde", sfx="cartoon boing",
         gag="Luna aponta para o sol com a patinha."),
    dict(sid="sc_21", act=3, spk="narrador", av="none",
         text="Mas quem veio mesmo foi a maré, subindo depressa e engolindo a praia inteira.",
         vis="Uma onda grande estourando na areia, espuma subindo perto das duas.",
         loc="Ondas na beira da praia", sfx="cartoon splash",
         gag="A espuma avança e cobre as patinhas."),
    dict(sid="sc_22", act=3, spk="narrador", av="none",
         text="A água invadiu o castelo, levou as torres e deixou todo mundo encharcado.",
         vis="Frida e Luna encharcadas na água rasa, o castelo derretendo atrás delas.",
         loc="Água rasa da praia", sfx="cartoon splash",
         gag="Uma torre do castelo passa flutuando como barquinho."),
    dict(sid="sc_23", act=3, spk="frida", av="frida",
         text="Sai, sai, sai! Sacode essa água antes que eu vire sopa de cachorro!",
         vis="Frida e Luna sacudindo o pelo molhado, gotinhas voando em volta.",
         loc="Areia molhada da praia", sfx="cartoon giggle",
         gag="A água do pelo respinga na cara da Luna."),
    dict(sid="sc_24", act=3, spk="narrador", av="none",
         text="Elas correram para a beirinha, chapinharam água e riram até perder o fôlego.",
         vis="Frida e Luna na beira da água, respingos para cima, as duas sorrindo.",
         loc="Beira do mar", sfx="cartoon run",
         gag="As duas correm em zigue-zague pela areia molhada."),
    dict(sid="sc_25", act=3, spk="narrador", av="none",
         text="Quando o mar ficou calminho, as duas sentaram juntinhas para ver o céu mudar de cor.",
         vis="Frida e Luna sentadas juntinhas na areia, o pôr do sol laranja no mar.",
         loc="Beira do mar ao pôr do sol", sfx="cartoon fanfare",
         gag="As duas se encostam e suspiram ao mesmo tempo."),
    dict(sid="sc_26", act=3, spk="luna", av="luna",
         text="Que gostoso! Cheirinho de mar, de sol e de toalha quentinha!",
         vis="Luna enrolada na toalha colorida, só o focinho para fora, Frida ao lado.",
         loc="Toalha colorida na areia", sfx="cartoon giggle",
         gag="Luna se enrola tanto que vira um burrito de cachorro."),
    dict(sid="sc_27", act=3, spk="narrador", av="none",
         text="A Frida encostou o focinho no focinho da Luna, do jeito que só irmã faz.",
         vis="Frida e Luna com os focinhos encostados na areia, olhos fechados.",
         loc="Areia da praia ao pôr do sol", sfx="cartoon giggle",
         gag="As duas ficam assim por um tempinho, bem quietinhas."),
    dict(sid="sc_28", act=3, spk="frida", av="frida",
         text="Você é a melhor irmãzinha do mundo, mesmo quando cava buracos gigantes!",
         vis="Frida e Luna bem pertinho, focinhos encostados, o sol dourado atrás.",
         loc="Areia da praia ao pôr do sol", sfx="cartoon giggle",
         gag="Luna lambe o focinho da Frida de surpresa."),
    dict(sid="sc_29", act=3, spk="narrador", av="none",
         text="E assim terminou o primeiro dia de praia, com areia em todo lugar e o coração cheio de alegria.",
         vis="Frida e Luna abraçadas na areia ao pôr do sol, o mar calmo atrás.",
         loc="Areia da praia ao pôr do sol", sfx="cartoon fanfare",
         gag="As duas fecham os olhos e aproveitam o último sol."),
    dict(sid="sc_30", act=3, spk="narrador", av="none",
         text="Se você também ama praia, bagunça e cachorrinho, se inscreve no canal e vem com a gente!",
         vis="Frida e Luna se despedem na sala com confete, botão do YouTube e SUBSCRIBE na tela.",
         loc="Sala colorida com confete", sfx="cartoon fanfare",
         gag="As duas acenam para a câmera com confete caindo."),
]

# Uma imagem REAL do pool aprovado para cada cena (nomes = arquivo original).
# Isso mata a repeticao e garante que a imagem mostra o que a narracao conta.
PREFERRED_IMAGES: dict[str, str] = {
    "sc_01": "sc_01_p1.jpg",
    "sc_02": "sc_05_p1.jpg",
    "sc_03": "sc_06_p1.jpg",
    "sc_04": "sc_07_p1.jpg",
    "sc_05": "sc_03_p1.jpg",
    "sc_06": "sc_09_p1.jpg",
    "sc_07": "sc_10_p1.jpg",
    "sc_08": "sc_12_p1.jpg",
    "sc_09": "sc_13_p1.jpg",
    "sc_10": "sc_11_p1.jpg",
    "sc_11": "sc_20_p1.jpg",
    "sc_12": "sc_21_p1.jpg",
    "sc_13": "sc_21_p2.jpg",
    "sc_14": "sc_20_p2.jpg",
    "sc_15": "sc_14_p1.jpg",
    "sc_16": "sc_15_p1.jpg",
    "sc_17": "sc_16_p1.jpg",
    "sc_18": "sc_17_p1.jpg",
    "sc_19": "sc_02_p1.jpg",
    "sc_20": "sc_22_p1.jpg",
    "sc_21": "sc_06_p2.jpg",
    "sc_22": "sc_07_p2.jpg",
    "sc_23": "sc_08_p1.jpg",
    "sc_24": "sc_05_p2.jpg",
    "sc_25": "sc_24_p1.jpg",
    "sc_26": "sc_08_p2.jpg",
    "sc_27": "sc_23_p1.jpg",
    "sc_28": "sc_23_p2.jpg",
    "sc_29": "sc_24_p2.jpg",
}

EMOTION = {
    "narrador": "contando a historia como uma brincadeira, muito alegre, sorridente e saltitante",
    "frida": "alegre, brincalhona e sorridente, como uma cachorrinha crianca",
    "luna": "curiosa, assustada e engracada, como uma salsicha crianca",
}


def build_script() -> dict:
    scenes = []
    for s in SCENES:
        scenes.append({
            "scene_id": s["sid"],
            "act": s["act"],
            "speaker": s["spk"],
            "emotion_direction": EMOTION[s["spk"]],
            "text": s["text"],
            "location": s["loc"],
            "visual_action": s["vis"],
            "sfx": s["sfx"],
            "comedy_beat": s["gag"],
            "avatar_mode": s["av"],
            "avatar_pip": s["av"] != "none",
            "characters": ["Frida", "Luna"],
        })
    return {
        "title": "O PRIMEIRO DIA DE PRAIA DA FRIDA E DA LUNA",
        "thumb_hook": "SALSICHA VS MAR",
        "description": "Frida e Luna descobrem a praia: onda gelada, protetor escorregadio, castelo de areia, concha brilhante e uma maré muito atrevida!",
        "tags": ["frida e luna", "historia infantil", "desenho animado", "primeira vez na praia", "salsicha e buldogue"],
        "target_minutes": 3.5,
        "catchphrase": "Eu virei um fantasminha branco e cheiroso!",
        "secondary_characters": [],
        "story_props": [],
        "scenes": scenes,
    }


def _probe_dur(p: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 2.0


def _concat_xfade(parts: list[Path], out: Path, fade: float = 0.4) -> None:
    cmd = [FFMPEG_EXE, "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", str(p)]
    filters = [f"[{i}:v]fps=30,settb=AVTB,format=yuv420p,setpts=PTS-STARTPTS[s{i}]" for i in range(len(parts))]
    durs = [_probe_dur(p) for p in parts]
    prev, cum = "[s0]", durs[0]
    for i in range(1, len(parts)):
        nxt = "[vout]" if i == len(parts) - 1 else f"[x{i}]"
        filters.append(f"{prev}[s{i}]xfade=transition=fade:duration={fade}:offset={max(0.0, cum - fade):.3f}{nxt}")
        prev = nxt
        cum = cum + durs[i] - fade
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True)


def prepare_project(proj: Path) -> None:
    src = ROOT / "projects" / SRC_SLUG
    for sub in ("assets/images", "assets/audio", "artifacts", "work", "output"):
        (proj / sub).mkdir(parents=True, exist_ok=True)
    vdir = proj / "assets" / "videos"
    vdir.mkdir(parents=True, exist_ok=True)
    for old in vdir.glob("*.mp4"):
        old.unlink()
    # Regra 25: reaproveita TODOS os videos bons; nada de gerar novo.
    for p in sorted((src / "assets" / "videos").glob("*.mp4")):
        if p.stem.startswith("sc_30"):
            continue
        shutil.copy2(p, vdir / p.name)
    print(f"[v7] videos reaproveitados: {len(list(vdir.glob('*.mp4')))}", flush=True)

    # Despedida (Regra 25): usa o video canonico em assets/reference/goodbye/.
    # O audio do clipe NUNCA entra — a narracao ja faz o CTA falado.
    from core.goodbye_video import prepare_goodbye

    bye = prepare_goodbye(proj)
    print(f"[v7] despedida ({bye['source']}, {bye['duration']:.1f}s, audio={bye['audio']}) -> sc_30.mp4", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=("script", "tts", "pacing", "images", "all"))
    ap.add_argument("slug", nargs="?", default="primeiro-dia-de-praia-v7")
    args = ap.parse_args()
    proj = ROOT / "projects" / args.slug
    artifacts = proj / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    prepare_project(proj)
    script = build_script()
    errs = validate_script_schema(script)
    (artifacts / "script_v2.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    words = sum(len(str(s["text"]).split()) for s in script["scenes"])
    narr = sum(1 for s in script["scenes"] if s["speaker"] == "narrador")
    print(f"[v7] roteiro: {len(script['scenes'])} cenas | {words} palavras | {narr} narradas ({narr/len(script['scenes']):.0%})", flush=True)
    if errs:
        for e in errs:
            print("  [SCRIPT-ERR]", e, flush=True)
        return 2
    if args.stage == "script":
        return 0

    timings_path = artifacts / "tts_timings_v2.json"
    if args.stage in ("tts", "all"):
        print("[v7] sintetizando vozes locais (Voice Studio)...", flush=True)
        timings = synthesize_all_scenes(script, proj / "assets" / "audio", provider="voice_studio", force=True)
        timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[v7] {len(timings)} falas | total {sum(float(t['duration']) for t in timings):.1f}s", flush=True)
    else:
        timings = json.loads(timings_path.read_text(encoding="utf-8"))

    if args.stage in ("pacing", "images", "all"):
        videos_dir = proj / "assets" / "videos"
        video_sids = {p.stem.split("_v")[0] for p in videos_dir.glob("*.mp4")}
        pacing, prompts = build_pacing_plan(script, timings, video_scene_ids=video_sids)
        (artifacts / "pacing_plan_v2.json").write_text(json.dumps(pacing, ensure_ascii=False, indent=2), encoding="utf-8")
        (artifacts / "image_prompts_v2.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[v7] pacing: {len(pacing)} clips | {len({c['scene_id'] for c in pacing})} cenas | "
              f"{sum(float(c['duration']) for c in pacing):.1f}s | videos={len(video_sids)}/{TARGET_VEO_VIDEOS}", flush=True)

    if args.stage in ("images", "all"):
        rep = assign_images(proj, json.loads((artifacts / "pacing_plan_v2.json").read_text(encoding="utf-8")),
                            proj / "assets" / "images", preferred=PREFERRED_IMAGES)
        reused = {k: v for k, v in rep["reuse"].items() if len(v) > 1}
        print(f"[v7] imagens: {len(rep['scenes'])} cenas | pool={rep['pool_size']} | reusadas={len(reused)}", flush=True)
        for sha, sids in reused.items():
            print(f"   {sha[:10]}: {sids}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
