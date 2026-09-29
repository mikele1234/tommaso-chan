# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE DELLA NEVE - terza serie per Blender.

    01  ORSO-AURORA          (pelliccia a fibra ottica con l'aurora boreale)
    02  PINGUINO-CRISTALLO   (pancia-lampadina di vetro spesso)
    03  RENNA-COMETA         (corna-antenne accecanti e scia di neve luminosa)
    04  VOLPE-GHIACCIAIO     (corpo di ghiaccio con un cuore di luce)
    05  LEOPARDO-VALANGA     (rosette di scaglie ciano e bulbo sulla coda)
    06  FALENA-YETI          (pelliccia bianca, luce magenta che filtra da sotto)
    07  CIVETTA-BUFERA       (piume bordate di cristalli di ghiaccio, occhi-faro)
    08  IL PUPAZZO "SKIBIDI" (collo infinito e naso LED RGB)

Usa l'infrastruttura di `creature_luminose.py` e alcuni strumenti di
`creature_deserto.py`: tutti e tre i file devono stare nella stessa cartella.

USO DENTRO BLENDER (4.2 o piu' recente)
    1. Workspace "Scripting" > Text > Open... > scegli questo file.
    2. Cambia CREATURA qui sotto (oppure lascia "tutte") e premi Run Script.

USO DA RIGA DI COMANDO
    blender --background --python creature_neve.py -- \\
            --creatura orso --salva orso.blend --render orso.png
"""

import bpy
import bmesh
import importlib.util
import math
import os
import random
import sys
from math import cos, pi, radians, sin

from mathutils import Matrix, Vector
from mathutils import noise as mnoise

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# "orso", "pinguino", "renna", "volpe", "leopardo", "yeti", "civetta",
# "pupazzo" oppure "tutte"
CREATURA = "tutte"

# "EEVEE" oppure "CYCLES"
MOTORE = "EEVEE"

# ============================================================================
# Infrastruttura condivisa
# ============================================================================


def _carica(nome):
    if nome in sys.modules:
        return sys.modules[nome]
    qui = os.path.dirname(os.path.abspath(__file__))
    percorso = os.path.join(qui, nome + ".py")
    if not os.path.exists(percorso):
        raise RuntimeError("Metti %s.py nella stessa cartella di questo script." % nome)
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


CL = _carica("creature_luminose")
DS = _carica("creature_deserto")
TAU = CL.TAU
V = Vector
ellipsoid = CL.ellipsoid
capsule = CL.capsule
ball = CL.ball

# verde, ciano, viola (e di nuovo verde: la tavolozza e' circolare)
AURORA = [(0.08, 1.0, 0.42), (0.03, 0.85, 1.0), (0.1, 1.0, 0.72), (0.5, 0.2, 1.0), (0.08, 1.0, 0.42)]


# ============================================================================
# STRUMENTI
# ============================================================================

def side_name(sx):
    return "L" if sx < 0 else "R"


def rgb_mix(nb, fac, a, b):
    """Miscela di due colori (nodo Mix RGBA, Blender 3.4+)."""
    mx = nb.node('ShaderNodeMix', data_type='RGBA')
    nb.set(mx, 0, fac)
    for idx, col in ((6, a), (7, b)):
        if isinstance(col, bpy.types.NodeSocket):
            nb.link(col, mx.inputs[idx])
        else:
            nb.set(mx, idx, col)
    return mx.outputs[2]


def hair_shader(nb, surface, color, rough=0.35):
    """Sui peli del sistema particellare usa il Principled Hair BSDF (il pelo
    bianco resta bianco anche se folto); sulla pelle lo shader normale."""
    hi = nb.node('ShaderNodeHairInfo')
    hb = nb.node('ShaderNodeBsdfHairPrincipled')
    try:
        hb.parametrization = 'COLOR'
    except (TypeError, AttributeError):
        pass
    nb.set(hb, 'Color', color)
    nb.set(hb, 'Roughness', rough)
    nb.set(hb, 'Radial Roughness', 0.5)
    nb.set(hb, 'Coat', 0.1)
    return nb.mix_shader(hi.outputs['Is Strand'], surface, hb.outputs[0])


def looped_time(nb, cycles):
    """Valore che cresce di `cycles` unita' in ANIM_FRAMES frame: usato con
    FRACT da' un'animazione che si ripete perfettamente."""
    return nb.value(0.0, "frame*%.6f" % (cycles / CL.ANIM_FRAMES))


def snow_lump(name, center, radius, mat, seed=0, lump=0.1, melt=0.0, squash=1.0,
              stretch=(1.0, 1.0), ground=0.0, sub=4):
    """Palla di neve irregolare (goffa, 'fatta a mano'); melt > 0 la fa
    afflosciare e allargare alla base come neve bagnata che si scioglie."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub if CL.DETTAGLIO > 0.6 else sub - 1, radius=1.0)
    off = V((seed * 1.71, seed * 0.93, seed * 2.37))
    c = V(center)
    for v in bm.verts:
        d = v.co.normalized()
        n = mnoise.fractal(d * 1.7 + off, 0.6, 2.0, 3) + 0.35 * mnoise.noise(d * 4.5 + off)
        p = d * radius * (1.0 + lump * n)
        p.x *= stretch[0]
        p.y *= stretch[1]
        p.z *= squash
        if melt:
            h = (d.z + 1.0) * 0.5                     # 0 in basso, 1 in alto
            spread = melt * max(0.0, 0.5 - h) / 0.5
            p.x *= 1.0 + 1.3 * spread
            p.y *= 1.0 + 1.3 * spread
            p.z -= radius * 0.35 * spread
        p = p + c
        if p.z < ground + 0.004:
            p.z = ground + 0.004
        v.co = p
    return CL.mesh_object(name, bm, mat)


def ring_points(center, normal, radius, n=24, up=(0, 0, 1)):
    fr = CL.frame_matrix(V(center), V(up), V(normal))
    return [fr @ V((radius * cos(TAU * i / n), radius * sin(TAU * i / n), 0.0)) for i in range(n)]


def inside(bvh, p):
    loc, nor, _i, _d = bvh.find_nearest(p)
    return loc is not None and (p - loc).dot(nor) < 0.0


# ============================================================================
# MATERIALI DELLA NEVE
# ============================================================================

def m_aurora_fur(name, base=(0.8, 0.85, 0.9), palette=AURORA, strength=2.2, pulse=None):
    """Pelliccia a fibra ottica: onde di luce verde/ciano/viola che scorrono sul
    corpo (rampa colori animata + bordo Fresnel). Sul pelo (sistema
    particellare) la luce cresce verso la punta di ogni pelo, come in una fibra."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    obj = tc.outputs['Object']
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(obj, sep.inputs[0])
    nz = nb.node('ShaderNodeTexNoise', noise_dimensions='4D')
    nb.set(nz, 'Scale', 2.0)
    nb.set(nz, 'Detail', 3.0)
    nb.link(obj, nz.inputs['Vector'])
    CL.add_driver(nz.inputs['W'], "default_value", "0.7*sin(frame*%.6f)" % (TAU / CL.ANIM_FRAMES))
    # tende di luce che scorrono lungo il corpo (2 onde per ciclo)
    s = nb.math('ADD', nb.math('MULTIPLY', sep.outputs['Y'], 1.7), nb.math('MULTIPLY', sep.outputs['Z'], 1.1))
    s = nb.math('ADD', s, nb.math('MULTIPLY', nz.outputs['Fac'], 1.6))
    s = nb.math('SUBTRACT', s, looped_time(nb, 2.0))
    tri = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', s), 0.5)), 2.0)
    curtain = nb.maprange(tri, 0.12, 0.95, 0.12, 1.0)
    # colore che cambia: verde -> ciano -> viola
    cf = nb.math('FRACT', nb.math('ADD', nb.math('ADD', nb.math('MULTIPLY', nz.outputs['Fac'], 0.9),
                                                 nb.math('MULTIPLY', sep.outputs['X'], 0.5)), looped_time(nb, 1.0)))
    col = nb.ramp(cf, [(i / (len(palette) - 1), c) for i, c in enumerate(palette)])
    hair = nb.node('ShaderNodeHairInfo')
    fiber = nb.maprange(hair.outputs['Intercept'], 0.0, 1.0, 0.3, 1.0, smooth=False)
    rim = nb.maprange(nb.fresnel(0.35), 0.25, 0.9, 0.0, 1.0)
    amt = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', curtain, fiber), nb.math('MULTIPLY', rim, 0.6)),
                  nb.glow(strength, pulse))
    bsdf = nb.principled(base=base, rough=0.55, sheen=1.0, sheen_tint=(0.7, 0.95, 1.0), sss=0.2,
                         sss_radius=(0.6, 0.9, 1.0), spec=0.4)
    surf = hair_shader(nb, bsdf.outputs[0], base)
    nb.output(nb.add_shader(surf, nb.emission(col, amt)))
    nb.bake_output("RBX_COLOR", nb.emission(rgb_mix(nb, nb.math('MULTIPLY', curtain, 0.45), base, col), 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(col, curtain))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = 0.6
    mat["rbx_emit_strength"] = float(strength)
    mat["rbx_highlight"] = list(palette[1][:3])
    mat["rbx_cycle"] = {"pal": [list(c) for c in palette[:-1]], "cyc": 1.0, "ph": 0.0}
    CL.diffuse_display(mat, base)
    return mat


def m_two_tone(name, dark, light, mask_fn, rough=0.5, sheen=0.5, frost=0.0):
    """Piumaggio / pelo a due colori: mask_fn(nb, sep) -> 0 = scuro, 1 = chiaro
    (sep = coordinate XYZ nello spazio della creatura)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    mask = mask_fn(nb, sep)
    col = rgb_mix(nb, mask, dark, light)
    if frost:
        vo = nb.voronoi(tc.outputs['Object'], 90.0, 'F1')
        bw = nb.node('ShaderNodeRGBToBW')
        nb.link(vo.outputs['Color'], bw.inputs[0])
        speck = nb.math('MULTIPLY', nb.maprange(bw.outputs[0], 1.0 - frost, 1.0), 0.8)
        col = rgb_mix(nb, speck, col, (0.85, 0.92, 1.0))
    nz = nb.noise(tc.outputs['Object'], 60.0, 6.0, 0.6)
    bsdf = nb.principled(base=col, rough=rough, sheen=sheen, sheen_tint=(0.8, 0.9, 1.0), spec=0.5, coat=0.3)
    nb.set(bsdf, 'Normal', nb.bump(nz.outputs['Fac'], 0.2, 0.01))
    nb.output(bsdf.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = rough
    CL.diffuse_display(mat, dark)
    return mat


def m_bulb_glass(name, tint, glow, strength=6.0, pulse=None, center=0.85):
    """Vetro spesso con la luce dentro: miscela di Glass BSDF ed Emission
    (al centro vince l'emissione, sui bordi i riflessi del vetro)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    glass = nb.node('ShaderNodeBsdfGlass', {'Color': tint, 'Roughness': 0.04, 'IOR': 1.5})
    f = nb.facing(0.45)
    core = nb.maprange(f, 0.0, 0.85, center, 0.08)
    s = nb.glow(strength, pulse)
    em = nb.emission(glow, s)
    nb.output(nb.mix_shader(core, glass.outputs[0], em))
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = list(glow)
    mat["rbx_transp"] = 0.3
    CL.diffuse_display(mat, glow)
    return mat


def m_ice(name, tint=(0.72, 0.9, 1.0), glow=(0.4, 0.75, 1.0), glow_str=0.08, crack_scale=4.0):
    """Ghiaccio purissimo: Transmission con Roughness variabile (zone lisce e
    zone smerigliate) e sottili crepe bianche all'interno."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    obj = tc.outputs['Object']
    nz = nb.noise(obj, 5.0, 6.0, 0.6)
    vo = nb.voronoi(obj, crack_scale, 'DISTANCE_TO_EDGE')
    crack = nb.math('MULTIPLY', nb.maprange(vo.outputs['Distance'], 0.018, 0.004),
                    nb.maprange(nb.noise(obj, 3.0, 3.0, 0.5).outputs['Fac'], 0.42, 0.58))
    rough = nb.math('ADD', nb.maprange(nz.outputs['Fac'], 0.35, 0.7, 0.02, 0.3), nb.math('MULTIPLY', crack, 0.5))
    ice = nb.principled(base=tint, rough=rough, trans=1.0, ior=1.31, spec=0.6, coat=0.7, coat_rough=0.03)
    frost = nb.principled(base=(0.92, 0.96, 1.0), rough=0.6)
    shader = nb.mix_shader(nb.math('MULTIPLY', crack, 0.85), ice.outputs[0], frost.outputs[0])
    edge = nb.maprange(nb.fresnel(0.3), 0.2, 1.0, 0.0, 1.0)
    shader = nb.add_shader(shader, nb.emission(glow, nb.math('MULTIPLY', edge, nb.glow(glow_str))))
    nb.output(shader)
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = list(tint)
    mat["rbx_transp"] = 0.45
    CL.diffuse_display(mat, tint)
    return mat


def m_snow(name, wet=0.0, rbx="Snow"):
    """Neve: bianca e azzurrina, soffice (subsurface) e irregolare; wet > 0 la
    rende bagnata e lucida, come mezza sciolta."""
    mat = CL.m_body(name, (0.8, 0.86, 0.96), rough=0.6 - 0.35 * wet, sss=0.35, sss_radius=(0.5, 0.75, 1.0),
                    coat=wet * 0.6, coat_rough=0.12, spec=0.5 + 0.2 * wet, bump=(9.0, 0.45, 'noise'))
    mat["rbx_material"] = rbx
    mat["rbx_color"] = [0.86, 0.9, 0.97]
    return mat


def m_frost_feather(name, base=(0.92, 0.93, 0.96), bar=(0.55, 0.57, 0.62), glow=(0.7, 0.9, 1.0),
                    strength=3.0, bars=0.0, pulse=None):
    """Piuma bianca bordata di cristalli di ghiaccio luminosi. L'emissione e'
    limitata ai bordi e alla punta della piuma (maschera dalle UV) e rinforzata
    di taglio dal Fresnel. UV: u attraverso la piuma, v dalla radice alla punta."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    au = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5)), 2.0)
    zone = nb.math('MAXIMUM', nb.maprange(au, 0.68, 0.9), nb.maprange(v, 0.8, 0.94))
    zone = nb.math('MULTIPLY', zone, nb.maprange(v, 0.25, 0.45))
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('MULTIPLY', u, 7.0), cmb.inputs[0])
    nb.link(nb.math('MULTIPLY', v, 16.0), cmb.inputs[1])
    vo = nb.voronoi(cmb.outputs[0], 1.0, 'DISTANCE_TO_EDGE')
    facets = nb.maprange(vo.outputs['Distance'], 0.0, 0.15, 0.35, 1.0)
    cryst = nb.math('MULTIPLY', zone, facets)
    rimf = nb.maprange(nb.fresnel(0.3), 0.0, 0.7, 0.55, 1.2)
    col = base
    if bars:
        b = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', v, 4.0)), 0.5))
        bm_ = nb.math('MULTIPLY', nb.maprange(b, 0.12, 0.06), bars)
        bm_ = nb.math('MULTIPLY', bm_, nb.maprange(v, 0.3, 0.5))
        col = rgb_mix(nb, bm_, base, bar)
    rachis = nb.math('MULTIPLY', nb.maprange(au, 0.05, 0.02), nb.maprange(v, 0.95, 0.5))
    col = rgb_mix(nb, nb.math('MULTIPLY', rachis, 0.4), col, bar)
    bsdf = nb.principled(base=col, rough=0.55, sheen=0.8, sheen_tint=(0.85, 0.95, 1.0), spec=0.35)
    s = nb.glow(strength, pulse)
    em = nb.emission(glow, nb.math('MULTIPLY', rimf, s))
    nb.output(nb.mix_shader(cryst, bsdf.outputs[0], em))
    nb.bake_output("RBX_COLOR", nb.mix_shader(cryst, nb.emission(col, 1.0), nb.emission(glow, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(cryst, nb.emission((0, 0, 0), 1.0), nb.emission(glow, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_emit_strength"] = float(strength)
    CL.diffuse_display(mat, base)
    return mat


def m_halo_cycle(name, strength, cycles, phase=0.0, softness=2.0):
    """Come CL.m_halo (volume luminoso), ma con il colore che fa il giro
    dell'arcobaleno."""
    mat = CL.m_halo(name, (1.0, 0.0, 0.0), strength, softness=softness)
    nt = mat.node_tree
    em = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeEmission')
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Color'].default_value = (1.0, 0.0, 0.0, 1.0)
    hs.inputs['Fac'].default_value = 1.0
    CL.add_driver(hs.inputs['Hue'], "default_value",
                  "fmod(frame*%.6f+%.4f,1.0)" % (cycles / CL.ANIM_FRAMES, phase + 0.5))
    nt.links.new(hs.outputs['Color'], em.inputs['Color'])
    mat["rbx_cycle"] = {"pal": [list(c) for c in CL.ARCOBALENO], "cyc": float(cycles), "ph": float(phase)}
    return mat


# ============================================================================
# SCENA DELLA NEVE: cielo con l'aurora, neve che luccica
# ============================================================================

def setup_snow_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Notte_Polare")
    sc.world = w
    if CL.BL < (5, 0, 0):
        w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    L = nt.links.new

    def node(t, **kw):
        n = nt.nodes.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def math(op, a, b):
        n = node('ShaderNodeMath', operation=op)
        for i, x in enumerate((a, b)):
            if isinstance(x, bpy.types.NodeSocket):
                L(x, n.inputs[i])
            else:
                n.inputs[i].default_value = x
        return n.outputs[0]

    def mapr(x, a, b, c=0.0, d=1.0):
        n = node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        L(x, n.inputs['Value'])
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = c
        n.inputs['To Max'].default_value = d
        return n.outputs[0]

    tc = node('ShaderNodeTexCoord')
    sep = node('ShaderNodeSeparateXYZ')
    L(tc.outputs['Generated'], sep.inputs[0])
    z = sep.outputs['Z']
    # tende dell'aurora: bande ondulate lungo l'orizzonte, rigate da raggi verticali
    az = math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    cv = node('ShaderNodeCombineXYZ')
    L(math('MULTIPLY', az, 1.3), cv.inputs[0])
    L(math('MULTIPLY', z, 0.6), cv.inputs[1])
    nz = node('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 2.0
    nz.inputs['Detail'].default_value = 3.0
    L(cv.outputs[0], nz.inputs['Vector'])
    t = node('ShaderNodeValue')
    CL.add_driver(t.outputs[0], "default_value", "frame*%.6f" % (TAU / CL.ANIM_FRAMES))
    ph = math('ADD', math('ADD', math('MULTIPLY', az, 3.0), math('MULTIPLY', nz.outputs['Fac'], 5.0)), t.outputs[0])
    band = mapr(math('SINE', ph, 0.0), 0.1, 0.95)
    rv = node('ShaderNodeCombineXYZ')
    L(math('MULTIPLY', az, 40.0), rv.inputs[0])
    L(math('MULTIPLY', z, 1.5), rv.inputs[1])
    rn = node('ShaderNodeTexNoise')
    rn.inputs['Scale'].default_value = 1.0
    rn.inputs['Detail'].default_value = 2.0
    L(rv.outputs[0], rn.inputs['Vector'])
    rays = mapr(rn.outputs['Fac'], 0.35, 0.7, 0.35, 1.0)
    height = math('MULTIPLY', mapr(z, -0.02, 0.03), mapr(z, 0.5, 0.12))
    aur = math('MULTIPLY', math('MULTIPLY', band, rays), height)
    ramp = node('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.03
    cr.elements[0].color = (0.05, 1.0, 0.45, 1)
    cr.elements[1].position = 0.3
    cr.elements[1].color = (0.5, 0.15, 1.0, 1)
    L(z, ramp.inputs[0])
    # stelle
    vo = node('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 260.0
    L(tc.outputs['Generated'], vo.inputs['Vector'])
    bw = node('ShaderNodeRGBToBW')
    L(vo.outputs['Color'], bw.inputs[0])
    star = math('MULTIPLY', mapr(vo.outputs['Distance'], 0.09, 0.02), mapr(bw.outputs[0], 0.8, 0.95))
    star = math('MULTIPLY', star, mapr(z, 0.02, 0.2))
    # cielo scuro, un po' piu' chiaro all'orizzonte
    sky = node('ShaderNodeValToRGB')
    sky.color_ramp.elements[0].position = 0.0
    sky.color_ramp.elements[0].color = (0.006, 0.01, 0.022, 1)
    sky.color_ramp.elements[1].position = 0.5
    sky.color_ramp.elements[1].color = (0.0015, 0.002, 0.007, 1)
    L(z, sky.inputs[0])
    mix1 = node('ShaderNodeMix', data_type='RGBA', blend_type='ADD')
    L(math('MULTIPLY', aur, 0.11), mix1.inputs[0])
    L(sky.outputs[0], mix1.inputs[6])
    L(ramp.outputs[0], mix1.inputs[7])
    mix2 = node('ShaderNodeMix', data_type='RGBA', blend_type='ADD')
    L(math('MULTIPLY', star, 0.35), mix2.inputs[0])
    L(mix1.outputs[2], mix2.inputs[6])
    mix2.inputs[7].default_value = (0.8, 0.88, 1.0, 1.0)
    bg = node('ShaderNodeBackground')
    L(mix2.outputs[2], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    out = node('ShaderNodeOutputWorld')
    L(bg.outputs[0], out.inputs['Surface'])
    return w


def setup_snow_ground(size=200.0):
    mat = CL.new_material("Neve_Notte")
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    obj = tc.outputs['Object']
    drift = nb.noise(obj, 0.3, 4.0, 0.55)
    fine = nb.noise(obj, 30.0, 3.0, 0.5)
    col = nb.ramp(drift.outputs['Fac'], [(0.3, (0.42, 0.5, 0.68)), (0.7, (0.62, 0.7, 0.86))])
    bsdf = nb.principled(base=col, rough=0.62, spec=0.5, sss=0.2, sss_radius=(0.5, 0.75, 1.0))
    h = nb.math('ADD', nb.math('MULTIPLY', drift.outputs['Fac'], 0.8), nb.math('MULTIPLY', fine.outputs['Fac'], 0.25))
    nb.set(bsdf, 'Normal', nb.bump(h, 0.3, 0.02))
    vo = nb.voronoi(obj, 160.0, 'F1')
    bw = nb.node('ShaderNodeRGBToBW')
    nb.link(vo.outputs['Color'], bw.inputs[0])
    glit = nb.math('MULTIPLY', nb.maprange(bw.outputs[0], 0.975, 0.99), nb.maprange(vo.outputs['Distance'], 0.3, 0.08))
    nb.output(nb.add_shader(bsdf.outputs[0], nb.emission((0.75, 0.88, 1.0), nb.math('MULTIPLY', glit, 2.5))))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    return CL.mesh_object("Terreno_Neve", bm, mat, smooth=False)


# ============================================================================
# 01  ORSO-AURORA
# ============================================================================

def build_bear():
    DS.texspace("Orso")
    K = 1.65
    m_fur = m_aurora_fur("Orso_Pelliccia_Aurora", strength=2.4, pulse=(0.7, 1.3, 1, 0.0))
    m_eye = CL.m_body("Orso_Occhi", (0.005, 0.005, 0.01), rough=0.05, coat=1.0, emit=(0.1, 0.9, 1.0), emit_str=0.4)
    m_nose = CL.m_body("Orso_Naso", (0.01, 0.01, 0.015), rough=0.2, coat=0.8)
    m_claw = CL.m_body("Orso_Artigli", (0.03, 0.03, 0.035), rough=0.3, coat=0.5)
    m_wing = CL.m_wing("Orso_Ali_Aurora",
                       [(0.0, (0.08, 1.0, 0.45)), (0.5, (0.03, 0.85, 1.0)), (0.85, (0.4, 0.3, 1.0)),
                        (1.0, (0.5, 0.3, 1.0))],
                       alpha=0.03, membrane_str=0.8,
                       vein_ramp=[(0.0, (0.5, 1.0, 0.7)), (1.0, (0.6, 0.9, 1.0))], vein_str=3.2,
                       radial=(8, 0.07), cross=(3, 0.04), edge=0.07, v_mix=1.0, facing_mix=0.35,
                       distort=0.06, spots=[(0.52, 0.56, 0.1, True)], pulse=(0.6, 1.4, 1, 0.5))

    E = [ellipsoid((0, 0.08, 0.8), 0.33 * K, (0.95, 1.5, 0.85)),
         ellipsoid((0, -0.3, 0.86), 0.29 * K, (1.0, 1.0, 1.0)),
         ellipsoid((0, 0.5, 0.8), 0.29 * K, (1.0, 1.05, 1.0)),
         capsule((0, -0.45, 0.88), (0, -0.72, 0.8), 0.155 * K),
         ellipsoid((0, -0.82, 0.8), 0.15 * K, (0.95, 1.2, 0.9)),
         capsule((0, -0.92, 0.76), (0, -1.1, 0.7), 0.08 * K),
         ball((0, 0.86, 0.84), 0.06 * K)]
    for sx in (-1, 1):
        E += [ellipsoid((0.09 * sx, -0.77, 0.94), 0.042 * K, (1.0, 0.6, 1.0)),
              capsule((0.18 * sx, -0.32, 0.72), (0.19 * sx, -0.38, 0.14), 0.11 * K),
              ellipsoid((0.19 * sx, -0.43, 0.06), 0.1 * K, (1.0, 1.35, 0.55)),
              capsule((0.18 * sx, 0.52, 0.72), (0.19 * sx, 0.57, 0.14), 0.12 * K),
              ellipsoid((0.19 * sx, 0.52, 0.06), 0.1 * K, (1.0, 1.35, 0.55))]
    body = CL.metaball_mesh("Orso_Corpo", E, m_fur, res=0.03)
    CL.add_fur(body, 0, count=15000, length=0.055, children=10, radius=0.005, clump=0.15)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.84, 0.8))
    for sx in (-1, 1):
        CL.make_eye("Orso_Occhio_" + side_name(sx), bvh, head_c, (0.42 * sx, -1.0, 0.4), 0.024, m_eye,
                    None, None, sink=0.3, flat=0.8)
    nl, _nn = CL.surface_hit(bvh, V((0, -1.05, 0.72)), (0, -1, 0.15))
    CL.sphere("Orso_Naso", nl, (0.045, 0.032, 0.032), m_nose)
    for sx in (-1, 1):
        for y0 in (-0.43, 0.52):
            for k in range(4):
                x = 0.19 * sx + (k - 1.5) * 0.032
                b = V((x, y0 - 0.15, 0.03))
                CL.cone_between("Orso_Artiglio_%s%d_%d" % (side_name(sx), int(y0 > 0), k), b,
                                b + V((0, -0.035, -0.02)), 0.009, 0.0, m_claw, 6)

    # ali da falena notturna fatte di pura luce boreale
    fore = [(-32, 0.3), (-18, 0.72), (-4, 0.95), (10, 1.0), (24, 0.88), (40, 0.64), (54, 0.36), (62, 0.12)]
    hind = [(38, 0.18), (54, 0.5), (72, 0.66), (90, 0.64), (108, 0.46), (120, 0.16)]
    CL.wing_pair("Orso_AlaAnt", fore, m_wing, (0.13, -0.26, 1.12), elev=36, sweep=-6, roll=0, rings=12,
                 flap=(9, 1, 0.0), n=64)
    CL.wing_pair("Orso_AlaPost", hind, m_wing, (0.13, -0.12, 1.1), elev=28, sweep=4, roll=0, rings=10,
                 flap=(9, 1, 0.35), n=48)

    # luci: tre colori dell'aurora che si accendono in sequenza
    for k, (col, y) in enumerate(((AURORA[0], -0.45), (AURORA[1], 0.05), (AURORA[3], 0.5))):
        CL.add_light("Orso_Luce_Aurora_%d" % k, 'POINT', (0, y, 1.6), 12.0, col, 0.4,
                     pulse=(2.0, 16.0, 1, -TAU * k / 3))
    CL.add_light("Orso_Luce_Terra", 'POINT', (0, -0.3, 0.2), 4.0, (0.2, 0.9, 1.0), 0.4, pulse=(2.0, 6.0, 2, 0.0))


# ============================================================================
# 02  PINGUINO-CRISTALLO
# ============================================================================

def build_penguin():
    DS.texspace("Pinguino")
    K = 1.65
    blue = (0.3, 0.72, 1.0)

    def pmask(nb, sep):
        # davanti e' bianco (sotto la testa), il resto nero
        front = nb.maprange(sep.outputs['Y'], -0.05, -0.15)
        return nb.math('MULTIPLY', front, nb.maprange(sep.outputs['Z'], 0.54, 0.48))

    m_body = m_two_tone("Pinguino_Piumaggio", (0.012, 0.014, 0.022), (0.86, 0.9, 0.95), pmask, rough=0.45,
                        sheen=0.6, frost=0.03)
    m_glass = m_bulb_glass("Pinguino_Pancia_Vetro", (0.82, 0.94, 1.0), blue, 1.0, pulse=(0.7, 1.4, 1, 0.0),
                           center=0.3)
    m_core = CL.m_emit("Pinguino_Nucleo_Luce", (0.45, 0.82, 1.0), 3.5, pulse=(2.5, 5.0, 1, 0.0))
    m_rib = CL.m_body("Pinguino_Segmenti_Vetro", (0.75, 0.9, 1.0), rough=0.25, coat=1.0,
                      emit=(0.55, 0.85, 1.0), emit_str=1.2, emit_pulse=(0.8, 1.6, 1, 0.0))
    m_halo = CL.m_halo("Pinguino_Alone", blue, 0.5, pulse=(0.3, 0.7, 1, 0.0))
    m_white = CL.m_body("Pinguino_Anello_Occhio", (0.9, 0.93, 0.97), rough=0.4)
    m_eye = CL.m_body("Pinguino_Occhi", (0.005, 0.005, 0.01), rough=0.05, coat=1.0, emit=blue, emit_str=0.3)
    m_beak = CL.m_body("Pinguino_Becco", (0.03, 0.03, 0.035), rough=0.3, coat=0.6)
    m_orange = CL.m_body("Pinguino_Arancio", (0.95, 0.42, 0.06), rough=0.45)
    m_ice = CL.m_body("Pinguino_Lastra_Ghiaccio", (0.45, 0.7, 0.9), rough=0.04, coat=1.0, spec=0.8,
                      bump=(3.0, 0.15, 'scales'))
    m_ice["rbx_material"] = "Ice"
    m_ice["rbx_color"] = [0.55, 0.78, 0.95]
    m_wing = CL.m_wing("Pinguino_Ali_Brinate", [(0.0, (0.75, 0.9, 1.0)), (1.0, (0.95, 0.98, 1.0))],
                       alpha=0.25, membrane_str=0.25, vein_ramp=[(0.0, (0.6, 0.85, 1.0)), (1.0, (0.9, 0.97, 1.0))],
                       vein_str=2.2, radial=(5, 0.08), edge=0.08, cells=(28.0, 0.035, 0.9), v_mix=1.0,
                       facing_mix=0.3)

    # lastra di ghiaccio su cui scivola
    DS.lathe("Pinguino_Lastra", [(0.62, 0.0), (0.64, 0.012), (0.6, 0.022)], m_ice, seg=64, cap_top=True)

    E = [ellipsoid((0, 0.0, 0.28), 0.23 * K, (1.0, 0.92, 1.2)),
         ellipsoid((0, 0.02, 0.13), 0.21 * K, (1.05, 1.0, 0.7)),
         ball((0, -0.04, 0.57), 0.145 * K),
         ellipsoid((0, 0.21, 0.1), 0.05 * K, (1.0, 1.6, 0.5))]
    body = CL.metaball_mesh("Pinguino_Corpo", E, m_body, res=0.016)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.04, 0.57))

    # pancia: bulbo di vetro spesso con la luce dentro, incastonato nel corpo
    bc, ba = V((0, -0.19, 0.27)), V((0.2, 0.13, 0.23))
    CL.sphere("Pinguino_Pancia", bc, tuple(ba), m_glass, seg=48, rings=24)
    core = CL.sphere("Pinguino_Nucleo", bc + V((0, -0.03, 0)), (0.08, 0.05, 0.1), m_core)
    CL.no_shadow(core)
    halo = CL.sphere("Pinguino_Alone", bc + V((0, -0.08, 0)), (0.3, 0.26, 0.32), m_halo)
    CL.no_shadow(halo)
    # cornice di piume dove il vetro entra nel corpo
    rim = []
    for i in range(32):
        a = TAU * i / 32
        dx, dz = cos(a), sin(a)
        p = None
        for k in range(60):
            t = k / 59 * (pi / 2)                 # dall'apice verso il bordo dell'ellissoide
            q = bc + V((ba.x * sin(t) * dx, -ba.y * cos(t), ba.z * sin(t) * dz))
            if inside(bvh, q):
                p = q
                break
        rim.append(p if p is not None else bc + V((ba.x * dx, 0, ba.z * dz)))
    CL.tube("Pinguino_Cornice", rim + [rim[0]], 0.018, m_body, bevel_res=2, poly=True)
    # segmenti trasversali, come l'addome di una lucciola
    for k, zo in enumerate((-0.13, -0.05, 0.03, 0.11)):
        f = math.sqrt(max(0.0, 1.0 - (zo / ba.z) ** 2))
        pts = []
        for i in range(25):
            a = radians(-90 + 180 * i / 24)
            q = bc + V((ba.x * f * sin(a), -ba.y * f * cos(a) * 1.015, zo))
            if not inside(bvh, q):
                pts.append(q)
        if len(pts) > 2:
            CL.tube("Pinguino_Segmento_%d" % k, pts, 0.006, m_rib, bevel_res=1, poly=True)

    # occhi con l'anello bianco, becco
    for sx in (-1, 1):
        s = side_name(sx)
        loc, nor = CL.surface_hit(bvh, head_c, (0.55 * sx, -0.8, 0.25))
        e = CL.sphere("Pinguino_Occhio_" + s, (0, 0, 0), 1.0, m_eye, seg=20, rings=10)
        CL.orient(e, loc - nor * 0.004, nor, scale=(0.02, 0.02, 0.014))
        ring = ring_points(loc + nor * 0.002, nor, 0.03, 20)
        CL.tube("Pinguino_AnelloOcchio_" + s, ring + [ring[0]], 0.006, m_white, bevel_res=1, poly=True)
    bl, bn = CL.surface_hit(bvh, head_c + V((0, 0, -0.02)), (0, -1, -0.1))
    CL.cone_between("Pinguino_Becco", bl - bn * 0.02, bl + V((0, -0.09, -0.02)), 0.028, 0.002, m_beak, 12)
    for sx in (-1, 1):
        CL.sphere("Pinguino_Macchia_Becco_" + side_name(sx), bl + V((0.018 * sx, -0.012, -0.004)),
                  (0.006, 0.02, 0.008), m_orange, seg=12, rings=6)

    # pinne tozze e zampe palmate
    for sx in (-1, 1):
        s = side_name(sx)
        DS.segment("Pinguino_Pinna_" + s, (0.23 * sx, 0.02, 0.3), (0.4 * sx, 0.1, -1.0), 0.055, 0.26, m_body,
                   flat=0.3, up=(sx, 0, 0))
        foot = V((0.08 * sx, -0.1, 0.035))
        CL.sphere("Pinguino_Zampa_" + s, foot, (0.05, 0.075, 0.018), m_orange, rot=(0, 0, 12 * sx))
        for k, ang in enumerate((-25, 0, 25)):
            d = V((sin(radians(ang + 10 * sx)), -cos(radians(ang + 10 * sx)), 0))
            CL.sphere("Pinguino_Dito_%s%d" % (s, k), foot + d * 0.065 + V((0, 0, -0.008)), (0.018, 0.03, 0.01),
                      m_orange, rot=(0, 0, -(ang + 10 * sx)), seg=12, rings=6)

    # piccole ali da insetto brinate
    small = [(-15, 0.1), (-5, 0.24), (8, 0.3), (22, 0.27), (36, 0.16), (45, 0.05)]
    CL.wing_pair("Pinguino_Aluccia", small, m_wing, (0.1, 0.12, 0.44), elev=34, sweep=52, roll=15, rings=6,
                 flap=(24, 20, 0.0))
    CL.wing_pair("Pinguino_Aluccia2", small, m_wing, (0.1, 0.16, 0.38), elev=20, sweep=74, roll=15, rings=6,
                 flap=(24, 20, 1.2))

    CL.add_light("Pinguino_Luce_Pancia", 'POINT', bc + V((0, -0.2, 0)), 14.0, blue, 0.08, pulse=(9.0, 16.0, 1, 0.0))
    sp = CL.add_light("Pinguino_Luce_Ghiaccio", 'SPOT', bc + V((0, -0.16, -0.05)), 40.0, blue, 0.05,
                      spot_size=110, pulse=(25.0, 45.0, 1, 0.0))
    CL.aim(sp, V((0, -0.55, 0.0)))


# ============================================================================
# 03  RENNA-COMETA
# ============================================================================

def m_antenna(name, color, strength, pulse=None, rings=26.0):
    """Corno-antenna: emissione fortissima con anelli (segmenti da antenna di
    insetto) lungo la lunghezza (UV u)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    b = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', sep.outputs['X'], rings)), 0.5))
    band = nb.maprange(b, 0.5, 0.3, 0.55, 1.0)
    s = nb.glow(strength, pulse)
    nb.output(nb.emission(color, nb.math('MULTIPLY', band, s)))
    CL.diffuse_display(mat, color)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(color)
    if pulse:
        mat["rbx_pulse"] = [pulse[0] / pulse[1], 1.0, float(pulse[2]), float(pulse[3])]
    return mat


def build_reindeer():
    DS.texspace("Renna")
    K = 1.65
    white = (0.8, 0.9, 1.0)
    m_fur = CL.m_body("Renna_Pelo", (0.26, 0.21, 0.18), rough=0.7, sheen=1.0, sheen_tint=(0.8, 0.85, 1.0),
                      mottle=((0.4, 0.35, 0.31), 3.5), rim=(0.6, 0.8, 1.0), rim_str=0.55)
    m_mane = CL.m_body("Renna_Criniera", (0.75, 0.74, 0.72), rough=0.75, sheen=1.0, sheen_tint=(0.8, 0.9, 1.0),
                       rim=(0.7, 0.85, 1.0), rim_str=0.5)
    m_hoof = CL.m_body("Renna_Zoccoli", (0.04, 0.035, 0.03), rough=0.35, coat=0.6)
    m_eye = CL.m_body("Renna_Occhi", (0.01, 0.01, 0.015), rough=0.05, coat=1.0, emit=white, emit_str=0.4)
    m_nose = CL.m_body("Renna_Naso", (0.05, 0.045, 0.05), rough=0.3, coat=0.5)
    m_ant = m_antenna("Renna_Corna_Antenne", (0.72, 0.88, 1.0), 16.0, pulse=(12.0, 18.0, 1, 0.0))
    m_ant_halo = CL.m_halo("Renna_Alone_Corna", (0.6, 0.82, 1.0), 1.4, pulse=(1.0, 1.8, 1, 0.0))
    m_tail = CL.m_halo("Renna_Coda_Cometa", (0.5, 0.75, 1.0), 1.6, pulse=(1.0, 2.0, 1, 0.0))
    m_flake = CL.m_sparkle("Renna_Granelli_Neve", (0.75, 0.9, 1.0), 9.0, twinkle=5.0)
    m_star = CL.m_emit("Renna_Fiocchi", (0.8, 0.92, 1.0), 6.0, pulse=(3.0, 8.0, 2, 0.0))

    # --- corpo slanciato su zampe lunghe, al passo -------------------------------
    E = [ellipsoid((0, 0.05, 0.95), 0.2 * K, (1.0, 2.1, 1.05)),
         ellipsoid((0, -0.3, 0.96), 0.2 * K, (1.0, 1.0, 1.15)),
         ellipsoid((0, 0.38, 0.98), 0.19 * K, (1.0, 1.0, 1.05)),
         capsule((0, -0.42, 1.05), (0, -0.62, 1.34), 0.095 * K),
         ellipsoid((0, -0.7, 1.42), 0.085 * K, (0.95, 1.25, 0.9)),
         capsule((0, -0.74, 1.4), (0, -0.9, 1.3), 0.055 * K),
         ball((0, 0.58, 1.03), 0.04 * K)]
    legs = {  # (anca/spalla, ginocchio, zoccolo)
        "AntL": ((-0.11, -0.3, 0.86), (-0.11, -0.44, 0.52), (-0.11, -0.5, 0.08)),
        "AntR": ((0.11, -0.3, 0.86), (0.11, -0.2, 0.52), (0.11, -0.12, 0.08)),
        "PostL": ((-0.11, 0.4, 0.88), (-0.11, 0.3, 0.52), (-0.11, 0.42, 0.08)),
        "PostR": ((0.11, 0.4, 0.88), (0.11, 0.56, 0.52), (0.11, 0.66, 0.08)),
    }
    for a, b, c in legs.values():
        E += [capsule(a, b, 0.055 * K), capsule(b, c, 0.032 * K)]
    for sx in (-1, 1):
        E.append(ellipsoid((0.085 * sx, -0.66, 1.5), 0.03 * K, (1.8, 0.6, 0.8)))
    body = CL.metaball_mesh("Renna_Corpo", E, m_fur, res=0.018)
    CL.add_fur(body, 0, count=7000, length=0.028, children=8, radius=0.004, clump=0.2)
    for key, (_a, _b, c) in legs.items():
        CL.sphere("Renna_Zoccolo_" + key, V(c) + V((0, -0.02, -0.04)), (0.04, 0.05, 0.04), m_hoof)
    mane = CL.sphere("Renna_Criniera", (0, -0.47, 1.06), (0.1, 0.12, 0.16), m_mane, rot=(-30, 0, 0))
    CL.add_fur(mane, 0, count=1400, length=0.09, children=10, radius=0.005, clump=0.35)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.72, 1.42))
    for sx in (-1, 1):
        CL.make_eye("Renna_Occhio_" + side_name(sx), bvh, head_c, (0.8 * sx, -0.6, 0.25), 0.02, m_eye,
                    None, None, sink=0.3, flat=0.8)
    nl, _nn = CL.surface_hit(bvh, V((0, -0.9, 1.3)), (0, -1, -0.1))
    CL.sphere("Renna_Naso", nl, (0.035, 0.025, 0.025), m_nose)

    # --- corna = colossali antenne da insetto, coperte di peli sensoriali -----------
    halo_pts = []
    for sx in (-1, 1):
        s = side_name(sx)

        def P(x, y, z):
            return V((x * sx, y, z))
        branches = [
            [P(0.05, -0.66, 1.49), P(0.16, -0.62, 1.66), P(0.3, -0.52, 1.86), P(0.36, -0.36, 2.05),
             P(0.32, -0.22, 2.22), P(0.24, -0.16, 2.34)],                                   # asta
            [P(0.1, -0.64, 1.58), P(0.14, -0.78, 1.66), P(0.12, -0.9, 1.78), P(0.08, -0.95, 1.86)],  # pugnale
            [P(0.29, -0.53, 1.84), P(0.36, -0.64, 1.98), P(0.36, -0.72, 2.12)],
            [P(0.36, -0.38, 2.03), P(0.46, -0.42, 2.18), P(0.5, -0.5, 2.3)],
            [P(0.33, -0.25, 2.18), P(0.42, -0.24, 2.34), P(0.44, -0.3, 2.46)],
            [P(0.26, -0.17, 2.32), P(0.25, -0.08, 2.44), P(0.2, -0.04, 2.52)],
        ]
        for k, ctrl in enumerate(branches):
            pts = DS.spline(ctrl, CL.det(18 if k == 0 else 10, 5))
            r0 = 0.03 if k == 0 else 0.017
            radii = [r0 * (1.0 - 0.7 * i / (len(pts) - 1)) for i in range(len(pts))]
            ob, _fr, _l = DS.sweep_mesh("Renna_Corno_%s%d" % (s, k), pts, radii, m_ant, ring=10)
            CL.no_shadow(ob)
            CL.add_fur(ob, 0, count=260 if k == 0 else 120, length=0.03, children=4, radius=0.002, clump=0.0)
            halo_pts += pts[::3]
    for sx in (-1, 1):
        c = V((0.3 * sx, -0.45, 2.05))
        h = CL.sphere("Renna_Alone_Corna_" + side_name(sx), c, (0.34, 0.42, 0.42), m_ant_halo)
        CL.no_shadow(h)
    CL.add_light("Renna_Luce_Corna", 'POINT', (0, -0.5, 2.1), 30.0, (0.7, 0.85, 1.0), 0.5,
                 pulse=(22.0, 34.0, 1, 0.0))

    # --- scia di "neve luminosa" come la coda di una cometa ------------------------
    path = DS.spline([(0.0, 0.45, 1.12), (0.05, 0.85, 1.25), (0.18, 1.35, 1.42), (0.38, 1.85, 1.55),
                      (0.62, 2.35, 1.62)], 30)
    radii = [0.1 + 0.42 * (i / 29) ** 0.8 for i in range(30)]
    em, _fr, _l = DS.sweep_mesh("Renna_Scia_Emettitore", path, radii, m_tail, ring=12)
    grain = CL.sphere("Renna_Granello", path[3], 0.018, m_flake, seg=6, rings=3)
    CL.particle_scatter(em, grain, 2600, size=1.0, size_random=0.8, emit_from='VOLUME', seed=11)
    for i in range(6):
        t = (i + 0.5) / 6
        j = int(t * 29)
        hs = CL.sphere("Renna_Scia_%d" % i, path[j], radii[j] * 1.25, m_tail)
        CL.no_shadow(hs)
    random.seed(17)
    w = TAU / CL.ANIM_FRAMES
    for i in range(26):
        t = random.uniform(0.02, 1.0) ** 0.8
        j = min(29, int(t * 29))
        off = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
        loc = path[j] + off * radii[j] * random.uniform(0.1, 0.8)
        f = CL.sphere("Renna_Fiocco_%02d" % i, loc, random.uniform(0.012, 0.022), m_star, seg=4, rings=2)
        CL.no_shadow(f)
        cyc = random.choice((1, 2))
        ph = random.uniform(0, TAU)
        CL.add_driver(f, "location", "%.4f+0.05*sin(frame*%.6f+%.3f)" % (loc.z, w * cyc, ph), 2,
                      meta=dict(tipo='bob', amp=0.05, cyc=cyc, ph=ph))
    CL.add_light("Renna_Luce_Scia", 'POINT', path[12], 10.0, (0.6, 0.8, 1.0), 0.6, pulse=(6.0, 12.0, 1, 0.5))
    CL.add_light("Renna_Luce_Terra", 'POINT', (0, -0.2, 0.3), 3.0, (0.7, 0.85, 1.0), 0.4, pulse=(2.0, 4.0, 1, 0.0))


# ============================================================================
# 04  VOLPE-GHIACCIAIO
# ============================================================================

def build_ice_fox():
    DS.texspace("Volpe")
    K = 1.65
    cold = (0.55, 0.85, 1.0)
    m_ice_body = m_ice("Volpe_Corpo_Ghiaccio", tint=(0.78, 0.93, 1.0), glow_str=0.35)
    m_heart = CL.m_emit("Volpe_Cuore_Luce", (0.6, 0.9, 1.0), 9.0, pulse=(2.0, 14.0, 2, 0.0, True))
    m_heart_glow = CL.m_halo("Volpe_Alone_Cuore", cold, 3.0, pulse=(0.6, 4.0, 2, 0.0, True))
    m_eye = CL.m_radial_glow("Volpe_Occhi", [(0.0, (1.0, 1.0, 1.0)), (0.5, (0.5, 0.85, 1.0)),
                                             (1.0, (0.1, 0.4, 0.9))], 3.0)
    m_nose = CL.m_body("Volpe_Naso", (0.05, 0.1, 0.16), rough=0.1, coat=1.0)
    m_spike = DS.m_crystal("Volpe_Punte_Ghiaccio", (0.75, 0.92, 1.0), cold, 0.6, pulse=(0.3, 0.9, 2, 0.5))
    m_wing = CL.m_wing("Volpe_Ali_Ghiacciate", [(0.0, (0.6, 0.9, 1.0)), (1.0, (0.9, 0.97, 1.0))],
                       alpha=0.08, membrane_str=0.15, vein_ramp=[(0.0, (0.55, 0.85, 1.0)), (1.0, (0.85, 0.95, 1.0))],
                       vein_str=2.4, radial=(6, 0.06), cross=(3, 0.04), edge=0.06, cells=(34.0, 0.03, 0.8),
                       v_mix=1.0, facing_mix=0.4)

    E = [ellipsoid((0, 0.04, 0.42), 0.12 * K, (0.9, 2.1, 0.95)),
         ellipsoid((0, -0.19, 0.45), 0.125 * K, (0.95, 1.05, 1.12)),
         ellipsoid((0, 0.27, 0.44), 0.115 * K, (1.0, 1.0, 1.0)),
         capsule((0, -0.24, 0.5), (0, -0.35, 0.64), 0.065 * K),
         ellipsoid((0, -0.39, 0.66), 0.085 * K, (1.0, 1.05, 0.9)),
         capsule((0, -0.44, 0.645), (0, -0.53, 0.615), 0.03 * K)]
    for sx in (-1, 1):
        E += [capsule((0.06 * sx, -0.19, 0.38), (0.06 * sx, -0.22, 0.2), 0.03 * K),
              capsule((0.06 * sx, -0.22, 0.2), (0.06 * sx, -0.25, 0.035), 0.02 * K),
              ellipsoid((0.06 * sx, -0.27, 0.02), 0.022 * K, (1.0, 1.4, 0.6)),
              capsule((0.07 * sx, 0.28, 0.4), (0.08 * sx, 0.36, 0.22), 0.036 * K),
              capsule((0.08 * sx, 0.36, 0.22), (0.07 * sx, 0.31, 0.035), 0.021 * K),
              ellipsoid((0.07 * sx, 0.29, 0.02), 0.022 * K, (1.0, 1.4, 0.6))]
    body = CL.metaball_mesh("Volpe_Corpo", E, m_ice_body, res=0.014)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.4, 0.66))
    for sx in (-1, 1):
        s = side_name(sx)
        CL.cone_between("Volpe_Orecchio_" + s, (0.045 * sx, -0.37, 0.7), (0.075 * sx, -0.35, 0.82), 0.035, 0.002,
                        m_ice_body, 12)
        CL.make_eye("Volpe_Occhio_" + s, bvh, head_c, (0.5 * sx, -1.0, 0.3), 0.018, m_eye, None, None,
                    sink=0.35, flat=0.7)
    nl, _nn = CL.surface_hit(bvh, V((0, -0.53, 0.61)), (0, -1, 0.1))
    CL.sphere("Volpe_Naso", nl, (0.015, 0.012, 0.012), m_nose)
    # coda folta di ghiaccio
    tail = DS.spline([(0, 0.34, 0.46), (0.1, 0.52, 0.38), (0.2, 0.58, 0.22), (0.2, 0.44, 0.1), (0.1, 0.3, 0.07)],
                     CL.det(36, 12))
    nt = len(tail)
    DS.sweep_mesh("Volpe_Coda", tail, [0.03 + 0.045 * sin(pi * min(1.0, i / (nt * 0.8))) for i in range(nt)],
                  m_ice_body, ring=14)

    # il cuore: nucleo di luce fredda e pulsante (come la lanterna di una lucciola)
    for k, (y, r) in enumerate(((-0.14, 0.05), (-0.05, 0.047), (0.04, 0.04))):
        h = CL.sphere("Volpe_Cuore_%d" % k, (0, y, 0.44), (r, r * 0.9, r * 1.1), m_heart)
        CL.no_shadow(h)
    g = CL.sphere("Volpe_Alone_Cuore", (0, -0.05, 0.44), (0.1, 0.16, 0.1), m_heart_glow)
    CL.no_shadow(g)
    CL.add_light("Volpe_Luce_Cuore", 'POINT', (0, -0.06, 0.24), 6.0, cold, 0.1, pulse=(1.0, 8.0, 2, 0.0))

    # piccole punte di ghiaccio lungo la schiena
    for i in range(7):
        t = i / 6
        loc, nor = CL.surface_hit(bvh, V((0, -0.2 + 0.46 * t, 0.42)), (0, 0, 1))
        if loc is None:
            continue
        me = DS.crystal_mesh("Volpe_Punta_%d" % i, 0.05 + 0.03 * sin(pi * t), 0.012, seed=40 + i)
        me.materials.append(m_spike)
        ob = bpy.data.objects.new(me.name, me)
        CL.link(ob)
        DS.place_on(ob, loc - nor * 0.004, (nor + V((0, 0.35, 0))).normalized())

    # minuscole ali da libellula ghiacciate
    small = [(-12, 0.08), (-4, 0.2), (6, 0.26), (16, 0.24), (26, 0.14), (32, 0.05)]
    CL.wing_pair("Volpe_Ala", small, m_wing, (0.05, -0.14, 0.53), elev=24, sweep=48, roll=18, rings=6,
                 flap=(18, 36, 0.0))
    CL.wing_pair("Volpe_Ala2", small, m_wing, (0.05, -0.07, 0.52), elev=16, sweep=70, roll=18, rings=6,
                 flap=(18, 36, 1.4))


# ============================================================================
# 05  LEOPARDO-VALANGA
# ============================================================================

def m_leopard(name, fur=(0.74, 0.73, 0.7), fur2=(0.6, 0.6, 0.6), glow=(0.08, 0.92, 1.0), strength=3.5,
              pulse=None):
    """Pelliccia del leopardo delle nevi: le rosette (anelli spezzati di una
    trama Voronoi) sono chiazze di scaglie d'insetto che emettono luce ciano;
    il resto e' pelo chiaro con subsurface. Sul pelo la luce e' piu' forte
    alla radice, come se filtrasse da sotto."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    obj = tc.outputs['Object']
    vec = DS._coords(nb, distort=0.2)
    vo = nb.voronoi(vec, 8.5, 'F1', randomness=0.85)
    d = vo.outputs['Distance']
    ring = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', d, 0.3)), 0.11, 0.05)
    gaps = nb.maprange(nb.noise(vec, 18.0, 2.0, 0.5).outputs['Fac'], 0.36, 0.48)
    spot = nb.math('MULTIPLY', nb.maprange(d, 0.1, 0.05), 0.6)
    mask = nb.math('MAXIMUM', nb.math('MULTIPLY', ring, gaps), spot)
    sc = nb.voronoi(obj, 90.0, 'DISTANCE_TO_EDGE')
    scales = nb.maprange(sc.outputs['Distance'], 0.0, 0.12, 0.35, 1.0)
    em_mask = nb.math('MULTIPLY', mask, scales)
    nz = nb.noise(obj, 6.0, 5.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.35, fur2), (0.65, fur)])
    col = rgb_mix(nb, mask, col, (0.05, 0.12, 0.14))
    hair = nb.node('ShaderNodeHairInfo')
    through = nb.maprange(hair.outputs['Intercept'], 0.0, 1.0, 1.0, 0.25, smooth=False)
    bsdf = nb.principled(base=col, rough=0.6, sheen=1.0, sheen_tint=(0.85, 0.95, 1.0), sss=0.3,
                         sss_radius=(1.0, 0.9, 0.8), spec=0.4)
    s = nb.glow(strength, pulse)
    em = nb.emission(glow, nb.math('MULTIPLY', nb.math('MULTIPLY', em_mask, through), s))
    nb.output(nb.add_shader(hair_shader(nb, bsdf.outputs[0], col), em))
    nb.bake_output("RBX_COLOR", nb.emission(rgb_mix(nb, mask, col, glow), 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(glow, em_mask))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = 0.6
    mat["rbx_emit_strength"] = float(strength)
    CL.diffuse_display(mat, fur)
    return mat


def build_leopard():
    DS.texspace("Leopardo")
    K = 1.65
    cyan = (0.08, 0.92, 1.0)
    m_fur = m_leopard("Leopardo_Pelliccia_Rosette", strength=3.2, pulse=(0.6, 1.3, 1, 0.0))
    m_eye = CL.m_radial_glow("Leopardo_Occhi", [(0.0, (0.02, 0.05, 0.05)), (0.3, (0.3, 0.8, 0.75)),
                                                (0.8, (0.55, 0.85, 0.7)), (1.0, (0.2, 0.3, 0.3))], 1.2)
    m_pupil = CL.m_body("Leopardo_Pupilla", (0.0, 0.0, 0.0), rough=0.05, coat=1.0)
    m_nose = CL.m_body("Leopardo_Naso", (0.35, 0.22, 0.24), rough=0.35, coat=0.4)
    m_whisk = CL.m_emit("Leopardo_Baffi", (0.7, 0.95, 1.0), 1.2)
    m_bulb = CL.m_body("Leopardo_Bulbo", (0.7, 1.0, 0.95), rough=0.3, sss=1.0, sss_radius=(0.4, 1.0, 1.0),
                       emit=(0.45, 1.0, 0.95), emit_str=6.0, emit_pulse=(3.0, 8.0, 1, 0.0), emit_center=True)
    m_bulb_glow = CL.m_halo("Leopardo_Alone_Bulbo", (0.3, 1.0, 0.95), 2.0, pulse=(1.0, 3.0, 1, 0.0))
    m_band = CL.m_body("Leopardo_Anelli_Bulbo", (0.08, 0.1, 0.1), rough=0.4)

    E = [ellipsoid((0, 0.05, 0.54), 0.19 * K, (1.0, 2.0, 0.92)),
         ellipsoid((0, -0.3, 0.57), 0.19 * K, (1.05, 1.0, 1.1)),
         ellipsoid((0, 0.4, 0.56), 0.18 * K, (1.0, 1.0, 1.0)),
         capsule((0, -0.38, 0.64), (0, -0.53, 0.72), 0.11 * K),
         ellipsoid((0, -0.59, 0.74), 0.125 * K, (1.1, 1.0, 0.95)),
         ellipsoid((0, -0.7, 0.7), 0.065 * K, (1.25, 0.9, 0.8))]
    for sx in (-1, 1):
        E += [ellipsoid((0.085 * sx, -0.55, 0.87), 0.034 * K, (1.0, 0.5, 0.9)),
              capsule((0.12 * sx, -0.32, 0.48), (0.12 * sx, -0.36, 0.15), 0.08 * K),
              ellipsoid((0.12 * sx, -0.41, 0.055), 0.072 * K, (1.0, 1.3, 0.6)),
              capsule((0.13 * sx, 0.42, 0.52), (0.14 * sx, 0.52, 0.28), 0.09 * K),
              capsule((0.14 * sx, 0.52, 0.28), (0.13 * sx, 0.46, 0.08), 0.06 * K),
              ellipsoid((0.13 * sx, 0.43, 0.055), 0.072 * K, (1.0, 1.3, 0.6))]
    body = CL.metaball_mesh("Leopardo_Corpo", E, m_fur, res=0.02)
    CL.add_fur(body, 0, count=11000, length=0.035, children=10, radius=0.004, clump=0.15)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.6, 0.74))
    for sx in (-1, 1):
        CL.make_eye("Leopardo_Occhio_" + side_name(sx), bvh, head_c, (0.5 * sx, -1.0, 0.25), 0.028, m_eye,
                    m_pupil, None, pupil=(0.35, 0.7), sink=0.3, flat=0.75)
    nl, _nn = CL.surface_hit(bvh, V((0, -0.73, 0.71)), (0, -1, 0.3))
    CL.sphere("Leopardo_Naso", nl, (0.027, 0.017, 0.015), m_nose)
    for sx in (-1, 1):
        for k in range(3):
            a = V((0.035 * sx, -0.74, 0.685 - 0.008 * k))
            b = a + V((0.2 * sx, -0.05 + 0.03 * k, 0.02 - 0.03 * k))
            w = CL.tube("Leopardo_Baffo_%s%d" % (side_name(sx), k), [a, a.lerp(b, 0.5) + V((0, 0, 0.01)), b],
                        [0.002, 0.0015, 0.0005], m_whisk, bevel_res=1)
            CL.no_shadow(w)

    # coda spessa e lunghissima che finisce in un bulbo di lucciola
    nt = CL.det(48, 16)
    tail = DS.spline([(0, 0.55, 0.58), (0.03, 0.85, 0.5), (0.18, 1.12, 0.36), (0.38, 1.22, 0.46),
                      (0.46, 1.12, 0.7), (0.4, 1.0, 0.86)], nt)
    radii = [0.085 - 0.012 * i / (nt - 1) for i in range(nt)]
    tob, _fr, _l = DS.sweep_mesh("Leopardo_Coda", tail, radii, m_fur, ring=16)
    CL.add_fur(tob, 0, count=3600, length=0.06, children=10, radius=0.004, clump=0.2)
    tip = tail[-1]
    tdir = (tail[-1] - tail[-4]).normalized()
    bulbs = []
    for k, (off, r) in enumerate(((0.05, 0.075), (0.13, 0.085), (0.22, 0.078), (0.3, 0.055))):
        c = tip + tdir * off
        bulbs.append(DS.segment("Leopardo_Bulbo_%d" % k, c, tdir, r, 0.1, m_bulb, flat=1.0))
        if k < 3:
            DS.segment("Leopardo_Anello_%d" % k, c + tdir * 0.045, tdir, r * 0.9, 0.012, m_band, flat=1.0)
    bc = tip + tdir * 0.16
    h = CL.sphere("Leopardo_Alone_Bulbo", bc, 0.26, m_bulb_glow)
    CL.no_shadow(h)
    CL.add_light("Leopardo_Luce_Bulbo", 'POINT', bc, 14.0, (0.4, 1.0, 0.95), 0.08, pulse=(7.0, 18.0, 1, 0.0))
    CL.add_light("Leopardo_Luce_Rosette", 'POINT', (0, -0.1, 1.1), 4.0, cyan, 0.5, pulse=(2.0, 5.0, 1, 0.0))


