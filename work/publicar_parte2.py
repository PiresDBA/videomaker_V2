import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.youtube_publisher import publish_episode_youtube_pt  # noqa: E402

PROJ = ROOT / 'projects' / 'primeiro-dia-de-praia-parte2'
script = json.loads((PROJ / 'artifacts' / 'script_v2.json').read_text(encoding='utf-8'))
video = PROJ / 'output' / 'primeiro-dia-de-praia-parte2_16x9.mp4'
srt = PROJ / 'output' / 'primeiro-dia-de-praia-parte2.srt'
hero = PROJ / 'output' / 'thumbs' / 'thumb_B_hook.jpg'

rec = publish_episode_youtube_pt(
    proj_dir=PROJ,
    script_data=script,
    video_mp4=video,
    srt_path=srt if srt.exists() else None,
    hero_image=hero if hero.exists() else None,
    privacy='public',
    badge_text='A GAIVOTA ROUBOU O BISCOITO!',
)
print('PUBLICADO:', rec.get('url'))
print(json.dumps(rec, ensure_ascii=False, indent=2))
