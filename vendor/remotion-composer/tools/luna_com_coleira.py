# MANUAL — luna_com_coleira.py
# Carrega luna-base, adiciona a corrente dourada da ficha no pescoco e renderiza
# previa + versao LADO A LADO com o frame original para a critica visual.
# Uso: D:/Blender/blender.exe -b -P luna_com_coleira.py -- --saida <png>
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
saida = argv[argv.index("--saida") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="D:/CRAFT/video-orquestracao/public/assets/historinha-luninha-e-fridoca/modelos-3d-sketchfab/luna-base/scene.gltf")
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
maior = max(maxv - minv)
fator = 3.0 / maior
for o in malhas:
    o.scale = (fator, fator, fator)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(scale=True)
centro *= fator
print("BBOX altura", maior, "centro", tuple(round(v, 2) for v in centro))

# corrente dourada: o cao esta de pe; o pescoco fica no quartel frontal superior
# (a dachshund olha para -y no arquivo... ajusto pelo eixo mais curto: frente = menor extensao)
ext = maxv - minv
# frente = eixo com menor extensao entre x e y (profundidade do corpo)
eixo_frente = "x" if ext.x < ext.y else "y"
sinal = -1.0
pos_frente = minv.x if eixo_frente == "x" else minv.y
z_pescoco = maxv.z - (maxv.z - minv.z) * 0.18
if eixo_frente == "x":
    loc_corrente = (pos_frente + sinal * 0.25, centro.y, z_pescoco)
else:
    loc_corrente = (centro.x, pos_frente + sinal * 0.25, z_pescoco)
rot = (0, 0, 0)
raio = 0.3
bpy.ops.mesh.primitive_torus_add(major_radius=raio, minor_radius=0.03, location=loc_corrente, rotation=rot, major_segments=32, minor_segments=8)
corrente = bpy.context.active_object
mat = bpy.data.materials.new("ouro")
mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.95, 0.72, 0.2, 1.0)
b.inputs["Metallic"].default_value = 1.0
b.inputs["Roughness"].default_value = 0.25
corrente.data.materials.append(mat)

# luzes
bpy.ops.object.light_add(type='AREA', location=(4, 3, 6)); bpy.context.active_object.data.energy = 900
bpy.ops.object.light_add(type='AREA', location=(-4, -2, 3)); bpy.context.active_object.data.energy = 400
bpy.ops.object.light_add(type='AREA', location=(0, -6, 1.5)); bpy.context.active_object.data.energy = 600

bpy.ops.object.camera_add(location=(centro.x + 3.4, centro.y - 4.4, centro.z + 1.6))
cam = bpy.context.active_object
bpy.ops.object.empty_add(location=centro)
alvo = bpy.context.active_object
t = cam.constraints.new(type="TRACK_TO"); t.target = alvo; t.track_axis = "TRACK_NEGATIVE_Z"; t.up_axis = "UP_Y"
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("mundo-claro")
scene = bpy.context.scene
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.4, 0.42, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.eevee.taa_samples = 48
scene.render.filepath = saida
bpy.ops.render.render(write_still=True)
print("LUNA_COLEIRA_OK", saida)