# ============================================================================
# 06  FALENA-YETI
# ============================================================================

def m_yeti_fur(name, fur=(0.94, 0.93, 0.97), skin=(0.22, 0.03, 0.2), glow=(0.85, 0.05, 0.75),
               strength=2.2, pulse=None):
    """Pelliccia bianca, lunga e arruffata. Il corpo sotto brilla di magenta e
    la luce si vede anche alla radice di ogni pelo, sfumando verso la punta."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    hi = nb.node('ShaderNodeHairInfo')
    root = nb.maprange(hi.outputs['Intercept'], 0.0, 0.3, 1.0, 0.0)
    skin_bsdf = nb.principled(base=skin, rough=0.45, sss=0.5, sss_radius=(1.0, 0.2, 0.8), coat=0.3)
    surf = hair_shader(nb, skin_bsdf.outputs[0], fur, rough=0.4)
    s = nb.glow(strength, pulse)
    nb.output(nb.add_shader(surf, nb.emission(glow, nb.math('MULTIPLY', root, s))))
    CL.diffuse_display(mat, fur)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(glow)
    return mat


def m_fur_fog(name, color=(0.95, 0.92, 1.0), glow=(0.85, 0.05, 0.75), density=5.0, strength=0.5, pulse=None):
    """Nebbia bianca (Volume Scatter) intorno al corpo, illuminata da dentro:
    la luce magenta 'filtra' attraverso la pelliccia."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    nb.output(nb.transparent())
    pv = nb.node('ShaderNodeVolumePrincipled')
    nb.set(pv, 'Color', color)
    nb.set(pv, 'Density', density)
    nb.set(pv, 'Anisotropy', 0.25)
    nb.set(pv, 'Emission Color', glow)
    nb.set(pv, 'Emission Strength', nb.glow(strength, pulse))
    nb.link(pv.outputs[0], nb.out.inputs['Volume'])
    CL.set_transparent(mat)
    CL.diffuse_display(mat, color)
    mat["rbx_kind"] = "ghost"
    mat["rbx_color"] = [1.0, 0.82, 0.97]
    mat["rbx_highlight"] = list(glow)
    return mat


