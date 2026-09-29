# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE: I DRAGHI - ottava serie per Blender (modelli statici).

    01  TESORINO, IL DRAGO CUSTODE     (Fafnir: arrotolato sul tesoro, scaglie-moneta)
    02  PERLA, IL DRAGO CINESE LONG    (corpo sinuoso, corna di cervo, perla fiammeggiante)
    03  MAREA, IL RE DRAGO RYUJIN      (criniera a onda, i due gioielli delle maree)
    04  QUETZAL, IL SERPENTE PIUMATO   (piume smeraldo, sette triangoli di luce)
    05  DDRAIG, IL DRAGO ROSSO GALLESE (la torre di Vortigern sul dorso)
    06  IDRA, LA PICCOLA IDRA DI LERNA (nove testine, code a foglia di ninfea)
    07  BLASONE, IL WYVERN ARALDICO    (scudetto sul petto, coda a punta di freccia)
    08  OUROBO' OUROBO', IL CIAMBELLINO DRACONICO (si morde la coda, rotola con 4 sneakers)

Solo modelli 3D: nessuna animazione. Setup EEVEE Next: AgX Medium High
Contrast, esposizione -0.5, Bloom 0.4 (vedi creature_strumenti.py).

USO DA RIGA DI COMANDO
    blender --background --python creature_draghi.py -- \\
            --creatura tesorino --salva tesorino.blend --render tesorino.png
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

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# "tesorino", "long", "ryujin", "quetzal", "ddraig", "idra", "wyvern",
# "ourobo" oppure "tutte"
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

CHIT = dict(rough=0.35, coat=0.5, sss=0.05)
ALA = dict(alpha=0.15, film=400.0)


def chitina(nome, base, **kw):
    d = dict(CHIT)
    d.update(kw)
    return ST.m_chitina(nome, base, **d)


# ============================================================================
# MATERIALI DEI DRAGHI
# ============================================================================

def m_squame(nome, dorso, ventre, film=400.0, lung=14.0, giro=5.0, luce_ventre=None, forza=0.0, macchie=None,
             triangoli=None):
    """Squame di drago per corpi a tubo (UV: u lungo il corpo, v attorno; v = 0
    sul dorso, 0.5 sul ventre): squame sovrapposte con Thin Film, ventre a
    placche lisce (anche luminoso), e se richiesto i sette triangoli di luce
    di Kukulkan lungo i fianchi. triangoli = (colore, forza, u0, u1, n)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('MULTIPLY', u, lung), cmb.inputs[0])
    nb.link(nb.math('MULTIPLY', v, giro), cmb.inputs[1])
    vo = nb.voronoi(cmb.outputs[0], 5.0, 'DISTANCE_TO_EDGE', randomness=0.35)
    bordo = nb.maprange(vo.outputs['Distance'], 0.1, 0.02)
    vv = nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.5))
    pancia = nb.maprange(vv, 0.2, 0.14)
    placche = nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', u, lung * 3.0)),
                                                      0.5)), 0.42, 0.5)
    col = NV.rgb_mix(nb, bordo, dorso, tuple(c * 0.35 for c in dorso))
    if macchie is not None:
        nz = nb.noise(cmb.outputs[0], 1.5, 3.0, 0.5)
        col = NV.rgb_mix(nb, nb.maprange(nz.outputs['Fac'], 0.55, 0.65), col, macchie)
    col = NV.rgb_mix(nb, pancia, col, NV.rgb_mix(nb, placche, ventre, tuple(c * 0.6 for c in ventre)))
    pb = nb.principled(base=col, rough=0.32, coat=0.5, spec=0.5, sss=0.05)
    nb.set(pb, 'Thin Film Thickness', film)
    nb.set(pb, 'Thin Film IOR', 1.45)
    h = nb.math('ADD', nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, bordo), nb.math('SUBTRACT', 1.0, pancia)),
                nb.math('MULTIPLY', placche, pancia))
    nb.set(pb, 'Normal', nb.bump(h, 0.4, 0.01))
    sh = pb.outputs[0]
    emit_mask = None
    ecol = None
    if luce_ventre is not None and forza:
        ecol = ST.colore(nb, luce_ventre)
        emit_mask = nb.math('MULTIPLY', pancia, nb.maprange(placche, 1.0, 0.0, 0.4, 1.0))
        sh = nb.add_shader(sh, nb.emission(ecol, nb.math('MULTIPLY', emit_mask, forza * CL.INTENSITA_LUCE)))
    if triangoli is not None:
        tcol, tforza, u0, u1, n = triangoli
        s = nb.math('FRACT', nb.math('MULTIPLY', nb.maprange(u, u0, u1, 0.0, 1.0, smooth=False), float(n)))
        dent = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', s, 0.5)), 2.0)
        dv = nb.math('MINIMUM', nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.25)),
                     nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.75)))
        tri = nb.math('SUBTRACT', nb.math('SUBTRACT', 1.0, dent), nb.math('MULTIPLY', dv, 9.0))
        tri = nb.maprange(tri, 0.0, 0.06)
        dentro = nb.math('MULTIPLY', nb.maprange(u, u0, u0 + 0.005), nb.maprange(u, u1, u1 - 0.005))
        tri = nb.math('MULTIPLY', tri, dentro)
        tc2 = nb.ramp(dent, [(0.0, ST.rgb(tcol[0])), (1.0, ST.rgb(tcol[1]))])
        sh = nb.mix_shader(tri, sh, nb.emission(tc2, tforza * CL.INTENSITA_LUCE))
        emit_mask = tri
        ecol = tc2
    nb.output(sh)
    if emit_mask is not None:
        nb.bake_output("RBX_COLOR", nb.mix_shader(emit_mask, nb.emission(col, 1.0), nb.emission(ecol, 1.0)))
        nb.bake_output("RBX_EMIT", nb.mix_shader(emit_mask, nb.emission((0, 0, 0), 1.0), nb.emission(ecol, 1.0)))
        mat["rbx_emit_strength"] = 6.0
    else:
        nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_res"] = [2048, 512]
    mat["rbx_rough"] = 0.32
    CL.diffuse_display(mat, dorso)
    return mat


def m_perla(nome, nucleo, forza=90.0, bordo=(1.0, 1.0, 1.0)):
    """Perla luminosa: nucleo colorato (Kelvin), bordo bianco brillante con il
    Fresnel (Layer Weight)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    f = nb.maprange(nb.fresnel(0.35), 0.1, 0.8)
    col = NV.rgb_mix(nb, f, ST.colore(nb, nucleo), bordo)
    s = nb.maprange(f, 0.0, 1.0, forza, forza * 1.4)
    nb.output(nb.emission(col, nb.math('MULTIPLY', s, CL.INTENSITA_LUCE)))
    CL.diffuse_display(mat, ST.rgb(nucleo))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(ST.mescola(nucleo, bordo, 0.35))
    return mat


