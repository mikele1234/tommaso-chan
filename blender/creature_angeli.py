# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE: GLI ANGELI - settima serie per Blender (modelli statici).

    01  FIAMMELLA, IL SERAFINO         (sei ali, addome bianco-oro 5500 K)
    02  QUATTRO MUSETTI, IL CHERUBINO  (quattro facce sul pronoto: uomo, leone, bue, aquila)
    03  RUOTINA, L'OFANIM              (ruote dentro ruote piene di occhi)
    04  SCUDO STELLATO, MICHELE        (placche d'armatura, scudo a stella, bilancia)
    05  TROMBETTINA, GABRIELE          (antenne a giglio, addome a tromba con il fascio)
    06  DOTTOR SMERALDO, RAFFAELE      (antenne a spirale col serpentello, sacca-pesce)
    07  LANTERNINA, L'ANGELO CUSTODE   (addome a lanterna con la gabbia di chitina)
    08  HALOLO HALOLA', IL LUCCIOLO MUSICANTE (aureola-hula-hoop e sei sneakers)

Solo modelli 3D: nessuna animazione. Setup EEVEE Next: AgX Medium High
Contrast, esposizione -0.5, Bloom 0.4 (vedi creature_strumenti.py).

USO DA RIGA DI COMANDO
    blender --background --python creature_angeli.py -- \\
            --creatura serafino --salva serafino.blend --render serafino.png
"""

import bpy
import bmesh
import importlib.util
import os
import random
import sys
from math import cos, pi, radians, sin

from mathutils import Matrix, Vector
from mathutils import noise as mnoise

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# "serafino", "cherubino", "ofanim", "michele", "gabriele", "raffaele",
# "custode", "halolo" oppure "tutte"
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

# chitina e ali del setup degli angeli
CHIT = dict(rough=0.35, coat=0.5, sss=0.05)
ALA = dict(alpha=0.15, film=400.0)


def chitina(nome, base, **kw):
    d = dict(CHIT)
    d.update(kw)
    return ST.m_chitina(nome, base, **d)


def ala(nome, ramp, **kw):
    d = dict(ALA)
    d.update(kw)
    return ST.m_ala(nome, ramp, **d)


# ============================================================================
# STRUMENTI DEGLI ANGELI
# ============================================================================

def goccia(nome, base, punta, r, mat, seed=1, rumore=0.018, seg=40, rows=18, sub=1):
    """Addome a goccia (tondo vicino al torace, a punta in fondo) con un
    leggero Displace a rumore e la Subdivision."""
    base, punta = V(base), V(punta)
    L = (punta - base).length
    prof = []
    for i in range(rows + 1):
        t = 0.02 + 0.96 * i / rows
        prof.append((r * sin(pi * t ** 0.6) ** 0.8, L * t))
    ob = DS.lathe(nome, prof, mat, seg=seg, cap_bottom=True, cap_top=True)
    off = V((seed * 1.7, seed * 0.3, seed * 2.9))
    for v in ob.data.vertices:
        n = mnoise.noise(v.co * 9.0 + off)
        d = V((v.co.x, v.co.y, 0.0))
        if d.length > 1e-6:
            v.co += d.normalized() * rumore * n
    ob.matrix_world = CL.frame_matrix(base, V((1, 0, 0)) if abs((punta - base).normalized().x) < 0.9 else V((0, 1, 0)),
                                      punta - base)
    if sub:
        CL.add_subsurf(ob, sub, sub + 1)
    return ob


def m_anello_ofanim(nome, base=(0.3, 0.45, 0.75), luce=9000, forza=3.0):
    """Anello di chitina cristallina: due scanalature luminose lungo l'anello
    e un'onda di luce piu' intensa (maschera a gradiente sferico)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    righe = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', v, 2.0)), 0.5)),
                        0.06, 0.02)
    gr = nb.node('ShaderNodeTexGradient', gradient_type='SPHERICAL')
    mp = nb.node('ShaderNodeMapping')
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    nb.set(mp, 'Location', (-0.45, -0.3, 0.0))
    nb.set(mp, 'Scale', (1.6, 1.6, 1.6))
    nb.link(mp.outputs[0], gr.inputs['Vector'])
    onda = nb.maprange(gr.outputs['Fac'], 0.0, 0.9, 0.25, 1.0)
    fili = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', u, 48.0)), 0.5)),
                       0.47, 0.5)
    mask = nb.math('MAXIMUM', righe, nb.math('MULTIPLY', fili, 0.35))
    col = ST.colore(nb, luce)
    pb = nb.principled(base=base, rough=0.12, coat=0.8, trans=0.3, ior=1.5, spec=0.6)
    nb.set(pb, 'Thin Film Thickness', 450.0)
    s = nb.math('MULTIPLY', nb.math('MULTIPLY', mask, onda), ST.lum(forza))
    glow = nb.math('MULTIPLY', onda, 0.25)
    sh = nb.add_shader(pb.outputs[0], nb.emission(col, nb.math('ADD', s, glow)))
    nb.output(sh)
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(base, 1.0), nb.emission(col, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(mask, nb.emission((0.05, 0.08, 0.15), 1.0), nb.emission(col, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_res"] = [1024, 256]
    mat["rbx_emit_strength"] = 6.0
    CL.diffuse_display(mat, base)
    return mat


def m_aureola_arcobaleno(nome, forza=3.0, colori=((1.0, 0.18, 0.55), (1.0, 0.75, 0.05), (0.1, 0.55, 1.0))):
    """Aureola-hula-hoop: Color Ramp rosa -> giallo -> azzurro lungo l'anello
    (ciclico) con il nucleo bianco."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u = sep.outputs['X']
    stops = [(i / len(colori), c) for i, c in enumerate(colori)] + [(1.0, colori[0])]
    col = nb.ramp(u, stops)
    core = nb.maprange(nb.facing(0.5), 0.35, 0.9)
    col = NV.rgb_mix(nb, nb.math('MULTIPLY', core, 0.15), col, (1.0, 1.0, 1.0))
    nb.output(nb.emission(col, ST.lum(forza)))
    nb.bake_output("RBX_COLOR", nb.emission(nb.ramp(u, stops), 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(nb.ramp(u, stops), 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_res"] = [512, 64]
    mat["rbx_emit_strength"] = 10.0
    CL.diffuse_display(mat, colori[0])
    return mat


def m_candela(nome, K=1900, forza=25.0):
    """Luce di candela: Emission 25 con un leggero Noise sull'intensita'."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    nz = nb.noise(nb.texcoord(use_space=False).outputs['Object'], 3.0, 3.0, 0.5)
    s = nb.math('MULTIPLY', nb.maprange(nz.outputs['Fac'], 0.3, 0.7, 0.85, 1.15), ST.lum(forza))
    nb.output(nb.emission(ST.colore(nb, K), s))
    CL.diffuse_display(mat, ST.kelvin(K))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(ST.kelvin(K))
    return mat


def petalo_mesh(nome, lung, larg, mat, curl=0.35):
    return CL.feather_mesh(nome, lung, larg, mat, rows=8, cols=4, curl=curl, shape='pointed')


def giglio(prefisso, centro, asse, r, m_petalo, m_stame, m_polline):
    """Fiore di giglio a sei petali che si aprono all'indietro, con gli stami."""
    a = V(asse).normalized()
    fr = CL.frame_matrix(V(centro), a.orthogonal(), a)
    me = petalo_mesh(prefisso + "_Petalo", r, r * 0.38, m_petalo)
    for i in range(6):
        ang = TAU * i / 6
        d = V((cos(ang), sin(ang), 0.0))
        out = (fr.to_3x3() @ (d * 0.9 + V((0, 0, 0.75)))).normalized()
        ob = bpy.data.objects.new("%s_Petalo_%d" % (prefisso, i), me)
        CL.link(ob)
        ob.matrix_world = CL.frame_matrix(V(centro), out, fr.to_3x3() @ d - a * 0.3)
    for i in range(6):
        ang = TAU * i / 6 + 0.3
        tip = fr @ V((cos(ang) * r * 0.3, sin(ang) * r * 0.3, r * 0.8))
        CL.tube("%s_Stame_%d" % (prefisso, i), [V(centro), tip], 0.0025, m_stame, bevel_res=0, poly=True)
        CL.sphere("%s_Antera_%d" % (prefisso, i), tip, (0.007, 0.007, 0.012), m_polline, seg=8, rings=4)


def elica(base, asse, lung, raggio, giri, n=60, fase=0.0, stringi=0.3):
    """Punti di un'elica attorno a un asse (antenne a spirale, serpentello)."""
    a = V(asse).normalized()
    u = a.orthogonal().normalized()
    w = a.cross(u)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        th = fase + TAU * giri * t
        rr = raggio * (1.0 - stringi * t)
        pts.append(V(base) + a * lung * t + (u * cos(th) + w * sin(th)) * rr)
    return pts


# ============================================================================
# 01  FIAMMELLA, IL SERAFINO
# ============================================================================

def build_serafino():
    DS.texspace("Serafino")
    oro, bordo = 5500, 2600
    m_addome = ST.m_luce("Serafino_Addome_Ardente", 4000, 1.3, bordo=bordo, forza_bordo=3.0)
    m_chit = chitina("Serafino_Chitina_Perla", (0.5, 0.36, 0.15), metal=0.35, film=380.0)
    m_occhi = CL.m_body("Serafino_Occhi_Composti", (0.35, 0.12, 0.02), rough=0.2, coat=1.0, bump=(120.0, 0.4, 'scales'))
    m_elitre = chitina("Serafino_Elitre_Aperte", (0.55, 0.38, 0.12), metal=0.6, film=420.0,
                       rim=ST.kelvin(bordo), rim_str=0.35)
    m_elitre["rbx_thick"] = 1
    m_ala = ala("Serafino_Ali_Nervature", [(0.0, ST.kelvin(oro)), (1.0, ST.kelvin(3500))], membrane_str=0.25,
                vein_ramp=[(0.0, ST.kelvin(oro)), (1.0, ST.kelvin(bordo))], vein_str=ST.lum(6.0), radial=(7, 0.05),
                cells=(22.0, 0.035, 1.0), edge=0.05)
    m_nimbo = ST.m_luce("Serafino_Nimbo", oro, 8.0, bordo=bordo, forza_bordo=10.0)
    m_alone = ST.m_volume("Serafino_Alone_Dorato", (1.0, 0.85, 0.55), 0.5, luce_c=oro, forza=0.25, roblox="aura")
    Z = 0.95
    E = [el((0, -0.1, Z), 0.085, (1.0, 1.25, 1.0)), el((0, -0.27, Z + 0.04), 0.07),
         cap((0, -0.16, Z + 0.01), (0, -0.24, Z + 0.03), 0.055)]
    CL.metaball_mesh("Serafino_Torace", E, m_chit, res=0.011)
    ab = goccia("Serafino_Addome", (0, 0.0, Z - 0.02), (0, 0.5, Z - 0.12), 0.14, m_addome, seed=3)
    CL.no_shadow(ab)
    h = CL.sphere("Serafino_Alone", (0, 0.24, Z - 0.07), (0.3, 0.42, 0.28), m_alone, seg=16, rings=8)
    CL.no_shadow(h)
    ST.proxy(ab, (0, 0.2, Z - 0.1), oro, 10.0, nome="Serafino_Luce_Addome")
    ST.proxy(ab, (0, 0.25, Z - 0.35), bordo, 4.0, nome="Serafino_Luce_Sotto")
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Serafino_Occhio_" + s, (0.05 * sx, -0.31, Z + 0.06), (0.04, 0.035, 0.045), m_occhi, seg=16, rings=8)
        a = V((0.02 * sx, -0.33, Z + 0.1))
        CL.tube("Serafino_Antenna_" + s, [a, a + V((0.03 * sx, -0.05, 0.08)), a + V((0.07 * sx, -0.06, 0.14))],
                [0.005, 0.004, 0.002], m_chit, bevel_res=1)
        # zampette posteriori ripiegate e nascoste
        for k, y in enumerate((-0.16, -0.08, 0.0)):
            a = V((0.04 * sx, y, Z - 0.05))
            DS.leg("Serafino_Zampa_%s%d" % (s, k), [a, a + V((0.05 * sx, -0.02, -0.06)), a + V((0.02 * sx, -0.06, -0.08))],
                   [0.01, 0.008, 0.006], m_chit)
    # sei ali: elitre aperte (non coprono niente), due ali davanti agli occhi,
    # due ali sotto che coprono le zampe
    el_ctrl = [(-6, 0.1), (4, 0.36), (12, 0.54), (20, 0.58), (28, 0.42), (34, 0.1)]
    ws = CL.wing_pair("Serafino_Elitra", el_ctrl, m_elitre, (0.06, -0.12, Z + 0.05), elev=48, sweep=35, roll=25,
                      rings=6, cup=0.06, n=36)
    for w in ws:
        ST.solidifica(w, 0.008, 0.0)
    CL.wing_pair("Serafino_Ala_Occhi", [(-12, 0.06), (0, 0.2), (15, 0.27), (30, 0.24), (45, 0.08)], m_ala,
                 (0.05, -0.27, Z + 0.1), elev=-32, sweep=-112, roll=35, rings=6, cup=0.07, n=40)
    CL.wing_pair("Serafino_Ala_Zampe", [(-10, 0.1), (0, 0.32), (15, 0.4), (30, 0.34), (45, 0.1)], m_ala,
                 (0.05, -0.08, Z - 0.04), elev=-55, sweep=-50, roll=20, rings=6, cup=0.05, n=40)
    CL.wing_pair("Serafino_Ala_Volo", [(-8, 0.12), (4, 0.5), (16, 0.7), (30, 0.6), (44, 0.14)], m_ala,
                 (0.05, -0.06, Z + 0.06), elev=20, sweep=15, roll=10, rings=8, cup=0.03, n=48)
    # il piccolo nimbo tondo attorno al capo
    n = V((0, 0.35, 1.0)).normalized()
    halo = ST.toro("Serafino_Nimbo", 0.12, 0.008, m_nimbo, seg=48, sez=8,
                   matrice=CL.frame_matrix(V((0, -0.25, Z + 0.17)), V((1, 0, 0)), n))
    ST.proxy(halo, (0, -0.25, Z + 0.25), oro, 3.0, nome="Serafino_Luce_Nimbo")


# ============================================================================
# 02  QUATTRO MUSETTI, IL CHERUBINO
# ============================================================================

def faccia_umana(m, m_scuro):
    E = [el((0, -0.01, 0), 0.06, (0.9, 0.45, 1.15)), el((0, -0.04, -0.005), 0.013, (0.7, 1.0, 1.5)),
         el((0, -0.03, -0.05), 0.025, (1.0, 0.6, 0.7))]
    for sx in (-1, 1):
        E.append(el((0.03 * sx, -0.03, -0.02), 0.02, (1.0, 0.6, 0.8)))
    obs = [CL.metaball_mesh("Viso_Umano", E, m, res=0.007)]
    for sx in (-1, 1):
        obs.append(CL.tube("Viso_Umano_Palpebra_" + side_name(sx), [V((0.013 * sx, -0.042, 0.018)),
                                                                   V((0.024 * sx, -0.045, 0.014)),
                                                                   V((0.035 * sx, -0.04, 0.018))], 0.0025, m_scuro,
                           bevel_res=1))
    obs.append(CL.tube("Viso_Umano_Bocca", [V((-0.012, -0.045, -0.03)), V((0, -0.047, -0.033)),
                                            V((0.012, -0.045, -0.03))], 0.0025, m_scuro, bevel_res=1))
    return obs


def faccia_leone(m, m_scuro):
    E = [el((0, -0.01, 0), 0.055, (1.0, 0.5, 1.0)), el((0, -0.04, -0.02), 0.03, (1.2, 0.9, 0.8)),
         el((0, -0.02, 0.025), 0.03, (1.3, 0.6, 0.5))]
    obs = [CL.metaball_mesh("Viso_Leone", E, m, res=0.007)]
    obs.append(CL.sphere("Viso_Leone_Naso", (0, -0.068, -0.012), (0.012, 0.008, 0.008), m_scuro, seg=8, rings=4))
    for i in range(14):
        a = TAU * i / 14
        p = V((0.07 * cos(a), 0.0, 0.07 * sin(a)))
        obs.append(CL.cone_between("Viso_Leone_Criniera_%02d" % i, p * 0.8, p * 1.35 + V((0, 0.01, 0)), 0.02, 0.0, m,
                                   6))
    for sx in (-1, 1):
        obs.append(CL.sphere("Viso_Leone_Occhio_" + side_name(sx), (0.022 * sx, -0.048, 0.012), 0.008, m_scuro, seg=8,
                             rings=4))
        obs.append(CL.sphere("Viso_Leone_Orecchio_" + side_name(sx), (0.05 * sx, 0.0, 0.05), (0.02, 0.01, 0.02), m,
                             seg=8, rings=4))
    return obs


def faccia_bue(m, m_scuro):
    E = [el((0, -0.01, 0.01), 0.05, (1.1, 0.5, 1.0)), el((0, -0.045, -0.03), 0.04, (1.3, 0.8, 0.75))]
    obs = [CL.metaball_mesh("Viso_Bue", E, m, res=0.007)]
    for sx in (-1, 1):
        s = side_name(sx)
        obs.append(CL.sphere("Viso_Bue_Narice_" + s, (0.018 * sx, -0.075, -0.035), (0.008, 0.004, 0.006), m_scuro,
                             seg=8, rings=4))
        obs.append(CL.tube("Viso_Bue_Corno_" + s, [V((0.04 * sx, -0.01, 0.04)), V((0.08 * sx, -0.01, 0.05)),
                                                   V((0.1 * sx, -0.02, 0.09))], [0.012, 0.009, 0.002], m, bevel_res=2))
        obs.append(ST.cono_piatto("Viso_Bue_Orecchio_" + s, (0.05 * sx, 0.0, 0.015), (0.09 * sx, 0.0, 0.0), 0.015, m,
                                  0.4))
        obs.append(CL.sphere("Viso_Bue_Occhio_" + s, (0.032 * sx, -0.04, 0.02), 0.007, m_scuro, seg=8, rings=4))
    return obs


def faccia_aquila(m, m_scuro):
    E = [el((0, -0.005, 0), 0.05, (1.0, 0.55, 1.1)), el((0, -0.03, 0.025), 0.028, (1.5, 0.7, 0.5))]
    obs = [CL.metaball_mesh("Viso_Aquila", E, m, res=0.007)]
    obs.append(CL.tube("Viso_Aquila_Becco", [V((0, -0.035, 0.0)), V((0, -0.07, -0.005)), V((0, -0.085, -0.025)),
                                             V((0, -0.075, -0.04))], [0.02, 0.014, 0.007, 0.001], m, bevel_res=2))
    for sx in (-1, 1):
        obs.append(CL.sphere("Viso_Aquila_Occhio_" + side_name(sx), (0.022 * sx, -0.04, 0.012), 0.008, m_scuro, seg=8,
                             rings=4))
    return obs


def build_cherubino():
    DS.texspace("Cherubino")
    ambra = 3200
    m_elettro = chitina("Cherubino_Armatura_Elettro", (0.85, 0.6, 0.25), metal=0.8, rough=0.3, aniso=0.5)
    m_scuro = CL.m_body("Cherubino_Dettagli_Scuri", (0.05, 0.03, 0.015), rough=0.3, metal=0.5)
    m_organi = ST.m_luce("Cherubino_Organi_Luce", ambra, 8.0, bordo=4500, forza_bordo=10.0)
    m_lanterna = ST.m_luce("Cherubino_Lanternino", ambra, 10.0)
    m_scintille = ST.m_luce("Cherubino_Scintille", (1.0, 1.0, 1.0), 15.0)
    m_zoccoli = CL.m_body("Cherubino_Zoccoli", (0.03, 0.02, 0.015), rough=0.15, coat=1.0)
    m_ala = ala("Cherubino_Ali_Ambra", [(0.0, (1.0, 0.8, 0.5)), (1.0, (1.0, 0.65, 0.3))], membrane_str=0.4,
                vein_ramp=[(0.0, ST.kelvin(ambra)), (1.0, ST.kelvin(4500))], vein_str=4.0, radial=(8, 0.05),
                cross=(5, 0.04), edge=0.05)
    E = [el((0, -0.05, 0.48), 0.13, (1.1, 1.2, 0.9)), el((0, 0.25, 0.46), 0.15, (1.0, 1.35, 0.8))]
    CL.metaball_mesh("Cherubino_Corpo", E, m_elettro, res=0.014)
    # il pronoto-capo con le quattro facce scolpite
    Pc = V((0, -0.2, 0.72))
    CL.sphere("Cherubino_Pronoto", Pc, (0.17, 0.17, 0.16), m_elettro, seg=40, rings=20)
    facce = ((V((0, -1, 0.08)), faccia_umana), (V((1, 0, 0.08)), faccia_leone), (V((-1, 0, 0.08)), faccia_bue),
             (V((0, 1, 0.18)), faccia_aquila))
    for i, (d, fn) in enumerate(facce):
        d = d.normalized()
        master = fn(m_elettro, m_scuro)
        M = ST.frame(Pc + d * 0.155, d)
        ST.istanze(master, [M], "Cherubino_Faccia_%d" % i)
        o = CL.sphere("Cherubino_Organo_%d" % i, Pc + d * 0.16 + V((0, 0, -0.09)), (0.03, 0.03, 0.02), m_organi,
                      seg=14, rings=7)
        o.matrix_world = CL.frame_matrix(Pc + d * 0.15 + V((0, 0, -0.09)), V((0, 0, 1)), d) @ \
            Matrix.Diagonal((0.035, 0.022, 0.018, 1.0))
        ST.proxy(o, Pc + d * 0.25 + V((0, 0, -0.1)), ambra, 3.0)
    for sx in (-1, 1):
        a = V((0.04 * sx, -0.2, 0.87))
        CL.tube("Cherubino_Antenna_" + side_name(sx), [a, a + V((0.04 * sx, -0.02, 0.1)), a + V((0.1 * sx, -0.05, 0.16))],
                [0.006, 0.005, 0.003], m_elettro, bevel_res=1)
    # lanternino addominale e scintille bianche
    for k in range(3):
        o = CL.sphere("Cherubino_Lanternino_%d" % k, (0, 0.44 + 0.07 * k, 0.4 - 0.02 * k),
                      (0.1 - 0.02 * k, 0.05, 0.07 - 0.01 * k), m_lanterna, seg=16, rings=8)
    ST.proxy(o, (0, 0.55, 0.25), ambra, 6.0, nome="Cherubino_Luce_Lanternino")
    rnd = random.Random(12)
    for i in range(14):
        p = V((rnd.uniform(-0.25, 0.25), 0.5 + rnd.uniform(-0.1, 0.25), 0.3 + rnd.uniform(-0.1, 0.3)))
        CL.sphere("Cherubino_Scintilla_%02d" % i, p, rnd.uniform(0.004, 0.009), m_scintille, seg=6, rings=3)
    # quattro ali: elitre di elettro socchiuse e ali membranose doppie
    ws = CL.wing_pair("Cherubino_Elitra", [(-6, 0.12), (4, 0.34), (12, 0.46), (20, 0.44), (28, 0.3), (34, 0.1)],
                      m_elettro, (0.05, -0.02, 0.62), elev=30, sweep=62, roll=15, rings=6, cup=0.08, n=36)
    for w in ws:
        ST.solidifica(w, 0.01, 0.0)
    CL.wing_pair("Cherubino_Ala", [(-8, 0.12), (4, 0.5), (16, 0.68), (30, 0.6), (44, 0.14)], m_ala,
                 (0.05, 0.02, 0.6), elev=26, sweep=22, roll=10, rings=8, cup=0.03, n=48)
    # zampette con piccoli zoccoli tondi
    for i, y in enumerate((-0.15, 0.05, 0.25)):
        for sx in (-1, 1):
            s = side_name(sx)
            a = V((0.1 * sx, y, 0.42))
            k = V((0.26 * sx, y - 0.02, 0.32))
            f = V((0.3 * sx, y - 0.03, 0.03))
            DS.leg("Cherubino_Zampa_%s%d" % (s, i), [a, k, f], [0.02, 0.017, 0.013], m_elettro, joint_mat=m_elettro)
            CL.sphere("Cherubino_Zoccolo_%s%d" % (s, i), f + V((0, 0, -0.01)), (0.028, 0.032, 0.02), m_zoccoli, seg=12,
                      rings=6)


# ============================================================================
# 03  RUOTINA, L'OFANIM
# ============================================================================

def occhio_ofanim(m_bianco, m_iride, m_pupilla, r=0.026):
    """Ocello (costruito all'origine, guarda verso -Y)."""
    obs = [CL.sphere("Ocello_Bulbo", (0, 0, 0), (r, r * 0.7, r), m_bianco, seg=12, rings=6),
           CL.sphere("Ocello_Iride", (0, -r * 0.62, 0), (r * 0.62, r * 0.12, r * 0.62), m_iride, seg=12, rings=6),
           CL.sphere("Ocello_Pupilla", (0, -r * 0.72, 0), (r * 0.26, r * 0.06, r * 0.26), m_pupilla, seg=8, rings=4)]
    return obs


def build_ofanim():
    DS.texspace("Ofanim")
    blu = 9000
    m_ring = m_anello_ofanim("Ofanim_Anello_Cristallo", luce=blu)
    m_ring2 = m_anello_ofanim("Ofanim_Anello_Interno", base=(0.5, 0.55, 0.85), luce=blu, forza=2.5)
    m_bianco = CL.m_body("Ofanim_Occhi_Bianco", (0.9, 0.88, 0.8), rough=0.1, coat=1.0)
    m_iride = ST.m_luce("Ofanim_Iridi_Oro", 4500, 10.0, bordo=(1.0, 0.8, 0.4), forza_bordo=8.0)
    m_pup = CL.m_body("Ofanim_Pupille", (0.01, 0.01, 0.02), rough=0.05, coat=1.0)
    m_chit = chitina("Ofanim_Chitina", (0.25, 0.32, 0.55), metal=0.5, film=450.0)
    m_ala = ala("Ofanim_Alucce", [(0.0, (0.7, 0.85, 1.0)), (1.0, (0.85, 0.9, 1.0))], membrane_str=0.5,
                vein_ramp=[(0.0, ST.kelvin(blu)), (1.0, (1, 1, 1))], vein_str=6.0, radial=(5, 0.06))
    C = V((0, 0, 0.66))
    Rm, rm = 0.55, 0.085
    outer = ST.toro("Ofanim_Ruota_Esterna", Rm, rm, m_ring, seg=80, sez=16,
                    matrice=Matrix.Translation(C) @ Matrix.Rotation(pi / 2, 4, 'X'))
    ST.toro("Ofanim_Ruota_Interna", 0.36, 0.045, m_ring2, seg=64, sez=12,
            matrice=Matrix.Translation(C) @ Matrix.Rotation(pi / 2, 4, 'Y'))
    ST.toro("Ofanim_Ruota_Centrale", 0.22, 0.032, m_ring2, seg=48, sez=10, matrice=Matrix.Translation(C))
    CL.sphere("Ofanim_Mozzo", C, 0.06, m_chit, seg=20, rings=10)
    # decine di ocelli sul cerchione (istanze dello stesso occhio)
    mats = []
    for v, n in ((0.0, 22), (radians(58), 20), (radians(-58), 20)):
        for i in range(n):
            a = TAU * (i + 0.5 * (v != 0)) / n + pi / 2
            if abs(sin(a) + 1.0) < 0.05:
                continue                         # niente occhi dove tocca terra
            nr = V((cos(a), 0, sin(a)))
            nax = V((0, -1, 0))
            nrm = nr * cos(v) + nax * sin(v)
            p = C + nr * (Rm + rm * cos(v)) + nax * rm * sin(v)
            mats.append(ST.frame(p - nrm * 0.008, nrm, nax if abs(v) < 1e-3 else nr))
    ST.istanze(occhio_ofanim(m_bianco, m_iride, m_pup), mats, "Ofanim_Ocello")
    for i in range(4):
        a = TAU * i / 4 + pi / 4
        ST.proxy(outer, C + V((cos(a), -0.25, sin(a))) * 0.7, blu, 3.0, nome="Ofanim_Luce_Anello_%d" % i)
    ST.proxy(outer, C + V((0, -0.5, 0)), 4500, 3.0, nome="Ofanim_Luce_Occhi")
    # piccolo torace con la testa in cima alla ruota e ali quasi vestigiali
    top = C + V((0, 0, Rm + rm + 0.04))
    CL.metaball_mesh("Ofanim_Torace", [el(top, 0.05, (1.0, 1.2, 0.9)), el(top + V((0, -0.08, 0.03)), 0.045)], m_chit,
                     res=0.008)
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Ofanim_Occhio_Testa_" + s, top + V((0.03 * sx, -0.11, 0.045)), 0.017, m_iride, seg=10, rings=5)
        a = top + V((0.015 * sx, -0.11, 0.07))
        CL.tube("Ofanim_Antenna_" + s, [a, a + V((0.03 * sx, -0.03, 0.06)), a + V((0.06 * sx, -0.02, 0.1))],
                [0.004, 0.003, 0.002], m_chit, bevel_res=1)
    CL.wing_pair("Ofanim_Aluccia", [(-10, 0.04), (0, 0.1), (15, 0.12), (30, 0.1), (40, 0.04)], m_ala,
                 top + V((0.03, 0.0, 0.03)), elev=40, sweep=30, roll=15, rings=4, n=24)


# ============================================================================
# 04  SCUDO STELLATO, L'ARCANGELO MICHELE
# ============================================================================

def build_michele():
    DS.texspace("Michele")
    acciaio = 8500
    m_placca = chitina("Michele_Placche_Armatura", (0.62, 0.66, 0.74), metal=0.9, rough=0.32,
                       rim=ST.kelvin(acciaio), rim_str=0.35, rim_power=0.55)
    m_corpo = chitina("Michele_Corpo_Acciaio", (0.12, 0.13, 0.16), metal=0.85, rough=0.3)
    m_scudo = ST.m_luce("Michele_Scudo_Stella", acciaio, 1.2, bordo=(1.0, 1.0, 1.0), forza_bordo=3.0)
    m_occhi = ST.m_luce("Michele_Occhi", acciaio, 12.0)
    m_catena = CL.m_body("Michele_Catene", (0.7, 0.72, 0.78), rough=0.25, metal=1.0)
    m_piatti = chitina("Michele_Piatti_Bilancia", (0.75, 0.72, 0.6), metal=0.9, rough=0.25, film=300.0)
    E = [el((0, -0.1, 0.45), 0.13, (1.1, 1.0, 0.85)), el((0, 0.2, 0.45), 0.17, (1.05, 1.4, 0.8)),
         el((0, -0.33, 0.5), 0.09, (1.0, 1.0, 0.9))]
    CL.metaball_mesh("Michele_Corpo", E, m_corpo, res=0.014)
    # elitre fatte di placche sovrapposte come un'armatura a scaglie
    C, R = V((0, 0.18, 0.47)), (0.28, 0.42, 0.2)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.12, segments=1, affect='EDGES')
    master = CL.mesh_object("Michele_Placca", bm, m_placca, smooth=False)
    mats = []
    for j in range(7):
        y = -0.18 + 0.1 * j
        for sx in (-1, 1):
            for i in range(4):
                x = sx * (0.045 + 0.065 * i)
                z = ST.ellissoide_z(C, R, x, y)
                if z <= C.z + 0.02:
                    continue
                q = V((x, y, z)) - C
                nrm = V((q.x / R[0] ** 2, q.y / R[1] ** 2, q.z / R[2] ** 2)).normalized()
                M = CL.frame_matrix(V((x, y, z + 0.006)), V((0, 1, 0)), nrm) @ Matrix.Rotation(radians(-10), 4, 'X')
                mats.append(M @ Matrix.Diagonal((0.07, 0.11, 0.014, 1.0)))
    ST.istanze([master], mats, "Michele_Placca")
    # lo scudo a stella sul dorso
    star = ST.stella_mesh("Michele_Scudo", 8, 0.19, 0.085, 0.03, m_scudo)
    star.matrix_world = CL.frame_matrix(V((0, 0.14, 0.74)), V((0, 1, 0)), V((0, 0.3, 1.0)))
    ST.proxy(star, (0, 0.1, 0.95), acciaio, 8.0, nome="Michele_Luce_Scudo")
    ring = [V((0.21 * cos(a), 0.14 + 0.21 * sin(a) * 0.95, 0.735 - 0.06 * sin(a))) for a in
            [TAU * i / 32 for i in range(33)]]
    CL.tube("Michele_Scudo_Bordo", ring, 0.012, m_placca, bevel_res=2)
    # testa con l'elmo e la cresta
    ST.guscio("Michele_Elmo", (0, -0.34, 0.52), (0.1, 0.1, 0.1), m_placca, [((0, 0, 0.48), (0, 0, 1))])
    OC.fin_mesh("Michele_Cresta", [(-0.1, 0.0), (-0.05, 0.05), (0.05, 0.06), (0.12, 0.02), (0.13, 0.0)], 0.01, m_placca,
                CL.frame_matrix(V((0, -0.32, 0.61)), V((0, 0, 1)), V((1, 0, 0))) @ Matrix.Rotation(pi / 2, 4, 'Z'))
    for sx in (-1, 1):
        s = side_name(sx)
        e = CL.sphere("Michele_Occhio_" + s, (0.05 * sx, -0.42, 0.5), (0.025, 0.012, 0.012), m_occhi, seg=10, rings=5)
        ST.proxy(e, (0.05 * sx, -0.48, 0.5), acciaio, 0.6)
        a = V((0.03 * sx, -0.42, 0.56))
        CL.tube("Michele_Antenna_" + s, [a, a + V((0.04 * sx, -0.12, 0.12)), a + V((0.08 * sx, -0.2, 0.26))],
                [0.007, 0.005, 0.002], m_corpo, bevel_res=1)
        for i, y in enumerate((-0.18, 0.02, 0.22)):
            DS.leg("Michele_Zampa_%s%d" % (s, i), [V((0.12 * sx, y, 0.4)), V((0.3 * sx, y - 0.02, 0.32)),
                                                  V((0.34 * sx, y - 0.04, 0.0))], [0.022, 0.018, 0.012], m_corpo,
                   joint_mat=m_placca, joint_r=0.024)
    # due lobi addominali come piatti di una bilancia, in perfetto equilibrio
    post = [V((0, 0.56, 0.44)), V((0, 0.64, 0.56)), V((0, 0.66, 0.68))]
    CL.tube("Michele_Bilancia_Asta", post, 0.012, m_catena, bevel_res=1)
    CL.tube("Michele_Bilancia_Giogo", [V((-0.32, 0.66, 0.68)), V((0, 0.66, 0.7)), V((0.32, 0.66, 0.68))], 0.011,
            m_catena, bevel_res=1)
    CL.sphere("Michele_Bilancia_Perno", (0, 0.66, 0.7), 0.022, m_catena, seg=12, rings=6)
    for sx in (-1, 1):
        s = side_name(sx)
        top = V((0.32 * sx, 0.66, 0.68))
        pc = V((0.32 * sx, 0.66, 0.36))
        dish = DS.lathe("Michele_Piatto_" + s, [(0.002, -0.03), (0.06, -0.028), (0.1, -0.012), (0.12, 0.012),
                                               (0.115, 0.015)], m_piatti, seg=32, cap_bottom=False)
        dish.location = pc
        ST.solidifica(dish, 0.006, -1.0)
        for k in range(3):
            a = TAU * k / 3 + pi / 2
            CL.tube("Michele_Catena_%s%d" % (s, k), [top, pc + V((0.11 * cos(a), 0.11 * sin(a), 0.012))], 0.003,
                    m_catena, bevel_res=0, poly=True)


# ============================================================================
# 05  TROMBETTINA, L'ARCANGELO GABRIELE
# ============================================================================

def build_gabriele():
    DS.texspace("Gabriele")
    luna = 7500
    latte = ST.mescola(luna, (0.92, 0.95, 1.0), 0.45)
    m_chit = chitina("Gabriele_Chitina_Perla", (0.86, 0.88, 0.92), metal=0.25, film=420.0)
    m_campana = chitina("Gabriele_Tromba_Argento", (0.8, 0.82, 0.88), metal=0.9, rough=0.18)
    m_interno = ST.m_luce("Gabriele_Campana_Luce", latte, 8.0, bordo=(1.0, 1.0, 1.0), forza_bordo=10.0)
    m_fascio = OC.m_beam("Gabriele_Fascio_Lunare", latte, 1.0, length=2.4)
    m_stelo = CL.m_body("Gabriele_Steli_Giglio", (0.35, 0.55, 0.25), rough=0.4, sss=0.3)
    m_petalo = CL.m_body("Gabriele_Petali_Giglio", (0.95, 0.95, 0.92), rough=0.35, sss=0.6, sss_radius=(1, 1, 0.9),
                         emit=latte, emit_str=1.2)
    m_petalo["rbx_thick"] = 1
    m_stame = CL.m_body("Gabriele_Stami", (0.6, 0.7, 0.3), rough=0.4)
    m_polline = CL.m_body("Gabriele_Polline", (1.0, 0.55, 0.05), rough=0.6)
    m_ala = ala("Gabriele_Ali_Bianche", [(0.0, (0.95, 0.97, 1.0)), (1.0, (1.0, 1.0, 1.0))], membrane_str=0.5,
                vein_ramp=[(0.0, latte), (1.0, (1, 1, 1))], vein_str=5.0, radial=(9, 0.04), edge=0.04)
    Z = 0.85
    E = [el((0, -0.08, Z), 0.08, (1.0, 1.3, 1.0)), el((0, -0.24, Z + 0.05), 0.06),
         cap((0, -0.14, Z + 0.02), (0, -0.22, Z + 0.04), 0.045)]
    CL.metaball_mesh("Gabriele_Corpo", E, m_chit, res=0.011)
    # l'addome si apre in una campana di tromba
    ax = V((0, 0.85, -0.45)).normalized()
    J = V((0, 0.02, Z - 0.02))
    prof = [(0.06, 0.0), (0.055, 0.05), (0.04, 0.12), (0.03, 0.2), (0.032, 0.28), (0.045, 0.34), (0.075, 0.39),
            (0.12, 0.43), (0.165, 0.455), (0.175, 0.465)]
    fr = CL.frame_matrix(J, V((1, 0, 0)), ax)
    tromba = DS.lathe("Gabriele_Tromba", prof, m_campana, seg=40, cap_bottom=True)
    tromba.matrix_world = fr
    ST.solidifica(tromba, 0.006, -1.0)
    luce = DS.lathe("Gabriele_Campana_Interno", [(0.03, 0.3), (0.06, 0.37), (0.11, 0.425), (0.155, 0.452)], m_interno,
                    seg=32, cap_bottom=True)
    luce.matrix_world = fr @ Matrix.Translation((0, 0, -0.004))
    M = fr @ V((0, 0, 0.465))
    beam = CL.cone_between("Gabriele_Fascio", M, M + ax * 2.4, 0.16, 0.95, m_fascio, 32)
    CL.no_shadow(beam)
    sp = CL.add_light("Gabriele_Luce_Tromba", 'SPOT', M + ax * 0.02, 350.0, latte, 0.08, spot_size=42)
    CL.aim(sp, M + ax * 2.0)
    ST.proxy(luce, M - ax * 0.05, latte, 4.0, nome="Gabriele_Luce_Campana")
    # antenne a stelo di giglio con i fiori
    for sx in (-1, 1):
        s = side_name(sx)
        a = V((0.025 * sx, -0.28, Z + 0.09))
        tip = V((0.16 * sx, -0.5, Z + 0.45))
        stelo = [a, a + V((0.02 * sx, -0.08, 0.15)), tip - V((0.02 * sx, -0.02, 0.05)), tip]
        CL.tube("Gabriele_Stelo_" + s, stelo, [0.006, 0.005, 0.004, 0.004], m_stelo, bevel_res=1)
        for k in range(2):
            p = V(stelo[1]).lerp(V(stelo[2]), 0.3 + 0.4 * k)
            lf = CL.sphere("Gabriele_Foglia_%s%d" % (s, k), (0, 0, 0), 1.0, m_stelo, seg=10, rings=5)
            lf.matrix_world = CL.frame_matrix(p, V((0, 0, 1)), V((sx, -0.3, 0.4))) @ Matrix.Translation((0, 0, 0.03)) @ \
                Matrix.Diagonal((0.012, 0.004, 0.035, 1.0))
        giglio("Gabriele_Giglio_" + s, tip, (0.25 * sx, -0.6, 0.75), 0.11, m_petalo, m_stame, m_polline)
        CL.sphere("Gabriele_Occhio_" + s, (0.04 * sx, -0.28, Z + 0.06), 0.022, m_campana, seg=12, rings=6)
        for i, y in enumerate((-0.16, -0.08, 0.0)):
            DS.leg("Gabriele_Zampa_%s%d" % (s, i), [V((0.04 * sx, y, Z - 0.04)), V((0.14 * sx, y - 0.03, Z - 0.1)),
                                                   V((0.18 * sx, y + 0.02 * i, Z - 0.3))], [0.009, 0.007, 0.004],
                   m_chit, joint_mat=m_chit)
    # ali lunghe e sottili, quasi bianche
    CL.wing_pair("Gabriele_Ala_Anteriore", [(-8, 0.08), (0, 0.35), (6, 0.72), (12, 0.8), (18, 0.52), (24, 0.08)],
                 m_ala, (0.05, -0.1, Z + 0.05), elev=24, sweep=4, roll=8, rings=8, cup=0.02, n=48)
    CL.wing_pair("Gabriele_Ala_Posteriore", [(10, 0.08), (18, 0.4), (26, 0.62), (34, 0.5), (42, 0.08)], m_ala,
                 (0.05, -0.04, Z + 0.03), elev=14, sweep=16, roll=6, rings=8, cup=0.02, n=40)


# ============================================================================
# 06  DOTTOR SMERALDO, L'ARCANGELO RAFFAELE
# ============================================================================

def build_raffaele():
    DS.texspace("Raffaele")
    sme = (0.2, 1.0, 0.5)
    m_torace = CL.m_body("Raffaele_Torace_Smeraldo", (0.03, 0.25, 0.1), rough=0.3, sss=0.3,
                         sss_radius=(0.2, 1.0, 0.5), coat=0.6, emit=sme, emit_str=ST.lum(3.0), emit_center=True)
    m_chit = chitina("Raffaele_Chitina", (0.03, 0.12, 0.07), film=500.0)
    m_bastone = CL.m_body("Raffaele_Bastone", (0.3, 0.22, 0.1), rough=0.5, coat=0.3, bump=(40.0, 0.3, 'noise'))
    m_serpe = CL.m_body("Raffaele_Serpentello", (0.08, 0.45, 0.2), rough=0.3, coat=0.6, bump=(90.0, 0.35, 'scales'))
    m_pesce = CL.m_body("Raffaele_Sacca_Pesce", (0.1, 0.6, 0.35), rough=0.15, sss=0.8, sss_radius=(0.2, 1.0, 0.5),
                        coat=1.0, alpha=0.8, emit=sme, emit_str=ST.lum(2.5), emit_center=True)
    m_occhi = ST.m_luce("Raffaele_Occhi", sme, 10.0)
    m_conchiglia = CL.m_body("Raffaele_Conchiglia", (0.95, 0.8, 0.55), rough=0.35, sss=0.3, coat=0.4)
    m_bisaccia = CL.m_body("Raffaele_Bisaccia", (0.25, 0.14, 0.07), rough=0.75, bump=(60.0, 0.3, 'noise'))
    m_ala = ala("Raffaele_Ali_Verdi", [(0.0, (0.6, 1.0, 0.8)), (1.0, (0.8, 1.0, 0.9))], membrane_str=0.4,
                vein_ramp=[(0.0, sme), (1.0, (0.6, 1.0, 0.8))], vein_str=6.0, radial=(7, 0.05))
    Z = 0.95
    ch = CL.metaball_mesh("Raffaele_Torace", [el((0, -0.05, Z), 0.1, (1.0, 1.25, 1.0))], m_torace, res=0.011)
    CL.metaball_mesh("Raffaele_Corpo", [el((0, -0.22, Z + 0.06), 0.065), el((0, 0.26, Z - 0.05), 0.11, (0.9, 1.5, 0.8)),
                                        cap((0, -0.14, Z + 0.02), (0, -0.2, Z + 0.05), 0.05)], m_chit, res=0.011)
    ST.proxy(ch, (0, -0.2, Z - 0.1), sme, 5.0, nome="Raffaele_Luce_Torace")
    # sacca a forma di pesce sul dorso
    fish = CL.metaball_mesh("Raffaele_Pesce", [el((0, 0.14, Z + 0.14), 0.07, (0.65, 1.6, 0.9)),
                                               el((0, 0.05, Z + 0.15), 0.05, (0.7, 1.0, 0.9))], m_pesce, res=0.009)
    OC.fin_mesh("Raffaele_Pesce_Coda", [(0.0, -0.02), (0.08, -0.06), (0.06, 0.0), (0.08, 0.06), (0.0, 0.02)], 0.008,
                m_pesce, CL.frame_matrix(V((0, 0.24, Z + 0.14)), V((0, 0, 1)), V((1, 0, 0))) @
                Matrix.Rotation(pi / 2, 4, 'Z'))
    for sx in (-1, 1):
        CL.sphere("Raffaele_Pesce_Occhio_" + side_name(sx), (0.028 * sx, 0.02, Z + 0.17), 0.01, m_occhi, seg=8, rings=4)
    ST.proxy(fish, (0, 0.14, Z + 0.3), sme, 3.0, nome="Raffaele_Luce_Pesce")
    CL.no_shadow(fish)
    # antenne a spirale: il bastone del pellegrino con il serpentello avvolto
    base = V((0.0, -0.25, Z + 0.12))
    asse = V((0.0, -0.3, 1.0)).normalized()
    top = base + asse * 0.62
    CL.tube("Raffaele_Antenna_Bastone", [base, base.lerp(top, 0.5), top], [0.008, 0.009, 0.01], m_bastone, bevel_res=2)
    CL.sphere("Raffaele_Pomo", top + asse * 0.02, 0.022, m_bastone, seg=12, rings=6)
    spir = elica(base + asse * 0.04, asse, 0.52, 0.03, 3.2, n=64, stringi=0.25)
    CL.tube("Raffaele_Antenna_Serpente", spir, [0.009 - 0.004 * (i / 63) ** 2 for i in range(64)], m_serpe,
            bevel_res=2, poly=True)
    d = (spir[-1] - spir[-3]).normalized()
    hd = CL.sphere("Raffaele_Serpente_Testa", (0, 0, 0), 1.0, m_serpe, seg=12, rings=6)
    hd.matrix_world = CL.frame_matrix(spir[-1] + d * 0.012, V((0, 0, 1)), d) @ Matrix.Diagonal((0.012, 0.009, 0.02, 1))
    # conchiglia del pellegrino sul petto e bisaccia
    shell = OC.fin_mesh("Raffaele_Conchiglia", [(0, 0)] + [(0.05 * cos(a), 0.05 * sin(a) + 0.01) for a in
                                                          [pi * (0.1 + 0.8 * i / 10) for i in range(11)]], 0.006,
                        m_conchiglia, CL.frame_matrix(V((0, -0.16, Z - 0.02)), V((0, 0, 1)), V((0, -1, 0.3))))
    del shell
    OC.lumpy("Raffaele_Bisaccia", (0.12, 0.02, Z - 0.12), (0.05, 0.035, 0.06), m_bisaccia, seed=3, amount=0.1)
    CL.tube("Raffaele_Tracolla", [V((0.1, -0.06, Z + 0.05)), V((0.12, 0.0, Z - 0.06))], 0.005, m_bisaccia, bevel_res=0)
    # zampe lunghe da viandante
    for sx in (-1, 1):
        s = side_name(sx)
        CL.sphere("Raffaele_Occhio_" + s, (0.04 * sx, -0.26, Z + 0.07), 0.022, m_occhi, seg=12, rings=6)
        for i, y in enumerate((-0.14, -0.04, 0.06)):
            a = V((0.05 * sx, y, Z - 0.04))
            k = V((0.3 * sx, y - 0.04 + 0.03 * i, Z + 0.18))
            f = V((0.46 * sx, y - 0.1 + 0.12 * i, 0.0))
            DS.leg("Raffaele_Zampa_%s%d" % (s, i), [a, k, f.lerp(k, 0.3), f], [0.011, 0.01, 0.007, 0.004], m_chit,
                   joint_mat=m_chit)
    CL.wing_pair("Raffaele_Ala", [(-8, 0.1), (4, 0.45), (16, 0.6), (30, 0.52), (44, 0.12)], m_ala,
                 (0.05, -0.08, Z + 0.06), elev=22, sweep=18, roll=10, rings=8, cup=0.03, n=48)


# ============================================================================
# 07  LANTERNINA, L'ANGELO CUSTODE
# ============================================================================

def build_custode():
    DS.texspace("Custode")
    candela = 1900
    m_pelo = CL.m_body("Custode_Corpo_Morbido", (0.9, 0.82, 0.68), rough=0.55, sheen=1.0, sheen_tint=(1.0, 0.85, 0.6),
                       sss=0.3, sss_radius=(1.0, 0.7, 0.5), bump=(120.0, 0.2, 'noise'))
    m_occhi = CL.m_body("Custode_Occhioni", (0.02, 0.015, 0.012), rough=0.05, coat=1.0)
    m_rifl = ST.m_luce("Custode_Riflessi", (1, 1, 1), 6.0)
    m_gabbia = chitina("Custode_Gabbia_Chitina", (0.55, 0.38, 0.15), metal=0.7, rough=0.3)
    m_vetro = ST.m_vetro_sottile("Custode_Vetro_Lanterna", (1.0, 0.95, 0.85), bordo=candela, forza_bordo=0.8)
    m_fiamma = m_candela("Custode_Candela", candela, 25.0)
    m_punte = ST.m_luce("Custode_Punte_Antenne", candela, 12.0)
    m_guance = CL.m_body("Custode_Guance", (1.0, 0.5, 0.45), rough=0.6, sss=0.5)
    m_ala = ala("Custode_Ali", [(0.0, (1.0, 0.92, 0.75)), (1.0, (1.0, 0.95, 0.85))], membrane_str=0.4,
                vein_ramp=[(0.0, ST.kelvin(candela)), (1.0, (1.0, 0.85, 0.6))], vein_str=4.0, radial=(6, 0.05),
                edge=0.05)
    Z = 0.6
    CL.metaball_mesh("Custode_Corpo", [el((0, 0.0, Z), 0.13, (1.0, 1.0, 0.95)), el((0, -0.13, Z + 0.08), 0.12)],
                     m_pelo, res=0.01)
    for sx in (-1, 1):
        s = side_name(sx)
        n = V((0.35 * sx, -1.0, 0.1)).normalized()
        ST.occhio_cartone("Custode_Occhio_" + s, (0.055 * sx, -0.22, Z + 0.1), n, 0.045, m_occhi, m_occhi, m_rifl,
                          guarda=(0.0, 0.1), pupilla=0.3, piatto=0.8)
        CL.sphere("Custode_Guancia_" + s, (0.09 * sx, -0.2, Z + 0.03), (0.025, 0.01, 0.017), m_guance, seg=10, rings=5)
        a = V((0.035 * sx, -0.17, Z + 0.2))
        tip = a + V((0.05 * sx, -0.05, 0.12))
        CL.tube("Custode_Antenna_" + s, [a, a + V((0.02 * sx, -0.03, 0.06)), tip], [0.006, 0.005, 0.004], m_pelo,
                bevel_res=1)
        t = CL.sphere("Custode_Punta_Antenna_" + s, tip, 0.017, m_punte, seg=10, rings=5)
        ST.proxy(t, tip + V((0, -0.03, 0)), candela, 0.6)
        for i, y in enumerate((-0.06, 0.0, 0.06)):
            DS.leg("Custode_Zampa_%s%d" % (s, i), [V((0.06 * sx, y, Z - 0.08)), V((0.1 * sx, y - 0.02, Z - 0.16)),
                                                  V((0.1 * sx, y - 0.04, Z - 0.22))], [0.012, 0.01, 0.008], m_pelo)
    CL.tube("Custode_Sorriso", [V((-0.025, -0.245, Z + 0.035)), V((0.0, -0.252, Z + 0.025)),
                                V((0.025, -0.245, Z + 0.035))], 0.004, m_occhi, bevel_res=1)
    # l'addome-lanterna: gabbia di chitina (Wireframe) e sfera di luce dentro
    L = V((0, 0.2, Z - 0.1))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0)
    cage = CL.mesh_object("Custode_Gabbia", bm, m_gabbia, smooth=False)
    cage.location = L
    cage.scale = (0.12, 0.12, 0.15)
    wf = cage.modifiers.new("Gabbia_Wireframe", 'WIREFRAME')
    wf.thickness = 0.06
    wf.use_even_offset = True
    ST.applica(cage)
    glass = CL.sphere("Custode_Vetro", L, (0.108, 0.108, 0.135), m_vetro, seg=24, rings=12)
    CL.no_shadow(glass)
    flame = CL.sphere("Custode_Luce_Candela", L, (0.07, 0.07, 0.09), m_fiamma, seg=20, rings=10)
    CL.no_shadow(flame)
    ST.proxy(flame, L + V((0, 0, 0.01)), candela, 25.0, nome="Custode_Luce_Lanterna")
    ST.proxy(flame, L + V((0, -0.2, -0.2)), candela, 6.0, nome="Custode_Luce_Terra")
    top = DS.lathe("Custode_Cappello_Lanterna", [(0.07, 0.0), (0.06, 0.02), (0.03, 0.04), (0.012, 0.05)], m_gabbia,
                   seg=20, cap_bottom=True, cap_top=True)
    top.location = L + V((0, 0, 0.14))
    bot = DS.lathe("Custode_Fondo_Lanterna", [(0.01, -0.05), (0.04, -0.035), (0.065, -0.012), (0.07, 0.0)], m_gabbia,
                   seg=20, cap_bottom=True, cap_top=True)
    bot.location = L + V((0, 0, -0.14))
    CL.tube("Custode_Manico", [L + V((0, 0, 0.19)), L + V((0, -0.06, 0.22)), V((0, 0.05, Z - 0.02))], 0.008, m_gabbia,
            bevel_res=1)
    # ali: una e' piu' piccola e si china in avanti verso chi protegge
    fw = [(-10, 0.1), (2, 0.32), (15, 0.4), (30, 0.36), (44, 0.12)]
    ws = CL.wing_pair("Custode_Ala_Anteriore", fw, m_ala, (0.06, -0.03, Z + 0.1), elev=30, sweep=10, roll=10, rings=6,
                      cup=0.03, n=40)
    ws[1].scale = (0.8, 0.8, 0.8)
    ws[1].rotation_euler.z += radians(28)
    ws[1].rotation_euler.y -= radians(12)
    CL.wing_pair("Custode_Ala_Posteriore", [(20, 0.1), (32, 0.26), (46, 0.32), (60, 0.28), (72, 0.1)], m_ala,
                 (0.06, 0.02, Z + 0.08), elev=18, sweep=18, roll=6, rings=6, cup=0.02, n=36)


# ============================================================================
# 08  HALOLO HALOLA', IL LUCCIOLO MUSICANTE
# ============================================================================

def build_halolo():
    DS.texspace("Halolo")
    m_corpo = chitina("Halolo_Corpo_Pastello", (0.72, 0.58, 0.95), rough=0.3, sss=0.35, sss_radius=(1.0, 0.7, 1.0),
                      film=300.0)
    m_bianco = ST.m_occhio_bianco("Halolo_Occhi_Bianchi")
    m_pup = CL.m_body("Halolo_Pupille", (0.01, 0.01, 0.02), rough=0.05, coat=1.0)
    m_rifl = ST.m_luce("Halolo_Riflessi", (1, 1, 1), 8.0)
    m_labbra = CL.m_body("Halolo_Labbra", (0.95, 0.4, 0.55), rough=0.25, coat=0.6, sss=0.3)
    m_bocca = CL.m_body("Halolo_Bocca", (0.12, 0.01, 0.03), rough=0.5)
    m_lingua = CL.m_body("Halolo_Lingua", (0.9, 0.3, 0.4), rough=0.35, sss=0.4)
    m_guance = CL.m_body("Halolo_Guance", (1.0, 0.45, 0.6), rough=0.6, sss=0.5)
    m_aureola = m_aureola_arcobaleno("Halolo_Aureola_Hula_Hoop", 2.5)
    m_punto = ST.m_luce("Halolo_Puntino_Addome", (1.0, 1.0, 1.0), 12.0)
    m_suola = CL.m_body("Halolo_Suole", (0.97, 0.96, 0.94), rough=0.5)
    m_lacci = CL.m_body("Halolo_Lacci", (1.0, 1.0, 1.0), rough=0.6)
    scarpe = [CL.m_body("Halolo_Sneakers_Rosa", (1.0, 0.45, 0.65), rough=0.35, coat=0.3),
              CL.m_body("Halolo_Sneakers_Gialle", (1.0, 0.85, 0.3), rough=0.35, coat=0.3),
              CL.m_body("Halolo_Sneakers_Azzurre", (0.4, 0.75, 1.0), rough=0.35, coat=0.3)]
    m_ala = ala("Halolo_Alucce", [(0.0, (1.0, 0.8, 0.95)), (1.0, (0.8, 0.9, 1.0))], membrane_str=0.8,
                vein_ramp=[(0.0, (1.0, 0.6, 0.85)), (1.0, (0.6, 0.85, 1.0))], vein_str=6.0, radial=(5, 0.07))
    # corpo a goccia (in piedi)
    prof = []
    for i in range(19):
        t = i / 18
        z = 0.16 + 0.88 * t
        r = 0.33 * sin(pi * t ** 0.62) ** 0.9 + 0.002
        prof.append((r, z))
    body = DS.lathe("Halolo_Corpo", prof, m_corpo, seg=48, cap_bottom=True, cap_top=True)
    CL.add_subsurf(body, 1, 2)
    # faccia: occhi enormi da cartone e bocca a "O" che canta
    for sx in (-1, 1):
        s = side_name(sx)
        n = V((0.38 * sx, -1.0, 0.15)).normalized()
        ST.occhio_cartone("Halolo_Occhio_" + s, (0.1 * sx, -0.25, 0.66), n, 0.085, m_bianco, m_pup, m_rifl,
                          guarda=(-0.2 * sx, 0.25), pupilla=0.45, piatto=0.75)
        CL.sphere("Halolo_Guancia_" + s, (0.19 * sx, -0.25, 0.5), (0.04, 0.012, 0.025), m_guance, seg=12, rings=6)
    mc = V((0, -0.325, 0.47))
    fr = CL.frame_matrix(mc, V((0, 0, 1)), V((0, -1, 0.1)))
    ST.toro("Halolo_Labbra", 0.042, 0.017, m_labbra, seg=32, sez=10, matrice=fr @ Matrix.Diagonal((1.0, 1.25, 1, 1)))
    CL.sphere("Halolo_Bocca_Aperta", (0, 0, 0), 1.0, m_bocca, seg=16, rings=8).matrix_world = \
        fr @ Matrix.Translation((0, 0, -0.012)) @ Matrix.Diagonal((0.04, 0.05, 0.02, 1.0))
    CL.sphere("Halolo_Lingua", (0, 0, 0), 1.0, m_lingua, seg=12, rings=6).matrix_world = \
        fr @ Matrix.Translation((0, -0.022, -0.008)) @ Matrix.Diagonal((0.025, 0.018, 0.01, 1.0))
    # l'aureola gigante che gira come un hula-hoop attorno all'addome
    hoop_m = Matrix.Translation((0, 0.0, 0.42)) @ Matrix.Rotation(radians(12), 4, 'X') @ \
        Matrix.Rotation(radians(-8), 4, 'Y')
    hoop = ST.toro("Halolo_Aureola", 0.6, 0.03, m_aureola, seg=96, sez=10, matrice=hoop_m)
    for i, c in enumerate(((1.0, 0.18, 0.55), (1.0, 0.75, 0.05), (0.1, 0.55, 1.0))):
        a = TAU * i / 3 + 0.4
        ST.proxy(hoop, hoop_m @ V((0.6 * cos(a), 0.6 * sin(a), 0.05)), c, 2.0, nome="Halolo_Luce_Aureola_%d" % i)
    dot = CL.sphere("Halolo_Puntino", (0, 0.3, 0.22), 0.022, m_punto, seg=12, rings=6)
    ST.proxy(dot, (0, 0.38, 0.2), (1, 1, 1), 2.0)
    # tre paia di sneakers (Mirror + Array: istanze della stessa scarpa)
    for k, y in enumerate((-0.14, 0.0, 0.14)):
        master = ST.sneaker("Halolo_Scarpa_%d" % k, 0.15, scarpe[k], m_suola, m_lacci, m_suola)
        mats = []
        for sx in (-1, 1):
            foot = V((0.15 * sx, y - 0.02, 0.0))
            CL.tube("Halolo_Gamba_%s%d" % (side_name(sx), k), [V((0.1 * sx, y, 0.2)), V((0.14 * sx, y, 0.12)),
                                                              foot + V((0, 0.02, 0.06))], [0.022, 0.02, 0.018],
                    m_corpo, bevel_res=2)
            mats.append(ST.frame(foot, (0.15 * sx, -1.0, 0.0)))
        ST.istanze(master, mats, "Halolo_Scarpa_%d" % k)
    # due alette minuscole, troppo piccole per volare
    CL.wing_pair("Halolo_Aletta", [(-10, 0.04), (0, 0.11), (15, 0.14), (30, 0.12), (42, 0.04)], m_ala,
                 (0.08, 0.2, 0.75), elev=35, sweep=40, roll=20, rings=4, n=24)


# ============================================================================
# SCENE DEGLI ANGELI
# ============================================================================

def scena_gruppo(which):
    ST.mondo((0.004, 0.006, 0.02), (0.03, 0.04, 0.09), 1.0, nome="Cielo_Angeli")
    ST.pavimento("Terreno_Nuvole", (0.05, 0.055, 0.075), (0.12, 0.12, 0.15), scala=0.35, rough=(0.5, 0.8))
    ST.nebbia("Foschia_Dorata", (0, 3, 1.6), (30, 30, 3.2), (1.0, 0.9, 0.7), 0.006)
    ST.luci_studio(which, chiave=6500, contro=4000, riempimento=(0.6, 0.7, 1.0))


def scena_serafino():
    m = ST.m_volume("Volume_Dorato", (1.0, 0.85, 0.55), 0.1, luce_c=5500, forza=0.03, roblox="drop")
    v = CL.sphere("Volume_Dorato_Scena", (0, 0.1, 0.9), (1.4, 1.4, 1.1), m, seg=16, rings=8)
    v["rbx_drop"] = 1
    ST.compositor(0.4, 7, (6, 20.0, 0.12), 0.0)


def scena_cherubino():
    ST.luce("Luce_Di_Taglio", 'SPOT', (0.6, -0.3, 2.6), 250.0, 5000, 0.2, rot=(10, 10, 0), spot=40)


def scena_ofanim():
    ST.nebbia("Volume_Blu", (0, 0.5, 1.0), (6, 6, 2), (0.5, 0.7, 1.0), 0.012)
    cam = bpy.context.scene.camera
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 2.8
    cam.data.dof.focus_distance = (cam.location - V((0, 0, 0.66))).length
    ST.compositor(0.4, 6, None, 0.0)


def scena_michele():
    ST.luce("Rim_Fredda", 'AREA', (0.5, 1.6, 1.3), 150.0, 9000, 2.0, rot=(-65, 0, 180))
    ST.compositor(0.4, 7, (2, 0.0, 0.35), 0.0)


def scena_gabriele():
    ST.mondo((0.002, 0.004, 0.02), (0.01, 0.02, 0.07), 1.0, nome="Notte_Blu")
    ST.nebbia("Velo_Blu", (0, 1.0, 1.0), (7, 7, 2), (0.7, 0.8, 1.0), 0.02)


def scena_raffaele():
    ST.luce("Riempimento_Verde", 'AREA', (-1.5, -1.0, 1.5), 60.0, (0.3, 1.0, 0.5), 3.0, rot=(60, 0, -60))
    ST.compositor(0.45, 8, None, 0.0)


def scena_custode():
    sp = ST.luce("Cerchio_Caldo", 'SPOT', (0, 0.1, 2.4), 300.0, 1900, 0.3, spot=38)
    sp.data.spot_blend = 0.3
    ST.nebbia("Volume_Sottile", (0, 0.3, 1.0), (5, 5, 2), (1.0, 0.9, 0.8), 0.015)


def scena_halolo():
    ST.mondo((0.6, 0.45, 0.65), (0.45, 0.6, 0.85), 0.5, nome="Sfondo_Pastello")
    colori = [(1.0, 0.3, 0.6), (1.0, 0.85, 0.2), (0.3, 0.7, 1.0), (0.5, 1.0, 0.5), (0.8, 0.4, 1.0), (1.0, 0.5, 0.2)]
    for i, c in enumerate(colori):
        a = TAU * i / len(colori)
        ST.luce("Disco_%d" % i, 'POINT', (1.4 * cos(a), 1.4 * sin(a), 0.4 + 0.8 * (i % 2)), 40.0, c, 0.1)
    ST.compositor(0.6, 8, None, 0.0)


CREATURE_ANGELI = {
    #  chiave        (collezione,                    funzione,          camera: target, dist, elev, azim, lente)
    "serafino":  ("A01_Fiammella-Serafino",        build_serafino,    ((0, 0.05, 0.92), 3.6, 10, 35, 50)),
    "cherubino": ("A02_Quattro-Musetti-Cherubino", build_cherubino,   ((0, -0.05, 0.6), 3.2, 16, 40, 50)),
    "ofanim":    ("A03_Ruotina-Ofanim",            build_ofanim,      ((0, 0.0, 0.7), 3.6, 8, 20, 50)),
    "michele":   ("A04_Scudo-Stellato-Michele",    build_michele,     ((0, 0.1, 0.5), 3.4, 28, 35, 50)),
    "gabriele":  ("A05_Trombettina-Gabriele",      build_gabriele,    ((0, 0.2, 0.8), 4.0, 8, 60, 50)),
    "raffaele":  ("A06_Dottor-Smeraldo-Raffaele",  build_raffaele,    ((0, -0.05, 0.8), 4.6, 10, 35, 50)),
    "custode":   ("A07_Lanternina-Custode",        build_custode,     ((0, 0.0, 0.55), 2.4, 10, 35, 50)),
    "halolo":    ("A08_Halolo-Halola",             build_halolo,      ((0, 0.0, 0.52), 3.0, 10, 20, 50)),
}

DISPOSIZIONE_ANGELI = {
    "ofanim":    (-4.6, 4.8, 0),
    "serafino":  (-1.6, 4.6, 20),
    "gabriele":  (1.5, 4.8, -40),
    "raffaele":  (4.5, 4.6, -20),
    "michele":   (-3.8, 0.7, 25),
    "cherubino": (-1.2, 0.4, 20),
    "custode":   (1.2, 0.3, -15),
    "halolo":    (3.8, 0.5, -20),
}

SCENE_ANGELI = {"serafino": scena_serafino, "cherubino": scena_cherubino, "ofanim": scena_ofanim,
                "michele": scena_michele, "gabriele": scena_gabriele, "raffaele": scena_raffaele,
                "custode": scena_custode, "halolo": scena_halolo}


def build(which=None, engine=None, clean=None):
    ST.build_serie(CREATURE_ANGELI, DISPOSIZIONE_ANGELI, which or CREATURA, scena_gruppo, SCENE_ANGELI,
                   ((0, 2.5, 0.75), 10.2, 13, 0, 32), ST.SETUP["angeli"], engine or MOTORE, clean)


def main():
    ST.main(build)


if __name__ == "__main__":
    main()