def shaggy(md):
    """Pelo lungo e arruffato (da yeti)."""
    if md is None:
        return
    ps = md.particle_system.settings
    for attr, val in (('roughness_1', 0.06), ('roughness_2', 0.12), ('roughness_endpoint', 0.08),
                      ('roughness_2_size', 1.5), ('clump_shape', 0.3)):
        if hasattr(ps, attr):
            setattr(ps, attr, val)


def build_yeti_moth():
    DS.texspace("Yeti")
    K = 1.65
    mag = (0.85, 0.05, 0.75)
    m_fur = m_yeti_fur("Yeti_Pelliccia", strength=1.2, pulse=(0.5, 1.8, 1, 0.0))
    m_fog = m_fur_fog("Yeti_Bagliore_Nella_Pelliccia", density=2.5, pulse=(0.04, 0.2, 1, 0.0))
    m_wing = CL.m_wing("Yeti_Ali_Carnose",
                       [(0.0, (0.1, 0.02, 0.1)), (0.5, (0.2, 0.04, 0.2)), (1.0, (0.36, 0.08, 0.34))],
                       alpha=0.93, membrane_str=0.12,
                       vein_ramp=[(0.0, (1.0, 0.08, 0.75)), (1.0, (0.75, 0.15, 1.0))], vein_str=2.6,
                       radial=(10, 0.05), cross=(4, 0.035), edge=0.04, cells=(9.0, 0.03, 0.15), v_mix=1.0,
                       facing_mix=0.2, distort=0.08, spots=[(0.6, 0.6, 0.13, True)], pulse=(0.4, 1.5, 1, 0.0))
    m_eye = CL.m_body("Yeti_Occhi", (0.03, 0.0, 0.03), rough=0.05, coat=1.0, emit=mag, emit_str=0.9)
    m_leg = CL.m_body("Yeti_Zampe", (0.85, 0.83, 0.9), rough=0.8, sheen=1.0, sheen_tint=(1.0, 0.8, 1.0),
                      rim=mag, rim_str=0.35)
    m_ant = CL.m_body("Yeti_Antenne", (0.8, 0.78, 0.85), rough=0.6, sheen=1.0, emit=mag, emit_str=0.35)

    E = [ball((0, -0.47, 0.36), 0.12 * K),
         ellipsoid((0, -0.25, 0.38), 0.17 * K, (1.0, 1.15, 0.95)),
         ellipsoid((0, 0.06, 0.34), 0.16 * K, (0.95, 1.3, 0.9)),
         ellipsoid((0, 0.34, 0.3), 0.13 * K, (0.9, 1.25, 0.85)),
         ellipsoid((0, 0.56, 0.27), 0.09 * K, (0.85, 1.2, 0.8))]
    body = CL.metaball_mesh("Yeti_Corpo", E, m_fur, res=0.02)
    md = CL.add_fur(body, 0, count=10000, length=0.2, children=12, radius=0.006, clump=0.45)
    shaggy(md)
    if md is not None:                    # pelo corto sulla testa, lungo sul corpo
        vg = body.vertex_groups.new(name="Lunghezza_Pelo")
        for v in body.data.vertices:
            vg.add([v.index], 0.3 if v.co.y < -0.36 else 1.0, 'REPLACE')
        md.particle_system.vertex_group_length = vg.name
    E2 = [dict(e, r=e['r'] * 1.4) for e in E]
    fog = CL.metaball_mesh("Yeti_Nebbia", E2, m_fog, res=0.03)
    CL.no_shadow(fog)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.47, 0.36))
    for sx in (-1, 1):
        CL.make_eye("Yeti_Occhio_" + side_name(sx), bvh, head_c, (0.8 * sx, -0.7, 0.15), 0.08, m_eye,
                    None, None, sink=0.15, flat=0.95)

    # antenne piumate enormi (bipettinate)
    for sx in (-1, 1):
        s = side_name(sx)
        shaft = DS.spline([(0.05 * sx, -0.53, 0.47), (0.16 * sx, -0.7, 0.6), (0.3 * sx, -0.8, 0.7),
                           (0.42 * sx, -0.82, 0.74)], 16)
        CL.tube("Yeti_Antenna_" + s, shaft, [0.012 - 0.006 * i / 15 for i in range(16)], m_ant, bevel_res=2)
        tans, norms, binors = DS.frames_along(shaft)
        for i in range(2, 16):
            ln = 0.1 * (1.0 - 0.75 * i / 15)
            for side in (-1, 1):
                d = (binors[i] * side * 0.8 + tans[i] * 0.5 - V((0, 0, 0.15))).normalized()
                CL.tube("Yeti_Filamento_%s%02d%s" % (s, i, "a" if side < 0 else "b"),
                        [shaft[i], shaft[i] + d * ln], [0.004, 0.0015], m_ant, bevel_res=1, poly=True)

    # sei zampe pelose
    for sx in (-1, 1):
        for k, y in enumerate((-0.33, -0.23, -0.12)):
            a = V((0.1 * sx, y, 0.28))
            b = V((0.3 * sx, y - 0.06 + 0.05 * k, 0.26))
            c = V((0.4 * sx, y - 0.1 + 0.1 * k, 0.02))
            CL.tube("Yeti_Zampa_%s%d" % (side_name(sx), k), [a, b, c], [0.035, 0.03, 0.02], m_leg, bevel_res=3)

    # ali enormi e carnose, con ciuffi di pelo alla base
    fore = [(-30, 0.45), (-15, 1.05), (0, 1.25), (15, 1.2), (30, 1.0), (45, 0.7), (58, 0.35), (66, 0.12)]
    hind = [(35, 0.3), (55, 0.75), (75, 0.9), (95, 0.85), (115, 0.6), (130, 0.2)]
    CL.wing_pair("Yeti_AlaAnt", fore, m_wing, (0.12, -0.3, 0.46), elev=12, sweep=-4, rings=14, cup=0.05,
                 flap=(7, 1, 0.0), n=72, scallop=(0.05, 9))
    CL.wing_pair("Yeti_AlaPost", hind, m_wing, (0.12, -0.18, 0.44), elev=8, sweep=6, rings=12, cup=0.05,
                 flap=(7, 1, 0.3), n=56, scallop=(0.06, 7))
    for sx in (-1, 1):
        tuft = CL.sphere("Yeti_Ciuffo_" + side_name(sx), (0.2 * sx, -0.24, 0.45), (0.13, 0.16, 0.09), m_fur)
        shaggy(CL.add_fur(tuft, 0, count=900, length=0.12, children=12, radius=0.006, clump=0.45))

    CL.add_light("Yeti_Luce_Sotto", 'POINT', (0, -0.1, 0.12), 5.0, mag, 0.3, pulse=(1.5, 7.0, 1, 0.0))
    CL.add_light("Yeti_Luce_Luna", 'POINT', (0.3, -0.9, 1.2), 25.0, (0.8, 0.85, 1.0), 0.6)
    for sx in (-1, 1):
        CL.add_light("Yeti_Luce_Ala_" + side_name(sx), 'POINT', (0.8 * sx, -0.1, 0.9), 3.0, (0.8, 0.15, 1.0),
                     0.4, pulse=(0.5, 4.0, 1, 0.0))


