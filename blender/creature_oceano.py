# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE DELL'OCEANO - quarta serie per Blender.

    01  MEDUSA-LANTERNA         (ombrella-addome di lucciola, antenne da falena)
    02  CAVALLUCCIO-NEON        (tatuaggi tribali verde neon, ali frenetiche)
    03  GRANCHIO-FARO           (corazza di roccia viva, faro rotante)
    04  MANTA-LUMINESCENTE      (pinne a ali di falena luna, ocelli pulsanti)
    05  SQUALO-PLASMA           (vasi sanguigni di plasma, quattro ali)
    06  TARTARUGA-FOSFORICA     (guscio di bulbi esagonali che pulsano a onde)
    07  RANA PESCATRICE-ABISSO  (una lucciola intrappolata nell'esca)
    08  IL BLOBFISH "MEWING"    (mascella squadrata e "shhh")

Usa l'infrastruttura di `creature_luminose.py` e gli strumenti di
`creature_deserto.py` e `creature_neve.py`: i quattro file devono stare nella
stessa cartella.

USO DENTRO BLENDER (4.2 o piu' recente)
    1. Workspace "Scripting" > Text > Open... > scegli questo file.
    2. Cambia CREATURA qui sotto (oppure lascia "tutte") e premi Run Script.

USO DA RIGA DI COMANDO
    blender --background --python creature_oceano.py -- \\
            --creatura medusa --salva medusa.blend --render medusa.png
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

# "medusa", "cavalluccio", "granchio", "manta", "squalo", "tartaruga",
# "pescatrice", "blobfish" oppure "tutte"
CREATURA = "tutte"

# "EEVEE" oppure "CYCLES"
MOTORE = "EEVEE"

# Acqua con un velo di foschia (rende visibili i fasci di luce, ma rallenta
# un po' il render)
FOSCHIA = True

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
NV = _carica("creature_neve")
TAU = CL.TAU
V = Vector
ellipsoid = CL.ellipsoid
capsule = CL.capsule
ball = CL.ball
side_name = NV.side_name
rgb_mix = NV.rgb_mix


# ============================================================================
# STRUMENTI
# ============================================================================

def comb_mesh(name, shaft, fil_len, mat, count=None, radius=0.004, droop=0.3, both=True, plane=None):
    """Filamenti sottili (piramidi a 3 facce) lungo un'asta: antenne piumate da
    falena. Poche facce per filamento, cosi' restano leggere anche su Roblox."""
    tans, norms, binors = DS.frames_along(shaft)
    n = len(shaft)
    idx = range(1, n - 1) if count is None else [int(1 + i * (n - 3) / max(1, count - 1)) for i in range(count)]
    bm = bmesh.new()
    for i in idx:
        t = i / (n - 1)
        L = fil_len * (1.0 - 0.7 * t)
        side_v = binors[i] if plane is None else (V(plane) - tans[i] * V(plane).dot(tans[i])).normalized()
        for sd in ((-1, 1) if both else (1,)):
            d = (side_v * sd + tans[i] * 0.45 + V((0, 0, -droop))).normalized()
            base = shaft[i]
            u = d.orthogonal().normalized()
            w = d.cross(u)
            b = [bm.verts.new(base + (u * cos(a) + w * sin(a)) * radius) for a in (0.0, TAU / 3, 2 * TAU / 3)]
            tip = bm.verts.new(base + d * L)
            for k in range(3):
                bm.faces.new((b[k], b[(k + 1) % 3], tip))
            bm.faces.new((b[2], b[1], b[0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return CL.mesh_object(name, bm, mat, smooth=False)


def fin_mesh(name, outline, thickness, mat, frame, curl=0.0):
    """Pinna piatta con uno spessore: outline = [(x, y)] nel piano della pinna,
    frame = matrice che la posiziona (X, Y nel piano, Z = normale)."""
    bm = bmesh.new()
    top, bot = [], []
    for (x, y) in outline:
        z = curl * x * x
        top.append(bm.verts.new((x, y, z + thickness / 2)))
        bot.append(bm.verts.new((x, y, z - thickness / 2)))
    n = len(outline)
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top[i], bot[i], bot[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = CL.mesh_object(name, bm, mat)
    ob.matrix_world = frame
    return ob


def lumpy(name, center, size, mat, seed=0, amount=0.15, freq=1.8, sub=4, flat_bottom=None):
    """Sfera deformata dal rumore (rocce, corazze, corpi molli)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub if CL.DETTAGLIO > 0.6 else sub - 1, radius=1.0)
    off = V((seed * 1.3, seed * 2.1, seed * 0.7))
    c = V(center)
    for v in bm.verts:
        d = v.co.normalized()
        nz = mnoise.fractal(d * freq + off, 0.6, 2.0, 4)
        p = d * (1.0 + amount * nz)
        p = V((p.x * size[0], p.y * size[1], p.z * size[2])) + c
        if flat_bottom is not None and p.z < flat_bottom:
            p.z = flat_bottom
        v.co = p
    return CL.mesh_object(name, bm, mat)


def along_x_frames(pts):
    """Sezioni per corpi nel piano YZ (cavalluccio): la normale sta nel piano
    del corpo e la binormale e' l'asse X, cosi' squash stringe il corpo ai lati."""
    tans, _n, _b = DS.frames_along(pts)
    X = V((1, 0, 0))
    norms = [t.cross(X).normalized() for t in tans]
    return tans, norms, [X.copy() for _t in tans]


def eyespot_world(ob, outline, u=0.5, v=0.55, left=False):
    """Posizione (e normale) nel mondo di un punto dell'ala (coordinate UV
    del ventaglio): serve per mettere gli ocelli luminosi sopra la texture."""
    i = int(u * (len(outline) - 1))
    x, y = outline[i]
    p = V((-x * v if left else x * v, y * v, 0.0))
    bpy.context.view_layer.update()
    mw = ob.matrix_world
    return mw @ p, (mw.to_3x3() @ V((0, 0, 1))).normalized()


# ============================================================================
# MATERIALI DELL'OCEANO
# ============================================================================

def m_jelly(name, tint, glow, strength=2.0, pulse=None, rings=6.0):
    """Gelatina: semitrasparente, subsurface, con la luce ciano dentro (piu'
    forte al centro) e i segmenti dell'addome di lucciola."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Generated'], sep.inputs[0])
    seg = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', sep.outputs['Z'], rings)), 0.5))
    seg = nb.maprange(seg, 0.5, 0.38, 1.0, 0.45)
    bsdf = nb.principled(base=tint, rough=0.12, sss=1.0, sss_radius=(0.3, 0.9, 1.0), trans=0.5, ior=1.34,
                         coat=0.8, spec=0.6)
    shader = nb.mix_shader(0.55, nb.transparent(), bsdf.outputs[0])
    core = nb.maprange(nb.facing(0.45), 0.0, 0.9, 1.0, 0.25)
    s = nb.glow(strength, pulse)
    shader = nb.add_shader(shader, nb.emission(glow, nb.math('MULTIPLY', nb.math('MULTIPLY', core, seg), s)))
    rim = nb.maprange(nb.fresnel(0.3), 0.3, 1.0, 0.0, 1.5)
    shader = nb.add_shader(shader, nb.emission(glow, rim))
    nb.output(shader)
    CL.set_transparent(mat, blended=False)
    CL.diffuse_display(mat, glow)
    mat["rbx_kind"] = "ghost"
    mat["rbx_color"] = list(glow)
    mat["rbx_highlight"] = list(glow)
    return mat


def m_tribal(name, base=(0.012, 0.016, 0.014), glow=(0.25, 1.0, 0.3), strength=4.0, pulse=None, uv=True,
             length=12.0):
    """Pelle quasi nera coperta di tatuaggi tribali naturali (onde, spirali e
    reticoli) che brillano di verde neon. Con uv=True usa le UV del corpo
    (u = lungo il corpo, v = attorno)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    if uv:
        sep = nb.node('ShaderNodeSeparateXYZ')
        nb.link(tc.outputs['UV'], sep.inputs[0])
        u = nb.math('MULTIPLY', sep.outputs['X'], length)
        v = nb.math('MULTIPLY', sep.outputs['Y'], TAU)
        cmb = nb.node('ShaderNodeCombineXYZ')
        nb.link(u, cmb.inputs[0])
        nb.link(nb.math('MULTIPLY', sep.outputs['Y'], 3.0), cmb.inputs[1])
        vec = cmb.outputs[0]
    else:
        sep = nb.node('ShaderNodeSeparateXYZ')
        nb.link(tc.outputs['Object'], sep.inputs[0])
        u = nb.math('MULTIPLY', sep.outputs['Z'], length * 1.5)
        v = nb.math('MULTIPLY', nb.math('ARCTAN2', sep.outputs['X'], sep.outputs['Y']), 1.0)
        vec = tc.outputs['Object']
    nz = nb.noise(vec, 3.0, 3.0, 0.5)
    wob = nb.math('MULTIPLY', nb.math('SUBTRACT', nz.outputs['Fac'], 0.5), 2.5)
    a = nb.math('SINE', nb.math('ADD', nb.math('ADD', nb.math('MULTIPLY', u, 3.2),
                                               nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', v, 2.0)), 1.8)),
                                wob))
    lines = nb.maprange(nb.math('ABSOLUTE', a), 0.16, 0.05)
    vo = nb.voronoi(DS._coords(nb, 0.0) if not uv else vec, 2.2 if uv else 14.0, 'DISTANCE_TO_EDGE')
    cells = nb.maprange(vo.outputs['Distance'], 0.035, 0.01)
    keep = nb.maprange(nb.noise(vec, 1.6, 2.0, 0.5).outputs['Fac'], 0.56, 0.68)
    swirl = nb.math('MULTIPLY', nb.math('COSINE', nb.math('MULTIPLY', v, 3.0)), 2.2)
    b2 = nb.math('SINE', nb.math('ADD', nb.math('SUBTRACT', nb.math('MULTIPLY', u, 2.1), swirl),
                                 nb.math('MULTIPLY', wob, 1.4)))
    lines = nb.math('MAXIMUM', lines, nb.maprange(nb.math('ABSOLUTE', b2), 0.12, 0.04))
    mask = nb.math('MAXIMUM', nb.math('MULTIPLY', lines, nb.math('SUBTRACT', 1.0, keep)),
                   nb.math('MULTIPLY', cells, keep))
    dots = nb.voronoi(vec, 4.0 if uv else 30.0, 'F1')
    dm = nb.math('MULTIPLY', nb.maprange(dots.outputs['Distance'], 0.12, 0.06), nb.math('SUBTRACT', 1.0, keep))
    mask = nb.math('MAXIMUM', mask, dm)
    bsdf = nb.principled(base=base, rough=0.3, coat=0.8, coat_rough=0.05, spec=0.5)
    s = nb.glow(strength, pulse)
    nb.output(nb.mix_shader(mask, bsdf.outputs[0], nb.emission(glow, s)))
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(base, 1.0), nb.emission(glow, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(mask, nb.emission((0, 0, 0), 1.0), nb.emission(glow, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_emit_strength"] = float(strength)
    mat["rbx_rough"] = 0.3
    if uv:
        mat["rbx_uv_only"] = 1
        mat["rbx_res"] = [2048, 512]
    CL.diffuse_display(mat, base)
    return mat


def m_light_trail(name, color, strength=1.5, pulse=None):
    """Scia luminosa lasciata dalle ali: sfuma verso i bordi del ventaglio."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    fade = nb.math('MULTIPLY', nb.maprange(v, 0.2, 0.95), nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5)),
                                                                      0.5, 0.2))
    s = nb.glow(strength, pulse)
    nb.output(nb.mix_shader(nb.math('MULTIPLY', fade, 0.8), nb.transparent(), nb.emission(color, s)))
    CL.set_transparent(mat)
    CL.diffuse_display(mat, color)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(color)
    mat["rbx_transp"] = 0.75
    mat["rbx_thick"] = 1               # su Roblox serve uno spessore per vederla dai due lati
    return mat


def m_beam(name, color, strength=2.0, length=1.0, pulse=None):
    """Fascio di luce volumetrico (per coni costruiti con cone_between: la
    coordinata Z dell'oggetto va da 0 alla base a `length` in punta)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    fall = nb.maprange(sep.outputs['Z'], 0.0, length, 1.0, 0.0, smooth=False)
    fall = nb.math('POWER', fall, 1.6)
    s = nb.glow(strength, pulse)
    nb.output(nb.transparent())
    nb.link(nb.emission(color, nb.math('MULTIPLY', fall, s)), nb.out.inputs['Volume'])
    CL.set_transparent(mat)
    CL.diffuse_display(mat, color)
    mat["rbx_kind"] = "aura"
    mat["rbx_color"] = list(color)
    return mat


# ============================================================================
# SCENA DELL'OCEANO: fondale con le caustiche, luce dall'alto, plancton
# ============================================================================

def setup_ocean_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Abisso")
    sc.world = w
    if CL.BL < (5, 0, 0):
        w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.35
    cr.elements[0].color = (0.001, 0.004, 0.01, 1)
    cr.elements[1].position = 0.75
    cr.elements[1].color = (0.006, 0.03, 0.05, 1)
    mp = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], mp.inputs['Value'])
    mp.inputs['From Min'].default_value = -1.0
    mp.inputs['From Max'].default_value = 1.0
    nt.links.new(mp.outputs[0], ramp.inputs[0])
    bg = nt.nodes.new('ShaderNodeBackground')
    nt.links.new(ramp.outputs[0], bg.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def setup_seabed(size=200.0):
    mat = CL.new_material("Fondale_Sabbia")
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    obj = tc.outputs['Object']
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    nb.set(wv, 'Scale', 2.4)
    nb.set(wv, 'Distortion', 5.0)
    nb.set(wv, 'Detail', 2.0)
    nb.link(obj, wv.inputs['Vector'])
    nz = nb.noise(obj, 0.4, 5.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, (0.09, 0.11, 0.11)), (0.7, (0.16, 0.17, 0.16))])
    bsdf = nb.principled(base=col, rough=0.9, spec=0.3)
    nb.set(bsdf, 'Normal', nb.bump(nb.math('MULTIPLY', wv.outputs['Fac'], 0.6), 0.35, 0.01))
    # caustiche: reticolo di luce che si muove sul fondo
    cv = nb.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', voronoi_dimensions='4D')
    nb.set(cv, 'Scale', 4.5)
    nb.link(obj, cv.inputs['Vector'])
    CL.add_driver(cv.inputs['W'], "default_value", "0.8*sin(frame*%.6f)" % (TAU / CL.ANIM_FRAMES))
    caus = nb.maprange(cv.outputs['Distance'], 0.035, 0.0)
    fade = nb.maprange(nb.noise(obj, 0.15, 2.0, 0.5).outputs['Fac'], 0.35, 0.65, 0.3, 1.0)
    nb.output(nb.add_shader(bsdf.outputs[0], nb.emission((0.3, 0.75, 0.9), nb.math('MULTIPLY', nb.math(
        'MULTIPLY', caus, fade), 0.07))))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    return CL.mesh_object("Fondale", bm, mat, smooth=False)


def setup_water(extent=(26.0, 26.0, 7.0), center=(0.0, 3.0, 3.4), plankton=1400):
    """Foschia azzurra (volume) e plancton sospeso (particelle fisse)."""
    if FOSCHIA:
        mat = CL.new_material("Acqua_Foschia")
        nb = CL.NodeBuilder(mat)
        pv = nb.node('ShaderNodeVolumePrincipled')
        nb.set(pv, 'Color', (0.35, 0.75, 0.9))
        nb.set(pv, 'Density', 0.035)
        nb.set(pv, 'Anisotropy', 0.35)
        nb.link(pv.outputs[0], nb.out.inputs['Volume'])
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        ob = CL.mesh_object("Acqua", bm, mat, smooth=False)
        ob.location = center
        ob.scale = extent
        ob.visible_shadow = False
    if plankton:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        em = CL.mesh_object("Plancton_Emettitore", bm, None, smooth=False)
        em.location = center
        em.scale = (extent[0] * 0.6, extent[1] * 0.5, extent[2] * 0.8)
        grain = CL.sphere("Plancton", (0, 0, -5), 0.01, CL.m_sparkle("Plancton_Luce", (0.4, 0.9, 1.0), 4.0),
                          seg=6, rings=3)
        CL.particle_scatter(em, grain, plankton, size=1.0, size_random=0.8, seed=2)


# ============================================================================
# 01  MEDUSA-LANTERNA
# ============================================================================

def build_jellyfish():
    DS.texspace("Medusa")
    cyan = (0.1, 0.9, 1.0)
    m_bell = m_jelly("Medusa_Ombrella_Gelatina", (0.55, 0.9, 1.0), cyan, 2.4, pulse=(1.4, 3.0, 1, 0.0))
    m_gas = CL.m_halo("Medusa_Gas_Luminoso", cyan, 2.5, pulse=(1.5, 3.5, 1, 0.0))
    m_core = CL.m_emit("Medusa_Lanterna", (0.6, 1.0, 1.0), 8.0, pulse=(5.0, 10.0, 1, 0.0))
    m_bead = CL.m_emit("Medusa_Perline", (0.3, 1.0, 0.95), 5.0, pulse=(2.0, 6.0, 2, 0.0))
    m_ant = CL.m_emit("Medusa_Antenne", (0.3, 0.95, 1.0), 3.0, pulse=(1.5, 4.0, 1, 1.0))

    Z = 1.35                                   # bordo dell'ombrella
    R, H = 0.42, 0.52

    def bell_profile(scale_r, scale_h, z0, reverse=False):
        prof = []
        for i in range(25):
            t = i / 24
            a = t * pi / 2
            r = R * scale_r * cos(a) ** 0.75 * (1.0 + 0.035 * (0.5 + 0.5 * cos(TAU * 5.5 * t)))
            prof.append((max(r, 0.002), z0 + H * scale_h * sin(a)))
        return list(reversed(prof)) if reverse else prof

    prof = bell_profile(1.0, 1.0, Z) + bell_profile(0.9, 0.85, Z + 0.015, reverse=True)
    bell = DS.lathe("Medusa_Ombrella", prof, m_bell, seg=64, cap_bottom=False)
    gas = CL.sphere("Medusa_Gas", (0, 0, Z + 0.2), (0.34, 0.34, 0.26), m_gas)
    CL.no_shadow(gas)
    core = CL.sphere("Medusa_Lanterna", (0, 0, Z + 0.3), (0.12, 0.12, 0.1), m_core)
    CL.no_shadow(core)
    # l'ombrella si contrae e si espande (respira)
    w = TAU * 1 / CL.ANIM_FRAMES
    for ob, base in ((bell, (1, 1, 1)), (gas, (0.34, 0.34, 0.26))):
        for i in range(3):
            k = 1.0 if i < 2 else 0.6
            CL.add_driver(ob, "scale", "%.4f*(1.0-%.3f*sin(frame*%.6f))" % (base[i], 0.07 * k, w), i,
                          meta=dict(tipo='scala', lo=0.93, hi=1.07, cyc=1, ph=pi) if i == 0 else None)
    # perline luminose lungo il bordo
    for i in range(24):
        a = TAU * i / 24
        b = CL.sphere("Medusa_Perla_%02d" % i, (R * 1.01 * cos(a), R * 1.01 * sin(a), Z - 0.005), 0.013, m_bead,
                      seg=10, rings=5)
        CL.no_shadow(b)

    # al posto dei tentacoli: lunghe antenne piumate da falena che ondeggiano
    for k in range(8):
        a = TAU * (k + 0.5) / 8
        r0 = R * (0.55 + 0.25 * (k % 2))
        root = V((r0 * cos(a), r0 * sin(a), Z + 0.03))
        L = 1.0 + 0.25 * ((k * 3) % 4) / 3
        out = V((cos(a), sin(a), 0))
        ctrl = [root, root + out * 0.06 + V((0, 0, -0.25 * L)), root + out * 0.14 + V((0, 0, -0.55 * L)),
                root + out * 0.1 + V((0, 0, -0.85 * L)), root + out * 0.18 + V((0, 0, -1.05 * L))]
        shaft = DS.spline(ctrl, CL.det(26, 10))
        radii = [0.008 - 0.005 * i / (len(shaft) - 1) for i in range(len(shaft))]
        a_ob = CL.tube("Medusa_Antenna_%d" % k, shaft, radii, m_ant, bevel_res=2)
        c_ob = comb_mesh("Medusa_Piume_%d" % k, shaft, 0.08, m_ant, count=CL.det(18, 8), radius=0.003, droop=0.35,
                         plane=out)
        for ob in (a_ob, c_ob):
            CL.no_shadow(ob)
        piv = DS.pivot("Medusa_Antenna_Perno_%d" % k, root, [a_ob, c_ob])
        DS.wobble(piv, 0, 7, 1, 0.8 * k)
        DS.wobble(piv, 1, 7, 1, 0.8 * k + 1.3)

    CL.add_light("Medusa_Luce_Gas", 'POINT', (0, 0, Z + 0.15), 20.0, cyan, 0.2, pulse=(10.0, 26.0, 1, 0.0))
    CL.add_light("Medusa_Luce_Antenne", 'POINT', (0, 0, Z - 0.6), 6.0, (0.3, 0.95, 1.0), 0.4, pulse=(3.0, 8.0, 1, 1.0))
    CL.float_all("Medusa_Galleggiamento", (0, 0, Z), 0.08, 1, -pi / 2, sway=(3, 3))


# ============================================================================
# 02  CAVALLUCCIO-NEON
# ============================================================================

def build_seahorse():
    DS.texspace("Cavalluccio")
    green = (0.25, 1.0, 0.3)
    m_body = m_tribal("Cavalluccio_Pelle_Tribale", strength=4.0, pulse=(2.5, 5.0, 1, 0.0), length=14.0)
    m_head = m_tribal("Cavalluccio_Testa_Tribale", strength=4.0, pulse=(2.5, 5.0, 1, 0.0), uv=False, length=6.0)
    m_eye = CL.m_radial_glow("Cavalluccio_Occhio", [(0.0, (0.0, 0.0, 0.0)), (0.35, (0.05, 0.3, 0.05)),
                                                    (0.6, (0.4, 1.0, 0.4)), (1.0, (0.1, 0.4, 0.1))], 2.0)
    m_wing = CL.m_wing("Cavalluccio_Ali_Frenetiche", [(0.0, (0.4, 1.0, 0.5)), (1.0, (0.7, 1.0, 0.7))], alpha=0.06,
                       membrane_str=0.3, vein_ramp=[(0.0, (0.3, 1.0, 0.35)), (1.0, (0.6, 1.0, 0.5))], vein_str=2.5,
                       radial=(7, 0.07), cross=(3, 0.04), edge=0.06, cells=(30.0, 0.03, 0.6), v_mix=1.0,
                       facing_mix=0.3)
    m_trail = m_light_trail("Cavalluccio_Scia_Ali", green, 1.4, pulse=(0.8, 1.8, 4, 0.0))

    # corpo a "S": testa in alto, pancia in avanti, coda arrotolata
    ctrl = [(0, 0.03, 1.22), (0, 0.07, 1.08), (0, 0.02, 0.94), (0, -0.05, 0.78), (0, -0.02, 0.62), (0, 0.05, 0.5),
            (0, 0.07, 0.39), (0, 0.03, 0.29), (0, -0.04, 0.26), (0, -0.07, 0.32), (0, -0.04, 0.37), (0, -0.005, 0.345)]
    path = DS.spline(ctrl, CL.det(90, 30))
    n = len(path)
    prof = [(0.0, 0.05), (0.12, 0.065), (0.3, 0.085), (0.45, 0.08), (0.58, 0.05), (0.75, 0.028), (1.0, 0.01)]

    def radius(t):
        for (t0, r0), (t1, r1) in zip(prof, prof[1:]):
            if t <= t1:
                f = (t - t0) / (t1 - t0)
                return r0 + (r1 - r0) * f
        return prof[-1][1]
    radii = [radius(i / (n - 1)) * (1.0 + 0.08 * cos(TAU * 16 * i / (n - 1)) ** 2) for i in range(n)]
    DS.sweep_mesh("Cavalluccio_Corpo", path, radii, m_body, ring=16, squash=0.7, frames=along_x_frames(path))
    # testa, muso a trombetta, coroncina di spine
    hc = V((0, 0.0, 1.27))
    CL.sphere("Cavalluccio_Testa", hc, (0.042, 0.065, 0.06), m_head)
    CL.tube("Cavalluccio_Muso", [hc + V((0, -0.04, -0.01)), hc + V((0, -0.14, -0.03)), hc + V((0, -0.2, -0.035))],
            [0.024, 0.016, 0.02], m_head, bevel_res=3)
    for i in range(5):
        a = radians(-40 + 20 * i)
        b = hc + V((0.02 * sin(a), 0.02 + 0.02 * cos(a), 0.05))
        CL.cone_between("Cavalluccio_Corona_%d" % i, b, b + V((0.015 * sin(a), 0.01, 0.045)), 0.01, 0.0, m_head, 6)
    tans, norms, binors = along_x_frames(path)
    for i in range(4, int(n * 0.7), 3):
        back = -norms[i] if norms[i].y < 0 else norms[i]
        p = path[i] + back * radii[i] * 0.95
        CL.cone_between("Cavalluccio_Spina_%02d" % i, p - back * 0.005, p + back * 0.025, 0.007, 0.0, m_head, 5)
    for sx in (-1, 1):
        e = CL.sphere("Cavalluccio_Occhio_" + side_name(sx), (0, 0, 0), 1.0, m_eye, seg=20, rings=10)
        DS.place_on(e, hc + V((0.036 * sx, -0.012, 0.01)), (sx, 0, 0), scale=(0.018, 0.018, 0.01))

    # pinne = piccole ali da insetto frenetiche, con la scia luminosa
    dors = [(-10, 0.08), (0, 0.16), (15, 0.2), (30, 0.17), (45, 0.08)]
    pect = [(-10, 0.05), (0, 0.1), (15, 0.12), (30, 0.1), (42, 0.04)]
    CL.wing_pair("Cavalluccio_Ala_Dorsale", dors, m_wing, (0.02, 0.1, 0.72), elev=55, sweep=80, roll=30, rings=6,
                 flap=(30, 36, 0.0))
    CL.wing_pair("Cavalluccio_Ala_Pettorale", pect, m_wing, (0.035, 0.03, 1.13), elev=15, sweep=60, roll=40, rings=5,
                 flap=(35, 40, 0.7))
    for (ctrlw, attach, elev, sweep, roll) in ((dors, (0.02, 0.1, 0.72), 55, 80, 30),
                                               (pect, (0.035, 0.03, 1.13), 15, 60, 40)):
        outline = CL.wing_outline([(a, r * 1.05) for a, r in ctrlw], 32)
        for left in (False, True):
            for k, de in enumerate((-30, 30)):
                ob = CL.wing_mesh("Cavalluccio_Scia_%s_%d_%d" % ("L" if left else "R", int(attach[2] * 10), k), outline,
                                  m_trail, rings=3, mirror=left)
                ax = V(attach)
                if left:
                    ax.x = -ax.x
                CL.place_wing(ob, ax, elev + de, sweep, roll, left)
    CL.add_light("Cavalluccio_Luce", 'POINT', (0, -0.35, 0.9), 6.0, green, 0.3, pulse=(3.0, 8.0, 1, 0.0))
    CL.add_light("Cavalluccio_Luce_Coda", 'POINT', (0.2, 0.0, 0.35), 3.0, green, 0.3, pulse=(1.5, 4.0, 1, 1.5))
    CL.float_all("Cavalluccio_Galleggiamento", (0, 0, 0.8), 0.05, 1, 0.0, sway=(4, 0))


# ============================================================================
# 03  GRANCHIO-FARO
# ============================================================================

def build_crab():
    DS.texspace("Granchio")
    warm = (1.0, 0.85, 0.45)
    m_shell = CL.m_body("Granchio_Corazza_Roccia", (0.2, 0.12, 0.09), rough=0.97, mottle=((0.1, 0.09, 0.08), 5.0),
                        bump=(14.0, 0.9, 'warts'))
    m_limb = CL.m_body("Granchio_Zampe", (0.32, 0.12, 0.07), rough=0.9, mottle=((0.18, 0.08, 0.05), 8.0),
                       bump=(30.0, 0.6, 'warts'))
    m_tip = CL.m_body("Granchio_Punte_Chele", (0.03, 0.025, 0.025), rough=0.4, coat=0.5)
    m_eye = CL.m_body("Granchio_Occhi", (0.01, 0.01, 0.01), rough=0.05, coat=1.0, emit=warm, emit_str=0.4)
    m_coral = CL.m_body("Granchio_Corallo", (0.9, 0.25, 0.35), rough=0.7, sss=0.4, sss_radius=(1.0, 0.3, 0.3),
                        emit=(1.0, 0.35, 0.45), emit_str=0.25)
    m_coral2 = CL.m_body("Granchio_Corallo_Arancio", (0.95, 0.5, 0.15), rough=0.7, sss=0.4, emit=(1.0, 0.5, 0.2),
                         emit_str=0.25)
    m_barn = CL.m_body("Granchio_Balani", (0.55, 0.52, 0.48), rough=0.8, bump=(60.0, 0.4, 'warts'))
    m_crack = CL.m_body("Granchio_Crepa", (0.01, 0.005, 0.0), rough=1.0, emit=(1.0, 0.6, 0.2), emit_str=0.5)
    m_bulb = NV.m_bulb_glass("Granchio_Bulbo_Vetro", (1.0, 0.95, 0.85), warm, 2.5, pulse=(2.0, 3.5, 1, 0.0),
                             center=0.6)
    m_bulb["rbx_kind"] = "neon"
    m_bulb["rbx_transp"] = 0.15
    m_lamp = CL.m_emit("Granchio_Lampada_Faro", (1.0, 0.95, 0.8), 40.0, pulse=(34.0, 44.0, 2, 0.0))
    m_ray = m_beam("Granchio_Fascio", (1.0, 0.9, 0.6), 0.65, length=2.4)
    m_metal = CL.m_body("Granchio_Lanterna", (0.06, 0.05, 0.04), rough=0.4, metal=0.8)

    # corazza di roccia viva, spaccata al centro
    shell = lumpy("Granchio_Corazza", (0, 0.02, 0.3), (0.44, 0.35, 0.17), m_shell, seed=3, amount=0.2, freq=2.2)
    sb = CL.bvh_of(shell)
    top, _n = CL.surface_hit(sb, V((0, 0.02, 0.3)), (0, 0, 1))
    CL.sphere("Granchio_Crepa", (0, 0.02, top.z - 0.035), (0.17, 0.15, 0.04), m_crack)
    random.seed(4)
    for i in range(11):
        a = TAU * i / 11 + random.uniform(-0.15, 0.15)
        d = V((cos(a), sin(a), 0))
        base = V((0, 0.02, top.z - 0.02)) + d * 0.15
        me = DS.crystal_mesh("Granchio_Scheggia_%02d" % i, random.uniform(0.07, 0.12), 0.045, sides=4, tip=0.7,
                             seed=30 + i)
        me.materials.append(m_shell)
        ob = bpy.data.objects.new(me.name, me)
        CL.link(ob)
        DS.place_on(ob, base, (d * 0.8 + V((0, 0, 0.9))).normalized(), d)

    # coralli e balani incrostati
    for i in range(6):
        a = TAU * (i + 0.3) / 6
        loc, nor = CL.surface_hit(sb, V((0, 0.02, 0.3)), (cos(a) * 0.8, sin(a) * 0.8, 0.55))
        if loc is None:
            continue
        mat = m_coral if i % 2 else m_coral2
        tip = loc + nor * 0.1
        CL.tube("Granchio_Corallo_%d" % i, [loc - nor * 0.01, loc + nor * 0.05, tip], [0.012, 0.01, 0.006], mat,
                bevel_res=2)
        for k in range(3):
            b = loc.lerp(tip, 0.4 + 0.2 * k)
            side = nor.orthogonal().normalized()
            side = Matrix.Rotation(TAU * k / 3 + i, 3, nor) @ side
            CL.tube("Granchio_Rametto_%d_%d" % (i, k), [b, b + (side + nor).normalized() * 0.05], [0.007, 0.003], mat,
                    bevel_res=1)
    for i in range(14):
        a = random.uniform(0, TAU)
        loc, nor = CL.surface_hit(sb, V((0, 0.02, 0.3)), (cos(a), sin(a), random.uniform(0.15, 0.8)))
        if loc is None:
            continue
        CL.cone_between("Granchio_Balano_%02d" % i, loc - nor * 0.005, loc + nor * 0.025, 0.02, 0.009, m_barn, 8)

    # bulbo di lucciola che esce dalla crepa + lanterna del faro che ruota
    c0 = V((0, 0.02, top.z - 0.02))
    segs = []
    for k, (h, r) in enumerate(((0.05, 0.13), (0.15, 0.12), (0.24, 0.1), (0.31, 0.075))):
        segs.append(CL.sphere("Granchio_Bulbo_%d" % k, c0 + V((0, 0, h)), (r, r, 0.065), m_bulb, seg=40, rings=20))
    L0 = c0 + V((0, 0, 0.42))
    CL.cone_between("Granchio_Lanterna_Base", L0 - V((0, 0, 0.07)), L0 - V((0, 0, 0.04)), 0.06, 0.05, m_metal, 16)
    lamp = CL.sphere("Granchio_Lampada", L0, 0.055, m_lamp)
    CL.no_shadow(lamp)
    CL.cone_between("Granchio_Lanterna_Tetto", L0 + V((0, 0, 0.05)), L0 + V((0, 0, 0.11)), 0.07, 0.0, m_metal, 16)
    beams = []
    for sgn in (1, -1):
        d = V((sgn, 0, -0.08)).normalized()
        b = CL.cone_between("Granchio_Fascio_%s" % ("A" if sgn > 0 else "B"), L0 + d * 0.03, L0 + d * 2.4, 0.04, 0.3,
                            m_ray, 24)
        CL.no_shadow(b)
        sp = CL.add_light("Granchio_Faro_%s" % ("A" if sgn > 0 else "B"), 'SPOT', L0 + d * 0.06, 50.0, warm, 0.03,
                          spot_size=16, pulse=(40.0, 55.0, 2, 0.0))
        CL.aim(sp, L0 + d * 3.0)
        beams += [b, sp]
    rot_piv = DS.pivot("Granchio_Faro_Perno", L0, beams)
    DS.spin(rot_piv, 2, 2)
    CL.add_light("Granchio_Luce_Bulbo", 'POINT', c0 + V((0, 0, 0.2)), 15.0, warm, 0.1, pulse=(10.0, 18.0, 1, 0.0))
    CL.add_light("Granchio_Luce_Corazza", 'POINT', (0.4, -0.9, 0.9), 12.0, (0.75, 0.85, 1.0), 0.6)

    # occhi su peduncoli, chele (una enorme), otto zampe
    for sx in (-1, 1):
        s = side_name(sx)
        a = V((0.07 * sx, -0.28, 0.36))
        b = a + V((0.02 * sx, -0.03, 0.12))
        CL.tube("Granchio_Peduncolo_" + s, [a, b], [0.012, 0.01], m_limb, bevel_res=2)
        CL.sphere("Granchio_Occhio_" + s, b + V((0, 0, 0.015)), 0.022, m_eye)
    for sx in (-1, 1):
        s = side_name(sx)
        big = 1.35 if sx > 0 else 0.9
        A = V((0.28 * sx, -0.2, 0.27))
        B = V((0.42 * sx, -0.36, 0.3))
        DS.leg("Granchio_Braccio_" + s, [A, B], [0.045 * big, 0.045 * big], m_limb)
        hand = B + V((0.02 * sx, -0.12 * big, 0.0))
        DS.segment("Granchio_Chela_" + s, hand, V((0.15 * sx, -1, 0.1)), 0.075 * big, 0.24 * big, m_limb, flat=0.7)
        tipc = hand + V((0.03 * sx, -0.13 * big, 0.0))
        f1 = [tipc, tipc + V((0.02 * sx, -0.1 * big, 0.03)), tipc + V((-0.01 * sx, -0.16 * big, 0.02))]
        CL.tube("Granchio_Dito1_" + s, f1, [0.035 * big, 0.022 * big, 0.004], m_tip, bevel_res=3)
        CL.tube("Granchio_Dito2_" + s, [tipc + V((0, 0, -0.03)), tipc + V((0.03 * sx, -0.09 * big, -0.05)),
                                        tipc + V((0.0, -0.14 * big, -0.03))],
                [0.03 * big, 0.018 * big, 0.004], m_tip, bevel_res=3)
        for k, ang in enumerate((-20, 5, 30, 55)):
            a = radians(ang)
            d = V((sx * cos(a), sin(a), 0))
            A = V((0.3 * sx, 0.0, 0.22)) + V((0, 0.05 * k, 0))
            Kn = A + d * 0.22 + V((0, 0, 0.14))
            F = A + d * 0.48 + V((0, 0, -0.2))
            DS.leg("Granchio_Zampa_%s%d" % (s, k), [A, Kn, F], [0.03, 0.024, 0.008], m_limb)


# ============================================================================
# 04  MANTA-LUMINESCENTE
# ============================================================================

def build_manta():
    DS.texspace("Manta")
    K = 1.65
    Zc = 1.3
    cobalt = (0.1, 0.3, 1.0)
    violet = (0.55, 0.2, 1.0)
    m_skin = NV.m_two_tone("Manta_Pelle", (0.02, 0.035, 0.06), (0.75, 0.82, 0.88),
                           lambda nb, sep: nb.maprange(sep.outputs['Z'], Zc - 0.01, Zc - 0.05), rough=0.35, sheen=0.2)
    m_eye = CL.m_body("Manta_Occhi", (0.01, 0.01, 0.02), rough=0.05, coat=1.0, emit=cobalt, emit_str=0.6)
    m_wing = CL.m_wing("Manta_Ali_Falena_Luna",
                       [(0.0, (0.08, 0.3, 0.4)), (0.5, (0.18, 0.72, 0.78)), (0.85, (0.35, 0.85, 0.95)),
                        (1.0, (0.5, 0.35, 1.0))],
                       alpha=0.35, membrane_str=0.45, vein_ramp=[(0.0, cobalt), (1.0, (0.35, 0.55, 1.0))],
                       vein_str=3.0, radial=(9, 0.06), cross=(3, 0.035), edge=0.05, v_mix=1.0, facing_mix=0.25,
                       distort=0.04, spots=[(0.5, 0.55, 0.11, True)], pulse=(0.6, 1.3, 1, 0.0))
    m_spot_out = CL.m_emit("Manta_Ocello_Cobalto", cobalt, 2.2, pulse=(0.5, 3.0, 1, 0.0))
    m_spot_in = CL.m_emit("Manta_Ocello_Viola", violet, 2.2, pulse=(0.5, 3.0, 1, pi))
    m_plank = CL.m_sparkle("Manta_Plancton_Scia", (0.35, 0.8, 1.0), 7.0, twinkle=4.0)
    m_scale = CL.m_emit("Manta_Scaglie_Luminose", (0.4, 0.75, 1.0), 5.0, pulse=(2.0, 7.0, 2, 0.0))

    E = [ellipsoid((0, 0.0, Zc), 0.36 * K, (1.0, 1.25, 0.24)),
         ellipsoid((0, -0.36, Zc), 0.22 * K, (1.3, 0.8, 0.28)),
         capsule((0, 0.35, Zc), (0, 0.58, Zc), 0.06 * K)]
    body = CL.metaball_mesh("Manta_Corpo", E, m_skin, res=0.02)
    for sx in (-1, 1):
        s = side_name(sx)
        lobe = [(0.14 * sx, -0.48, Zc), (0.17 * sx, -0.62, Zc - 0.02), (0.15 * sx, -0.69, Zc - 0.08),
                (0.12 * sx, -0.64, Zc - 0.12)]
        CL.tube("Manta_Lobo_" + s, lobe, [0.035, 0.03, 0.022, 0.012], m_skin, bevel_res=3)
        CL.sphere("Manta_Occhio_" + s, (0.21 * sx, -0.43, Zc + 0.02), 0.018, m_eye, seg=16, rings=8)
    CL.tube("Manta_Coda", [(0, 0.55, Zc), (0.03, 0.9, Zc - 0.02), (-0.02, 1.25, Zc - 0.04), (0.02, 1.55, Zc - 0.03)],
            [0.022, 0.012, 0.006, 0.002], m_skin, bevel_res=2)
    disc = [(-0.72, 0.02), (-0.5, -0.2), (-0.22, -0.4), (0.22, -0.4), (0.5, -0.2), (0.72, 0.02), (0.45, 0.2),
            (0.2, 0.42), (-0.2, 0.42), (-0.45, 0.2)]
    fin_mesh("Manta_Disco", disc, 0.035, m_skin, Matrix.Translation((0, -0.02, Zc)), curl=-0.06)
    del body

    # pinne pettorali = ali di una gigantesca falena luna marina
    fore = [(-35, 0.35), (-20, 0.9), (-8, 1.25), (2, 1.35), (12, 1.2), (24, 0.95), (36, 0.7), (48, 0.45)]
    hind = [(40, 0.4), (55, 0.8), (66, 0.95), (74, 0.9), (80, 1.4), (84, 2.1), (87, 2.2), (90, 1.4), (97, 0.75),
            (112, 0.45), (126, 0.2)]
    wings = []
    for key, ctrl, attach, ph in (("Ant", fore, (0.3, -0.14, Zc), 0.0), ("Post", hind, (0.26, 0.08, Zc), 0.25)):
        obs = CL.wing_pair("Manta_Ala" + key, ctrl, m_wing, attach, elev=4, sweep=0, roll=0, rings=12, droop=0.06,
                           flap=(16, 1, ph), n=64)
        wings.append((ctrl, obs))
    # ocelli che pulsano di blu cobalto e viola
    for ctrl, obs in wings:
        outline = CL.wing_outline(ctrl, 64)
        for ob in obs:
            left = ob.name.endswith("_L")
            p, nrm = eyespot_world(ob, outline, 0.5, 0.55, left)
            for nm, mat, r, th in (("Esterno", m_spot_out, 0.1, 0.012), ("Interno", m_spot_in, 0.055, 0.02)):
                d = CL.sphere("%s_Ocello_%s" % (ob.name, nm), (0, 0, 0), 1.0, mat, seg=24, rings=8)
                CL.orient(d, p, nrm, scale=(r, r, th))
                CL.no_shadow(d)
                bpy.context.view_layer.update()
                mw = d.matrix_world.copy()
                d.parent = ob.parent
                d.matrix_parent_inverse = ob.parent.matrix_world.inverted()
                d.matrix_world = mw
    CL.add_light("Manta_Luce_Cobalto", 'POINT', (0, -0.2, Zc - 0.35), 10.0, cobalt, 0.4, pulse=(3.0, 12.0, 1, 0.0))
    CL.add_light("Manta_Luce_Viola", 'POINT', (0, 0.3, Zc + 0.4), 8.0, violet, 0.4, pulse=(3.0, 10.0, 1, pi))
    CL.float_all("Manta_Galleggiamento", (0, 0, Zc), 0.1, 1, 0.0, sway=(0, 4))

    # scia di plancton luminoso (le scaglie che lascia al suo passaggio)
    path = DS.spline([(0, 0.5, Zc), (0.1, 1.3, Zc + 0.05), (0.3, 2.2, Zc + 0.2), (0.6, 3.0, Zc + 0.4)], 24)
    radii = [0.2 + 0.6 * i / 23 for i in range(24)]
    em, _f, _l = DS.sweep_mesh("Manta_Scia_Emettitore", path, radii, None, ring=10)
    grain = CL.sphere("Manta_Granello", path[2], 0.012, m_plank, seg=6, rings=3)
    CL.particle_scatter(em, grain, 1600, size=1.0, size_random=0.7, seed=5)
    random.seed(33)
    w = TAU / CL.ANIM_FRAMES
    for i in range(22):
        j = random.randint(0, 23)
        off = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
        loc = path[j] + off * radii[j] * random.uniform(0.1, 0.8)
        f = CL.sphere("Manta_Scaglia_%02d" % i, loc, random.uniform(0.01, 0.018), m_scale, seg=4, rings=2)
        CL.no_shadow(f)
        cyc = random.choice((1, 2))
        ph = random.uniform(0, TAU)
        CL.add_driver(f, "location", "%.4f+0.05*sin(frame*%.6f+%.3f)" % (loc.z, w * cyc, ph), 2,
                      meta=dict(tipo='bob', amp=0.05, cyc=cyc, ph=ph))


# ============================================================================
# 05  SQUALO-PLASMA
# ============================================================================

def m_vessels(name, skin=(0.025, 0.035, 0.05), belly=(0.3, 0.34, 0.38), glow=(0.25, 0.6, 1.0), strength=5.0,
              pulse=None, length=7.0):
    """Pelle scura e bagnata (clearcoat alto) con il sistema circolatorio che
    brilla sotto: grandi vasi lungo i fianchi e sul dorso, e una rete di
    capillari. UV del corpo: u = dal muso alla coda, v = attorno (0 = dorso)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('MULTIPLY', u, length), cmb.inputs[0])
    nb.link(nb.math('MULTIPLY', v, 2.2), cmb.inputs[1])
    vec = cmb.outputs[0]
    nz = nb.noise(vec, 2.5, 3.0, 0.5)
    wig = nb.math('MULTIPLY', nb.math('SUBTRACT', nz.outputs['Fac'], 0.5), 0.05)
    mains = None
    for c in (0.25, 0.75, 0.0, 1.0):
        d = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('ADD', v, wig), c))
        m = nb.maprange(d, 0.014, 0.004)
        mains = m if mains is None else nb.math('MAXIMUM', mains, m)
    halo = None
    for c in (0.25, 0.75):
        d = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('ADD', v, wig), c))
        m = nb.maprange(d, 0.07, 0.0, 0.0, 0.25)
        halo = m if halo is None else nb.math('MAXIMUM', halo, m)
    vo = nb.voronoi(vec, 3.2, 'DISTANCE_TO_EDGE')
    branch = nb.maprange(nb.noise(vec, 1.3, 2.0, 0.5).outputs['Fac'], 0.45, 0.58)
    net = nb.math('MULTIPLY', nb.maprange(vo.outputs['Distance'], 0.018, 0.005), nb.math('MULTIPLY', branch, 0.6))
    net = nb.math('MULTIPLY', net, nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.5)), 0.08, 0.2))
    fade = nb.maprange(u, 0.02, 0.08)
    mask = nb.math('MULTIPLY', nb.math('MAXIMUM', mains, net), fade)
    bellym = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.5)), 0.2, 0.08)
    col = rgb_mix(nb, bellym, skin, belly)
    bsdf = nb.principled(base=col, rough=0.3, coat=1.0, coat_rough=0.02, spec=0.6)
    s = nb.glow(strength, pulse)
    em = nb.math('MULTIPLY', nb.math('ADD', mask, nb.math('MULTIPLY', halo, fade)), s)
    nb.output(nb.add_shader(bsdf.outputs[0], nb.emission(glow, em)))
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(col, 1.0), nb.emission(glow, 1.0)))
    nb.bake_output("RBX_EMIT", nb.emission(glow, nb.math('ADD', mask, nb.math('MULTIPLY', halo, fade))))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_res"] = [2048, 512]
    mat["rbx_rough"] = 0.3
    mat["rbx_emit_strength"] = float(strength)
    CL.diffuse_display(mat, skin)
    return mat


def build_shark():
    DS.texspace("Squalo")
    Zc = 1.0
    plasma = (0.15, 0.45, 1.0)
    m_skin = m_vessels("Squalo_Pelle_Vasi_Plasma", glow=plasma, strength=2.6, pulse=(1.6, 3.2, 2, 0.0))
    m_fin = CL.m_body("Squalo_Pinne", (0.03, 0.04, 0.055), rough=0.3, coat=1.0, emit=plasma, emit_str=0.25,
                      rim=plasma, rim_str=0.4)
    m_gill = CL.m_emit("Squalo_Branchie", (0.25, 0.6, 1.0), 3.0, pulse=(1.0, 4.0, 2, 0.0))
    m_eye = CL.m_body("Squalo_Occhi", (0.005, 0.005, 0.01), rough=0.03, coat=1.0, emit=plasma, emit_str=0.8)
    m_wing = CL.m_wing("Squalo_Ali_Energia", [(0.0, (0.2, 0.5, 1.0)), (1.0, (0.4, 0.7, 1.0))], alpha=0.03,
                       membrane_str=0.2, vein_ramp=[(0.0, (0.25, 0.6, 1.0)), (1.0, (0.5, 0.8, 1.0))], vein_str=2.2,
                       radial=(7, 0.05), cross=(3, 0.035), edge=0.06, cells=(32.0, 0.025, 0.45), v_mix=1.0,
                       facing_mix=0.35, pulse=(0.6, 1.5, 4, 0.0))

    n = CL.det(70, 24)
    path = [V((0.035 * sin(pi * 1.5 * i / (n - 1)), -0.75 + 1.3 * i / (n - 1), Zc + 0.02 * (1 - i / (n - 1))))
            for i in range(n)]
    prof = [(0.0, 0.004), (0.05, 0.045), (0.14, 0.09), (0.3, 0.12), (0.42, 0.125), (0.62, 0.095), (0.84, 0.048),
            (1.0, 0.026)]

    def radius(t):
        for (t0, r0), (t1, r1) in zip(prof, prof[1:]):
            if t <= t1:
                f = (t - t0) / (t1 - t0)
                f = f * f * (3 - 2 * f)
                return r0 + (r1 - r0) * f
        return prof[-1][1]
    radii = [radius(i / (n - 1)) for i in range(n)]
    fr = DS.frames_up(path)
    DS.sweep_mesh("Squalo_Corpo", path, radii, m_skin, ring=18, squash=0.82, frames=fr)
    tans, norms, binors = fr

    def at(t, a_deg, lift=1.0):
        i = min(n - 1, int(t * (n - 1)))
        a = radians(a_deg)
        return path[i] + (norms[i] * cos(a) * radii[i] + binors[i] * sin(a) * radii[i] * 0.82) * lift

    # pinne: dorsale, pettorali, caudale (su un perno che ondeggia)
    def frame(origin, xa, ya):
        xa, ya = V(xa).normalized(), V(ya).normalized()
        za = xa.cross(ya).normalized()
        ya = za.cross(xa)
        m = Matrix((xa, ya, za)).transposed().to_4x4()
        m.translation = origin
        return m
    fin_mesh("Squalo_Pinna_Dorsale", [(-0.12, 0.0), (-0.03, 0.1), (0.05, 0.19), (0.1, 0.21), (0.07, 0.11), (0.1, 0.0)],
             0.016, m_fin, frame(at(0.42, 0, 0.9), (0, 1, 0), (0, 0, 1)))
    for sx in (-1, 1):
        fin_mesh("Squalo_Pinna_Pettorale_" + side_name(sx),
                 [(0.0, -0.07), (0.24, 0.06), (0.3, 0.12), (0.18, 0.1), (0.0, 0.07)], 0.014, m_fin,
                 frame(at(0.3, 110 * sx, 0.9), (sx, 0.25, -0.35), (0, 1, 0)))
        fin_mesh("Squalo_Pinna_Pelvica_" + side_name(sx), [(0.0, -0.03), (0.09, 0.03), (0.1, 0.07), (0.0, 0.04)],
                 0.01, m_fin, frame(at(0.64, 140 * sx, 0.9), (sx, 0.3, -0.6), (0, 1, 0)))
    tail_base = path[-1]
    caud = fin_mesh("Squalo_Pinna_Caudale", [(-0.02, 0.03), (0.12, 0.32), (0.17, 0.33), (0.1, 0.12), (0.07, 0.01),
                                             (0.13, -0.16), (0.08, -0.15), (-0.02, -0.03)],
                    0.014, m_fin, frame(tail_base, (0, 1, 0), (0, 0, 1)))
    piv = DS.pivot("Squalo_Coda_Perno", tail_base, [caud])
    DS.wobble(piv, 2, 16, 2, 0.0)

    # branchie luminose e occhi
    for sx in (-1, 1):
        s = side_name(sx)
        for k in range(5):
            t = 0.2 + 0.022 * k
            pts = [at(t, sx * a, 1.015) for a in range(60, 131, 10)]
            g = CL.tube("Squalo_Branchia_%s%d" % (s, k), pts, 0.004, m_gill, bevel_res=1, poly=True)
            CL.no_shadow(g)
        e = CL.sphere("Squalo_Occhio_" + s, (0, 0, 0), 1.0, m_eye, seg=16, rings=8)
        CL.orient(e, at(0.1, 62 * sx, 0.98), (at(0.1, 62 * sx) - path[int(0.1 * (n - 1))]).normalized(),
                  scale=(0.016, 0.016, 0.01))
    # quattro ali da libellula cariche di energia, vicino alle branchie
    ctrl = [(-8, 0.1), (-3, 0.36), (4, 0.42), (12, 0.36), (18, 0.1)]
    p1 = at(0.27, 0, 1.0)
    CL.wing_pair("Squalo_Ala", ctrl, m_wing, (0.06, p1.y, p1.z - 0.02), elev=28, sweep=72, roll=15, rings=6,
                 flap=(18, 24, 0.0))
    CL.wing_pair("Squalo_Ala2", ctrl, m_wing, (0.06, p1.y + 0.07, p1.z - 0.03), elev=12, sweep=98, roll=15, rings=6,
                 flap=(18, 24, 1.3))
    CL.add_light("Squalo_Luce_Plasma", 'POINT', (0, -0.2, Zc - 0.3), 10.0, plasma, 0.4, pulse=(4.0, 12.0, 2, 0.0))
    CL.add_light("Squalo_Luce_Ali", 'POINT', (0, -0.2, Zc + 0.45), 6.0, (0.5, 0.75, 1.0), 0.3, pulse=(2.0, 7.0, 4, 0.0))
    CL.float_all("Squalo_Galleggiamento", (0, 0, Zc), 0.06, 1, 0.0, sway=(0, 5))


# ============================================================================
# 06  TARTARUGA-FOSFORICA
# ============================================================================

def m_hexcell(name, glow, phase):
    """Cella di vetro spesso piena di liquido luminescente (pulsa per conto suo)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    bsdf = nb.principled(base=(0.75, 1.0, 0.9), rough=0.05, trans=1.0, ior=1.45, coat=1.0, spec=0.7)
    core = nb.maprange(nb.facing(0.4), 0.0, 0.9, 1.0, 0.2)
    s = nb.glow(1.8, (0.25, 2.2, 1, phase))
    nb.output(nb.add_shader(bsdf.outputs[0], nb.emission(glow, nb.math('MULTIPLY', core, s))))
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    CL.diffuse_display(mat, glow)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(glow)
    mat["rbx_transp"] = 0.2
    return mat


def hex_cell_mesh(name, R):
    """Esagono a lente: fianchi bassi e cupola, come una cella di vetro spesso."""
    bm = bmesh.new()
    rings = [(R, -0.025), (R, 0.008), (R * 0.62, 0.028)]
    loops = []
    for r, z in rings:
        loops.append([bm.verts.new((r * cos(TAU * k / 6), r * sin(TAU * k / 6), z)) for k in range(6)])
    apex = bm.verts.new((0, 0, 0.038))
    for a, b in zip(loops, loops[1:]):
        for k in range(6):
            bm.faces.new((a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k]))
    for k in range(6):
        bm.faces.new((loops[-1][k], loops[-1][(k + 1) % 6], apex))
    bm.faces.new(list(reversed(loops[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def build_turtle():
    DS.texspace("Tartaruga")
    K = 1.65
    Zs = 0.8
    aqua = (0.1, 1.0, 0.75)
    m_skin = CL.m_body("Tartaruga_Pelle", (0.16, 0.22, 0.18), rough=0.55, mottle=((0.42, 0.46, 0.36), 7.0),
                       bump=(45.0, 0.5, 'scales'), coat=0.3)
    m_under = CL.m_body("Tartaruga_Guscio_Base", (0.02, 0.035, 0.03), rough=0.6)
    m_plastron = CL.m_body("Tartaruga_Piastrone", (0.5, 0.46, 0.3), rough=0.6)
    m_beak = CL.m_body("Tartaruga_Becco", (0.1, 0.1, 0.07), rough=0.35, coat=0.5)
    m_eye = CL.m_body("Tartaruga_Occhi", (0.01, 0.015, 0.012), rough=0.05, coat=1.0, emit=aqua, emit_str=0.5)
    NPH = 8
    cells_m = [m_hexcell("Tartaruga_Cella_%d" % k, aqua, -TAU * k / NPH) for k in range(NPH)]

    a, b, c = 0.42, 0.55, 0.2
    CL.sphere("Tartaruga_Guscio", (0, 0, Zs), (a * 0.97, b * 0.97, c * 0.95), m_under, seg=48, rings=24)
    CL.sphere("Tartaruga_Piastrone", (0, 0, Zs - 0.015), (a * 0.93, b * 0.95, 0.07), m_plastron)
    # decine di bulbi esagonali uniti a formare il guscio
    R = 0.068
    cell_me = hex_cell_mesh("Tartaruga_Cella", R * 0.93)
    count = 0
    ys = []
    centers = []
    for q in range(-8, 9):
        for r in range(-10, 11):
            x = 1.5 * R * q
            y = math.sqrt(3) * R * (r + q / 2.0)
            if (x / (a * 0.92)) ** 2 + (y / (b * 0.92)) ** 2 > 1.0:
                continue
            centers.append((x, y))
            ys.append(y)
    y0, y1 = min(ys), max(ys)
    for (x, y) in centers:
        h = math.sqrt(max(0.0, 1.0 - (x / a) ** 2 - (y / b) ** 2))
        z = Zs + c * h
        nrm = V((x / a ** 2, y / b ** 2, (z - Zs) / c ** 2)).normalized()
        k = int((y - y0) / (y1 - y0 + 1e-6) * NPH) % NPH
        me = cell_me.copy()
        me.materials.append(cells_m[k])
        ob = bpy.data.objects.new("Tartaruga_Cella_%03d" % count, me)
        CL.link(ob)
        ob.matrix_world = CL.frame_matrix(V((x, y, z)), (0, 1, 0), nrm)
        count += 1

    # testa, collo, zampe-pinna
    E = [capsule((0, -0.46, Zs), (0, -0.62, Zs + 0.02), 0.07 * K),
         ellipsoid((0, -0.7, Zs + 0.03), 0.09 * K, (0.95, 1.3, 0.85))]
    head = CL.metaball_mesh("Tartaruga_Testa", E, m_skin, res=0.016)
    hb = CL.bvh_of(head)
    for sx in (-1, 1):
        CL.make_eye("Tartaruga_Occhio_" + side_name(sx), hb, V((0, -0.72, Zs + 0.04)), (0.7 * sx, -0.6, 0.3), 0.018,
                    m_eye, None, None, sink=0.3, flat=0.8)
    bl, _bn = CL.surface_hit(hb, V((0, -0.72, Zs + 0.02)), (0, -1, -0.15))
    CL.cone_between("Tartaruga_Becco", bl - V((0, -0.02, 0)), bl + V((0, -0.035, -0.02)), 0.028, 0.004, m_beak, 12)
    del head
    for sx in (-1, 1):
        s = side_name(sx)
        sh = V((0.3 * sx, -0.3, Zs - 0.02))
        d = V((sx, -0.25, -0.05)).normalized()
        fl = DS.segment("Tartaruga_Pinna_Ant_" + s, sh + d * 0.32, d, 0.1, 0.66, m_skin, flat=0.2)
        piv = DS.pivot("Tartaruga_Pinna_Ant_Perno_" + s, sh, [fl])
        DS.wobble(piv, 1, 22 * sx, 1, 0.0)
        DS.wobble(piv, 2, 10 * sx, 1, pi / 2)
        hp = V((0.26 * sx, 0.42, Zs - 0.03))
        d = V((0.7 * sx, 1.0, -0.1)).normalized()
        hf = DS.segment("Tartaruga_Pinna_Post_" + s, hp + d * 0.13, d, 0.07, 0.28, m_skin, flat=0.25)
        piv = DS.pivot("Tartaruga_Pinna_Post_Perno_" + s, hp, [hf])
        DS.wobble(piv, 2, 12 * sx, 1, 1.0)
    CL.cone_between("Tartaruga_Coda", (0, 0.5, Zs - 0.02), (0, 0.66, Zs - 0.05), 0.04, 0.0, m_skin, 12)
    for k in range(3):
        CL.add_light("Tartaruga_Luce_Onda_%d" % k, 'POINT', (0, -0.35 + 0.35 * k, Zs + 0.55), 6.0, aqua, 0.3,
                     pulse=(1.0, 9.0, 1, -TAU * (k * 3 + 1) / NPH))
    CL.float_all("Tartaruga_Galleggiamento", (0, 0, Zs), 0.07, 1, 0.0, sway=(3, 2))


# ============================================================================
# 07  RANA PESCATRICE-ABISSO
# ============================================================================

def build_anglerfish():
    DS.texspace("Pescatrice")
    K = 1.65
    Zc = 0.75
    firefly = (0.75, 1.0, 0.25)
    m_skin = CL.m_body("Pescatrice_Pelle_Abissale", (0.03, 0.025, 0.028), rough=0.92,
                       mottle=((0.065, 0.05, 0.05), 5.0), bump=(22.0, 0.8, 'warts'))
    m_mouth = CL.m_body("Pescatrice_Bocca", (0.06, 0.01, 0.015), rough=0.6)
    m_tooth = CL.m_body("Pescatrice_Denti", (0.82, 0.8, 0.7), rough=0.25, sss=0.3, coat=0.5)
    m_eye = CL.m_body("Pescatrice_Occhi", (0.12, 0.15, 0.18), rough=0.1, coat=1.0)
    m_fin = CL.m_body("Pescatrice_Pinne", (0.04, 0.035, 0.035), rough=0.7)
    m_glass = CL.new_material("Pescatrice_Esca_Vetro_Organico")
    nb = CL.NodeBuilder(m_glass)
    gb = nb.principled(base=(0.9, 1.0, 0.85), rough=0.03, trans=1.0, ior=1.33, spec=0.6, coat=0.5)
    rim = nb.maprange(nb.fresnel(0.3), 0.3, 1.0, 0.0, 0.6)
    nb.output(nb.add_shader(gb.outputs[0], nb.emission((0.6, 1.0, 0.4), rim)))
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(m_glass, attr):
            setattr(m_glass, attr, val)
    m_glass["rbx_kind"] = "glass"
    m_glass["rbx_color"] = [0.75, 1.0, 0.6]
    m_glass["rbx_transp"] = 0.55
    m_lantern = CL.m_emit("Pescatrice_Lucciola_Lanterna", firefly, 12.0, pulse=(6.0, 16.0, 6, 0.0))
    m_halo = CL.m_halo("Pescatrice_Alone_Esca", firefly, 0.25, pulse=(0.1, 0.4, 6, 0.0))
    m_ff_dark = CL.m_body("Pescatrice_Lucciola_Corpo", (0.03, 0.025, 0.02), rough=0.3, coat=0.8)
    m_ff_red = CL.m_body("Pescatrice_Lucciola_Pronoto", (0.85, 0.25, 0.08), rough=0.35, coat=0.6)
    m_ff_wing = CL.m_wing("Pescatrice_Lucciola_Ali", [(0.0, (0.8, 0.85, 0.7)), (1.0, (0.95, 1.0, 0.85))], alpha=0.3,
                          membrane_str=0.3, vein_ramp=[(0.0, (0.3, 0.3, 0.2)), (1.0, (0.4, 0.4, 0.3))], vein_str=0.6,
                          radial=(5, 0.08), edge=0.05, v_mix=1.0)

    E = [ellipsoid((0, 0.05, Zc), 0.3 * K, (1.0, 1.15, 0.9)),
         ellipsoid((0, -0.2, Zc + 0.03), 0.28 * K, (1.05, 0.9, 0.95)),
         ellipsoid((0, -0.3, Zc - 0.15), 0.19 * K, (1.1, 0.95, 0.5)),
         capsule((0, 0.3, Zc), (0, 0.56, Zc + 0.02), 0.1 * K),
         ellipsoid((0, -0.47, Zc - 0.03), 0.17 * K, (1.0, 0.75, 0.5), neg=True)]
    body = CL.metaball_mesh("Pescatrice_Corpo", E, m_skin, res=0.02)
    bvh = CL.bvh_of(body)
    CL.sphere("Pescatrice_Gola", (0, -0.3, Zc - 0.03), (0.2, 0.12, 0.09), m_mouth)
    # zanne: sotto grandi e storte verso l'alto, sopra piu' corte verso il basso
    random.seed(9)
    for row, (zo, up, n, ln) in enumerate(((-0.08, 1, 13, 0.085), (0.075, -1, 11, 0.06))):
        for i in range(n):
            ang = radians(-72 + 144 * i / (n - 1))
            d = V((sin(ang), -cos(ang), 0))
            loc, nor = CL.surface_hit(bvh, V((0, -0.3, Zc + zo)), d)
            if loc is None:
                continue
            L = ln * random.uniform(0.6, 1.15) * (1.0 - 0.35 * abs(sin(ang)))
            tip = loc + V((0, 0, up * L)) + d * 0.02 * up + V((random.uniform(-0.01, 0.01), 0, 0))
            CL.cone_between("Pescatrice_Dente_%d_%02d" % (row, i), loc - nor * 0.01, tip, 0.012, 0.0, m_tooth, 6)
    for sx in (-1, 1):
        CL.make_eye("Pescatrice_Occhio_" + side_name(sx), bvh, V((0, -0.2, Zc + 0.12)), (0.75 * sx, -0.5, 0.4), 0.02,
                    m_eye, None, None, sink=0.4, flat=0.8)
    # pinne
    for sx in (-1, 1):
        f = fin_mesh("Pescatrice_Pinna_" + side_name(sx), [(0, -0.05), (0.14, -0.1), (0.2, -0.02), (0.18, 0.08),
                                                           (0.0, 0.05)], 0.01, m_fin,
                     CL.frame_matrix(V((0.27 * sx, 0.02, Zc - 0.05)), (0, 1, 0), (0.3 * sx, 0, 1)))
        f.scale = (sx, 1, 1)
    fin_mesh("Pescatrice_Coda", [(0, -0.04), (0.2, -0.18), (0.24, 0.0), (0.2, 0.18), (0, 0.04)], 0.012, m_fin,
             CL.frame_matrix(V((0, 0.62, Zc + 0.02)), (0, 0, 1), (1, 0, 0)) @ Matrix.Rotation(pi / 2, 4, 'Z'))
    for i in range(5):
        p = V((0, 0.05 + 0.08 * i, Zc + 0.36 - 0.05 * i))
        CL.cone_between("Pescatrice_Spina_%d" % i, p - V((0, 0, 0.05)), p + V((0, 0.03, 0.08 - 0.01 * i)), 0.012, 0.0,
                        m_fin, 6)

    # ILLICIO + ESCA: una lucciola vera intrappolata in una sfera di vetro organico
    base = V((0, -0.2, Zc + 0.3))
    rod_pts = [base, V((0, -0.3, Zc + 0.52)), V((0, -0.52, Zc + 0.62)), V((0, -0.73, Zc + 0.55)),
               V((0, -0.78, Zc + 0.44))]
    rod = CL.tube("Pescatrice_Illicio", rod_pts, [0.016, 0.012, 0.009, 0.007, 0.006], m_skin, bevel_res=3)
    Ec = V((0, -0.785, Zc + 0.35))
    RE = 0.075
    group = []
    group.append(CL.cone_between("Pescatrice_Attacco_Esca", Ec + V((0, 0, RE + 0.03)), Ec + V((0, 0, RE - 0.02)),
                                 0.012, 0.03, m_skin, 12))
    g = CL.sphere("Pescatrice_Esca", Ec, RE, m_glass, seg=48, rings=24)
    CL.no_shadow(g)
    group.append(g)
    h = CL.sphere("Pescatrice_Alone_Esca", Ec, RE * 2.2, m_halo)
    CL.no_shadow(h)
    group.append(h)
    # micro-lucciola dettagliata (lunga 6 cm), leggermente inclinata
    F = Ec + V((0, 0.0, -0.005))
    group.append(CL.sphere("Pescatrice_Lucciola_Testa", F + V((0, -0.024, 0.004)), 0.0065, m_ff_dark, seg=16, rings=8))
    group.append(CL.sphere("Pescatrice_Lucciola_Pronoto", F + V((0, -0.013, 0.006)), (0.011, 0.01, 0.004), m_ff_red,
                           seg=16, rings=8))
    for sx in (-1, 1):
        group.append(CL.sphere("Pescatrice_Lucciola_Elitra_" + side_name(sx), F + V((0.007 * sx, 0.006, 0.008)),
                               (0.0055, 0.017, 0.0025), m_ff_dark, rot=(8, 0, 18 * sx), seg=16, rings=8))
    lant = [CL.sphere("Pescatrice_Lucciola_Lanterna_%d" % k, F + V((0, 0.017 + 0.011 * k, -0.001 - 0.001 * k)),
                      (0.0085 - 0.0015 * k, 0.008, 0.0065 - 0.001 * k), m_lantern, seg=16, rings=8) for k in range(2)]
    for ob in lant:
        CL.no_shadow(ob)
    group += lant
    for sx in (-1, 1):
        s = side_name(sx)
        for k in range(3):
            a = F + V((0.004 * sx, -0.014 + 0.008 * k, -0.002))
            b = a + V((0.012 * sx, -0.004 + 0.004 * k, -0.006))
            c = b + V((0.006 * sx, -0.002 + 0.004 * k, -0.01))
            group.append(CL.tube("Pescatrice_Lucciola_Zampa_%s%d" % (s, k), [a, b, c], [0.0012, 0.001, 0.0006],
                                 m_ff_dark, bevel_res=1, poly=True))
        a = F + V((0.003 * sx, -0.029, 0.006))
        group.append(CL.tube("Pescatrice_Lucciola_Antenna_" + s,
                             [a, a + V((0.01 * sx, -0.012, 0.012)), a + V((0.018 * sx, -0.016, 0.02))],
                             [0.0011, 0.0009, 0.0006], m_ff_dark, bevel_res=1, poly=True))
    # ali che sbattono disperatamente (dentro la sfera)
    wctrl = [(-10, 0.012), (0, 0.03), (12, 0.036), (24, 0.03), (34, 0.012)]
    wob = CL.wing_pair("Pescatrice_Lucciola_Ala", wctrl, m_ff_wing, F + V((0.003, -0.005, 0.009)), elev=35, sweep=70,
                       roll=10, rings=4, flap=(40, 60, 0.0), n=24)
    group += [o.parent for o in wob]
    group.append(CL.add_light("Pescatrice_Luce_Esca", 'POINT', Ec + V((0, -0.12, 0)), 6.0, firefly, 0.02,
                              pulse=(3.0, 9.0, 6, 0.0)))
    esca_piv = DS.pivot("Pescatrice_Esca_Perno", rod_pts[-1], group)
    DS.wobble(esca_piv, 0, 10, 2, 0.0)
    DS.wobble(esca_piv, 1, 8, 1, 1.0)
    rod_piv = DS.pivot("Pescatrice_Illicio_Perno", base, [rod, esca_piv])
    DS.wobble(rod_piv, 0, 4, 1, 0.5)
    CL.add_light("Pescatrice_Luce_Riflesso", 'POINT', (0, -0.6, Zc + 0.1), 3.0, firefly, 0.2, pulse=(1.5, 4.0, 6, 0.0))
    CL.add_light("Pescatrice_Controluce", 'POINT', (-0.5, 0.6, Zc + 0.8), 8.0, (0.4, 0.7, 1.0), 0.5)
    CL.float_all("Pescatrice_Galleggiamento", (0, 0, Zc), 0.05, 1, 0.0, sway=(2, 0))


# ============================================================================
# 08  IL BLOBFISH "MEWING"
# ============================================================================

def jaw_mesh(name, mat, center, width=0.2, depth=0.26, h0=0.0, h1=0.075, h2=0.14):
    """Mascella squadrata iper-definita: un prisma a U con spigoli vivi e il
    mento con la fossetta."""
    w, d = width, depth
    outline = [(-w, 0.06), (-w * 0.98, -d * 0.55), (-w * 0.62, -d * 0.93), (-0.045, -d), (0.0, -d * 0.95),
               (0.045, -d), (w * 0.62, -d * 0.93), (w * 0.98, -d * 0.55), (w, 0.06)]
    bm = bmesh.new()
    loops = []
    for z, sc, dy in ((h0, 0.9, 0.02), (h1, 1.0, 0.0), (h2, 0.94, 0.03)):
        loops.append([bm.verts.new((x * sc, y * sc + dy, z)) for x, y in outline])
    for a, b in zip(loops, loops[1:]):
        for i in range(len(outline) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    bm.faces.new(list(reversed(loops[0])))
    bm.faces.new(loops[-1])
    bm.faces.new((loops[0][-1], loops[0][0], loops[1][0], loops[1][-1]))
    bm.faces.new((loops[1][-1], loops[1][0], loops[2][0], loops[2][-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = CL.mesh_object(name, bm, mat, smooth=False)
    ob.location = center
    return ob


def build_blobfish():
    DS.texspace("Blobfish")
    K = 1.65
    pink = (1.0, 0.3, 0.65)
    m_blob = CL.m_body("Blobfish_Gelatina_Rosa", (0.85, 0.45, 0.5), rough=0.18, sss=0.8,
                       sss_radius=(1.0, 0.35, 0.35), coat=0.7, coat_rough=0.04, spec=0.85,
                       mottle=((0.72, 0.33, 0.4), 4.0), bump=(12.0, 0.25, 'noise'))
    m_jaw = CL.m_body("Blobfish_Mascella_Squadrata", (0.9, 0.52, 0.55), rough=0.3, sss=0.5, sss_radius=(1.0, 0.4, 0.4),
                      spec=0.7, coat=0.4, rim=(1.0, 0.8, 0.8), rim_str=0.45)
    m_lip = CL.m_body("Blobfish_Labbra", (0.55, 0.22, 0.28), rough=0.25, coat=0.6)
    m_eye = CL.m_body("Blobfish_Occhi", (0.01, 0.01, 0.012), rough=0.05, coat=1.0)
    m_leg = CL.m_body("Blobfish_Zampetta", (0.4, 0.2, 0.16), rough=0.3, coat=0.8)
    m_slime = CL.m_body("Blobfish_Bava", (0.9, 0.7, 0.75), rough=0.02, coat=1.0, alpha=0.5)
    m_wing = CL.m_wing("Blobfish_Alucce_Patetiche", [(0.0, (1.0, 0.45, 0.7)), (1.0, (1.0, 0.6, 0.8))], alpha=0.15,
                       membrane_str=0.35, vein_ramp=[(0.0, pink), (1.0, (1.0, 0.5, 0.8))], vein_str=0.9,
                       radial=(5, 0.08), edge=0.08, v_mix=1.0, pulse=(0.4, 1.0, 1, 0.0))
    m_glow = CL.m_halo("Blobfish_Bagliore_Ridicolo", pink, 0.25, pulse=(0.1, 0.35, 1, 0.0))

    E = [ellipsoid((0, 0.0, 0.32), 0.3 * K, (1.05, 1.0, 0.85)),
         ellipsoid((0, -0.05, 0.2), 0.3 * K, (1.2, 1.0, 0.55)),
         ellipsoid((0, 0.3, 0.17), 0.17 * K, (0.9, 1.3, 0.7)),
         capsule((0, 0.45, 0.15), (0, 0.72, 0.12), 0.07 * K),
         capsule((0, -0.3, 0.4), (0, -0.36, 0.3), 0.075 * K)]
    for sx in (-1, 1):
        E.append(ellipsoid((0.25 * sx, -0.12, 0.15), 0.12 * K, (1.0, 1.0, 0.75)))
    body = CL.metaball_mesh("Blobfish_Corpo", E, m_blob, res=0.018)
    bvh = CL.bvh_of(body)
    # occhietti tristi con le palpebre cadenti
    for sx in (-1, 1):
        s = side_name(sx)
        loc, nor = CL.surface_hit(bvh, V((0.1 * sx, -0.15, 0.44)), (0.3 * sx, -1.0, 0.25))
        e = CL.sphere("Blobfish_Occhio_" + s, (0, 0, 0), 1.0, m_eye, seg=16, rings=8)
        CL.orient(e, loc, nor, scale=(0.018, 0.018, 0.014))
        lid = CL.sphere("Blobfish_Palpebra_" + s, (0, 0, 0), 1.0, m_blob, seg=20, rings=10)
        m = CL.frame_matrix(loc + nor * 0.006 + V((0, 0, 0.012)), (sx * 0.5, 0, 1), nor)
        lid.matrix_world = m @ Matrix.Diagonal((0.03, 0.017, 0.012, 1.0))
    # la mascella da "gigachad" (sta facendo mewing)
    jaw = jaw_mesh("Blobfish_Mascella", m_jaw, (0, -0.09, 0.02), width=0.21, depth=0.34, h1=0.09, h2=0.19)
    lips = [(-0.12, -0.41, 0.215), (-0.04, -0.44, 0.212), (0.04, -0.44, 0.212), (0.12, -0.41, 0.215)]
    CL.tube("Blobfish_Labbra", lips, 0.012, m_lip, bevel_res=2)
    for i, (x, L) in enumerate(((-0.08, 0.05), (0.09, 0.035))):
        CL.cone_between("Blobfish_Bava_%d" % i, (x, -0.43, 0.2), (x + 0.005, -0.44, 0.2 - L), 0.007, 0.002, m_slime, 8)
    del jaw
    # la zampetta da insetto premuta sulle labbra: "shhh"
    pts = [V((0.32, -0.14, 0.14)), V((0.38, -0.34, 0.22)), V((0.2, -0.5, 0.29)), V((0.03, -0.48, 0.31)),
           V((0.0, -0.465, 0.16))]
    DS.leg("Blobfish_Dito", pts, [0.026, 0.022, 0.018, 0.014, 0.011], m_leg, joint_mat=m_leg, joint_r=0.022)
    CL.sphere("Blobfish_Polpastrello", pts[-1] + V((0, 0, -0.005)), (0.011, 0.009, 0.013), m_leg)
    # due inutili alucce microscopiche, con un bagliore rosa patetico
    CL.wing_pair("Blobfish_Aluccia", [(-10, 0.02), (0, 0.06), (12, 0.075), (26, 0.06), (36, 0.02)], m_wing,
                 (0.05, 0.12, 0.49), elev=35, sweep=60, roll=20, rings=4, flap=(10, 2, 0.0), n=24)
    g = CL.sphere("Blobfish_Bagliore", (0, 0.12, 0.52), 0.12, m_glow)
    CL.no_shadow(g)
    CL.add_light("Blobfish_Luce_Patetica", 'POINT', (0, 0.12, 0.6), 0.6, pink, 0.1, pulse=(0.2, 0.8, 1, 0.0))
    CL.add_light("Blobfish_Luce_Viso", 'POINT', (0.25, -1.0, 0.8), 25.0, (1.0, 0.92, 0.95), 0.6)


# ============================================================================
# REGISTRO, SCENA E AVVIO
# ============================================================================

CREATURE_OCEANO = {
    #  chiave        (collezione,                    funzione,          camera: target, dist, elev, azim, lente)
    "medusa":      ("O01_Medusa-Lanterna",         build_jellyfish,   ((0, 0, 1.05), 5.2, 4, 20, 50)),
    "cavalluccio": ("O02_Cavalluccio-Neon",        build_seahorse,    ((0, -0.02, 0.8), 3.2, 5, 60, 50)),
    "granchio":    ("O03_Granchio-Faro",           build_crab,        ((0, -0.15, 0.35), 3.4, 16, 30, 50)),
    "manta":       ("O04_Manta-Luminescente",      build_manta,       ((0, 0.4, 1.2), 7.2, 30, 25, 50)),
    "squalo":      ("O05_Squalo-Plasma",           build_shark,       ((0, -0.05, 1.0), 4.4, 12, 60, 50)),
    "tartaruga":   ("O06_Tartaruga-Fosforica",     build_turtle,      ((0, -0.05, 0.75), 4.2, 28, 35, 50)),
    "pescatrice":  ("O07_Rana-Pescatrice-Abisso",  build_anglerfish,  ((0, -0.4, 0.85), 3.2, 8, 35, 50)),
    "blobfish":    ("O08_Blobfish-Mewing",         build_blobfish,    ((0, -0.15, 0.25), 2.6, 8, 28, 50)),
}

DISPOSIZIONE_OCEANO = {
    #  chiave        (x, y, rotazione_z)
    "manta":       (-4.2, 5.0, 30),
    "medusa":      (-1.2, 4.6, 0),
    "squalo":      (2.0, 4.4, -70),
    "tartaruga":   (4.8, 4.8, -30),
    "granchio":    (-3.6, 0.8, 25),
    "cavalluccio": (-1.2, 0.4, 50),
    "pescatrice":  (1.3, 0.6, -25),
    "blobfish":    (3.6, 0.4, -20),
}


def build(which=None, engine=None, clean=None):
    which = (which or CREATURA).lower()
    if clean if clean is not None else CL.PULISCI_SCENA:
        CL.clear_scene()
    setup_ocean_world()
    CL.setup_render(engine or MOTORE)
    base = CL.new_collection("Scena_Oceano")
    CL.set_collection(base)
    setup_seabed()
    setup_water()
    CL.setup_moonlight()
    CL.add_light("Luce_Superficie", 'AREA', (0, 3, 9), 900.0, (0.45, 0.8, 1.0), 12.0, creature_light=False)
    CL.set_collection(None)
    if which == "tutte":
        for k in CREATURE_OCEANO:
            x, y, rz = DISPOSIZIONE_OCEANO[k]
            CL.build_one(k, (x, y, 0), rot_z=rz, registry=CREATURE_OCEANO)
        CL.setup_camera((0.0, 2.4, 0.9), 10.5, 14, 0, 32)
    else:
        if which not in CREATURE_OCEANO:
            raise ValueError("Creatura sconosciuta: %s (scegli tra %s o 'tutte')"
                             % (which, ", ".join(CREATURE_OCEANO)))
        CL.build_one(which, registry=CREATURE_OCEANO)
        tgt, dist, el, az, lens = CREATURE_OCEANO[which][2]
        CL.setup_camera(tgt, dist, el, az, lens)
    CL.setup_viewport()
    bpy.context.scene.frame_set(1)


def main():
    CL.build = build            # il main condiviso usa questa funzione
    CL.main()


if __name__ == "__main__":
    main()
