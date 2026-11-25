# -*- coding: utf-8 -*-
"""Corrige o metadata da voz da cena final e reexecuta a auditoria sem remontar."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.self_audit import run_final_audit  # noqa: E402

PROJ = ROOT / 'projects' / 'primeiro-dia-de-praia-parte2'
ART = PROJ / 'artifacts'
tp = ART / 'tts_timings_v2.json'
timings = json.loads(tp.read_text(encoding='utf-8'))
for t in timings:
    if t['scene_id'] == 'sc_30':
        t['voice'] = 'voice_studio:Simone-feliz'
        t['emotion_mode'] = 'voice_studio'
        print('voz da sc_30 corrigida para', t['voice'])
tp.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding='utf-8')

script = json.loads((ART / 'script_v2.json').read_text(encoding='utf-8'))
clips = json.loads((ART / 'pacing_plan_v2.json').read_text(encoding='utf-8'))
audit = run_final_audit(
    proj_dir=PROJ,
    script_data=script,
    tts_timings=timings,
    visual_clips=clips,
    images_dir=PROJ / 'assets' / 'images',
    out_16_9=PROJ / 'output' / f'{PROJ.name}_16x9.mp4',
    out_short=None,
    thumbs_dir=PROJ / 'output' / 'thumbs',
    vision_check=False,
    min_veo_videos=0,
)
print(f'Auditoria: APPROVED={audit["approved"]} | Issues={audit["issues_count"]}')
for i in audit['issues']:
    print('  -', i)
sys.exit(0 if audit['approved'] else 2)
