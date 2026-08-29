import bpy
import math
import urllib.request
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "assets" / "v3"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

CHAR_DIR = ASSET_ROOT / "characters"
ANIM_DIR = ASSET_ROOT / "animations"
ENV_DIR = ASSET_ROOT / "environment"
PROP_DIR = ASSET_ROOT / "props"

# CC0 Quaternius character derivatives distributed in a public GitHub repository.
# Provenance is documented by the source repository's ATTRIBUTION.md.
CHARACTER_ASSETS = {
    "customer_a.glb": "https://raw.githubusercontent.com/fastrouter/experiments-costa-vista/main/public/assets/toon/chars/220fa5da.glb",
    "customer_b.glb": "https://raw.githubusercontent.com/fastrouter/experiments-costa-vista/main/public/assets/toon/chars/3ac627e2.glb",
    "customer_c.glb": "https://raw.githubusercontent.com/fastrouter/experiments-costa-vista/main/public/assets/toon/chars/5ab8ebe2.glb",
    "employee.glb": "https://raw.githubusercontent.com/fastrouter/experiments-costa-vista/main/public/assets/toon/tpose-hero.glb",
}

ANIMATION_ASSETS = {
    "AnimationLibrary_Godot_Standard.gltf": "https://raw.githubusercontent.com/J-Ponzo/gltf-universal-animation-library/main/glTF/AnimationLibrary_Godot_Standard.gltf",
    "AnimationLibrary_Godot_Standard.bin": "https://raw.githubusercontent.com/J-Ponzo/gltf-universal-animation-library/main/glTF/AnimationLibrary_Godot_Standard.bin",
}


def download_if_missing(folder: Path, filename: str, url: str):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    if target.exists() and target.stat().st_size > 1024:
        return target
    print(f"Downloading asset: {filename}")
    urllib.request.urlretrieve(url, target)
    return target


def ensure_external_assets():
    for name, url in CHARACTER_ASSETS.items():
        download_if_missing(CHAR_DIR, name, url)
    for name, url in ANIMATION_ASSETS.items():
        download_if_missing(ANIM_DIR, name, url)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_asset(path: Path):
    suffix = path.suffix.lower()
    before = set(bpy.data.objects)
    if suffix == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix in {'.glb', '.gltf'}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == '.blend':
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = src.objects
        for obj in dst.objects:
            if obj:
                bpy.context.collection.objects.link(obj)
    else:
        return []
    return list(set(bpy.data.objects) - before)


def discover(folder: Path):
    if not folder.exists():
        return []
    allowed = {'.fbx', '.glb', '.gltf', '.blend'}
    return sorted([p for p in folder.rglob('*') if p.suffix.lower() in allowed])


