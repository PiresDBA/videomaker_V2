# MANUAL — previa_modelo_sketchfab.py (v2)
# Renderiza um glTF do Sketchfab com enquadramento automatico (bbox real).
# Uso: D:/Blender/blender.exe -b -P previa_modelo_sketchfab.py -- --gltf <arquivo> --saida <png>
import bpy, sys, math

argv = sys.argv[sys.argv.index("--") + 1:]
gltf = argv[argv.index("--gltf") + 1]
saida = argv[argv.index("--saida") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=gltf)

# so malhas (remove lixo como icospheres de cena)
malhas = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print("MALHAS:", len(malhas))
bpy.ops.object.select_all(action="DESELECT")
for o in malhas:
    o.select_set(True)
bpy.context.view_layer.objects.active = malhas[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# bounding box combinada
from mathutils import Vector
pontos = []
for o in malhas:
    for c in o.bound_box:
        pontos.append(o.matrix_world @ Vector(c))
minv = Vector((min(p.x for p in pontos), min(p.y for p in pontos), min(p.z for p in pontos)))
maxv = Vector((max(p.x for p in pontos), max(p.y for p in pontos), max(p.z for p in pontos)))
centro = (minv + maxv) / 2
maior = max(maxv - minv)
fator = 3.0 / maior
for o in malhas:
    o.scale = (fator, fator, fator)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(scale=True)
centro *= fator

# luzes de estudo
bpy.ops.object.light_add(type='AREA', location=(4, 3, 6)); bpy.context.active_object.data.energy = 900
bpy.ops.object.light_add(type='AREA', location=(-4, -2, 3)); bpy.context.active_object.data.energy = 400
bpy.ops.object.light_add(type='AREA', location=(0, -6, 1.5)); bpy.context.active_object.data.energy = 600

# camera apontada para o centro
bpy.ops.object.camera_add(location=(centro.x + 3.4, centro.y - 4.4, centro.z + 1.6))
cam = bpy.context.active_object
track = cam.constraints.new(type="TRACK_TO")
bpy.ops.object.empty_add(location=centro)
alvo = bpy.context.active_object
track.target = alvo
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
bpy.context.scene.camera = cam

scene = bpy.context.scene
world = bpy.data.worlds.new("mundo-claro")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.4, 0.42, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.eevee.taa_samples = 48
scene.render.film_transparent = False
scene.render.filepath = saida
bpy.ops.render.render(write_still=True)
print("PREVIA_OK", saida)
