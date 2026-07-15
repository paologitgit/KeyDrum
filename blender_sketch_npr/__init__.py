bl_info = {
    "name": "Sketch NPR (Line Art + Dynamic Hatching)",
    "author": "Claude",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Sketch NPR",
    "description": "Schwarz/Weiss-Skizzenlook fuer Eevee: Line-Art-Konturen + prozedurale "
                   "Schraffur-Shader, deren Ausrichtung dynamisch der Lichtrichtung folgt.",
    "category": "Render",
}

import bpy
import math
from bpy.props import (
    PointerProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
)
from bpy.types import (
    Operator,
    Panel,
    PropertyGroup,
)

HATCH_NODEGROUP_NAME = "NPR_Hatching"
INK_MATERIAL_NAME = "Sketch_Ink"
LINEART_OBJECT_NAME = "Sketch_LineArt"

IS_GP3 = bpy.app.version >= (4, 3, 0)


# ---------------------------------------------------------------------------
# Hatching shader node group
# ---------------------------------------------------------------------------

def _new_socket(tree, name, in_out, socket_type, default=None, min_val=None, max_val=None):
    """Create a node-group interface socket using the Blender 4.x interface API."""
    socket = tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default is not None:
        socket.default_value = default
    if min_val is not None:
        socket.min_value = min_val
    if max_val is not None:
        socket.max_value = max_val
    return socket


def _add_light_angle_driver(value_node, light_obj, extra_deg=0.0):
    """Drive a Value node's output with the chosen light's Z rotation (radians)."""
    # Clear any pre-existing driver first so re-runs don't stack them.
    try:
        value_node.outputs[0].driver_remove('default_value')
    except Exception:
        pass
    if light_obj is None:
        value_node.outputs[0].default_value = math.radians(extra_deg)
        return
    fcurve = value_node.outputs[0].driver_add('default_value')
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    var = drv.variables.new()
    var.name = "lz"
    var.type = 'SINGLE_PROP'
    var.targets[0].id = light_obj
    var.targets[0].data_path = "rotation_euler[2]"
    drv.expression = f"lz + {math.radians(extra_deg)!r}"


