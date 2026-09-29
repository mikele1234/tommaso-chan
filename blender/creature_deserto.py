# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE DEL DESERTO - seconda serie per Blender.

    01  SCORPIONE-LANTERNA        (coda con bulbo-lanterna ambrato)
    02  FENNEC-SOLARE             (orecchie-ali di luce solare)
    03  SCARABEO-FORNACE          (spinge una sfera di magma luminoso)
    04  VIPERA-SONAGLIO LUMINOSO  (sonaglio ad anelli e strisce "in caricamento")
    05  LUCERTOLA-CRISTALLO       (spine di quarzo incandescente)
    06  AVVOLTOIO-MIRAGGIO        (ali di calore trasparenti, collare di luce)
    07  TARANTOLA-BRACE           (crepe di lava e sole sulla schiena)
    08  IL CACTUS "CHILL GUY"     (faretto da stadio in testa)

Usa l'infrastruttura di `creature_luminose.py`, che deve stare nella stessa
cartella.

USO DENTRO BLENDER (4.2 o piu' recente)
    1. Workspace "Scripting" > Text > Open... > scegli questo file
       (creature_luminose.py deve essere nella stessa cartella).
    2. Cambia CREATURA qui sotto (oppure lascia "tutte") e premi Run Script.

USO DA RIGA DI COMANDO
    blender --background --python creature_deserto.py -- \
            --creatura vipera --salva vipera.blend --render vipera.png
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

# "scorpione", "fennec", "scarabeo", "vipera", "lucertola", "avvoltoio",
# "tarantola", "cactus" oppure "tutte"
CREATURA = "tutte"

# "EEVEE" oppure "CYCLES"
MOTORE = "EEVEE"

# ============================================================================
# Infrastruttura condivisa (creature_luminose.py)
# ============================================================================


def _carica_base():
    if "creature_luminose" in sys.modules:
        return sys.modules["creature_luminose"]
    qui = os.path.dirname(os.path.abspath(__file__))
    percorso = os.path.join(qui, "creature_luminose.py")
    if not os.path.exists(percorso):
        raise RuntimeError("Metti creature_luminose.py nella stessa cartella di questo script.")
    spec = importlib.util.spec_from_file_location("creature_luminose", percorso)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["creature_luminose"] = mod
    spec.loader.exec_module(mod)
    return mod


CL = _carica_base()
TAU = CL.TAU
V = Vector
ellipsoid = CL.ellipsoid
capsule = CL.capsule
ball = CL.ball


# ============================================================================
# STRUMENTI DI MODELLAZIONE
# ============================================================================

def texspace(prefix):
    """Empty all'origine della creatura usato come spazio texture comune."""
    e = CL.empty(prefix + "_SpazioTexture", (0, 0, 0), 0.1)
    CL._STATE["texspace"] = e
    return e


def spline(ctrl, n):
    """Catmull-Rom attraverso i punti di controllo -> n punti."""
    ctrl = [V(p) for p in ctrl]
    k = len(ctrl)
    out = []
    for i in range(n):
        f = i / (n - 1) * (k - 1)
        j = min(int(f), k - 2)
        t = f - j
        p0 = ctrl[max(j - 1, 0)]
        p1, p2 = ctrl[j], ctrl[j + 1]
        p3 = ctrl[min(j + 2, k - 1)]
        t2, t3 = t * t, t * t * t
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def frames_along(pts):
    """Tangenti e normali 'parallel transport' lungo un percorso."""
    n = len(pts)
    tans = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tans.append((b - a).normalized())
    ref = V((0, 0, 1)) if abs(tans[0].z) < 0.9 else V((1, 0, 0))
    nor = tans[0].cross(ref).normalized()
    norms = [nor]
    for i in range(1, n):
        q = tans[i - 1].rotation_difference(tans[i])
        nor = (q @ norms[-1])
        nor = (nor - tans[i] * nor.dot(tans[i])).normalized()
        norms.append(nor)
    binors = [t.cross(nv).normalized() for t, nv in zip(tans, norms)]
    return tans, norms, binors


def sweep_mesh(name, pts, radii, mat=None, ring=20, caps=True, squash=1.0, frames=None):
    """Tubo 'estruso' lungo un percorso. UV: u = lungo il tubo, v = attorno.
    squash < 1 schiaccia la sezione (es. ventre piatto del serpente)."""
    pts = [V(p) for p in pts]
    n = len(pts)
    ring = CL.det(ring, 6)
    tans, norms, binors = frames or frames_along(pts)
    lengths = [0.0]
    for i in range(1, n):
        lengths.append(lengths[-1] + (pts[i] - pts[i - 1]).length)
    L = lengths[-1] or 1.0
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for i in range(n):
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        row = []
        for j in range(ring):
            a = TAU * j / ring
            off = norms[i] * cos(a) * r + binors[i] * sin(a) * r * squash
            row.append(bm.verts.new(pts[i] + off))
        rings.append(row)
    for i in range(n - 1):
        for j in range(ring):
            j2 = (j + 1) % ring
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            us = (lengths[i] / L, lengths[i + 1] / L)
            vs = (j / ring, (j + 1) / ring)
            for lp, (ui, vi) in zip(f.loops, ((0, 0), (0, 1), (1, 1), (1, 0))):
                lp[uvl].uv = (us[ui], vs[vi])
    if caps:
        for idx, sign in ((0, -1), (n - 1, 1)):
            c = bm.verts.new(pts[idx] + tans[idx] * sign * 0.0)
            for j in range(ring):
                j2 = (j + 1) % ring
                tri = (rings[idx][j], c, rings[idx][j2]) if sign > 0 else (rings[idx][j2], c, rings[idx][j])
                f = bm.faces.new(tri)
                for lp in f.loops:
                    lp[uvl].uv = (lengths[idx] / L, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = CL.mesh_object(name, bm, mat)
    return ob, (tans, norms, binors), lengths


def lathe(name, profile, mat=None, seg=48, cap_bottom=True, cap_top=False, deform=None):
    """Solido di rivoluzione attorno a Z. profile = [(raggio, z), ...] dal basso."""
    seg = CL.det(seg, 12)
    bm = bmesh.new()
    rows = []
    for k, (r, z) in enumerate(profile):
        row = []
        for j in range(seg):
            a = TAU * j / seg
            co = V((r * cos(a), r * sin(a), z))
            if deform:
                co = deform(co, a, k)
            row.append(bm.verts.new(co))
        rows.append(row)
    for k in range(len(rows) - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            bm.faces.new((rows[k][j], rows[k][j2], rows[k + 1][j2], rows[k + 1][j]))
    if cap_bottom:
        bm.faces.new(list(reversed(rows[0])))
    if cap_top:
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return CL.mesh_object(name, bm, mat)


def crystal_mesh(name, length, radius, sides=6, tip=0.32, seed=0):
    """Cristallo grezzo: prisma esagonale con punta. Base in z<0 (piantata)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    base, top = [], []
    for j in range(sides):
        a = TAU * j / sides + rnd.uniform(-0.12, 0.12)
        rr = radius * rnd.uniform(0.85, 1.1)
        base.append(bm.verts.new((rr * cos(a), rr * sin(a), -0.25 * length)))
        top.append(bm.verts.new((rr * 0.92 * cos(a), rr * 0.92 * sin(a), (1 - tip) * length)))
    apex = bm.verts.new((rnd.uniform(-0.2, 0.2) * radius, rnd.uniform(-0.2, 0.2) * radius, length))
    for j in range(sides):
        j2 = (j + 1) % sides
        bm.faces.new((base[j], base[j2], top[j2], top[j]))
        bm.faces.new((top[j], top[j2], apex))
    bm.faces.new(list(reversed(base)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def rock(name, loc, size, mat, seed=1, rough=0.35):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4 if CL.DETTAGLIO > 0.6 else 3, radius=1.0)
    off = V((seed * 1.37, seed * 2.11, seed * 0.73))
    for v in bm.verts:
        d = v.co.normalized()
        n = mnoise.fractal(d * 1.6 + off, 0.6, 2.0, 4)
        n2 = mnoise.noise(d * 5.0 + off)
        v.co = d * (1.0 + rough * n + 0.05 * n2)
    ob = CL.mesh_object(name, bm, mat)
    ob.location = loc
    ob.scale = size
    bpy.context.view_layer.update()
    return ob


def place_on(ob, loc, z_axis, y_axis=(0, 0, 1), scale=(1, 1, 1)):
    m = CL.frame_matrix(V(loc), V(y_axis), V(z_axis))
    ob.matrix_world = m @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    return ob


def segment(name, center, direction, radius, length, mat, flat=0.85, up=(0, 0, 1)):
    """Ellissoide allungato lungo `direction` (segmenti di coda, zampe...)."""
    ob = CL.sphere(name, (0, 0, 0), 1.0, mat, seg=24, rings=12)
    d = V(direction).normalized()
    upv = V(up)
    if abs(d.dot(upv.normalized())) > 0.95:
        upv = V((1, 0, 0))
    nrm = (upv - d * upv.dot(d)).normalized()
    m = CL.frame_matrix(V(center), d, nrm)
    ob.matrix_world = m @ Matrix.Diagonal((radius, length / 2, radius * flat, 1.0))
    return ob


def leg(prefix, pts, radii, mat, joint_mat=None, joint_r=None):
    """Zampa a segmenti rigidi (tubi poligonali) con giunture opzionali."""
    pts = [V(p) for p in pts]
    obs = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        r0 = radii[i]
        r1 = radii[i + 1]
        obs.append(CL.tube("%s_%d" % (prefix, i), [a, a.lerp(b, 0.5), b], [r0, (r0 + r1) / 2, r1],
                           mat, bevel_res=3))
        if joint_mat is not None and 0 < i + 1 < len(pts) - 1:
            jr = joint_r or r1 * 1.25
            obs.append(CL.sphere("%s_Giuntura_%d" % (prefix, i), b, jr, joint_mat, seg=16, rings=8))
    return obs


def wing_pair_edges(prefix, ctrl, mat, edge_mat, attach, elev, sweep, roll=0.0, rings=14,
                    cup=0.0, droop=0.0, flap=None, n=72, scallop=None, edge_r=0.008, wave=None):
    """Come CL.wing_pair, ma con un bordo luminoso (tubo) che segue l'ala e,
    se richiesto, un'ondulazione della superficie (wave = (ampiezza, frequenza))."""
    outline = CL.wing_outline(ctrl, n, scallop)
    out = []
    for left in (False, True):
        side = "L" if left else "R"
        ob = CL.wing_mesh("%s_%s" % (prefix, side), outline, mat, rings=rings, cup=cup,
                          droop=droop, mirror=left)
        if wave:
            amp, freq = wave
            for v in ob.data.vertices:
                r = math.hypot(v.co.x, v.co.y)
                ang = math.atan2(v.co.y, abs(v.co.x))
                v.co.z += amp * r * sin(freq * r + 3.0 * ang)
        pts = []
        for (x, y) in outline:
            r = math.hypot(x, y)
            z = 0.0
            if wave:
                amp, freq = wave
                z = amp * r * sin(freq * r + 3.0 * math.atan2(y, abs(x)))
            z += cup * 1.0 * sin(pi * (len(pts) / max(1, len(outline) - 1))) - droop * r * r
            pts.append(V((-x if left else x, y, z)))
        edge = CL.tube("%s_Bordo_%s" % (prefix, side), pts, edge_r, edge_mat, bevel_res=2, poly=True)
        CL.no_shadow(edge)
        ax = V(attach)
        if left:
            ax.x = -ax.x
        if flap:
            amp, cyc, ph = flap
            piv = CL.empty("%s_Perno_%s" % (prefix, side), ax, 0.05)
            for o in (ob, edge):
                CL.place_wing(o, (0, 0, 0), elev, sweep, roll, left)
                o.parent = piv
            sign = 1 if left else -1
            w = TAU * cyc / CL.ANIM_FRAMES
            CL.add_driver(piv, "rotation_euler",
                          "%d*radians(%.3f)*sin(frame*%.6f+%.3f)" % (sign, amp, w, ph), 1,
                          meta=dict(tipo='rot', amp=sign * radians(amp), cyc=cyc, ph=ph))
        else:
            CL.place_wing(ob, ax, elev, sweep, roll, left)
            CL.place_wing(edge, ax, elev, sweep, roll, left)
        out.append((ob, edge))
    return out


def spin(owner, axis_index, cycles, phase=0.0):
    """Rotazione continua (es. sfera che rotola)."""
    w = TAU * cycles / CL.ANIM_FRAMES
    CL.add_driver(owner, "rotation_euler", "frame*%.6f+%.3f" % (w, phase), axis_index,
                  meta=dict(tipo='rot', spin=True, amp=0.0, cyc=cycles, ph=phase))


def wobble(owner, axis_index, amp_deg, cycles, phase=0.0):
    w = TAU * cycles / CL.ANIM_FRAMES
    CL.add_driver(owner, "rotation_euler", "radians(%.3f)*sin(frame*%.6f+%.3f)" % (amp_deg, w, phase),
                  axis_index, meta=dict(tipo='rot', amp=radians(amp_deg), cyc=cycles, ph=phase))


def pivot(name, loc, children):
    """Empty perno a cui vengono imparentati gli oggetti (senza spostarli)."""
    piv = CL.empty(name, loc, 0.06)
    inv = Matrix.Translation(-V(loc))
    for ob in children:
        ob.parent = piv
        ob.matrix_parent_inverse = inv
    return piv


# ============================================================================
# MATERIALI DEL DESERTO
# ============================================================================

def _coords(nb, distort=0.0, scale=1.0, use_space=True, uv=False):
    tc = nb.texcoord(use_space=use_space)
    vec = tc.outputs['UV'] if uv else tc.outputs['Object']
    if scale != 1.0:
        vm = nb.node('ShaderNodeVectorMath', operation='SCALE')
        nb.link(vec, vm.inputs[0])
        nb.set(vm, 'Scale', scale)
        vec = vm.outputs[0]
    if distort:
        nz = nb.noise(vec, 3.0, 4.0, 0.5)
        sub = nb.node('ShaderNodeVectorMath', operation='SUBTRACT')
        nb.link(nz.outputs['Color'], sub.inputs[0])
        nb.set(sub, 1, (0.5, 0.5, 0.5))
        sc = nb.node('ShaderNodeVectorMath', operation='SCALE')
        nb.link(sub.outputs[0], sc.inputs[0])
        nb.set(sc, 'Scale', distort)
        add = nb.node('ShaderNodeVectorMath', operation='ADD')
        nb.link(vec, add.inputs[0])
        nb.link(sc.outputs[0], add.inputs[1])
        vec = add.outputs[0]
    return vec


def m_chitin_veins(name, base, dark, vein, vein_emit=0.8, scale=9.0, rough=0.55, pulse=None):
    """Corazza color sabbia con venature d'oro (metalliche e un po' luminose)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    vec = _coords(nb, distort=0.25)
    vo = nb.voronoi(vec, scale, 'DISTANCE_TO_EDGE')
    veins = nb.maprange(vo.outputs['Distance'], 0.028, 0.008)
    nz = nb.noise(vec, 6.0, 6.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, dark), (0.7, base)])
    shell = nb.principled(base=col, rough=rough, coat=0.35, coat_rough=0.2, spec=0.4)
    nb.set(shell, 'Normal', nb.bump(nb.math('SUBTRACT', 1.0, veins), 0.25, 0.01))
    gold = nb.principled(base=vein, metal=1.0, rough=0.25)
    shader = nb.mix_shader(veins, shell.outputs[0], gold.outputs[0])
    s = nb.glow(vein_emit, pulse)
    shader = nb.add_shader(shader, nb.emission(vein, nb.math('MULTIPLY', veins, s)))
    nb.output(shader)
    nb.bake_output("RBX_COLOR", nb.mix_shader(veins, nb.emission(col, 1.0), nb.emission(vein, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(veins, nb.emission((0, 0, 0), 1.0), nb.emission(vein, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = rough
    mat["rbx_emit_strength"] = float(vein_emit)
    CL.diffuse_display(mat, base)
    return mat


def m_lava(name, crust=(0.02, 0.015, 0.012), crust2=(0.06, 0.035, 0.025),
           glow=((0.0, (0.6, 0.02, 0.0)), (0.5, (1.0, 0.22, 0.0)), (1.0, (1.0, 0.6, 0.08))),
           scale=7.0, crack=0.06, strength=4.0, pulse=None, uv=False, sun=None):
    """Crosta scura con crepe di lava incandescente (Voronoi).
    sun = (raggi, raggio_disco) aggiunge un sole stilizzato (coordinate UV)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    vec = _coords(nb, distort=0.3, uv=uv)
    vo = nb.voronoi(vec, scale, 'DISTANCE_TO_EDGE')
    cr = nb.maprange(vo.outputs['Distance'], crack, crack * 0.15)
    nz = nb.noise(vec, 4.0, 5.0, 0.55)
    cr = nb.math('MULTIPLY', cr, nb.maprange(nz.outputs['Fac'], 0.3, 0.55, 0.35, 1.0))
    mask = cr
    if sun:
        rays, disk = sun
        tc = nb.texcoord(use_space=False)
        sep = nb.node('ShaderNodeSeparateXYZ')
        nb.link(tc.outputs['UV'], sep.inputs[0])
        x = nb.math('SUBTRACT', sep.outputs['X'], 0.5)
        y = nb.math('SUBTRACT', sep.outputs['Y'], 0.5)
        d = nb.math('MULTIPLY', nb.math('SQRT', nb.math('ADD', nb.math('MULTIPLY', x, x),
                                                        nb.math('MULTIPLY', y, y))), 2.0)
        ang = nb.math('ARCTAN2', y, x)
        fr = nb.math('FRACT', nb.math('MULTIPLY', ang, rays / TAU))
        tri = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', fr, 0.5)), 2.0)
        ray = nb.math('MULTIPLY', nb.maprange(tri, 0.72, 0.9),
                      nb.math('MULTIPLY', nb.maprange(d, disk * 1.25, disk * 1.45),
                              nb.maprange(d, 0.78, 0.62)))
        core = nb.maprange(d, disk, disk * 0.9)
        ring = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', d, disk * 1.12)), 0.025, 0.008)
        mask = nb.math('MAXIMUM', nb.math('MAXIMUM', mask, ray), nb.math('MAXIMUM', core, ring))
    gcol = nb.ramp(nz.outputs['Fac'], list(glow))
    ccol = nb.ramp(nz.outputs['Fac'], [(0.3, crust), (0.7, crust2)])
    crust_bsdf = nb.principled(base=ccol, rough=0.85, sheen=0.4, sheen_tint=(1.0, 0.5, 0.3))
    nb.set(crust_bsdf, 'Normal', nb.bump(nb.math('SUBTRACT', 1.0, cr), 0.5, 0.015))
    s = nb.glow(strength, pulse)
    shader = nb.mix_shader(mask, crust_bsdf.outputs[0], nb.emission(gcol, s))
    nb.output(shader)
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(ccol, 1.0), nb.emission(gcol, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(mask, nb.emission((0, 0, 0), 1.0), nb.emission(gcol, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = 0.85
    mat["rbx_emit_strength"] = float(strength)
    if uv:
        mat["rbx_uv_only"] = 1
    CL.diffuse_display(mat, crust2)
    return mat


def m_magma(name, strength=6.0, pulse=None):
    """Sfera di pura luce densa come magma (emissione con vortici)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    nz = nb.noise(tc.outputs['Object'], 2.5, 8.0, 0.6)
    nb.set(nz, 'Distortion', 3.0)
    col = nb.ramp(nz.outputs['Fac'], [(0.2, (0.85, 0.08, 0.0)), (0.45, (1.0, 0.3, 0.0)),
                                      (0.62, (1.0, 0.55, 0.05)), (0.8, (1.0, 0.85, 0.35))])
    s = nb.glow(strength, pulse)
    nb.output(nb.emission(col, s))
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_emit_strength"] = float(strength)
    CL.diffuse_display(mat, (1.0, 0.4, 0.05))
    return mat


def m_crystal(name, tint, glow, strength=3.0, pulse=None):
    """Quarzo grezzo trasparente con brace accesa all'interno."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    bsdf = nb.principled(base=tint, rough=0.12, trans=1.0, ior=1.55, spec=0.6)
    f = nb.facing(0.4)
    core = nb.maprange(f, 0.0, 0.9, 1.0, 0.25)
    s = nb.glow(strength, pulse)
    shader = nb.add_shader(bsdf.outputs[0], nb.emission(glow, nb.math('MULTIPLY', core, s)))
    nb.output(shader)
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(glow)
    mat["rbx_transp"] = 0.2
    CL.diffuse_display(mat, glow)
    return mat


def m_mirage(name, tint=(0.75, 0.92, 1.0), glow=(0.5, 0.9, 1.0)):
    """Ali-miraggio: vetro quasi invisibile deformato da un rumore animato
    (effetto calore sull'asfalto) con il bordo che brilla."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    nz = nb.node('ShaderNodeTexNoise', noise_dimensions='4D')
    nb.set(nz, 'Scale', 6.0)
    nb.set(nz, 'Detail', 3.0)
    nb.link(tc.outputs['Object'], nz.inputs['Vector'])
    CL.add_driver(nz.inputs['W'], "default_value", "frame*0.035")
    normal = nb.bump(nz.outputs['Fac'], 0.5, 0.03)
    glass = nb.node('ShaderNodeBsdfGlass', {'Color': tint, 'Roughness': 0.02, 'IOR': 1.12})
    nb.set(glass, 'Normal', normal)
    shader = nb.mix_shader(0.72, glass.outputs[0], nb.transparent())
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    edge = nb.maprange(sep.outputs['Y'], 0.9, 0.99)
    shimmer = nb.maprange(nz.outputs['Fac'], 0.5, 0.75, 0.0, 0.05)
    rays = nb.math('FRACT', nb.math('MULTIPLY', sep.outputs['X'], 9.0))
    rays = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', rays, 0.5)), 0.47, 0.5, 0.0, 0.35)
    shimmer = nb.math('ADD', shimmer, nb.math('MULTIPLY', rays, nb.maprange(sep.outputs['Y'], 0.2, 0.9)))
    s = nb.glow(1.0)
    em = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', edge, 2.5), shimmer), s)
    shader = nb.add_shader(shader, nb.emission(glow, em))
    nb.output(shader)
    CL.set_transparent(mat, blended=False)
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = list(tint)
    mat["rbx_transp"] = 0.55
    CL.diffuse_display(mat, tint)
    return mat


def m_glowfeather(name, inner, outer, strength=3.0, pulse=None):
    """Piuma fatta di luce: bianca alla base, colorata verso la punta."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    col = nb.ramp(sep.outputs['Y'], [(0.0, inner), (1.0, outer)])
    au = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', sep.outputs['X'], 0.5)), 2.0)
    alpha = nb.math('MULTIPLY', nb.maprange(sep.outputs['Y'], 1.0, 0.6), nb.maprange(au, 1.0, 0.6))
    s = nb.glow(strength, pulse)
    nb.output(nb.mix_shader(alpha, nb.transparent(), nb.emission(col, s)))
    CL.set_transparent(mat)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(outer)
    CL.diffuse_display(mat, outer)
    return mat


# ============================================================================
# SCENA DEL DESERTO
# ============================================================================

def setup_desert_ground(size=40.0):
    mat = CL.new_material("Sabbia_Notte")
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    nb.set(wv, 'Scale', 1.6)
    nb.set(wv, 'Distortion', 4.0)
    nb.set(wv, 'Detail', 2.0)
    nb.link(tc.outputs['Object'], wv.inputs['Vector'])
    nz = nb.noise(tc.outputs['Object'], 0.35, 6.0, 0.6)
    fine = nb.noise(tc.outputs['Object'], 60.0, 2.0, 0.5)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, (0.07, 0.045, 0.028)), (0.7, (0.13, 0.085, 0.05))])
    h = nb.math('ADD', nb.math('MULTIPLY', wv.outputs['Fac'], 0.5), nb.math('MULTIPLY', fine.outputs['Fac'], 0.3))
    bsdf = nb.principled(base=col, rough=0.9, spec=0.3)
    nb.set(bsdf, 'Normal', nb.bump(h, 0.35, 0.01))
    nb.output(bsdf.outputs[0])
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    return CL.mesh_object("Terreno_Deserto", bm, mat, smooth=False)


# ============================================================================
# 01  SCORPIONE-LANTERNA
# ============================================================================

def build_scorpion():
    texspace("Scorpione")
    sand = (0.42, 0.29, 0.14)
    m_shell = m_chitin_veins("Scorpione_Corazza", sand, (0.26, 0.17, 0.08), (1.0, 0.68, 0.18),
                             vein_emit=0.9, scale=7.0, pulse=(0.6, 1.2, 1, 0.0))
    m_leg = m_chitin_veins("Scorpione_Zampe", (0.36, 0.24, 0.12), (0.2, 0.13, 0.06), (1.0, 0.65, 0.15),
                           vein_emit=0.5, scale=14.0)
    m_elytra = CL.m_body("Scorpione_Elitre", (0.3, 0.17, 0.05), rough=0.25, metal=0.6, coat=1.0,
                         emit=(1.0, 0.55, 0.1), emit_str=0.3, rim=(1.0, 0.6, 0.2), rim_str=0.5)
    m_eye = CL.m_body("Scorpione_Occhi", (0.0, 0.0, 0.0), rough=0.05, coat=1.0)
    m_gold = CL.m_body("Scorpione_Anelli_Oro", (1.0, 0.7, 0.25), rough=0.2, metal=1.0,
                       emit=(1.0, 0.6, 0.15), emit_str=0.4)
    m_bulb = CL.m_body("Scorpione_Bulbo_Smerigliato", (1.0, 0.55, 0.15), rough=0.55, sss=1.0,
                       sss_radius=(1.0, 0.45, 0.15), emit=(1.0, 0.4, 0.05), emit_pulse=(0.6, 2.2, 2, 0.0),
                       emit_center=True, alpha=0.92)
    m_bulb["rbx_transp"] = 0.2
    m_core = CL.m_emit("Scorpione_Fiamma_Interna", (1.0, 0.45, 0.06), 6.0, pulse=(3.0, 9.0, 2, 0.0))
    m_aura = CL.m_halo("Scorpione_Alone", (1.0, 0.42, 0.06), 1.2, pulse=(0.5, 1.8, 2, 0.0))

    # prosoma (carapace) e mesosoma a placche
    CL.sphere("Scorpione_Carapace", (0, -0.28, 0.2), (0.2, 0.22, 0.09), m_shell, rot=(-4, 0, 0))
    for i in range(7):
        t = i / 6
        w = 0.21 - 0.03 * t * t
        CL.sphere("Scorpione_Placca_%d" % i, (0, -0.1 + 0.11 * i, 0.19 + 0.02 * sin(pi * t)),
                  (w, 0.085, 0.085), m_shell)
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        CL.sphere("Scorpione_Occhio_" + s, (0.03 * sx, -0.36, 0.285), 0.018, m_eye)
        CL.sphere("Scorpione_OcchioLat_" + s, (0.14 * sx, -0.44, 0.22), 0.012, m_eye)

    # coda (metasoma) che si arcua sopra il dorso + bulbo-lanterna
    tail_ctrl = [(0, 0.62, 0.2), (0, 0.8, 0.42), (0, 0.8, 0.78), (0, 0.6, 1.05), (0, 0.32, 1.16)]
    path = spline(tail_ctrl, 60)  # solo per posizionare i segmenti
    tail_obs = []
    for i in range(5):
        t0, t1 = i / 5, (i + 1) / 5
        a = path[int(t0 * 59)]
        b = path[int(t1 * 59)]
        r = 0.085 - 0.008 * i
        tail_obs.append(segment("Scorpione_Coda_%d" % i, (a + b) / 2, b - a, r, (b - a).length * 1.18,
                                m_shell, flat=0.9))
        tail_obs.append(segment("Scorpione_CodaAnello_%d" % i, b, b - a, r * 0.8, 0.03, m_gold))
    end = path[-1]
    tdir = (path[-1] - path[-4]).normalized()
    bulb_c = end + tdir * 0.14 + V((0, 0, -0.1))
    tail_obs.append(segment("Scorpione_Collo_Bulbo", end + tdir * 0.03, tdir, 0.06, 0.08, m_gold))
    bulb = CL.sphere("Scorpione_Bulbo", bulb_c, (0.2, 0.22, 0.2), m_bulb, seg=48, rings=24)
    core = CL.sphere("Scorpione_Fiamma", bulb_c, (0.09, 0.1, 0.11), m_core)
    aura = CL.sphere("Scorpione_Alone", bulb_c, 0.42, m_aura)
    CL.no_shadow(aura)
    CL.no_shadow(core)
    lamp = CL.add_light("Scorpione_Luce_Lanterna", 'POINT', bulb_c, 25.0, (1.0, 0.5, 0.15), 0.12,
                        pulse=(12.0, 40.0, 2, 0.0))
    tail_obs += [bulb, core, aura, lamp]
    piv = pivot("Scorpione_Coda_Perno", (0, 0.6, 0.2), tail_obs)
    wobble(piv, 1, 5, 1, 0.0)
    wobble(piv, 0, 3, 2, 0.8)

    # chele massicce
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        a = V((0.1 * sx, -0.42, 0.18))
        b = V((0.3 * sx, -0.55, 0.22))
        c = V((0.36 * sx, -0.75, 0.2))
        leg("Scorpione_Braccio_" + s, [a, b, c], [0.045, 0.05, 0.05], m_leg)
        hand_c = V((0.36 * sx, -0.9, 0.19))
        segment("Scorpione_Chela_" + s, hand_c, V((0.05 * sx, -1, 0)), 0.095, 0.26, m_shell, flat=0.7)
        f1 = [hand_c + V((0.03 * sx, -0.1, 0.02)), hand_c + V((0.06 * sx, -0.25, 0.03)),
              hand_c + V((0.02 * sx, -0.35, 0.02))]
        f2 = [hand_c + V((-0.03 * sx, -0.1, -0.01)), hand_c + V((-0.07 * sx, -0.24, -0.02)),
              hand_c + V((-0.03 * sx, -0.33, -0.01))]
        CL.tube("Scorpione_Dito1_" + s, f1, [0.035, 0.025, 0.006], m_shell, bevel_res=3)
        CL.tube("Scorpione_Dito2_" + s, f2, [0.03, 0.022, 0.005], m_shell, bevel_res=3)

    # otto zampe
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        for k, (y, ang) in enumerate(((-0.2, -30), (-0.08, -8), (0.04, 14), (0.16, 36))):
            a = radians(ang)
            d = V((sx * cos(a), sin(a), 0))
            A = V((0.13 * sx, y, 0.16))
            K = A + d * 0.26 + V((0, 0, 0.14))
            T = A + d * 0.46 + V((0, 0, 0.02))
            F = A + d * 0.56 + V((0, 0, -0.16))
            leg("Scorpione_Zampa_%s%d" % (s, k), [A, K, T, F], [0.03, 0.028, 0.02, 0.008], m_leg)

    # piccole ali da coleottero ripiegate sul dorso
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        CL.sphere("Scorpione_Elitra_" + s, (0.075 * sx, 0.2, 0.285), (0.085, 0.24, 0.035), m_elytra,
                  rot=(4, -8 * sx, 3 * sx))

    CL.add_light("Scorpione_Luce_Terra", 'POINT', (0, -0.2, 0.6), 8.0, (1.0, 0.55, 0.2), 0.3,
                 pulse=(5.0, 12.0, 2, 0.0))


# ============================================================================
# 02  FENNEC-SOLARE
# ============================================================================

def build_fennec():
    texspace("Fennec")
    K = 1.65
    m_fur = CL.m_body("Fennec_Pelo", (0.72, 0.5, 0.28), rough=0.7, sheen=1.0, sheen_tint=(1.0, 0.85, 0.6),
                      sss=0.15, sss_radius=(1.0, 0.6, 0.3), mottle=((0.9, 0.72, 0.48), 3.0),
                      rim=(1.0, 0.8, 0.4), rim_str=0.35)
    m_belly = CL.m_body("Fennec_Pancia", (0.92, 0.8, 0.62), rough=0.75, sheen=1.0)
    m_eye = CL.m_body("Fennec_Occhi", (0.03, 0.015, 0.005), rough=0.05, coat=1.0)
    m_spark = CL.m_emit("Fennec_Luccichio", (1.0, 0.95, 0.8), 1.5)
    m_nose = CL.m_body("Fennec_Naso", (0.01, 0.01, 0.01), rough=0.15, coat=0.8)
    m_tip = CL.m_body("Fennec_Punta_Coda", (1.0, 0.8, 0.45), rough=0.6, sheen=1.0,
                      emit=(1.0, 0.6, 0.15), emit_str=2.5, emit_pulse=(1.2, 3.5, 1, 0.5))
    m_tip_glow = CL.m_halo("Fennec_Alone_Coda", (1.0, 0.6, 0.15), 2.0, pulse=(1.0, 3.0, 1, 0.5))
    m_ear = CL.m_wing("Fennec_Orecchie_Solari",
                      [(0.0, (1.0, 0.4, 0.02)), (0.5, (1.0, 0.62, 0.05)), (1.0, (1.0, 0.8, 0.2))],
                      alpha=0.1, membrane_str=0.45, vein_ramp=[(0.0, (1.0, 0.75, 0.1)), (1.0, (1.0, 0.92, 0.35))],
                      vein_str=3.5, radial=(9, 0.08), cross=(3, 0.05), edge=0.06, v_mix=1.0,
                      facing_mix=0.2, distort=0.02, pulse=(0.75, 1.25, 1, 0.0))

    E = [ellipsoid((0, 0.12, 0.25), 0.2 * K, (1.05, 1.1, 1.0)),
         ellipsoid((0, -0.06, 0.42), 0.15 * K, (0.95, 0.95, 1.35)),
         capsule((0, -0.1, 0.55), (0, -0.14, 0.68), 0.1 * K),
         ball((0, -0.16, 0.78), 0.135 * K),
         ellipsoid((0, -0.21, 0.74), 0.1 * K, (1.35, 0.9, 0.85)),
         capsule((0, -0.25, 0.735), (0, -0.36, 0.71), 0.045 * K),
         capsule((0, -0.36, 0.71), (0, -0.43, 0.7), 0.028 * K)]
    for sx in (-1, 1):
        E += [capsule((0.06 * sx, -0.11, 0.4), (0.065 * sx, -0.15, 0.05), 0.034 * K),
              ellipsoid((0.065 * sx, -0.18, 0.025), 0.034 * K, (1.0, 1.4, 0.7)),
              ellipsoid((0.12 * sx, 0.12, 0.2), 0.12 * K, (0.8, 1.2, 1.0)),
              ellipsoid((0.11 * sx, -0.05, 0.03), 0.038 * K, (1.0, 1.7, 0.6))]
    body = CL.metaball_mesh("Fennec_Corpo", E, m_fur, res=0.018)
    CL.add_fur(body, 0, count=9000, length=0.022, children=10, radius=0.004, clump=0.1)
    bvh = CL.bvh_of(body)
    head_c = V((0, -0.17, 0.77))

    belly = CL.sphere("Fennec_Pettorina", (0, -0.14, 0.45), (0.1, 0.06, 0.16), m_belly)
    CL.add_fur(belly, 0, count=900, length=0.022, children=10, radius=0.004, clump=0.1)

    # occhi grandi e scuri, naso
    for sx in (-1, 1):
        CL.make_eye("Fennec_Occhio_" + ("L" if sx < 0 else "R"), bvh, head_c, (0.5 * sx, -1.0, 0.22),
                    0.052, m_eye, None, None, sink=0.35, flat=0.75)
        loc, nor = CL.surface_hit(bvh, head_c, (0.5 * sx, -1.0, 0.22))
        CL.sphere("Fennec_Luccichio_" + ("L" if sx < 0 else "R"), loc + nor * 0.035 + V((0.012 * -sx, 0, 0.016)),
                  0.006, m_spark, seg=12, rings=6)
    nl, nn = CL.surface_hit(bvh, V((0, -0.38, 0.71)), (0, -1, 0.15))
    CL.sphere("Fennec_Naso", nl, (0.022, 0.016, 0.016), m_nose)

    # orecchie gigantesche = ali di luce solare rivolte verso l'alto
    ear = [(-52, 0.26), (-38, 0.38), (-20, 0.56), (0, 0.8), (20, 0.56), (38, 0.38), (52, 0.26)]
    ears = CL.wing_pair("Fennec_Orecchio", ear, m_ear, (0.06, -0.13, 0.86), elev=50, sweep=2, roll=80,
                        rings=12, cup=-0.05, flap=(5, 1, 0.0), n=64)
    for ob in ears:                       # orecchie "spesse"
        sd = ob.modifiers.new("Spessore", 'SOLIDIFY')
        sd.thickness = 0.012
        sd.offset = 0.0

    # coda vaporosa che avvolge le zampe, con punta luminosa
    nt = CL.det(40, 16)
    tail = spline([(0, 0.28, 0.12), (0.18, 0.32, 0.08), (0.3, 0.14, 0.06), (0.26, -0.1, 0.06),
                   (0.14, -0.22, 0.07)], nt)
    radii = [0.045 + 0.04 * sin(pi * min(1.0, i / (nt * 0.75))) for i in range(nt)]
    cut = int(nt * 0.85)
    tob, _fr, _l = sweep_mesh("Fennec_Coda", tail[:cut + 1], radii[:cut + 1], m_fur, ring=16)
    CL.add_fur(tob, 0, count=2500, length=0.04, children=12, radius=0.005, clump=0.2)
    tip, _fr2, _l2 = sweep_mesh("Fennec_Coda_Punta", tail[cut:], radii[cut:], m_tip, ring=16)
    CL.add_fur(tip, 0, count=800, length=0.035, children=12, radius=0.005, clump=0.2)
    halo = CL.sphere("Fennec_Alone_Coda", tail[-3], 0.14, m_tip_glow)
    CL.no_shadow(halo)
    CL.add_light("Fennec_Luce_Coda", 'POINT', tail[-3] + V((0, 0, 0.05)), 3.0, (1.0, 0.65, 0.25), 0.1,
                 pulse=(1.5, 5.0, 1, 0.5))
    CL.add_light("Fennec_Luce_Orecchie", 'POINT', (0, -0.1, 1.25), 3.0, (1.0, 0.75, 0.3), 0.4,
                 pulse=(2.0, 4.5, 1, 0.0))


# ============================================================================
# 03  SCARABEO-FORNACE
# ============================================================================

def m_scratched(name, base=(0.012, 0.011, 0.01), gold=(1.0, 0.7, 0.28)):
    """Guscio nero opaco con graffi d'oro (ruvido e un po' metallico)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    mp = nb.node('ShaderNodeMapping')
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    nb.set(mp, 'Scale', (1.0, 7.0, 1.0))
    nb.set(mp, 'Rotation', (0.3, 0.2, 0.5))
    vo = nb.voronoi(mp.outputs[0], 9.0, 'DISTANCE_TO_EDGE')
    lines = nb.maprange(vo.outputs['Distance'], 0.02, 0.004)
    nz = nb.noise(tc.outputs['Object'], 5.0, 4.0, 0.6)
    keep = nb.maprange(nz.outputs['Fac'], 0.45, 0.62)
    wear = nb.maprange(nb.noise(tc.outputs['Object'], 2.0, 6.0, 0.7).outputs['Fac'], 0.62, 0.75, 0.0, 0.8)
    mask = nb.math('MAXIMUM', nb.math('MULTIPLY', lines, keep), wear)
    shell = nb.principled(base=base, rough=0.82, metal=0.35, spec=0.4)
    nb.set(shell, 'Normal', nb.bump(nz.outputs['Fac'], 0.25, 0.01))
    au = nb.principled(base=gold, rough=0.28, metal=1.0)
    nb.output(nb.mix_shader(mask, shell.outputs[0], au.outputs[0]))
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(base, 1.0), nb.emission(gold, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = 0.7
    mat["rbx_metal"] = 0.4
    CL.diffuse_display(mat, (0.05, 0.045, 0.04))
    return mat


def build_scarab():
    texspace("Scarabeo")
    m_shell = m_scratched("Scarabeo_Guscio")
    m_ember = m_lava("Scarabeo_Addome_Brace", scale=11.0, crack=0.09, strength=5.0,
                     pulse=(3.0, 7.0, 2, 0.0))
    m_ball = m_magma("Scarabeo_Sfera_Magma", 2.2, pulse=(1.8, 3.0, 1, 0.0))
    m_ball_glow = CL.m_halo("Scarabeo_Alone_Sfera", (1.0, 0.3, 0.02), 0.5, pulse=(0.3, 0.8, 1, 0.0))
    m_wing = CL.m_wing("Scarabeo_Ali_Membrana",
                       [(0.0, (0.25, 0.1, 0.02)), (1.0, (0.6, 0.3, 0.05))], alpha=0.15, membrane_str=0.15,
                       vein_ramp=[(0.0, (1.0, 0.45, 0.05)), (1.0, (1.0, 0.6, 0.1))], vein_str=1.8,
                       radial=(5, 0.07), cross=(2, 0.04), edge=0.05, v_mix=1.0)

    # sfera perfetta di luce densa come magma, che rotola
    BC, BR = V((0, -0.52, 0.34)), 0.34
    ball_ob = CL.sphere("Scarabeo_Sfera", BC, BR, m_ball, seg=64, rings=32)
    halo = CL.sphere("Scarabeo_Alone", BC, BR * 1.35, m_ball_glow)
    CL.no_shadow(halo)
    CL.no_shadow(ball_ob)
    piv = pivot("Scarabeo_Sfera_Perno", BC, [ball_ob])
    spin(piv, 0, -1, 0.0)
    CL.add_light("Scarabeo_Luce_Sfera", 'POINT', BC, 45.0, (1.0, 0.42, 0.08), BR * 0.9,
                 pulse=(35.0, 55.0, 1, 0.0))
    CL.add_light("Scarabeo_Luce_Bassa", 'POINT', (0, -0.15, 0.03), 10.0, (1.0, 0.4, 0.06), 0.2,
                 pulse=(6.0, 14.0, 1, 0.0))

    # corpo corazzato
    CL.sphere("Scarabeo_Pronoto", (0, 0.0, 0.2), (0.19, 0.14, 0.11), m_shell)
    CL.sphere("Scarabeo_Testa", (0, -0.16, 0.16), (0.16, 0.09, 0.045), m_shell, rot=(-12, 0, 0))
    for i in range(6):
        x = (i - 2.5) * 0.045
        CL.cone_between("Scarabeo_Dente_%d" % i, (x, -0.22, 0.15), (x * 1.12, -0.28, 0.16), 0.018, 0.0,
                        m_shell, 8)
    CL.sphere("Scarabeo_Addome", (0, 0.2, 0.17), (0.17, 0.25, 0.1), m_ember)
    CL.add_light("Scarabeo_Luce_Addome", 'POINT', (0, 0.22, 0.33), 6.0, (1.0, 0.35, 0.05), 0.12,
                 pulse=(3.0, 8.0, 2, 0.0))
    # elitre aperte (rivelano l'addome che brucia)
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        CL.sphere("Scarabeo_Elitra_" + s, (0.16 * sx, 0.2, 0.3), (0.11, 0.25, 0.04), m_shell,
                  rot=(18, -42 * sx, 8 * sx))
    CL.wing_pair("Scarabeo_Ala", [(-10, 0.15), (0, 0.45), (15, 0.55), (35, 0.5), (55, 0.3), (65, 0.1)],
                 m_wing, (0.06, 0.08, 0.28), elev=22, sweep=58, roll=-15, rings=10, flap=(6, 3, 0.0))
    # antenne a ventaglio
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        b = V((0.07 * sx, -0.19, 0.17))
        t = b + V((0.05 * sx, -0.06, 0.03))
        CL.tube("Scarabeo_Antenna_" + s, [b, t], [0.008, 0.006], m_shell, bevel_res=1)
        for k in range(3):
            CL.sphere("Scarabeo_Lamella_%s%d" % (s, k), t + V((0.006 * k * sx, -0.012 * k, 0.004 * k)),
                      (0.014, 0.006, 0.012), m_shell, seg=12, rings=6)
    # zampe: le anteriori spingono la sfera
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        A = V((0.12 * sx, -0.08, 0.14))
        K = V((0.24 * sx, -0.18, 0.26))
        d = V((0.2 * sx, 0.3, 0.2)).normalized()
        T = BC + d * (BR + 0.012)
        leg("Scarabeo_ZampaAnt_" + s, [A, K, T], [0.028, 0.026, 0.016], m_shell)
        for k in range(3):
            p = K.lerp(T, 0.35 + 0.2 * k)
            CL.cone_between("Scarabeo_Dentino_%s%d" % (s, k), p, p + V((0.035 * sx, 0.005, -0.01)), 0.01, 0.0,
                            m_shell, 6)
        A = V((0.15 * sx, 0.06, 0.12))
        leg("Scarabeo_ZampaMed_" + s, [A, A + V((0.2 * sx, -0.02, 0.1)), A + V((0.3 * sx, -0.1, -0.12))],
            [0.025, 0.022, 0.012], m_shell)
        A = V((0.14 * sx, 0.18, 0.11))
        leg("Scarabeo_ZampaPost_" + s, [A, A + V((0.2 * sx, 0.12, 0.1)), A + V((0.25 * sx, 0.3, -0.11))],
            [0.025, 0.022, 0.012], m_shell)


# ============================================================================
# 04  VIPERA-SONAGLIO LUMINOSO
# ============================================================================

def frames_up(pts):
    """Come frames_along, ma con la normale rivolta il piu' possibile verso
    l'alto: v = 0 corrisponde al dorso, v = 0.5 al ventre."""
    tans, norms, _b = frames_along(pts)
    up = V((0, 0, 1))
    out_n = []
    prev = None
    for t, n0 in zip(tans, norms):
        if abs(t.dot(up)) < 0.85:
            n = (up - t * up.dot(t)).normalized()
        else:
            n = prev if prev is not None else n0
            n = (n - t * n.dot(t)).normalized()
        out_n.append(n)
        prev = n
    binors = [t.cross(n).normalized() for t, n in zip(tans, out_n)]
    return tans, out_n, binors


def m_snake(name, length_ratio=15.0):
    """Squame di serpente (UV: u lungo il corpo, v attorno) con rombi dorsali,
    ventre chiaro e rilievo forte (diventa una normal map per Roblox)."""
    mat = CL.new_material(name)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    rows = 18.0
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('MULTIPLY', u, rows * length_ratio), cmb.inputs[0])
    nb.link(nb.math('MULTIPLY', v, rows), cmb.inputs[1])
    vo = nb.voronoi(cmb.outputs[0], 1.0, 'F1', randomness=0.25)
    scale_h = nb.maprange(vo.outputs['Distance'], 0.0, 0.62, 1.0, 0.0)
    scale_h = nb.math('POWER', scale_h, 0.6)
    edge = nb.voronoi(cmb.outputs[0], 1.0, 'DISTANCE_TO_EDGE', randomness=0.25)
    grooves = nb.maprange(edge.outputs['Distance'], 0.0, 0.08)
    height = nb.math('MULTIPLY', scale_h, grooves)
    # rombi sul dorso
    dv = nb.math('MULTIPLY', nb.math('MINIMUM', v, nb.math('SUBTRACT', 1.0, v)), 4.0)
    du = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT',
                 nb.math('FRACT', nb.math('MULTIPLY', u, length_ratio * 1.6)), 0.5)), 2.0)
    dia = nb.math('ADD', du, nb.math('MULTIPLY', dv, 1.1))
    inner = nb.maprange(dia, 0.72, 0.62)
    border = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', dia, 0.8)), 0.09, 0.04)
    belly = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.5)), 0.2, 0.12)
    base = (0.36, 0.13, 0.05)
    col = nb.ramp(inner, [(0.0, base), (1.0, (0.16, 0.055, 0.02))])
    mixb = nb.node('ShaderNodeMix', data_type='RGBA')
    nb.link(border, mixb.inputs[0])
    nb.link(col, mixb.inputs[6])
    nb.set(mixb, 7, (0.62, 0.4, 0.24, 1.0))
    mixc = nb.node('ShaderNodeMix', data_type='RGBA')
    nb.link(belly, mixc.inputs[0])
    nb.link(mixb.outputs[2], mixc.inputs[6])
    nb.set(mixc, 7, (0.62, 0.48, 0.32, 1.0))
    final = mixc.outputs[2]
    bsdf = nb.principled(base=final, rough=0.78, spec=0.35, sheen=0.2)
    nb.set(bsdf, 'Normal', nb.bump(height, 0.9, 0.02))
    nb.output(bsdf.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(final, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_normal"] = 1
    mat["rbx_res"] = [4096, 512]
    mat["rbx_rough"] = 0.78
    CL.diffuse_display(mat, base)
    return mat


def build_viper():
    texspace("Vipera")
    r0 = 0.065
    m_skin = m_snake("Vipera_Squame_Terracotta")
    m_head = CL.m_body("Vipera_Testa", (0.33, 0.12, 0.05), rough=0.75, bump=(70.0, 0.5, 'scales'))
    m_eye = CL.m_radial_glow("Vipera_Occhi", [(0.0, (1.0, 0.85, 0.2)), (0.7, (0.9, 0.55, 0.05)),
                                              (1.0, (0.3, 0.12, 0.0))], 1.2)
    m_pupil = CL.m_body("Vipera_Pupilla", (0.0, 0.0, 0.0), rough=0.05, coat=1.0)
    m_tongue = CL.m_body("Vipera_Lingua", (0.5, 0.02, 0.05), rough=0.3, coat=0.8)
    m_sep = CL.m_body("Vipera_Anelli_Scuri", (0.05, 0.04, 0.02), rough=0.5)
    green = (0.6, 1.0, 0.08)
    n_ph = 8
    m_stripe = [CL.m_emit("Vipera_Striscia_%d" % k, green, 3.0, pulse=(0.05, 3.0, 2, -TAU * k / n_ph))
                for k in range(n_ph)]
    m_ring = [CL.m_emit("Vipera_Sonaglio_%d" % k, (0.75, 1.0, 0.12), 4.0, pulse=(0.3, 4.0, 3, -TAU * k / 7))
              for k in range(7)]
    m_rattle_glow = CL.m_halo("Vipera_Alone_Sonaglio", (0.6, 1.0, 0.1), 1.5, pulse=(0.6, 2.0, 3, 0.0))

    # percorso: punta della coda (sonaglio) -> spirale a terra -> collo -> testa
    rb = V((0.6, 0.18, 0.26))
    ctrl = [rb, V((0.6, 0.12, 0.12)), V((0.57, 0.02, r0))]
    th0 = math.atan2(0.02, 0.57)
    loops = 1.75
    for i in range(1, 29):
        t = i / 28
        th = th0 + TAU * loops * t
        R = 0.57 - 0.3 * t
        ctrl.append(V((R * cos(th), R * sin(th), r0 + 0.03 * t)))
    end = ctrl[-1]
    ctrl += [V((end.x * 0.55, end.y * 0.55, 0.16)), V((0.05, 0.1, 0.3)), V((0.02, 0.02, 0.42)),
             V((0.0, -0.08, 0.48)), V((0.0, -0.16, 0.5))]
    path = spline(ctrl, CL.det(460, 90))
    n = len(path)
    radii = []
    for i in range(n):
        t = i / (n - 1)
        r = r0 * min(1.0, 0.35 + t * 6.0) * (1.0 - 0.35 * max(0.0, (t - 0.88) / 0.12))
        radii.append(r)
    fr = frames_up(path)
    lengths = [0.0]
    for i in range(1, n):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    sweep_mesh("Vipera_Corpo", path, radii, m_skin, ring=20, squash=0.88, frames=fr)

    # strisce laterali che si accendono in sequenza verso la coda
    tans, norms, binors = fr
    seg_len = 0.16
    i0 = int(n * 0.1)
    i_end = int(n * 0.93)
    cuts = [i0]
    while cuts[-1] < i_end:
        target = lengths[cuts[-1]] + seg_len
        j = cuts[-1]
        while j < i_end and lengths[j] < target:
            j += 1
        cuts.append(j)
    nseg = len(cuts) - 1
    for side in (1, -1):
        for si in range(nseg):
            a, b = cuts[si], cuts[si + 1] - 1
            if b - a < 2:
                continue
            pts = [path[i] + binors[i] * side * radii[i] * 0.86 + norms[i] * radii[i] * 0.2
                   for i in range(a, b + 1)]
            from_head = nseg - 1 - si
            mat = m_stripe[from_head % n_ph]
            ob = CL.tube("Vipera_Striscia_%s%02d" % ("L" if side < 0 else "R", si), pts, 0.008, mat,
                         bevel_res=1, poly=True)
            CL.no_shadow(ob)

    # sonaglio: anelli di lucciola indipendenti
    rdir = (path[0] - path[3]).normalized()
    p = path[0]
    for kk in range(7):
        rr = 0.036 - 0.0025 * kk
        c = p + rdir * (0.022 + 0.036 * kk)
        segment("Vipera_AnelloLuce_%d" % kk, c, rdir, rr, 0.034, m_ring[kk], flat=1.0)
        segment("Vipera_AnelloScuro_%d" % kk, c + rdir * 0.018, rdir, rr * 0.82, 0.008, m_sep, flat=1.0)
    halo = CL.sphere("Vipera_Alone", p + rdir * 0.13, 0.17, m_rattle_glow)
    CL.no_shadow(halo)
    CL.add_light("Vipera_Luce_Sonaglio", 'POINT', p + rdir * 0.13, 6.0, (0.6, 1.0, 0.15), 0.08,
                 pulse=(2.0, 9.0, 3, 0.0))

    # testa triangolare, occhi a fessura, lingua biforcuta
    hd = (path[-1] - path[-6]).normalized()
    hc = path[-1] + hd * 0.05
    head = segment("Vipera_Testa", hc, hd, 0.075, 0.2, m_head, flat=0.55)
    head.name = "Vipera_Testa"
    tp = head.modifiers.new("Triangolo", 'SIMPLE_DEFORM')
    tp.deform_method = 'TAPER'
    tp.deform_axis = 'Y'
    tp.factor = -0.55
    side_v = hd.cross(V((0, 0, 1))).normalized()
    for sx in (-1, 1):
        ec = hc + side_v * sx * 0.058 + V((0, 0, 0.022)) - hd * 0.01
        e = CL.sphere("Vipera_Occhio_%s" % ("L" if sx < 0 else "R"), (0, 0, 0), 1.0, m_eye, seg=20, rings=10)
        place_on(e, ec, side_v * sx + V((0, 0, 0.3)), scale=(0.018, 0.018, 0.012))
        pp = CL.sphere("Vipera_Pupilla_%s" % ("L" if sx < 0 else "R"), (0, 0, 0), 1.0, m_pupil, seg=12, rings=6)
        place_on(pp, ec + (side_v * sx) * 0.011, side_v * sx, scale=(0.003, 0.013, 0.003))
    mouth = hc + hd * 0.095 + V((0, 0, -0.012))
    tongue_pts = [mouth, mouth + hd * 0.06 + V((0, 0, -0.005)), mouth + hd * 0.1 + V((0, 0, 0.004))]
    t1 = CL.tube("Vipera_Lingua", tongue_pts, [0.006, 0.005, 0.004], m_tongue, bevel_res=1)
    f = tongue_pts[-1]
    t2 = CL.tube("Vipera_Lingua_PuntaL", [f, f + hd * 0.035 + side_v * 0.018], [0.004, 0.0015], m_tongue, bevel_res=1)
    t3 = CL.tube("Vipera_Lingua_PuntaR", [f, f + hd * 0.035 - side_v * 0.018], [0.004, 0.0015], m_tongue, bevel_res=1)
    tpiv = pivot("Vipera_Lingua_Perno", mouth, [t1, t2, t3])
    wobble(tpiv, 0, 14, 6, 0.0)
    CL.add_light("Vipera_Luce_Strisce", 'POINT', (0, 0, 0.5), 3.0, green, 0.5, pulse=(1.5, 4.0, 2, 0.0))


# ============================================================================
# 05  LUCERTOLA-CRISTALLO
# ============================================================================

def build_lizard():
    texspace("Lucertola")
    K = 1.65
    m_skin = CL.m_body("Lucertola_Pelle", (0.38, 0.19, 0.08), rough=0.65,
                       mottle=((0.7, 0.45, 0.2), 4.5), bump=(22.0, 0.45, 'warts'), sss=0.1,
                       sss_radius=(1.0, 0.5, 0.3))
    m_eye = CL.m_body("Lucertola_Occhi", (0.02, 0.01, 0.0), rough=0.05, coat=1.0,
                      emit=(1.0, 0.4, 0.05), emit_str=0.3)
    cry = [m_crystal("Lucertola_Cristallo_Rosso", (0.8, 0.06, 0.02), (1.0, 0.04, 0.0), 0.8, pulse=(0.3, 1.2, 3, 0.0)),
           m_crystal("Lucertola_Cristallo_Brace", (0.85, 0.15, 0.02), (1.0, 0.14, 0.0), 0.8, pulse=(0.3, 1.2, 4, 1.7)),
           m_crystal("Lucertola_Cristallo_Arancio", (0.9, 0.3, 0.04), (1.0, 0.3, 0.01), 0.8, pulse=(0.3, 1.2, 5, 3.1))]
    m_wing = CL.m_wing("Lucertola_Alucce", [(0.0, (1.0, 0.5, 0.2)), (1.0, (1.0, 0.8, 0.5))], alpha=0.05,
                       membrane_str=0.12, vein_str=2.0, radial=(5, 0.08), edge=0.08, v_mix=1.0)

    E = [ellipsoid((0, 0.05, 0.16), 0.22 * K, (1.1, 1.45, 0.6)),
         ellipsoid((0, -0.3, 0.16), 0.105 * K, (1.0, 1.15, 0.75)),
         ball((0, -0.17, 0.25), 0.07 * K),
         capsule((0, 0.35, 0.13), (0, 0.72, 0.06), 0.06 * K),
         capsule((0, 0.72, 0.06), (0.08, 0.98, 0.035), 0.035 * K)]
    for sx in (-1, 1):
        E += [capsule((0.15 * sx, -0.12, 0.14), (0.3 * sx, -0.2, 0.08), 0.045 * K),
              capsule((0.3 * sx, -0.2, 0.08), (0.33 * sx, -0.3, 0.02), 0.032 * K),
              capsule((0.16 * sx, 0.22, 0.13), (0.32 * sx, 0.3, 0.08), 0.05 * K),
              capsule((0.32 * sx, 0.3, 0.08), (0.35 * sx, 0.4, 0.02), 0.034 * K)]
    body = CL.metaball_mesh("Lucertola_Corpo", E, m_skin, res=0.018)
    bvh = CL.bvh_of(body)
    for sx in (-1, 1):
        CL.make_eye("Lucertola_Occhio_" + ("L" if sx < 0 else "R"), bvh, V((0, -0.3, 0.17)),
                    (0.8 * sx, -0.5, 0.35), 0.026, m_eye, None, None, sink=0.3, flat=0.8)

    # spine di cristallo piantate nel corpo
    random.seed(5)
    zones = [(V((0, 0.05, 0.12)), 34, 0.07, 0.13, 0.018, 0.028, 0.25),
             (V((0, -0.3, 0.14)), 10, 0.035, 0.06, 0.012, 0.018, 0.35),
             (V((0, -0.17, 0.22)), 6, 0.06, 0.1, 0.016, 0.024, 0.2),
             (V((0, 0.55, 0.1)), 14, 0.035, 0.07, 0.012, 0.02, 0.3)]
    placed = []
    idx = 0
    for center, count, lmin, lmax, rmin, rmax, zmin in zones:
        tries = 0
        made = 0
        while made < count and tries < count * 30:
            tries += 1
            d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(zmin, 1.0)))
            if d.length < 0.2:
                continue
            loc, nor = CL.surface_hit(bvh, center, d)
            if loc is None or nor.z < 0.15 or any((loc - q).length < rmax * 2.2 for q in placed):
                continue
            placed.append(loc)
            L = random.uniform(lmin, lmax)
            me = crystal_mesh("Lucertola_Cristallo_%03d" % idx, L, random.uniform(rmin, rmax), seed=idx)
            me.materials.append(cry[idx % 3])
            ob = bpy.data.objects.new(me.name, me)
            CL.link(ob)
            tilt = V((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), 0))
            axis = (nor * 0.6 + V((0, 0, 0.4)) + tilt).normalized()
            yv = V((random.uniform(-1, 1), random.uniform(-1, 1), 0.01))
            place_on(ob, loc - nor * 0.004, axis, yv)
            idx += 1
            made += 1
    # due grandi corna di cristallo sopra gli occhi
    for sx in (-1, 1):
        loc, nor = CL.surface_hit(bvh, V((0, -0.3, 0.17)), (0.6 * sx, -0.2, 0.9))
        me = crystal_mesh("Lucertola_Corno_%s" % ("L" if sx < 0 else "R"), 0.11, 0.024, seed=90 + sx)
        me.materials.append(cry[0])
        ob = bpy.data.objects.new(me.name, me)
        CL.link(ob)
        place_on(ob, loc, (nor + V((0.5 * sx, 0.2, 0.6))).normalized())

    # minuscole alucce che battono velocissime
    CL.wing_pair("Lucertola_Aluccia", [(-20, 0.08), (-5, 0.2), (15, 0.24), (40, 0.2), (60, 0.08)],
                 m_wing, (0.1, -0.12, 0.25), elev=40, sweep=35, roll=20, rings=6, flap=(28, 60, 0.0))
    CL.add_light("Lucertola_Luce_Brace", 'POINT', (0, 0.05, 0.55), 5.0, (1.0, 0.3, 0.05), 0.4,
                 pulse=(3.0, 7.0, 3, 0.0))
    CL.add_light("Lucertola_Luce_Terra", 'POINT', (0, -0.1, 0.05), 3.0, (1.0, 0.3, 0.05), 0.2,
                 pulse=(2.0, 4.0, 4, 1.0))