def m_smalti(nome, forza=100.0, smalto=0.0):
    """Punta di freccia araldica: Color Ramp a 4 stop con gli smalti (oro 3000 K,
    argento 8000 K, rosso 2200 K, azzurro 12000 K); il valore 'Smalto'
    (0, 0.33, 0.66, 1) sceglie il colore."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    sm = nb.value(smalto)
    sm.node.label = "Smalto (0 oro, 0.33 argento, 0.66 rosso, 1 azzurro)"
    stops = [(0.0, ST.kelvin(3000)), (0.33, ST.kelvin(8000)), (0.66, ST.mescola(2200, (1.0, 0.05, 0.05), 0.5)),
             (1.0, ST.mescola(12000, (0.1, 0.3, 1.0), 0.5))]
    col = nb.ramp(sm, stops, interp='CONSTANT')
    f = nb.maprange(nb.fresnel(0.3), 0.2, 0.9)
    col = NV.rgb_mix(nb, nb.math('MULTIPLY', f, 0.5), col, (1.0, 1.0, 1.0))
    nb.output(nb.emission(col, forza * CL.INTENSITA_LUCE))
    CL.diffuse_display(mat, ST.kelvin(3000))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(ST.kelvin(3000))
    return mat


def m_anello_cromatico(nome, centro, forza=50.0):
    """Ourobo': Color Ramp ciclico rosa -> giallo -> azzurro -> verde -> rosa
    guidato dall'angolo attorno al centro dell'anello (Gradient Angular)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord()
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    cmb = nb.node('ShaderNodeCombineXYZ')
    nb.link(nb.math('SUBTRACT', sep.outputs['X'], centro[0]), cmb.inputs[0])
    nb.link(nb.math('SUBTRACT', sep.outputs['Z'], centro[2]), cmb.inputs[1])
    gr = nb.node('ShaderNodeTexGradient', gradient_type='RADIAL')
    nb.link(cmb.outputs[0], gr.inputs['Vector'])
    stops = [(0.0, ST.mescola(3500, (1.0, 0.45, 0.75), 0.6)), (0.25, (1.0, 0.9, 0.35)),
             (0.5, ST.mescola(9000, (0.35, 0.75, 1.0), 0.5)), (0.75, (0.45, 1.0, 0.5)),
             (1.0, ST.mescola(3500, (1.0, 0.45, 0.75), 0.6))]
    col = nb.ramp(gr.outputs['Fac'], stops)
    pb = nb.principled(base=col, rough=0.3, coat=0.6, sss=0.2, sss_radius=(1, 1, 1))
    nb.set(pb, 'Thin Film Thickness', 350.0)
    sh = nb.add_shader(pb.outputs[0], nb.emission(col, forza * CL.INTENSITA_LUCE))
    nb.output(sh)
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    nb.bake_output("RBX_EMIT", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_emit_strength"] = 8.0
    CL.diffuse_display(mat, (1.0, 0.6, 0.8))
    return mat


def m_pietra(nome, base=(0.3, 0.28, 0.25)):
    return CL.m_body(nome, base, rough=0.9, bump=(25.0, 0.7, 'noise'), mottle=(tuple(c * 0.6 for c in base), 6.0))


# ============================================================================
# STRUMENTI DEI DRAGHI
# ============================================================================

def corpo(nome, ctrl, raggi, mat, n=48, ring=18, squash=0.92):
    """Corpo di drago/serpente: tubo lungo un percorso (Curve + Bevel con UV),
    con la normale verso l'alto (dorso a v = 0)."""
    pts = DS.spline([V(p) for p in ctrl], n)
    if callable(raggi):
        rad = [raggi(i / (n - 1)) for i in range(n)]
    else:
        rad = raggi
    frames = DS.frames_up(pts)
    ob, _fr, _l = DS.sweep_mesh(nome, pts, rad, mat, ring=ring, squash=squash, frames=frames)
    return ob, pts, rad, frames


def punto(pts, rad, frames, t, ang=0.0, alza=1.0):
    """Punto sulla superficie del corpo: t lungo il corpo (0..1), ang attorno
    (0 = dorso, 90 = fianco destro, 180 = ventre). Restituisce (punto, normale,
    tangente)."""
    n = len(pts)
    f = t * (n - 1)
    i = min(int(f), n - 2)
    s = f - i
    p = pts[i].lerp(pts[i + 1], s)
    r = rad[i] + (rad[i + 1] - rad[i]) * s
    tans, norms, binors = frames
    tg = tans[i].lerp(tans[i + 1], s).normalized()
    nr = norms[i].lerp(norms[i + 1], s).normalized()
    bn = binors[i].lerp(binors[i + 1], s).normalized()
    a = radians(ang)
    d = (nr * cos(a) + bn * sin(a)).normalized()
    return p + d * r * alza, d, tg


def testa_drago(m_pelle, m_occhi, m_corna, m_bocca=None, m_denti=None, muso=0.2, largo=0.075, corna='dritte',
                occhi='aperti', bocca=0.0, baffi=0.0, m_baffi=None, orecchie=True, m_extra=None):
    """Testa di drago costruita all'origine con il muso verso -Y.
    corna: 'dritte' | 'cervo' | 'ariete' | 'cresta' | None
    occhi: 'aperti' | 'chiusi' (dorme) | ('cartone', m_bianco, m_pupilla, m_riflesso)
    bocca: apertura della mascella in gradi. baffi: lunghezza dei baffi."""
    obs = []
    w = largo
    E = [el((0, 0, 0), w, (1.0, 1.1, 0.9)), el((0, -muso * 0.5, -w * 0.15), w * 0.72, (0.85, muso / (w * 1.3), 0.62)),
         el((0, -muso * 0.95, -w * 0.12), w * 0.5, (0.95, 1.0, 0.7))]
    for sx in (-1, 1):
        E.append(el((w * 0.5 * sx, -w * 0.5, w * 0.45), w * 0.35, (1.0, 1.5, 0.55)))
    obs.append(CL.metaball_mesh("Drago_Testa", E, m_pelle, res=w * 0.14))
    # mascella (aperta di `bocca` gradi attorno alla cerniera)
    J = [el((0, -muso * 0.5, -w * 0.55), w * 0.62, (0.8, muso / (w * 1.25), 0.3)),
         el((0, -muso * 0.92, -w * 0.52), w * 0.42, (0.9, 1.0, 0.35))]
    jaw = CL.metaball_mesh("Drago_Mascella", J, m_pelle, res=w * 0.14)
    piv = V((0, w * 0.2, -w * 0.35))
    rot = Matrix.Translation(piv) @ Matrix.Rotation(radians(bocca), 4, 'X') @ Matrix.Translation(-piv)
    jaw.matrix_world = rot
    obs.append(jaw)
    if bocca > 3 and m_bocca is not None:
        obs.append(CL.sphere("Drago_Gola", (0, -muso * 0.45, -w * 0.45), (w * 0.5, muso * 0.45, w * 0.22), m_bocca,
                             rot=(bocca * 0.5, 0, 0), seg=16, rings=8))
    if m_denti is not None:
        for sx in (-1, 1):
            for k in range(4):
                y = -muso * (0.55 + 0.12 * k)
                a = V((w * 0.42 * sx * (1 - 0.12 * k), y, -w * 0.4))
                obs.append(CL.cone_between("Drago_Dente_%s%d" % (side_name(sx), k), a, a + V((0, 0, -w * 0.3)), w * 0.07,
                                           0.0, m_denti, 6))
    for sx in (-1, 1):
        s = side_name(sx)
        obs.append(CL.sphere("Drago_Narice_" + s, (w * 0.22 * sx, -muso * 1.12, w * 0.12), (w * 0.12, w * 0.08, w * 0.06),
                             m_corna, seg=8, rings=4))
        ep = V((w * 0.62 * sx, -w * 0.45, w * 0.28))
        if occhi == 'aperti':
            obs.append(CL.sphere("Drago_Occhio_" + s, ep, (w * 0.22, w * 0.2, w * 0.22), m_occhi, seg=14, rings=7))
        elif occhi == 'chiusi':
            obs.append(CL.tube("Drago_Palpebra_" + s, [ep + V((-0.0, w * 0.2, 0.0)), ep + V((w * 0.05 * sx, 0.0, -w * 0.06)),
                                                       ep + V((0.0, -w * 0.2, 0.0))], w * 0.04, m_corna, bevel_res=1))
        else:
            _tag, m_b, m_p, m_r = occhi
            n = V((0.75 * sx, -0.6, 0.35)).normalized()
            obs += ST.occhio_cartone("Drago_Occhio_" + s, ep + n * w * 0.1, n, w * 0.5, m_b, m_p, m_r,
                                     guarda=(-0.4 * sx, 0.2), pupilla=0.45, piatto=0.8)
            obs.append(ST.sopracciglio("Drago_Sopracciglio_" + s, ep + n * w * 0.1 + V((0, 0, w * 0.35)), n, w * 1.1,
                                       -12.0, w * 0.12, m_corna, lato=sx, arco=0.25, alza=w * 0.2))
        base = V((w * 0.45 * sx, w * 0.2, w * 0.7))
        if corna == 'dritte':
            obs.append(CL.tube("Drago_Corno_" + s, [base, base + V((w * 0.3 * sx, w * 0.9, w * 0.7)),
                                                    base + V((w * 0.45 * sx, w * 2.0, w * 0.9))],
                               [w * 0.2, w * 0.13, w * 0.02], m_corna, bevel_res=2))
        elif corna == 'cervo':
            tr = [base, base + V((w * 0.4 * sx, w * 0.4, w * 1.2)), base + V((w * 0.9 * sx, w * 1.1, w * 2.2)),
                  base + V((w * 1.1 * sx, w * 1.8, w * 3.0))]
            obs.append(CL.tube("Drago_Corno_" + s, tr, [w * 0.15, w * 0.12, w * 0.08, w * 0.03], m_corna, bevel_res=2))
            for k, (i0, d) in enumerate(((1, (0.2, -0.6, 0.9)), (2, (0.6, -0.3, 0.8)), (2, (-0.3, 0.8, 0.6)))):
                a = tr[i0]
                obs.append(CL.tube("Drago_Ramo_%s%d" % (s, k), [a, a + V((d[0] * sx, d[1], d[2])) * w * 0.9],
                                   [w * 0.07, w * 0.02], m_corna, bevel_res=1))
        elif corna == 'ariete':
            pts = [base + V((w * (0.2 + 0.7 * sin(a)) * sx, w * (0.2 + 1.0 * (1 - cos(a))), w * (0.6 * sin(a * 1.3))))
                   for a in [i * 0.45 for i in range(9)]]
            obs.append(CL.tube("Drago_Corno_" + s, pts, [w * (0.22 - 0.022 * i) for i in range(9)], m_corna,
                               bevel_res=2))
        if orecchie:
            obs.append(ST.cono_piatto("Drago_Orecchio_" + s, (w * 0.75 * sx, w * 0.35, w * 0.35),
                                      (w * 1.4 * sx, w * 0.9, w * 0.55), w * 0.25, m_pelle, 0.35,
                                      avanti=(0.2 * sx, -1, 0.2)))
        if baffi:
            a = V((w * 0.35 * sx, -muso * 1.0, -w * 0.05))
            pts = [a, a + V((w * 1.2 * sx, -w * 0.2, -w * 0.2)), a + V((baffi * 0.45 * sx, baffi * 0.1, -baffi * 0.3)),
                   a + V((baffi * 0.75 * sx, baffi * 0.4, -baffi * 0.35)), a + V((baffi * 0.9 * sx, baffi * 0.6, -baffi * 0.2))]
            obs.append(CL.tube("Drago_Baffo_" + s, pts, [w * 0.07, w * 0.06, w * 0.05, w * 0.03, w * 0.01],
                               m_baffi or m_corna, bevel_res=1))
    if corna == 'cresta':
        obs.append(OC.fin_mesh("Drago_Cresta", [(-w * 0.2, 0.0), (0.0, w * 1.0), (w * 0.8, w * 1.4), (w * 1.6, w * 0.9),
                                                (w * 2.2, 0.0)], w * 0.12, m_corna,
                               CL.frame_matrix(V((0, -w * 0.3, w * 0.75)), V((0, 0, 1)), V((1, 0, 0))) @
                               Matrix.Rotation(pi / 2, 4, 'Z') @ Matrix.Rotation(pi, 4, 'Y')))
    return obs


def zampa_drago(prefisso, anca, ginocchio, caviglia, piede, r, mat, m_artigli, artigli=3, tondi=False, avanti=None):
    """Zampa con coscia, stinco, piede e artigli (a punta o tondi)."""
    pts = [V(anca), V(ginocchio), V(caviglia), V(piede)]
    DS.leg(prefisso, pts, [r, r * 0.8, r * 0.65, r * 0.55], mat, joint_mat=mat, joint_r=r * 0.85)
    f = pts[-1]
    fw = V(avanti) if avanti is not None else V((pts[-1].x - pts[-2].x, pts[-1].y - pts[-2].y, 0.0))
    if fw.length < 1e-4:
        fw = V((0, -1, 0))
    fw.z = 0
    fw.normalize()
    sd = V((fw.y, -fw.x, 0))
    CL.sphere(prefisso + "_Palmo", f, (r * 0.9, r * 0.9, r * 0.5), mat, seg=12, rings=6)
    for k in range(artigli):
        o = (k - (artigli - 1) / 2) / max(1, artigli - 1)
        a = f + fw * r * 0.6 + sd * o * r * 1.4
        b = a + fw * r * 1.1 + V((0, 0, -r * 0.35))
        if tondi:
            CL.tube("%s_Dito_%d" % (prefisso, k), [f, a, b], [r * 0.35, r * 0.3, r * 0.28], mat, bevel_res=1)
            CL.sphere("%s_Artiglio_%d" % (prefisso, k), b + fw * r * 0.2, r * 0.3, m_artigli, seg=10, rings=5)
        else:
            CL.tube("%s_Dito_%d" % (prefisso, k), [f, a], [r * 0.35, r * 0.28], mat, bevel_res=1)
            CL.cone_between("%s_Artiglio_%d" % (prefisso, k), a, b, r * 0.25, 0.0, m_artigli, 6)


def piume_lungo(prefisso, pts, rad, frames, meshes, t0, t1, passi, angoli, scala=1.0, alza=0.95, seed=0):
    """Piume istanziate lungo il corpo (Instance on Points + Align Euler):
    ogni piuma giace sulla superficie e punta verso la coda."""
    rnd = random.Random(seed)
    k = 0
    for i in range(passi):
        t = t0 + (t1 - t0) * i / max(1, passi - 1)
        for a in angoli:
            p, d, tg = punto(pts, rad, frames, t, a + rnd.uniform(-6, 6), alza)
            ob = bpy.data.objects.new("%s_%03d" % (prefisso, k), rnd.choice(meshes))
            CL.link(ob)
            M = CL.frame_matrix(p, tg, d) @ Matrix.Rotation(radians(12), 4, 'X')
            s = scala * rnd.uniform(0.85, 1.1) * (0.6 + 0.4 * sin(pi * min(1.0, 0.2 + t)))
            ob.matrix_world = M @ Matrix.Diagonal((s, s, s, 1.0))
            k += 1
    return k


# ============================================================================
# 01  TESORINO, IL DRAGO CUSTODE
# ============================================================================

def build_tesorino():
    DS.texspace("Tesorino")
    oro = 3000
    m_sq = m_squame("Tesorino_Squame", (0.12, 0.09, 0.04), (0.9, 0.62, 0.22), film=420.0, luce_ventre=oro, forza=40.0)
    m_moneta = CL.m_body("Tesorino_Monete_Oro", (1.0, 0.72, 0.28), rough=0.2, metal=1.0, bump=(80.0, 0.2, 'noise'))
    m_corna = chitina("Tesorino_Corna", (0.3, 0.22, 0.12), rough=0.3, metal=0.4)
    m_lanterna = ST.m_luce("Tesorino_Lanternino_Coda", oro, 40.0, bordo=(1.0, 0.95, 0.8), forza_bordo=60.0)
    m_mem = chitina("Tesorino_Ali_Ripiegate", (0.18, 0.12, 0.05), rough=0.5, sss=0.3, sss_radius=(1.0, 0.6, 0.2))
    m_mem["rbx_thick"] = 1
    m_gemme = [ST.m_vetro("Tesorino_Rubino", (1.0, 0.1, 0.15), ior=1.7, bordo=(1.0, 0.2, 0.2), forza_bordo=2.0),
               ST.m_vetro("Tesorino_Smeraldo", (0.1, 1.0, 0.4), ior=1.6, bordo=(0.2, 1.0, 0.4), forza_bordo=2.0)]
    rr = {0.0: 0.1, 0.12: 0.16, 0.3: 0.175, 0.55: 0.14, 1.0: 0.02}
    ks = sorted(rr)

    def raggio(t):
        for a, b in zip(ks, ks[1:]):
            if t <= b:
                return rr[a] + (rr[b] - rr[a]) * (t - a) / (b - a)
        return rr[ks[-1]]

    ctrl = []
    for i in range(14):
        t = i / 13
        th = radians(250 - 410 * t)
        R = 0.47 - 0.21 * t
        ctrl.append(V((R * cos(th), 0.05 + R * sin(th), raggio(t) * 0.82 + 0.005)))
    body, pts, rad, frames = corpo("Tesorino_Corpo", ctrl, raggio, m_sq, n=60, ring=20, squash=0.85)
    # testa che dorme appoggiata a terra (occhi chiusi)
    tg0 = frames[0][0]
    hd = -tg0
    hd.z = 0
    hd.normalize()
    hp = pts[0] + hd * 0.2 + V((0, 0, -0.02))
    hp.z = 0.1
    master = testa_drago(m_sq, m_corna, m_corna, occhi='chiusi', corna='dritte', muso=0.2, largo=0.08)
    ST.istanze(master, [ST.frame(hp, hd)], "Tesorino_Testa")
    CL.tube("Tesorino_Collo", [pts[0] - tg0 * 0.02, pts[0].lerp(hp, 0.5) + V((0, 0, 0.02)), hp + hd * 0.02],
            [0.1, 0.09, 0.075], m_sq, bevel_res=3)
    # scaglie a forma di monetina sul dorso (istanze di un cilindro schiacciato)
    coin = ST.moneta_mesh("Tesorino_Moneta", 0.03, 0.006, m_moneta, seg=14)
    coin.matrix_world = Matrix.Identity(4)
    mats = []
    for i in range(38):
        t = 0.04 + 0.6 * i / 37
        for a in (-38, 0, 38):
            p, d, tg = punto(pts, rad, frames, t, a + (12 if i % 2 else -12) * (a == 0), 0.98)
            M = CL.frame_matrix(p, tg, d) @ Matrix.Rotation(radians(-18), 4, 'X')
            s = 0.75 + 0.5 * raggio(t) / 0.175
            mats.append(M @ Matrix.Diagonal((s, s, 1.0, 1.0)))
    ST.istanze([coin], mats, "Tesorino_Scaglia")
    # la pila di monete abbracciata dalla coda, con un calice e due gemme
    coin2 = ST.moneta_mesh("Tesorino_Moneta_Pila", 0.032, 0.007, m_moneta, seg=16)
    rnd = random.Random(21)
    mats = []
    for i in range(70):
        r = 0.17 * math.sqrt(rnd.random())
        a = rnd.uniform(0, TAU)
        z = 0.004 + (0.15 * (1 - r / 0.17)) * rnd.uniform(0.1, 1.0)
        M = Matrix.Translation((r * cos(a), 0.05 + r * sin(a), z)) @ Matrix.Rotation(rnd.uniform(-0.5, 0.5), 4, 'X') @ \
            Matrix.Rotation(rnd.uniform(-0.5, 0.5), 4, 'Y')
        mats.append(M)
    ST.istanze([coin2], mats, "Tesorino_Tesoro")
    calice = DS.lathe("Tesorino_Calice", [(0.045, 0.0), (0.04, 0.008), (0.008, 0.02), (0.008, 0.07), (0.03, 0.09),
                                          (0.05, 0.13), (0.052, 0.16), (0.048, 0.16), (0.044, 0.13)], m_moneta, seg=24,
                      cap_bottom=True)
    calice.location = (0.05, 0.08, 0.1)
    calice.rotation_euler = (radians(15), radians(8), 0)
    for i, (x, y) in enumerate(((-0.07, 0.03), (0.02, -0.04))):
        g = CL.sphere("Tesorino_Gemma_%d" % i, (x, 0.05 + y, 0.13), 0.025, m_gemme[i], seg=6, rings=4)
        g.rotation_euler = (0.4, 0.2 * i, 0.3)
    # lanternino sotto la coda
    lp, _d, _t = punto(pts, rad, frames, 0.58, 180, 0.9)
    lan = CL.sphere("Tesorino_Lanternino", lp + V((0, 0, 0.01)), (0.05, 0.05, 0.03), m_lanterna, seg=16, rings=8)
    ST.proxy(lan, lp + V((0, 0, 0.06)), oro, 8.0, nome="Tesorino_Luce_Lanternino")
    ST.proxy(body, (0, 0.05, 0.35), oro, 25.0, nome="Tesorino_Luce_Tesoro")
    # zampe rannicchiate e ali ripiegate sul dorso
    for t, sx in ((0.1, 1), (0.1, -1), (0.46, 1), (0.46, -1)):
        p, d, tg = punto(pts, rad, frames, t, 90 * sx, 0.8)
        knee = p + d * 0.08 + V((0, 0, -0.05))
        foot = knee + tg * -0.12 + V((0, 0, -0.06))
        foot.z = 0.02
        zampa_drago("Tesorino_Zampa_%s%d" % (side_name(sx), int(t * 10)), p, knee, knee.lerp(foot, 0.6), foot, 0.045, m_sq,
                    m_corna, artigli=3, avanti=-tg)
    for sx in (-1, 1):
        p, d, tg = punto(pts, rad, frames, 0.22, 40 * sx, 1.0)
        tips = [p + tg * 0.35 + d * 0.05 + V((0, 0, 0.02)), p + tg * 0.32 + d * 0.12, p + tg * 0.25 + d * 0.16]
        mem, ossa = ST.ala_membrana("Tesorino_Ala_%s" % side_name(sx), p, p + tg * 0.12 + V((0, 0, 0.05)),
                                    p + tg * 0.2 + V((0, 0, 0.06)), tips, p + tg * 0.18 + d * 0.15, m_mem, m_corna,
                                    sacca=0.1, gonfia=0.02, righe=3, colonne=2, r_osso=0.01)


# ============================================================================
# 02  PERLA, IL DRAGO CINESE LONG
# ============================================================================

def build_long():
    DS.texspace("Long")
    acqua = 9500
    m_sq = m_squame("Long_Squame_Giada", (0.05, 0.32, 0.18), (0.85, 0.75, 0.45), film=450.0, lung=20.0)
    m_pelle = chitina("Long_Muso_Giada", (0.06, 0.35, 0.2), film=450.0)
    m_corna = chitina("Long_Corna_Oro", (0.8, 0.55, 0.2), metal=0.6, rough=0.3)
    m_occhi = CL.m_body("Long_Occhi_Coniglio", (0.5, 0.03, 0.05), rough=0.08, coat=1.0)
    m_criniera = CL.m_body("Long_Criniera", (0.9, 0.3, 0.08), rough=0.6, sheen=1.0, sss=0.2)
    m_pearl = m_perla("Long_Perla_Fiammeggiante", acqua, 90.0)
    m_fiamme = ST.m_luce("Long_Fiamme_Perla", ST.mescola(acqua, (0.6, 0.9, 1.0), 0.5), 40.0, alpha=0.7)
    m_gocce = ST.m_luce("Long_Gocce_Pioggia", ST.mescola(acqua, (0.7, 0.95, 1.0), 0.5), 30.0)
    m_denti = CL.m_body("Long_Denti", (0.95, 0.92, 0.85), rough=0.2)
    m_bocca = CL.m_body("Long_Bocca", (0.3, 0.02, 0.03), rough=0.4)

    def raggio(t):
        if t < 0.12:
            return 0.08 + 0.3 * t
        return max(0.022, 0.116 * (1.0 - ((t - 0.12) / 0.88) ** 1.6))

    ctrl = []
    for i in range(16):
        t = i / 15
        ctrl.append(V((-1.05 + 2.4 * t, 0.2 * sin(TAU * 1.2 * t + 0.4), 0.95 + 0.26 * sin(TAU * t + 1.4) - 0.3 * t)))
    body, pts, rad, frames = corpo("Long_Corpo", ctrl, raggio, m_sq, n=80, ring=18)
    tg0 = frames[0][0]
    fwd = (-tg0 + V((0, 0, -0.25))).normalized()
    hp = pts[0] + fwd * 0.14
    master = testa_drago(m_pelle, m_occhi, m_corna, m_bocca, m_denti, muso=0.24, largo=0.085, corna='cervo',
                         bocca=14.0, baffi=0.55, m_baffi=m_corna)
    ST.istanze(master, [ST.frame(hp, fwd)], "Long_Testa")
    # criniera e cresta dorsale
    for i in range(26):
        t = 0.02 + 0.9 * i / 25
        p, d, tg = punto(pts, rad, frames, t, 0, 0.9)
        h = 0.07 * (1.0 - 0.6 * t)
        CL.cone_between("Long_Cresta_%02d" % i, p, p + d * h - tg * h * 0.6, h * 0.35, 0.0,
                        m_criniera if t < 0.2 else m_corna, 6)
    for i in range(10):
        t = 0.0 + 0.12 * i / 9
        for a in (-60, 60):
            p, d, tg = punto(pts, rad, frames, t, a, 0.95)
            CL.cone_between("Long_Criniera_%d%s" % (i, "AB"[a > 0]), p, p + d * 0.1 - tg * 0.12, 0.022, 0.0,
                            m_criniera, 6)
    tp = pts[-1]
    for k in range(7):
        a = TAU * k / 7
        CL.cone_between("Long_Ciuffo_Coda_%d" % k, tp - frames[0][-1] * 0.03, tp + frames[0][-1] * 0.16 +
                        V((0.05 * cos(a), 0.05 * sin(a), 0.03 * sin(a))), 0.02, 0.0, m_criniera, 6)
    # quattro zampe con cinque artigli tondi
    for t in (0.2, 0.6):
        for sx in (-1, 1):
            p, d, tg = punto(pts, rad, frames, t, 110 * sx, 0.7)
            knee = p + d * 0.1 + V((0, 0, -0.08)) - tg * 0.03
            ank = knee + V((0, 0, -0.12)) + tg * 0.06
            foot = ank + tg * -0.05 + V((0, 0, -0.04)) + d * 0.02
            zampa_drago("Long_Zampa_%s%d" % (side_name(sx), int(t * 10)), p, knee, ank, foot, 0.035, m_pelle,
                        m_corna, artigli=5, tondi=True, avanti=-tg)
    # la perla fiammeggiante che galleggia sotto il mento
    pc = hp + fwd * 0.2 + V((0, 0, -0.22))
    pearl = CL.sphere("Long_Perla", pc, 0.075, m_pearl, seg=28, rings=14)
    ST.proxy(pearl, pc + V((0, -0.1, 0.05)), acqua, 15.0, nome="Long_Luce_Perla")
    for k in range(6):
        a = TAU * k / 6
        b = pc + V((0.07 * cos(a), 0.07 * sin(a), 0.02))
        ST.cono_piatto("Long_Fiamma_Perla_%d" % k, b, b + V((0.05 * cos(a), 0.05 * sin(a), 0.1)), 0.025, m_fiamme,
                       0.4, avanti=(cos(a), sin(a), 0))
    # goccioline di luce lungo i baffi
    bpy.context.view_layer.update()
    for o in bpy.data.objects:
        if o.name.startswith("Long_Testa") and "Baffo" in o.name:
            sp = o.data.splines[0]
            mw = o.matrix_world
            for k, bp in enumerate(sp.bezier_points[1:]):
                CL.sphere("%s_Goccia_%d" % (o.name, k), mw @ bp.co + V((0, 0, -0.015)), 0.008, m_gocce, seg=8, rings=4)


# ============================================================================
# 03  MAREA, IL RE DRAGO RYUJIN
# ============================================================================

def build_ryujin():
    DS.texspace("Ryujin")
    m_sq = m_squame("Ryujin_Squame_Verde_Mare", (0.03, 0.3, 0.3), (0.75, 0.85, 0.75), film=380.0, lung=16.0,
                    macchie=(0.02, 0.15, 0.25))
    m_pelle = chitina("Ryujin_Muso", (0.04, 0.32, 0.32), film=380.0)
    m_schiuma = CL.m_body("Ryujin_Criniera_Onda", (0.75, 0.92, 0.95), rough=0.35, sss=0.6, sss_radius=(0.5, 0.9, 1.0),
                          coat=0.6)
    m_onda = CL.m_body("Ryujin_Criniera_Blu", (0.05, 0.3, 0.6), rough=0.3, sss=0.4, coat=0.6)
    m_corna = chitina("Ryujin_Corna", (0.8, 0.75, 0.6), rough=0.3)
    m_occhi = ST.m_luce("Ryujin_Occhi", (1.0, 0.8, 0.2), 30.0)
    m_denti = CL.m_body("Ryujin_Denti", (0.95, 0.92, 0.85), rough=0.2)
    m_bocca = CL.m_body("Ryujin_Bocca", (0.25, 0.02, 0.05), rough=0.4)
    gioielli = [(12000, ST.mescola(12000, (0.05, 0.2, 1.0), 0.6), "Kanju"), (7000, (0.95, 0.98, 1.0), "Manju")]
    ctrl = []
    for i in range(12):
        t = i / 11
        th = TAU * 1.25 * t
        R = 0.44 - 0.12 * t
        ctrl.append(V((R * cos(th), R * sin(th), 0.1 + 0.62 * t ** 1.15)))
    ctrl += [V((0.12, -0.3, 0.95)), V((0.02, -0.28, 1.2)), V((0.0, -0.2, 1.38))]

    def raggio(t):
        return 0.02 + 0.09 * min(1.0, t / 0.35) - 0.015 * max(0.0, (t - 0.85) / 0.15)

    body, pts, rad, frames = corpo("Ryujin_Corpo", ctrl, raggio, m_sq, n=90, ring=18)
    tgE = frames[0][-1]
    fwd = (V((0, -1, -0.35))).normalized()
    hp = pts[-1] + tgE * 0.05 + fwd * 0.1
    master = testa_drago(m_pelle, m_occhi, m_corna, m_bocca, m_denti, muso=0.22, largo=0.085, corna='dritte',
                         bocca=18.0, baffi=0.45, m_baffi=m_schiuma)
    ST.istanze(master, [ST.frame(hp, fwd)], "Ryujin_Testa")
    # criniera a onde che si arricciano (Curve + Simple Deform)
    for i in range(16):
        t = 0.45 + 0.52 * i / 15
        p, d, tg = punto(pts, rad, frames, t, 0, 0.85)
        h = 0.14 + 0.05 * sin(i)
        back = -tg
        pts_c = [p, p + d * h * 0.5 + back * h * 0.2, p + d * h + back * h * 0.55]
        c = pts_c[-1]
        for k in range(1, 6):
            a = k * 0.9
            pts_c.append(c + back * h * 0.3 * sin(a) + d * h * 0.3 * (cos(a) - 1) * (1 - 0.1 * k))
        CL.tube("Ryujin_Onda_%02d" % i, pts_c, [0.025, 0.022, 0.018, 0.014, 0.01, 0.008, 0.005, 0.002],
                m_schiuma if i % 2 else m_onda, bevel_res=2)
    # zampe a tre artigli; le anteriori stringono i due gioielli delle maree
    for t, sx, k in ((0.86, 1, 0), (0.86, -1, 1), (0.3, 1, None), (0.3, -1, None)):
        p, d, tg = punto(pts, rad, frames, t, 100 * sx, 0.7)
        if k is not None:
            knee = p + d * 0.12 + fwd * 0.05
            ank = knee + fwd * 0.12 + V((0, 0, -0.05))
            foot = ank + fwd * 0.05
        else:
            knee = p + d * 0.1 + V((0, 0, -0.04))
            ank = knee + V((0, 0, -0.06)) + d * 0.03
            foot = ank + d * 0.04
            foot.z = max(0.02, foot.z)
        zampa_drago("Ryujin_Zampa_%s%d" % (side_name(sx), int(t * 10)), p, knee, ank, foot, 0.032, m_pelle, m_corna,
                    artigli=3, avanti=fwd if k is not None else d)
        if k is not None:
            K, col, nome = gioielli[k]
            gp = foot + fwd * 0.05 + V((0, 0, -0.01))
            core = CL.sphere("Ryujin_Gioiello_%s" % nome, gp, 0.04, ST.m_luce("Ryujin_%s_Luce" % nome, col, 70.0,
                                                                              bordo=(1, 1, 1), forza_bordo=90.0),
                             seg=20, rings=10)
            shell = CL.sphere("Ryujin_Gioiello_%s_Guscio" % nome, gp, 0.05,
                              ST.m_vetro("Ryujin_%s_Vetro" % nome, ST.mescola(col, (1, 1, 1), 0.6), ior=1.3), seg=24,
                              rings=12)
            CL.no_shadow(shell)
            ST.proxy(core, gp + V((0, -0.08, 0.05)), col, 10.0, nome="Ryujin_Luce_%s" % nome)


# ============================================================================
# 04  QUETZAL, IL SERPENTE PIUMATO
# ============================================================================

def build_quetzal():
    DS.texspace("Quetzal")
    sm, tu = (0.05, 0.9, 0.35), (0.1, 0.85, 0.85)
    m_sq = m_squame("Quetzal_Squame", (0.02, 0.28, 0.12), (0.85, 0.7, 0.3), film=520.0, lung=18.0,
                    triangoli=((sm, tu), 40.0, 0.22, 0.78, 7))
    m_piuma = CL.m_feather("Quetzal_Piume_Smeraldo", (0.02, 0.3, 0.12), (0.03, 0.45, 0.4), (0.15, 1.0, 0.7), 40.0,
                           edge_w=0.1, rachis_w=0.04)
    ST._principled_extra(m_piuma, film=520.0)
    m_piuma["rbx_thick"] = 1
    m_coda = CL.m_feather("Quetzal_Piume_Coda", (0.02, 0.35, 0.2), (0.05, 0.55, 0.55), (0.2, 1.0, 0.9), 40.0,
                          edge_w=0.08, rachis_w=0.04)
    ST._principled_extra(m_coda, film=600.0)
    m_coda["rbx_thick"] = 1
    m_pelle = chitina("Quetzal_Testa", (0.03, 0.3, 0.14), film=520.0)
    m_occhi = ST.m_luce("Quetzal_Occhi", (1.0, 0.75, 0.1), 30.0)
    m_denti = CL.m_body("Quetzal_Zanne", (0.95, 0.92, 0.85), rough=0.2)
    m_bocca = CL.m_body("Quetzal_Bocca", (0.4, 0.03, 0.05), rough=0.4)
    m_rossa = CL.m_body("Quetzal_Petto_Rosso", (0.7, 0.05, 0.05), rough=0.5, sheen=0.8)
    ctrl = [V((0.35, 0.45, 0.05)), V((0.47, 0.1, 0.07)), V((0.3, -0.22, 0.09)), V((-0.05, -0.32, 0.1)),
            V((-0.36, -0.12, 0.1)), V((-0.36, 0.24, 0.1)), V((-0.1, 0.36, 0.12)), V((0.06, 0.16, 0.3)),
            V((0.06, -0.04, 0.55)), V((-0.02, -0.14, 0.8)), V((0.0, -0.22, 0.95))]

    def raggio(t):
        return 0.025 + 0.085 * min(1.0, t / 0.3) - 0.02 * max(0.0, (t - 0.8) / 0.2)

    body, pts, rad, frames = corpo("Quetzal_Corpo", ctrl, raggio, m_sq, n=90, ring=18)
    fwd = V((0, -1, -0.15)).normalized()
    hp = pts[-1] + frames[0][-1] * 0.06
    master = testa_drago(m_pelle, m_occhi, m_pelle, m_bocca, m_denti, muso=0.16, largo=0.07, corna=None, bocca=22.0,
                         orecchie=False)
    ST.istanze(master, [ST.frame(hp, fwd)], "Quetzal_Testa")
    # piume istanziate lungo il corpo (dorso e fianchi)
    meshes = [CL.feather_mesh("Quetzal_Piuma_%d" % i, 0.12 + 0.02 * i, 0.05, m_piuma, rows=6, cols=3, curl=0.1)
              for i in range(3)]
    piume_lungo("Quetzal_Piuma", pts, rad, frames, meshes, 0.08, 0.95, 36, (-75, -38, 0, 38, 75), scala=1.0, seed=3)
    # coda a ventaglio di lunghe piume
    tail = pts[0]
    lunghe = [CL.feather_mesh("Quetzal_Penna_%d" % i, 0.55 + 0.08 * i, 0.07, m_coda, rows=10, cols=4, curl=0.05)
              for i in range(3)]
    t0 = -frames[0][0]
    for k in range(7):
        a = radians(-45 + 15 * k)
        d = (t0 * cos(a) + V((0, 0, 1)) * sin(a) * 0.9 + V((0, 0, 0.3))).normalized()
        ob = bpy.data.objects.new("Quetzal_Coda_%d" % k, lunghe[k % 3])
        CL.link(ob)
        ob.matrix_world = CL.frame_matrix(tail, d, t0.cross(V((0, 0, 1))).normalized())
    ST.proxy(body, tail + t0 * 0.3 + V((0, 0, 0.3)), 6500, 10.0, nome="Quetzal_Luce_Coda")
    # due grandi ali di piume, come un mantello, e il collare
    for sx in (-1, 1):
        p, d, tg = punto(pts, rad, frames, 0.78, 80 * sx, 0.9)
        for k in range(8):
            a = radians(-10 + 13 * k)
            dd = (d * cos(a) + V((0, 0, 1)) * sin(a) * 0.8 - tg * 0.4).normalized()
            ob = bpy.data.objects.new("Quetzal_Ala_%s%d" % (side_name(sx), k), lunghe[k % 3])
            CL.link(ob)
            s = 0.75 + 0.03 * k
            ob.matrix_world = CL.frame_matrix(p, dd, tg) @ Matrix.Diagonal((s, s, s, 1.0))
    for k in range(12):
        a = 360 * k / 12
        p, d, tg = punto(pts, rad, frames, 0.9, a, 0.95)
        ob = bpy.data.objects.new("Quetzal_Collare_%02d" % k, meshes[k % 3])
        CL.link(ob)
        ob.matrix_world = CL.frame_matrix(p, (d * 0.8 - tg * 0.5).normalized(), tg)
    CL.sphere("Quetzal_Gola", pts[-6], (0.09, 0.07, 0.09), m_rossa, seg=16, rings=8)
    # cresta di piume sul capo
    for k in range(5):
        b = hp + V(((k - 2) * 0.02, 0.03, 0.06))
        d = V(((k - 2) * 0.15, 0.4, 1.0)).normalized()
        ob = bpy.data.objects.new("Quetzal_Cresta_%d" % k, meshes[k % 3])
        CL.link(ob)
        ob.matrix_world = CL.frame_matrix(b, d, V((0, -1, 0.2))) @ Matrix.Diagonal((1.2, 1.2, 1.2, 1.0))
    for k in range(3):
        p, d, tg = punto(pts, rad, frames, 0.3 + 0.2 * k, 90, 1.3)
        ST.proxy(body, p, ST.mescola(sm, tu, 0.5), 4.0, nome="Quetzal_Luce_Triangoli_%d" % k)


# ============================================================================
# 05  DDRAIG, IL DRAGO ROSSO GALLESE
# ============================================================================

def build_ddraig():
    DS.texspace("Ddraig")
    rosso = 2200
    m_pelle = chitina("Ddraig_Scaglie_Rosse", (0.5, 0.03, 0.02), film=300.0, bump=(60.0, 0.4, 'scales'))
    m_petto = ST.m_luce("Ddraig_Petto_Rosso", ST.mescola(rosso, (1.0, 0.1, 0.03), 0.5), 70.0, bordo=rosso,
                        forza_bordo=90.0)
    m_mem = CL.m_body("Ddraig_Membrana_Ali", (0.3, 0.02, 0.02), rough=0.5, sss=0.5, sss_radius=(1.0, 0.2, 0.1),
                      coat=0.2)
    m_mem["rbx_thick"] = 1
    m_ossa = chitina("Ddraig_Ossa_Ali", (0.35, 0.02, 0.01))
    m_bianco = ST.m_luce("Ddraig_Fratello_Bianco", (1.0, 1.0, 1.0), 20.0)
    m_coda = ST.m_luce("Ddraig_Coda_Brace", rosso, 70.0, bordo=(1.0, 0.8, 0.4), forza_bordo=90.0)
    m_corna = chitina("Ddraig_Corna", (0.85, 0.8, 0.7), rough=0.3)
    m_occhi = ST.m_luce("Ddraig_Occhi", (1.0, 0.7, 0.1), 40.0)
    m_bocca = CL.m_body("Ddraig_Bocca", (0.3, 0.01, 0.02), rough=0.4)
    m_lingua = CL.m_body("Ddraig_Lingua", (0.8, 0.1, 0.15), rough=0.3, sss=0.4)
    m_denti = CL.m_body("Ddraig_Denti", (0.95, 0.92, 0.85), rough=0.2)
    m_torre = m_pietra("Ddraig_Torre_Pietra")
    m_buio = CL.m_body("Ddraig_Porta", (0.01, 0.008, 0.006), rough=0.9)
    E = [el((0, 0.0, 0.55), 0.2, (0.9, 1.4, 0.85)), el((0, -0.28, 0.63), 0.17, (1.0, 0.9, 1.0)),
         el((0, 0.3, 0.55), 0.16, (1.0, 1.0, 0.9)), cap((0, -0.38, 0.7), (0, -0.52, 0.95), 0.09),
         cap((0, -0.52, 0.95), (0, -0.58, 1.08), 0.075)]
    CL.metaball_mesh("Ddraig_Corpo", E, m_pelle, res=0.016)
    chest = CL.sphere("Ddraig_Petto", (0, -0.36, 0.56), (0.13, 0.08, 0.16), m_petto, rot=(-25, 0, 0), seg=24, rings=12)
    ST.proxy(chest, (0, -0.6, 0.55), rosso, 25.0, nome="Ddraig_Luce_Petto")
    fwd = V((0, -1, -0.1)).normalized()
    hp = V((0, -0.66, 1.12))
    master = testa_drago(m_pelle, m_occhi, m_corna, m_bocca, m_denti, muso=0.2, largo=0.08, corna='dritte', bocca=26.0)
    ST.istanze(master, [ST.frame(hp, fwd)], "Ddraig_Testa")
    lt = [hp + V((0, -0.08, -0.05)), hp + V((0, -0.2, -0.1)), hp + V((0, -0.3, -0.08))]
    CL.tube("Ddraig_Lingua", lt, [0.014, 0.01, 0.006], m_lingua, bevel_res=1)
    for sx in (-1, 1):
        CL.tube("Ddraig_Lingua_Punta_" + side_name(sx), [lt[-1], lt[-1] + V((0.035 * sx, -0.06, 0.02))], [0.006, 0.001],
                m_lingua, bevel_res=1)
    # zampe: una anteriore alzata (posa araldica), artigli tondi
    legs = [((0.14, -0.3, 0.5), (0.24, -0.46, 0.55), (0.22, -0.58, 0.5), (0.2, -0.66, 0.44)),
            ((-0.14, -0.3, 0.5), (-0.2, -0.38, 0.28), (-0.2, -0.42, 0.1), (-0.2, -0.5, 0.02)),
            ((0.15, 0.3, 0.48), (0.24, 0.2, 0.28), (0.22, 0.36, 0.1), (0.22, 0.28, 0.02)),
            ((-0.15, 0.3, 0.48), (-0.24, 0.24, 0.28), (-0.22, 0.4, 0.1), (-0.22, 0.32, 0.02))]
    for i, (a, k, c, f) in enumerate(legs):
        zampa_drago("Ddraig_Zampa_%d" % i, a, k, c, f, 0.05, m_pelle, m_corna, artigli=3, tondi=True,
                    avanti=(0, -1, 0))
    # ali membranose alzate, con la rete delle nervature (Wireframe) e i puntini bianchi
    S, Eb, W = V((0.12, -0.12, 0.72)), V((0.4, -0.05, 1.0)), V((0.58, -0.12, 1.3))
    tips = [V((0.9, -0.3, 1.55)), V((1.08, 0.05, 1.3)), V((1.0, 0.35, 0.98)), V((0.7, 0.45, 0.75))]
    mem, ossa = ST.ala_membrana("Ddraig_Ala", S, Eb, W, tips, V((0.12, 0.2, 0.65)), m_mem, m_ossa, sacca=0.2,
                                gonfia=0.05, righe=7, colonne=5, r_osso=0.018, artiglio=m_corna)
    rete = CL.mesh_object("Ddraig_Rete_R", _copia(mem), m_ossa, smooth=False)
    wf = rete.modifiers.new("Rete_Wireframe", 'WIREFRAME')
    wf.thickness = 0.005
    rete["rbx_drop"] = 1
    rnd = random.Random(5)
    punti = []
    bpy.context.view_layer.update()
    vs = [mem.matrix_world @ v.co for v in mem.data.vertices]
    for i in range(14):
        p = rnd.choice(vs)
        punti.append(CL.sphere("Ddraig_Puntino_%02d_R" % i, p + V((0, 0, 0.012)), 0.012, m_bianco, seg=8, rings=4))
    lat = ST.specchia_x([mem, rete] + ossa + punti)
    for o in lat:
        if o.name.startswith("Ddraig_Rete"):
            o["rbx_drop"] = 1
    ST.proxy(punti[0], (0.8, 0.2, 1.4), (1, 1, 1), 3.0, nome="Ddraig_Luce_Fratello_Bianco")
    # coda a ricciolo con la punta a picca incandescente
    tail = DS.spline([V((0, 0.4, 0.5)), V((0, 0.75, 0.35)), V((0.15, 1.0, 0.3)), V((0.3, 0.95, 0.55)),
                      V((0.15, 0.8, 0.65)), V((0.05, 0.9, 0.78))], 30)
    CL.tube("Ddraig_Coda", tail, [0.08 - 0.0023 * i for i in range(30)], m_pelle, bevel_res=2)
    d = (tail[-1] - tail[-2]).normalized()
    punta = OC.fin_mesh("Ddraig_Punta_Coda", [(0.0, -0.02), (0.02, -0.07), (0.13, 0.0), (0.02, 0.07), (0.0, 0.02)],
                        0.02, m_coda, CL.frame_matrix(tail[-1], d.cross(V((1, 0, 0))), V((1, 0, 0))) @
                        Matrix.Rotation(-pi / 2, 4, 'Z'))
    ST.proxy(punta, tail[-1] + d * 0.12, rosso, 6.0, nome="Ddraig_Luce_Coda")
    # la torre di Vortigern sul dorso
    T = V((0, 0.08, 0.74))
    tower = DS.lathe("Ddraig_Torre", [(0.1, 0.0), (0.095, 0.2), (0.105, 0.21), (0.105, 0.24), (0.07, 0.24)], m_torre,
                     seg=24, cap_bottom=True, cap_top=True)
    tower.location = T
    for k in range(8):
        a = TAU * k / 8
        DS.box("Ddraig_Merlo_%d" % k, T + V((0.095 * cos(a), 0.095 * sin(a), 0.265)), (0.035, 0.035, 0.05), m_torre,
               rot=(0, 0, math.degrees(a)))
    DS.box("Ddraig_Porta", T + V((0, -0.098, 0.05)), (0.05, 0.01, 0.09), m_buio)
    DS.box("Ddraig_Finestra", T + V((0.0, -0.096, 0.16)), (0.02, 0.01, 0.035), m_buio)


def _copia(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    return bm


# ============================================================================
# 06  IDRA, LA PICCOLA IDRA DI LERNA
# ============================================================================

def build_idra():
    DS.texspace("Idra")
    verde = ST.mescola(6000, (0.35, 1.0, 0.3), 0.6)
    oro = 3500
    m_pelle = CL.m_body("Idra_Pelle_Palude", (0.05, 0.16, 0.06), rough=0.3, coat=0.6, sss=0.2,
                        sss_radius=(0.3, 1.0, 0.3), mottle=((0.02, 0.07, 0.03), 7.0), bump=(50.0, 0.35, 'warts'))
    m_testa = chitina("Idra_Testine", (0.06, 0.2, 0.08), film=420.0)
    m_oro = chitina("Idra_Testa_Centrale_Oro", (0.75, 0.55, 0.15), metal=0.6, film=380.0)
    m_luce = ST.m_luce("Idra_Luci_Fronte", verde, 40.0)
    m_luce_oro = ST.m_luce("Idra_Luce_Oro", oro, 60.0)
    m_occhi = CL.m_body("Idra_Occhi", (0.8, 0.6, 0.05), rough=0.1, coat=1.0)
    m_ninfea = CL.m_body("Idra_Code_Ninfea", (0.08, 0.35, 0.08), rough=0.4, coat=0.5, bump=(20.0, 0.3, 'noise'))
    m_ninfea["rbx_thick"] = 1
    m_fiore = CL.m_body("Idra_Fiore_Ninfea", (1.0, 0.75, 0.85), rough=0.4, sss=0.5)
    E = [el((0, 0.1, 0.24), 0.26, (1.1, 1.3, 0.62)), el((0, -0.15, 0.3), 0.2, (1.2, 0.9, 0.7))]
    CL.metaball_mesh("Idra_Corpo", E, m_pelle, res=0.016)
    # nove testine su nove colli a ventaglio (istanze della stessa testa)
    master = testa_drago(m_testa, m_occhi, m_testa, muso=0.1, largo=0.05, corna=None, orecchie=False)
    lamp = CL.sphere("Drago_Luce_Fronte", (0, -0.03, 0.05), (0.018, 0.012, 0.014), m_luce, seg=12, rings=6)
    master.append(lamp)
    mats, dati = [], []
    for i in range(9):
        f = (i - 4) / 4.0
        a = radians(-90 + 62 * f)
        L = 0.62 - 0.1 * abs(f)
        hp = V((L * cos(a) * 0.9, -0.2 + L * sin(a) * 0.85, 0.72 + 0.2 * (1 - abs(f)) ** 2 - 0.05 * abs(f)))
        d = V((cos(a) * 0.9, sin(a), -0.15)).normalized()
        s = 1.25 if i == 4 else 1.0
        mats.append(ST.frame(hp, d) @ Matrix.Diagonal((s, s, s, 1.0)))
        dati.append((hp, d, V((0.12 * f, -0.3, 0.38))))
    gruppi = ST.istanze(master, mats, "Idra_Testa")
    for i, (grp, (hp, d, b)) in enumerate(zip(gruppi, dati)):
        centrale = i == 4
        if centrale:
            for o in grp:
                if "Luce_Fronte" in o.name:
                    ST.materiale_oggetto(o, m_luce_oro)
                elif o.type == 'MESH' and o.data.materials and o.data.materials[0] == m_testa:
                    ST.materiale_oggetto(o, m_oro)
        tip = hp - d * 0.07 + V((0, 0, -0.03))
        mid = b.lerp(tip, 0.5) + V((0, 0, 0.12)) - d * 0.05
        CL.tube("Idra_Collo_%d" % i, [b, mid, tip], [0.06, 0.045, 0.04], m_oro if centrale else m_pelle, bevel_res=2)
        lampo = next(o for o in grp if "Luce_Fronte" in o.name)
        ST.proxy(lampo, hp + d * 0.1 + V((0, 0, 0.06)), oro if centrale else verde, 2.5 if not centrale else 5.0,
                 nome="Idra_Luce_Testa_%d" % i)
    # code a foglia di ninfea
    for k, x in enumerate((-0.14, 0.0, 0.14)):
        tail = [V((x * 0.5, 0.45, 0.2)), V((x, 0.65, 0.12)), V((x * 1.4, 0.82, 0.06))]
        CL.tube("Idra_Coda_%d" % k, tail, [0.05, 0.035, 0.02], m_pelle, bevel_res=2)
        pad = [(0.0, 0.0)] + [(0.13 * cos(a), 0.13 * sin(a)) for a in [radians(20 + 320 * i / 20) for i in range(21)]]
        OC.fin_mesh("Idra_Ninfea_%d" % k, pad, 0.008, m_ninfea,
                    CL.frame_matrix(tail[-1] + V((0, 0.12, -0.035)), V((0, 1, 0)), V((0.05 * k - 0.05, 0, 1))))
        if k == 1:
            for j in range(8):
                a = TAU * j / 8
                c = tail[-1] + V((0, 0.12, 0.0))
                p = CL.sphere("Idra_Petalo_%d" % j, (0, 0, 0), 1.0, m_fiore, seg=10, rings=5)
                p.matrix_world = CL.frame_matrix(c + V((0.02 * cos(a), 0.02 * sin(a), 0.02)), V((0, 0, 1)),
                                                 V((cos(a), sin(a), 0.8))) @ Matrix.Diagonal((0.015, 0.008, 0.04, 1))
    # zampette palmate
    for sx in (-1, 1):
        for i, y in enumerate((-0.12, 0.3)):
            a = V((0.22 * sx, y, 0.2))
            k = V((0.34 * sx, y - 0.02, 0.15))
            f = V((0.4 * sx, y - 0.06, 0.02))
            DS.leg("Idra_Zampa_%s%d" % (side_name(sx), i), [a, k, f], [0.045, 0.04, 0.03], m_pelle, joint_mat=m_pelle)
            web = [(0.0, 0.0)] + [(0.1 * cos(t), 0.1 * sin(t)) for t in [radians(-60 + 30 * j) for j in range(5)]]
            OC.fin_mesh("Idra_Palma_%s%d" % (side_name(sx), i), web, 0.006, m_ninfea,
                        CL.frame_matrix(f + V((0, 0, -0.012)), V((0, 1, 0)), V((0, 0, 1))) @
                        Matrix.Rotation(radians(-90 + (20 * sx)), 4, 'Z'))


# ============================================================================
# 07  BLASONE, IL WYVERN ARALDICO
# ============================================================================

def build_wyvern():
    DS.texspace("Wyvern")
    m_pelle = chitina("Wyvern_Scaglie", (0.12, 0.1, 0.18), film=420.0, bump=(60.0, 0.35, 'scales'))
    m_mem = CL.m_body("Wyvern_Membrana", (0.2, 0.12, 0.3), rough=0.5, sss=0.4, sss_radius=(0.6, 0.3, 1.0))
    m_mem["rbx_thick"] = 1
    m_corna = chitina("Wyvern_Corna_Artigli", (0.85, 0.75, 0.5), metal=0.5, rough=0.3)
    m_occhi = ST.m_luce("Wyvern_Occhi", (1.0, 0.8, 0.2), 40.0)
    m_bocca = CL.m_body("Wyvern_Bocca", (0.3, 0.02, 0.04), rough=0.4)
    m_denti = CL.m_body("Wyvern_Denti", (0.95, 0.92, 0.85), rough=0.2)
    m_freccia = m_smalti("Wyvern_Punta_Freccia_Smalti", 100.0, 0.0)
    m_or = CL.m_body("Wyvern_Scudo_Oro", (1.0, 0.72, 0.25), rough=0.25, metal=1.0)
    m_az = CL.m_body("Wyvern_Scudo_Azzurro", (0.05, 0.15, 0.7), rough=0.3, coat=0.8)
    E = [el((0, 0.08, 0.55), 0.15, (1.0, 1.1, 1.0)), el((0, 0.0, 0.8), 0.14, (1.05, 0.9, 1.2)),
         cap((0, -0.02, 0.92), (0, -0.1, 1.12), 0.07), cap((0, -0.1, 1.12), (0, -0.2, 1.24), 0.06)]
    for sx in (-1, 1):
        E += [cap((0.1 * sx, 0.1, 0.5), (0.18 * sx, -0.06, 0.36), 0.07), cap((0.18 * sx, -0.06, 0.36),
                                                                               (0.15 * sx, 0.1, 0.12), 0.05)]
    CL.metaball_mesh("Wyvern_Corpo", E, m_pelle, res=0.014)
    fwd = V((0, -1, -0.15)).normalized()
    hp = V((0, -0.3, 1.3))
    master = testa_drago(m_pelle, m_occhi, m_corna, m_bocca, m_denti, muso=0.18, largo=0.07, corna='cresta', bocca=20.0)
    ST.istanze(master, [ST.frame(hp, fwd)], "Wyvern_Testa")
    for sx in (-1, 1):
        s = side_name(sx)
        ank = V((0.15 * sx, 0.1, 0.12))
        foot = V((0.16 * sx, -0.02, 0.02))
        zampa_drago("Wyvern_Zampa_" + s, (0.18 * sx, -0.06, 0.36), ank, ank.lerp(foot, 0.5), foot, 0.045, m_pelle,
                    m_corna, artigli=3, avanti=(0.1 * sx, -1, 0))
    # le ali sono le zampe anteriori
    S, Eb, W = V((0.12, -0.02, 0.9)), V((0.4, 0.05, 1.12)), V((0.62, 0.0, 1.4))
    tips = [V((0.95, -0.15, 1.6)), V((1.1, 0.1, 1.3)), V((0.95, 0.3, 0.95)), V((0.65, 0.3, 0.7))]
    mem, ossa = ST.ala_membrana("Wyvern_Ala", S, Eb, W, tips, V((0.12, 0.12, 0.55)), m_mem, m_corna, sacca=0.2,
                                gonfia=0.05, righe=7, colonne=5, r_osso=0.016, artiglio=m_corna)
    ST.specchia_x([mem] + ossa)
    # coda con la punta a freccia
    tail = DS.spline([V((0, 0.2, 0.45)), V((0, 0.5, 0.2)), V((0.25, 0.75, 0.08)), V((0.45, 0.7, 0.2)),
                      V((0.5, 0.5, 0.35))], 26)
    CL.tube("Wyvern_Coda", tail, [0.06 - 0.002 * i for i in range(26)], m_pelle, bevel_res=2)
    d = (tail[-1] - tail[-2]).normalized()
    punta = CL.cone_between("Wyvern_Freccia", tail[-1] - d * 0.02, tail[-1] + d * 0.16, 0.07, 0.0, m_freccia, 4)
    ST.proxy(punta, tail[-1] + d * 0.25, 3000, 8.0, nome="Wyvern_Luce_Freccia")
    # scudetto sul petto (partito d'oro e d'azzurro)
    out = [(-0.08, 0.1), (0.08, 0.1), (0.08, 0.0), (0.05, -0.07), (0.0, -0.11), (-0.05, -0.07), (-0.08, 0.0)]
    for i, (poly, m) in enumerate(((out[:1] + [(0.0, 0.1), (0.0, -0.11)] + out[4:], m_or),
                                   ([(0.0, 0.1)] + out[1:5], m_az))):
        OC.fin_mesh("Wyvern_Scudo_%d" % i, poly, 0.014, m,
                    CL.frame_matrix(V((0, -0.14, 0.82)), V((0, 0.2, 1.0)), V((0, -1, 0.2))))


# ============================================================================
# 08  OUROBO' OUROBO', IL CIAMBELLINO DRACONICO
# ============================================================================

def build_ourobo():
    DS.texspace("Ourobo")
    C = V((0, 0, 0.72))
    R, r = 0.5, 0.15
    m_anello = m_anello_cromatico("Ourobo_Anello_Cromatico", C, 50.0)
    m_bianco = ST.m_occhio_bianco("Ourobo_Occhi_Bianchi")
    m_pup = CL.m_body("Ourobo_Pupille", (0.01, 0.01, 0.02), rough=0.05, coat=1.0)
    m_rifl = ST.m_luce("Ourobo_Riflessi", (1, 1, 1), 8.0)
    m_corna = CL.m_body("Ourobo_Sopracciglia", (0.1, 0.05, 0.15), rough=0.4)
    m_suola = CL.m_body("Ourobo_Suole", (0.97, 0.96, 0.94), rough=0.5)
    m_lacci = CL.m_body("Ourobo_Lacci", (1.0, 1.0, 1.0), rough=0.6)
    m_tomaia = CL.m_body("Ourobo_Sneakers", (0.35, 0.3, 0.95), rough=0.35, coat=0.3)
    m_acc = CL.m_body("Ourobo_Striscia", (1.0, 0.4, 0.7), rough=0.4)
    m_ala = ST.m_ala("Ourobo_Alucce", [(0.0, (1.0, 0.8, 0.95)), (1.0, (0.8, 0.95, 1.0))], alpha=0.15,
                     membrane_str=0.8, vein_ramp=[(0.0, (1.0, 0.6, 0.85)), (1.0, (0.6, 0.85, 1.0))], vein_str=6.0,
                     radial=(5, 0.07))
    # corpo a ciambella: parte dal collo e gira fino alla coda che entra in bocca
    n = 72
    a0, span = radians(72), radians(318)
    ctrl = [C + V((R * cos(a0 - span * i / (n - 1)), 0.0, R * sin(a0 - span * i / (n - 1)))) for i in range(n)]

    def raggio(t):
        return r if t < 0.72 else r - (r - 0.06) * ((t - 0.72) / 0.28)

    rad = [raggio(i / (n - 1)) for i in range(n)]
    DS.sweep_mesh("Ourobo_Corpo", ctrl, rad, m_anello, ring=CL.det(22, 8), squash=1.0)
    # testa da cartone che si morde la coda
    top = C + V((0, 0, R + 0.02))
    master = testa_drago(m_anello, None, m_corna, None, None, muso=0.2, largo=0.13, corna=None,
                         occhi=('cartone', m_bianco, m_pup, m_rifl), bocca=22.0, orecchie=True)
    ST.istanze(master, [ST.frame(top + V((0.08, 0, 0.05)), (-1.0, 0.0, -0.15))], "Ourobo_Testa")
    for i, a in enumerate((20, 140, 200, 260, 320)):
        p = C + V((0.5 * cos(radians(a)), -0.22, 0.5 * sin(radians(a))))
        ST.proxy(bpy.data.objects["Ourobo_Corpo"], p, (1.0, 0.7, 0.8) if i % 2 else (0.6, 0.85, 1.0), 4.0,
                 nome="Ourobo_Luce_Anello_%d" % i)
    # quattro zampette con le sneakers: ci rotola sopra come una ruota
    master = ST.sneaker("Ourobo_Scarpa", 0.2, m_tomaia, m_suola, m_lacci, m_acc)
    mats = []
    for a in (60, 120, 240, 300):
        d = V((cos(radians(a)), 0.0, sin(radians(a))))
        b = C + d * (R + r * 0.8)
        e = C + d * (R + r + 0.07)
        CL.tube("Ourobo_Zampetta_%d" % a, [b, e], [0.035, 0.03], m_anello, bevel_res=2)
        up = -d
        fw = V((0, -1, 0))
        z = up
        x = fw.cross(z).normalized() * -1
        M = Matrix((x, -fw, z)).transposed().to_4x4()
        M.translation = e + d * 0.09
        mats.append(M)
    ST.istanze(master, mats, "Ourobo_Scarpa")
    CL.wing_pair("Ourobo_Aletta", [(-10, 0.04), (0, 0.12), (15, 0.15), (30, 0.12), (42, 0.04)], m_ala,
                 C + V((0.02, 0.1, R + 0.1)), elev=30, sweep=80, roll=20, rings=4, n=24)


# ============================================================================
# SCENE DEI DRAGHI
# ============================================================================

def scena_gruppo(which):
    ST.mondo((0.004, 0.006, 0.012), (0.02, 0.03, 0.06), 1.0, nome="Cielo_Draghi")
    ST.pavimento("Terreno_Grotta", (0.03, 0.028, 0.025), (0.07, 0.065, 0.06), scala=0.5, rough=(0.6, 0.9))
    ST.nebbia("Foschia_Draghi", (0, 3, 1.6), (30, 30, 3.2), (0.7, 0.8, 1.0), 0.012)
    ST.luci_studio(which, chiave=6000, contro=(0.6, 0.7, 1.0), riempimento=3500)


def scena_tesorino():
    ST.luce("Luce_Calda_Dal_Basso", 'AREA', (0, -0.4, 0.05), 80.0, 3000, 1.5)


def scena_long():
    ST.nebbia("Nuvole_Blu", (0, 0.5, 1.0), (7, 6, 2), (0.6, 0.75, 1.0), 0.03)
    ST.compositor(0.4, 7, (4, 45.0, 0.2), 0.0)


def scena_ryujin():
    ST.nebbia("Volume_Azzurro", (0, 0, 1.0), (6, 6, 2), (0.4, 0.75, 1.0), 0.04)
    m = CL.new_material("Caustiche_Finte")
    nb = CL.NodeBuilder(m)
    tc = nb.texcoord(use_space=False)
    vo = nb.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    nb.set(vo, 'Scale', 5.0)
    nb.link(tc.outputs['Object'], vo.inputs['Vector'])
    c = nb.maprange(vo.outputs['Distance'], 0.04, 0.0)
    nb.output(nb.add_shader(nb.principled(base=(0.04, 0.06, 0.07), rough=0.8).outputs[0],
                            nb.emission((0.4, 0.8, 1.0), nb.math('MULTIPLY', c, 0.4))))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3.0)
    g = CL.mesh_object("Fondale_Caustiche", bm, m, smooth=False)
    g.location = (0, 0, 0.003)


def scena_quetzal():
    ST.mondo((0.35, 0.12, 0.05), (0.05, 0.08, 0.2), 0.6, nome="Alba")
    ST.luce("Alba_Radente", 'SUN', (0, 0, 5), 2.5, (1.0, 0.55, 0.2), 2.0, rot=(80, 0, -60))
    ST.compositor(0.4, 7, (4, 30.0, 0.2), 0.0)


def scena_ddraig():
    ST.mondo((0.5, 0.18, 0.06), (0.1, 0.06, 0.15), 0.6, nome="Tramonto")
    m = CL.m_body("Colline_Verdi", (0.05, 0.14, 0.04), rough=0.9, mottle=((0.03, 0.09, 0.02), 1.5))
    for i, (x, y, s) in enumerate(((-2.5, 5, 2.2), (1.5, 6, 2.8), (4.5, 4.5, 2.0))):
        h = CL.sphere("Collina_%d" % i, (x, y, -s * 0.75), (s * 1.6, s, s), m, seg=24, rings=12)
        h["rbx_drop"] = 1
    ST.luce("Rim_Rossa", 'AREA', (0.5, 1.8, 1.8), 200.0, (1.0, 0.2, 0.08), 2.0, rot=(-65, 0, 180))


def scena_idra():
    ST.nebbia("Palude_Verde", (0, 0, 1.0), (6, 6, 2), (0.5, 0.8, 0.5), 0.05)
    m = CL.m_body("Acqua_Palude", (0.01, 0.025, 0.015), rough=0.05, spec=0.8)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3.0)
    w = CL.mesh_object("Acqua_Palude", bm, m, smooth=False)
    w.location = (0, 0, 0.015)
    mr = CL.m_body("Canne", (0.1, 0.12, 0.04), rough=0.7)
    rnd = random.Random(4)
    for i in range(24):
        x, y = rnd.uniform(-1.8, 1.8), rnd.uniform(0.6, 2.2)
        CL.tube("Canna_%02d" % i, [V((x, y, 0)), V((x + rnd.uniform(-0.05, 0.05), y, rnd.uniform(0.6, 1.2)))],
                [0.008, 0.003], mr, bevel_res=0, poly=True)