def build_hatch_nodegroup(light_obj=None):
    """Create (or rebuild) the NPR_Hatching node group. Returns the node tree."""
    existing = bpy.data.node_groups.get(HATCH_NODEGROUP_NAME)
    if existing is not None:
        bpy.data.node_groups.remove(existing)

    tree = bpy.data.node_groups.new(HATCH_NODEGROUP_NAME, 'ShaderNodeTree')

    # --- interface -----------------------------------------------------
    _new_socket(tree, "Paper Color", 'INPUT', 'NodeSocketColor', default=(1, 1, 1, 1))
    _new_socket(tree, "Ink Color", 'INPUT', 'NodeSocketColor', default=(0, 0, 0, 1))
    _new_socket(tree, "Exposure", 'INPUT', 'NodeSocketFloat', default=1.0, min_val=0.0, max_val=10.0)
    _new_socket(tree, "Contrast", 'INPUT', 'NodeSocketFloat', default=1.4, min_val=0.1, max_val=5.0)
    _new_socket(tree, "Hatch Scale", 'INPUT', 'NodeSocketFloat', default=80.0, min_val=1.0, max_val=1000.0)
    _new_socket(tree, "Line Width", 'INPUT', 'NodeSocketFloat', default=0.10, min_val=0.01, max_val=0.9)
    _new_socket(tree, "Angle Offset", 'INPUT', 'NodeSocketFloat', default=0.0, min_val=-360.0, max_val=360.0)
    _new_socket(tree, "Wobble", 'INPUT', 'NodeSocketFloat', default=0.15, min_val=0.0, max_val=2.0)
    _new_socket(tree, "Blur", 'INPUT', 'NodeSocketFloat', default=0.03, min_val=0.001, max_val=0.5)
    _new_socket(tree, "Color", 'OUTPUT', 'NodeSocketColor')
    _new_socket(tree, "Alpha", 'OUTPUT', 'NodeSocketFloat')

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1400, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1200, 0)

    # --- shading term (Eevee-only trick: Diffuse -> Shader to RGB) -----
    geo = nodes.new('ShaderNodeNewGeometry')
    geo.location = (-1400, -300)

    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = (-1150, -300)
    diffuse.inputs['Color'].default_value = (1, 1, 1, 1)
    links.new(geo.outputs['Normal'], diffuse.inputs['Normal'])

    to_rgb = nodes.new('ShaderNodeShaderToRGB')
    to_rgb.location = (-950, -300)
    links.new(diffuse.outputs['BSDF'], to_rgb.inputs['Shader'])

    exposure_mul = nodes.new('ShaderNodeMath')
    exposure_mul.operation = 'MULTIPLY'
    exposure_mul.location = (-750, -300)
    links.new(to_rgb.outputs['Color'], exposure_mul.inputs[0])
    links.new(n_in.outputs['Exposure'], exposure_mul.inputs[1])

    # contrast around 0.5 pivot: (v - 0.5) * contrast + 0.5, clamped
    sub05 = nodes.new('ShaderNodeMath')
    sub05.operation = 'SUBTRACT'
    sub05.inputs[1].default_value = 0.5
    sub05.location = (-550, -300)
    links.new(exposure_mul.outputs[0], sub05.inputs[0])

    mul_contrast = nodes.new('ShaderNodeMath')
    mul_contrast.operation = 'MULTIPLY'
    mul_contrast.location = (-350, -300)
    links.new(sub05.outputs[0], mul_contrast.inputs[0])
    links.new(n_in.outputs['Contrast'], mul_contrast.inputs[1])

    add05 = nodes.new('ShaderNodeMath')
    add05.operation = 'ADD'
    add05.inputs[1].default_value = 0.5
    add05.location = (-150, -300)
    links.new(mul_contrast.outputs[0], add05.inputs[0])

    tone = nodes.new('ShaderNodeClamp')
    tone.location = (50, -300)
    links.new(add05.outputs[0], tone.inputs['Value'])

    # --- light-driven hatch angle ---------------------------------------
    light_angle = nodes.new('ShaderNodeValue')
    light_angle.name = "LightAngleDriver"
    light_angle.label = "Light Angle (driven)"
    light_angle.location = (-1400, 500)
    _add_light_angle_driver(light_angle, light_obj)

    offset_rad = nodes.new('ShaderNodeMath')
    offset_rad.operation = 'MULTIPLY'
    offset_rad.inputs[1].default_value = math.pi / 180.0
    offset_rad.location = (-1400, 350)
    links.new(n_in.outputs['Angle Offset'], offset_rad.inputs[0])

    base_angle = nodes.new('ShaderNodeMath')
    base_angle.operation = 'ADD'
    base_angle.location = (-1200, 450)
    links.new(light_angle.outputs[0], base_angle.inputs[0])
    links.new(offset_rad.outputs[0], base_angle.inputs[1])

    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-1400, 900)

    def make_hatch_layer(idx, angle_deg_static, scale_mul, x):
        """One directional hatch layer: rotated + wobble-warped wave texture -> soft line mask."""
        static_add = nodes.new('ShaderNodeMath')
        static_add.operation = 'ADD'
        static_add.inputs[1].default_value = math.radians(angle_deg_static)
        static_add.location = (x - 200, 750 - idx * 60)
        links.new(base_angle.outputs[0], static_add.inputs[0])

        rot = nodes.new('ShaderNodeVectorRotate')
        rot.rotation_type = 'Z_AXIS'
        rot.location = (x, 700 - idx * 250)
        links.new(tex_coord.outputs['Object'], rot.inputs['Vector'])
        links.new(static_add.outputs[0], rot.inputs['Angle'])

        scale_node = nodes.new('ShaderNodeMath')
        scale_node.operation = 'MULTIPLY'
        scale_node.inputs[1].default_value = scale_mul
        scale_node.location = (x, 550 - idx * 250)
        links.new(n_in.outputs['Hatch Scale'], scale_node.inputs[0])

        # decorrelate each layer's noise sample so layers don't wobble in lockstep
        layer_offset = nodes.new('ShaderNodeVectorMath')
        layer_offset.operation = 'ADD'
        layer_offset.inputs[1].default_value = (idx * 13.7, idx * 7.3, idx * 3.1)
        layer_offset.location = (x + 200, 900 - idx * 250)
        links.new(rot.outputs['Vector'], layer_offset.inputs[0])

        noise = nodes.new('ShaderNodeTexNoise')
        noise.noise_dimensions = '3D'
        noise.inputs['Detail'].default_value = 2.0
        noise.inputs['Roughness'].default_value = 0.5
        noise.location = (x + 400, 900 - idx * 250)
        links.new(layer_offset.outputs['Vector'], noise.inputs['Vector'])
        links.new(scale_node.outputs[0], noise.inputs['Scale'])

        noise_centered = nodes.new('ShaderNodeVectorMath')
        noise_centered.operation = 'SUBTRACT'
        noise_centered.inputs[1].default_value = (0.5, 0.5, 0.5)
        noise_centered.location = (x + 600, 900 - idx * 250)
        links.new(noise.outputs['Color'], noise_centered.inputs[0])

        wobble_scaled = nodes.new('ShaderNodeVectorMath')
        wobble_scaled.operation = 'SCALE'
        wobble_scaled.location = (x + 800, 900 - idx * 250)
        links.new(noise_centered.outputs['Vector'], wobble_scaled.inputs[0])
        links.new(n_in.outputs['Wobble'], wobble_scaled.inputs['Scale'])

        warped = nodes.new('ShaderNodeVectorMath')
        warped.operation = 'ADD'
        warped.location = (x + 400, 700 - idx * 250)
        links.new(rot.outputs['Vector'], warped.inputs[0])
        links.new(wobble_scaled.outputs['Vector'], warped.inputs[1])

        wave = nodes.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'X'
        wave.inputs['Distortion'].default_value = 0.0
        wave.inputs['Detail'].default_value = 0.0
        wave.location = (x + 600, 650 - idx * 250)
        links.new(warped.outputs['Vector'], wave.inputs['Vector'])
        links.new(scale_node.outputs[0], wave.inputs['Scale'])

        line_low = nodes.new('ShaderNodeMath')
        line_low.operation = 'SUBTRACT'
        line_low.location = (x + 800, 500 - idx * 250)
        links.new(n_in.outputs['Line Width'], line_low.inputs[0])
        links.new(n_in.outputs['Blur'], line_low.inputs[1])

        line_high = nodes.new('ShaderNodeMath')
        line_high.operation = 'ADD'
        line_high.location = (x + 800, 380 - idx * 250)
        links.new(n_in.outputs['Line Width'], line_high.inputs[0])
        links.new(n_in.outputs['Blur'], line_high.inputs[1])

        line_mask = nodes.new('ShaderNodeMapRange')
        line_mask.interpolation_type = 'SMOOTHSTEP'
        line_mask.clamp = True
        line_mask.inputs['To Min'].default_value = 1.0
        line_mask.inputs['To Max'].default_value = 0.0
        line_mask.location = (x + 1000, 650 - idx * 250)
        links.new(wave.outputs['Fac'], line_mask.inputs['Value'])
        links.new(line_low.outputs[0], line_mask.inputs['From Min'])
        links.new(line_high.outputs[0], line_mask.inputs['From Max'])
        return line_mask

    layer1 = make_hatch_layer(0, 45.0, 1.0, -900)
    layer2 = make_hatch_layer(1, -45.0, 1.0, -900)
    layer3 = make_hatch_layer(2, 90.0, 1.8, -900)

    # gates: which layers are active per tone band (darker -> more layers)
    gate1 = nodes.new('ShaderNodeMath')
    gate1.operation = 'LESS_THAN'
    gate1.inputs[1].default_value = 0.70
    gate1.location = (250, -100)
    links.new(tone.outputs['Result'], gate1.inputs[0])

    gate2 = nodes.new('ShaderNodeMath')
    gate2.operation = 'LESS_THAN'
    gate2.inputs[1].default_value = 0.40
    gate2.location = (250, -220)
    links.new(tone.outputs['Result'], gate2.inputs[0])

    gate3 = nodes.new('ShaderNodeMath')
    gate3.operation = 'LESS_THAN'
    gate3.inputs[1].default_value = 0.15
    gate3.location = (250, -340)
    links.new(tone.outputs['Result'], gate3.inputs[0])

    def gated(layer_mask, gate, x, y):
        m = nodes.new('ShaderNodeMath')
        m.operation = 'MULTIPLY'
        m.location = (x, y)
        links.new(layer_mask.outputs[0], m.inputs[0])
        links.new(gate.outputs[0], m.inputs[1])
        return m

    g1 = gated(layer1, gate1, 500, -100)
    g2 = gated(layer2, gate2, 500, -220)
    g3 = gated(layer3, gate3, 500, -340)

    max12 = nodes.new('ShaderNodeMath')
    max12.operation = 'MAXIMUM'
    max12.location = (700, -160)
    links.new(g1.outputs[0], max12.inputs[0])
    links.new(g2.outputs[0], max12.inputs[1])

    ink_mask = nodes.new('ShaderNodeMath')
    ink_mask.operation = 'MAXIMUM'
    ink_mask.location = (900, -220)
    links.new(max12.outputs[0], ink_mask.inputs[0])
    links.new(g3.outputs[0], ink_mask.inputs[1])

    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.location = (1000, 200)
    links.new(ink_mask.outputs[0], mix.inputs['Factor'])
    links.new(n_in.outputs['Paper Color'], mix.inputs['A'])
    links.new(n_in.outputs['Ink Color'], mix.inputs['B'])

    links.new(mix.outputs['Result'], n_out.inputs['Color'])
    links.new(ink_mask.outputs[0], n_out.inputs['Alpha'])

    return tree