# ============================================================================
# 06  AVVOLTOIO-MIRAGGIO
# ============================================================================

def build_vulture():
    texspace("Avvoltoio")
    K = 1.65
    oasis = (0.3, 0.85, 1.0)
    m_rock = CL.m_body("Avvoltoio_Roccia", (0.28, 0.16, 0.09), rough=0.9,
                       mottle=((0.4, 0.26, 0.15), 2.5), bump=(9.0, 0.6, 'warts'))
    m_feath = CL.m_body("Avvoltoio_Piumaggio", (0.06, 0.04, 0.028), rough=0.7, sheen=0.8,
                        sheen_tint=(0.8, 0.7, 0.6), bump=(70.0, 0.25, 'scales'))
    m_skin = CL.m_body("Avvoltoio_Pelle_Nuda", (0.5, 0.33, 0.32), rough=0.6, sss=0.3,
                       sss_radius=(1.0, 0.4, 0.3), bump=(40.0, 0.3, 'warts'))
    m_beak = CL.m_body("Avvoltoio_Becco", (0.7, 0.6, 0.42), rough=0.3, coat=0.8)
    m_eye = CL.m_body("Avvoltoio_Occhi", (0.02, 0.015, 0.01), rough=0.05, coat=1.0,
                      emit=oasis, emit_str=0.4)
    m_talon = CL.m_body("Avvoltoio_Artigli", (0.12, 0.11, 0.1), rough=0.4, coat=0.5)
    m_ruff = m_glowfeather("Avvoltoio_Collare_Luce", (1.0, 1.0, 1.0), oasis, 4.0, pulse=(2.0, 6.0, 1, 0.0))
    m_mir = m_mirage("Avvoltoio_Ali_Miraggio", (0.8, 0.94, 1.0), oasis)
    m_edge = CL.m_emit("Avvoltoio_Bordo_Ali", (0.55, 0.92, 1.0), 3.0, pulse=(1.8, 3.6, 1, 0.8))

    rk = rock("Avvoltoio_Roccia", (0, 0.1, 0.22), (0.62, 0.5, 0.32), m_rock, seed=3, rough=0.3)
    rb = CL.bvh_of(rk)
    top, _n = CL.surface_hit(rb, V((0, 0.05, 0.2)), (0, 0, 1))
    h = top.z - 0.02

    E = [ellipsoid((0, -0.02, h + 0.4), 0.19 * K, (1.05, 1.1, 1.15)),
         ellipsoid((0, 0.14, h + 0.36), 0.16 * K, (1.0, 1.25, 0.95)),
         ellipsoid((0, 0.36, h + 0.18), 0.08 * K, (0.95, 1.9, 0.4))]
    for sx in (-1, 1):
        E.append(ellipsoid((0.08 * sx, 0.02, h + 0.17), 0.09 * K, (1.0, 1.0, 1.3)))
        # spalle rialzate (postura curva da avvoltoio)
        E.append(ellipsoid((0.15 * sx, 0.04, h + 0.55), 0.1 * K, (0.9, 1.3, 0.8)))
    CL.metaball_mesh("Avvoltoio_Corpo", E, m_feath, res=0.024)

    # collo nudo, testa, becco uncinato
    CL.tube("Avvoltoio_Collo", [(0, -0.04, h + 0.6), (0, -0.1, h + 0.72), (0, -0.15, h + 0.8)],
            [0.05, 0.042, 0.04], m_skin, bevel_res=4)
    hc = V((0, -0.19, h + 0.84))
    CL.sphere("Avvoltoio_Testa", hc, (0.075, 0.095, 0.07), m_skin)
    CL.tube("Avvoltoio_Becco", [hc + V((0, -0.06, 0.005)), hc + V((0, -0.13, 0.0)),
                                hc + V((0, -0.16, -0.035)), hc + V((0, -0.14, -0.06))],
            [0.028, 0.02, 0.012, 0.004], m_beak, bevel_res=3)
    for sx in (-1, 1):
        CL.sphere("Avvoltoio_Occhio_%s" % ("L" if sx < 0 else "R"), hc + V((0.05 * sx, -0.03, 0.02)),
                  0.014, m_eye, seg=16, rings=8)

    # collare di piume fatte di luce azzurro-oasi
    f1 = CL.feather_mesh("Avvoltoio_PiumaLuce", 0.2, 0.085, m_ruff, rows=6, cols=4, curl=0.1)
    c0 = V((0, -0.05, h + 0.62))
    for layer, (n, down, sc) in enumerate(((22, 0.35, 1.0), (16, 0.1, 0.75))):
        for k in range(n):
            a = TAU * (k + 0.5 * layer) / n
            d = V((cos(a), sin(a) * 0.9, -down)).normalized()
            ob = bpy.data.objects.new("Avvoltoio_Collare_%d_%02d" % (layer, k), f1)
            CL.link(ob)
            place_on(ob, c0 + d * 0.05 + V((0, 0, 0.02 * layer)), (V((0, 0, 1)) - d * 0.3).normalized(), d,
                     scale=(sc, sc, sc))
            CL.no_shadow(ob)
    CL.add_light("Avvoltoio_Luce_Collare", 'POINT', c0 + V((0, -0.15, 0.05)), 5.0, oasis, 0.2,
                 pulse=(2.5, 8.0, 1, 0.0))

    # zampe e artigli sulla roccia
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        a = V((0.08 * sx, 0.0, h + 0.14))
        b = V((0.085 * sx, -0.04, h + 0.02))
        CL.tube("Avvoltoio_Zampa_" + s, [a, b], [0.022, 0.018], m_skin, bevel_res=2)
        for k, ang in enumerate((-30, 0, 30)):
            d = V((sin(radians(ang)), -cos(radians(ang)), 0))
            CL.tube("Avvoltoio_Dito_%s%d" % (s, k), [b, b + d * 0.07 + V((0, 0, -0.01)),
                                                     b + d * 0.1 + V((0, 0, -0.03))],
                    [0.012, 0.009, 0.003], m_talon, bevel_res=1)

    # ali immense, trasparenti e ondulate come un miraggio, con il bordo acceso
    wing = [(-6, 0.25), (-2, 0.9), (4, 1.35), (12, 1.5), (22, 1.46), (34, 1.3), (48, 1.0),
            (60, 0.65), (70, 0.28)]
    wing_pair_edges("Avvoltoio_Ala", wing, m_mir, m_edge, (0.12, 0.02, h + 0.52), elev=22, sweep=14,
                    roll=62, rings=12, flap=(5, 1, 0.0), scallop=(0.12, 7), edge_r=0.01, wave=(0.05, 7.0))
    CL.add_light("Avvoltoio_Luce_Ali", 'POINT', (0, 0.2, h + 1.1), 6.0, oasis, 0.6, pulse=(4.0, 8.0, 1, 0.8))


