import bpy, math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def mat(name, color, metallic=0.0, rough=.45, emission=None):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metallic; bs.inputs['Roughness'].default_value=rough
    if emission:
        k='Emission Color' if 'Emission Color' in bs.inputs else 'Emission'
        if k in bs.inputs: bs.inputs[k].default_value=(*emission,1)
        if 'Emission Strength' in bs.inputs: bs.inputs['Emission Strength'].default_value=4.0
    return m

def cube(name,loc,scale,material,bevel=.04):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        md=o.modifiers.new('bevel','BEVEL'); md.width=bevel; md.segments=2
    o.data.materials.append(material); return o

def human(name,x,y,shirt,phase=0):
    skin=mat(name+' skin',(.34,.16,.09),rough=.62); cloth=mat(name+' cloth',shirt,rough=.7); dark=mat(name+' pants',(.02,.025,.035),rough=.8)
    torso=cube(name+' torso',(x,y,1.42),(.25,.16,.45),cloth,.1)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=(x,y,2.02)); head=bpy.context.object; head.scale=(.20,.20,.25); head.data.materials.append(skin)
    for dx in (-.12,.12): cube(name+' leg',(x+dx,y,.61),(.075,.09,.46),dark,.04)
    for dx in (-.31,.31):
        arm=cube(name+' arm',(x+dx,y,1.48),(.065,.065,.34),skin,.04); arm.rotation_euler[1]=math.radians((-18 if dx<0 else 18)+phase); arm.keyframe_insert(data_path='rotation_euler',frame=1); arm.rotation_euler[1]+=math.radians(10); arm.keyframe_insert(data_path='rotation_euler',frame=120)
    torso.rotation_euler[2]=math.radians(phase*.35); torso.keyframe_insert(data_path='rotation_euler',frame=1); torso.rotation_euler[2]+=math.radians(3); torso.keyframe_insert(data_path='rotation_euler',frame=120)

def track(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

floor=mat('polished charcoal floor',(.025,.032,.042),.25,.18); wall=mat('deep navy walls',(.035,.045,.065),rough=.78); shelf=mat('black metal shelving',(.025,.028,.035),.3,.28)
blue=mat('blue cases',(.02,.12,.38)); gold=mat('amber cases',(.62,.23,.025)); red=mat('red cases',(.38,.025,.018)); cream=mat('cream cases',(.58,.52,.40)); cyan=mat('cyan practical',(.015,.18,.50),emission=(.01,.18,1)); warm=mat('warm practical',(.45,.16,.025),emission=(1,.22,.025))

cube('floor',(0,4,-.08),(5.2,9,.08),floor,0); cube('back',(0,12,2.5),(5.2,.12,2.6),wall,0); cube('left',(-5.1,4,2.5),(.12,8,2.6),wall,0); cube('right',(5.1,4,2.5),(.12,8,2.6),wall,0)
# luminous entrance frame / nostalgic storefront
cube('entrance top',(0,-2.2,4.25),(2.8,.08,.07),cyan,.02); cube('entrance L',(-2.75,-2.2,2.2),(.07,.08,2.0),cyan,.02); cube('entrance R',(2.75,-2.2,2.2),(.07,.08,2.0),cyan,.02)
# wall shelves with denser case detail
for sx in (-3.55,3.55):
    for sy in (1.7,4.5,7.3,10.1):
        cube('shelf',(sx,sy,1.42),(1.18,.32,1.42),shelf,.025)
        for row in range(5):
            for col in range(10): cube('case',(sx-.98+col*.215,sy-.35,.28+row*.54),(.078,.026,.215),(blue,gold,red,cream)[(row*3+col)%4],.008)
# central aisles
for sy in (3.1,6.1,9.0):
    cube('center rack',(0,sy,.82),(1.55,.42,.82),shelf,.035)
    for side in (-1,1):
        for col in range(12): cube('dvd',(-1.3+col*.235,sy+side*.45,1.43),(.075,.025,.225),(blue,gold,red,cream)[(col+side)%4],.006)
# checkout and glowing back-wall accents
cube('counter',(0,10.8,.62),(2.45,.58,.62),shelf,.07); cube('counter glow',(0,10.17,.88),(1.7,.025,.05),warm,.01)
for x in (-3,-1,1,3): cube('ceiling practical',(x,4.8,4.72),(.48,3.7,.025),cyan,.015)

human('browser A',-1.8,4.0,(.045,.08,.15),-12); human('browser B',1.65,7.15,(.18,.055,.025),15); human('employee',.3,9.9,(.025,.10,.24),-5)

# cinematic camera: lower eye level, gentle lateral parallax and forward dolly
bpy.ops.object.camera_add(location=(-.55,-3.6,1.72)); cam=bpy.context.object; bpy.context.scene.camera=cam; cam.data.lens=32; cam.data.sensor_width=32; cam.data.dof.use_dof=True; cam.data.dof.focus_distance=7.0; cam.data.dof.aperture_fstop=3.2
track(cam,(0,5.2,1.35)); cam.keyframe_insert(data_path='location',frame=1); cam.keyframe_insert(data_path='rotation_euler',frame=1)
cam.location=(.42,1.25,1.68); track(cam,(0,7.4,1.38)); cam.keyframe_insert(data_path='location',frame=120); cam.keyframe_insert(data_path='rotation_euler',frame=120)

# layered lighting: cool key, warm backlight, aisle pools
bpy.ops.object.light_add(type='AREA',location=(0,.5,4.1)); key=bpy.context.object; key.data.energy=1050; key.data.shape='RECTANGLE'; key.data.size=6; key.data.color=(.55,.72,1)
bpy.ops.object.light_add(type='AREA',location=(0,10.2,3.8)); back=bpy.context.object; back.data.energy=1450; back.data.size=4.5; back.data.color=(1,.32,.09); track(back,(0,6.5,1.2))
for x,y in ((-2.7,4),(2.7,6.5),(-2.3,9)):
    bpy.ops.object.light_add(type='AREA',location=(x,y,3.2)); l=bpy.context.object; l.data.energy=420; l.data.size=2.0; l.data.color=(.18,.35,1); track(l,(0,y,1))

scene=bpy.context.scene; scene.world.color=(.002,.004,.009); scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=540; scene.render.resolution_y=960; scene.render.resolution_percentage=100; scene.render.fps=24; scene.frame_start=1; scene.frame_end=120
scene.render.image_settings.file_format='FFMPEG'; scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='H264'; scene.render.ffmpeg.constant_rate_factor='MEDIUM'; scene.render.filepath='output/blender-video-store-sample.mp4'
scene.render.film_transparent=False
try: scene.view_settings.look='AgX - Medium High Contrast'
except Exception: pass
bpy.ops.wm.save_as_mainfile(filepath='output/blender-video-store-sample.blend'); bpy.ops.render.render(animation=True)