def build_hatch_material(light_obj=None, wobble=0.15, blur=0.03, transparent=False):
    mat = bpy.data.materials.get("Sketch_Hatch")
    if mat is None:
        mat = bpy.data.materials.new("Sketch_Hatch")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    tree = build_hatch_nodegroup(light_obj)

    group = nt.nodes.new('ShaderNodeGroup')
    group.node_tree = tree
    group.location = (-200, 0)
    group.inputs['Wobble'].default_value = wobble
    group.inputs['Blur'].default_value = blur

    emission = nt.nodes.new('ShaderNodeEmission')
    emission.location = (100, 150)
    emission.inputs['Strength'].default_value = 1.0
    nt.links.new(group.outputs['Color'], emission.inputs['Color'])

    if transparent:
        # Paper areas become fully see-through; only ink strokes stay opaque black.
        transp = nt.nodes.new('ShaderNodeBsdfTransparent')
        transp.location = (100, -100)

        mix_shader = nt.nodes.new('ShaderNodeMixShader')
        mix_shader.location = (350, 0)
        nt.links.new(group.outputs['Alpha'], mix_shader.inputs['Fac'])
        nt.links.new(transp.outputs['BSDF'], mix_shader.inputs[1])
        nt.links.new(emission.outputs['Emission'], mix_shader.inputs[2])
        surface_socket = mix_shader.outputs['Shader']

        for attr, value in (("blend_method", 'HASHED'), ("shadow_method", 'HASHED'),
                            ("use_transparent_shadow", True)):
            try:
                setattr(mat, attr, value)
            except Exception:
                pass
    else:
        surface_socket = emission.outputs['Emission']
        try:
            mat.blend_method = 'OPAQUE'
        except Exception:
            pass

    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (600, 0)
    nt.links.new(surface_socket, out.inputs['Surface'])

    return mat


