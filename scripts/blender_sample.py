import bpy, math
from mathutils import Vector

# Clean scene
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def mat(name, color, metallic=0.0, rough=.45, emission=None):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Metallic'].default_value=metallic; bs.inputs['Roughness'].default_value=rough
    if emission:
        bs.inputs['Emission Color'].default_value=(*emission,1); bs.inputs['Emission Strength'].default_value=3.0
    return m

def cube(name, loc, scale, material, bevel=.06):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('soft edges','BEVEL'); mod.width=bevel; mod.segments=2
    o.data.materials.append(material); return o

def human(name, x,y, shirt, phase=0):
    skin=mat(name+'skin',(0.35,0.16,0.09),rough=.65); cloth=mat(name+'cloth',shirt,rough=.7); dark=mat(name+'pants',(0.025,0.03,0.04),rough=.8)
    cube(name+'torso',(x,y,1.45),(.28,.18,.48),cloth,.12)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=(x,y,2.08)); bpy.context.object.scale=(.22,.22,.27); bpy.context.object.data.materials.append(skin)
    for dx in (-.13,.13): cube(name+'leg',(x+dx,y,0.62),(.09,.1,.48),dark,.05)
    # subtle browsing arm motion
    arm=cube(name+'arm',(x+.34,y,1.55),(.08,.08,.38),skin,.05); arm.rotation_euler[1]=math.radians(-25)
    arm.rotation_euler.keyframe_insert('rotation_euler',frame=1); arm.rotation_euler[1]=math.radians(-45); arm.rotation_euler.keyframe_insert('rotation_euler',frame=144)

# Materials
floor=mat('polished floor',(0.035,0.045,0.055),metallic=.25,rough=.23); wall=mat('walls',(0.055,0.065,0.08),rough=.72); shelf=mat('shelves',(0.055,0.06,0.07),metallic=.15,rough=.35)
blue=mat('blue cases',(0.025,0.16,0.42),rough=.38); gold=mat('warm cases',(0.62,0.28,0.035),rough=.45); red=mat('red cases',(0.42,0.035,0.025),rough=.45); neon=mat('neon',(0.03,0.25,0.72),emission=(0.02,0.2,1.0))
# Room
cube('floor',(0,3,-.08),(5.2,9,.08),floor,0); cube('back',(0,11.8,2.5),(5.2,.12,2.6),wall,0); cube('left',(-5.1,4,2.5),(.12,8,2.6),wall,0); cube('right',(5.1,4,2.5),(.12,8,2.6),wall,0)
# Shelving aisles + many cases
for sx in (-3.25,3.25):
    for sy in (2.0,5.2,8.4):
        cube('shelf',(sx,sy,1.25),(1.15,.35,1.25),shelf,.03)
        for row in range(4):
            for col in range(9):
                mm=(blue,gold,red)[(row+col)%3]
                cube('case',(sx-0.92+col*.23,sy-.38,0.35+row*.57),(.09,.035,.23),mm,.015)
# central low racks
for sy in (3.4,6.8):
    cube('center rack',(0,sy,.8),(1.5,.48,.8),shelf,.04)
    for col in range(11): cube('dvd',( -1.25+col*.25,sy-.5,1.42),(.09,.035,.24),(blue,gold,red)[col%3],.01)
# Counter and glowing ceiling strips
cube('counter',(0,10.5,.62),(2.5,.55,.62),shelf,.08)
for x in (-3,-1,1,3):
    cube('light',(x,4.8,4.75),(.62,3.8,.035),neon,.02)
# Humans
human('customerA',-1.7,4.2,(0.08,.12,.18),0); human('customerB',1.7,7.3,(0.18,.07,.035),1); human('employee',0,9.8,(0.03,.12,.28),2)
# Camera
bpy.ops.object.camera_add(location=(0,-4.2,2.0)); cam=bpy.context.object; bpy.context.scene.camera=cam; cam.data.lens=28; cam.data.sensor_width=32

def track(obj, target):
    direction=Vector(target)-obj.location; obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
track(cam,(0,5.5,1.35)); cam.keyframe_insert('location',frame=1); cam.location=(0.25,1.2,1.85); track(cam,(0,7.2,1.45)); cam.keyframe_insert('location',frame=144); cam.keyframe_insert('rotation_euler',frame=144)
# lights
bpy.ops.object.light_add(type='AREA', location=(0,1.5,4.2)); key=bpy.context.object; key.data.energy=950; key.data.shape='RECTANGLE'; key.data.size=7; key.data.color=(.68,.8,1.0)
bpy.ops.object.light_add(type='AREA', location=(0,9,3.8)); fill=bpy.context.object; fill.data.energy=1200; fill.data.size=5; fill.data.color=(1.0,.48,.18); track(fill,(0,6,1))
# world/render
world=bpy.context.scene.world; world.color=(.004,.006,.012)
scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.resolution_x=540; scene.render.resolution_y=960; scene.render.resolution_percentage=100; scene.render.fps=24; scene.frame_start=1; scene.frame_end=144
scene.render.image_settings.file_format='FFMPEG'; scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='H264'; scene.render.ffmpeg.constant_rate_factor='MEDIUM'; scene.render.filepath='output/blender-video-store-sample.mp4'
scene.render.film_transparent=False
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath='output/blender-video-store-sample.blend'); bpy.ops.render.render(animation=True)
