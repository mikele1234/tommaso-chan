# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE: I MOSTRI - quinta serie per Blender (modelli statici).

    01  PIPISTRELLO-SANGUISUGA   (addome a fiala di vetro piena di sangue luminoso)
    02  FRANKEN-SCARABEO         (pezzi di insetti cuciti, energia dalle cicatrici)
    03  GARGOYLE-OSSIDIANA       (pietra lavica con crepe di magma, occhi di fiamma)
    04  ZUCCA-INFESTATA          (falena con l'addome a Jack-o'-Lantern)
    05  CORVO-PESTE              (maschera da medico della peste, lenti radioattive)
    06  OCCHIO-FLUTTUANTE        (bulbo oculare levitante con il faro giallo)
    07  CALDERONE-ANIMATO        (pozione viola ribollente, zampe di rana)
    08  IL VERME DELL'OHIO "NEXTBOT" (bruco RGB con la faccia piatta che ti guarda)

Solo modelli 3D: nessuna animazione. Setup di render EEVEE Next (vedi
creature_strumenti.py). Richiede nella stessa cartella: creature_luminose.py,
creature_deserto.py, creature_neve.py, creature_oceano.py, creature_strumenti.py.

USO DENTRO BLENDER (4.2 o piu' recente)
    1. Workspace "Scripting" > Text > Open... > scegli questo file.
    2. Cambia CREATURA qui sotto (oppure lascia "tutte") e premi Run Script.

USO DA RIGA DI COMANDO
    blender --background --python creature_mostri.py -- \\
            --creatura zucca --salva zucca.blend --render zucca.png
"""

import bpy
import bmesh
import importlib.util
import math
import os
import random
import sys
from math import cos, pi, radians, sin

import numpy as np
from mathutils import Matrix, Vector
from mathutils import noise as mnoise

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# "pipistrello", "scarabeo", "gargoyle", "zucca", "corvo", "occhio",
# "calderone", "verme" oppure "tutte"
CREATURA = "tutte"

# "EEVEE" (quello del setup) oppure "CYCLES"
MOTORE = "EEVEE"


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


ST = _carica("creature_strumenti")
CL, DS, NV, OC = ST.CL, ST.DS, ST.NV, ST.OC
TAU = CL.TAU
V = Vector
el, cap, bl = ST.el, ST.cap, ST.bl
side_name = ST.side_name


# ============================================================================
# MATERIALI DEI MOSTRI
# ============================================================================

def m_membrana(nome, base=(0.035, 0.02, 0.022), vena=(0.25, 0.03, 0.035), sss=(1.0, 0.15, 0.1), rough=0.55):
    """Membrana coriacea (pipistrello, gargoyle, draghi): pelle scura con le
    venature che seguono le dita (UV del ventaglio) e un po' di luce che la
    attraversa (Subsurface rosso)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    nz = nb.noise(tc.outputs['Object'], 9.0, 5.0, 0.6)
    du = nb.math('MULTIPLY', nb.math('SUBTRACT', nz.outputs['Fac'], 0.5), 0.05)
    x = nb.math('FRACT', nb.math('MULTIPLY', nb.math('ADD', u, du), 22.0))
    x = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', x, 0.5)), 2.0)
    vene = nb.math('MULTIPLY', nb.maprange(x, 0.86, 0.98), nb.maprange(v, 0.95, 0.3))
    rughe = nb.voronoi(tc.outputs['Object'], 60.0, 'DISTANCE_TO_EDGE')
    col = nb.ramp(nz.outputs['Fac'], [(0.3, base), (0.7, tuple(c * 1.6 for c in base))])
    col = NV.rgb_mix(nb, vene, col, vena)
    pb = nb.principled(base=col, rough=rough, sss=0.35, sss_radius=sss, coat=0.25, spec=0.4)
    h = nb.math('ADD', nb.maprange(rughe.outputs['Distance'], 0.0, 0.1), nb.math('MULTIPLY', vene, 0.8))
    nb.set(pb, 'Normal', nb.bump(h, 0.35, 0.004))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_thick"] = 1
    mat["rbx_rough"] = rough
    CL.diffuse_display(mat, base)
    return mat


def m_ruggine(nome, ferro=(0.03, 0.028, 0.027), ruggine=(0.26, 0.085, 0.025), scala=2.5):
    """Ghisa scura, opaca e ruvidissima, mangiata dalla ruggine."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    vec = DS._coords(nb, distort=0.2)
    nz = nb.noise(vec, scala, 8.0, 0.65)
    pit = nb.voronoi(vec, scala * 18, 'F1')
    m = nb.maprange(nz.outputs['Fac'], 0.46, 0.6)
    col = NV.rgb_mix(nb, m, ferro, ruggine)
    fine = nb.noise(vec, scala * 30, 6.0, 0.7)
    col = NV.rgb_mix(nb, nb.math('MULTIPLY', fine.outputs['Fac'], 0.35), col, (0.12, 0.05, 0.02))
    metal = nb.maprange(m, 0.0, 1.0, 0.75, 0.05)
    pb = nb.principled(base=col, rough=nb.maprange(m, 0.0, 1.0, 0.82, 0.97), metal=metal, spec=0.4)
    h = nb.math('ADD', nb.math('MULTIPLY', nb.maprange(pit.outputs['Distance'], 0.0, 0.25), 0.5),
                nb.math('MULTIPLY', m, 0.6))
    nb.set(pb, 'Normal', nb.bump(nb.math('ADD', h, nb.math('MULTIPLY', fine.outputs['Fac'], 0.4)), 0.5, 0.01))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.9
    mat["rbx_metal"] = 0.4
    CL.diffuse_display(mat, ferro)
    return mat


def m_cuoio(nome, base=(0.11, 0.06, 0.035), scuro=(0.035, 0.02, 0.012)):
    """Cuoio logoro: macchie scure, graffi chiari, grana e pieghe."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    vec = DS._coords(nb, distort=0.3)
    nz = nb.noise(vec, 4.0, 6.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, scuro), (0.72, base)])
    sc = nb.noise(DS._coords(nb, scale=1.0), 40.0, 2.0, 0.5)
    graffi = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', sc.outputs['Fac'], 0.5)), 0.012, 0.0)
    col = NV.rgb_mix(nb, nb.math('MULTIPLY', graffi, 0.6), col, (0.3, 0.2, 0.13))
    grana = nb.voronoi(vec, 90.0, 'F1')
    pb = nb.principled(base=col, rough=nb.maprange(nz.outputs['Fac'], 0.3, 0.8, 0.55, 0.8), sheen=0.3, spec=0.45,
                       coat=0.15)
    h = nb.math('ADD', nb.math('MULTIPLY', grana.outputs['Distance'], 0.5), nb.math('MULTIPLY', graffi, -0.6))
    nb.set(pb, 'Normal', nb.bump(h, 0.4, 0.004))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.7
    CL.diffuse_display(mat, base)
    return mat