def overlay_hatch_on_material(mat, light_obj=None, wobble=0.15, blur=0.03):
    """Splice the hatch pattern on top of an existing material's shader output.

    Keeps whatever the material already does (Principled BSDF, textures, ...)
    and draws ink strokes over it via Mix Shader, so no alpha/blend-mode
    setup is needed and there is no z-fighting risk (same faces, same
    material slot).
    """
    if not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree

    out = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None)
    if out is None:
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        out.location = (600, 0)

    surface_input = out.inputs['Surface']
    original_link = surface_input.links[0] if surface_input.links else None
    original_socket = original_link.from_socket if original_link else None

    tree = build_hatch_nodegroup(light_obj)

    group = nt.nodes.new('ShaderNodeGroup')
    group.node_tree = tree
    group.location = (out.location.x - 500, out.location.y + 400)
    group.inputs['Wobble'].default_value = wobble
    group.inputs['Blur'].default_value = blur

    emission = nt.nodes.new('ShaderNodeEmission')
    emission.location = (out.location.x - 250, out.location.y + 400)
    nt.links.new(group.outputs['Color'], emission.inputs['Color'])

    mix_shader = nt.nodes.new('ShaderNodeMixShader')
    mix_shader.location = (out.location.x - 100, out.location.y + 150)
    nt.links.new(group.outputs['Alpha'], mix_shader.inputs['Fac'])
    if original_socket is not None:
        nt.links.new(original_socket, mix_shader.inputs[1])
    nt.links.new(emission.outputs['Emission'], mix_shader.inputs[2])

    nt.links.new(mix_shader.outputs['Shader'], surface_input)


# ---------------------------------------------------------------------------
# Line Art setup (version-aware: legacy GPv2 vs. new GPv3 4.3+)
# ---------------------------------------------------------------------------

