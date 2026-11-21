# MANUAL — amostra_estilos_luna.py
# Renderiza a luna-base (dachshund aprovada) em 2 estilos, fundo transparente:
# 1. GLOSSY PIXAR (luz de estudo suave, coat alto)
# 2. CEL/CARTOON (luz dura frontal, quase sem sombra gradual)
# Uso: D:/Blender/blender.exe -b -P amostra_estilos_luna.py -- --gltf <arquivo> --prefixo <nome>
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
gltf = argv[argv.index("--gltf") + 1]
prefixo = argv[argv.index("--prefixo") + 1] if "--prefixo" in argv else "amostra"

def montar_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=gltf)
    malhas = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in malhas:
        o.select_set(True)
    bpy.context.view_layer.objects.active = malhas[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    pontos = [o.matrix_world @ Vector(c) for o in malhas for c in o.bound_box]
    minv = Vector((min(p.x for p in pontos), min(p.y for p in pontos), min(p.z for p in pontos)))
    maxv = Vector((max(p.x for p in pontos), max(p.y for p in pontos), max(p.z for p in pontos)))
    centro = (minv + maxv) / 2
    fator = 3.0 / max(maxv - minv)
    for o in malhas:
        o.scale = (fator, fator, fator)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(scale=True)
    return malhas, centro * fator

malhas, centro = montar_cena()

# 1. GLOSSY
bpy.ops.object.light_add(type='AREA', location=(4, 3, 6)); bpy.context.active_object.data.energy = 900
bpy.ops.object.light_add(type='AREA', location=(-4, -2, 3)); bpy.context.active_object.data.energy = 400
bpy.ops.object.light_add(type='AREA', location=(0, -6, 1.5)); bpy.context.active_object.data.energy = 600
bpy.ops.object.camera_add(location=(centro.x + 3.4, centro.y - 4.4, centro.z + 1.6))
cam = bpy.context.active_object
bpy.ops.object.empty_add(location=centro)
alvo = bpy.context.active_object
t = cam.constraints.new(type="TRACK_TO"); t.target = alvo; t.track_axis = "TRACK_NEGATIVE_Z"; t.up_axis = "UP_Y"
scene = bpy.context.scene
scene.camera = cam
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.4, 0.42, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.render.engine = 'BLENDER_EEVEE'
scene.render.film_transparent = True
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.eevee.taa_samples = 48
scene.render.filepath = f"D:/CRAFT/video-orquestracao/public/assets/historinha-luninha-e-fridoca/estilos/{prefixo}-glossy.png"
bpy.ops.render.render(write_still=True)
print("ESTILO_GLOSSY_OK")

# 2. CEL: luz frontal dura, mata as sombras graduais (olha cartoon 2D com fundo 3D)
for luz in [o for o in scene.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(luz, do_unlink=True)
bpy.ops.object.light_add(type='SUN', location=(0, -5, 6))
sol = bpy.context.active_object
sol.data.energy = 4.0
sol.rotation_euler = (0.9, 0, 0)
world.node_tree.nodes["Background"].inputs[1].default_value = 2.2
scene.render.filepath = f"D:/CRAFT/video-orquestracao/public/assets/historinha-luninha-e-fridoca/estilos/{prefixo}-cel.png"
bpy.ops.render.render(write_still=True)
print("ESTILO_CEL_OK")