def m_zucca(nome, buccia=(0.85, 0.24, 0.02), solco=(0.35, 0.08, 0.01)):
    """Buccia di zucca ruvida: arancio con i solchi scuri, macchie e nervature."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    ang = nb.math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    rib = nb.math('ABSOLUTE', nb.math('COSINE', nb.math('MULTIPLY', ang, 5.0)))
    solchi = nb.maprange(rib, 0.25, 0.0)
    nz = nb.noise(tc.outputs['Object'], 6.0, 8.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, tuple(c * 0.7 for c in buccia)), (0.7, buccia)])
    col = NV.rgb_mix(nb, solchi, col, solco)
    macchie = nb.maprange(nb.noise(tc.outputs['Object'], 14.0, 3.0, 0.5).outputs['Fac'], 0.62, 0.72)
    col = NV.rgb_mix(nb, nb.math('MULTIPLY', macchie, 0.7), col, (0.2, 0.12, 0.02))
    pb = nb.principled(base=col, rough=0.72, sss=0.05, sss_radius=(1.0, 0.4, 0.1), spec=0.35)
    fibre = nb.noise(tc.outputs['Object'], 60.0, 4.0, 0.6)
    nb.set(pb, 'Normal', nb.bump(nb.math('ADD', nb.math('MULTIPLY', fibre.outputs['Fac'], 0.5), solchi), 0.35,
                                 0.01))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.72
    CL.diffuse_display(mat, buccia)
    return mat


def m_foglia_secca(nome, c1=(0.42, 0.12, 0.015), c2=(0.6, 0.25, 0.03), c3=(0.13, 0.05, 0.015), buchi=True):
    """Foglia autunnale morta (ala): arancio-bruno maculato, bordi bruciati,
    nervature palmate dalla base, qualche buco. UV del ventaglio dell'ala."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    obj = tc.outputs['Object']
    nz = nb.noise(obj, 7.0, 6.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.25, c1), (0.55, c2), (0.8, (0.55, 0.35, 0.05))])
    bruc = nb.math('MAXIMUM', nb.maprange(v, 0.78, 1.0),
                   nb.maprange(nb.noise(obj, 3.0, 4.0, 0.6).outputs['Fac'], 0.62, 0.72))
    col = NV.rgb_mix(nb, bruc, col, c3)
    x = nb.math('FRACT', nb.math('MULTIPLY', nb.math('ADD', u, nb.math('MULTIPLY', nz.outputs['Fac'], 0.03)), 7.0))
    x = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', x, 0.5)), 2.0)
    vene = nb.math('MULTIPLY', nb.maprange(x, 0.9, 0.99), nb.maprange(v, 1.0, 0.2))
    fine = nb.voronoi(obj, 45.0, 'DISTANCE_TO_EDGE')
    vene2 = nb.math('MULTIPLY', nb.maprange(fine.outputs['Distance'], 0.03, 0.005), 0.5)
    vv = nb.math('MAXIMUM', vene, vene2)
    col = NV.rgb_mix(nb, vv, col, (0.75, 0.45, 0.12))
    pb = nb.principled(base=col, rough=0.7, sss=0.25, sss_radius=(1.0, 0.5, 0.1), spec=0.3)
    nb.set(pb, 'Normal', nb.bump(nb.math('ADD', vv, nb.math('MULTIPLY', nz.outputs['Fac'], 0.5)), 0.4, 0.004))
    sh = pb.outputs[0]
    alpha = nb.value(1.0)
    if buchi:
        hole = nb.maprange(nb.noise(obj, 5.5, 3.0, 0.5).outputs['Fac'], 0.7, 0.68)
        alpha = nb.math('MULTIPLY', hole, nb.maprange(v, 0.05, 0.25))
        alpha = nb.math('MAXIMUM', alpha, nb.maprange(v, 0.25, 0.0))
        sh = nb.mix_shader(alpha, nb.transparent(), sh)
    nb.output(sh)
    CL.set_transparent(mat, blended=False)
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    nb.bake_output("RBX_EMIT", nb.emission((0, 0, 0), 1.0))
    ca = nb.node('ShaderNodeCombineXYZ')
    for i in range(3):
        nb.link(alpha, ca.inputs[i])
    nb.bake_output("RBX_ALPHA", nb.emission(ca.outputs[0], 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_alpha"] = 1
    mat["rbx_wing"] = 1
    mat["rbx_emit_strength"] = 0.0
    CL.diffuse_display(mat, c2)
    return mat


def m_pozione(nome, base=(0.4, 0.04, 0.7), luce_c=(0.55, 0.08, 1.0), forza=14.0):
    """Pozione: Subsurface estremo e luce viola che ribolle da dentro."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    nz = nb.noise(tc.outputs['Object'], 5.0, 6.0, 0.6)
    nb.set(nz, 'Distortion', 2.0)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, luce_c), (0.55, (1.0, 0.15, 0.75)), (0.8, (0.8, 0.5, 1.0))])
    pb = nb.principled(base=base, rough=0.12, sss=1.0, sss_radius=(0.8, 0.2, 1.0), coat=0.7, spec=0.6)
    nb.set(pb, 'Subsurface Scale', 0.4)
    s = nb.math('MULTIPLY', nb.maprange(nz.outputs['Fac'], 0.3, 0.8, 0.5, 1.4), ST.lum(forza))
    nb.output(nb.add_shader(pb.outputs[0], nb.emission(col, s)))
    CL.diffuse_display(mat, luce_c)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(luce_c)
    return mat


def m_bolla(nome, c, forza=8.0, alpha=0.45):
    """Bolla luminosa trasparente (Alpha Blend) con il bordo piu' acceso."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    f = nb.maprange(nb.fresnel(0.25), 0.0, 1.0, 0.35, 1.6)
    em = nb.emission(c, nb.math('MULTIPLY', f, ST.lum(forza)))
    nb.output(nb.mix_shader(alpha, nb.transparent(), em))
    CL.set_transparent(mat, blended=True)
    CL.diffuse_display(mat, c)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(c)
    mat["rbx_transp"] = round(1.0 - alpha, 3)
    return mat


def m_sclera(nome, C, gaze, R):
    """Sclera bagnata (alta specularita', roughness bassa) piena di capillari
    rossi, piu' fitti dietro e attorno all'iride."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    rel = nb.node('ShaderNodeVectorMath', operation='SUBTRACT')
    nb.link(tc.outputs['Object'], rel.inputs[0])
    nb.set(rel, 1, tuple(C))
    dot = nb.node('ShaderNodeVectorMath', operation='DOT_PRODUCT')
    nb.link(rel.outputs[0], dot.inputs[0])
    nb.set(dot, 1, tuple(gaze))
    along = nb.math('DIVIDE', dot.outputs['Value'], R)          # -1 dietro, +1 davanti
    vec = DS._coords(nb, distort=0.6, scale=1.0)
    vo = nb.voronoi(vec, 9.0, 'DISTANCE_TO_EDGE')
    vo2 = nb.voronoi(vec, 26.0, 'DISTANCE_TO_EDGE')
    dens = nb.math('MAXIMUM', nb.maprange(along, 0.2, -0.9), nb.maprange(along, 0.55, 0.8))
    capill = nb.math('MAXIMUM', nb.maprange(vo.outputs['Distance'], 0.03, 0.004),
                     nb.math('MULTIPLY', nb.maprange(vo2.outputs['Distance'], 0.025, 0.003), 0.7))
    capill = nb.math('MULTIPLY', capill, nb.maprange(dens, 0.0, 1.0, 0.25, 1.0))
    arross = nb.math('MULTIPLY', nb.maprange(along, 0.3, -1.0), 0.6)
    col = NV.rgb_mix(nb, arross, (0.86, 0.8, 0.62), (0.7, 0.28, 0.25))
    col = NV.rgb_mix(nb, capill, col, (0.55, 0.02, 0.03))
    pb = nb.principled(base=col, rough=0.07, spec=0.9, coat=1.0, coat_rough=0.02, sss=0.35,
                       sss_radius=(1.0, 0.3, 0.25))
    nb.set(pb, 'Normal', nb.bump(capill, 0.3, 0.003))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = 0.1
    CL.diffuse_display(mat, (0.86, 0.8, 0.62))
    return mat


def m_iride(nome, c=(0.85, 1.0, 0.08), forza=150.0):
    """Iride-lampadina: fibre radiali giallo-malattia, nucleo quasi bianco."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    x, y = sep.outputs['X'], sep.outputs['Y']
    d = nb.math('SQRT', nb.math('ADD', nb.math('MULTIPLY', x, x), nb.math('MULTIPLY', y, y)))
    ang = nb.math('ARCTAN2', y, x)
    fib = nb.noise(None, 1.0, 3.0, 0.5)
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('MULTIPLY', ang, 12.0), cmb.inputs[0])
    nb.link(nb.math('MULTIPLY', d, 6.0), cmb.inputs[1])
    nb.link(cmb.outputs[0], fib.inputs['Vector'])
    nb.set(fib, 'Scale', 1.6)
    f = nb.maprange(fib.outputs['Fac'], 0.3, 0.7, 0.55, 1.2)
    col = nb.ramp(d, [(0.0, (1.0, 1.0, 0.75)), (0.06, (1.0, 1.0, 0.35)), (0.16, c), (0.235, (0.45, 0.5, 0.02)),
                      (0.25, (0.15, 0.12, 0.0))])
    s = nb.math('MULTIPLY', f, nb.maprange(d, 0.0, 0.25, ST.lum(forza), ST.lum(forza) * 0.35))
    nb.output(nb.emission(col, s))
    CL.diffuse_display(mat, c)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(c)
    return mat


# ============================================================================
# STRUMENTI DEI MOSTRI
# ============================================================================

guscio = ST.guscio


def cucitura(prefisso, pts, normale_fn, m_filo, m_labbra=None, passo=0.045, largo=0.03, incrocio=True):
    """Cicatrice cucita lungo una linea sulla corazza: due labbra in rilievo e
    i punti di sutura (a X) che attraversano la fessura."""
    pts = [V(p) for p in pts]
    n = len(pts)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    obs = []
    if m_labbra is not None:
        for sd in (-1, 1):
            lab = []
            for i, p in enumerate(pts):
                t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
                nr = normale_fn(p)
                side = t.cross(nr).normalized()
                lab.append(p + side * sd * largo * 0.55 + nr * 0.004)
            obs.append(CL.tube("%s_Labbro_%s" % (prefisso, "AB"[sd > 0]), lab, 0.007, m_labbra, bevel_res=1))
    k = 0
    d = passo * 0.5
    while d < acc[-1] - passo * 0.3:
        i = max(1, min(n - 1, next(j for j in range(1, n) if acc[j] >= d)))
        f = (d - acc[i - 1]) / max(1e-6, acc[i] - acc[i - 1])
        p = pts[i - 1].lerp(pts[i], f)
        t = (pts[i] - pts[i - 1]).normalized()
        nr = normale_fn(p)
        side = t.cross(nr).normalized()
        for dd in ((-0.4, 0.4), (0.4, -0.4)) if incrocio else ((0.0, 0.0),):
            a = p + side * largo + t * largo * dd[0] + nr * 0.003
            b = p - side * largo + t * largo * dd[1] + nr * 0.003
            obs.append(CL.tube("%s_Punto_%02d" % (prefisso, k), [a, (a + b) / 2 + nr * 0.012, b], 0.0045, m_filo,
                               bevel_res=1, res=3))
            k += 1
        d += passo
    return obs


def fulmine(nome, a, direzione, lung, mat, passi=6, seed=0, r=0.004):
    """Scarica elettrica a zig-zag."""
    rnd = random.Random(seed)
    d = V(direzione).normalized()
    u = d.orthogonal().normalized()
    w = d.cross(u)
    pts = [V(a)]
    for i in range(1, passi + 1):
        t = i / passi
        off = (u * rnd.uniform(-1, 1) + w * rnd.uniform(-1, 1)) * lung * 0.18 * (1 - 0.5 * t)
        pts.append(V(a) + d * lung * t + off)
    rad = [r * (1.0 - 0.8 * i / passi) for i in range(passi + 1)]
    ob = CL.tube(nome, pts, rad, mat, bevel_res=1, poly=True)
    CL.no_shadow(ob)
    return ob


def prisma(nome, contorno, y0, y1, mat_index=0, mats=None):
    """Prisma estruso lungo Y da un contorno nel piano XZ (taglierini per le
    booleane)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in contorno]
    b = [bm.verts.new((x, y1, z)) for x, z in contorno]
    n = len(contorno)
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = mat_index
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    CL.link(ob)
    for m in mats or []:
        me.materials.append(m)
    return ob


def unisci(nome, obs):
    """Unisce piu' mesh in un solo oggetto (stesso materiale)."""
    bpy.context.view_layer.update()
    bm = bmesh.new()
    mat = obs[0].data.materials[0] if obs[0].data.materials else None
    for o in obs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for o in obs:
        bpy.data.objects.remove(o)
    return CL.mesh_object(nome, bm, mat, smooth=False)


def piume_strappate(nome, lung, larg, mat, seed=0):
    """Piuma nera strappata: la sagoma di una piuma con morsi e sfilacciature."""
    me = CL.feather_mesh(nome, lung, larg, mat, rows=12, cols=6, curl=0.12, shape='pointed')
    rnd = random.Random(seed)
    tagli = [rnd.uniform(0.35, 0.95) for _ in range(3)]
    for vtx in me.vertices:
        v = vtx.co.y / lung
        for t in tagli:
            if abs(v - t) < 0.06:
                vtx.co.x *= rnd.uniform(0.15, 0.6)
        if v > 0.85:
            vtx.co.x *= rnd.uniform(0.5, 1.0)
            vtx.co.y -= rnd.uniform(0.0, 0.06) * lung
    return me


# ============================================================================
# 01  PIPISTRELLO-SANGUISUGA
# ============================================================================

def build_pipistrello():
    DS.texspace("Pipistrello")
    Z = 1.05
    cremisi = (0.75, 0.0, 0.035)
    m_pelo = CL.m_body("Pipistrello_Pelo_Nero", (0.008, 0.007, 0.008), rough=0.8, sheen=0.3,
                       sheen_tint=(0.25, 0.15, 0.2), bump=(140.0, 0.3, 'noise'), rim=(0.9, 0.05, 0.1), rim_str=0.25)
    m_pelle = ST.m_chitina("Pipistrello_Pelle_Muso", (0.05, 0.02, 0.025), rough=0.5, coat=0.3, sss=0.3,
                           sss_radius=(1.0, 0.2, 0.15))
    m_mem = m_membrana("Pipistrello_Membrana_Cuoio")
    m_ossa = CL.m_body("Pipistrello_Ossa_Ali", (0.02, 0.013, 0.014), rough=0.45, coat=0.3)
    m_occhi = ST.m_luce("Pipistrello_Occhi_Cremisi", (1.0, 0.04, 0.03), 40.0)
    m_zanne = CL.m_body("Pipistrello_Zanne", (0.9, 0.87, 0.78), rough=0.25, coat=0.6, sss=0.2)
    m_orecchio = CL.m_body("Pipistrello_Orecchio_Interno", (0.2, 0.045, 0.055), rough=0.5, sss=0.6,
                           sss_radius=(1.0, 0.2, 0.2))
    m_fiala = ST.m_vetro_sottile("Pipistrello_Fiala_Vetro", (0.95, 0.9, 0.92), bordo=(1.0, 0.25, 0.25),
                                 forza_bordo=0.6)
    m_sangue = ST.m_liquido("Pipistrello_Sangue_Luminoso", (0.8, 0.015, 0.02), 45.0, cremisi, 28.0)
    m_ghiera = CL.m_body("Pipistrello_Ghiera_Metallo", (0.62, 0.6, 0.62), rough=0.28, metal=1.0)
    m_alone = CL.m_halo("Pipistrello_Alone_Cremisi", cremisi, 0.35)

    E = [el((0, 0.0, Z), 0.11, (0.95, 1.3, 0.92)),
         el((0, -0.16, Z + 0.05), 0.085, (1.0, 0.95, 0.95)),
         el((0, -0.235, Z + 0.035), 0.05, (1.0, 1.0, 0.85)),
         el((0, 0.13, Z - 0.03), 0.075, (0.85, 1.1, 0.8)),
         cap((0, -0.08, Z + 0.03), (0, -0.14, Z + 0.05), 0.07)]
    for sx in (-1, 1):
        E.append(cap((0.05 * sx, 0.14, Z - 0.05), (0.08 * sx, 0.24, Z - 0.17), 0.018))
    body = CL.metaball_mesh("Pipistrello_Corpo", E, m_pelo, res=0.011)
    del body
    # muso: foglia nasale, narici, zanne
    CL.sphere("Pipistrello_Foglia_Nasale", (0, -0.285, Z + 0.05), (0.024, 0.012, 0.03), m_pelle, seg=16, rings=8)
    for sx in (-1, 1):
        CL.sphere("Pipistrello_Narice_" + side_name(sx), (0.009 * sx, -0.294, Z + 0.042), 0.005, m_ossa, seg=8,
                  rings=4)
        CL.cone_between("Pipistrello_Zanna_" + side_name(sx), (0.017 * sx, -0.268, Z + 0.012),
                        (0.015 * sx, -0.276, Z - 0.035), 0.0065, 0.0, m_zanne, 8)
        e = CL.sphere("Pipistrello_Occhio_" + side_name(sx), (0.043 * sx, -0.228, Z + 0.083), 0.014, m_occhi,
                      seg=12, rings=6)
        ST.proxy(e, (0.05 * sx, -0.25, Z + 0.085), (1.0, 0.04, 0.03), 0.4)
        # orecchie enormi e appuntite
        base = V((0.045 * sx, -0.14, Z + 0.1))
        tip = V((0.13 * sx, -0.1, Z + 0.3))
        ST.cono_piatto("Pipistrello_Orecchio_" + side_name(sx), base, tip, 0.05, m_pelle, 0.4,
                       avanti=(0.35 * sx, -1, 0.2))
        ST.cono_piatto("Pipistrello_Orecchio_Dentro_" + side_name(sx), base + V((0.004 * sx, -0.012, 0.01)),
                       tip + V((-0.004 * sx, -0.012, -0.03)), 0.036, m_orecchio, 0.25, avanti=(0.35 * sx, -1, 0.2))
        # zampette posteriori con gli artigli
        foot = V((0.08 * sx, 0.24, Z - 0.17))
        for k in range(4):
            CL.cone_between("Pipistrello_Unghia_%s%d" % (side_name(sx), k), foot,
                            foot + V(((k - 1.5) * 0.012 * sx, 0.02, -0.035)), 0.005, 0.0, m_ossa, 6)
    # ali membranose, dita aperte
    S, Eb, W = V((0.07, -0.02, Z + 0.05)), V((0.28, 0.06, Z + 0.2)), V((0.47, -0.08, Z + 0.26))
    tips = [V((0.86, -0.2, Z + 0.28)), V((0.98, 0.12, Z + 0.13)), V((0.84, 0.38, Z + 0.0)),
            V((0.55, 0.47, Z - 0.07))]
    mem, ossa = ST.ala_membrana("Pipistrello_Ala", S, Eb, W, tips, V((0.07, 0.2, Z - 0.1)), m_mem, m_ossa,
                                sacca=0.2, gonfia=0.05, righe=8, colonne=6, r_osso=0.009, artiglio=m_zanne)
    ST.specchia_x([mem] + ossa)

    # ADDOME: una fiala medica di vetro piena di sangue luminoso
    dv = V((0, 0.62, -0.78)).normalized()
    A = V((0, 0.2, Z - 0.05))
    base = A + dv * 0.3
    fr = CL.frame_matrix(base, V((1, 0, 0)), -dv)
    prof = [(0.002, 0.0), (0.03, 0.004), (0.052, 0.02), (0.062, 0.05), (0.062, 0.2), (0.054, 0.228),
            (0.032, 0.246), (0.024, 0.256), (0.024, 0.285)]
    fiala = DS.lathe("Pipistrello_Fiala", prof, m_fiala, seg=40, cap_bottom=False, cap_top=True)
    fiala.matrix_world = fr
    CL.no_shadow(fiala)
    liq = DS.lathe("Pipistrello_Sangue", [(0.002, 0.007), (0.028, 0.011), (0.048, 0.026), (0.057, 0.05),
                                          (0.057, 0.2), (0.05, 0.218)], m_sangue, seg=36, cap_bottom=False,
                   cap_top=True)
    liq.matrix_world = fr
    gh = DS.lathe("Pipistrello_Ghiera", [(0.027, 0.25), (0.031, 0.256), (0.031, 0.305), (0.02, 0.31)], m_ghiera,
                  seg=24, cap_bottom=False, cap_top=True)
    gh.matrix_world = fr
    h = CL.sphere("Pipistrello_Alone", fr @ V((0, 0, 0.12)), (0.16, 0.16, 0.22), m_alone)
    h.matrix_world = fr @ Matrix.Translation((0, 0, 0.12)) @ Matrix.Diagonal((0.15, 0.15, 0.22, 1.0))
    CL.no_shadow(h)
    ST.proxy(liq, fr @ V((0, 0, 0.11)), cremisi, 14.0)
    ST.proxy(liq, fr @ V((0, 0.0, -0.08)), cremisi, 4.0, nome="Pipistrello_Luce_Riflesso")


# ============================================================================
# 02  FRANKEN-SCARABEO
# ============================================================================

def build_franken_scarabeo():
    DS.texspace("FrankenScarabeo")
    Zc = 0.5
    verde = (0.12, 1.0, 0.72)
    m_energia = ST.m_luce("FrankenScarabeo_Energia_Intrappolata", verde, 12.0, bordo=(0.7, 1.0, 1.0),
                          forza_bordo=20.0)
    m_fessura = ST.m_luce("FrankenScarabeo_Energia_Fessure", verde, 45.0, bordo=(0.8, 1.0, 1.0), forza_bordo=60.0)
    m_scarica = ST.m_luce("FrankenScarabeo_Scariche", (0.55, 1.0, 1.0), 90.0)
    m_gioiello = ST.m_chitina("FrankenScarabeo_Elitra_Smeraldo", (0.02, 0.22, 0.07), rough=0.22, metal=0.7,
                              coat=0.7, film=380.0)
    m_viola = ST.m_chitina("FrankenScarabeo_Elitra_Viola", (0.13, 0.02, 0.18), rough=0.25, metal=0.5, coat=0.6,
                           film=520.0)
    m_bruna = CL.m_body("FrankenScarabeo_Elitra_Coccinella", (0.42, 0.13, 0.025), rough=0.35, coat=0.6,
                        mottle=((0.02, 0.015, 0.01), 7.0))
    m_nera = ST.m_chitina("FrankenScarabeo_Pronoto_Cervo", (0.012, 0.01, 0.012), rough=0.15, coat=0.8)
    m_testa = ST.m_chitina("FrankenScarabeo_Testa", (0.17, 0.04, 0.02), rough=0.3, coat=0.6)
    m_ventre = CL.m_body("FrankenScarabeo_Ventre_Larva", (0.55, 0.45, 0.3), rough=0.45, sss=0.3,
                         sss_radius=(1.0, 0.8, 0.5), bump=(30.0, 0.3, 'noise'))
    m_cicatrice = CL.m_body("FrankenScarabeo_Cicatrici", (0.16, 0.08, 0.09), rough=0.75, sss=0.2,
                            bump=(70.0, 0.9, 'warts'))
    m_filo = CL.m_body("FrankenScarabeo_Filo_Sutura", (0.02, 0.02, 0.018), rough=0.8)
    m_metallo = CL.m_body("FrankenScarabeo_Bulloni", (0.42, 0.42, 0.44), rough=0.35, metal=1.0,
                          bump=(45.0, 0.25, 'noise'))
    m_gamba = [ST.m_chitina("FrankenScarabeo_Zampa_Talpa", (0.28, 0.14, 0.05), rough=0.4),
               ST.m_chitina("FrankenScarabeo_Zampa_Mantide", (0.12, 0.35, 0.06), rough=0.4, sss=0.2),
               ST.m_chitina("FrankenScarabeo_Zampa_Nera", (0.015, 0.013, 0.015), rough=0.2),
               ST.m_chitina("FrankenScarabeo_Zampa_Cavalletta", (0.2, 0.42, 0.1), rough=0.4),
               ST.m_chitina("FrankenScarabeo_Zampa_Saltatrice", (0.3, 0.3, 0.08), rough=0.35),
               CL.m_body("FrankenScarabeo_Zampa_Pelosa", (0.12, 0.07, 0.04), rough=0.8, sheen=0.8,
                         bump=(90.0, 0.4, 'noise'))]
    m_occhio_mosca = CL.m_body("FrankenScarabeo_Occhio_Mosca", (0.5, 0.03, 0.02), rough=0.15, coat=1.0,
                               bump=(90.0, 0.5, 'scales'))
    m_occhio_nero = CL.m_body("FrankenScarabeo_Occhio_Nero", (0.01, 0.01, 0.01), rough=0.05, coat=1.0)

    C, R = V((0, 0.14, Zc)), (0.3, 0.46, 0.23)
    g = 0.018
    # nucleo di energia (visibile solo dalle fessure)
    core = CL.sphere("FrankenScarabeo_Nucleo", C, (R[0] - 0.03, R[1] - 0.03, R[2] - 0.03), m_energia, seg=32,
                     rings=16)
    CL.sphere("FrankenScarabeo_Nucleo_Pronoto", (0, -0.36, Zc + 0.02), (0.24, 0.14, 0.155), m_energia, seg=24,
              rings=12)
    CL.sphere("FrankenScarabeo_Nucleo_Collo", (0, -0.5, Zc - 0.02), (0.1, 0.07, 0.08), m_energia, seg=16, rings=8)
    # pezzi di corazza da donatori diversi, separati da fessure
    diag = V((0.35, -1.0, 0.0)).normalized()
    guscio("FrankenScarabeo_Elitra_Destra_Davanti", C, R, m_gioiello,
           [((g, 0, 0), (1, 0, 0)), ((0, 0, Zc - 0.07), (0, 0, 1)), ((0, -0.22, 0), (0, 1, 0)),
            ((0, 0.06 - g, Zc), diag)])
    guscio("FrankenScarabeo_Elitra_Destra_Dietro", C, R, m_viola,
           [((g, 0, 0), (1, 0, 0)), ((0, 0, Zc - 0.07), (0, 0, 1)), ((0, 0.06 + g, Zc), -diag)])
    guscio("FrankenScarabeo_Elitra_Sinistra", C, R, m_bruna,
           [((-g, 0, 0), (-1, 0, 0)), ((0, 0, Zc - 0.07), (0, 0, 1)), ((0, -0.22, 0), (0, 1, 0))])
    guscio("FrankenScarabeo_Ventre", (0, 0.14, Zc - 0.02), (0.29, 0.45, 0.2), m_ventre,
           [((0, 0, Zc - 0.078), (0, 0, -1))])
    PC, PR = V((0, -0.36, Zc + 0.02)), (0.27, 0.16, 0.18)
    guscio("FrankenScarabeo_Pronoto", PC, PR, m_nera,
           [((0, -0.25, 0), (0, -1, 0)), ((0, -0.49, 0), (0, 1, 0)), ((0, 0, Zc - 0.16), (0, 0, 1))])
    HC, HR = V((0, -0.585, Zc - 0.02)), (0.14, 0.11, 0.1)
    guscio("FrankenScarabeo_Testa", HC, HR, m_testa, [((0, -0.52, 0), (0, -1, 0))], spessore=0.0)

    def nrm_dorso(p):
        q = p - C
        return V((q.x / R[0] ** 2, q.y / R[1] ** 2, q.z / R[2] ** 2)).normalized()

    def nrm_pron(p):
        q = p - PC
        return V((q.x / PR[0] ** 2, q.y / PR[1] ** 2, q.z / PR[2] ** 2)).normalized()

    # cuciture: linea dorsale, diagonale sull'elitra destra, attacco del pronoto
    dorsale = [V((0, y, ST.ellissoide_z(C, R, 0, y) + 0.003)) for y in [(-0.21 + 0.79 * i / 16) for i in range(17)]]
    xs = [0.02 + 0.26 * i / 10 for i in range(11)]
    diag_pts = [V((x, 0.06 + 0.35 * x, ST.ellissoide_z(C, R, x, 0.06 + 0.35 * x) + 0.003)) for x in xs]
    trasv = [V((x, -0.235, ST.ellissoide_z(C, R, x, -0.235) + 0.004)) for x in
             [(-0.25 + 0.5 * i / 12) for i in range(13)]]
    for nome, linea in (("Dorso", dorsale), ("Diagonale", diag_pts), ("Pronoto", trasv)):
        CL.tube("FrankenScarabeo_Fessura_" + nome, [p - V((0, 0, 0.01)) for p in linea], 0.012, m_fessura,
                bevel_res=1)
    cucitura("FrankenScarabeo_Cucitura_Dorso", dorsale, nrm_dorso, m_filo, m_cicatrice, passo=0.06)
    cucitura("FrankenScarabeo_Cucitura_Diagonale", diag_pts, nrm_dorso, m_filo, m_cicatrice, passo=0.055)
    cucitura("FrankenScarabeo_Cucitura_Pronoto", trasv, nrm_dorso, m_filo, m_cicatrice, passo=0.07, incrocio=False)
    collo = [V((0.14 * cos(a), -0.5, Zc - 0.02 + 0.1 * sin(a))) for a in [pi * i / 10 for i in range(11)]]
    cucitura("FrankenScarabeo_Cucitura_Collo", collo, nrm_pron, m_filo, None, passo=0.05, incrocio=False)
    # scariche elettriche che escono con violenza dalle fessure
    for i, (p, d) in enumerate(((dorsale[5], (0.3, -0.2, 1)), (dorsale[12], (-0.4, 0.3, 1)),
                                (diag_pts[6], (0.8, 0.2, 0.9)), (trasv[3], (-0.5, -0.4, 0.8)),
                                (trasv[10], (0.6, -0.3, 0.9)))):
        fulmine("FrankenScarabeo_Scarica_%d" % i, p, d, 0.16 + 0.04 * (i % 3), m_scarica, seed=i + 3)
    for i, p in enumerate((dorsale[4], dorsale[13], diag_pts[5], trasv[6])):
        ST.proxy(core, p + V((0, 0, 0.05)), verde, 10.0, nome="FrankenScarabeo_Luce_Fessura_%d" % i)

    # bulloni alla base della testa
    for sx in (-1, 1):
        s = side_name(sx)
        a = V((0.12 * sx, -0.47, Zc - 0.01))
        b = V((0.25 * sx, -0.47, Zc - 0.01))
        CL.cone_between("FrankenScarabeo_Bullone_" + s, a, b, 0.024, 0.024, m_metallo, 12)
        CL.cone_between("FrankenScarabeo_Dado_" + s, a + (b - a) * 0.55, a + (b - a) * 0.8, 0.045, 0.045, m_metallo,
                        6)
        CL.sphere("FrankenScarabeo_Testa_Bullone_" + s, b, (0.028, 0.034, 0.034), m_metallo, seg=12, rings=6)
        for k in range(3):
            fulmine("FrankenScarabeo_Scintilla_%s%d" % (s, k), b + V((0.02 * sx, 0, 0)),
                    (sx, (k - 1) * 0.8, 0.5 + 0.3 * k), 0.07, m_scarica, passi=4, seed=20 + k + (sx > 0) * 5,
                    r=0.003)
        ST.proxy(core, b + V((0.05 * sx, 0, 0.02)), (0.55, 1.0, 1.0), 3.0, nome="FrankenScarabeo_Luce_Bullone_" + s)

    # testa: mandibole spaiate, occhi diversi, antenne di due insetti diversi
    CL.tube("FrankenScarabeo_Mandibola_Cervo", [V((0.05, -0.68, Zc - 0.05)), V((0.14, -0.8, Zc - 0.01)),
                                                V((0.1, -0.94, Zc + 0.03)), V((0.02, -0.98, Zc + 0.04))],
            [0.024, 0.02, 0.013, 0.004], m_testa, bevel_res=3)
    CL.cone_between("FrankenScarabeo_Dente_Mandibola", V((0.12, -0.86, Zc)), V((0.05, -0.86, Zc + 0.05)), 0.012, 0.0,
                    m_testa, 8)
    CL.tube("FrankenScarabeo_Mandibola_Piccola", [V((-0.045, -0.68, Zc - 0.06)), V((-0.09, -0.74, Zc - 0.05)),
                                                  V((-0.05, -0.79, Zc - 0.05))], [0.014, 0.01, 0.003], m_nera,
            bevel_res=2)
    CL.sphere("FrankenScarabeo_Occhio_Mosca", (0.09, -0.63, Zc + 0.03), (0.05, 0.045, 0.05), m_occhio_mosca)
    CL.sphere("FrankenScarabeo_Occhio_Piccolo", (-0.085, -0.645, Zc + 0.02), 0.022, m_occhio_nero, seg=16, rings=8)
    a = V((0.05, -0.66, Zc + 0.05))
    CL.tube("FrankenScarabeo_Antenna_Lamellata", [a, a + V((0.06, -0.08, 0.08)), a + V((0.14, -0.14, 0.16))],
            0.007, m_testa, bevel_res=2)
    for k in range(3):
        CL.sphere("FrankenScarabeo_Lamella_%d" % k, a + V((0.15 + 0.012 * k, -0.15 - 0.014 * k, 0.17)),
                  (0.03, 0.009, 0.022), m_testa, rot=(0, 20, -40), seg=12, rings=6)
    a = V((-0.05, -0.66, Zc + 0.05))
    ant = DS.spline([a, a + V((-0.1, -0.12, 0.12)), a + V((-0.25, -0.1, 0.25)), a + V((-0.42, 0.05, 0.28))], 18)
    CL.tube("FrankenScarabeo_Antenna_Lunga", ant, [0.006 - 0.0002 * i for i in range(18)], m_gamba[2],
            bevel_res=1, poly=True)
    for i in range(2, 18, 2):
        CL.sphere("FrankenScarabeo_Articolo_%02d" % i, ant[i], 0.009, m_gamba[2], seg=10, rings=5)

    # sei zampe di sei insetti diversi, attaccate con anelli di luce cuciti
    specs = [((0.15, -0.3), (0.3, -0.48, 0.3), (0.34, -0.62, 0.0), [0.032, 0.036, 0.028, 0.02], 0),
             ((-0.15, -0.3), (-0.32, -0.45, 0.32), (-0.4, -0.66, 0.0), [0.014, 0.012, 0.01, 0.007], 1),
             ((0.17, -0.02), (0.4, -0.02, 0.36), (0.5, 0.02, 0.0), [0.022, 0.02, 0.016, 0.01], 2),
             ((-0.17, -0.02), (-0.42, 0.0, 0.34), (-0.52, 0.05, 0.0), [0.015, 0.013, 0.011, 0.007], 3),
             ((0.16, 0.24), (0.36, 0.44, 0.62), (0.44, 0.58, 0.0), [0.04, 0.045, 0.022, 0.012], 4),
             ((-0.16, 0.24), (-0.4, 0.38, 0.34), (-0.5, 0.56, 0.0), [0.02, 0.022, 0.018, 0.01], 5)]
    for i, ((x, y), knee, foot, rads, mi) in enumerate(specs):
        a = V((x, y, Zc - 0.1))
        k = V(knee)
        f = V(foot)
        pts = [a, k, f.lerp(k, 0.25), f]
        DS.leg("FrankenScarabeo_Zampa_%d" % i, pts, rads, m_gamba[mi], joint_mat=m_cicatrice, joint_r=rads[1] * 1.3)
        ring = NV.ring_points(a.lerp(k, 0.12), (k - a).normalized(), rads[0] * 1.35, 12)
        CL.tube("FrankenScarabeo_Anello_Luce_%d" % i, ring + [ring[0]], 0.006, m_energia, bevel_res=1, poly=True)
        if mi in (0, 2):
            for s in range(4):
                p = k.lerp(f, 0.2 + 0.18 * s)
                CL.cone_between("FrankenScarabeo_Spina_%d_%d" % (i, s), p, p + V((0.04 * (1 if x > 0 else -1), -0.02,
                                                                                  0.02)), 0.007, 0.0, m_gamba[mi], 6)


# ============================================================================
# 03  GARGOYLE-OSSIDIANA
# ============================================================================

def build_gargoyle():
    DS.texspace("Gargoyle")
    Z0 = 0.95
    m_pietra = ST.m_crepe("Gargoyle_Ossidiana_Crepe", pietra=(0.025, 0.022, 0.028), pietra2=(0.08, 0.075, 0.085),
                          luce_c=1450, lucido=2300, forza=30.0, scala=2.4, crepa=0.028, metal=0.6, rough=0.85,
                          profondita=0.02, rado=0.12)
    m_ali = ST.m_crepe("Gargoyle_Ali_Pietra", pietra=(0.03, 0.027, 0.032), pietra2=(0.09, 0.085, 0.09),
                       luce_c=1500, lucido=2300, forza=25.0, scala=2.0, crepa=0.025, metal=0.55, rough=0.9,
                       profondita=0.015, rado=0.14)
    m_fiamma = ST.m_luce("Gargoyle_Occhi_Fiamma", 2000, 100.0, bordo=2800, forza_bordo=140.0)
    m_lingua = ST.m_luce("Gargoyle_Lingue_Fuoco", 1800, 60.0, alpha=0.8)
    m_cuore = ST.m_luce("Gargoyle_Magma_Interno", 1500, 50.0)

    E = [el((0, 0.04, Z0), 0.1, (1.2, 1.0, 0.9)),
         el((0, 0.0, Z0 + 0.1), 0.11, (1.1, 0.9, 1.0)),
         el((0, -0.02, Z0 + 0.24), 0.14, (1.25, 0.85, 0.95)),
         el((0, 0.06, Z0 + 0.3), 0.12, (1.3, 0.9, 0.8)),
         cap((0, -0.04, Z0 + 0.34), (0, -0.1, Z0 + 0.42), 0.06),
         el((0, -0.13, Z0 + 0.47), 0.085, (1.05, 1.1, 1.0)),
         el((0, -0.22, Z0 + 0.44), 0.05, (1.1, 1.3, 0.75)),
         el((0, -0.2, Z0 + 0.405), 0.045, (1.05, 1.2, 0.6)),
         el((0, -0.19, Z0 + 0.5), 0.04, (1.8, 0.7, 0.5))]
    for sx in (-1, 1):
        E += [el((0.17 * sx, -0.02, Z0 + 0.3), 0.065),
              cap((0.17 * sx, -0.02, Z0 + 0.3), (0.26 * sx, -0.08, Z0 + 0.14), 0.045),
              cap((0.26 * sx, -0.08, Z0 + 0.14), (0.2 * sx, -0.2, Z0 + 0.02), 0.038),
              el((0.19 * sx, -0.23, Z0 - 0.0), 0.04, (1.0, 1.2, 0.7)),
              cap((0.1 * sx, 0.04, Z0 - 0.02), (0.17 * sx, -0.14, Z0 + 0.02), 0.06),
              cap((0.17 * sx, -0.14, Z0 + 0.02), (0.14 * sx, 0.0, Z0 - 0.18), 0.045),
              cap((0.14 * sx, 0.0, Z0 - 0.18), (0.14 * sx, -0.13, Z0 - 0.2), 0.035),
              el((0.07 * sx, -0.13, Z0 + 0.43), 0.035, (1.0, 1.0, 0.8))]
    body = CL.metaball_mesh("Gargoyle_Corpo", E, m_pietra, res=0.014)
    for sx in (-1, 1):
        s = side_name(sx)
        # artigli delle mani e dei piedi
        for k in range(3):
            h = V((0.19 * sx + (k - 1) * 0.022, -0.26, Z0 - 0.01))
            CL.cone_between("Gargoyle_Artiglio_Mano_%s%d" % (s, k), h, h + V((0, -0.035, -0.045)), 0.011, 0.0,
                            m_pietra, 6)
            f = V((0.14 * sx + (k - 1) * 0.025, -0.17, Z0 - 0.21))
            CL.cone_between("Gargoyle_Artiglio_Piede_%s%d" % (s, k), f, f + V((0, -0.05, -0.03)), 0.013, 0.0,
                            m_pietra, 6)
        # corna da ariete, orecchie a punta
        CL.tube("Gargoyle_Corno_" + s, [V((0.045 * sx, -0.12, Z0 + 0.53)), V((0.1 * sx, -0.07, Z0 + 0.62)),
                                        V((0.13 * sx, 0.03, Z0 + 0.66)), V((0.11 * sx, 0.11, Z0 + 0.61))],
                [0.024, 0.018, 0.011, 0.002], m_pietra, bevel_res=2)
        ST.cono_piatto("Gargoyle_Orecchio_" + s, (0.085 * sx, -0.1, Z0 + 0.48), (0.2 * sx, -0.05, Z0 + 0.54), 0.035,
                       m_pietra, 0.35, avanti=(0.3 * sx, -1, 0.3))
        # occhi di pura fiamma
        e = CL.sphere("Gargoyle_Occhio_" + s, (0.034 * sx, -0.205, Z0 + 0.478), (0.02, 0.014, 0.014), m_fiamma,
                      seg=16, rings=8)
        CL.no_shadow(e)
        for k in range(2):
            b = V((0.036 * sx, -0.2, Z0 + 0.49))
            ST.cono_piatto("Gargoyle_Fiamma_%s%d" % (s, k), b, b + V((0.03 * sx * (k + 0.5), 0.03, 0.08 - 0.02 * k)),
                           0.012, m_lingua, 0.5, avanti=(0, -1, 0))
        ST.proxy(e, (0.04 * sx, -0.25, Z0 + 0.49), 2000, 2.5)
        # zanne
        CL.cone_between("Gargoyle_Zanna_" + s, (0.03 * sx, -0.25, Z0 + 0.41), (0.028 * sx, -0.26, Z0 + 0.37), 0.009,
                        0.0, m_pietra, 6)
    # coda con la punta a picca
    tail = [V((0, 0.12, Z0)), V((0, 0.3, Z0 - 0.08)), V((0.1, 0.45, Z0 - 0.2)), V((0.05, 0.55, Z0 - 0.35))]
    CL.tube("Gargoyle_Coda", tail, [0.04, 0.03, 0.02, 0.012], m_pietra, bevel_res=2)
    d = (tail[-1] - tail[-2]).normalized()
    OC.fin_mesh("Gargoyle_Punta_Coda", [(0.0, -0.01), (0.03, -0.05), (0.11, 0.0), (0.03, 0.05), (0.0, 0.01)], 0.015,
                m_pietra, CL.frame_matrix(tail[-1] - d * 0.01, d.cross(V((1, 0, 0))), V((1, 0, 0))) @
                Matrix.Rotation(-pi / 2, 4, 'Z'))
    # ali di pietra pesanti, sollevate
    S, Eb, W = V((0.09, 0.08, Z0 + 0.34)), V((0.3, 0.16, Z0 + 0.56)), V((0.44, 0.1, Z0 + 0.76))
    tips = [V((0.72, 0.0, Z0 + 0.92)), V((0.88, 0.22, Z0 + 0.64)), V((0.76, 0.34, Z0 + 0.38)),
            V((0.5, 0.32, Z0 + 0.18))]
    mem, ossa = ST.ala_membrana("Gargoyle_Ala", S, Eb, W, tips, V((0.08, 0.16, Z0 + 0.1)), m_ali, m_pietra,
                                sacca=0.14, gonfia=0.03, righe=5, colonne=4, r_osso=0.02, artiglio=m_pietra)
    ST.solidifica(mem, 0.02, 0.0)
    for p in mem.data.polygons:
        p.use_smooth = False
    ST.specchia_x([mem] + ossa)
    # un cuore di magma dentro il petto, che accende le crepe da dentro
    core = CL.sphere("Gargoyle_Magma", (0, -0.02, Z0 + 0.2), 0.05, m_cuore, seg=12, rings=6)
    ST.proxy(core, (0, -0.25, Z0 + 0.2), 1500, 25.0, nome="Gargoyle_Luce_Petto")
    ST.proxy(core, (0, 0.3, Z0 + 0.35), 1500, 12.0, nome="Gargoyle_Luce_Schiena")
    del body


# ============================================================================
# 04  ZUCCA-INFESTATA
# ============================================================================

def build_zucca():
    DS.texspace("Zucca")
    Z = 1.2
    P = V((0, 0.05, 0.62))
    R, H = 0.27, 0.2
    arancio = 1850
    m_buccia = m_zucca("Zucca_Buccia")
    m_polpa = CL.m_body("Zucca_Polpa_Accesa", (1.0, 0.55, 0.12), rough=0.6, sss=0.8, sss_radius=(1.0, 0.4, 0.1),
                        emit=ST.kelvin(arancio), emit_str=8.0)
    m_nucleo = ST.m_luce("Zucca_Luce_Interna", arancio, 80.0)
    m_fumo = ST.m_volume("Zucca_Fumo_Luminoso", (1.0, 0.7, 0.45), 3.0, luce_c=arancio, forza=1.2, rumore=4.0)
    m_gambo = CL.m_body("Zucca_Gambo", (0.16, 0.14, 0.05), rough=0.8, bump=(25.0, 0.6, 'noise'),
                        mottle=((0.08, 0.1, 0.03), 8.0))
    m_pelo = CL.m_body("Zucca_Falena_Pelo", (0.09, 0.055, 0.03), rough=0.85, sheen=1.0, sheen_tint=(1.0, 0.7, 0.4),
                       bump=(120.0, 0.35, 'noise'))
    m_legno = CL.m_bark("Zucca_Rametti", (0.12, 0.07, 0.035), (0.04, 0.025, 0.012))
    m_occhio = CL.m_body("Zucca_Occhi_Falena", (0.02, 0.012, 0.01), rough=0.1, coat=1.0)
    m_ali = m_foglia_secca("Zucca_Ali_Foglie_Morte")
    m_ali2 = m_foglia_secca("Zucca_Ali_Foglie_Rosse", c1=(0.35, 0.05, 0.02), c2=(0.55, 0.12, 0.03),
                            c3=(0.12, 0.03, 0.01))

    # la zucca: costolata, schiacciata e un po' deforme
    rows = 16
    prof = []
    for i in range(rows + 1):
        t = 0.03 + 0.94 * i / rows
        s = sin(pi * t)
        z = -H * cos(pi * t)
        z += 0.35 * H * (1 - s) ** 4 * (1 if t < 0.5 else -1)
        prof.append((R * s ** 0.75, z))

    def deform(co, a, k):
        f = 1.0 - 0.1 * (1.0 - abs(cos(5 * a))) ** 2
        co = V((co.x * f, co.y * f, co.z))
        n = mnoise.noise(co * 3.0 + V((2.1, 0.3, 1.7)))
        co *= 1.0 + 0.07 * n
        co.x += 0.03 * co.z
        return co

    shell = DS.lathe("Zucca_Guscio", prof, m_buccia, seg=60, cap_bottom=True, cap_top=True, deform=deform)
    shell.data.materials.append(m_polpa)
    shell.location = P
    md = ST.solidifica(shell, 0.022, -1.0)
    md.material_offset = 1
    md.material_offset_rim = 1
    # il volto intagliato (taglierini estrusi verso -Y)
    eye = [(0.045, 0.02), (0.15, 0.035), (0.1, 0.115)]
    mouth_top, mouth_bot = [], []
    for i in range(21):
        x = -0.17 + 0.34 * i / 20
        zt = -0.055 + 0.045 * (x / 0.17) ** 2
        if 0.03 < abs(x) < 0.075:
            zt -= 0.035
        mouth_top.append((x, zt))
        zb = -0.145 + 0.135 * (x / 0.17) ** 2
        if abs(x) < 0.025:
            zb += 0.04
        mouth_bot.append((x, zb))
    shapes = [[(x, z) for x, z in eye], [(-x, z) for x, z in reversed(eye)],
              [(-0.025, -0.012), (0.025, -0.012), (0.0, 0.035)], mouth_top + list(reversed(mouth_bot))[1:-1]]
    cutters = []
    for i, sh in enumerate(shapes):
        c = prisma("Zucca_Taglio_%d" % i, [(x, z) for x, z in sh], -R * 1.6, 0.0, 1, [m_buccia, m_polpa])
        c.location = P
        cutters.append(c)
    cut = unisci("Zucca_Taglierino", cutters)
    cut.data.materials.clear()
    cut.data.materials.append(m_buccia)
    cut.data.materials.append(m_polpa)
    for f in cut.data.polygons:
        f.material_index = 1
    bo = shell.modifiers.new("Volto_Intagliato", 'BOOLEAN')
    bo.operation = 'DIFFERENCE'
    bo.solver = 'EXACT'
    bo.object = cut
    ST.applica(shell)
    bpy.data.objects.remove(cut)
    ST.separa_materiali(shell)
    core = CL.sphere("Zucca_Nucleo", P + V((0, 0.02, -0.02)), 0.12, m_nucleo, seg=16, rings=8)
    CL.no_shadow(core)
    ST.proxy(core, P + V((0, 0.0, 0.0)), arancio, 60.0, nome="Zucca_Luce_Candela")
    ST.proxy(core, P + V((0, -0.35, 0.0)), arancio, 8.0, nome="Zucca_Luce_Volto")
    # fumo luminoso che esce dai buchi
    for i, (x, z) in enumerate(((0.1, 0.07), (-0.1, 0.07), (0.0, -0.07))):
        base = P + V((x, -R * 0.95, z))
        for k in range(3):
            c = base + V((0.02 * k * (1 if x >= 0 else -1), -0.05 - 0.07 * k, 0.07 + 0.12 * k))
            s = 0.05 + 0.03 * k
            f = CL.sphere("Zucca_Fumo_%d_%d" % (i, k), c, (s * 0.6, s * 0.8, s * 1.9), m_fumo, rot=(20 + 15 * k, 0, 0),
                          seg=12, rings=6)
            CL.no_shadow(f)
    # gambo che la tiene attaccata al torace
    CL.tube("Zucca_Gambo", [P + V((0, 0, H * 0.72)), P + V((0.03, 0.02, H + 0.08)), V((0.0, 0.02, Z - 0.16)),
                            V((0, 0.01, Z - 0.08))], [0.04, 0.03, 0.024, 0.02], m_gambo, bevel_res=2)
    ric = [P + V((0.03, 0.02, H + 0.05)) + V((0.06 * cos(a) + 0.02 * a, 0.05 * sin(a), 0.012 * a))
           for a in [i * 0.6 for i in range(12)]]
    CL.tube("Zucca_Viticcio", ric, [0.007 - 0.0005 * i for i in range(12)], m_gambo, bevel_res=1)

    # la falena: torace peloso, occhi, antenne e zampe di rametti
    E = [el((0, 0.0, Z), 0.1, (1.0, 1.25, 1.0)), el((0, -0.15, Z + 0.02), 0.07),
         el((0, 0.13, Z - 0.03), 0.07, (0.9, 1.0, 0.9))]
    CL.metaball_mesh("Zucca_Torace", E, m_pelo, res=0.012)
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Zucca_Occhio_" + s, (0.05 * sx, -0.19, Z + 0.035), 0.032, m_occhio, seg=16, rings=8)
        a = V((0.025 * sx, -0.2, Z + 0.07))
        ant = [a, a + V((0.06 * sx, -0.1, 0.1)), a + V((0.13 * sx, -0.16, 0.2)), a + V((0.16 * sx, -0.2, 0.3))]
        CL.tube("Zucca_Antenna_" + s, ant, [0.008, 0.006, 0.004, 0.002], m_legno, bevel_res=1)
        for k, j in enumerate((1, 2)):
            b = ant[j]
            CL.tube("Zucca_Rametto_%s%d" % (s, k), [b, b + V((0.05 * sx, 0.0, 0.03 + 0.02 * k))], [0.004, 0.0015],
                    m_legno, bevel_res=1)
        for k in range(3):
            a = V((0.05 * sx, -0.07 + 0.08 * k, Z - 0.06))
            knee = a + V((0.12 * sx, -0.03 + 0.03 * k, -0.06))
            foot = knee + V((0.05 * sx, -0.02 + 0.04 * k, -0.18))
            DS.leg("Zucca_Zampa_%s%d" % (s, k), [a, knee, foot], [0.012, 0.009, 0.004], m_legno,
                   joint_mat=m_legno, joint_r=0.013)
    fw = [(-8, 0.18), (6, 0.5), (22, 0.66), (40, 0.6), (58, 0.46), (75, 0.32), (92, 0.16)]
    hw = [(45, 0.12), (60, 0.34), (80, 0.44), (102, 0.38), (125, 0.2)]
    for i, (ctrl, mat, att, sc) in enumerate(((fw, m_ali, (0.07, -0.04, Z + 0.05), (0.2, 5)),
                                               (hw, m_ali2, (0.06, 0.06, Z + 0.02), (0.14, 4)))):
        ws = CL.wing_pair("Zucca_Ala_%d" % i, ctrl, mat, att, elev=18 - 8 * i, sweep=-4 + 10 * i, roll=5, rings=10,
                          cup=0.04, droop=0.12, n=56, scallop=sc)
        for w in ws:
            for vtx in w.data.vertices:
                vtx.co.z += 0.03 * mnoise.noise(vtx.co * 6.0 + V((i, 0.5, 1.3)))
            # nervatura centrale fatta di un rametto
            bpy.context.view_layer.update()
            o = CL.wing_outline(ctrl, 56, sc)
            mid = o[int(len(o) * 0.45)]
            left = w.name.endswith("_L")
            p1 = V((-mid[0] if left else mid[0], mid[1], 0.0)) * 0.95
            mw = w.matrix_world
            CL.tube(w.name + "_Rametto", [mw @ V((0, 0, 0)), mw @ (p1 * 0.5 + V((0, 0, 0.01))), mw @ p1],
                    [0.008, 0.006, 0.002], m_legno, bevel_res=1)


# ============================================================================
# 05  CORVO-PESTE
# ============================================================================

def build_corvo():
    DS.texspace("CorvoPeste")
    acido = (0.42, 1.0, 0.06)
    m_pelle = CL.m_body("CorvoPeste_Pelle_Spennata", (0.2, 0.15, 0.17), rough=0.6, sss=0.2,
                        sss_radius=(1.0, 0.4, 0.4), bump=(70.0, 0.5, 'warts'), mottle=((0.12, 0.08, 0.1), 5.0))
    m_ossa = CL.m_body("CorvoPeste_Costole", (0.72, 0.68, 0.58), rough=0.45, sss=0.1)
    m_mask = m_cuoio("CorvoPeste_Maschera_Cuoio")
    m_ottone = CL.m_body("CorvoPeste_Ottone", (0.55, 0.36, 0.12), rough=0.35, metal=1.0, bump=(50.0, 0.2, 'noise'))
    m_lente = ST.m_vetro_sottile("CorvoPeste_Lenti_Vetro", (0.85, 1.0, 0.8), bordo=acido, forza_bordo=1.0)
    m_bagliore = ST.m_luce("CorvoPeste_Bagliore_Acido", acido, 55.0, bordo=(0.8, 1.0, 0.5), forza_bordo=80.0)
    m_nucleo = ST.m_luce("CorvoPeste_Petto_Radioattivo", acido, 15.0)
    m_alone = CL.m_halo("CorvoPeste_Alone_Tossico", acido, 0.15)
    m_zampe = CL.m_body("CorvoPeste_Zampe", (0.05, 0.045, 0.045), rough=0.5, bump=(60.0, 0.5, 'scales'))
    m_piuma = CL.m_feather("CorvoPeste_Piume_Strappate", (0.01, 0.01, 0.014), (0.02, 0.02, 0.025), acido, 3.0,
                           edge_w=0.07, rachis_w=0.035)
    ST._principled_extra(m_piuma, film=300.0)
    m_piuma["rbx_thick"] = 1
    m_polvere = ST.m_luce("CorvoPeste_Polvere_Tossica", acido, 30.0)

    E = [cap((0, 0.14, 0.46), (0, -0.04, 0.68), 0.1),
         el((0, 0.0, 0.58), 0.11, (0.85, 0.9, 1.15)),
         el((0, -0.12, 0.6), 0.07, (1.1, 0.6, 1.3), neg=True),
         cap((0, -0.04, 0.68), (0, -0.09, 0.82), 0.035),
         el((0, 0.2, 0.42), 0.05)]
    for sx in (-1, 1):
        E.append(cap((0.05 * sx, 0.08, 0.44), (0.055 * sx, 0.06, 0.3), 0.03))
    CL.metaball_mesh("CorvoPeste_Corpo", E, m_pelle, res=0.011)
    # gabbia toracica scoperta con la luce verde acida dentro
    for sx in (-1, 1):
        for i, z in enumerate((0.69, 0.65, 0.61, 0.57, 0.53)):
            w = 1.0 - 0.08 * abs(i - 2)
            pts = [V((0.085 * sx * w, 0.02, z)), V((0.1 * sx * w, -0.07, z - 0.01)), V((0.055 * sx * w, -0.145, z - 0.02)),
                   V((0.008 * sx, -0.165, z - 0.03))]
            CL.tube("CorvoPeste_Costola_%s%d" % (side_name(sx), i), pts, [0.009, 0.008, 0.007, 0.006], m_ossa,
                    bevel_res=2)
    CL.tube("CorvoPeste_Sterno", [V((0, -0.16, 0.7)), V((0, -0.18, 0.6)), V((0, -0.16, 0.5))], [0.01, 0.012, 0.008],
            m_ossa, bevel_res=2)
    core = CL.sphere("CorvoPeste_Cuore_Tossico", (0, -0.08, 0.6), (0.06, 0.05, 0.07), m_nucleo, seg=16, rings=8)
    CL.no_shadow(core)
    h = CL.sphere("CorvoPeste_Alone_Petto", (0, -0.12, 0.6), 0.16, m_alone)
    CL.no_shadow(h)
    ST.proxy(core, (0, -0.2, 0.6), acido, 10.0, nome="CorvoPeste_Luce_Petto")
    # zampe scheletriche con gli artigli
    for sx in (-1, 1):
        s = side_name(sx)
        a = V((0.055 * sx, 0.06, 0.3))
        k = V((0.06 * sx, 0.02, 0.12))
        f = V((0.06 * sx, 0.0, 0.02))
        DS.leg("CorvoPeste_Zampa_" + s, [a, k, f], [0.014, 0.01, 0.009], m_zampe, joint_mat=m_zampe)
        for j, d in enumerate(((-0.4, -1.0), (0.0, -1.0), (0.4, -1.0), (0.0, 1.0))):
            dv = V((d[0] * 0.5 * sx, d[1], 0)).normalized()
            L = 0.09 if d[1] < 0 else 0.06
            p = [f, f + dv * L * 0.6 + V((0, 0, -0.012)), f + dv * L + V((0, 0, -0.018))]
            CL.tube("CorvoPeste_Dito_%s%d" % (s, j), p, [0.008, 0.006, 0.004], m_zampe, bevel_res=1)
            CL.cone_between("CorvoPeste_Artiglio_%s%d" % (s, j), p[-1], p[-1] + dv * 0.03 + V((0, 0, -0.012)), 0.005,
                            0.0, m_ossa, 6)
    # maschera da medico della peste: cappuccio, becco lungo, lenti di vetro
    CL.metaball_mesh("CorvoPeste_Cappuccio", [el((0, -0.1, 0.89), 0.078, (0.95, 1.12, 1.0)),
                                              el((0, -0.03, 0.85), 0.07, (1.0, 1.0, 0.8))], m_mask, res=0.01)
    beak = DS.spline([V((0, -0.155, 0.875)), V((0, -0.26, 0.855)), V((0, -0.37, 0.81)), V((0, -0.46, 0.745)),
                      V((0, -0.51, 0.69))], 16)
    rad = [0.052 * (1 - i / 15) ** 1.1 + 0.002 for i in range(16)]
    DS.sweep_mesh("CorvoPeste_Becco", beak, rad, m_mask, ring=20, squash=0.8, frames=DS.frames_up(beak))
    tans, norms, _b = DS.frames_up(beak)
    for i in range(1, 13):
        p = beak[i] + norms[i] * rad[i] * 0.98
        t = tans[i]
        side = t.cross(norms[i]).normalized()
        CL.tube("CorvoPeste_Cucitura_%02d" % i, [p - side * 0.01, p + norms[i] * 0.003, p + side * 0.01], 0.0022,
                m_ossa, bevel_res=1, res=2)
    for sx in (-1, 1):
        s = side_name(sx)
        n = V((0.4 * sx, -1.0, 0.12)).normalized()
        c = V((0.045 * sx, -0.158, 0.906))
        fr = CL.frame_matrix(c, V((0, 0, 1)), n)
        rim = DS.lathe("CorvoPeste_Montatura_" + s, [(0.029, -0.004), (0.036, -0.004), (0.036, 0.012),
                                                    (0.03, 0.014)], m_ottone, seg=24, cap_bottom=False)
        rim.matrix_world = fr
        lens = CL.sphere("CorvoPeste_Lente_" + s, (0, 0, 0), 1.0, m_lente, seg=20, rings=10)
        lens.matrix_world = fr @ Matrix.Translation((0, 0, 0.004)) @ Matrix.Diagonal((0.03, 0.03, 0.016, 1.0))
        CL.no_shadow(lens)
        glow = CL.sphere("CorvoPeste_Sguardo_" + s, (0, 0, 0), 1.0, m_bagliore, seg=16, rings=8)
        glow.matrix_world = fr @ Matrix.Translation((0, 0, -0.008)) @ Matrix.Diagonal((0.022, 0.022, 0.01, 1.0))
        ST.proxy(glow, fr @ V((0, 0, 0.05)), acido, 1.5)
        CL.sphere("CorvoPeste_Narice_" + s, (0.018 * sx, -0.3, 0.85), (0.006, 0.012, 0.004), m_ottone, seg=8,
                  rings=4)
        for k in range(2):
            CL.sphere("CorvoPeste_Borchia_%s%d" % (s, k), (0.05 * sx, -0.17 + 0.02 * k, 0.845 - 0.035 * k), 0.007,
                      m_ottone, seg=8, rings=4)
    strap = [V((0.075 * cos(a), -0.08 + 0.085 * sin(a), 0.9)) for a in [pi * (0.05 + 0.9 * i / 12) for i in range(13)]]
    CL.tube("CorvoPeste_Cinghia", strap, 0.009, m_mask, bevel_res=1)
    # ali di piume nere strappate, semiaperte
    random.seed(4)
    meshes = [piume_strappate("CorvoPeste_Piuma_%d" % i, 0.34, 0.06, m_piuma, seed=i) for i in range(4)]
    for sx in (-1, 1):
        s = side_name(sx)
        sh = V((0.085 * sx, 0.02, 0.66))
        wr = V((0.3 * sx, 0.07, 0.62))
        CL.tube("CorvoPeste_Braccio_" + s, [sh, sh.lerp(wr, 0.5) + V((0, 0, 0.03)), wr], [0.02, 0.015, 0.01], m_pelle,
                bevel_res=2)
        for k in range(8):
            if k in (2, 6) and sx > 0:
                continue                    # piume mancanti
            t = k / 7
            base = sh.lerp(wr, 0.35 + 0.65 * t)
            d = V((sx * (0.35 + 0.65 * t), 0.35 + 0.45 * (1 - t), -0.9 + 0.3 * t)).normalized()
            m = CL.frame_matrix(base, d, V((sx * 0.3, -0.2, 0.9)))
            ob = bpy.data.objects.new("CorvoPeste_Remigante_%s%d" % (s, k), random.choice(meshes))
            CL.link(ob)
            sc = 0.8 + 0.4 * t
            ob.matrix_world = m @ Matrix.Diagonal((sc, sc, sc, 1.0))
    for k in range(4):
        ob = bpy.data.objects.new("CorvoPeste_Coda_%d" % k, meshes[k % 4])
        CL.link(ob)
        m = CL.frame_matrix(V((0, 0.22, 0.42)), V(((k - 1.5) * 0.12, 1.0, -0.55)), V((0, -0.2, 1)))
        ob.matrix_world = m @ Matrix.Diagonal((1.0, 1.1, 1.0, 1.0))
    # polvere tossica che si stacca dalle ali
    em = CL.sphere("CorvoPeste_Polvere_Emettitore", (0, 0.1, 0.45), (0.55, 0.3, 0.3), None, seg=12, rings=6)
    grain = CL.sphere("CorvoPeste_Granello", (0, 0, -3), 0.005, m_polvere, seg=6, rings=3)
    CL.particle_scatter(em, grain, 350, size=1.0, size_random=0.8, seed=5)
    rnd = random.Random(8)
    for i in range(14):
        sx = rnd.choice((-1, 1))
        p = V((sx * rnd.uniform(0.25, 0.55), rnd.uniform(0.0, 0.3), rnd.uniform(0.2, 0.6)))
        CL.sphere("CorvoPeste_Polvere_%02d" % i, p, rnd.uniform(0.006, 0.012), m_polvere, seg=6, rings=3)


# ============================================================================
# 06  OCCHIO-FLUTTUANTE
# ============================================================================

def build_occhio():
    DS.texspace("OcchioFluttuante")
    C = V((0, 0, 1.5))
    R = 0.42
    gaze = V((0, -1, -0.27)).normalized()
    giallo = (0.85, 1.0, 0.06)
    lim = radians(36)
    m_scl = m_sclera("OcchioFluttuante_Sclera_Bagnata", C, gaze, R)
    m_ir = m_iride("OcchioFluttuante_Iride_Lampadina", giallo, 70.0)
    m_cornea = ST.m_vetro_sottile("OcchioFluttuante_Cornea", (0.95, 1.0, 0.9), bordo=giallo, forza_bordo=0.8)
    m_nervo = CL.m_body("OcchioFluttuante_Nervo_Ottico", (0.75, 0.45, 0.4), rough=0.18, sss=0.6,
                        sss_radius=(1.0, 0.3, 0.25), coat=0.9, coat_rough=0.05, spec=0.8,
                        mottle=((0.55, 0.12, 0.12), 9.0), bump=(30.0, 0.35, 'noise'))
    m_muscolo = CL.m_body("OcchioFluttuante_Muscoli", (0.45, 0.06, 0.06), rough=0.3, sss=0.5,
                          sss_radius=(1.0, 0.2, 0.2), coat=0.7, bump=(80.0, 0.5, 'noise'))
    m_vaso = CL.m_body("OcchioFluttuante_Vasi", (0.35, 0.01, 0.02), rough=0.2, coat=0.8, sss=0.4)
    m_fascio = OC.m_beam("OcchioFluttuante_Fascio_Volumetrico", giallo, 0.35, length=4.2)
    fr = CL.frame_matrix(C, V((0, 0, 1)), gaze)
    # bulbo con il buco per l'iride concava
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=CL.det(64, 16), v_segments=CL.det(32, 10), radius=R)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=V((0, 0, R * cos(lim))), plane_no=V((0, 0, 1)), clear_outer=True)
    eye = CL.mesh_object("OcchioFluttuante_Bulbo", bm, m_scl)
    eye.matrix_world = fr
    rl, zl = R * sin(lim), R * cos(lim)
    prof = [(0.002, zl - 0.07), (0.05, zl - 0.066), (0.1, zl - 0.055), (0.16, zl - 0.035), (0.21, zl - 0.014), (rl, zl)]
    iris = DS.lathe("OcchioFluttuante_Iride", prof, m_ir, seg=48, cap_bottom=False)
    iris.matrix_world = fr
    CL.no_shadow(iris)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=CL.det(48, 12), v_segments=CL.det(24, 8), radius=R * 1.015)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=V((0, 0, R * cos(lim + 0.03))), plane_no=V((0, 0, 1)), clear_inner=True)
    cor = CL.mesh_object("OcchioFluttuante_Cornea", bm, m_cornea)
    cor.matrix_world = fr
    CL.no_shadow(cor)
    # fascio di luce volumetrica a cono + faretto
    src = C + gaze * (zl - 0.04)
    beam = CL.cone_between("OcchioFluttuante_Fascio", src, src + gaze * 4.2, rl * 0.9, 1.35, m_fascio, 32)
    CL.no_shadow(beam)
    sp = CL.add_light("OcchioFluttuante_Faro", 'SPOT', src + gaze * 0.02, 900.0, giallo, 0.1, spot_size=34)
    CL.aim(sp, src + gaze * 3.0)
    sp.data.spot_blend = 0.35
    ST.proxy(iris, src + gaze * 0.06, giallo, 6.0, nome="OcchioFluttuante_Luce_Iride")
    # nervo ottico che pende come una coda
    back = C - gaze * R * 0.92
    nerve = DS.spline([back + gaze * 0.05, back + V((0.0, 0.1, -0.12)), back + V((0.08, 0.2, -0.38)),
                       back + V((-0.04, 0.16, -0.62)), back + V((0.03, 0.08, -0.85)), V((0.05, 0.12, 0.34))], 26)
    rn = [0.075 - 0.04 * (i / 25) + 0.006 * sin(i * 1.3) for i in range(26)]
    DS.sweep_mesh("OcchioFluttuante_Nervo", nerve, rn, m_nervo, ring=16)
    rnd = random.Random(3)
    end = nerve[-1]
    for i in range(5):
        a = TAU * i / 5
        pts = [end + V((0.02 * cos(a), 0.02 * sin(a), 0.0)),
               end + V((0.05 * cos(a), 0.05 * sin(a), -0.05)),
               end + V((0.07 * cos(a) + rnd.uniform(-0.02, 0.02), 0.07 * sin(a), -0.1 - rnd.uniform(0, 0.06)))]
        CL.tube("OcchioFluttuante_Filamento_%d" % i, pts, [0.012, 0.007, 0.002], m_nervo, bevel_res=1)
    # muscoli recisi e vasi sanguigni
    up = fr.to_3x3() @ V((0, 1, 0))
    side = fr.to_3x3() @ V((1, 0, 0))
    for i, d in enumerate((up, -up, side, -side)):
        a = C + d * R * 0.93 - gaze * 0.12
        b = a - gaze * 0.12 + d * 0.06 + V((0, 0, -0.08))
        c = b + V((0.0, 0.03, -0.12))
        CL.tube("OcchioFluttuante_Muscolo_%d" % i, [a, b, c], [0.035, 0.028, 0.02], m_muscolo, bevel_res=2)
    for i in range(6):
        a0 = TAU * i / 6 + 0.3
        pts = []
        for k in range(8):
            th = pi * 0.95 - k * 0.1
            dloc = V((sin(th) * cos(a0 + 0.08 * k), sin(th) * sin(a0 + 0.08 * k), cos(th)))
            pts.append(fr @ (dloc * R * 1.006))
        CL.tube("OcchioFluttuante_Vaso_%d" % i, pts, [0.009 - 0.0009 * k for k in range(8)], m_vaso, bevel_res=1)


