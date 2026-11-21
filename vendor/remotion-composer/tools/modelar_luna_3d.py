# MANUAL — modelar_luna_3d.py
# ============================
# O que faz
# ---------
# Luna 3D estilizada alvo "Pixel Disney" (frame-060s do video original):
# dachshund marrom-escuro com pontos tan (focinho, sobrancelhas, patas),
# orelhas grandes ERGUIDAS, focinho comprido, corrente dourada, rabo longo
# com ponta clara. Volume glossy, contorno limpo, anatomia completa.
#
# Como rodar
# ----------
#   D:/Blender/blender.exe -b -P modelar_luna_3d.py -- --saida luna3d.png --vista frente
#   (vistas: frente | perfil)
import bpy, sys, math

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
saida = argv[argv.index("--saida") + 1] if "--saida" in argv else "luna3d.png"
vista = argv[argv.index("--vista") + 1] if "--vista" in argv else "frente"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# cores da referencia
MARRON_ESCURO = (0.11, 0.06, 0.035, 1.0)
TAN = (0.62, 0.36, 0.16, 1.0)
CREME = (0.9, 0.85, 0.75, 1.0)
DOURADO = (0.95, 0.72, 0.2, 1.0)

def material(nome, cor, rugosidade=0.42, metalico=0.0):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = cor
    bsdf.inputs["Roughness"].default_value = rugosidade
    bsdf.inputs["Coat Weight"].default_value = 0.3
    bsdf.inputs["Metallic"].default_value = metalico
    return mat

mat_corpo = material("corpo", MARRON_ESCURO, 0.5)
mat_tan = material("tan", TAN, 0.5)
mat_creme = material("creme", CREME, 0.5)
mat_ouro = material("ouro", DOURADO, 0.25, 1.0)
mat_olho_branco = material("olho-branco", (1, 1, 1, 1), 0.08)
mat_iris = material("iris", (0.35, 0.2, 0.08, 1.0), 0.1)
mat_pupila = material("pupila", (0.02, 0.01, 0.01, 1.0), 0.05)
mat_nariz = material("nariz", (0.03, 0.02, 0.02, 1.0), 0.15)
mat_lingua = material("lingua", (0.75, 0.25, 0.22, 1.0), 0.4)

def esfera(nome, loc, escala, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=loc, segments=48, ring_count=32)
    obj = bpy.context.active_object
    obj.name = nome
    obj.scale = escala
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj

# --- corpo: salsicha elegante, levemente arqueada ---
esfera("corpo-tronco", (0, 0, 1.05), (1.05, 0.42, 0.4), mat_corpo)
esfera("corpo-peito", (0.62, 0, 0.98), (0.52, 0.4, 0.42), mat_corpo)
esfera("corpo-garupa", (-0.85, 0, 1.0), (0.5, 0.42, 0.42), mat_corpo)
# peito tan (pontos tan da referencia)
esfera("peito-tan", (0.75, 0, 0.9), (0.28, 0.34, 0.36), mat_tan)

# --- pescoco integrado (parado ereto na frente) ---
esfera("pescoco", (1.05, 0, 1.4), (0.24, 0.24, 0.34), mat_corpo)

# --- cabeca: cranio + focinho comprido de dachshund ---
esfera("cabeca", (1.2, 0, 1.8), (0.28, 0.26, 0.26), mat_corpo)
# focinho: capsula alongada para frente com ponta tan
esfera("focinho-base", (1.42, 0, 1.74), (0.14, 0.13, 0.13), mat_corpo)
esfera("ponte-nasal", (1.5, 0, 1.76), (0.11, 0.1, 0.1), mat_corpo)
esfera("focinho-tan", (1.56, 0, 1.72), (0.12, 0.11, 0.1), mat_tan)
esfera("nariz", (1.66, 0, 1.76), (0.055, 0.05, 0.045), mat_nariz)
# sorriso com lingua
esfera("lingua", (1.58, 0, 1.6), (0.05, 0.045, 0.02), mat_lingua)

# olhos grandes com iris e brilho (os dois, 3/4)
for lado in (1, -1):
    esfera(f"patch-tan-olho-{lado}", (1.34, lado * 0.13, 1.9), (0.095, 0.085, 0.075), mat_corpo)
    esfera(f"olho-branco-{lado}", (1.39, lado * 0.15, 1.9), (0.068, 0.068, 0.068), mat_olho_branco)
    esfera(f"iris-{lado}", (1.41, lado * 0.175, 1.9), (0.045, 0.045, 0.05), mat_iris)
    esfera(f"pupila-{lado}", (1.425, lado * 0.18, 1.9), (0.024, 0.024, 0.028), mat_pupila)
    esfera(f"brilho-{lado}", (1.445, lado * 0.195, 1.94), (0.012, 0.012, 0.012), mat_olho_branco)
    # pontos tan de sobrancelha
    esfera(f"sobrancelha-tan-{lado}", (1.3, lado * 0.16, 2.06), (0.045, 0.04, 0.02), mat_tan)