def scena_wyvern():
    m = CL.new_material("Muro_Castello")
    nb = CL.NodeBuilder(m)
    tc = nb.texcoord(use_space=False)
    br = nb.node('ShaderNodeTexBrick')
    nb.set(br, 'Color1', (0.18, 0.16, 0.14))
    nb.set(br, 'Color2', (0.12, 0.11, 0.1))
    nb.set(br, 'Mortar', (0.04, 0.035, 0.03))
    nb.set(br, 'Scale', 1.2)
    sep = nb.node('ShaderNodeCombineXYZ')
    s2 = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], s2.inputs[0])
    nb.link(s2.outputs['X'], sep.inputs[0])
    nb.link(s2.outputs['Z'], sep.inputs[1])
    nb.link(sep.outputs[0], br.inputs['Vector'])
    pb = nb.principled(base=br.outputs['Color'], rough=0.9)
    nb.set(pb, 'Normal', nb.bump(br.outputs['Fac'], 0.6, 0.02))
    nb.output(pb.outputs[0])
    DS.box("Muro_Castello", (0, 1.2, 1.5), (6, 0.3, 3), m)
    mf = ST.m_luce("Fiamma_Torcia", 1800, 60.0)
    mt = CL.m_body("Torcia_Legno", (0.1, 0.06, 0.03), rough=0.8)
    CL.tube("Torcia", [V((-1.1, 1.02, 1.1)), V((-1.1, 0.95, 1.45))], 0.025, mt, bevel_res=1)
    ST.cono_piatto("Torcia_Fiamma", (-1.1, 0.95, 1.45), (-1.1, 0.95, 1.65), 0.05, mf, 0.8)
    ST.luce("Luce_Torcia", 'POINT', (-1.1, 0.85, 1.6), 80.0, 1800, 0.1)
    ST.compositor(0.4, 6, None, 0.0)