def setup_line_art(context, thickness_px=2):
    scene = context.scene
    existing = bpy.data.objects.get(LINEART_OBJECT_NAME)
    if existing is not None:
        gp_obj = existing
    else:
        if IS_GP3:
            bpy.ops.object.grease_pencil_add(type='EMPTY', align='WORLD', location=(0, 0, 0))
        else:
            bpy.ops.object.gpencil_add(type='EMPTY', align='WORLD', location=(0, 0, 0))
        gp_obj = context.object
        gp_obj.name = LINEART_OBJECT_NAME

    context.view_layer.objects.active = gp_obj

    if IS_GP3:
        mod = gp_obj.modifiers.get("LineArt")
        if mod is None:
            bpy.ops.object.modifier_add(type='GREASE_PENCIL_LINEART')
            mod = gp_obj.modifiers[-1]
            mod.name = "LineArt"
    else:
        mod = gp_obj.grease_pencil_modifiers.get("LineArt")
        if mod is None:
            bpy.ops.object.gpencil_modifier_add(type='LINEART')
            mod = gp_obj.grease_pencil_modifiers[-1]
            mod.name = "LineArt"

    try:
        mod.source_type = 'SCENE'
    except Exception as e:
        print(f"[Sketch NPR] source_type konnte nicht gesetzt werden: {e}")
    try:
        mod.thickness = thickness_px
    except Exception as e:
        print(f"[Sketch NPR] thickness konnte nicht gesetzt werden: {e}")
    for flag in ("use_contour", "use_crease", "use_material"):
        try:
            setattr(mod, flag, True)
        except Exception:
            pass

    # black stroke material
    mat = bpy.data.materials.get(INK_MATERIAL_NAME)
    if mat is None:
        mat = bpy.data.materials.new(INK_MATERIAL_NAME)
        try:
            bpy.data.materials.create_gpencil_data(mat)
            mat.grease_pencil.color = (0, 0, 0, 1)
            mat.grease_pencil.show_stroke = True
            mat.grease_pencil.show_fill = False
        except Exception as e:
            print(f"[Sketch NPR] GP-Material konnte nicht initialisiert werden: {e}")
    if mat.name not in [m.name for m in gp_obj.data.materials if m]:
        gp_obj.data.materials.append(mat)

    return gp_obj