# ============================================================================
# 07  CIVETTA-BUFERA
# ============================================================================

def build_snowy_owl():
    DS.texspace("Civetta")
    K = 1.65
    ice = (0.55, 0.85, 1.0)
    m_down = CL.m_body("Civetta_Piumino", (0.85, 0.87, 0.9), rough=0.7, sheen=0.8, sheen_tint=ice,
                       rim=ice, rim_str=0.3, bump=(90.0, 0.2, 'noise'))
    m_f = m_frost_feather("Civetta_Piuma_Cristallo", strength=3.0, bars=0.45, pulse=(0.7, 1.2, 2, 0.0))
    m_f2 = m_frost_feather("Civetta_Piuma_Petto", strength=2.2, pulse=(0.7, 1.2, 2, 1.0))
    m_disc = CL.m_body("Civetta_Disco_Facciale", (0.9, 0.92, 0.95), rough=0.75, sheen=0.6,
                       bump=(40.0, 0.25, 'scales'), rim=ice, rim_str=0.5)
    m_eye = CL.m_radial_glow("Civetta_Occhio_Faro", [(0.0, (1.0, 1.0, 1.0)), (0.3, (0.7, 0.92, 1.0)),
                                                     (0.65, (0.2, 0.6, 1.0)), (0.9, (0.05, 0.25, 0.9)),
                                                     (1.0, (0.01, 0.05, 0.3))], 3.5, pulse=(2.8, 4.2, 1, 0.0))
    m_lid = CL.m_body("Civetta_Palpebre", (0.02, 0.02, 0.025), rough=0.4)
    m_beak = CL.m_body("Civetta_Becco", (0.05, 0.05, 0.06), rough=0.3, coat=0.6)
    m_sn = m_snow("Civetta_Neve")
    m_rock = CL.m_body("Civetta_Roccia", (0.07, 0.08, 0.1), rough=0.85, mottle=((0.14, 0.15, 0.18), 3.0),
                       bump=(8.0, 0.5, 'warts'))
    m_icicle = DS.m_crystal("Civetta_Ghiaccioli", (0.8, 0.93, 1.0), ice, 0.4)
    m_flash = CL.m_halo("Civetta_Lampo_Bufera", (0.85, 0.93, 1.0), 4.0, pulse=(0.05, 5.0, 1, 0.0, True))

    # roccia innevata con ghiaccioli
    rk = DS.rock("Civetta_Roccia", (0, 0.05, 0.2), (0.55, 0.45, 0.3), m_rock, seed=6, rough=0.28)
    rb = CL.bvh_of(rk)
    top, _n = CL.surface_hit(rb, V((0, 0.05, 0.2)), (0, 0, 1))
    h = top.z - 0.02
    snow_lump("Civetta_Neve_Roccia", (0, 0.05, top.z - 0.04), 0.45, m_sn, seed=4, lump=0.12, squash=0.2,
              stretch=(1.15, 0.95))
    for i in range(7):
        a = TAU * (i + 0.3) / 7
        loc, nor = CL.surface_hit(rb, V((0, 0.05, 0.2)), (cos(a), sin(a), 0.05))
        if loc is None:
            continue
        me = DS.crystal_mesh("Civetta_Ghiacciolo_%d" % i, 0.08 + 0.04 * (i % 3), 0.018, sides=5, tip=0.6,
                             seed=60 + i)
        me.materials.append(m_icicle)
        ob = bpy.data.objects.new(me.name, me)
        CL.link(ob)
        DS.place_on(ob, loc + V((0, 0, 0.01)), (0, 0, -1), nor)

    # corpo, testa tonda e piume a tegola con i bordi di cristallo
    E = [ellipsoid((0, 0.02, h + 0.34), 0.25 * K, (1.0, 0.92, 1.18)),
         ellipsoid((0, 0.0, h + 0.2), 0.21 * K, (1.05, 0.95, 0.8)),
         ellipsoid((0, -0.01, h + 0.74), 0.24 * K, (1.1, 0.95, 0.88))]
    body = CL.metaball_mesh("Civetta_Corpo", E, m_down, res=0.025)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.01, h + 0.74))
    body_c = V((0, 0.02, h + 0.34))
    f_big = CL.feather_mesh("Civetta_Piuma_M", 0.17, 0.13, m_f, curl=0.12)
    f_small = CL.feather_mesh("Civetta_Piuma_S", 0.13, 0.11, m_f, curl=0.12)
    f_chest = CL.feather_mesh("Civetta_Piuma_P", 0.12, 0.11, m_f2, curl=0.1)

    def face_zone(d, z):
        dd = V((d.x, d.y, 0)).normalized()
        return z > h + 0.56 and dd.y < -0.35

    def chest_zone(d, z):
        dd = V((d.x, d.y, 0)).normalized()
        return dd.y < -0.55

    random.seed(8)
    CL.scatter_feathers("Civetta_PiumaTesta", bvh, head_c, [f_small], rows=6, zr=(h + 0.95, h + 0.6),
                        cols=lambda t: int(10 + 14 * t), skip=face_zone, lift=5, scale=1.0)
    CL.scatter_feathers("Civetta_PiumaDorso", bvh, body_c, [f_big, f_small], rows=8, zr=(h + 0.6, h + 0.1),
                        cols=24, skip=chest_zone, lift=6, scale=1.05)
    CL.scatter_feathers("Civetta_PiumaPetto", bvh, body_c, [f_chest], rows=9, zr=(h + 0.58, h + 0.08), cols=28,
                        skip=lambda d, z: not chest_zone(d, z), lift=4, scale=0.95)

    # dischi facciali, occhi-faro azzurri, becco
    for sx in (-1, 1):
        sd = side_name(sx)
        d = V((0.5 * sx, -1.0, 0.05))
        loc, nor = CL.surface_hit(bvh, head_c, d)
        disc = CL.sphere("Civetta_Disco_" + sd, (0, 0, 0), 1.0, m_disc, seg=32, rings=16)
        CL.orient(disc, loc - nor * 0.035, (nor + V((0, -0.6, 0))).normalized(), scale=(0.19, 0.19, 0.06))
        c = loc + nor * 0.004
        dirv = (nor + V((0, -0.8, 0))).normalized()
        eye = CL.sphere("Civetta_Occhio_" + sd, (0, 0, 0), 1.0, m_eye, seg=40, rings=20)
        CL.orient(eye, c, dirv, scale=(0.095, 0.095, 0.04))
        ring = ring_points(c + dirv * 0.003, dirv, 0.1, 24)
        CL.tube("Civetta_Palpebra_" + sd, ring + [ring[0]], 0.008, m_lid, bevel_res=2, poly=True)
        sp = CL.add_light("Civetta_Faro_" + sd, 'SPOT', c + dirv * 0.05, 18.0, (0.6, 0.85, 1.0), 0.05,
                          spot_size=36, pulse=(12.0, 20.0, 1, 0.0))
        CL.aim(sp, c + dirv * 3.0 + V((0, 0, -1.2)))
    bl, bn = CL.surface_hit(bvh, head_c, (0, -1.0, -0.35))
    CL.cone_between("Civetta_Becco", bl - bn * 0.02, bl + V((0, -0.05, -0.07)), 0.03, 0.002, m_beak, 12)
    for sx in (-1, 1):
        top_f = V((0.1 * sx, -0.06, h + 0.1))
        CL.sphere("Civetta_Zampa_" + side_name(sx), top_f, (0.06, 0.06, 0.06), m_down)
        for k, ang in enumerate((-25, 0, 25)):
            a = radians(ang)
            p0 = top_f + V((0.02 * sin(a), -0.03, -0.04))
            p2 = V((p0.x + 0.05 * sin(a), -0.15, h + 0.0))
            CL.cone_between("Civetta_Artiglio_%s%d" % (side_name(sx), k), p0, p2, 0.012, 0.002, m_beak, 8)

    # ali aperte e sollevate: remiganti, secondarie e copritrici su un perno
    f_prim = CL.feather_mesh("Civetta_Remigante", 0.5, 0.15, m_f, rows=12, curl=0.05)
    f_sec = CL.feather_mesh("Civetta_Secondaria", 0.36, 0.14, m_f, rows=10, curl=0.05)
    f_cov = CL.feather_mesh("Civetta_Copritrice", 0.22, 0.13, m_f, rows=8, curl=0.06)
    up = V((0, 0, 1))
    for sx in (-1, 1):
        sd = side_name(sx)
        out = V((sx, 0.3, 0.0)).normalized()
        n = up.cross(out)
        if n.y > 0:
            n = -n
        n = (n + V((0, 0, 0.15))).normalized()
        S, _nn = CL.surface_hit(bvh, body_c + V((0, 0.04, 0.22)), out)
        S = S - out * 0.06
        W = S + out * 0.3 + up * 0.14
        piv = CL.empty("Civetta_Ala_Perno_" + sd, S, 0.06)
        inv = Matrix.Translation(-S)
        feathers = []

        def feather(name, me, origin, phi_deg, scale, lift):
            phi = radians(phi_deg)
            d = (out * cos(phi) + up * sin(phi)).normalized()
            m = CL.frame_matrix(origin + n * lift, d, n)
            ob = bpy.data.objects.new(name, me)
            ob.matrix_world = m @ Matrix.Diagonal((1.0, scale, 1.0, 1.0))
            CL.link(ob)
            feathers.append(ob)

        for k in range(9):
            t = k / 8
            feather("Civetta_Remigante_%s_%d" % (sd, k), f_prim, W, -5 + 88 * t, 0.85 + 0.3 * sin(pi * t),
                    -0.004 * k)
        for k in range(7):
            t = k / 6
            feather("Civetta_Secondaria_%s_%d" % (sd, k), f_sec, S.lerp(W, 0.15 + 0.85 * t), -80 + 55 * t, 1.0,
                    0.01 + 0.003 * k)
        for row, (ln, lift) in enumerate(((1.0, 0.03), (0.7, 0.05))):
            for k in range(7):
                t = k / 6
                feather("Civetta_Copritrice_%s_%d_%d" % (sd, row, k), f_cov, S.lerp(W, 0.05 + 0.95 * t),
                        -70 + 90 * t, ln, lift)
        for ob in feathers:
            ob.parent = piv
            ob.matrix_parent_inverse = inv
        sign = 1 if sx < 0 else -1
        w = TAU / CL.ANIM_FRAMES
        CL.add_driver(piv, "rotation_euler", "%d*radians(14)*sin(frame*%.6f)" % (sign, w), 1,
                      meta=dict(tipo='rot', amp=sign * radians(14), cyc=1, ph=0.0))

    # il lampo di luce bianca quando le ali sono aperte del tutto
    fl = CL.sphere("Civetta_Lampo", (0, 0.12, h + 0.95), (0.7, 0.45, 0.55), m_flash)
    CL.no_shadow(fl)
    CL.add_light("Civetta_Luce_Lampo", 'POINT', (0, 0.1, h + 1.0), 60.0, (0.85, 0.93, 1.0), 0.6,
                 pulse=(2.0, 90.0, 1, 0.0, True))
    CL.add_light("Civetta_Luce_Piume", 'POINT', (0, -0.6, h + 0.6), 1.5, ice, 0.4, pulse=(0.8, 2.0, 2, 0.0))


