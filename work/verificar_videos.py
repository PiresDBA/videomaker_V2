import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'selecao_continuacao'
ffprobe = str(Path(FFMPEG_EXE).with_name('ffprobe.exe'))
items = json.loads((OUT / 'dados.json').read_text(encoding='utf-8'))
beach = [x for x in items if x['category'] == 'praia' and x['kind'] == 'video']
print('total videos praia:', len(beach))
bad = []
for x in beach:
    p = Path(x['path'])
    r = subprocess.run([ffprobe, '-v', 'error', '-show_entries',
                        'format=duration:stream=codec_name,width,height',
                        '-of', 'json', str(p)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout or '{}')
        dur = float(d.get('format', {}).get('duration', 0) or 0)
        streams = d.get('streams', [])
        ok = bool(streams) and dur > 1.0
    except Exception:
        dur, ok = 0, False
    if not ok:
        bad.append(x['name'])
    print(('OK ' if ok else 'BAD'), f'{dur:5.2f}s', x['name'])
print('\nDEFEITOS:', len(bad))
for n in bad:
    print(' ', n)