# ============================================================================
# 07  CALDERONE-ANIMATO
# ============================================================================

def build_calderone():
    DS.texspace("Calderone")
    Z = 0.2
    viola = (0.55, 0.08, 1.0)
    fucsia = (1.0, 0.08, 0.7)
    m_ghisa = m_ruggine("Calderone_Ghisa_Arrugginita")
    m_poz = m_pozione("Calderone_Pozione", luce_c=viola)
    m_b1 = m_bolla("Calderone_Bolle_Fucsia", fucsia, 12.0)
    m_b2 = m_bolla("Calderone_Bolle_Viola", viola, 12.0)
    m_rana = CL.m_body("Calderone_Zampe_Rana", (0.12, 0.33, 0.05), rough=0.25, coat=0.6, sss=0.4,
                       sss_radius=(0.4, 1.0, 0.3), mottle=((0.05, 0.15, 0.02), 9.0), bump=(40.0, 0.3, 'warts'))
    m_ventre = CL.m_body("Calderone_Ventre_Rana", (0.55, 0.52, 0.3), rough=0.35, sss=0.3)
    # pentola in ghisa
    prof = [(0.02, 0.0), (0.14, 0.008), (0.24, 0.045), (0.305, 0.12), (0.322, 0.2), (0.305, 0.29), (0.27, 0.36),
            (0.262, 0.4), (0.285, 0.425), (0.292, 0.445), (0.272, 0.455), (0.25, 0.435), (0.246, 0.33)]
    pot = DS.lathe("Calderone_Pentola", [(r, z + Z) for r, z in prof], m_ghisa, seg=56, cap_bottom=True)
    parts = [pot]
    band = DS.lathe("Calderone_Fascia", [(0.318, Z + 0.17), (0.332, Z + 0.18), (0.332, Z + 0.22), (0.318, Z + 0.23)],
                    m_ghisa, seg=56, cap_bottom=False)
    parts.append(band)
    for i in range(16):
        a = TAU * i / 16
        parts.append(CL.sphere("Calderone_Rivetto_%02d" % i, (0.334 * cos(a), 0.334 * sin(a), Z + 0.2), 0.009,
                               m_ghisa, seg=8, rings=4))
    for sx in (-1, 1):
        s = side_name(sx)
        parts.append(CL.sphere("Calderone_Attacco_" + s, (0.3 * sx, 0, Z + 0.34), (0.02, 0.04, 0.03), m_ghisa,
                               seg=10, rings=5))
        ring = [V((0.33 * sx + 0.03 * sx * sin(a), 0.055 * cos(a), Z + 0.3 - 0.055 * sin(a) * 0.6))
                for a in [pi * i / 10 - pi / 2 for i in range(11)]]
        parts.append(CL.tube("Calderone_Maniglia_" + s, ring, 0.011, m_ghisa, bevel_res=2))
    # pozione che ribolle e trabocca
    Zp = Z + 0.37
    rnd = random.Random(11)
    E = [el((0, 0, Zp), 1.0, (0.255, 0.255, 0.03))]
    for i in range(9):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(0.0, 0.2)
        E.append(bl((r * cos(a), r * sin(a), Zp + 0.01), rnd.uniform(0.025, 0.055)))
    E += [el((0.2, -0.16, Zp + 0.04), 0.05, (1.0, 1.0, 0.8)), cap((0.24, -0.2, Zp + 0.06), (0.27, -0.23, Zp + 0.03), 0.03)]
    for k, (a, L) in enumerate(((-0.75, 0.14), (-0.55, 0.22), (-0.95, 0.1), (2.4, 0.12))):
        x, y = 0.29 * cos(a), 0.29 * sin(a)
        E.append(cap((x, y, Z + 0.44), (x * 1.08, y * 1.08, Z + 0.44 - L), 0.018))
        E.append(bl((x * 1.08, y * 1.08, Z + 0.44 - L - 0.01), 0.024))
    poz = CL.metaball_mesh("Calderone_Pozione", E, m_poz, res=0.012)
    parts.append(poz)
    tilt = DS.pivot("Calderone_Inclinazione", (0, 0, Z), parts)
    tilt.rotation_euler = (radians(-7), 0, 0)
    ST.proxy(poz, (0, -0.02, Zp + 0.12), viola, 25.0, nome="Calderone_Luce_Pozione")
    # bolle luminose che schizzano fuori e scoppiettano nell'aria
    for i in range(18):
        t = i / 17
        a = rnd.uniform(0, TAU)
        r = 0.05 + 0.3 * t * rnd.uniform(0.5, 1.0)
        p = V((r * cos(a), r * sin(a) - 0.06, Zp + 0.08 + 0.75 * t + rnd.uniform(-0.05, 0.05)))
        CL.sphere("Calderone_Bolla_%02d" % i, p, rnd.uniform(0.018, 0.05) * (1.1 - 0.4 * t),
                  m_b1 if i % 2 else m_b2, seg=14, rings=7)
    em = CL.sphere("Calderone_Bolle_Emettitore", (0, -0.05, Zp + 0.5), (0.35, 0.35, 0.45), None, seg=12, rings=6)
    grain = CL.sphere("Calderone_Bollicina", (0, 0, -3), 0.012, m_b1, seg=10, rings=5)
    CL.particle_scatter(em, grain, 160, size=1.0, size_random=0.7, seed=6)
    ST.proxy(poz, (0.1, -0.1, Zp + 0.45), fucsia, 8.0, nome="Calderone_Luce_Bolle")
    # due tozze zampe di rana che corrono
    for sx, (knee, ankle, foot) in ((1, ((0.2, -0.13, 0.16), (0.17, -0.2, 0.05), (0.17, -0.31, 0.012))),
                                    (-1, ((-0.21, 0.1, 0.1), (-0.17, 0.22, 0.07), (-0.17, 0.33, 0.02)))):
        s = side_name(sx)
        hip = V((0.12 * sx, 0.0, Z + 0.03))
        E = [cap(hip, knee, 0.055), cap(knee, ankle, 0.04), el(hip, 0.07, (1.0, 1.1, 0.8))]
        fwd = (V(foot) - V(ankle))
        fwd.z = 0
        fwd.normalize()
        sd = V((fwd.y, -fwd.x, 0))
        for j in range(4):
            tip = V(foot) + fwd * 0.07 + sd * (j - 1.5) * 0.035
            E.append(cap(V(ankle).lerp(V(foot), 0.6), tip, 0.014))
            E.append(bl(tip + V((0, 0, 0.004)), 0.02))
        E.append(el(V(foot) + fwd * 0.02, 0.06, (1.0, 1.0, 0.18)))
        CL.metaball_mesh("Calderone_Zampa_" + s, E, m_rana, res=0.012)
        CL.sphere("Calderone_Coscia_Chiara_" + s, hip.lerp(V(knee), 0.4) + V((0, 0, -0.03)), (0.05, 0.06, 0.03),
                  m_ventre, seg=12, rings=6)