# ============================================================================
# 07  TARANTOLA-BRACE
# ============================================================================

def project_uv_top(ob):
    """UV proiettate dall'alto (coordinate locali x, y) per i pattern 'a sole'."""
    me = ob.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (0.5 + co.x * 0.5, 0.5 + co.y * 0.5)


def build_tarantula():
    texspace("Tarantola")
    m_carapace = m_lava("Tarantola_Carapace_Sole", scale=6.0, crack=0.035, strength=4.0,
                        pulse=(2.5, 5.0, 1, 0.0), uv=True, sun=(12, 0.16))
    m_abd = m_lava("Tarantola_Addome_Lava", scale=5.5, crack=0.07, strength=5.0, pulse=(3.0, 6.5, 1, 0.9))
    m_leg = m_lava("Tarantola_Zampe", scale=16.0, crack=0.03, strength=2.5, pulse=(1.5, 3.5, 1, 0.3))
    m_joint = CL.m_emit("Tarantola_Giunture_Lava", (1.0, 0.32, 0.02), 4.0, pulse=(2.0, 6.0, 1, 0.4))
    m_eye = CL.m_body("Tarantola_Occhi", (0.0, 0.0, 0.0), rough=0.03, coat=1.0,
                      emit=(1.0, 0.3, 0.05), emit_str=0.25)
    m_fang = CL.m_body("Tarantola_Zanne", (0.02, 0.015, 0.012), rough=0.25, coat=0.8,
                       emit=(1.0, 0.3, 0.02), emit_str=0.6)

    ceph = CL.sphere("Tarantola_Cefalotorace", (0, -0.1, 0.22), (0.2, 0.23, 0.095), m_carapace, seg=48, rings=24)
    project_uv_top(ceph)
    CL.sphere("Tarantola_Peduncolo", (0, 0.13, 0.22), (0.07, 0.06, 0.06), m_leg)
    CL.sphere("Tarantola_Addome", (0, 0.36, 0.27), (0.26, 0.32, 0.22), m_abd, seg=48, rings=24)
    CL.add_light("Tarantola_Luce_Addome", 'POINT', (0, 0.36, 0.62), 10.0, (1.0, 0.35, 0.05), 0.3,
                 pulse=(5.0, 14.0, 1, 0.9))
    CL.add_light("Tarantola_Luce_Sole", 'POINT', (0, -0.1, 0.55), 5.0, (1.0, 0.45, 0.08), 0.2,
                 pulse=(3.0, 7.0, 1, 0.0))
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        c = V((0.05 * sx, -0.32, 0.17))
        CL.sphere("Tarantola_Chelicera_" + s, c, (0.05, 0.07, 0.06), m_leg)
        CL.cone_between("Tarantola_Zanna_" + s, c + V((0, -0.04, -0.03)), c + V((0.0, -0.02, -0.12)), 0.016,
                        0.0, m_fang, 8)
    for i, (x, y) in enumerate(((-0.03, -0.26), (0.03, -0.26), (-0.015, -0.24), (0.015, -0.24),
                                (-0.05, -0.25), (0.05, -0.25), (-0.04, -0.22), (0.04, -0.22))):
        CL.sphere("Tarantola_Occhio_%d" % i, (x, y, 0.31 - abs(x) * 0.4), 0.012 if i < 2 else 0.008,
                  m_eye, seg=12, rings=6)
    # otto zampe con articolazioni di lava + pedipalpi
    for sx in (-1, 1):
        s = "L" if sx < 0 else "R"
        for k, ang in enumerate((-38, -12, 16, 44)):
            a = radians(ang)
            d = V((sx * cos(a), sin(a), 0))
            A = V((0, -0.1, 0.2)) + d * 0.17
            Kn = A + d * 0.3 + V((0, 0, 0.24))
            T = A + d * 0.62 + V((0, 0, 0.1))
            F = A + d * 0.8 + V((0, 0, -0.2))
            leg("Tarantola_Zampa_%s%d" % (s, k), [A, Kn, T, F], [0.042, 0.036, 0.028, 0.014], m_leg,
                joint_mat=m_joint, joint_r=0.034)
        A = V((0.07 * sx, -0.3, 0.18))
        leg("Tarantola_Pedipalpo_" + s, [A, A + V((0.08 * sx, -0.14, 0.08)), A + V((0.1 * sx, -0.26, -0.15))],
            [0.03, 0.026, 0.02], m_leg, joint_mat=m_joint, joint_r=0.03)