def scena_ourobo():
    ST.mondo((0.55, 0.5, 0.7), (0.45, 0.65, 0.8), 0.5, nome="Sfondo_Pastello")
    ST.compositor(0.6, 8, None, 0.0)


CREATURE_DRAGHI = {
    #  chiave       (collezione,                        funzione,        camera: target, dist, elev, azim, lente)
    "tesorino": ("D01_Tesorino-Drago-Custode",          build_tesorino,  ((0, 0.05, 0.2), 3.0, 30, 25, 50)),
    "long":     ("D02_Perla-Drago-Cinese",              build_long,      ((0.05, 0.0, 0.85), 4.6, 8, 10, 50)),
    "ryujin":   ("D03_Marea-Re-Drago",                  build_ryujin,    ((0, -0.05, 0.7), 3.8, 10, 25, 50)),
    "quetzal":  ("D04_Quetzal-Serpente-Piumato",        build_quetzal,   ((0, 0.0, 0.5), 3.6, 14, 30, 50)),
    "ddraig":   ("D05_Ddraig-Drago-Rosso",              build_ddraig,    ((0, 0.0, 0.85), 4.6, 8, 40, 50)),
    "idra":     ("D06_Idra-di-Lerna",                   build_idra,      ((0, -0.1, 0.45), 3.4, 18, 20, 50)),
    "wyvern":   ("D07_Blasone-Wyvern",                  build_wyvern,    ((0, 0.0, 0.9), 4.2, 6, 25, 50)),
    "ourobo":   ("D08_Ourobo-Ourobo",                   build_ourobo,    ((0, 0.0, 0.78), 3.6, 6, 10, 50)),
}

DISPOSIZIONE_DRAGHI = {
    "ddraig":   (-4.8, 5.0, 20),
    "long":     (-1.2, 5.2, 0),
    "ryujin":   (2.0, 4.8, -10),
    "wyvern":   (4.9, 5.0, -25),
    "tesorino": (-3.9, 0.9, 25),
    "idra":     (-1.3, 0.6, 15),
    "quetzal":  (1.3, 0.6, -20),
    "ourobo":   (3.9, 0.8, -15),
}

SCENE_DRAGHI = {"tesorino": scena_tesorino, "long": scena_long, "ryujin": scena_ryujin, "quetzal": scena_quetzal,
                "ddraig": scena_ddraig, "idra": scena_idra, "wyvern": scena_wyvern, "ourobo": scena_ourobo}


def build(which=None, engine=None, clean=None):
    ST.build_serie(CREATURE_DRAGHI, DISPOSIZIONE_DRAGHI, which or CREATURA, scena_gruppo, SCENE_DRAGHI,
                   ((0, 2.6, 1.0), 13.0, 12, 0, 32), ST.SETUP["draghi"], engine or MOTORE, clean)


def main():
    ST.main(build)


if __name__ == "__main__":
    main()
