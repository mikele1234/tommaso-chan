# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE DELL'INFERNO - sesta serie per Blender (modelli statici).

    01  CERBERO PICCINO          (il guardiano a tre teste, fari ambra sulle fronti)
    02  CARONTE BARCHETTA        (addome a barca, remo, lanterna fantasma)
    03  ADE OMBRETTA             (bidente, elmo, mantello con il bordo viola)
    04  PERSEFONE MELAGRANA      (addome a melagrana con sei semi rubino)
    05  ALICHINO ARLECCHINO      (elitre a rombi colorati, cornetti con i campanelli)
    06  GHIACCIOLO, RE DI GHIACCIO (tre facce, sei ali, prigioniero del Cocito)
    07  FLEGETONTE SCINTILLA     (addome a lampada lava, ali di fiamma)
    08  TUNG TUNG TUNG SAHUR INFERNALE (il tronco arrabbiato con la mazza rovente)

Solo modelli 3D: nessuna animazione. Setup EEVEE Next dell'inferno: AgX High
Contrast, esposizione -0.7, Bloom 0.5, vignettatura leggera (vedi
creature_strumenti.py). Richiede gli altri file creature_*.py nella stessa
cartella.

USO DA RIGA DI COMANDO
    blender --background --python creature_inferno.py -- \\
            --creatura cerbero --salva cerbero.blend --render cerbero.png
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

# "cerbero", "caronte", "ade", "persefone", "alichino", "ghiacciolo",
# "flegetonte", "tungtung" oppure "tutte"
CREATURA = "tutte"

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

# chitina e ali del setup dell'inferno
CHIT = dict(rough=0.4, coat=0.4, sss=0.05)
ALA = dict(alpha=0.2, film=400.0)


def chitina(nome, base, **kw):
    d = dict(CHIT)
    d.update(kw)
    return ST.m_chitina(nome, base, **d)


# ============================================================================
# STRUMENTI DELL'INFERNO
# ============================================================================

def serpentello(nome, ctrl, r0, mat, m_occhi, m_lingua=None, n=14):
    """Serpentello (Curve con Taper): sottile in coda, testa a goccia, occhietti
    luminosi e lingua biforcuta."""
    pts = DS.spline([V(p) for p in ctrl], n)
    rad = [r0 * (0.3 + 0.7 * min(1.0, i / (n * 0.6))) * (0.85 if i > n - 3 else 1.0) for i in range(n)]
    obs = [CL.tube(nome, pts, rad, mat, bevel_res=2)]
    d = (pts[-1] - pts[-2]).normalized()
    up = V((0, 0, 1)) if abs(d.z) < 0.9 else V((0, 1, 0))
    c = pts[-1] + d * r0 * 1.2
    h = CL.sphere(nome + "_Testa", (0, 0, 0), 1.0, mat, seg=14, rings=7)
    h.matrix_world = CL.frame_matrix(c, up, d) @ Matrix.Diagonal((r0 * 1.5, r0 * 1.1, r0 * 2.0, 1.0))
    obs.append(h)
    side = d.cross(up).normalized()
    upv = side.cross(d).normalized()
    for sx in (-1, 1):
        obs.append(CL.sphere("%s_Occhio_%s" % (nome, side_name(sx)), c + side * sx * r0 * 1.1 + upv * r0 * 0.5
                             + d * r0 * 0.5, r0 * 0.35, m_occhi, seg=8, rings=4))
    if m_lingua is not None:
        a = c + d * r0 * 1.9
        b = a + d * r0 * 1.2
        obs.append(CL.tube(nome + "_Lingua", [a, b, b + d * r0 * 0.8 + side * r0 * 0.5], [r0 * 0.12, r0 * 0.1,
                                                                                         r0 * 0.04], m_lingua,
                           bevel_res=1, poly=True))
        obs.append(CL.tube(nome + "_Lingua2", [b, b + d * r0 * 0.8 - side * r0 * 0.5], [r0 * 0.1, r0 * 0.04],
                           m_lingua, bevel_res=1, poly=True))
    return obs


def zampa_tozza(prefisso, a, knee, paw, r, mat, m_unghie=None):
    DS.leg(prefisso, [V(a), V(knee), V(paw)], [r, r * 0.9, r * 0.8], mat, joint_mat=mat, joint_r=r)
    p = V(paw)
    CL.sphere(prefisso + "_Zampa", p + V((0, -0.01, -0.01)), (r * 1.3, r * 1.45, r * 0.75), mat, seg=16, rings=8)
    for k in range(3):
        CL.sphere("%s_Dito_%d" % (prefisso, k), p + V(((k - 1) * r * 0.75, -r * 1.25, -r * 0.3)), r * 0.42,
                  m_unghie or mat, seg=10, rings=5)


def blocco_ghiaccio(nome, centro, dim, mat, seed=3):
    """Blocco di ghiaccio: cubo smussato (Bevel), suddiviso e deformato
    (Displace a rumore)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.06, segments=3, affect='EDGES')
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=CL.det(3, 1), use_grid_fill=True)
    off = V((seed * 1.3, seed * 0.7, seed * 2.1))
    for v in bm.verts:
        p = V((v.co.x * dim[0], v.co.y * dim[1], v.co.z * dim[2]))
        n = mnoise.fractal(p * 2.2 + off, 0.6, 2.0, 3)
        p += v.co.normalized() * 0.035 * n
        v.co = p + V(centro)
    return CL.mesh_object(nome, bm, mat, smooth=False)


def m_ghiaccio_cocito(nome):
    """Ghiaccio del Cocito: Transmission 1, IOR 1.31, Roughness 0.2 e dentro
    un Volume Absorption ciano."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    vo = nb.voronoi(tc.outputs['Object'], 3.0, 'DISTANCE_TO_EDGE')
    crepe = nb.maprange(vo.outputs['Distance'], 0.02, 0.0)
    pb = nb.principled(base=(0.8, 0.95, 1.0), rough=nb.maprange(crepe, 0.0, 1.0, 0.2, 0.5), trans=1.0, ior=1.31,
                       spec=0.6)
    nb.set(pb, 'Normal', nb.bump(nb.noise(tc.outputs['Object'], 6.0, 5.0, 0.6).outputs['Fac'], 0.15, 0.01))
    nb.output(nb.add_shader(pb.outputs[0], nb.emission((0.5, 0.85, 1.0), nb.math('MULTIPLY', crepe, 0.6))))
    ab = nb.node('ShaderNodeVolumeAbsorption', {'Color': (0.35, 0.85, 1.0), 'Density': 1.2})
    nb.link(ab.outputs[0], nb.out.inputs['Volume'])
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True), ('thickness_mode', 'SPHERE')):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    CL.diffuse_display(mat, (0.6, 0.85, 1.0))
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = [0.6, 0.88, 1.0]
    mat["rbx_transp"] = 0.45
    mat["rbx_material"] = "Ice"
    return mat