# ============================================================================
# 08  IL CACTUS "CHILL GUY"
# ============================================================================

def box(name, center, size, mat, bevel=0.0, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect='EDGES')
    ob = CL.mesh_object(name, bm, mat, smooth=False)
    ob.location = center
    ob.scale = size
    if rot is not None:
        ob.rotation_euler = [radians(a) for a in rot]
    return ob


def build_cactus():
    texspace("Cactus")
    m_pot = CL.m_body("Cactus_Vaso_Terracotta", (0.46, 0.17, 0.07), rough=0.88,
                      mottle=((0.6, 0.27, 0.12), 6.0), bump=(30.0, 0.35, 'noise'))
    m_soil = CL.m_body("Cactus_Terra", (0.06, 0.04, 0.025), rough=0.95, bump=(40.0, 0.5, 'warts'))
    m_green = CL.m_body("Cactus_Verde", (0.06, 0.2, 0.05), rough=0.55, sss=0.15,
                        sss_radius=(0.3, 1.0, 0.3), coat=0.2, bump=(60.0, 0.1, 'noise'))
    m_spine = CL.m_body("Cactus_Spine", (0.85, 0.72, 0.42), rough=0.4)
    m_wool = CL.m_body("Cactus_Lanugine", (0.9, 0.85, 0.7), rough=0.9, sheen=1.0)
    m_decal = CL.m_body("Cactus_Faccia_Decal", (0.008, 0.008, 0.008), rough=0.95)
    m_mirror = CL.m_body("Cactus_Occhiali_Specchio", (0.55, 0.6, 0.75), rough=0.03, metal=1.0,
                         emit=(0.55, 0.35, 1.0), emit_str=0.25)
    m_mirror["rbx_rifl"] = 0.8
    m_wood = CL.m_body("Cactus_Stuzzicadenti", (0.75, 0.58, 0.36), rough=0.7)
    m_metal = CL.m_body("Cactus_Faretto_Metallo", (0.07, 0.07, 0.08), rough=0.35, metal=0.9)
    m_chrome = CL.m_body("Cactus_Cromo", (0.8, 0.8, 0.82), rough=0.1, metal=1.0)
    m_led = CL.m_emit("Cactus_Faretto_Luce", (0.92, 0.96, 1.0), 60.0, pulse=(50.0, 60.0, 16, 0.0))
    m_wing = CL.m_wing("Cactus_Ali_Mosca",
                       [(0.0, (0.35, 0.55, 1.0)), (0.45, (0.8, 0.4, 1.0)), (0.8, (0.35, 1.0, 0.6)),
                        (1.0, (1.0, 0.9, 0.5))],
                       alpha=0.05, membrane_str=0.05, vein_ramp=[(0.0, (0.03, 0.02, 0.02)), (1.0, (0.05, 0.03, 0.02))],
                       vein_str=1.0, radial=(6, 0.06), cross=(4, 0.035), edge=0.03, v_mix=0.3, facing_mix=0.7)

    # vasetto di terracotta sbeccato
    def chip(co, a, k):
        da = (a - 0.6 + pi) % TAU - pi
        if k >= 3 and abs(da) < 0.28:
            f = (1 - abs(da) / 0.28) ** 1.5
            co = V((co.x * (1 - 0.04 * f), co.y * (1 - 0.04 * f), co.z - 0.07 * f))
        return co
    prof = [(0.17, 0.0), (0.19, 0.02), (0.245, 0.3), (0.29, 0.305), (0.295, 0.4), (0.255, 0.405), (0.25, 0.37)]
    lathe("Cactus_Vaso", prof, m_pot, seg=64, deform=chip)
    CL.sphere("Cactus_Terra", (0, 0, 0.365), (0.25, 0.25, 0.025), m_soil)
    for i, (x, y) in enumerate(((0.16, 0.1), (-0.14, 0.14), (0.1, -0.17))):
        CL.sphere("Cactus_Sassolino_%d" % i, (x, y, 0.385), (0.025, 0.02, 0.014), m_pot)

    # cactus a palla con costole
    C, R = V((0, 0, 0.6)), 0.27
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=max(32, CL.det(96, 32)), v_segments=CL.det(40, 12), radius=1.0)
    for v in bm.verts:
        th = math.atan2(v.co.y, v.co.x)
        rib = 1.0 + 0.065 * cos(16 * th)
        v.co = V((v.co.x * rib * R, v.co.y * rib * R, v.co.z * R * 0.86)) + C
    CL.mesh_object("Cactus_Palla", bm, m_green)
    # spine sulle creste (niente spine sulla faccia)
    idx = 0
    for i in range(16):
        th = TAU * i / 16
        for phi_deg in range(22, 150, 17):
            phi = radians(phi_deg)
            front = abs(((th + pi / 2 + pi) % TAU) - pi) < 0.75 and 55 < phi_deg < 125
            if front:
                continue
            p = C + V((sin(phi) * cos(th) * R * 1.065, sin(phi) * sin(th) * R * 1.065, cos(phi) * R * 0.86))
            nrm = (p - C).normalized()
            CL.sphere("Cactus_Areola_%03d" % idx, p, 0.012, m_wool, seg=8, rings=4)
            for k, (dx, dz) in enumerate(((0.35, 0.25), (-0.35, 0.25), (0.0, -0.4))):
                side = V((-sin(th), cos(th), 0))
                d = (nrm + side * dx + V((0, 0, dz))).normalized()
                CL.cone_between("Cactus_Spina_%03d_%d" % (idx, k), p, p + d * 0.055, 0.004, 0.0, m_spine, 5)
            idx += 1
    CL.sphere("Cactus_Corona_Lanosa", C + V((0, 0, R * 0.82)), (0.09, 0.09, 0.03), m_wool)

    # faccia "chill" piatta come una decalcomania: occhiali a specchio e sorrisetto
    def surf(th_deg, phi_deg, lift=0.004):
        th, phi = radians(th_deg), radians(phi_deg)
        rib = 1.0 + 0.065 * cos(16 * th)
        p = C + V((sin(phi) * cos(th) * R * rib, sin(phi) * sin(th) * R * rib, cos(phi) * R * 0.86))
        return p + (p - C).normalized() * lift, (p - C).normalized()
    for sx, th in ((-1, -109), (1, -71)):
        p, nrm = surf(th, 78, 0.02)
        rim_ = CL.sphere("Cactus_Montatura_%s" % ("L" if sx < 0 else "R"), (0, 0, 0), 1.0, m_decal, seg=24, rings=8)
        place_on(rim_, p, nrm, scale=(0.078, 0.058, 0.01))
        lens = CL.sphere("Cactus_Lente_%s" % ("L" if sx < 0 else "R"), (0, 0, 0), 1.0, m_mirror, seg=24, rings=8)
        place_on(lens, p + nrm * 0.006, nrm, scale=(0.068, 0.049, 0.008))
    pa, _ = surf(-90, 77, 0.022)
    CL.tube("Cactus_Ponte", [surf(-100, 75, 0.024)[0], pa, surf(-80, 75, 0.024)[0]], 0.009, m_decal, bevel_res=1)
    for sx, th in ((-1, -128), (1, -52)):
        CL.tube("Cactus_Asta_%s" % ("L" if sx < 0 else "R"), [surf(th, 76, 0.02)[0], surf(th + sx * 18, 74, 0.008)[0]],
                0.008, m_decal, bevel_res=1)
    smirk = [surf(-106, 103, 0.008)[0], surf(-95, 105, 0.008)[0], surf(-82, 103, 0.008)[0],
             surf(-71, 97, 0.008)[0]]
    CL.tube("Cactus_Sorrisetto", smirk, [0.007, 0.01, 0.01, 0.006], m_decal, bevel_res=1)
    CL.tube("Cactus_Sopracciglio", [surf(-62, 63, 0.006)[0], surf(-72, 60, 0.006)[0], surf(-82, 62, 0.006)[0]],
            0.006, m_decal, bevel_res=1)

    # braccine-stuzzicadenti conserte
    for sx in (-1, 1):
        a = surf(-90 + 62 * sx, 112, -0.01)[0]
        b = C + V((-0.13 * sx, -R * 1.2, -0.12 - 0.012 * sx))
        d = (b - a).normalized()
        CL.tube("Cactus_Braccio_%s" % ("L" if sx < 0 else "R"), [a, b], 0.009, m_wood, bevel_res=2)
        CL.cone_between("Cactus_Punta_%s" % ("L" if sx < 0 else "R"), b, b + d * 0.035, 0.009, 0.0, m_wood, 8)

    # alucce da mosca sovradimensionate attaccate al vaso (frenetiche!)
    fly = [(-15, 0.25), (-5, 0.7), (5, 0.95), (15, 1.0), (25, 0.9), (35, 0.6), (42, 0.25)]
    fly = [(a, r * 0.72) for a, r in fly]
    CL.wing_pair("Cactus_Ala_Mosca", fly, m_wing, (0.27, 0.04, 0.3), elev=28, sweep=28, roll=62,
                 rings=10, flap=(34, 48, 0.0))

    # FARETTO ALOGENO DA STADIO piantato in testa
    top = C + V((0, 0, R * 0.86))
    CL.tube("Cactus_Palo", [top - V((0, 0, 0.03)), top + V((0, 0, 0.16))], 0.022, m_chrome, bevel_res=2)
    H = top + V((0, -0.02, 0.4))
    tilt = -16
    head = box("Cactus_Faretto", H, (0.3, 0.075, 0.2), m_metal, bevel=0.15, rot=(tilt, 0, 0))
    rot = head.rotation_euler.to_matrix()
    fwd = rot @ V((0, -1, 0))
    panel = box("Cactus_Faretto_Vetro", H + fwd * 0.078, (0.27, 0.006, 0.175), m_led, rot=(tilt, 0, 0))
    CL.no_shadow(panel)
    for gx in (-1, 0, 1):
        box("Cactus_Griglia_V%d" % gx, H + fwd * 0.086 + rot @ V((gx * 0.09 + 0.045, 0, 0)),
            (0.006, 0.006, 0.175), m_metal, rot=(tilt, 0, 0))
    box("Cactus_Griglia_H", H + fwd * 0.086, (0.27, 0.006, 0.006), m_metal, rot=(tilt, 0, 0))
    for fz in range(7):
        box("Cactus_Aletta_%d" % fz, H - fwd * 0.09 + rot @ V((0, 0, -0.15 + 0.05 * fz)),
            (0.27, 0.02, 0.006), m_metal, rot=(tilt, 0, 0))
    yoke = [H + rot @ V((-0.33, 0, 0)), H + rot @ V((-0.33, 0, -0.26)), top + V((0, 0, 0.16)),
            H + rot @ V((0.33, 0, -0.26)), H + rot @ V((0.33, 0, 0))]
    CL.tube("Cactus_Staffa", yoke, 0.018, m_chrome, bevel_res=2, poly=True)
    for sx in (-1, 1):
        CL.cone_between("Cactus_Bullone_%s" % ("L" if sx < 0 else "R"), H + rot @ V((0.3 * sx, 0, 0)),
                        H + rot @ V((0.35 * sx, 0, 0)), 0.03, 0.03, m_chrome, 12)
    CL.add_light("Cactus_Faretto_Fascio", 'SPOT', H + fwd * 0.12, 900.0, (0.92, 0.96, 1.0), 0.25,
                 rot=None, spot_size=75, pulse=(780.0, 900.0, 16, 0.0))
    spot = bpy.data.objects["Cactus_Faretto_Fascio"]
    CL.aim(spot, H + fwd * 3.0 + V((0, 0, -0.6)))
    CL.add_light("Cactus_Faretto_Alone", 'POINT', H + fwd * 0.25, 40.0, (0.92, 0.96, 1.0), 0.3,
                 pulse=(34.0, 40.0, 16, 0.0))


