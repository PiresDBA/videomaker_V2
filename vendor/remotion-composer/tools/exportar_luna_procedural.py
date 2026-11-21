# MANUAL — exportar_luna_procedural.py
# Roda o modelo procedural da Luna (modelar_luna_3d.py) e exporta como GLTF
# para as amostras de estilo, sem novo download do Sketchfab.
import bpy, sys

# executa o construtor (ele termina com um render; interceptamos trocando a saida)
sys.argv = ["blender", "--", "--saida", "C:/Users/Pires/AppData/Local/Temp/opencode/luna-proc-dummy.png", "--vista", "frente"]
src = open("D:/CRAFT/OpenMontage/remotion-composer/tools/modelar_luna_3d.py", encoding="utf-8").read()
src = src.replace("bpy.ops.render.render(write_still=True)", "pass  # render pulado no export")
exec(src)

bpy.ops.export_scene.gltf(filepath="D:/CRAFT/video-orquestracao/public/assets/historinha-luninha-e-fridoca/estilos/luna-procedural.gltf", export_format="GLTF_SEPARATE")
print("EXPORT_OK")