# ============================================================================
# 08  IL VERME DELL'OHIO "NEXTBOT"
# ============================================================================

_Q50 = np.array([[16, 11, 10, 16, 24, 40, 51, 61], [12, 12, 14, 19, 26, 58, 60, 55],
                 [14, 13, 16, 24, 40, 57, 69, 56], [14, 17, 22, 29, 51, 87, 80, 62],
                 [18, 22, 37, 56, 68, 109, 103, 77], [24, 35, 55, 64, 81, 104, 113, 92],
                 [49, 64, 78, 87, 103, 121, 120, 101], [72, 92, 95, 98, 112, 100, 103, 99]], dtype=float)


def _jpeg(img, qualita=8):
    """Compressione JPEG vera (DCT 8x8, quantizzazione, colore sottocampionato):
    serve per l'aspetto 'compresso e sgranato' del meme."""
    N = img.shape[0]
    x = img * 255.0
    Y = 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    Cb = 128 - 0.1687 * x[..., 0] - 0.3313 * x[..., 1] + 0.5 * x[..., 2]
    Cr = 128 + 0.5 * x[..., 0] - 0.4187 * x[..., 1] - 0.0813 * x[..., 2]
    scale = 5000.0 / qualita if qualita < 50 else 200 - 2 * qualita
    Qt = np.maximum(1, np.floor((_Q50 * scale + 50) / 100))
    k = np.arange(8)
    Cm = np.cos((2 * k[None, :] + 1) * k[:, None] * pi / 16) * np.where(k[:, None] == 0, math.sqrt(1 / 8),
                                                                     math.sqrt(2 / 8))

    def canale(ch, q):
        n = ch.shape[0]
        b = (ch - 128).reshape(n // 8, 8, n // 8, 8).transpose(0, 2, 1, 3)
        d = np.einsum('ij,abjk,lk->abil', Cm, b, Cm)
        d = np.round(d / q) * q
        r = np.einsum('ji,abjk,kl->abil', Cm, d, Cm)
        return r.transpose(0, 2, 1, 3).reshape(n, n) + 128

    def sotto(ch):
        s = ch.reshape(N // 2, 2, N // 2, 2).mean(axis=(1, 3))
        s = canale(s, Qt * 1.6)
        return np.repeat(np.repeat(s, 2, axis=0), 2, axis=1)

    Y = canale(Y, Qt)
    Cb, Cr = sotto(Cb), sotto(Cr)
    r = Y + 1.402 * (Cr - 128)
    g = Y - 0.344136 * (Cb - 128) - 0.714136 * (Cr - 128)
    b = Y + 1.772 * (Cb - 128)
    return np.clip(np.stack([r, g, b], -1) / 255.0, 0, 1)


def immagine_nextbot(nome="Verme_Faccia_Meme", N=96):
    """Faccia meme inquietante, inventata e disegnata qui (niente foto vere):
    occhi neri troppo grandi con le pupille minuscole, sorriso enorme pieno di
    denti, poi compressa in JPEG a bassissima qualita' e sgranata."""
    img = bpy.data.images.get(nome)
    if img is not None:
        return img
    rng = np.random.RandomState(13)
    yy, xx = np.mgrid[0:N, 0:N] / (N - 1.0)
    out = np.zeros((N, N, 3))
    out[:] = (0.1, 0.09, 0.08)
    out += rng.rand(N, N, 1) * 0.06
    fx, fy = (xx - 0.5) / 0.37, (yy - 0.52) / 0.47
    rr = fx ** 2 + fy ** 2
    face = rr < 1
    skin = np.array([0.84, 0.76, 0.64])
    shade = (0.62 + 0.38 * (1 - np.clip(rr, 0, 1)) ** 0.5)[..., None] * skin
    out[face] = shade[face]
    for ex, ey, rx, ry, dx in ((0.34, 0.4, 0.09, 0.075, 0.018), (0.66, 0.39, 0.1, 0.085, -0.02)):
        bag = (((xx - ex) / (rx * 1.45)) ** 2 + ((yy - ey - 0.035) / (ry * 1.7)) ** 2 < 1) & face
        out[bag] *= 0.62
        m = ((xx - ex) / rx) ** 2 + ((yy - ey) / ry) ** 2 < 1
        out[m] = (0.02, 0.015, 0.015)
        p = ((xx - ex - dx) / 0.016) ** 2 + ((yy - ey + 0.01) / 0.016) ** 2 < 1
        out[p] = (0.96, 0.95, 0.9)
        brow = (np.abs(yy - (ey - 0.12 - 0.3 * (xx - ex) ** 2 * 8)) < 0.012) & (np.abs(xx - ex) < rx * 1.1)
        out[brow] = (0.25, 0.18, 0.12)
    mx = (xx - 0.5) / 0.3
    top = 0.63 - 0.09 * mx ** 2
    bot = 0.8 - 0.26 * mx ** 2
    mouth = (np.abs(mx) < 1) & (yy > top) & (yy < bot)
    out[mouth] = (0.25, 0.02, 0.03)
    teeth = mouth & (((yy < top + 0.045) | (yy > bot - 0.04)) & (np.mod(mx * 9, 1.0) < 0.78))
    out[teeth] = (0.93, 0.9, 0.78)
    lines = face & (np.abs(np.abs(xx - 0.5) - (0.3 + 0.05 * (yy - 0.6) * 4)) < 0.008) & (yy > 0.52) & (yy < 0.85)
    out[lines] *= 0.55
    out = np.clip(out * 1.15 + rng.randn(N, N, 1) * 0.03, 0, 1)
    out = _jpeg(out, 7)
    out = np.clip((out - 0.5) * 1.25 + 0.5 + rng.randn(N, N, 3) * 0.025, 0, 1)
    img = bpy.data.images.new(nome, N, N, alpha=False)
    px = np.ones((N, N, 4), dtype=np.float32)
    # l'immagine e' in sRGB: il buffer di Blender per le immagini byte e' sRGB
    px[..., :3] = out[::-1]
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def m_faccia(nome, img):
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tex = nb.node('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Closest'
    tc = nb.texcoord(use_space=False)
    nb.link(tc.outputs['UV'], tex.inputs['Vector'])
    em = nb.emission(tex.outputs['Color'], 1.6)
    nb.output(em)
    nb.bake_output("RBX_COLOR", nb.emission(tex.outputs['Color'], 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(tex.outputs['Color'], 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_thick"] = 1
    mat["rbx_emit_strength"] = 1.0
    CL.diffuse_display(mat, (0.8, 0.7, 0.6))
    return mat


def build_verme():
    DS.texspace("VermeOhio")
    import colorsys
    n = 7
    ys = [-0.3 + 0.19 * i for i in range(n)]
    rads = [0.19, 0.21, 0.21, 0.2, 0.18, 0.155, 0.13]
    segs = []
    for i, (y, r) in enumerate(zip(ys, rads)):
        h = i / n
        c = colorsys.hsv_to_rgb(h, 0.9, 1.0)
        c = tuple(x ** 2.2 for x in c)
        m = CL.m_body("VermeOhio_Segmento_RGB_%d" % i, tuple(0.45 * x for x in c), rough=0.2, coat=0.8, sss=0.3,
                      sss_radius=tuple(0.08 * x + 0.01 for x in c), emit=c, emit_str=2.5, rim=c, rim_str=1.2)
        z = r + 0.01 + 0.06 * sin(pi * min(1.0, i / (n - 1)))
        segs.append(CL.sphere("VermeOhio_Segmento_%d" % i, (0, y, z), (r * 1.02, r * 0.9, r * 0.95), m,
                              seg=28, rings=14))
        if 1 <= i <= 5:
            for sx in (-1, 1):
                CL.cone_between("VermeOhio_Zampetta_%s%d" % (side_name(sx), i), (0.55 * r * sx, y, z - 0.6 * r),
                                (0.6 * r * sx, y - 0.01, 0.0), 0.04, 0.022, m, 10)
        ST.proxy(segs[-1], (0.3 * (1 if i % 2 else -1), y, 0.08), c, 4.0)
    lanterna = ST.m_luce("VermeOhio_Coda_Lucciola", (1.0, 0.95, 0.7), 25.0)
    CL.sphere("VermeOhio_Lanterna", (0, ys[-1] + 0.12, rads[-1] + 0.02), (0.09, 0.08, 0.085), lanterna, seg=20,
              rings=10)
    # la faccia: un piano 2D completamente piatto con il meme compresso
    img = immagine_nextbot()
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.33, calc_uvs=True)
    face = CL.mesh_object("VermeOhio_Faccia_Piatta", bm, m_faccia("VermeOhio_Faccia_Meme", img), smooth=False)
    face.location = (0, ys[0] - 0.2, 0.4)
    face.rotation_euler = (radians(90), 0, 0)
    bpy.context.view_layer.update()
    face.parent = segs[0]
    face.matrix_parent_inverse = segs[0].matrix_world.inverted()
    ST.billboard(face)


# ============================================================================
# SCENA DEI MOSTRI
# ============================================================================

def scena_gruppo(which):
    ST.mondo((0.004, 0.003, 0.008), (0.02, 0.012, 0.035), 1.0, nome="Notte_Mostri")
    ST.pavimento("Terreno_Cimitero", (0.018, 0.016, 0.016), (0.045, 0.038, 0.035), scala=0.7, rough=(0.7, 0.95))
    ST.nebbia("Foschia_Mostri", (0, 3, 1.6), (30, 30, 3.2), (0.6, 0.55, 0.8), 0.018)
    ST.luce("Luna_Mostri", 'SUN', (0, 0, 10), 0.6, (0.55, 0.6, 1.0), 2.0, rot=(55, 0, -30))
    ST.luci_studio(which, chiave=(0.75, 0.8, 1.0), contro=(0.6, 0.4, 1.0))


def scena_occhio():
    ST.nebbia("Foschia_Faro", (0, -2.5, 1.2), (6, 7, 2.4), (0.9, 1.0, 0.8), 0.025)


def scena_pipistrello():
    m = ST.m_luce("Luna_Piena", (1.0, 0.92, 0.8), 3.0)
    CL.sphere("Luna_Sfondo", (1.5, 12, 4.5), 1.6, m)
    ST.luce("Luce_Luna_Retro", 'SPOT', (1, 6, 3), 400.0, (0.7, 0.75, 1.0), 0.5, rot=(-110, 0, 180), spot=40)


def scena_zucca():
    ST.luce("Luce_Arancio_Bassa", 'POINT', (0.8, -1.2, 0.3), 30.0, 1900, 0.3)


CREATURE_MOSTRI = {
    #  chiave         (collezione,                       funzione,                camera: target, dist, elev, azim, lente)
    "pipistrello": ("M01_Pipistrello-Sanguisuga",      build_pipistrello,       ((0, 0.05, 1.02), 3.3, 4, 38, 50)),
    "scarabeo":    ("M02_Franken-Scarabeo",            build_franken_scarabeo,  ((0, -0.1, 0.42), 3.6, 28, 35, 50)),
    "gargoyle":    ("M03_Gargoyle-Ossidiana",          build_gargoyle,          ((0, 0.05, 1.2), 3.8, 8, 28, 50)),
    "zucca":       ("M04_Zucca-Infestata",             build_zucca,             ((0, 0.0, 0.95), 4.0, 12, 22, 50)),
    "corvo":       ("M05_Corvo-Peste",                 build_corvo,             ((0, -0.1, 0.6), 3.0, 10, 35, 50)),
    "occhio":      ("M06_Occhio-Fluttuante",           build_occhio,            ((0, -0.25, 1.25), 4.0, 8, 38, 50)),
    "calderone":   ("M07_Calderone-Animato",           build_calderone,         ((0, -0.05, 0.55), 3.2, 18, 30, 50)),
    "verme":       ("M08_Verme-Ohio-Nextbot",          build_verme,             ((0, 0.1, 0.35), 3.4, 14, 35, 50)),
}

DISPOSIZIONE_MOSTRI = {
    "gargoyle":    (-4.6, 4.8, 15),
    "pipistrello": (-1.5, 4.6, 0),
    "occhio":      (1.6, 4.4, -30),
    "corvo":       (4.4, 4.8, -25),
    "zucca":       (-3.8, 0.8, 20),
    "scarabeo":    (-1.2, 0.3, 30),
    "calderone":   (1.4, 0.4, -15),
    "verme":       (3.7, 0.6, -35),
}

SCENE_MOSTRI = {"occhio": scena_occhio, "pipistrello": scena_pipistrello, "zucca": scena_zucca}


def build(which=None, engine=None, clean=None):
    ST.build_serie(CREATURE_MOSTRI, DISPOSIZIONE_MOSTRI, which or CREATURA, scena_gruppo, SCENE_MOSTRI,
                   ((0, 2.5, 0.75), 10.2, 13, 0, 32), ST.SETUP["mostri"], engine or MOTORE, clean)


def main():
    ST.main(build)


if __name__ == "__main__":
    main()