# ============================================================================
# REGISTRO, SCENA E AVVIO
# ============================================================================

CREATURE_DESERTO = {
    #  chiave      (collezione,                   funzione,          camera: target, dist, elev, azim, lente)
    "scorpione": ("D01_Scorpione-Lanterna",      build_scorpion,    ((0, 0.15, 0.55), 5.0, 16, 35, 50)),
    "fennec":    ("D02_Fennec-Solare",           build_fennec,      ((0, -0.05, 0.66), 3.6, 8, 38, 50)),
    "scarabeo":  ("D03_Scarabeo-Fornace",        build_scarab,      ((0, -0.12, 0.28), 3.3, 20, 62, 50)),
    "vipera":    ("D04_Vipera-Sonaglio",         build_viper,       ((0, 0.05, 0.25), 3.6, 28, 22, 50)),
    "lucertola": ("D05_Lucertola-Cristallo",     build_lizard,      ((0, 0.1, 0.16), 2.9, 28, 32, 50)),
    "avvoltoio": ("D06_Avvoltoio-Miraggio",      build_vulture,     ((0, 0.1, 0.95), 7.0, 10, 18, 50)),
    "tarantola": ("D07_Tarantola-Brace",         build_tarantula,   ((0, 0.05, 0.2), 3.8, 32, 30, 50)),
    "cactus":    ("D08_Cactus-Chill-Guy",        build_cactus,      ((0, -0.05, 0.75), 3.6, 8, 22, 50)),
}