def setup_render_scene(context):
    scene = context.scene
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
    if 'BLENDER_EEVEE_NEXT' in engines:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    elif 'BLENDER_EEVEE' in engines:
        scene.render.engine = 'BLENDER_EEVEE'

    if scene.world is None:
        scene.world = bpy.data.worlds.new("Sketch_World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (1, 1, 1, 1)
        bg.inputs[1].default_value = 1.0

    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class SketchNPRSettings(PropertyGroup):
    light: PointerProperty(
        name="Licht",
        description="Objekt, dessen Rotation die Schraffur-Ausrichtung steuert",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'LIGHT',
    )
    line_thickness: IntProperty(
        name="Linienstaerke", default=2, min=1, max=50,
    )
    wobble: FloatProperty(
        name="Wobble (zittrig)", description="Handgezeichnete Unregelmaessigkeit der Striche",
        default=0.15, min=0.0, max=2.0,
    )
    blur: FloatProperty(
        name="Blur (unscharf)", description="Weichheit der Strichkanten",
        default=0.03, min=0.001, max=0.5,
    )
    transparent: BoolProperty(
        name="Transparent (Paper = durchsichtig)",
        description="Nur Tinte bleibt sichtbar, Papierflaeche wird transparent "
                     "(z.B. fuer ein separates Overlay-Objekt)",
        default=False,
    )


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class SKETCHNPR_OT_setup_scene(Operator):
    bl_idname = "sketchnpr.setup_scene"
    bl_label = "Render Setup (Eevee, Weiss/Standard)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        setup_render_scene(context)
        self.report({'INFO'}, "Szene fuer Sketch-Look konfiguriert.")
        return {'FINISHED'}


class SKETCHNPR_OT_setup_lineart(Operator):
    bl_idname = "sketchnpr.setup_lineart"
    bl_label = "Line-Art-Konturen einrichten"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.sketch_npr
        try:
            setup_line_art(context, thickness_px=settings.line_thickness)
        except Exception as e:
            self.report({'ERROR'}, f"Line Art Setup fehlgeschlagen: {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Line-Art-Objekt eingerichtet.")
        return {'FINISHED'}


class SKETCHNPR_OT_build_hatch_material(Operator):
    bl_idname = "sketchnpr.build_hatch_material"
    bl_label = "Hatch-Material auf Auswahl anwenden"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.sketch_npr
        try:
            mat = build_hatch_material(
                settings.light, wobble=settings.wobble, blur=settings.blur,
                transparent=settings.transparent,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Hatch-Shader konnte nicht gebaut werden: {e}")
            return {'CANCELLED'}

        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "Keine Mesh-Objekte ausgewaehlt.")
            return {'CANCELLED'}

        for obj in targets:
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

        self.report({'INFO'}, f"Hatch-Material auf {len(targets)} Objekt(e) angewendet.")
        return {'FINISHED'}


class SKETCHNPR_OT_overlay_on_material(Operator):
    bl_idname = "sketchnpr.overlay_on_material"
    bl_label = "Auf bestehendes Material legen"
    bl_description = ("Legt die Schraffur als Overlay auf das aktive Material jedes "
                       "ausgewaehlten Objekts, ohne dessen bisheriges Shading zu ersetzen")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.sketch_npr
        targets = [o for o in context.selected_objects if o.type == 'MESH' and o.active_material]
        if not targets:
            self.report({'WARNING'}, "Keine Mesh-Objekte mit aktivem Material ausgewaehlt.")
            return {'CANCELLED'}

        count = 0
        for obj in targets:
            try:
                overlay_hatch_on_material(
                    obj.active_material, settings.light,
                    wobble=settings.wobble, blur=settings.blur,
                )
                count += 1
            except Exception as e:
                self.report({'WARNING'}, f"{obj.active_material.name}: {e}")

        self.report({'INFO'}, f"Hatch-Overlay auf {count} Material(ien) angewendet.")
        return {'FINISHED'}


class SKETCHNPR_OT_refresh_light_driver(Operator):
    bl_idname = "sketchnpr.refresh_light_driver"
    bl_label = "Licht-Kopplung aktualisieren"
    bl_description = "Aktualisiert den Driver, falls das gewaehlte Licht geaendert wurde"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.sketch_npr
        tree = bpy.data.node_groups.get(HATCH_NODEGROUP_NAME)
        if tree is None:
            self.report({'WARNING'}, "Noch kein Hatch-Material erzeugt.")
            return {'CANCELLED'}
        node = tree.nodes.get("LightAngleDriver")
        if node is None:
            self.report({'ERROR'}, "LightAngleDriver-Node nicht gefunden.")
            return {'CANCELLED'}
        _add_light_angle_driver(node, settings.light)
        self.report({'INFO'}, "Licht-Kopplung aktualisiert.")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class SKETCHNPR_PT_main(Panel):
    bl_label = "Sketch NPR"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Sketch NPR"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.sketch_npr

        box = layout.box()
        box.label(text="Render Setup", icon='SCENE')
        box.operator(SKETCHNPR_OT_setup_scene.bl_idname)

        box = layout.box()
        box.label(text="Konturen (Line Art)", icon='GREASEPENCIL')
        box.prop(settings, "line_thickness")
        box.operator(SKETCHNPR_OT_setup_lineart.bl_idname)

        box = layout.box()
        box.label(text="Schattierung (Hatching)", icon='SHADING_TEXTURE')
        box.prop(settings, "light")
        box.prop(settings, "wobble")
        box.prop(settings, "blur")
        box.prop(settings, "transparent")
        row = box.row(align=True)
        row.operator(SKETCHNPR_OT_build_hatch_material.bl_idname)
        row.operator(SKETCHNPR_OT_refresh_light_driver.bl_idname, text="", icon='FILE_REFRESH')
        box.operator(SKETCHNPR_OT_overlay_on_material.bl_idname)
        box.label(text="Tipp: Feintuning (Kontrast, Hatch Scale, Line Width)")
        box.label(text="direkt im Shader-Editor am 'NPR_Hatching'-Node.")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    SketchNPRSettings,
    SKETCHNPR_OT_setup_scene,
    SKETCHNPR_OT_setup_lineart,
    SKETCHNPR_OT_build_hatch_material,
    SKETCHNPR_OT_overlay_on_material,
    SKETCHNPR_OT_refresh_light_driver,
    SKETCHNPR_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.sketch_npr = PointerProperty(type=SketchNPRSettings)


def unregister():
    del bpy.types.Scene.sketch_npr
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