# ============================================================================
# 08  IL PUPAZZO DI NEVE "SKIBIDI"
# ============================================================================

def build_snowman():
    DS.texspace("Pupazzo")
    m_sn = m_snow("Pupazzo_Neve_Bagnata", wet=0.7)
    m_coal = CL.m_body("Pupazzo_Carbone", (0.02, 0.02, 0.022), rough=0.85, bump=(40.0, 0.6, 'warts'))
    m_coal["rbx_material"] = "Slate"
    m_mouth = CL.m_body("Pupazzo_Bocca", (0.05, 0.01, 0.02), rough=0.6)
    m_twig = CL.m_body("Pupazzo_Rametti", (0.18, 0.1, 0.05), rough=0.8)
    ph = 0.8                              # al primo fotogramma: fucsia
    m_led = CL.m_hue_cycle("Pupazzo_LED_RGB", 22.0, cycles=12, phase=ph)
    m_led_glow = m_halo_cycle("Pupazzo_Alone_LED", 0.8, cycles=12, phase=ph)
    m_metal = CL.m_body("Pupazzo_LED_Piedini", (0.8, 0.8, 0.82), rough=0.15, metal=1.0)
    m_water = CL.m_body("Pupazzo_Pozzanghera", (0.02, 0.03, 0.05), rough=0.02, coat=1.0, spec=0.9)
    m_water["rbx_material"] = "Glass"
    m_water["rbx_rifl"] = 0.5
    m_leg = CL.m_body("Pupazzo_Zampette", (0.04, 0.04, 0.05), rough=0.3, coat=0.8, rim=(0.8, 0.9, 1.0),
                      rim_str=0.4)
    m_ice = DS.m_crystal("Pupazzo_Gocce_Ghiaccio", (0.85, 0.95, 1.0), (0.6, 0.85, 1.0), 0.3)
    m_wing = CL.m_wing("Pupazzo_Alucce_Mosca", [(0.0, (0.7, 0.8, 0.9)), (1.0, (0.9, 0.95, 1.0))], alpha=0.3,
                       membrane_str=0.15, vein_ramp=[(0.0, (0.2, 0.22, 0.25)), (1.0, (0.4, 0.45, 0.5))],
                       vein_str=0.5, radial=(5, 0.07), cross=(3, 0.05), edge=0.05, cells=(30.0, 0.03, 0.7),
                       v_mix=1.0, facing_mix=0.3)

    # pozzanghera di neve sciolta
    bm = bmesh.new()
    n = 48
    ctr = bm.verts.new((0, 0, 0.004))
    ring = []
    for i in range(n):
        a = TAU * i / n
        r = 0.62 * (1.0 + 0.18 * sin(3 * a + 0.7) + 0.1 * sin(7 * a))
        ring.append(bm.verts.new((r * cos(a), r * sin(a), 0.004)))
    for i in range(n):
        bm.faces.new((ctr, ring[i], ring[(i + 1) % n]))
    CL.mesh_object("Pupazzo_Pozzanghera", bm, m_water, smooth=False)

    # due palle di neve sbilenche, mezze sciolte
    snow_lump("Pupazzo_Palla_Bassa", (0.0, 0.02, 0.27), 0.33, m_sn, seed=1, lump=0.1, melt=0.55, squash=0.85)
    snow_lump("Pupazzo_Palla_Media", (0.05, 0.0, 0.68), 0.23, m_sn, seed=2, lump=0.13, squash=0.92,
              stretch=(1.08, 0.95))
    for i, (x, z) in enumerate(((0.07, 0.8), (0.1, 0.68), (0.06, 0.55))):
        snow_lump("Pupazzo_Bottone_%d" % i, (x + 0.01 * i, -0.21 + 0.015 * i, z), 0.028 + 0.006 * (i == 1),
                  m_coal, seed=10 + i, lump=0.3, sub=2)
    # gocce che colano
    for i, (x, y, z, L) in enumerate(((0.2, -0.1, 0.5, 0.06), (-0.15, -0.12, 0.52, 0.09), (0.02, -0.2, 0.47, 0.05),
                                      (0.12, 0.15, 0.5, 0.07))):
        me = DS.crystal_mesh("Pupazzo_Goccia_%d" % i, L, 0.014, sides=5, tip=0.7, seed=80 + i)
        me.materials.append(m_ice)
        ob = bpy.data.objects.new(me.name, me)
        CL.link(ob)
        DS.place_on(ob, (x, y, z), (0, 0, -1))

    # zampette da mosca congelate e alucce misere ai lati
    for sx in (-1, 1):
        s = side_name(sx)
        a = V((0.24 * sx + 0.05, -0.02, 0.7))
        DS.leg("Pupazzo_Zampetta_" + s, [a, a + V((0.13 * sx, -0.03, 0.06)), a + V((0.22 * sx, -0.06, -0.08)),
                                         a + V((0.26 * sx, -0.08, -0.14))], [0.012, 0.01, 0.007, 0.003], m_leg)
    CL.wing_pair("Pupazzo_Aluccia", [(-15, 0.06), (-5, 0.16), (8, 0.2), (20, 0.17), (30, 0.06)], m_wing,
                 (0.19, 0.12, 0.8), elev=30, sweep=60, roll=40, rings=5, flap=(14, 16, 0.0))

    # COLLO ASSURDAMENTE LUNGO E FLESSIBILE + testa
    base = V((0.04, 0.0, 0.86))
    neck = DS.spline([base, (0.1, -0.03, 1.08), (-0.04, -0.07, 1.33), (0.03, -0.12, 1.56), (0.09, -0.17, 1.72)],
                     CL.det(40, 14))
    rng = random.Random(5)
    radii = [0.07 * (1.0 + 0.12 * sin(i * 1.3) + rng.uniform(-0.05, 0.05)) for i in range(len(neck))]
    nob, _fr, _l = DS.sweep_mesh("Pupazzo_Collo", neck, radii, m_sn, ring=14)
    collar = snow_lump("Pupazzo_Colletto", base + V((0, 0, -0.01)), 0.11, m_sn, seed=7, lump=0.2, squash=0.5, sub=3)
    head_c = neck[-1] + V((0.0, -0.05, 0.13))
    head = snow_lump("Pupazzo_Testa", head_c, 0.17, m_sn, seed=3, lump=0.14, squash=1.05, stretch=(1.05, 0.95))
    hb = CL.bvh_of(head)
    face = []

    def on_head(d, lift=0.0):
        loc, nor = CL.surface_hit(hb, head_c, d)
        return loc + nor * lift, nor

    # occhi di carbone di misure diverse, sopracciglia storte
    for i, (d, r) in enumerate((((-0.42, -1.0, 0.35), 0.032), ((0.38, -1.0, 0.42), 0.046))):
        p, nor = on_head(d)
        face.append(snow_lump("Pupazzo_Occhio_%d" % i, p, r, m_coal, seed=20 + i, lump=0.25, sub=2))
        a, _ = on_head((d[0] - 0.25, -1.0, d[2] + 0.35), 0.005)
        b, _ = on_head((d[0] + 0.25, -1.0, d[2] + (0.5 if i == 0 else 0.2)), 0.005)
        face.append(CL.tube("Pupazzo_Sopracciglio_%d" % i, [a, b], 0.008, m_twig, bevel_res=1))
    # bocca spalancata (sta cantando)
    p, nor = on_head((0.05, -1.0, -0.42))
    mo = CL.sphere("Pupazzo_Bocca", (0, 0, 0), 1.0, m_mouth, seg=20, rings=10)
    CL.orient(mo, p - nor * 0.01, nor, scale=(0.055, 0.045, 0.02))
    face.append(mo)
    for k in range(9):
        a = TAU * k / 9
        q, _ = on_head((0.05 + 0.28 * cos(a), -1.0, -0.42 + 0.22 * sin(a)), 0.004)
        face.append(snow_lump("Pupazzo_Carbone_Bocca_%d" % k, q, 0.014, m_coal, seed=30 + k, lump=0.3, sub=1))
    # NASO: gigantesca lampadina LED da gaming RGB
    p, nor = on_head((0.0, -1.0, 0.02))
    led_prof = [(0.0, -0.02), (0.062, -0.02), (0.062, 0.0), (0.05, 0.004), (0.05, 0.13)]
    led_prof += [(0.05 * cos(radians(a)), 0.13 + 0.05 * sin(radians(a))) for a in range(15, 91, 15)]
    led = DS.lathe("Pupazzo_Naso_LED", led_prof, m_led, seg=32)
    fwd = (nor + V((0, -0.4, -0.15))).normalized()
    DS.place_on(led, p - nor * 0.01, fwd)
    CL.no_shadow(led)
    face.append(led)
    for sx in (-1, 1):
        a = p + V((0.02 * sx, 0, 0))
        face.append(CL.tube("Pupazzo_LED_Piedino_" + side_name(sx), [a, a - fwd * 0.06 + V((0.01 * sx, 0, -0.02))],
                            0.004, m_metal, bevel_res=1))
    tip = p + fwd * 0.17
    g = CL.sphere("Pupazzo_Alone_LED", tip, 0.12, m_led_glow)
    CL.no_shadow(g)
    face.append(g)
    lamp = CL.add_light("Pupazzo_Luce_LED", 'POINT', tip + fwd * 0.2, 6.0, (1, 0, 0), 0.05, pulse=(3.0, 8.0, 6, 0.0))
    CL.color_cycle_light(lamp, 12, ph)
    face.append(lamp)
    lamp2 = CL.add_light("Pupazzo_Luce_LED_Terra", 'POINT', (0.1, -0.6, 0.6), 5.0, (1, 0, 0), 0.3)
    CL.color_cycle_light(lamp2, 12, ph)

    # il collo ondeggia (e la testa ancora di piu')
    head_piv = DS.pivot("Pupazzo_Testa_Perno", neck[-1], [head] + face)
    neck_piv = DS.pivot("Pupazzo_Collo_Perno", base, [nob, collar])
    head_piv.parent = neck_piv
    head_piv.matrix_parent_inverse = Matrix.Translation(-base)
    DS.wobble(neck_piv, 0, 7, 2, 0.0)
    DS.wobble(neck_piv, 1, 9, 1, 1.1)
    DS.wobble(head_piv, 1, 14, 3, 0.4)
    DS.wobble(head_piv, 0, 8, 2, 2.0)


