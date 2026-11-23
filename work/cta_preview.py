import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
ff = str(Path('bin/ffmpeg.exe').resolve())
mov = str(Path('work/cta_teste.mov').resolve())
d = Path('work/cta_frames')
d.mkdir(exist_ok=True)
for t in (0.3, 0.9, 1.5, 2.1, 2.7):
    subprocess.run([ff, '-y', '-v', 'error', '-ss', str(t), '-i', mov,
                    '-frames:v', '1', str(d / f'f_{t}.png')], check=True)
# composite on blue to see alpha
files = sorted(d.glob('f_*.png'))
tw, th = 480, 270
sheet = Image.new('RGB', (tw * len(files), th + 24), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGBA')
    bg = Image.new('RGBA', im.size, (60, 130, 200, 255))
    bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB').resize((tw, th)), (i * tw, 0))
    dr.text((i * tw + 6, th + 4), f.stem, fill=(255, 255, 255))
out = d / 'contato.jpg'
sheet.save(out, quality=92)
print(out)
