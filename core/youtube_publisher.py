# -*- coding: utf-8 -*-
"""Publicador YouTube PT-BR (Todo Publico / selfDeclaredMadeForKids=False) com thumbnail, titulo e descricao virais."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from config import BASE_DIR, THUMB_HEIGHT, THUMB_WIDTH

DEFAULT_CREDENTIALS_DIR = BASE_DIR / ".credentials"
YOUTUBE_SCRIPTS_DIR = Path(r"E:\videos\scripts")
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def resolve_pt_credentials(scripts_dir: Path | None = None) -> tuple[Path, Path]:
    """Localiza client_secret e youtube_token do canal PT prioritariamente em .credentials/ dentro da pasta do motor."""
    search_dirs = [Path(scripts_dir)] if scripts_dir else [DEFAULT_CREDENTIALS_DIR, YOUTUBE_SCRIPTS_DIR]
    for base in search_dirs:
        for cs_name, tk_name in (
            ("client_secret_pt.json", "youtube_token_pt.json"),
            ("client_secret.json", "youtube_token.json"),
        ):
            cs = base / cs_name
            tk = base / tk_name
            if cs.is_file() and tk.is_file():
                return cs, tk
    raise FileNotFoundError(f"Credenciais YouTube PT nao encontradas em {[str(d) for d in search_dirs]}")


def build_viral_pt_title(script_data: dict[str, Any]) -> str:
    """Gera titulo viral para todos os publicos em PT-BR (<= 95 chars, sem restricao kids)."""
    raw = " ".join(str(script_data.get("title") or "E Se os Cachorros Falassem?").split())
    if len(raw) <= 68 and "frida" not in raw.lower():
        cand = f"{raw} A Confusão da Frida e da Luna! 🐶✨"
        if len(cand) <= 95:
            return cand
    return raw[:95]


def build_viral_pt_description(script_data: dict[str, Any]) -> str:
    """Gera descricao completa PT-BR (>= 150 palavras) otimizada para alcance geral, comentarios e busca."""
    title = build_viral_pt_title(script_data)
    story_lines: list[str] = []
    for sc in script_data.get("scenes", [])[:12]:
        txt = re.sub(r"\s+", " ", str(sc.get("text") or "")).strip()
        if txt:
            story_lines.append(txt)
    enredo = " ".join(story_lines[:10])
    if len(enredo) > 1600:
        enredo = enredo[:1600].rsplit(" ", 1)[0].rstrip(" ,.;:") + "..."

    sec_names = [s.get("name") for s in (script_data.get("secondary_characters") or []) if s.get("name")]
    cast_note = (
        f"Além da dupla Frida (a buldogue sensata) e Luna (a salsichinha agitada), esta aventura conta com {', '.join(sec_names)}."
        if sec_names
        else "Acompanhe a dupla mais divertida da pracinha: Frida (a buldogue calma e cheia de bom senso) e Luna (a salsichinha agitada e dramática)!"
    )

    blocks = [
        title,
        (
            "Já imaginou o que o seu cachorro falaria na sua cara se ganhasse voz humana por apenas um dia?! "
            "Prepare-se para rir com essa história cheia de reviravoltas, amizade e confusão!"
        ),
        cast_note,
        enredo,
        "💬 E você: se o seu cachorro pudesse falar por 1 dia, qual seria a PRIMEIRA frase dele? Comenta aqui embaixo!",
        (
            "🤖 Transparência criativa: vídeo gerado com inteligência artificial e ferramentas digitais de animação, "
            "sem humanos no set — feito especialmente para quem ama pets, humor e boas histórias para todas as idades."
        ),
        "Não contém promoção paga — apenas entretenimento e humor pet de verdade.",
        "👍 Curtiu a história da Frida e da Luna? Deixe seu like, se inscreva no canal e compartilhe com quem ama cachorros!",
        (
            "#cachorros #fridaeluna #cachorrofalante #animacao3d #pets #humorpets "
            "#buldogueingles #dachshund #salsichinha #petlovers #historia #conteudocriativo"
        ),
    ]
    return "\n\n".join(b.strip() for b in blocks if b and b.strip())[:4950]


def _load_font(size: int):
    for p in ("C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def generate_viral_pt_thumbnail(
    hero_image: Path,
    out_jpg: Path,
    main_hook: str = "OS CÃES FALARAM?!",
    badge_text: str = "VOCÊ NÃO VAI ACREDITAR!",
) -> Path:
    """Cria thumbnail viral 1280x720 de altissimo contraste para feed geral do YouTube."""
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(hero_image).convert("RGB")
    # Crop levemente fechado no centro para destacar expressoes no feed do celular
    w, h = im.size
    crop_box = (int(w * 0.05), int(h * 0.04), int(w * 0.96), int(h * 0.94))
    im = im.crop(crop_box)
    im = ImageOps.fit(im, (THUMB_WIDTH, THUMB_HEIGHT), method=Image.Resampling.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.36)
    im = ImageEnhance.Contrast(im).enhance(1.22)
    im = ImageEnhance.Sharpness(im).enhance(1.30)

    rgba = im.convert("RGBA")
    grad = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    gd.rectangle([0, int(THUMB_HEIGHT * 0.69), THUMB_WIDTH, THUMB_HEIGHT], fill=(8, 10, 18, 165))
    rgba = Image.alpha_composite(rgba, grad).convert("RGB")
    draw = ImageDraw.Draw(rgba)

    # Selo vermelho viral no canto superior esquerdo
    draw.rounded_rectangle([38, 32, 540, 104], radius=20, fill=(225, 28, 36), outline=(255, 255, 255), width=4)
    f_badge = _load_font(36)
    draw.text((289, 68), badge_text.upper()[:28], font=f_badge, fill=(255, 255, 255), anchor="mm")

    # Texto principal gigante em amarelo dourado com contorno grosso preto
    f_big = _load_font(112)
    hook_txt = " ".join((main_hook or "OS CÃES FALARAM?!").upper().split()[:4])
    cx, cy = THUMB_WIDTH // 2, int(THUMB_HEIGHT * 0.855)
    for dx in range(-7, 8, 2):
        for dy in range(-7, 8, 2):
            draw.text((cx + dx, cy + dy), hook_txt, font=f_big, fill=(10, 8, 5), anchor="mm")
    draw.text((cx, cy), hook_txt, font=f_big, fill=(255, 226, 48), anchor="mm")

    # Borda dourada sutil de destaque no feed
    draw.rectangle([0, 0, THUMB_WIDTH - 1, THUMB_HEIGHT - 1], outline=(255, 212, 50), width=10)
    rgba.save(out_jpg, format="JPEG", quality=94)
    return out_jpg


def publish_episode_youtube_pt(
    proj_dir: Path,
    script_data: dict[str, Any],
    video_mp4: Path,
    srt_path: Path | None = None,
    hero_image: Path | None = None,
    privacy: str = "public",
    scripts_dir: Path | None = None,
    title_override: str = "",
    description_override: str = "",
    badge_text: str = "VOCÊ NÃO VAI ACREDITAR!",
) -> dict[str, Any]:
    """Publica o episodio no canal YouTube PT-BR com selfDeclaredMadeForKids=False (todo publico)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not video_mp4.is_file():
        raise FileNotFoundError(f"Video MP4 nao encontrado: {video_mp4}")

    cs_path, tk_path = resolve_pt_credentials(scripts_dir)
    creds = Credentials.from_authorized_user_file(str(tk_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tk_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(cs_path), SCOPES)
            creds = flow.run_local_server(port=0)
            tk_path.write_text(creds.to_json(), encoding="utf-8")

    service = build("youtube", "v3", credentials=creds)

    title = (title_override or "").strip() or build_viral_pt_title(script_data)
    description = (description_override or "").strip() or build_viral_pt_description(script_data)
    tags = [
        "cachorros", "frida e luna", "cachorros falantes", "animacao 3d", "humor pet",
        "buldogue ingles", "dachshund", "salsichinha", "pets", "familia", "comedia",
    ]
    for extra in script_data.get("tags") or []:
        t = str(extra).strip()
        if t and t.lower() not in {x.lower() for x in tags} and "infantil" not in t.lower():
            tags.append(t)

    # Thumbnail viral dedicada
    thumbs_dir = proj_dir / "output" / "thumbs"
    if hero_image is None or not hero_image.is_file():
        hero_image = proj_dir / "assets" / "images" / "sc_01_p1.jpg"
    viral_thumb = thumbs_dir / "thumb_viral_pt.jpg"
    if hero_image.is_file():
        generate_viral_pt_thumbnail(
            hero_image,
            viral_thumb,
            main_hook=script_data.get("thumb_hook") or "ELAS FALARAM?!",
            badge_text=badge_text or "VOCÊ NÃO VAI ACREDITAR!",
        )

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:25],
            "categoryId": "24",
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus": privacy,
            # Regra obrigatoria: NAO marcar para criancas, manter alcance para todo mundo
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_mp4), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    last_pct = -1
    while response is None:
        st, response = req.next_chunk()
        if st:
            pct = int(st.progress() * 100)
            if pct != last_pct and pct % 10 == 0:
                print(f"  [YouTube PT] Upload {pct}%", flush=True)
                last_pct = pct

    vid = response["id"]
    print(f"  [YouTube PT] Video publicado ({privacy}, MadeForKids=False): https://youtu.be/{vid}", flush=True)

    thumb_ok = False
    if viral_thumb.is_file():
        try:
            service.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(viral_thumb))).execute()
            thumb_ok = True
            print(f"  [YouTube PT] Thumbnail viral enviada: {viral_thumb.name}", flush=True)
        except HttpError as exc:
            print(f"  [YouTube PT] Aviso thumbnail ({exc.resp.status}): {exc}", flush=True)

    caption_id = ""
    if srt_path and srt_path.is_file():
        try:
            cap_body = {
                "snippet": {
                    "videoId": vid,
                    "language": "pt-BR",
                    "name": "Português (Brasil)",
                    "isDraft": False,
                }
            }
            cap_resp = service.captions().insert(
                part="snippet",
                body=cap_body,
                media_body=MediaFileUpload(str(srt_path), mimetype="text/caption", resumable=True),
            ).execute()
            caption_id = cap_resp.get("id", "")
            print(f"  [YouTube PT] Legenda PT-BR enviada (id={caption_id})", flush=True)
        except HttpError as exc:
            print(f"  [YouTube PT] Aviso legenda: {exc}", flush=True)

    receipt = {
        "video_id": vid,
        "url": f"https://youtu.be/{vid}",
        "studio_url": f"https://studio.youtube.com/video/{vid}/edit",
        "title": title,
        "description": description,
        "privacy": privacy,
        "selfDeclaredMadeForKids": False,
        "thumbnail": str(viral_thumb) if viral_thumb.is_file() else "",
        "thumbnail_uploaded": thumb_ok,
        "caption_id": caption_id,
        "published_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    art_dir = proj_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "youtube_publish_pt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def build_short_pt_metadata(
    script_data: dict[str, Any],
    short_variant: str,
    main_video_url: str = "",
) -> tuple[str, str, list[str]]:
    """Constroi titulo, descricao e tags virais PT-BR para cada Short (todo publico, com link do episodio)."""
    base_title = " ".join(str(script_data.get("title") or "Frida e Luna").split())
    hook = " ".join(str(script_data.get("thumb_hook") or "ELAS FALARAM?!").split())
    v = short_variant.lower()

    if "hook" in v or "01" in v:
        title = f"{hook} {base_title} 🐶😱 #Shorts"
        lead = (
            "Imagina acordar na pracinha e ouvir sua cachorrinha falando igual gente?! 😱🐶 "
            "Olha a reação impagável da Frida e da Luna!"
        )
        cta_q = "💬 Se o seu cachorro falasse por 1 dia, qual seria a primeira coisa que ele pediria? Comenta aqui!"
    elif "storybook" in v or "02" in v:
        title = f"Capítulo Secreto: A Confusão da Frida e da Luna! 😂🐶 #Shorts"
        lead = (
            "A Luninha tentou dar ordens no parque inteiro e acabou arrumando a maior confusão! 😂🐾 "
            "Será que a Frida vai conseguir salvar o plano?"
        )
        cta_q = "💬 Você é mais calmo igual a Frida ou agitado igual a Luna? Conta nos comentários!"
    else:
        title = f"O Final Mais Fofo da Frida e da Luna! 🥹✨ #Shorts"
        lead = (
            "No último segundo da magia, a Frida e a Luna descobriram a lição mais linda de todas! 🥹💛 "
            "Assista até o final!"
        )
        cta_q = "💬 O que você achou desse final? Deixe seu like e comenta qual aventura você quer ver amanhã!"

    if len(title) > 98:
        title = title[:89].rstrip(" -:|") + " #Shorts"

    link_block = (
        f"🎬 ASSISTA O EPISÓDIO COMPLETO AQUI: {main_video_url}\n"
        "👉 Clique também no vídeo relacionado aqui no Short para ver a história inteira!"
        if main_video_url
        else "🎬 Assista o episódio completo no nosso canal e se inscreva para novas histórias da Frida e da Luna!"
    )

    description = "\n\n".join([
        lead,
        link_block,
        cta_q,
        (
            "🤖 Transparência criativa: animação digital feita com inteligência artificial para quem ama pets, "
            "humor e histórias divertidas para todas as idades."
        ),
        "#Shorts #cachorros #fridaeluna #cachorrofalante #pets #humorpets #animacao3d #buldogueingles #dachshund #salsichinha",
    ])[:4950]

    tags = [
        "shorts", "cachorros", "frida e luna", "cachorro falante", "pets", "humor pet",
        "animacao 3d", "buldogue ingles", "dachshund", "salsichinha", "historia", "familia",
    ]
    return title, description, tags


def publish_shorts_pack_youtube_pt(
    proj_dir: Path,
    script_data: dict[str, Any],
    shorts_paths: list[Path],
    privacy: str = "public",
    scripts_dir: Path | None = None,
    main_video_url: str = "",
) -> list[dict[str, Any]]:
    """Publica os 3 Shorts 9:16 no canal YouTube PT-BR (selfDeclaredMadeForKids=False / Todo Publico)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    art_dir = proj_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    if not main_video_url:
        main_rec_p = art_dir / "youtube_publish_pt.json"
        if main_rec_p.is_file():
            try:
                main_video_url = str(json.loads(main_rec_p.read_text(encoding="utf-8")).get("url") or "")
            except Exception:
                main_video_url = ""

    cs_path, tk_path = resolve_pt_credentials(scripts_dir)
    creds = Credentials.from_authorized_user_file(str(tk_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tk_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(cs_path), SCOPES)
            creds = flow.run_local_server(port=0)
            tk_path.write_text(creds.to_json(), encoding="utf-8")

    service = build("youtube", "v3", credentials=creds)
    receipts: list[dict[str, Any]] = []

    for sp in shorts_paths:
        if not sp.is_file():
            raise FileNotFoundError(f"Short MP4 nao encontrado: {sp}")
        title, description, tags = build_short_pt_metadata(script_data, sp.stem, main_video_url=main_video_url)
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:25],
                "categoryId": "24",
                "defaultLanguage": "pt-BR",
                "defaultAudioLanguage": "pt-BR",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(str(sp), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
        req = service.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            st_up, response = req.next_chunk()
            if st_up:
                print(f"  [YouTube PT Short {sp.name}] Upload {int(st_up.progress() * 100)}%", flush=True)

        vid = response["id"]
        short_url = f"https://youtube.com/shorts/{vid}"
        print(f"  [YouTube PT Short] Publicado ({privacy}, MadeForKids=False): {short_url}", flush=True)
        receipts.append({
            "file": sp.name,
            "video_id": vid,
            "url": short_url,
            "watch_url": f"https://youtu.be/{vid}",
            "studio_url": f"https://studio.youtube.com/video/{vid}/edit",
            "title": title,
            "description": description,
            "privacy": privacy,
            "selfDeclaredMadeForKids": False,
            "main_video_url": main_video_url,
            "published_at": dt.datetime.now().isoformat(timespec="seconds"),
        })

    (art_dir / "youtube_shorts_publish_pt.json").write_text(
        json.dumps(receipts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return receipts