def m_legno_barca(nome, base=(0.08, 0.045, 0.025)):
    """Assi di legno vecchio e bagnato."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    assi = nb.math('FRACT', nb.math('MULTIPLY', sep.outputs['Z'], 22.0))
    fuga = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', assi, 0.5)), 0.44, 0.5)
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y')
    nb.set(wv, 'Scale', 6.0)
    nb.set(wv, 'Distortion', 8.0)
    nb.set(wv, 'Detail', 4.0)
    nb.link(tc.outputs['Object'], wv.inputs['Vector'])
    col = nb.ramp(wv.outputs['Fac'], [(0.2, tuple(c * 0.45 for c in base)), (0.8, base)])
    col = NV.rgb_mix(nb, fuga, col, (0.01, 0.006, 0.004))
    pb = nb.principled(base=col, rough=0.62, spec=0.45, coat=0.2)
    nb.set(pb, 'Normal', nb.bump(nb.math('ADD', nb.math('MULTIPLY', wv.outputs['Fac'], 0.4), nb.math(
        'SUBTRACT', 1.0, fuga)), 0.4, 0.01))
    nb.output(pb.outputs[0])
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.62
    CL.diffuse_display(mat, base)
    return mat


def m_mantello(nome, base=(0.012, 0.008, 0.02), luce=(0.5, 0.1, 1.0), forza=25.0):
    """Mantello di Ade: velluto scuro, la luce viola solo sul bordo (Layer
    Weight / Fresnel come fattore dell'emissione e l'orlo del mantello) e un
    mix con Transparent BSDF gia' pronto per l'invisibilita' (Visibilita' = 1)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    orlo = nb.math('MAXIMUM', nb.maprange(v, 0.95, 0.99),
                   nb.maprange(nb.math('MINIMUM', u, nb.math('SUBTRACT', 1.0, u)), 0.014, 0.003))
    fres = nb.maprange(nb.fresnel(0.35), 0.45, 1.0)
    fac = nb.math('MAXIMUM', orlo, nb.math('MULTIPLY', fres, 0.5))
    nz = nb.noise(tc.outputs['Object'], 4.0, 4.0, 0.6)
    pb = nb.principled(base=base, rough=0.75, sheen=1.0, sheen_tint=luce, spec=0.3)
    nb.set(pb, 'Normal', nb.bump(nz.outputs['Fac'], 0.15, 0.01))
    sh = nb.add_shader(pb.outputs[0], nb.emission(luce, nb.math('MULTIPLY', fac, ST.lum(forza))))
    vis = nb.value(1.0)
    vis.node.label = "Visibilita (1 = visibile, 0 = invisibile)"
    nb.output(nb.mix_shader(vis, nb.transparent(), sh))
    nb.bake_output("RBX_COLOR", nb.mix_shader(orlo, nb.emission(base, 1.0), nb.emission(luce, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(orlo, nb.emission((0, 0, 0), 1.0), nb.emission(luce, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_thick"] = 1
    mat["rbx_emit_strength"] = 6.0
    mat["rbx_highlight"] = list(luce)
    CL.diffuse_display(mat, base)
    return mat


def m_semi(nome):
    """Semi di melagrana: Subsurface rosso ed emissione; il colore passa da un
    Color Ramp (0 = rubino 2000 K sottoterra, 1 = verde 5500 K di primavera)
    comandato dal valore 'Stagione'."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    stag = nb.value(0.0)
    stag.node.label = "Stagione (0 = sottoterra, 1 = primavera)"
    rosso = nb.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    nb.set(rosso, 0, 1.0)
    nb.link(ST.colore(nb, 2000), rosso.inputs[6])
    nb.set(rosso, 7, (1.0, 0.08, 0.14))
    verde = nb.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    nb.set(verde, 0, 1.0)
    nb.link(ST.colore(nb, 5500), verde.inputs[6])
    nb.set(verde, 7, (0.3, 1.0, 0.3))
    col = NV.rgb_mix(nb, stag, rosso.outputs[2], verde.outputs[2])
    pb = nb.principled(base=(0.6, 0.02, 0.05), rough=0.08, sss=1.0, sss_radius=(1.0, 0.1, 0.1), coat=1.0, spec=0.7)
    nb.set(pb, 'Subsurface Scale', 0.05)
    nb.output(nb.add_shader(pb.outputs[0], nb.emission(col, ST.lum(25.0))))
    CL.diffuse_display(mat, (0.8, 0.02, 0.06))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = [1.0, 0.05, 0.1]
    return mat


def m_arlecchino(nome, colori, forza=40.0, scala=9.0):
    """Rombi da Arlecchino: Voronoi regolare (Randomness 0) ruotato di 45 gradi;
    ogni rombo prende un colore a caso (colore della cella) e si accende."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    mp = nb.node('ShaderNodeMapping')
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    nb.set(mp, 'Rotation', (0.0, 0.0, radians(45)))
    nb.set(mp, 'Scale', (1.0, 1.35, 1.0))
    vo = nb.voronoi(mp.outputs[0], scala, 'F1', randomness=0.0)
    vd = nb.voronoi(mp.outputs[0], scala, 'DISTANCE_TO_EDGE', randomness=0.0)
    bw = nb.node('ShaderNodeRGBToBW')
    nb.link(vo.outputs['Color'], bw.inputs[0])
    n = len(colori)
    col = nb.ramp(bw.outputs[0], [(i / n, c) for i, c in enumerate(colori)], interp='CONSTANT')
    bordo = nb.maprange(vd.outputs['Distance'], 0.06, 0.03)
    pb = nb.principled(base=col, rough=0.3, coat=0.6, spec=0.5)
    nero = nb.principled(base=(0.01, 0.01, 0.01), rough=0.3, coat=0.6)
    sh = nb.add_shader(pb.outputs[0], nb.emission(col, ST.lum(forza)))
    nb.output(nb.mix_shader(bordo, sh, nero.outputs[0]))
    nb.bake_output("RBX_COLOR", nb.mix_shader(bordo, nb.emission(col, 1.0), nb.emission((0.01, 0.01, 0.01), 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(bordo, nb.emission(col, 1.0), nb.emission((0, 0, 0), 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_emit_strength"] = 6.0
    mat["rbx_rough"] = 0.3
    CL.diffuse_display(mat, colori[0])
    return mat


def m_tronco(nome, luce_c=1600, forza=90.0):
    """Corteccia carbonizzata nera (Roughness 0.9) con crepe di lava: Voronoi
    (Distance to Edge) come maschera dell'emissione rossa."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    mp = nb.node('ShaderNodeMapping')
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    nb.set(mp, 'Scale', (1.0, 1.0, 0.35))
    vo = nb.voronoi(mp.outputs[0], 5.5, 'DISTANCE_TO_EDGE')
    nz = nb.noise(tc.outputs['Object'], 3.0, 5.0, 0.6)
    crepe = nb.math('MULTIPLY', nb.maprange(vo.outputs['Distance'], 0.02, 0.004),
                    nb.maprange(nz.outputs['Fac'], 0.45, 0.6))
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z')
    nb.set(wv, 'Scale', 2.0)
    nb.set(wv, 'Distortion', 10.0)
    nb.set(wv, 'Detail', 6.0)
    nb.link(tc.outputs['Object'], wv.inputs['Vector'])
    col = nb.ramp(wv.outputs['Fac'], [(0.2, (0.006, 0.005, 0.005)), (0.8, (0.03, 0.022, 0.018))])
    pb = nb.principled(base=col, rough=0.9, spec=0.3)
    nb.set(pb, 'Normal', nb.bump(nb.math('ADD', wv.outputs['Fac'], nb.math('MULTIPLY', crepe, -1.0)), 0.6, 0.02))
    gcol = ST.colore(nb, luce_c)
    nb.output(nb.mix_shader(crepe, pb.outputs[0], nb.emission(gcol, ST.lum(forza))))
    nb.bake_output("RBX_COLOR", nb.mix_shader(crepe, nb.emission(col, 1.0), nb.emission(gcol, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(crepe, nb.emission((0, 0, 0), 1.0), nb.emission(gcol, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.9
    mat["rbx_emit_strength"] = 8.0
    CL.diffuse_display(mat, (0.02, 0.015, 0.012))
    return mat


def m_mazza(nome, forza=50.0):
    """Mazza rovente: Color Ramp nero -> rosso -> giallo verso i bordi."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    f = nb.maprange(nb.facing(0.4), 0.0, 1.0)
    nz = nb.noise(nb.texcoord().outputs['Object'], 18.0, 4.0, 0.6)
    t = nb.math('ADD', f, nb.math('MULTIPLY', nb.math('SUBTRACT', nz.outputs['Fac'], 0.5), 0.3))
    col = nb.ramp(t, [(0.15, (0.02, 0.005, 0.0)), (0.45, (1.0, 0.04, 0.0)), (0.85, (1.0, 0.75, 0.05))])
    s = nb.maprange(t, 0.1, 0.9, 0.15, 1.0)
    nb.output(nb.emission(col, nb.math('MULTIPLY', s, ST.lum(forza))))
    CL.diffuse_display(mat, (1.0, 0.2, 0.0))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = [1.0, 0.18, 0.0]
    return mat


def m_flusso(nome, forza=40.0):
    """Fuoco che scorre nell'addome: Noise + Wave lungo Y (Mapping), Color Ramp
    lava da 1700 K a un nucleo giallo-bianco di 3800 K."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    mp = nb.node('ShaderNodeMapping')
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    nb.set(mp, 'Location', (0.0, 0.0, 0.0))
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y')
    nb.set(wv, 'Scale', 5.0)
    nb.set(wv, 'Distortion', 6.0)
    nb.set(wv, 'Detail', 3.0)
    nb.link(mp.outputs[0], wv.inputs['Vector'])
    nz = nb.noise(mp.outputs[0], 4.0, 6.0, 0.6)
    t = nb.math('ADD', nb.math('MULTIPLY', wv.outputs['Fac'], 0.6), nb.math('MULTIPLY', nz.outputs['Fac'], 0.5))
    lava = ST.colore(nb, 1700)
    nucleo = ST.colore(nb, 3800)
    col = NV.rgb_mix(nb, nb.maprange(t, 0.55, 0.85), lava, nucleo)
    col = NV.rgb_mix(nb, nb.maprange(t, 0.35, 0.15), col, (0.5, 0.02, 0.0))
    s = nb.math('MULTIPLY', nb.maprange(t, 0.1, 0.9, 0.3, 1.3), ST.lum(forza))
    nb.output(nb.emission(col, s))
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_emit_strength"] = 8.0
    CL.diffuse_display(mat, ST.kelvin(1700))
    return mat


def fiore(prefisso, centro, normale, r, m_petali, m_centro, petali=5):
    """Fiorellino a 5 petali (alle punte delle ali di Persefone)."""
    n = V(normale).normalized()
    fr = CL.frame_matrix(V(centro), n.orthogonal(), n)
    obs = []
    for i in range(petali):
        a = TAU * i / petali
        d = V((cos(a), sin(a), 0.25))
        p = CL.sphere("%s_Petalo_%d" % (prefisso, i), (0, 0, 0), 1.0, m_petali, seg=10, rings=5)
        m = fr @ CL.frame_matrix(d * r * 0.6, V((0, 0, 1)), d)
        p.matrix_world = m @ Matrix.Diagonal((r * 0.45, r * 0.18, r * 0.7, 1.0))
        obs.append(p)
    obs.append(CL.sphere(prefisso + "_Centro", fr @ V((0, 0, r * 0.12)), r * 0.28, m_centro, seg=10, rings=5))
    return obs


def spiga(prefisso, base, direzione, lung, m_stelo, m_chicchi):
    """Antenna a spiga di grano: stelo, chicchi a due file e reste."""
    d = V(direzione).normalized()
    b = V(base)
    side = d.cross(V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))).normalized()
    up = side.cross(d).normalized()
    stelo = [b, b + d * lung * 0.4 + up * lung * 0.05, b + d * lung]
    CL.tube(prefisso + "_Stelo", stelo, [0.006, 0.005, 0.003], m_stelo, bevel_res=1)
    for i in range(9):
        t = 0.5 + 0.48 * i / 8
        p = b + d * lung * t + up * lung * 0.05 * (1 - t)
        for sd in (-1, 1):
            q = p + side * sd * 0.012 * (1.1 - 0.5 * t)
            ch = CL.sphere("%s_Chicco_%d%s" % (prefisso, i, "AB"[sd > 0]), (0, 0, 0), 1.0, m_chicchi, seg=8,
                           rings=4)
            dd = (d + side * sd * 0.5).normalized()
            ch.matrix_world = CL.frame_matrix(q, up, dd) @ Matrix.Diagonal((0.008, 0.007, 0.015, 1.0))
            CL.tube("%s_Resta_%d%s" % (prefisso, i, "AB"[sd > 0]), [q + dd * 0.012, q + dd * 0.06 + d * 0.02],
                    [0.0012, 0.0004], m_stelo, bevel_res=0, poly=True)


# ============================================================================
# 01  CERBERO PICCINO
# ============================================================================

def testa_cane(m_pelo, m_muso, m_naso, m_occhi, m_faro, m_serpe, m_serpe_occhi, m_collare, m_borchie, m_lingua):
    """Testina di cagnolone costruita all'origine con il muso verso -Y (poi
    viene istanziata tre volte)."""
    obs = []
    E = [el((0, 0, 0), 0.1, (1.0, 1.05, 0.95)), el((0, -0.11, -0.03), 0.06, (0.95, 1.2, 0.75)),
         el((0, -0.05, 0.05), 0.05, (1.5, 0.6, 0.5))]
    for sx in (-1, 1):
        E.append(el((0.045 * sx, -0.1, -0.05), 0.035))
    obs.append(CL.metaball_mesh("Cane_Testa", E, m_pelo, res=0.012))
    obs.append(CL.sphere("Cane_Muso", (0, -0.14, -0.045), (0.05, 0.045, 0.035), m_muso, seg=16, rings=8))
    obs.append(CL.sphere("Cane_Naso", (0, -0.19, -0.018), (0.026, 0.018, 0.018), m_naso, seg=12, rings=6))
    obs.append(CL.sphere("Cane_Lingua", (0.01, -0.165, -0.085), (0.022, 0.03, 0.008), m_lingua, rot=(-20, 0, 8),
                         seg=10, rings=5))
    for sx in (-1, 1):
        s = side_name(sx)
        obs.append(CL.sphere("Cane_Occhio_" + s, (0.047 * sx, -0.085, 0.022), 0.021, m_occhi, seg=14, rings=7))
        obs.append(ST.cono_piatto("Cane_Orecchio_" + s, (0.065 * sx, 0.0, 0.07), (0.13 * sx, 0.03, -0.02), 0.045,
                                  m_pelo, 0.35, avanti=(0.3 * sx, -1, 0)))
        obs.append(CL.cone_between("Cane_Zanna_" + s, (0.025 * sx, -0.17, -0.06), (0.024 * sx, -0.172, -0.085),
                                   0.006, 0.0, m_borchie, 6))
        # antenne a serpentello
        a = V((0.035 * sx, -0.02, 0.085))
        obs += serpentello("Cane_Antenna_Serpe_" + s, [a, a + V((0.03 * sx, 0.0, 0.07)), a + V((0.08 * sx, -0.04, 0.12)),
                                                       a + V((0.1 * sx, -0.09, 0.1))], 0.011, m_serpe, m_serpe_occhi,
                           m_lingua, n=10)
    obs.append(CL.sphere("Cane_Faro", (0, -0.075, 0.075), (0.03, 0.02, 0.028), m_faro, seg=16, rings=8))
    ring = [V((0.085 * cos(a), 0.06, -0.035 + 0.075 * sin(a))) for a in [TAU * i / 16 for i in range(17)]]
    obs.append(CL.tube("Cane_Collare", ring, 0.016, m_collare, bevel_res=2))
    for i in range(6):
        a = TAU * i / 6 + 0.3
        p = V((0.085 * cos(a), 0.06, -0.035 + 0.075 * sin(a)))
        d = (p - V((0, 0.06, -0.035))).normalized()
        obs.append(CL.cone_between("Cane_Borchia_%d" % i, p, p + d * 0.03, 0.01, 0.0, m_borchie, 6))
    return obs


def build_cerbero():
    DS.texspace("Cerbero")
    ambra = 2400
    m_chit = DS.m_chitin_veins("Cerbero_Chitina_Brace", (0.045, 0.016, 0.01), (0.012, 0.005, 0.004),
                               (1.0, 0.32, 0.05), vein_emit=2.0, scale=7.0, rough=0.4)
    m_pelo = CL.m_body("Cerbero_Pelo", (0.05, 0.028, 0.02), rough=0.75, sheen=0.9, sheen_tint=(1.0, 0.6, 0.3),
                       bump=(110.0, 0.35, 'noise'), rim=ST.kelvin(ambra), rim_str=0.3)
    m_muso = CL.m_body("Cerbero_Muso", (0.12, 0.065, 0.035), rough=0.7, sheen=0.6, bump=(90.0, 0.25, 'noise'))
    m_naso = CL.m_body("Cerbero_Naso", (0.01, 0.008, 0.008), rough=0.15, coat=1.0, bump=(150.0, 0.3, 'warts'))
    m_occhi = CL.m_body("Cerbero_Occhi_Fresnel", (0.02, 0.01, 0.005), rough=0.08, coat=1.0,
                        rim=ST.kelvin(ambra), rim_str=3.0, rim_power=0.25)
    m_faro = ST.m_luce("Cerbero_Fari_Ambra", ambra, 60.0, bordo=3200, forza_bordo=80.0)
    m_serpe = CL.m_body("Cerbero_Serpentelli", (0.07, 0.09, 0.03), rough=0.35, coat=0.5, bump=(70.0, 0.4, 'scales'),
                        mottle=((0.02, 0.03, 0.01), 12.0))
    m_serpe_occhi = ST.m_luce("Cerbero_Occhi_Serpi", ambra, 30.0)
    m_collare = CL.m_body("Cerbero_Collare", (0.02, 0.012, 0.01), rough=0.5, coat=0.4)
    m_borchie = CL.m_body("Cerbero_Borchie", (0.6, 0.55, 0.5), rough=0.25, metal=1.0)
    m_lingua = CL.m_body("Cerbero_Lingua", (0.6, 0.08, 0.1), rough=0.3, sss=0.5, coat=0.6)

    E = [el((0, 0.0, 0.38), 0.16, (1.1, 1.15, 0.9)), el((0, -0.2, 0.48), 0.12, (1.2, 0.9, 1.0)),
         el((0, 0.3, 0.38), 0.17, (1.05, 1.25, 0.88))]
    CL.metaball_mesh("Cerbero_Torace", E, m_chit, res=0.016)
    C, R = V((0, 0.32, 0.41)), (0.2, 0.3, 0.17)
    for sx in (-1, 1):
        ST.guscio("Cerbero_Elitra_" + side_name(sx), C, R, m_chit,
                  [((0.012 * sx, 0, 0), (sx, 0, 0)), ((0, 0, 0.38), (0, 0, 1))])
    # tre colli e tre teste (la stessa testa istanziata tre volte)
    master = testa_cane(m_pelo, m_muso, m_naso, m_occhi, m_faro, m_serpe, m_serpe_occhi, m_collare, m_borchie,
                        m_lingua)
    teste = [((-0.3, -0.52, 0.72), (-0.65, -1.0, -0.15)), ((0.0, -0.6, 0.85), (0.0, -1.0, 0.2)),
             ((0.3, -0.52, 0.72), (0.65, -1.0, -0.1))]
    mats = [ST.frame(p, d) for p, d in teste]
    gruppi = ST.istanze(master, mats, "Cerbero_Testa")
    for i, ((p, d), grp) in enumerate(zip(teste, gruppi)):
        p, d = V(p), V(d).normalized()
        b = V((p.x * 0.35, -0.22, 0.5))
        tip = p - d * 0.06 + V((0, 0, -0.06))
        CL.tube("Cerbero_Collo_%d" % i, [b, b.lerp(tip, 0.5) + V((0, 0, 0.08)), tip], [0.075, 0.065, 0.06], m_pelo,
                bevel_res=3)
        faro = next(o for o in grp if "Faro" in o.name)
        ST.proxy(faro, p + d * 0.12 + V((0, 0, 0.1)), ambra, 6.0, nome="Cerbero_Luce_Faro_%d" % i)
    # criniera di serpentelli attorno all'attacco dei colli
    rnd = random.Random(5)
    for i in range(7):
        a = pi * (0.1 + 0.8 * i / 6)
        b = V((0.17 * cos(a), -0.12 + 0.05 * sin(a), 0.54 + 0.04 * sin(a)))
        d = V((cos(a) * 0.7, 0.4, 0.9)).normalized()
        c1 = b + d * 0.08
        c2 = c1 + V((rnd.uniform(-0.05, 0.05), 0.05, 0.08))
        c3 = c2 + V((cos(a) * 0.06, -0.05, 0.02))
        serpentello("Cerbero_Criniera_%d" % i, [b, c1, c2, c3], 0.016, m_serpe, m_serpe_occhi, m_lingua, n=10)
    # coda che finisce con una testina di serpente
    serpentello("Cerbero_Coda", [V((0, 0.58, 0.38)), V((0, 0.78, 0.43)), V((0.1, 0.93, 0.58)), V((0.06, 1.0, 0.74)),
                                 V((0.0, 0.96, 0.83))], 0.035, m_serpe, m_serpe_occhi, m_lingua, n=16)
    # zampe tozze da cagnone
    for i, y in enumerate((-0.14, 0.08, 0.3)):
        for sx in (-1, 1):
            zampa_tozza("Cerbero_Zampa_%s%d" % (side_name(sx), i), (0.16 * sx, y, 0.33), (0.26 * sx, y - 0.02, 0.2),
                        (0.27 * sx, y - 0.04, 0.05), 0.065, m_pelo, m_naso)


# ============================================================================
# 02  CARONTE BARCHETTA
# ============================================================================

def build_caronte():
    DS.texspace("Caronte")
    brace = 1800
    fantasma = 9500
    m_legno = m_legno_barca("Caronte_Legno_Barca")
    m_cloak = chitina("Caronte_Mantello_Elitre", (0.022, 0.024, 0.028), rough=0.75, coat=0.1,
                         bump=(18.0, 0.5, 'noise'))
    m_vuoto = CL.m_body("Caronte_Ombra_Cappuccio", (0.002, 0.002, 0.003), rough=0.9)
    m_occhi = ST.m_luce("Caronte_Occhi_Brace", brace, 80.0)
    m_capelli = CL.m_body("Caronte_Capelli_Bianchi", (0.75, 0.75, 0.72), rough=0.6, sheen=1.0)
    m_remo = CL.m_body("Caronte_Remo", (0.06, 0.04, 0.025), rough=0.55, coat=0.3, bump=(30.0, 0.3, 'noise'))
    m_oro = CL.m_body("Caronte_Obolo_Oro", (1.0, 0.72, 0.28), rough=0.22, metal=1.0, bump=(60.0, 0.3, 'noise'))
    m_ferro = CL.m_body("Caronte_Ferro_Lanterna", (0.05, 0.05, 0.05), rough=0.4, metal=0.9)
    m_vetro = ST.m_vetro_sottile("Caronte_Vetro_Lanterna", (0.8, 1.0, 0.95), bordo=fantasma, forza_bordo=1.0)
    m_fiamma = ST.m_luce("Caronte_Fiamma_Fantasma", fantasma, 50.0)
    m_alone = ST.m_volume("Caronte_Alone_Lanterna", (0.7, 1.0, 0.95), 3.0, luce_c=fantasma, forza=0.8,
                          roblox="aura")
    m_zampe = chitina("Caronte_Zampe", (0.02, 0.02, 0.022))

    # addome a barchetta: sezioni a U, prua a punta, poi Solidify
    L, B = 1.15, 0.2
    rows, cols = CL.det(26, 10), CL.det(14, 6)
    bm = bmesh.new()
    grid = []
    for i in range(rows + 1):
        t = i / rows
        y = -L * 0.5 + L * t
        w = B * math.sqrt(max(0.0, 1.0 - ((t - 0.56) / 0.56) ** 2))
        zt = 0.3 + 0.12 * (2 * t - 1) ** 2 + 0.12 * (1 - t) ** 8
        zb = 0.08 + 0.1 * (2 * t - 1) ** 4
        row = []
        for j in range(cols + 1):
            s = -1.0 + 2.0 * j / cols
            row.append(bm.verts.new((w * s, y, zb + (zt - zb) * abs(s) ** 2.2)))
        grid.append(row)
    for i in range(rows):
        for j in range(cols):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bm.faces.new(grid[rows])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    hull = CL.mesh_object("Caronte_Addome_Barca", bm, m_legno)
    ST.solidifica(hull, 0.02, 1.0)
    CL.add_subsurf(hull, 1, 1)
    # bordo (capodibanda) e panca
    edge = []
    for sgn in (-1, 1):
        pts = []
        for i in range(0, rows + 1, 2):
            t = i / rows
            y = -L * 0.5 + L * t
            w = B * math.sqrt(max(0.0, 1.0 - ((t - 0.56) / 0.56) ** 2))
            pts.append(V((w * sgn, y, 0.3 + 0.12 * (2 * t - 1) ** 2 + 0.12 * (1 - t) ** 8 + 0.01)))
        edge.append(pts)
    CL.tube("Caronte_Capodibanda", edge[0] + list(reversed(edge[1]))[1:], 0.014, m_legno, bevel_res=1)
    DS.box("Caronte_Panca", (0, 0.25, 0.26), (0.36, 0.1, 0.025), m_legno)
    # torace, cappuccio-mantello (elitre) e il volto d'ombra
    E = [el((0, -0.05, 0.4), 0.1, (1.0, 1.1, 1.2)), el((0, -0.12, 0.55), 0.08)]
    CL.metaball_mesh("Caronte_Torace", E, m_zampe, res=0.014)
    rnd = random.Random(2)

    def pieghe(co, a, k):
        return V((co.x * (1 + 0.06 * sin(9 * a) * k / 8), co.y * (1 + 0.06 * sin(9 * a) * k / 8), co.z))

    cloak = DS.lathe("Caronte_Mantello", [(0.07, 0.72), (0.1, 0.66), (0.125, 0.58), (0.14, 0.48), (0.15, 0.4),
                                          (0.155, 0.32), (0.155, 0.28)], m_cloak, seg=40,
                     cap_bottom=False, deform=pieghe)
    cloak.location = (0, 0.02, 0)
    ST.guscio("Caronte_Cappuccio", (0, -0.14, 0.78), (0.11, 0.12, 0.13), m_cloak,
                     [((0, -0.2, 0.76), (0.0, 1.0, 0.35))], spessore=0.015)
    CL.sphere("Caronte_Volto_Ombra", (0, -0.15, 0.77), (0.08, 0.06, 0.09), m_vuoto, seg=16, rings=8)
    for sx in (-1, 1):
        e = CL.sphere("Caronte_Occhio_" + side_name(sx), (0.03 * sx, -0.21, 0.79), (0.013, 0.008, 0.009), m_occhi,
                      seg=10, rings=5)
        ST.proxy(e, (0.03 * sx, -0.26, 0.8), brace, 0.8)
    # capelli bianchi e barba (le "lanose gote")
    for i in range(16):
        a = rnd.uniform(-1.2, 1.2)
        b = V((0.07 * sin(a), -0.2 + 0.03 * abs(sin(a)), 0.72 + rnd.uniform(-0.02, 0.02)))
        pts = [b, b + V((0.01 * sin(a), -0.03, -0.05)), b + V((0.02 * sin(a), -0.03, -0.12 - rnd.uniform(0, 0.06)))]
        CL.tube("Caronte_Barba_%02d" % i, pts, [0.006, 0.004, 0.001], m_capelli, bevel_res=1, poly=True)
    for i in range(8):
        sx = 1 if i % 2 else -1
        b = V((0.085 * sx, -0.17, 0.82 - 0.015 * i))
        CL.tube("Caronte_Capelli_%d" % i, [b, b + V((0.03 * sx, -0.02, -0.04)), b + V((0.05 * sx, -0.01, -0.12))],
                [0.005, 0.004, 0.001], m_capelli, bevel_res=1, poly=True)
    # l'obolo d'oro sul petto
    coin = ST.moneta_mesh("Caronte_Obolo", 0.035, 0.008, m_oro, seg=20)
    coin.matrix_world = CL.frame_matrix(V((0, -0.19, 0.5)), V((0, 0, 1)), V((0, -1, 0.15)))
    # antenne fuse in un remo lungo, tenuto con le zampe anteriori
    a1, a2 = V((0.03, -0.18, 0.86)), V((-0.02, -0.18, 0.86))
    j = V((0.12, -0.22, 1.02))
    for k, a in enumerate((a1, a2)):
        CL.tube("Caronte_Antenna_%d" % k, [a, a.lerp(j, 0.5) + V((0, -0.02, 0.01)), j], [0.008, 0.009, 0.014],
                m_remo, bevel_res=1)
    tipo = V((0.46, 0.32, 0.12))
    CL.tube("Caronte_Remo_Asta", [j, j.lerp(tipo, 0.5), tipo], 0.016, m_remo, bevel_res=2)
    dr = (tipo - j).normalized()
    pala = CL.sphere("Caronte_Remo_Pala", (0, 0, 0), 1.0, m_remo, seg=16, rings=8)
    pala.matrix_world = CL.frame_matrix(tipo + dr * 0.12, V((1, 0, 0)), dr) @ Matrix.Diagonal((0.07, 0.012, 0.16, 1))
    for sx, t in ((1, 0.25), (-1, 0.12)):
        grip = j.lerp(tipo, t)
        sh = V((0.07 * sx, -0.1, 0.45))
        DS.leg("Caronte_Zampa_Remo_" + side_name(sx), [sh, sh.lerp(grip, 0.5) + V((0.05 * sx, -0.08, 0.0)), grip],
               [0.014, 0.012, 0.01], m_zampe, joint_mat=m_zampe)
    # la lanterna fantasma sulla prua, con l'alone di Volume Scatter
    bow = V((0, -L * 0.5 + 0.04, 0.5))
    hook = V((0, -L * 0.5 - 0.1, 0.78))
    CL.tube("Caronte_Asta_Lanterna", [bow + V((0, 0.04, -0.14)), bow + V((0, 0, 0.12)), hook + V((0, 0.06, 0.02)),
                                      hook], 0.011, m_ferro, bevel_res=1)
    Lc = hook + V((0, 0, -0.14))
    CL.tube("Caronte_Gancio", [hook, hook + V((0, -0.01, -0.04)), Lc + V((0, 0, 0.07))], 0.004, m_ferro, bevel_res=1)
    cage = DS.lathe("Caronte_Lanterna_Tetto", [(0.055, 0.04), (0.045, 0.055), (0.015, 0.075), (0.01, 0.08)], m_ferro,
                    seg=16, cap_bottom=True, cap_top=True)
    cage.location = Lc
    base = DS.lathe("Caronte_Lanterna_Base", [(0.01, -0.065), (0.05, -0.06), (0.052, -0.045), (0.045, -0.04)], m_ferro,
                    seg=16, cap_bottom=True, cap_top=True)
    base.location = Lc
    for k in range(4):
        a = TAU * k / 4 + pi / 4
        CL.tube("Caronte_Lanterna_Sbarra_%d" % k, [Lc + V((0.047 * cos(a), 0.047 * sin(a), -0.045)),
                                                  Lc + V((0.047 * cos(a), 0.047 * sin(a), 0.045))], 0.004, m_ferro,
                bevel_res=0, poly=True)
    glass = CL.sphere("Caronte_Lanterna_Vetro", Lc, (0.044, 0.044, 0.05), m_vetro, seg=16, rings=8)
    CL.no_shadow(glass)
    flame = CL.sphere("Caronte_Lanterna_Fiamma", Lc + V((0, 0, -0.005)), (0.016, 0.016, 0.03), m_fiamma, seg=12,
                      rings=6)
    CL.no_shadow(flame)
    halo = CL.sphere("Caronte_Lanterna_Alone", Lc, 0.2, m_alone, seg=16, rings=8)
    CL.no_shadow(halo)
    ST.proxy(flame, Lc + V((0, -0.06, 0.0)), fantasma, 12.0, nome="Caronte_Luce_Lanterna")
    # zampe posteriori dentro la barca
    for sx in (-1, 1):
        DS.leg("Caronte_Zampa_Dietro_" + side_name(sx), [V((0.06 * sx, 0.02, 0.36)), V((0.14 * sx, 0.1, 0.3)),
                                                          V((0.12 * sx, 0.16, 0.14))], [0.012, 0.01, 0.008], m_zampe)


# ============================================================================
# 03  ADE OMBRETTA
# ============================================================================

def mantello_mesh(nome, mat, y0=0.06, z0=0.74, apertura=92.0, cols=26, rows=12):
    """Telo del mantello (elitre allargate): si apre dietro le spalle e scende
    fino a terra con le pieghe. UV: u attraverso, v dall'alto al fondo."""
    cols, rows = CL.det(cols, 10), CL.det(rows, 5)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(rows + 1):
        v = j / rows
        row = []
        for i in range(cols + 1):
            u = i / cols
            th = radians(-apertura + 2 * apertura * u)
            r = 0.16 + 0.42 * v ** 1.1 + 0.035 * v * sin(9 * th + 0.5)
            z = z0 - 0.7 * v - 0.04 * v * cos(9 * th)
            row.append(bm.verts.new((r * sin(th), y0 + r * cos(th) * 0.85, max(0.015, z))))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (a / cols, b / rows)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = CL.mesh_object(nome, bm, mat)
    ST.solidifica(ob, 0.01, 0.0)
    return ob


def build_ade():
    DS.texspace("Ade")
    viola = (0.5, 0.1, 1.0)
    m_chit = chitina("Ade_Chitina_Nera", (0.012, 0.008, 0.018), rough=0.3, coat=0.6, film=250.0)
    m_elmo = CL.m_body("Ade_Elmo_Oscurita", (0.02, 0.016, 0.025), rough=0.28, metal=0.85,
                       bump=(40.0, 0.2, 'noise'), rim=viola, rim_str=0.8)
    m_mant = m_mantello("Ade_Mantello_Bordo_Viola", luce=viola)
    m_punte = ST.m_luce("Ade_Punte_Bidente", viola, 70.0, bordo=(0.8, 0.6, 1.0), forza_bordo=100.0)
    m_occhi = ST.m_luce("Ade_Occhi", viola, 60.0)
    m_oro = CL.m_body("Ade_Ricchezze_Oro", (0.9, 0.6, 0.2), rough=0.25, metal=1.0)
    m_gemma = ST.m_vetro("Ade_Gemme", (0.6, 0.2, 1.0), ior=1.6, bordo=viola, forza_bordo=3.0)
    E = [el((0, -0.02, 0.55), 0.1, (1.0, 1.2, 1.0)), el((0, 0.2, 0.45), 0.12, (1.0, 1.4, 0.85)),
         el((0, -0.2, 0.68), 0.075), cap((0, -0.08, 0.6), (0, -0.16, 0.66), 0.06)]
    CL.metaball_mesh("Ade_Corpo", E, m_chit, res=0.014)
    # elmo dell'oscurita' con la cresta e la fessura degli occhi
    ST.guscio("Ade_Elmo", (0, -0.2, 0.7), (0.09, 0.1, 0.1), m_elmo,
              [((0, 0, 0.64), (0, 0, 1)), ((0, -0.28, 0.715), (0, 0.5, 1))], spessore=0.012)
    OC.fin_mesh("Ade_Cresta", [(-0.12, 0.0), (-0.06, 0.06), (0.04, 0.08), (0.12, 0.03), (0.13, 0.0)], 0.012, m_elmo,
                CL.frame_matrix(V((0, -0.19, 0.79)), V((0, 0, 1)), V((1, 0, 0))) @ Matrix.Rotation(pi / 2, 4, 'Z'))
    for sx in (-1, 1):
        s = side_name(sx)
        e = CL.sphere("Ade_Occhio_" + s, (0.035 * sx, -0.285, 0.7), (0.02, 0.008, 0.01), m_occhi, seg=10, rings=5)
        ST.proxy(e, (0.035 * sx, -0.33, 0.7), viola, 0.8)
        CL.sphere("Ade_Paraguancia_" + s, (0.07 * sx, -0.25, 0.64), (0.02, 0.05, 0.045), m_elmo, seg=12, rings=6)
        for k in range(3):
            CL.sphere("Ade_Borchia_%s%d" % (s, k), (0.085 * sx, -0.22 + 0.05 * k, 0.72), 0.01, m_oro, seg=8, rings=4)
    # antenne a bidente: un'asta con due punte uncinate
    base = V((0, -0.22, 0.8))
    fork = V((0, -0.3, 1.08))
    CL.tube("Ade_Bidente_Asta", [base, base.lerp(fork, 0.5) + V((0, 0.01, 0)), fork], [0.012, 0.011, 0.014], m_elmo,
            bevel_res=2)
    CL.tube("Ade_Bidente_Traversa", [fork + V((-0.07, 0, 0.0)), fork + V((0, 0, -0.012)), fork + V((0.07, 0, 0.0))],
            0.012, m_elmo, bevel_res=2)
    for sx in (-1, 1):
        a = fork + V((0.07 * sx, 0, 0.0))
        b = a + V((0.0, -0.02, 0.2))
        CL.tube("Ade_Bidente_Rebbio_" + side_name(sx), [a, a.lerp(b, 0.5), b], [0.011, 0.01, 0.008], m_elmo,
                bevel_res=2)
        p = CL.cone_between("Ade_Bidente_Punta_" + side_name(sx), b, b + V((0, -0.01, 0.09)), 0.02, 0.0, m_punte, 10)
        CL.cone_between("Ade_Bidente_Uncino_" + side_name(sx), b + V((0, 0, 0.02)), b + V((0.035 * sx, -0.005, -0.02)),
                        0.008, 0.0, m_punte, 6)
        ST.proxy(p, b + V((0, -0.05, 0.05)), viola, 3.0)
    # il mantello che si allarga come un telo, con il fermaglio e una gemma
    mantello_mesh("Ade_Mantello", m_mant)
    CL.sphere("Ade_Fermaglio", (0, -0.1, 0.72), (0.035, 0.012, 0.035), m_oro, seg=16, rings=8)
    g = CL.sphere("Ade_Gemma", (0, -0.113, 0.72), (0.02, 0.01, 0.02), m_gemma, seg=12, rings=6)
    ST.proxy(g, (0, -0.2, 0.72), viola, 1.5)
    for i, (x, y) in enumerate(((-0.3, 0.4), (0.32, 0.35), (0.0, 0.55))):
        ST.proxy(g, (x, y, 0.1), viola, 4.0, nome="Ade_Luce_Orlo_%d" % i)
    for i, y in enumerate((-0.08, 0.04, 0.16)):
        for sx in (-1, 1):
            DS.leg("Ade_Zampa_%s%d" % (side_name(sx), i), [V((0.06 * sx, y, 0.5)), V((0.2 * sx, y - 0.03, 0.4)),
                                                          V((0.26 * sx, y - 0.06, 0.0))], [0.013, 0.01, 0.006], m_chit,
                   joint_mat=m_chit)


# ============================================================================
# 04  PERSEFONE MELAGRANA
# ============================================================================

def build_persefone():
    DS.texspace("Persefone")
    m_chit = chitina("Persefone_Chitina_Prugna", (0.12, 0.018, 0.05), rough=0.3, coat=0.6, film=320.0)
    m_oro = CL.m_body("Persefone_Oro", (1.0, 0.72, 0.3), rough=0.25, metal=1.0)
    m_buccia = CL.m_body("Persefone_Buccia_Melagrana", (0.32, 0.018, 0.028), rough=0.45, coat=0.4, sss=0.1,
                         mottle=((0.5, 0.09, 0.05), 6.0), bump=(40.0, 0.25, 'noise'))
    m_bianco = CL.m_body("Persefone_Albedo", (0.9, 0.78, 0.62), rough=0.7, sss=0.4, sss_radius=(1.0, 0.8, 0.6))
    m_seme = m_semi("Persefone_Semi_Rubino")
    m_spiga = CL.m_body("Persefone_Spighe_Grano", (0.85, 0.6, 0.22), rough=0.5, sheen=0.5)
    m_ala = ST.m_ala("Persefone_Ali_Sottili", [(0.0, (1.0, 0.85, 0.8)), (1.0, (0.95, 0.75, 0.85))], alpha=0.2,
                     membrane_str=0.25, vein_ramp=[(0.0, (0.9, 0.5, 0.4)), (1.0, (1.0, 0.8, 0.7))], vein_str=0.6,
                     radial=(6, 0.05), edge=0.04)
    m_petali = CL.m_body("Persefone_Fiori_Petali", (1.0, 0.85, 0.9), rough=0.4, sss=0.5, sss_radius=(1.0, 0.6, 0.7),
                         emit=ST.kelvin(5500), emit_str=1.5)
    m_polline = ST.m_luce("Persefone_Fiori_Centro", (0.6, 1.0, 0.25), 20.0)
    # corpo snello
    E = [el((0, -0.12, 0.62), 0.085, (1.0, 1.3, 1.0)), el((0, -0.3, 0.72), 0.065),
         cap((0, -0.2, 0.66), (0, -0.28, 0.7), 0.05)]
    CL.metaball_mesh("Persefone_Corpo", E, m_chit, res=0.012)
    # addome a melagrana (asse inclinato verso l'alto dietro al torace)
    ax = V((0, 0.8, 0.45)).normalized()
    Pc = V((0, 0.2, 0.62))
    R = 0.2
    prof = []
    for i in range(15):
        t = 0.04 + 0.92 * i / 14
        prof.append((R * sin(pi * t) ** 0.85, -R * 0.95 * cos(pi * t)))

    def facce(co, a, k):
        f = 1.0 - 0.035 * abs(sin(3 * a))
        return V((co.x * f, co.y * f, co.z))

    fr = CL.frame_matrix(Pc, V((0, 0, 1)), ax)
    pom = DS.lathe("Persefone_Melagrana", prof, m_buccia, seg=48, cap_bottom=True, cap_top=True, deform=facce)
    pom.data.materials.append(m_bianco)
    pom.matrix_world = fr
    md = ST.solidifica(pom, 0.018, -1.0)
    md.material_offset = 1
    md.material_offset_rim = 1
    # spaccatura sul fianco che mostra i sei semi
    vd = V((0.78, -0.6, 0.12)).normalized()          # la spaccatura guarda verso l'osservatore
    cut = OC.lumpy("Persefone_Spaccatura", Pc + vd * 0.2, (0.12, 0.1, 0.13), None, seed=4, amount=0.3)
    bo = pom.modifiers.new("Spaccatura", 'BOOLEAN')
    bo.operation = 'DIFFERENCE'
    bo.solver = 'EXACT'
    bo.object = cut
    ST.applica(pom)
    bpy.data.objects.remove(cut)
    ST.separa_materiali(pom)
    rnd = random.Random(6)
    semi = []
    su = vd.cross(V((0, 0, 1))).normalized()
    sw = su.cross(vd).normalized()
    for i in range(6):
        a = (i % 3) - 1
        b = (i // 3) - 0.5
        p = Pc + vd * (0.1 - 0.015 * abs(a)) + su * 0.052 * a + sw * 0.06 * b + V((0, 0, rnd.uniform(-0.008, 0.008)))
        s = CL.sphere("Persefone_Seme_%d" % i, (0, 0, 0), 1.0, m_seme, seg=14, rings=7)
        s.matrix_world = CL.frame_matrix(p, V((0, 0, 1)), vd) @ Matrix.Diagonal((0.03, 0.028, 0.042, 1.0))
        semi.append(s)
    ST.proxy(semi[0], Pc + vd * 0.32, (1.0, 0.1, 0.12), 2.0, nome="Persefone_Luce_Semi")
    ST.proxy(semi[3], Pc + vd * 0.02, (1.0, 0.1, 0.12), 0.8, nome="Persefone_Luce_Dentro")
    # la corona a punta in cima
    tip = fr @ V((0, 0, R * 0.95))
    for i in range(6):
        a = TAU * i / 6
        d = fr.to_3x3() @ V((cos(a) * 0.55, sin(a) * 0.55, 1.0))
        CL.cone_between("Persefone_Corona_%d" % i, tip - ax * 0.02 + (fr.to_3x3() @ V((cos(a), sin(a), 0))) * 0.03,
                        tip + d.normalized() * 0.09, 0.02, 0.0, m_buccia, 8)
    # testa con la coroncina e le antenne a spiga di grano
    for i in range(7):
        a = TAU * i / 7
        CL.cone_between("Persefone_Diadema_%d" % i, (0.05 * cos(a), -0.3 + 0.05 * sin(a), 0.77),
                        (0.05 * cos(a), -0.3 + 0.05 * sin(a), 0.82), 0.012, 0.0, m_oro, 6)
    ring = [V((0.05 * cos(a), -0.3 + 0.05 * sin(a), 0.772)) for a in [TAU * i / 16 for i in range(17)]]
    CL.tube("Persefone_Diadema_Anello", ring, 0.006, m_oro, bevel_res=1)
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Persefone_Occhio_" + s, (0.045 * sx, -0.35, 0.73), 0.024, m_chit, seg=14, rings=7)
        spiga("Persefone_Antenna_Spiga_" + s, (0.02 * sx, -0.36, 0.77), (0.35 * sx, -0.6, 0.75), 0.36, m_spiga,
              m_spiga)
    # ali sottili con i fiorellini alle punte
    fw = [(-12, 0.1), (0, 0.4), (10, 0.62), (20, 0.66), (30, 0.4), (42, 0.1)]
    hw = [(20, 0.1), (32, 0.36), (44, 0.5), (56, 0.44), (68, 0.1)]
    for k, (ctrl, att, elev, sw) in enumerate(((fw, (0.05, -0.14, 0.68), 22, -10), (hw, (0.05, -0.06, 0.66), 12, 6))):
        ws = CL.wing_pair("Persefone_Ala_%d" % k, ctrl, m_ala, att, elev=elev, sweep=sw, roll=8, rings=6, cup=0.02,
                          n=40)
        o = CL.wing_outline(ctrl, 40)
        imax = max(range(len(o)), key=lambda i: math.hypot(*o[i]))
        bpy.context.view_layer.update()
        for w in ws:
            left = w.name.endswith("_L")
            x, y = o[imax]
            p = w.matrix_world @ V((-x if left else x, y, 0.0))
            n = w.matrix_world.to_3x3() @ V((0, 0, 1))
            fiore("Persefone_Fiore_%d%s" % (k, "L" if left else "R"), p, n, 0.035, m_petali, m_polline)
    # tutto il corpo scende di 20 cm (zampe da insetto, non trampoli)
    for ob in list(CL._STATE["coll"].objects):
        if ob.parent is None and not any(c.type == 'CHILD_OF' for c in ob.constraints):
            ob.location.z -= 0.2
    for sx in (-1, 1):
        for i, y in enumerate((-0.2, -0.1, 0.0)):
            DS.leg("Persefone_Zampa_%s%d" % (side_name(sx), i), [V((0.04 * sx, y, 0.38)), V((0.2 * sx, y - 0.03, 0.48)),
                                                                V((0.34 * sx, y - 0.08 + 0.08 * i, 0.0))],
                   [0.011, 0.009, 0.005], m_chit, joint_mat=m_oro)


# ============================================================================
# 05  ALICHINO ARLECCHINO
# ============================================================================

def build_alichino():
    DS.texspace("Alichino")
    colori = [(1.0, 0.05, 0.04), (1.0, 0.8, 0.02), (0.05, 0.9, 0.12), (0.05, 0.25, 1.0)]
    m_rombi = m_arlecchino("Alichino_Elitre_Rombi", colori, 40.0)
    m_pelle = chitina("Alichino_Pelle_Rossa", (0.4, 0.02, 0.015), rough=0.35, coat=0.5)
    m_nero = chitina("Alichino_Maschera_Nera", (0.01, 0.01, 0.012), rough=0.2, coat=0.8)
    m_bianco = ST.m_occhio_bianco("Alichino_Occhi")
    m_pup = CL.m_body("Alichino_Pupille", (0.005, 0.005, 0.005), rough=0.05, coat=1.0)
    m_rifl = ST.m_luce("Alichino_Riflessi", (1, 1, 1), 8.0)
    m_denti = CL.m_body("Alichino_Denti", (0.95, 0.92, 0.85), rough=0.2, coat=0.5)
    m_oro = CL.m_body("Alichino_Campanelli_Oro", (1.0, 0.75, 0.25), rough=0.2, metal=1.0)
    m_pom = [CL.m_body("Alichino_Pompon_%d" % i, c, rough=0.9, sheen=1.0, bump=(150.0, 0.6, 'noise'))
             for i, c in enumerate(((0.9, 0.05, 0.05), (1.0, 0.75, 0.05)))]
    m_gorg = CL.m_body("Alichino_Gorgiera", (0.92, 0.9, 0.86), rough=0.6, sheen=0.5)
    m_coda = ST.m_luce("Alichino_Punta_Coda", (1.0, 0.1, 0.05), 40.0, bordo=(1.0, 0.8, 0.1), forza_bordo=60.0)
    m_esca = [ST.m_luce("Alichino_Esca_Verde", (0.1, 1.0, 0.2), 40.0), ST.m_luce("Alichino_Esca_Blu", (0.1, 0.3, 1.0),
                                                                                40.0)]
    m_calza = [chitina("Alichino_Calze_Rosse", (0.5, 0.02, 0.02)), chitina("Alichino_Calze_Gialle", (0.8, 0.55, 0.02))]
    E = [el((0, 0.0, 0.5), 0.1, (1.0, 1.2, 1.0)), el((0, 0.26, 0.47), 0.13, (1.0, 1.3, 0.85)),
         el((0, -0.2, 0.62), 0.085), cap((0, -0.08, 0.54), (0, -0.16, 0.6), 0.06)]
    CL.metaball_mesh("Alichino_Corpo", E, m_pelle, res=0.013)
    C, R = V((0, 0.24, 0.5)), (0.16, 0.26, 0.14)
    for sx in (-1, 1):
        ST.guscio("Alichino_Elitra_" + side_name(sx), C, R, m_rombi,
                  [((0.01 * sx, 0, 0), (sx, 0, 0)), ((0, 0, 0.47), (0, 0, 1))])
    # maschera nera, occhioni, sorriso furbo
    CL.sphere("Alichino_Maschera", (0, -0.255, 0.65), (0.075, 0.035, 0.03), m_nero, seg=20, rings=10)
    for sx in (-1, 1):
        s = side_name(sx)
        ST.occhio_cartone("Alichino_Occhio_" + s, (0.032 * sx, -0.275, 0.655), (0.3 * sx, -1, 0.05), 0.02, m_bianco,
                          m_pup, m_rifl, guarda=(0.3 * sx, -0.1), pupilla=0.5)
        ST.cono_piatto("Alichino_Orecchio_" + s, (0.07 * sx, -0.2, 0.66), (0.14 * sx, -0.18, 0.72), 0.022, m_pelle,
                       0.4)
        # cornetti con pompon e campanellini
        base = V((0.035 * sx, -0.2, 0.7))
        horn = [base, base + V((0.03 * sx, 0.0, 0.06)), base + V((0.08 * sx, 0.02, 0.1)), base + V((0.12 * sx, 0.0, 0.1))]
        CL.tube("Alichino_Cornetto_" + s, horn, [0.016, 0.012, 0.008, 0.004], m_nero, bevel_res=2)
        CL.sphere("Alichino_Pompon_" + s, horn[-1], 0.028, m_pom[sx > 0], seg=16, rings=8)
        bell = horn[-1] + V((0.0, 0.0, -0.05))
        CL.tube("Alichino_Filo_" + s, [horn[-1], bell + V((0, 0, 0.015))], 0.002, m_nero, bevel_res=0, poly=True)
        CL.sphere("Alichino_Campanello_" + s, bell, (0.016, 0.016, 0.015), m_oro, seg=12, rings=6)
        CL.sphere("Alichino_Campanello_Batacchio_" + s, bell + V((0, 0, -0.013)), 0.005, m_nero, seg=6, rings=3)
    smile = [V((0.05 * (i / 4 - 1), -0.29 + 0.004 * abs(i - 4), 0.615 + 0.012 * ((i / 4 - 1) ** 2))) for i in range(9)]
    CL.tube("Alichino_Sorriso", smile, 0.006, m_nero, bevel_res=1)
    for i in (2, 3, 5, 6):
        CL.cone_between("Alichino_Dente_%d" % i, smile[i] + V((0, -0.002, 0.0)), smile[i] + V((0, -0.004, -0.012)),
                        0.005, 0.0, m_denti, 6)
    # gorgiera pieghettata
    def pieghe(co, a, k):
        return V((co.x, co.y, co.z + 0.012 * sin(22 * a)))

    gorg = DS.lathe("Alichino_Gorgiera", [(0.05, 0.0), (0.13, 0.0)], m_gorg, seg=88, cap_bottom=False, deform=pieghe)
    gorg.location = (0, -0.12, 0.58)
    gorg.rotation_euler = (radians(53), 0, 0)
    ST.solidifica(gorg, 0.008, 0.0)
    # coda a punta di freccia ("cattiva coda")
    tail = DS.spline([V((0, 0.5, 0.45)), V((0, 0.7, 0.42)), V((0.05, 0.84, 0.55)), V((0.0, 0.88, 0.72)),
                      V((-0.06, 0.82, 0.82))], 16)
    CL.tube("Alichino_Coda", tail, [0.02 - 0.001 * i for i in range(16)], m_pelle, bevel_res=2)
    d = (tail[-1] - tail[-2]).normalized()
    arrow = OC.fin_mesh("Alichino_Freccia", [(0.0, -0.012), (0.0, -0.05), (0.09, 0.0), (0.0, 0.05), (0.0, 0.012)], 0.012,
                        m_coda, CL.frame_matrix(tail[-1], d.cross(V((1, 0, 0))), V((1, 0, 0))) @
                        Matrix.Rotation(-pi / 2, 4, 'Z'))
    ST.proxy(arrow, tail[-1] + d * 0.08, (1.0, 0.25, 0.05), 3.0)
    # due false luci-esca che galleggiano vicino (i suoi scherzi)
    for i, p in enumerate(((-0.5, -0.3, 0.75), (0.55, 0.1, 0.9))):
        o = CL.sphere("Alichino_Esca_%d" % i, p, 0.035, m_esca[i], seg=14, rings=7)
        ST.proxy(o, V(p) + V((0, 0, 0.05)), m_esca[i]["rbx_color"], 3.0)
    for k in range(3):
        ST.proxy(arrow, (0.0, 0.1 + 0.15 * k, 0.8), colori[k], 2.5, nome="Alichino_Luce_Rombi_%d" % k)
    # zampe con le calze a righe e le scarpette a punta
    for i, y in enumerate((-0.08, 0.06, 0.2)):
        for sx in (-1, 1):
            a = V((0.06 * sx, y, 0.46))
            k = V((0.2 * sx, y - 0.02, 0.36))
            f = V((0.26 * sx, y - 0.04, 0.02))
            for j, (p, q) in enumerate(((a, a.lerp(k, 0.5)), (a.lerp(k, 0.5), k), (k, k.lerp(f, 0.5)),
                                        (k.lerp(f, 0.5), f))):
                CL.tube("Alichino_Calza_%s%d_%d" % (side_name(sx), i, j), [p, q], [0.012 - 0.001 * j, 0.011 - 0.001 * j],
                        m_calza[j % 2], bevel_res=1)
            CL.tube("Alichino_Scarpetta_%s%d" % (side_name(sx), i), [f, f + V((0.0, -0.05, 0.0)),
                                                                     f + V((0.0, -0.075, 0.03))], [0.014, 0.01, 0.003],
                    m_nero, bevel_res=1)


# ============================================================================
# 06  GHIACCIOLO, IL RE DI GHIACCIO (COCITO)
# ============================================================================

def faccia_lucifero(m_pelle, m_corna):
    """Maschera di una faccia (costruita all'origine, verso -Y): arcata,
    zigomi, naso, bocca severa e due cornetti."""
    E = [el((0, -0.02, 0.0), 0.07, (1.1, 0.5, 1.2)), el((0, -0.06, 0.03), 0.03, (2.0, 0.6, 0.5)),
         el((0, -0.075, -0.005), 0.022, (0.6, 0.9, 1.2)), el((0, -0.055, -0.06), 0.03, (1.3, 0.6, 0.6))]
    for sx in (-1, 1):
        E.append(el((0.045 * sx, -0.045, -0.015), 0.025, (1.0, 0.6, 0.8)))
    obs = [CL.metaball_mesh("Faccia_Maschera", E, m_pelle, res=0.009)]
    obs.append(CL.tube("Faccia_Bocca", [V((-0.025, -0.078, -0.052)), V((0, -0.08, -0.058)),
                                        V((0.025, -0.078, -0.052))], 0.004, m_corna, bevel_res=1))
    for sx in (-1, 1):
        obs.append(CL.sphere("Faccia_Occhio_" + side_name(sx), (0.028 * sx, -0.07, 0.012), (0.012, 0.006, 0.007),
                             m_corna, seg=10, rings=5))
        obs.append(CL.tube("Faccia_Corno_" + side_name(sx), [V((0.04 * sx, -0.03, 0.07)), V((0.06 * sx, -0.03, 0.11)),
                                                             V((0.055 * sx, -0.01, 0.15))], [0.012, 0.008, 0.001],
                           m_corna, bevel_res=1))
    return obs


def build_ghiacciolo():
    DS.texspace("Ghiacciolo")
    ciano = 12000
    m_ice = m_ghiaccio_cocito("Ghiacciolo_Ghiaccio_Cocito")
    m_chit = chitina("Ghiacciolo_Chitina_Brinata", (0.025, 0.028, 0.04), rough=0.35, coat=0.5, sheen=0.6,
                     sheen_tint=(0.7, 0.9, 1.0))
    m_facce = [chitina("Ghiacciolo_Faccia_Rossa", (0.5, 0.03, 0.02)),
               chitina("Ghiacciolo_Faccia_Gialla", (0.85, 0.8, 0.55)),
               chitina("Ghiacciolo_Faccia_Nera", (0.012, 0.01, 0.014))]
    m_corna = CL.m_body("Ghiacciolo_Corna", (0.03, 0.03, 0.035), rough=0.3, coat=0.6)
    m_puntini = [ST.m_luce("Ghiacciolo_Puntino_Rosso", 2200, 60.0), ST.m_luce("Ghiacciolo_Puntino_Giallo", 4500, 60.0),
                 ST.m_luce("Ghiacciolo_Puntino_Viola", (0.5, 0.1, 1.0), 60.0)]
    m_cuore = ST.m_luce("Ghiacciolo_Cuore", ciano, 60.0, bordo=(0.9, 1.0, 1.0), forza_bordo=90.0)
    m_mem = ST.m_chitina("Ghiacciolo_Membrana_Ali", (0.05, 0.06, 0.08), rough=0.5, coat=0.3, sss=0.3,
                         sss_radius=(0.4, 0.8, 1.0))
    m_mem["rbx_thick"] = 1
    m_filo = ST.m_luce("Ghiacciolo_Brina_Ali", (0.6, 0.9, 1.0), 2.0)
    # blocco di ghiaccio: la meta' inferiore del corpo resta dentro
    blocco_ghiaccio("Ghiacciolo_Blocco_Ghiaccio", (0, 0.05, 0.28), (0.95, 0.8, 0.58), m_ice)
    E = [el((0, 0.05, 0.3), 0.14, (1.0, 1.3, 0.9)), el((0, -0.05, 0.62), 0.14, (1.2, 0.9, 1.1)),
         el((0, -0.02, 0.78), 0.1, (1.5, 0.8, 0.6)), cap((0, -0.04, 0.8), (0, -0.05, 0.9), 0.06)]
    for sx in (-1, 1):
        E += [cap((0.12 * sx, 0.1, 0.25), (0.25 * sx, -0.05, 0.12), 0.035),
              cap((0.2 * sx, -0.02, 0.76), (0.3 * sx, -0.18, 0.62), 0.045),
              cap((0.3 * sx, -0.18, 0.62), (0.22 * sx, -0.32, 0.6), 0.038)]
    CL.metaball_mesh("Ghiacciolo_Corpo", E, m_chit, res=0.014)
    # la testa con le tre facce (una davanti, due ai lati)
    CL.sphere("Ghiacciolo_Testa", (0, -0.05, 1.0), (0.1, 0.1, 0.11), m_chit, seg=24, rings=12)
    master = faccia_lucifero(m_facce[0], m_corna)
    dirs = [V((0, -1, 0)), V((-1, 0.15, 0)), V((1, 0.15, 0))]
    mats = [ST.frame(V((0, -0.05, 1.0)) + d * 0.085, d) for d in dirs]
    gruppi = ST.istanze(master, mats, "Ghiacciolo_Faccia")
    for i, grp in enumerate(gruppi):
        ST.materiale_oggetto(grp[0], m_facce[i])
        p = V((0, -0.05, 1.0)) + dirs[i] * 0.16 + V((0, 0, 0.035))
        dot = CL.sphere("Ghiacciolo_Puntino_%d" % i, p, 0.01, m_puntini[i], seg=10, rings=5)
        ST.proxy(dot, p + dirs[i] * 0.05, m_puntini[i]["rbx_color"], 1.2)
    CL.tube("Ghiacciolo_Filo_Viola", [V((0.2, -0.05, 1.06)), V((0.21, -0.04, 1.0)), V((0.2, -0.05, 0.94))], 0.002,
            m_puntini[2], bevel_res=0)
    # il cuore che brilla nel ghiaccio
    heart = CL.sphere("Ghiacciolo_Cuore", (0, -0.14, 0.55), (0.06, 0.05, 0.065), m_cuore, seg=16, rings=8)
    CL.no_shadow(heart)
    ST.proxy(heart, (0, -0.3, 0.55), ciano, 15.0, nome="Ghiacciolo_Luce_Cuore")
    ST.proxy(heart, (0, 0.05, 0.3), ciano, 10.0, nome="Ghiacciolo_Luce_Ghiaccio")
    # sei ali da pipistrello (tre coppie), con una rete di brina (Wireframe)
    specs = [((0.12, 0.08, 0.86), (0.36, 0.2, 1.12), (0.5, 0.18, 1.35), [(0.75, 0.05, 1.6), (0.95, 0.3, 1.45),
                                                                          (0.85, 0.5, 1.2), (0.55, 0.45, 1.0)],
              (0.1, 0.18, 0.78)),
             ((0.14, 0.12, 0.76), (0.42, 0.28, 0.82), (0.62, 0.3, 0.86), [(0.95, 0.2, 0.95), (1.08, 0.48, 0.78),
                                                                          (0.92, 0.68, 0.62), (0.6, 0.58, 0.6)],
              (0.12, 0.2, 0.66)),
             ((0.13, 0.14, 0.66), (0.38, 0.32, 0.56), (0.55, 0.38, 0.45), [(0.85, 0.36, 0.42), (0.92, 0.6, 0.3),
                                                                          (0.72, 0.75, 0.25), (0.45, 0.62, 0.35)],
              (0.1, 0.2, 0.58))]
    for k, (S, Eb, W, tips, body) in enumerate(specs):
        mem, ossa = ST.ala_membrana("Ghiacciolo_Ala_%d" % k, S, Eb, W, tips, body, m_mem, m_chit, sacca=0.18,
                                    gonfia=0.04, righe=5, colonne=4, r_osso=0.014, artiglio=m_corna)
        rete = CL.mesh_object("Ghiacciolo_Brina_%d_R" % k, _copia_bm(mem), m_filo, smooth=False)
        wf = rete.modifiers.new("Rete_Brina", 'WIREFRAME')
        wf.thickness = 0.004
        rete["rbx_drop"] = 1
        ST.specchia_x([mem, rete] + ossa)
    for o in bpy.data.objects:
        if o.name.startswith("Ghiacciolo_Brina_") and o.name.endswith("_L"):
            o["rbx_drop"] = 1


def _copia_bm(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    return bm


# ============================================================================
# 07  FLEGETONTE SCINTILLA
# ============================================================================

def build_flegetonte():
    DS.texspace("Flegetonte")
    m_roccia = DS.m_lava("Flegetonte_Chitina_Vulcanica", strength=6.0, scale=9.0, crack=0.05)
    m_vetro = ST.m_vetro_sottile("Flegetonte_Guscio_Vetro", (1.0, 0.85, 0.7), bordo=1700, forza_bordo=1.5)
    m_fl = m_flusso("Flegetonte_Fuoco_Che_Scorre", 14.0)
    m_blob = ST.m_luce("Flegetonte_Bolle_Lava", 3800, 25.0, bordo=1700, forza_bordo=18.0)
    m_goccia = ST.m_luce("Flegetonte_Gocce_Lava", 1700, 25.0, bordo=3800, forza_bordo=35.0)
    m_ala = ST.m_ala("Flegetonte_Ali_Fiamma", [(0.0, ST.kelvin(3800)), (0.45, ST.kelvin(1900)), (1.0, (1.0, 0.1, 0.0))],
                     alpha=0.2, membrane_str=2.5, vein_ramp=[(0.0, ST.kelvin(4200)), (1.0, ST.kelvin(1700))],
                     vein_str=6.0, radial=(7, 0.08), edge=0.03, distort=0.4, film=0.0)
    m_zampe = chitina("Flegetonte_Zampe", (0.03, 0.02, 0.018))
    E = [el((0, -0.12, 0.56), 0.09, (1.0, 1.2, 1.0)), el((0, -0.32, 0.62), 0.07),
         cap((0, -0.2, 0.58), (0, -0.28, 0.61), 0.055)]
    CL.metaball_mesh("Flegetonte_Torace", E, m_roccia, res=0.012)
    # addome a goccia trasparente come una lampada lava
    ax = V((0, 1.0, -0.12)).normalized()
    P0 = V((0, -0.02, 0.56))
    prof = [(0.002, 0.0), (0.06, 0.012), (0.1, 0.04), (0.14, 0.1), (0.165, 0.18), (0.165, 0.26), (0.14, 0.34),
            (0.1, 0.41), (0.05, 0.47), (0.01, 0.5)]
    fr = CL.frame_matrix(P0, V((1, 0, 0)), ax)
    shell = DS.lathe("Flegetonte_Addome_Vetro", prof, m_vetro, seg=40, cap_bottom=False, cap_top=True)
    shell.matrix_world = fr
    CL.add_subsurf(shell, 1, 2)
    CL.no_shadow(shell)
    inner = DS.lathe("Flegetonte_Flusso", [(r * 0.82, z * 0.94 + 0.015) for r, z in prof], m_fl, seg=32,
                     cap_bottom=False, cap_top=True)
    inner.matrix_world = fr
    rnd = random.Random(7)
    E = []
    for i in range(7):
        z = 0.08 + 0.36 * i / 6
        E.append(bl((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), z), rnd.uniform(0.03, 0.05)))
    blobs = CL.metaball_mesh("Flegetonte_Bolle", E, m_blob, res=0.01)
    blobs.matrix_world = fr
    ST.proxy(inner, fr @ V((0, 0, 0.25)), 1700, 10.0, nome="Flegetonte_Luce_Addome")
    ST.proxy(inner, fr @ V((0, 0, 0.1)) + V((0, 0, -0.3)), 1900, 10.0, nome="Flegetonte_Luce_Terra")
    # gocce di lava che cadono dal ventre
    for i, (x, y, z) in enumerate(((0.02, 0.1, 0.36), (-0.04, 0.22, 0.28), (0.05, 0.3, 0.18), (-0.02, 0.16, 0.08),
                                   (0.01, 0.34, 0.33))):
        g = CL.metaball_mesh("Flegetonte_Goccia_%d" % i, [bl((x, y, z), 0.022), cap((x, y, z), (x, y, z + 0.05), 0.01)],
                             m_goccia, res=0.006)
        CL.no_shadow(g)
    # ali a lingue di fiamma
    fw = [(-12, 0.14), (2, 0.5), (16, 0.7), (32, 0.62), (48, 0.5), (64, 0.3), (80, 0.14)]
    hw = [(35, 0.12), (50, 0.4), (66, 0.52), (82, 0.44), (100, 0.14)]
    CL.wing_pair("Flegetonte_Ala_Anteriore", fw, m_ala, (0.05, -0.14, 0.62), elev=28, sweep=-6, roll=6, rings=8,
                 cup=0.03, n=64, scallop=(0.45, 4))
    CL.wing_pair("Flegetonte_Ala_Posteriore", hw, m_ala, (0.05, -0.06, 0.6), elev=16, sweep=10, roll=4, rings=6,
                 cup=0.02, n=48, scallop=(0.4, 3))
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Flegetonte_Occhio_" + s, (0.045 * sx, -0.37, 0.64), 0.025, m_goccia, seg=14, rings=7)
        a = V((0.02 * sx, -0.38, 0.67))
        CL.tube("Flegetonte_Antenna_" + s, [a, a + V((0.06 * sx, -0.1, 0.12)), a + V((0.14 * sx, -0.12, 0.2))],
                [0.006, 0.004, 0.002], m_zampe, bevel_res=1)
        for i, y in enumerate((-0.2, -0.12, -0.04)):
            DS.leg("Flegetonte_Zampa_%s%d" % (s, i), [V((0.04 * sx, y, 0.52)), V((0.17 * sx, y - 0.02, 0.44)),
                                                     V((0.22 * sx, y + 0.02 * i, 0.0))], [0.011, 0.009, 0.005], m_zampe,
                   joint_mat=m_goccia, joint_r=0.012)


# ============================================================================
# 08  TUNG TUNG TUNG SAHUR INFERNALE
# ============================================================================

def build_tungtung():
    DS.texspace("TungSahur")
    rosso = (1.0, 0.05, 0.0)
    m_tr = m_tronco("TungSahur_Corteccia_Lava", 1600, 40.0)
    m_bianco = ST.m_occhio_bianco("TungSahur_Occhi_Bianchi")
    m_iride = ST.m_luce("TungSahur_Iridi_Rosse", rosso, 60.0)
    m_pup = CL.m_body("TungSahur_Pupille", (0.004, 0.004, 0.004), rough=0.05, coat=1.0)
    m_rifl = ST.m_luce("TungSahur_Riflessi", (1, 1, 1), 10.0)
    m_nero = CL.m_body("TungSahur_Sopracciglia", (0.005, 0.004, 0.004), rough=0.6)
    m_vena = ST.m_luce("TungSahur_Vena_Rabbia", rosso, 80.0)
    m_bocca = CL.m_body("TungSahur_Bocca", (0.05, 0.0, 0.0), rough=0.4)
    m_denti = CL.m_body("TungSahur_Denti", (0.95, 0.92, 0.85), rough=0.25, coat=0.4)
    m_bat = m_mazza("TungSahur_Mazza_Rovente", 50.0)
    m_rami = CL.m_bark("TungSahur_Rami", (0.04, 0.025, 0.018), (0.012, 0.008, 0.006))
    m_rossa = CL.m_body("TungSahur_Sneakers_Rosse", (0.75, 0.02, 0.02), rough=0.35, coat=0.4)
    m_suola = CL.m_body("TungSahur_Sneakers_Suola", (0.92, 0.9, 0.86), rough=0.5)
    m_lacci = CL.m_body("TungSahur_Sneakers_Lacci", (0.95, 0.95, 0.95), rough=0.6)
    m_acc = CL.m_body("TungSahur_Sneakers_Striscia", (0.02, 0.02, 0.02), rough=0.4)
    m_corna = chitina("TungSahur_Cornetti", (0.25, 0.02, 0.01), rough=0.3)
    m_ala = ST.m_ala("TungSahur_Alucce", [(0.0, (1.0, 0.5, 0.3)), (1.0, (1.0, 0.3, 0.2))], alpha=0.2, membrane_str=0.5,
                     vein_ramp=[(0.0, (1.0, 0.3, 0.1)), (1.0, (1.0, 0.5, 0.2))], vein_str=2.0, radial=(5, 0.08))
    # il tronco: cilindro deformato (corteccia a coste) e suddiviso
    Rt, z0, z1 = 0.26, 0.3, 1.32
    bm = bmesh.new()
    seg, rows = CL.det(40, 12), CL.det(18, 6)
    rings = []
    for j in range(rows + 1):
        t = j / rows
        z = z0 + (z1 - z0) * t
        row = []
        for i in range(seg):
            a = TAU * i / seg
            r = Rt * (1.0 + 0.045 * sin(16 * a + 3 * t) + 0.05 * mnoise.noise(V((cos(a) * 2, sin(a) * 2, z * 3))))
            r *= 1.0 - 0.06 * t
            row.append(bm.verts.new((r * cos(a), r * sin(a), z)))
        rings.append(row)
    for j in range(rows):
        for i in range(seg):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % seg], rings[j + 1][(i + 1) % seg], rings[j + 1][i]))
    for row, top in ((rings[0], False), (rings[-1], True)):
        c = bm.verts.new((0, 0, row[0].co.z + (0.02 if top else -0.01)))
        for i in range(seg):
            f = (row[i], row[(i + 1) % seg], c) if top else (row[(i + 1) % seg], row[i], c)
            bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    log = CL.mesh_object("TungSahur_Tronco", bm, m_tr)
    CL.add_subsurf(log, 1, 1)
    ST.proxy(log, (0, -0.4, 0.8), 1600, 20.0, nome="TungSahur_Luce_Crepe")
    ST.proxy(log, (0, 0.4, 0.9), 1600, 12.0, nome="TungSahur_Luce_Schiena")
    # faccia da cartone arrabbiata
    ez = 1.04
    for sx in (-1, 1):
        s = side_name(sx)
        n = V((0.32 * sx, -1.0, 0.05)).normalized()
        c = V((0.1 * sx, -0.24, ez))
        eye = ST.occhio_cartone("TungSahur_Occhio_" + s, c, n, 0.085, m_bianco, m_pup, m_rifl, guarda=(-0.3 * sx, -0.2),
                                pupilla=0.38, piatto=0.7)
        ir = CL.sphere("TungSahur_Iride_" + s, (0, 0, 0), 1.0, m_iride, seg=16, rings=8)
        pc = eye[1].matrix_world.translation - n * 0.004
        ir.matrix_world = CL.frame_matrix(pc, V((0, 0, 1)), n) @ Matrix.Diagonal((0.05, 0.05, 0.01, 1.0))
        ST.proxy(ir, pc + n * 0.05, rosso, 1.0)
        ST.sopracciglio("TungSahur_Sopracciglio_" + s, c + V((0, 0, 0.05)), n, 0.2, 28.0, 0.022, m_nero, lato=sx,
                        arco=0.1, alza=0.06)
        CL.cone_between("TungSahur_Cornetto_" + s, (0.12 * sx, -0.08, z1 - 0.02), (0.16 * sx, -0.12, z1 + 0.12), 0.035,
                        0.0, m_corna, 10)
    # vena pulsante sulla fronte (il segno della rabbia)
    vc = V((0.12, -0.225, 1.2))
    for k in range(4):
        a = pi / 4 + k * pi / 2
        d = V((cos(a), -0.2, sin(a))) * 0.03
        CL.tube("TungSahur_Vena_%d" % k, [vc + d * 0.4, vc + d + V((0, -0.005, 0)), vc + d * 1.4 + V((0.01 * cos(a + 1),
                                                                                                    0, 0.01 * sin(a + 1)))],
                0.007, m_vena, bevel_res=1)
    # bocca arrabbiata con i denti
    mouth = CL.sphere("TungSahur_Bocca", (0, -0.245, 0.85), (0.1, 0.03, 0.045), m_bocca, seg=20, rings=10)
    del mouth
    for i in range(5):
        x = -0.06 + 0.03 * i
        CL.cone_between("TungSahur_Dente_%d" % i, (x, -0.27, 0.885), (x, -0.275, 0.855), 0.011, 0.0, m_denti, 6)
    # braccia di ramo: una alza la mazza rovente
    shR = V((0.24, -0.05, 0.9))
    hand = V((0.5, -0.12, 1.25))
    CL.tube("TungSahur_Braccio_R", [shR, V((0.42, -0.1, 0.95)), hand], [0.035, 0.03, 0.028], m_rami, bevel_res=2)
    CL.sphere("TungSahur_Mano_R", hand, 0.05, m_rami, seg=14, rings=7)
    shL = V((-0.24, -0.05, 0.85))
    CL.tube("TungSahur_Braccio_L", [shL, V((-0.4, -0.12, 0.72)), V((-0.42, -0.2, 0.6))], [0.035, 0.03, 0.028], m_rami,
            bevel_res=2)
    CL.sphere("TungSahur_Mano_L", (-0.42, -0.21, 0.58), 0.05, m_rami, seg=14, rings=7)
    bd = V((0.22, 0.05, 1.0)).normalized()
    bat = DS.lathe("TungSahur_Mazza", [(0.002, -0.14), (0.05, -0.13), (0.04, -0.1), (0.025, -0.08), (0.028, 0.1),
                                       (0.05, 0.3), (0.07, 0.48), (0.072, 0.58), (0.05, 0.62), (0.002, 0.63)], m_bat,
                   seg=24, cap_bottom=False, cap_top=False)
    bat.matrix_world = CL.frame_matrix(hand, V((1, 0, 0)), bd)
    ST.proxy(bat, hand + bd * 0.45 + V((0, -0.1, 0)), (1.0, 0.25, 0.0), 12.0, nome="TungSahur_Luce_Mazza")
    # gambe corte con le sneakers rosse
    master = ST.sneaker("TungSahur_Scarpa", 0.3, m_rossa, m_suola, m_lacci, m_acc)
    for sx in (-1, 1):
        s = side_name(sx)
        top = V((0.12 * sx, 0.0, 0.34))
        foot = V((0.14 * sx, -0.04, 0.09))
        CL.tube("TungSahur_Gamba_" + s, [top, top.lerp(foot, 0.5) + V((0.02 * sx, 0, 0)), foot], [0.04, 0.035, 0.032],
                m_rami, bevel_res=2)
    ST.istanze(master, [ST.frame((0.14, -0.06, 0.0), (0.12, -1, 0)), ST.frame((-0.14, -0.06, 0.0), (-0.12, -1, 0))],
               "TungSahur_Scarpa")
    # alucce da lucciola sul dorso, quasi nascoste
    CL.wing_pair("TungSahur_Aluccia", [(-10, 0.05), (0, 0.14), (15, 0.17), (30, 0.12), (40, 0.04)], m_ala,
                 (0.06, 0.24, 1.05), elev=30, sweep=110, roll=20, rings=4, n=24)


# ============================================================================
# SCENE DELL'INFERNO
# ============================================================================

def m_roccia_scena(nome="Roccia_Infernale"):
    return CL.m_body(nome, (0.035, 0.02, 0.018), rough=0.9, bump=(8.0, 0.8, 'noise'), mottle=((0.012, 0.008, 0.007),
                                                                                                3.0))


def scena_gruppo(which):
    brace = which in ("tutte", "cerbero", "flegetonte", "tungtung")
    if which == "ade":
        ST.mondo((0.0, 0.0, 0.0), (0.004, 0.002, 0.008), 1.0, nome="Buio_Ade")
        ST.pavimento("Terreno_Nero", (0.006, 0.005, 0.008), (0.015, 0.012, 0.02), scala=0.6, rough=(0.5, 0.8))
    elif which == "ghiacciolo":
        ST.mondo((0.002, 0.006, 0.015), (0.01, 0.03, 0.06), 1.0, nome="Cielo_Cocito")
        ST.pavimento("Lago_Cocito", (0.25, 0.35, 0.45), (0.5, 0.65, 0.8), scala=0.5, rough=(0.08, 0.25), bump=0.15)
    else:
        ST.mondo((0.012, 0.002, 0.001), (0.05, 0.01, 0.004), 1.0, nome="Cielo_Inferno")
        ST.pavimento("Terreno_Inferno", (0.012, 0.007, 0.006), (0.04, 0.018, 0.012), scala=0.6, rough=(0.7, 0.95),
                     lucido=(1500, 0.7, 0.9) if brace else None)
    if brace:
        ST.nebbia("Foschia_Calore", (0, 3, 1.6), (30, 30, 3.2), (1.0, 0.5, 0.3), 0.012)
    if which == "ghiacciolo":
        ST.luci_studio(which, chiave=(0.8, 0.9, 1.0), contro=(0.4, 0.75, 1.0), riempimento=(0.6, 0.7, 1.0))
    else:
        ST.luci_studio(which, chiave=(1.0, 0.85, 0.78), contro=(1.0, 0.3, 0.1), riempimento=(0.6, 0.65, 1.0))


def scena_cerbero():
    m = m_roccia_scena("Roccia_Portale")
    for i in range(9):
        a = pi * i / 8
        DS.rock("Portale_Roccia_%d" % i, (1.45 * cos(a), 1.3, 1.45 * sin(a) + 0.1), (0.32, 0.3, 0.32), m, seed=i + 1)
    ST.luce("Luce_Arancio_Dal_Basso", 'AREA', (0, -0.3, 0.03), 120.0, 2000, 1.5, rot=(0, 0, 0))
    ST.nebbia("Foschia_Leggera", (0, 0.5, 1.0), (5, 5, 2), (1.0, 0.6, 0.4), 0.05)


def scena_caronte():
    m = CL.new_material("Stige_Acqua")
    nb = CL.NodeBuilder(m)
    pb = nb.principled(base=(0.01, 0.025, 0.02), rough=0.16, spec=0.6, coat=0.6, coat_rough=0.03)
    nb.output(pb.outputs[0])
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    w = CL.mesh_object("Stige", bm, m, smooth=True)
    w.location = (0, 0, 0.2)
    try:
        md = w.modifiers.new("Onde_Ocean", 'OCEAN')
        md.geometry_mode = 'GENERATE'
        md.size = 1.0
        md.spatial_size = 12
        md.repeat_x = md.repeat_y = 2
        md.resolution = 10
        md.wave_scale = 0.35
        md.choppiness = 0.8
    except Exception as exc:
        print("[creature] Ocean modifier non disponibile:", exc)
        w.scale = (12, 12, 1)
    ST.nebbia("Nebbia_Stige", (0, 1, 1.0), (8, 8, 2), (0.55, 0.65, 0.55), 0.09)


def scena_ade():
    ST.luce("Rim_Viola", 'AREA', (0.5, 1.8, 1.4), 120.0, (0.5, 0.15, 1.0), 2.0, rot=(-70, 0, 180))
    ST.nebbia("Nebbia_Bassa", (0, 0.5, 0.2), (6, 6, 0.4), (0.7, 0.6, 1.0), 0.4)


def scena_persefone():
    ST.luce("Luce_Rossa_Basso", 'AREA', (0, -0.8, 0.05), 90.0, (1.0, 0.1, 0.05), 3.0, rot=(-20, 0, 0))
    ST.luce("Luce_Verde_Alto", 'AREA', (0, -0.3, 2.2), 90.0, (0.3, 1.0, 0.3), 3.0, rot=(0, 0, 0))


def scena_alichino():
    m = CL.new_material("Tendone_Circo")
    nb = CL.NodeBuilder(m)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    ang = nb.math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    st = nb.math('FRACT', nb.math('MULTIPLY', ang, 14.0 / pi))
    col = nb.ramp(st, [(0.0, (0.35, 0.01, 0.01)), (0.5, (0.02, 0.01, 0.01))], interp='CONSTANT')
    nb.output(nb.principled(base=col, rough=0.8, sheen=0.5).outputs[0])
    tent = DS.lathe("Tendone", [(5.0, 0.0), (5.0, 3.0), (3.0, 4.2), (0.05, 5.0)], m, seg=72, cap_bottom=False)
    tent.location = (0, 1.0, 0)
    ST.luce("Luce_Rossa_Laterale", 'SPOT', (1.8, -0.8, 1.6), 400.0, (1.0, 0.1, 0.05), 0.2, rot=(60, 0, 60), spot=45)


def scena_ghiacciolo():
    ST.nebbia("Nebbia_Blu", (0, 0.5, 1.0), (6, 6, 2), (0.4, 0.7, 1.0), 0.06)
    ST.compositor(ST.SETUP["inferno"]["bloom"], 7, (2, 0.0, 0.3), ST.SETUP["inferno"]["vignetta"])


def scena_flegetonte():
    m = m_roccia_scena("Roccia_Caverna")
    for i in range(12):
        a = pi * (0.1 + 0.8 * i / 11)
        DS.rock("Caverna_Roccia_%d" % i, (2.2 * cos(a), 1.2 + 1.2 * sin(a), 0.3 + 0.5 * (i % 3)),
                (0.6, 0.5, 0.7 + 0.2 * (i % 2)), m, seed=i + 3)
    ST.nebbia("Calore_Arancio", (0, 0.5, 1.0), (6, 6, 2), (1.0, 0.5, 0.2), 0.03)
    ST.compositor(ST.SETUP["inferno"]["bloom"], 7, (4, 15.0, 0.2), ST.SETUP["inferno"]["vignetta"])


def scena_tungtung():
    ST.nebbia("Nebbia_Rossa", (0, 0.5, 1.2), (7, 7, 2.4), (1.0, 0.2, 0.1), 0.05)
    m = ST.m_luce("Braci", 1400, 30.0)
    em = CL.sphere("Braci_Emettitore", (0, 0.6, 1.2), (2.2, 1.6, 1.1), None, seg=12, rings=6)
    grain = CL.sphere("Brace", (0, 0, -3), 0.008, m, seg=6, rings=3)
    CL.particle_scatter(em, grain, 300, size=1.0, size_random=0.8, seed=9)
    ST.compositor(0.7, 8, None, ST.SETUP["inferno"]["vignetta"])


CREATURE_INFERNO = {
    #  chiave         (collezione,                      funzione,          camera: target, dist, elev, azim, lente)
    "cerbero":    ("I01_Cerbero-Piccino",             build_cerbero,     ((0, -0.15, 0.62), 3.4, 12, 30, 50)),
    "caronte":    ("I02_Caronte-Barchetta",           build_caronte,     ((0, -0.15, 0.55), 3.4, 12, 40, 50)),
    "ade":        ("I03_Ade-Ombretta",                build_ade,         ((0, 0.0, 0.72), 3.8, 12, 30, 50)),
    "persefone":  ("I04_Persefone-Melagrana",         build_persefone,   ((0, -0.05, 0.45), 2.8, 12, 45, 50)),
    "alichino":   ("I05_Alichino-Arlecchino",         build_alichino,    ((0, 0.05, 0.6), 2.9, 16, 35, 50)),
    "ghiacciolo": ("I06_Ghiacciolo-Re-di-Ghiaccio",   build_ghiacciolo,  ((0, 0.05, 0.75), 4.0, 12, 25, 50)),
    "flegetonte": ("I07_Flegetonte-Scintilla",        build_flegetonte,  ((0, 0.0, 0.5), 2.8, 14, 40, 50)),
    "tungtung":   ("I08_Tung-Tung-Tung-Sahur",        build_tungtung,    ((0.08, -0.05, 0.95), 4.4, 8, 22, 50)),
}

DISPOSIZIONE_INFERNO = {
    "ghiacciolo": (-4.8, 4.8, 15),
    "caronte":    (-1.6, 4.6, 20),
    "ade":        (1.5, 4.6, -10),
    "tungtung":   (4.6, 4.8, -20),
    "cerbero":    (-3.8, 0.8, 25),
    "persefone":  (-1.2, 0.4, 30),
    "alichino":   (1.2, 0.4, -20),
    "flegetonte": (3.8, 0.6, -35),
}

SCENE_INFERNO = {"cerbero": scena_cerbero, "caronte": scena_caronte, "ade": scena_ade, "persefone": scena_persefone,
                 "alichino": scena_alichino, "ghiacciolo": scena_ghiacciolo, "flegetonte": scena_flegetonte,
                 "tungtung": scena_tungtung}


def build(which=None, engine=None, clean=None):
    ST.build_serie(CREATURE_INFERNO, DISPOSIZIONE_INFERNO, which or CREATURA, scena_gruppo, SCENE_INFERNO,
                   ((0, 2.4, 1.0), 12.5, 12, 0, 32), ST.SETUP["inferno"], engine or MOTORE, clean)


def main():
    ST.main(build)


if __name__ == "__main__":
    main()