# --- orelhas GRANDES ERGUIDAS (assinatura da referencia) ---
for lado, nome in ((1, "dir"), (-1, "esq")):
    orelha = esfera(f"orelha-{nome}", (1.08, lado * 0.2, 2.16), (0.13, 0.06, 0.22), mat_corpo)
    orelha.rotation_euler = (0, 0, lado * 0.35)
    esfera(f"orelha-interna-{nome}", (1.08, lado * 0.2, 2.16), (0.075, 0.03, 0.13), mat_tan)
    orelha2 = esfera(f"orelha-ponta-{nome}", (1.02, lado * 0.26, 2.36), (0.1, 0.05, 0.12), mat_corpo)
    orelha2.rotation_euler = (0, 0, lado * 0.5)

# --- corrente dourada no pescoco ---
bpy.ops.mesh.primitive_torus_add(major_radius=0.24, minor_radius=0.035, location=(1.05, 0, 1.5), rotation=(math.pi / 2, 0.15, 0), major_segments=24, minor_segments=10)
corrente = bpy.context.active_object
corrente.data.materials.append(mat_ouro)
# pingente
esfera("pingente", (1.05, 0, 1.26), (0.055, 0.055, 0.055), mat_ouro)

# --- patas: tan do joelho para baixo, com pes ---
for ix, x in enumerate((0.72, 0.38, -0.5, -0.85)):
    for lado in (1, -1):
        esfera(f"coxa-{ix}{lado}", (x, lado * 0.28, 0.62), (0.13, 0.13, 0.2), mat_corpo)
        esfera(f"pata-tan-{ix}{lado}", (x + 0.03, lado * 0.3, 0.3), (0.1, 0.1, 0.22), mat_tan)
        esfera(f"pe-{ix}{lado}", (x + 0.06, lado * 0.3, 0.09), (0.11, 0.1, 0.06), mat_tan)

# --- rabo longo curvado para cima, ponta creme ---
bpy.ops.curve.primitive_bezier_curve_add(location=(-0.85, 0, 1.1))
rabo = bpy.context.active_object
pts = rabo.data.splines[0].bezier_points
pts[0].co = (-0.85, 0, 1.1); pts[0].handle_right = (-1.3, 0, 1.45)
pts[1].co = (-1.75, 0, 1.95); pts[1].handle_left = (-1.65, 0, 1.6); pts[1].handle_right = (-2.1, 0, 2.1)
pts.add(1)
pts[2].co = (-2.3, 0, 2.5); pts[2].handle_left = (-2.2, 0, 2.3)
bpy.ops.object.shade_smooth()
rabo.data.bevel_depth = 0.095
rabo.data.bevel_resolution = 8
rabo.data.materials.append(mat_corpo)
# ponta creme
esfera("rabo-ponta", (-2.3, 0, 2.48), (0.08, 0.08, 0.08), mat_creme)

# --- luzes de estudio suaves ---
bpy.ops.object.light_add(type='AREA', location=(3, 4, 6)); k = bpy.context.active_object
k.data.energy = 900; k.data.size = 6
bpy.ops.object.light_add(type='AREA', location=(-4, -2, 3)); f = bpy.context.active_object
f.data.energy = 350; f.data.size = 8
bpy.ops.object.light_add(type='AREA', location=(0, -5, 2)); r = bpy.context.active_object
r.data.energy = 500; r.data.size = 5; r.rotation_euler = (1.2, 0, -1.4)

# --- camera ---
if vista == "perfil":
    bpy.ops.object.camera_add(location=(-0.6, -8.0, 2.2), rotation=(1.42, 0, 0.12))
else:
    bpy.ops.object.camera_add(location=(4.6, -5.4, 2.6), rotation=(1.28, 0, 0.7))
scene.camera = bpy.context.active_object

scene.render.engine = 'BLENDER_EEVEE'
scene.render.film_transparent = True
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.eevee.taa_samples = 64
scene.render.filepath = saida
bpy.ops.render.render(write_still=True)
print("LUNA_3D_OK", saida)