# ============================================================================
# REGISTRO, SCENA E AVVIO
# ============================================================================

CREATURE_NEVE = {
    #  chiave      (collezione,                 funzione,        camera: target, dist, elev, azim, lente)
    "orso":     ("N01_Orso-Aurora",          build_bear,      ((0, -0.05, 0.85), 6.2, 14, 35, 50)),
    "pinguino": ("N02_Pinguino-Cristallo",   build_penguin,   ((0, -0.1, 0.35), 2.6, 12, 25, 50)),
    "renna":    ("N03_Renna-Cometa",         build_reindeer,  ((0, 0.6, 1.3), 7.4, 10, 55, 50)),
    "volpe":    ("N04_Volpe-Ghiacciaio",     build_ice_fox,   ((0, 0.0, 0.42), 2.9, 14, 40, 50)),
    "leopardo": ("N05_Leopardo-Valanga",     build_leopard,   ((0.05, 0.3, 0.55), 4.6, 14, 50, 50)),
    "yeti":     ("N06_Falena-Yeti",          build_yeti_moth, ((0, 0.0, 0.4), 5.4, 30, 25, 50)),
    "civetta":  ("N07_Civetta-Bufera",       build_snowy_owl, ((0, 0.05, 0.95), 4.8, 8, 20, 50)),
    "pupazzo":  ("N08_Pupazzo-Skibidi",      build_snowman,   ((0, -0.05, 1.08), 5.4, 8, 25, 50)),
}