def make_material(name, base, metallic=0.0, roughness=0.45, emission=None, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if emission and 'Emission Color' in bsdf.inputs:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    elif emission and 'Emission' in bsdf.inputs:
        bsdf.inputs['Emission'].default_value = (*emission, 1)
    return mat


def cube(name, loc, scale, mat=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    return o


def fallback_store():
    floor = make_material('Floor', (0.025, 0.03, 0.04), metallic=.15, roughness=.22)
    wall = make_material('Wall', (0.03, 0.05, 0.075), roughness=.55)
    shelf = make_material('Shelf', (0.025, 0.025, 0.03), metallic=.35, roughness=.32)
    case_blue = make_material('CaseBlue', (.035, .12, .28), roughness=.32)
    case_red = make_material('CaseRed', (.32, .035, .035), roughness=.32)
    case_gold = make_material('CaseGold', (.38, .20, .035), roughness=.32)
    cyan = make_material('CyanPractical', (.02, .13, .16), roughness=.3, emission=(.02,.55,.7), strength=4)
    warm = make_material('WarmPractical', (.18, .07, .025), roughness=.3, emission=(1.0,.28,.06), strength=3)

    cube('Floor', (0, 3, -0.08), (5.2, 7.0, .08), floor)
    cube('BackWall', (0, 9.8, 2.0), (5.2,.08,2.0), wall)
    cube('LeftWall', (-5.1, 3.0, 2.0), (.08,7.0,2.0), wall)
    cube('RightWall', (5.1, 3.0, 2.0), (.08,7.0,2.0), wall)

    mats = [case_blue, case_red, case_gold]
    for shelf_i, x in enumerate((-3.2, 0, 3.2)):
        for y_i, y in enumerate((1.6, 4.0, 6.4)):
            cube(f'Shelf_{x}_{y}', (x,y,1.05), (1.05,.28,1.05), shelf)
            for z_i, z in enumerate((.35,.75,1.15,1.55)):
                cube('ShelfBoard', (x,y,z), (1.05,.42,.025), shelf)
                for k in range(9):
                    px = x - .88 + k * .22
                    cube(f'Case_{shelf_i}_{y_i}_{z_i}_{k}', (px,y-.32,z+.13), (.075,.055,.15), mats[(k+z_i+y_i)%3])

    cube('Counter', (2.9,8.1,.55), (1.6,.65,.55), shelf)
    cube('EntranceGlow', (0,-3.7,1.8), (2.15,.05,1.75), cyan)
    cube('CounterGlow', (2.9,7.42,.55), (1.45,.03,.32), warm)


def center_and_place(objects, location, scale=1.0, rotation_z=0.0):
    roots = [o for o in objects if o.parent is None]
    if not roots:
        roots = objects
    for obj in roots:
        obj.scale *= scale
        obj.rotation_euler.z += rotation_z
        obj.location += Vector(location)
    return roots


def animate_character_roots(roots, idx):
    if not roots:
        return
    # Natural ambient movement while the full mocap retarget stage is being integrated.
    offsets = [Vector((0.0, .18, 0.0)), Vector((-.10, .08, 0.0)), Vector((.12, -.10, 0.0)), Vector((0.0, .04, 0.0))]
    turns = [0.08, -0.10, 0.13, -0.05]
    for root in roots:
        start = root.location.copy()
        start_rot = root.rotation_euler.z
        root.keyframe_insert('location', frame=1)
        root.keyframe_insert('rotation_euler', frame=1)
        root.location = start + offsets[idx]
        root.rotation_euler.z = start_rot + turns[idx]
        root.keyframe_insert('location', frame=120)
        root.keyframe_insert('rotation_euler', frame=120)


def setup_camera():
    bpy.ops.object.camera_add(location=(-0.6,-4.6,1.72))
    cam = bpy.context.object
    cam.data.lens = 34
    cam.data.sensor_width = 32
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 7.0
    cam.data.dof.aperture_fstop = 3.2
    bpy.context.scene.camera = cam

    def point_at(obj, target):
        direction = Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()

    cam.location = (-.6,-4.6,1.72)
    point_at(cam, (0,4.2,1.35))
    cam.keyframe_insert('location', frame=1)
    cam.keyframe_insert('rotation_euler', frame=1)
    cam.location = (.48,1.15,1.67)
    point_at(cam, (.25,6.6,1.3))
    cam.keyframe_insert('location', frame=120)
    cam.keyframe_insert('rotation_euler', frame=120)


def setup_lights():
    bpy.ops.object.light_add(type='AREA', location=(-2.5,1.0,3.5))
    bpy.context.object.data.energy = 850
    bpy.context.object.data.shape = 'RECTANGLE'
    bpy.context.object.data.size = 5
    bpy.context.object.data.color = (.35,.55,1.0)

    bpy.ops.object.light_add(type='AREA', location=(2.8,7.3,3.1))
    bpy.context.object.data.energy = 1050
    bpy.context.object.data.size = 4
    bpy.context.object.data.color = (1.0,.38,.12)

    for y in (0.5,3.2,5.9,8.4):
        bpy.ops.object.light_add(type='AREA', location=(0,y,3.55))
        l = bpy.context.object
        l.data.energy = 500
        l.data.size = 3.0
        l.data.color = (.55,.72,1.0)
        l.rotation_euler.x = 0


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 540
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 120
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = str(OUT / 'blender-video-store-v3.mp4')
    if hasattr(scene, 'view_settings'):
        try:
            scene.view_settings.look = 'AgX - Medium High Contrast'
        except Exception:
            pass


def main():
    ensure_external_assets()
    clear_scene()
    configure_render()

    env_assets = discover(ENV_DIR)
    if env_assets:
        for p in env_assets[:4]:
            import_asset(p)
    else:
        fallback_store()

    char_assets = discover(CHAR_DIR)
    placements = [(-2.4,2.1,0), (1.0,3.4,0), (-.6,6.2,0), (2.9,7.4,0)]
    angles = [0.25,-0.5,0.9,math.pi]
    scales = [.95,.95,.95,.95]
    for idx, p in enumerate(char_assets[:4]):
        objs = import_asset(p)
        roots = center_and_place(objs, placements[idx], scales[idx], angles[idx])
        animate_character_roots(roots, idx)

    prop_assets = discover(PROP_DIR)
    for p in prop_assets[:10]:
        import_asset(p)

    setup_lights()
    setup_camera()

    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'blender-video-store-v3.blend'))
    bpy.ops.render.render(animation=True)


if __name__ == '__main__':
    main()