DISPOSIZIONE_DESERTO = {
    #  chiave      (x, y, rotazione_z)
    "avvoltoio": (-5.6, 4.9, 10),
    "scorpione": (-2.0, 4.6, 15),
    "fennec":    (1.6, 4.6, -5),
    "cactus":    (5.2, 4.8, -15),
    "vipera":    (-4.1, 0.5, 20),
    "lucertola": (-1.3, 0.0, 10),
    "scarabeo":  (1.4, 0.0, -30),
    "tarantola": (4.4, 0.3, -20),
}


def build(which=None, engine=None, clean=None):
    which = (which or CREATURA).lower()
    if clean if clean is not None else CL.PULISCI_SCENA:
        CL.clear_scene()
    CL.setup_world((0.004, 0.0028, 0.0075))
    CL.setup_render(engine or MOTORE)
    base = CL.new_collection("Scena_Deserto")
    CL.set_collection(base)
    setup_desert_ground()
    CL.setup_moonlight()
    CL.set_collection(None)
    if which == "tutte":
        for k in CREATURE_DESERTO:
            x, y, rz = DISPOSIZIONE_DESERTO[k]
            CL.build_one(k, (x, y, 0), rot_z=rz, registry=CREATURE_DESERTO)
        CL.setup_camera((0.0, 2.5, 0.8), 12.8, 21, 0, 32)
    else:
        if which not in CREATURE_DESERTO:
            raise ValueError("Creatura sconosciuta: %s (scegli tra %s o 'tutte')"
                             % (which, ", ".join(CREATURE_DESERTO)))
        CL.build_one(which, registry=CREATURE_DESERTO)
        tgt, dist, el, az, lens = CREATURE_DESERTO[which][2]
        CL.setup_camera(tgt, dist, el, az, lens)
    CL.setup_viewport()
    bpy.context.scene.frame_set(1)


def main():
    CL.build = build            # il main condiviso usa questa funzione
    CL.main()


if __name__ == "__main__":
    main()