DISPOSIZIONE_NEVE = {
    #  chiave     (x, y, rotazione_z)
    "yeti":     (-5.2, 4.8, 10),
    "orso":     (-1.6, 4.4, 30),
    "renna":    (2.0, 4.9, -30),
    "civetta":  (5.4, 5.6, -20),
    "leopardo": (-4.0, 0.9, 75),
    "volpe":    (-1.4, 0.0, 25),
    "pinguino": (1.0, -0.3, -10),
    "pupazzo":  (3.7, 0.2, -20),
}


def build(which=None, engine=None, clean=None):
    which = (which or CREATURA).lower()
    if clean if clean is not None else CL.PULISCI_SCENA:
        CL.clear_scene()
    setup_snow_world()
    CL.setup_render(engine or MOTORE)
    base = CL.new_collection("Scena_Neve")
    CL.set_collection(base)
    setup_snow_ground()
    CL.setup_moonlight()
    CL.set_collection(None)
    if which == "tutte":
        for k in CREATURE_NEVE:
            x, y, rz = DISPOSIZIONE_NEVE[k]
            CL.build_one(k, (x, y, 0), rot_z=rz, registry=CREATURE_NEVE)
        CL.setup_camera((0.0, 2.5, 0.9), 12.0, 14, 0, 32)
    else:
        if which not in CREATURE_NEVE:
            raise ValueError("Creatura sconosciuta: %s (scegli tra %s o 'tutte')"
                             % (which, ", ".join(CREATURE_NEVE)))
        CL.build_one(which, registry=CREATURE_NEVE)
        tgt, dist, el, az, lens = CREATURE_NEVE[which][2]
        CL.setup_camera(tgt, dist, el, az, lens)
    CL.setup_viewport()
    bpy.context.scene.frame_set(1)


def main():
    CL.build = build            # il main condiviso usa questa funzione
    CL.main()


if __name__ == "__main__":
    main()
