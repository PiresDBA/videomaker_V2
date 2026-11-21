# MANUAL — recolore_luna_texturas.py v2
# Corpo MARROM-ESCURO (#3E2A24) nas texturas .001; pontos TAN (#C89A6B) nas demais.
# Luminancia NORMALIZADA (min/max da imagem) para o sombreado sobreviver.
import shutil, os
from PIL import Image

RAIZ = "D:/CRAFT/video-orquestracao/public/assets/historinha-luninha-e-fridoca/modelos-3d-sketchfab"
ORIGEM = f"{RAIZ}/dachshund"
DESTINO = f"{RAIZ}/luna-base"

if os.path.exists(DESTINO):
    shutil.rmtree(DESTINO)
shutil.copytree(ORIGEM, DESTINO)

MARROM = (0.36, 0.227, 0.13)     # #5C3A21 chocolate legivel
TAN = (0.784, 0.604, 0.42)       # #C89A6B

def tingir(caminho_png, cor):
    img = Image.open(caminho_png).convert("RGB")
    px = img.load()
    w, h = img.size
    lums = []
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lums.append((r * 299 + g * 587 + b * 114) / 1000)
    lum_min, lum_max = min(lums), max(lums)
    alcance = max(1.0, lum_max - lum_min)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lum = (r * 299 + g * 587 + b * 114) / 1000
            fator = (lum - lum_min) / alcance          # 0..1 com o sombreado original
            piso = 0.55 if cor == MARROM else 0.45
            fator = piso + (1 - piso) * fator          # corpo escuro, tan claro
            px[x, y] = (int(min(255, cor[0] * 255 * fator)),
                        int(min(255, cor[1] * 255 * fator)),
                        int(min(255, cor[2] * 255 * fator)))
    img.save(caminho_png)
    print("tingida:", os.path.basename(caminho_png), "->", "MARROM" if cor == MARROM else "TAN")

pasta = f"{DESTINO}/textures"
for nome in os.listdir(pasta):
    if "baseColor" in nome:
        cor = TAN if ".001_" in nome else MARROM
        tingir(os.path.join(pasta, nome), cor)

print("OK", DESTINO)
