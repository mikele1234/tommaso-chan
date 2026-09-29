# -*- coding: utf-8 -*-
"""
STRUMENTI COMUNI per le serie MOSTRI, INFERNO, ANGELI e DRAGHI.

Queste quattro serie sono modelli 3D STATICI (nessuna animazione, nessun
driver): servono per render, icone e per l'esportazione su Roblox.

Contiene:
  * il setup EEVEE Next comune (Raytracing Screen-Trace, Virtual Shadows,
    Light Threshold 0.001, volumetrie 1:2 / 96 step / distribuzione 0.8,
    AgX con il Look richiesto, Glare Bloom e Streaks nel compositor,
    vignettatura leggera);
  * colori in Kelvin con il nodo Blackbody (e la conversione in RGB per le
    luci e per Roblox);
  * le luci proxy (Point Light con raggio 0.005 m agganciata all'organo
    luminoso con un vincolo Child Of);
  * materiali: chitina, ali Blended con Thin Film, vetro, liquidi e fumi
    volumetrici, pietra con crepe incandescenti (nodo Displacement);
  * pezzi riutilizzabili: occhi e sopracciglia da cartone, sneakers, ali
    membranose (pipistrello / drago), istanze (duplicati collegati).

Deve stare nella stessa cartella di creature_luminose.py, creature_deserto.py,
creature_neve.py e creature_oceano.py.
"""

import bpy
import bmesh
import importlib.util
import math
import os
import sys
from math import cos, pi, radians, sin

from mathutils import Matrix, Vector


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
OC = _carica("creature_oceano")
TAU = CL.TAU
V = Vector
ellipsoid = CL.ellipsoid
capsule = CL.capsule
ball = CL.ball
side_name = NV.side_name


# ============================================================================
# COLORI: Kelvin -> Blackbody
# ============================================================================

def _lobo(x, mu, s1, s2):
    s = s1 if x < mu else s2
    return math.exp(-0.5 * ((x - mu) / s) ** 2)


_KELVIN = {}


def kelvin(K):
    """Colore (RGB lineare, massimo = 1) di un corpo nero a K kelvin: spettro di
    Planck integrato con le funzioni colorimetriche CIE 1931. Serve per le luci
    e per i colori di Roblox (nei materiali si usa il nodo Blackbody)."""
    K = float(K)
    if K in _KELVIN:
        return _KELVIN[K]
    X = Y = Z = 0.0
    for lam in range(380, 781, 5):
        m = lam * 1e-9
        B = 1.0 / (m ** 5 * (math.exp(1.4388e-2 / (m * K)) - 1.0))
        X += B * (1.056 * _lobo(lam, 599.8, 37.9, 31.0) + 0.362 * _lobo(lam, 442.0, 16.0, 26.7)
                  - 0.065 * _lobo(lam, 501.1, 20.4, 26.2))
        Y += B * (0.821 * _lobo(lam, 568.8, 46.9, 40.5) + 0.286 * _lobo(lam, 530.9, 16.3, 31.1))
        Z += B * (1.217 * _lobo(lam, 437.0, 11.8, 36.0) + 0.681 * _lobo(lam, 459.0, 26.0, 13.8))
    r = max(0.0, 3.2406 * X - 1.5372 * Y - 0.4986 * Z)
    g = max(0.0, -0.9689 * X + 1.8758 * Y + 0.0415 * Z)
    b = max(0.0, 0.0557 * X - 0.2040 * Y + 1.0570 * Z)
    top = max(r, g, b)
    out = (r / top, g / top, b / top)
    _KELVIN[K] = out
    return out


def rgb(c):
    """Kelvin (numero) oppure colore RGB -> tupla RGB."""
    if isinstance(c, (int, float)):
        return kelvin(c)
    return tuple(c[:3])


def colore(nb, c):
    """Nel materiale: nodo Blackbody se c e' una temperatura, altrimenti RGB."""
    if isinstance(c, (int, float)):
        nd = nb.node('ShaderNodeBlackbody')
        nb.set(nd, 'Temperature', float(c))
        nd.label = "Blackbody %d K" % int(c)
        return nd.outputs[0]
    return tuple(c[:3])


def mescola(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ============================================================================
# LUCI PROXY (Point Light 0.005 m + Child Of)
# ============================================================================

def proxy(organo, loc, c, energia, nome=None, raggio=0.005):
    """Point Light proxy dello stesso colore dell'organo luminoso, agganciata
    all'organo con un vincolo Child Of (lo segue ovunque venga spostato)."""
    ob = CL.add_light(nome or (organo.name + "_Luce_Proxy"), 'POINT', loc, energia, rgb(c), raggio)
    bpy.context.view_layer.update()
    con = ob.constraints.new('CHILD_OF')
    con.name = "Aggancio_Organo"
    con.target = organo
    con.inverse_matrix = organo.matrix_world.inverted()
    return ob


def luce(nome, tipo, loc, energia, c=(1, 1, 1), size=0.1, rot=None, spot=None, scena=True):
    """Luce di scena (non fa parte della creatura) con colore in Kelvin o RGB."""
    return CL.add_light(nome, tipo, loc, energia, rgb(c), size, rot=rot, spot_size=spot,
                        creature_light=not scena)


# ============================================================================
# MATERIALI
# ============================================================================

def m_luce(nome, c, forza, bordo=None, forza_bordo=None, alpha=None):
    """Organo luminoso: emissione (Kelvin -> Blackbody). bordo = colore piu'
    chiaro sui contorni con Fresnel (Layer Weight)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    s = nb.value(forza * CL.INTENSITA_LUCE)
    em = nb.emission(colore(nb, c), s)
    if bordo is not None:
        f = nb.maprange(nb.fresnel(0.3), 0.25, 0.9)
        em = nb.mix_shader(f, em, nb.emission(colore(nb, bordo), (forza_bordo or forza) * CL.INTENSITA_LUCE))
    if alpha is not None:
        em = nb.mix_shader(alpha, nb.transparent(), em)
        CL.set_transparent(mat)
    nb.output(em)
    CL.diffuse_display(mat, rgb(c))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(rgb(c))
    if alpha is not None:
        mat["rbx_transp"] = round(1.0 - alpha, 3)
    return mat


def _principled_extra(mat, film=0.0, aniso=0.0, film_ior=1.45):
    for nd in mat.node_tree.nodes:
        if nd.bl_idname == 'ShaderNodeBsdfPrincipled':
            for key, val in (('Thin Film Thickness', film), ('Thin Film IOR', film_ior if film else None),
                             ('Anisotropic', aniso)):
                s = nd.inputs.get(key)
                if s is not None and val:
                    s.default_value = val
    return mat


def m_chitina(nome, base, rough=0.35, coat=0.5, sss=0.05, film=0.0, metal=0.0, aniso=0.0,
              sss_radius=(1.0, 0.45, 0.25), **kw):
    """Chitina / scaglie del setup: Principled con Coat e un filo di Subsurface
    (valori di default del setup angeli/draghi; l'inferno usa 0.4 / 0.4)."""
    mat = CL.m_body(nome, rgb(base), rough=rough, coat=coat, sss=sss, sss_radius=sss_radius, metal=metal, **kw)
    return _principled_extra(mat, film, aniso)


def m_ala(nome, ramp, alpha=0.15, film=400.0, **kw):
    """Ala membranosa: Render Method Blended, Thin Film ~400 nm, Alpha bassa."""
    ramp = [(p, rgb(c)) for p, c in ramp]
    if kw.get("vein_ramp"):
        kw["vein_ramp"] = [(p, rgb(c)) for p, c in kw["vein_ramp"]]
    for k in ("cell_color",):
        if kw.get(k) is not None:
            kw[k] = rgb(kw[k])
    mat = CL.m_wing(nome, ramp, alpha=alpha, film=film, **kw)
    CL.set_transparent(mat, blended=True)
    return mat


def m_vetro(nome, tinta=(0.95, 0.97, 1.0), ior=1.45, rough=0.02, bordo=None, forza_bordo=0.0,
            trasparenza=0.6, spessore='SPHERE'):
    """Vetro (Principled con Transmission 1) e rifrazione raytrace in EEVEE."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    pb = nb.principled(base=rgb(tinta), rough=rough, trans=1.0, ior=ior, spec=0.6)
    sh = pb.outputs[0]
    if bordo is not None and forza_bordo:
        r = nb.maprange(nb.fresnel(0.3), 0.3, 1.0, 0.0, forza_bordo)
        sh = nb.add_shader(sh, nb.emission(colore(nb, bordo), r))
    nb.output(sh)
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True),
                      ('thickness_mode', spessore)):
        if hasattr(mat, attr):
            try:
                setattr(mat, attr, val)
            except (TypeError, ValueError):
                pass
    CL.diffuse_display(mat, rgb(tinta))
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = list(rgb(tinta))
    mat["rbx_transp"] = trasparenza
    return mat


def m_liquido(nome, assorbe, densita, luce_c, forza, ior=1.33, tinta=(1.0, 0.9, 0.9), rbx_c=None):
    """Liquido dentro a un contenitore di vetro: superficie Glass, dentro un
    Volume Absorption denso piu' l'emissione del volume."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    gl = nb.node('ShaderNodeBsdfGlass', {'Color': rgb(tinta), 'Roughness': 0.02, 'IOR': ior})
    nb.output(gl.outputs[0])
    ab = nb.node('ShaderNodeVolumeAbsorption', {'Color': rgb(assorbe), 'Density': densita})
    pv = nb.node('ShaderNodeVolumePrincipled')
    nb.set(pv, 'Density', 0.0)
    nb.set(pv, 'Emission Color', colore(nb, luce_c))
    nb.set(pv, 'Emission Strength', forza * CL.INTENSITA_LUCE)
    nb.link(nb.add_shader(ab.outputs[0], pv.outputs[0]), nb.out.inputs['Volume'])
    for attr, val in (('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    CL.diffuse_display(mat, rgb(luce_c))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(rgb_c(rbx_c, luce_c))
    mat["rbx_transp"] = 0.2
    return mat


def m_vetro_sottile(nome, tinta=(0.95, 0.97, 1.0), bordo=None, forza_bordo=0.0, rough=0.03, trasparenza=0.7):
    """Vetro sottile (fiale, lenti, lanterne): trasparente al centro e lucido
    sui bordi, senza rifrazione, cosi' si vede cio' che c'e' dentro."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    gl = nb.node('ShaderNodeBsdfGlossy', {'Color': rgb(tinta), 'Roughness': rough})
    fac = nb.maprange(nb.fresnel(0.2), 0.0, 1.0, 0.08, 1.0, smooth=False)
    sh = nb.mix_shader(fac, nb.transparent(), gl.outputs[0])
    if bordo is not None and forza_bordo:
        r = nb.maprange(nb.fresnel(0.3), 0.35, 1.0, 0.0, forza_bordo)
        sh = nb.add_shader(sh, nb.emission(colore(nb, bordo), r))
    nb.output(sh)
    CL.set_transparent(mat, blended=True)
    CL.diffuse_display(mat, rgb(tinta))
    mat["rbx_kind"] = "glass"
    mat["rbx_color"] = list(rgb(tinta))
    mat["rbx_transp"] = trasparenza
    return mat


def rgb_c(a, b):
    return rgb(a) if a is not None else rgb(b)


def m_volume(nome, c=(1, 1, 1), densita=1.0, luce_c=None, forza=0.0, rumore=None, sfuma=True,
             anisotropia=0.2, roblox="drop", assorbe=None):
    """Volume (fumo, foschia, aloni di calore). rumore = scala del rumore che
    rende la densita' a sbuffi; sfuma = densita' che si annulla verso il bordo
    dell'oggetto (coordinate oggetto di una sfera o di un cubo unitario)."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    d = nb.value(densita)
    tc = nb.texcoord(use_space=False)
    if rumore:
        nz = nb.noise(tc.outputs['Object'], rumore, 6.0, 0.6)
        d = nb.math('MULTIPLY', d, nb.maprange(nz.outputs['Fac'], 0.42, 0.72, 0.0, 1.0))
    if sfuma:
        vm = nb.node('ShaderNodeVectorMath', operation='LENGTH')
        nb.link(tc.outputs['Object'], vm.inputs[0])
        d = nb.math('MULTIPLY', d, nb.maprange(vm.outputs['Value'], 1.0, 0.35, 0.0, 1.0))
    pv = nb.node('ShaderNodeVolumePrincipled')
    nb.set(pv, 'Color', rgb(c))
    nb.link(d, nb.socket(pv, 'Density'))
    nb.set(pv, 'Anisotropy', anisotropia)
    if assorbe is not None:
        nb.set(pv, 'Absorption Color', rgb(assorbe))
    if luce_c is not None and forza:
        nb.set(pv, 'Emission Color', colore(nb, luce_c))
        nb.link(nb.math('MULTIPLY', d, forza * CL.INTENSITA_LUCE), nb.socket(pv, 'Emission Strength'))
    nb.output(nb.transparent())
    nb.link(pv.outputs[0], nb.out.inputs['Volume'])
    CL.set_transparent(mat)
    CL.diffuse_display(mat, rgb(luce_c if luce_c is not None else c))
    mat["rbx_kind"] = roblox
    mat["rbx_color"] = list(rgb(luce_c if luce_c is not None else c))
    return mat


def m_crepe(nome, pietra=(0.02, 0.018, 0.022), pietra2=(0.05, 0.045, 0.05), luce_c=1500, forza=40.0,
            scala=6.0, crepa=0.05, metal=0.55, rough=0.9, profondita=0.012, lucido=None, uv=False, rado=0.0):
    """Pietra scura con fratture profonde (nodo Displacement) riempite di
    emissione incandescente. luce_c: Kelvin (Blackbody) o RGB."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    vec = DS._coords(nb, distort=0.35, uv=uv)
    vo = nb.voronoi(vec, scala, 'DISTANCE_TO_EDGE')
    nz = nb.noise(vec, 3.0, 6.0, 0.6)
    cr = nb.maprange(vo.outputs['Distance'], crepa, crepa * 0.12)
    cr = nb.math('MULTIPLY', cr, nb.maprange(nz.outputs['Fac'], 0.32 + rado, 0.55 + rado, 0.0, 1.0))
    fine = nb.noise(vec, 28.0, 8.0, 0.65)
    col = nb.ramp(fine.outputs['Fac'], [(0.3, rgb(pietra)), (0.75, rgb(pietra2))])
    rgh = nb.maprange(fine.outputs['Fac'], 0.3, 0.8, rough, rough * 0.75)
    sb = nb.principled(base=col, rough=rgh, metal=metal, spec=0.5)
    nb.set(sb, 'Normal', nb.bump(nb.math('ADD', nb.math('MULTIPLY', fine.outputs['Fac'], 0.4),
                                         nb.math('SUBTRACT', 1.0, cr)), 0.45, 0.01))
    gcol = colore(nb, luce_c)
    if lucido is not None:          # nucleo piu' chiaro al centro della crepa
        core = nb.maprange(vo.outputs['Distance'], crepa * 0.35, 0.0)
        gcol = rgb_mix_socket(nb, core, gcol, colore(nb, lucido))
    s = nb.value(forza * CL.INTENSITA_LUCE)
    nb.output(nb.mix_shader(cr, sb.outputs[0], nb.emission(gcol, s)))
    # le fratture sono scavate davvero (Displacement), non solo dipinte
    dn = nb.node('ShaderNodeDisplacement', {'Scale': profondita, 'Midlevel': 1.0})
    nb.link(nb.math('SUBTRACT', 1.0, cr), dn.inputs['Height'])
    nb.link(dn.outputs[0], nb.out.inputs['Displacement'])
    for attr in ('displacement_method',):
        if hasattr(mat, attr):
            try:
                setattr(mat, attr, 'BOTH')
            except (TypeError, ValueError):
                pass
    nb.bake_output("RBX_COLOR", nb.mix_shader(cr, nb.emission(col, 1.0), nb.emission(gcol, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(cr, nb.emission((0, 0, 0), 1.0), nb.emission(gcol, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_rough"] = rough
    mat["rbx_metal"] = metal
    mat["rbx_emit_strength"] = min(10.0, float(forza) / 8.0)
    mat["rbx_normal"] = 1
    if uv:
        mat["rbx_uv_only"] = 1
    CL.diffuse_display(mat, rgb(pietra2))
    return mat


def rgb_mix_socket(nb, fac, a, b):
    return NV.rgb_mix(nb, fac, a, b)


def m_occhio_bianco(nome="Occhio_Bianco"):
    return CL.m_body(nome, (0.92, 0.92, 0.9), rough=0.12, coat=1.0, sss=0.1, spec=0.6)


# ============================================================================
# GEOMETRIA
# ============================================================================

# Metaball in "misure visibili": con soglia 0.6 una sfera di raggio R appare
# grande circa 0.575 R, quindi qui il raggio viene moltiplicato.
K_META = 1.74


def el(co, r, size=(1, 1, 1), **kw):
    return ellipsoid(co, r * K_META, size, **kw)


def cap(a, b, r, **kw):
    return capsule(a, b, r * K_META, **kw)


def bl(co, r, **kw):
    return ball(co, r * K_META, **kw)


def separa_materiali(ob):
    """Divide un oggetto con piu' materiali in un oggetto per materiale (su
    Roblox ogni pezzo ha un solo materiale)."""
    me = ob.data
    if len(me.materials) < 2:
        return [ob]
    out = []
    for idx, mat in enumerate(me.materials):
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != idx], context='FACES')
        if not bm.faces:
            bm.free()
            continue
        for f in bm.faces:
            f.material_index = 0
        nome = "%s_%s" % (ob.name, mat.name.split("_", 1)[-1])
        nob = CL.mesh_object(nome, bm, mat)
        nob.matrix_world = ob.matrix_world
        out.append(nob)
    bpy.data.objects.remove(ob)
    return out


def applica(ob):
    """Applica tutti i modificatori (mesh finale)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def guscio(nome, centro, raggi, mat, piani, seg=56, rings=28, spessore=0.012):
    """Pezzo di corazza (elitre, elmi, cappucci): ellissoide tagliato da piani
    [(punto, normale)] (si tiene il lato verso cui punta la normale), con un
    po' di spessore verso l'interno."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=CL.det(seg, 12), v_segments=CL.det(rings, 8), radius=1.0)
    c = V(centro)
    for v in bm.verts:
        v.co = V((v.co.x * raggi[0], v.co.y * raggi[1], v.co.z * raggi[2])) + c
    for p0, n in piani:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=V(p0), plane_no=V(n).normalized(),
                               clear_inner=True)
    ob = CL.mesh_object(nome, bm, mat)
    if spessore:
        solidifica(ob, spessore, -1.0)
    return ob


def ellissoide_z(c, r, x, y):
    """Quota della superficie superiore di un ellissoide nel punto (x, y)."""
    q = 1.0 - ((x - c[0]) / r[0]) ** 2 - ((y - c[1]) / r[1]) ** 2
    return c[2] + r[2] * math.sqrt(max(0.0, q))


def cono_piatto(nome, base, punta, r, mat, piatto=0.35, avanti=(0, -1, 0), seg=10):
    """Cono schiacciato (orecchie, corna piatte, fiamme)."""
    base, punta = V(base), V(punta)
    d = punta - base
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=CL.det(seg, 5), radius1=r, radius2=0.0,
                          depth=d.length)
    bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=bm.verts)
    ob = CL.mesh_object(nome, bm, mat)
    ob.matrix_world = CL.frame_matrix(base, V(avanti), d) @ Matrix.Diagonal((1.0, piatto, 1.0, 1.0))
    return ob


def istanze(master, matrici, prefisso):
    """Duplicati collegati (stessa mesh / curva) di un gruppo di oggetti
    costruiti attorno all'origine: e' l'equivalente di 'Instance' in Blender.
    Restituisce una lista (per ogni matrice) di liste di oggetti."""
    bpy.context.view_layer.update()
    base = [(o, o.matrix_world.copy()) for o in master]
    out = []
    for i, M in enumerate(matrici):
        grp = []
        for o, mw in base:
            nome = "%s_%d_%s" % (prefisso, i + 1, o.name.split("_", 1)[1] if "_" in o.name else o.name)
            ob = bpy.data.objects.new(nome, o.data)
            CL.link(ob)
            ob.matrix_world = M @ mw
            for md in o.modifiers:
                nm = ob.modifiers.new(md.name, md.type)
                for attr in ('levels', 'render_levels', 'thickness', 'offset'):
                    if hasattr(md, attr):
                        setattr(nm, attr, getattr(md, attr))
            if o.get("rbx_drop"):
                ob["rbx_drop"] = 1
            grp.append(ob)
        out.append(grp)
    for o, _mw in base:
        bpy.data.objects.remove(o)
    return out


def materiale_oggetto(ob, mat):
    """Materiale diverso su un'istanza (slot collegato all'oggetto)."""
    if not ob.material_slots:
        ob.data.materials.append(mat)
    ob.material_slots[0].link = 'OBJECT'
    ob.material_slots[0].material = mat
    return ob


def frame(loc, avanti, su=(0, 0, 1)):
    """Matrice con -Y lungo `avanti` (il muso) e Z verso `su`."""
    f = V(avanti).normalized()
    z = V(su)
    z = (z - f * z.dot(f)).normalized()
    y = -f
    x = y.cross(z).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(loc)
    return m


def occhio_cartone(prefisso, centro, normale, r, m_bianco, m_pupilla, m_luce=None, guarda=(0.0, 0.0),
                   pupilla=0.5, su=(0, 0, 1), piatto=0.8):
    """Occhio enorme da cartone animato: bulbo bianco lucido, pupilla nera
    (spostata dove guarda) e un riflesso bianco."""
    n = V(normale).normalized()
    obs = []
    e = CL.sphere(prefisso, (0, 0, 0), 1.0, m_bianco, seg=24, rings=12)
    CL.orient(e, V(centro), n, su, (r, r, r * piatto))
    obs.append(e)
    m = CL.frame_matrix(V(centro), V(su), n)
    xa = m.to_3x3() @ V((1, 0, 0))
    ya = m.to_3x3() @ V((0, 1, 0))
    off = xa * guarda[0] * r * 0.45 + ya * guarda[1] * r * 0.45
    pc = V(centro) + off + n * (r * piatto * 0.92)
    p = CL.sphere(prefisso + "_Pupilla", (0, 0, 0), 1.0, m_pupilla, seg=16, rings=8)
    CL.orient(p, pc, n, su, (r * pupilla, r * pupilla, r * 0.12))
    obs.append(p)
    if m_luce is not None:
        h = CL.sphere(prefisso + "_Riflesso", (0, 0, 0), 1.0, m_luce, seg=10, rings=5)
        CL.orient(h, pc + xa * r * pupilla * -0.35 + ya * r * pupilla * 0.4 + n * r * 0.1, n, su,
                  (r * 0.14, r * 0.14, r * 0.05))
        obs.append(h)
    return obs


def sopracciglio(nome, centro, normale, largo, inclina, r, mat, su=(0, 0, 1), lato=1, arco=0.25, alza=0.0):
    """Sopracciglio da cartone (Curve + Bevel). inclina > 0: l'estremita' interna
    scende (faccia arrabbiata). lato = +1 occhio destro, -1 sinistro."""
    n = V(normale).normalized()
    m = CL.frame_matrix(V(centro), V(su), n).to_3x3()
    xa, ya = m @ V((1, 0, 0)), m @ V((0, 1, 0))
    pts, rad = [], []
    for i in range(5):
        t = i / 4.0 - 0.5                  # -0.5 (interno) .. 0.5 (esterno)
        x = t * largo * lato
        y = alza + arco * largo * (0.25 - t * t) + math.tan(radians(inclina)) * t * largo
        pts.append(V(centro) + xa * x + ya * y + n * r * 0.6)
        rad.append(r * (1.0 - 0.35 * abs(t) * 2))
    return CL.tube(nome, pts, rad, mat, bevel_res=2)


def sneaker(prefisso, lung, m_tomaia, m_suola, m_lacci, m_accento=None):
    """Sneaker da cartone (costruita all'origine, punta verso -Y, suola a z=0):
    suola bombata, tomaia morbida, lacci, linguetta e una striscia laterale."""
    L = lung
    W = L * 0.42
    obs = []
    # suola: impronta arrotondata, tre anelli per un bordo morbido
    bm = bmesh.new()
    n = CL.det(28, 12)
    rows = []
    for z, sc in ((0.0, 0.95), (0.03 * L, 1.0), (0.09 * L, 1.0), (0.11 * L, 0.96)):
        row = []
        for j in range(n):
            a = TAU * j / n
            y = -cos(a) * L * 0.5
            t = (y / (L * 0.5) + 1) / 2        # 0 punta .. 1 tallone
            w = W * 0.5 * (1.0 - 0.18 * sin(pi * min(1, max(0, (t - 0.25) / 0.6))))
            row.append(bm.verts.new((sin(a) * w * sc, y * sc, z)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bm.faces.new(list(reversed(rows[0])))
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obs.append(CL.mesh_object(prefisso + "_Suola", bm, m_suola))
    # tomaia
    h = 0.1 * L
    E = [ellipsoid((0, -0.28 * L, h + 0.1 * L), 0.24 * L, (0.95, 1.2, 0.62)),
         ellipsoid((0, 0.02 * L, h + 0.16 * L), 0.25 * L, (0.95, 1.1, 0.85)),
         ellipsoid((0, 0.28 * L, h + 0.19 * L), 0.22 * L, (0.95, 0.9, 1.0)),
         ellipsoid((0, 0.24 * L, h + 0.36 * L), 0.17 * L, (1.0, 0.95, 0.7))]
    obs.append(CL.metaball_mesh(prefisso + "_Tomaia", E, m_tomaia, res=0.05 * L))
    obs.append(CL.sphere(prefisso + "_Apertura", (0, 0.27 * L, h + 0.43 * L), (0.14 * L, 0.13 * L, 0.03 * L),
                         m_suola if m_accento is None else m_accento, seg=16, rings=6))
    obs.append(CL.sphere(prefisso + "_Linguetta", (0, 0.1 * L, h + 0.38 * L), (0.1 * L, 0.05 * L, 0.1 * L),
                         m_tomaia, rot=(-25, 0, 0), seg=12, rings=6))
    obs.append(CL.sphere(prefisso + "_Puntale", (0, -0.4 * L, h + 0.05 * L), (0.18 * L, 0.11 * L, 0.07 * L),
                         m_suola, seg=16, rings=8))
    for i in range(3):
        y = -0.12 * L + i * 0.09 * L
        z = h + 0.27 * L + i * 0.035 * L
        obs.append(CL.tube("%s_Laccio_%d" % (prefisso, i), [V((-0.1 * L, y, z - 0.01 * L)), V((0, y, z + 0.01 * L)),
                                                            V((0.1 * L, y, z - 0.01 * L))],
                           0.018 * L, m_lacci, bevel_res=1))
    if m_accento is not None:
        for sx in (-1, 1):
            pts = [V((sx * 0.215 * L, y * L, h + z * L)) for y, z in ((-0.2, 0.06), (0.0, 0.1), (0.2, 0.16),
                                                                      (0.3, 0.22))]
            obs.append(CL.tube("%s_Striscia_%s" % (prefisso, side_name(sx)), pts, 0.02 * L, m_accento,
                               bevel_res=1))
    return obs


def ala_membrana(prefisso, spalla, gomito, polso, punte, corpo, mat, m_ossa, sacca=0.22, gonfia=0.06,
                 righe=6, colonne=5, r_osso=0.012, artiglio=None, ossa_luce=None):
    """Ala membranosa da pipistrello / drago (lato destro, x > 0): la membrana
    e' tesa a ventaglio attorno al polso tra le dita (punte), poi fino al corpo
    e alla spalla; il bordo d'uscita e' festonato (sacca) e la superficie si
    gonfia (gonfia). UV: u = attorno al ventaglio, v = dal polso al bordo.
    Restituisce (membrana, [ossa])."""
    spalla, gomito, polso = V(spalla), V(gomito), V(polso)
    raggi = [V(p) for p in punte] + [V(corpo), spalla]
    righe, colonne = CL.det(righe, 3), CL.det(colonne, 2)
    nsett = len(raggi) - 1
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = {}
    tot_c = nsett * colonne
    nrm = (raggi[0] - polso).cross(raggi[-2] - polso).normalized()
    if nrm.z < 0:
        nrm = -nrm
    for k in range(nsett):
        A, B = raggi[k] - polso, raggi[k + 1] - polso
        festone = k < nsett - 1
        for i in range(colonne + 1):
            s = i / colonne
            gi = k * colonne + i
            if (gi, 0) in grid:
                continue
            for j in range(righe + 1):
                t = j / righe
                d = A.lerp(B, s)
                ln = A.length + (B.length - A.length) * s
                p = polso + d.normalized() * ln * t
                if festone:
                    p -= d.normalized() * ln * sacca * sin(pi * s) * t ** 3
                p += nrm * gonfia * ln * sin(pi * s) * sin(pi * t * 0.5 + 0.2)
                grid[(gi, j)] = bm.verts.new(p)
    for gi in range(tot_c):
        for j in range(righe):
            f = bm.faces.new((grid[(gi, j)], grid[(gi + 1, j)], grid[(gi + 1, j + 1)], grid[(gi, j + 1)]))
            for lp, (a, b) in zip(f.loops, ((gi, j), (gi + 1, j), (gi + 1, j + 1), (gi, j + 1))):
                lp[uvl].uv = (a / tot_c, b / righe)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mem = CL.mesh_object(prefisso + "_Membrana_R", bm, mat)
    ossa = [CL.tube(prefisso + "_Omero_R", [spalla, spalla.lerp(gomito, 0.5), gomito], [r_osso * 1.5, r_osso * 1.3,
                                                                                     r_osso * 1.2], m_ossa,
                    bevel_res=2),
            CL.tube(prefisso + "_Avambraccio_R", [gomito, gomito.lerp(polso, 0.5), polso], [r_osso * 1.2, r_osso,
                                                                                      r_osso * 1.1], m_ossa,
                    bevel_res=2)]
    for i, p in enumerate(punte):
        p = V(p)
        mid = polso.lerp(p, 0.5) + nrm * 0.03 * (p - polso).length
        ossa.append(CL.tube("%s_Dito_%d_R" % (prefisso, i), [polso, mid, p], [r_osso, r_osso * 0.7, r_osso * 0.25],
                            ossa_luce[i] if ossa_luce else m_ossa, bevel_res=2))
    if artiglio is not None:
        d = (polso - gomito).normalized()
        ossa.append(CL.cone_between(prefisso + "_Artiglio_R", polso, polso + d * r_osso * 5 + nrm * r_osso * 3,
                                    r_osso * 1.1, 0.0, artiglio, 8))
    return mem, ossa


def specchia_x(obs, suffisso=("_R", "_L")):
    """Copia speculare (asse X) di oggetti costruiti sul lato destro."""
    out = []
    for o in obs:
        if o.type == 'MESH':
            me = o.data.copy()
            me.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.reverse_faces(bm, faces=bm.faces, flip_multires=False)
            bm.to_mesh(me)
            bm.free()
            nome = o.name[:-2] + suffisso[1] if o.name.endswith(suffisso[0]) else o.name + suffisso[1]
            ob = bpy.data.objects.new(nome, me)
            CL.link(ob)
            ob.matrix_world = Matrix.Scale(-1, 4, (1, 0, 0)) @ o.matrix_world @ Matrix.Scale(-1, 4, (1, 0, 0))
        else:
            cu = o.data.copy()
            nome = o.name[:-2] + suffisso[1] if o.name.endswith(suffisso[0]) else o.name + suffisso[1]
            ob = bpy.data.objects.new(nome, cu)
            CL.link(ob)
            for sp in cu.splines:
                for bp in sp.bezier_points:
                    for attr in ('co', 'handle_left', 'handle_right'):
                        v = getattr(bp, attr)
                        setattr(bp, attr, (-v.x, v.y, v.z))
                for pt in sp.points:
                    pt.co = (-pt.co[0], pt.co[1], pt.co[2], pt.co[3])
            ob.matrix_world = Matrix.Scale(-1, 4, (1, 0, 0)) @ o.matrix_world @ Matrix.Scale(-1, 4, (1, 0, 0))
        for md in o.modifiers:
            nm = ob.modifiers.new(md.name, md.type)
            for attr in ('levels', 'render_levels', 'thickness', 'offset', 'use_even_offset'):
                if hasattr(md, attr):
                    setattr(nm, attr, getattr(md, attr))
        out.append(ob)
    return out


def solidifica(ob, spessore, offset=0.0):
    md = ob.modifiers.new("Spessore", 'SOLIDIFY')
    md.thickness = spessore
    md.offset = offset
    md.use_even_offset = True
    return md


def piatto_vuoto(nome, mat, r_est, r_int, h, seg=32):
    """Anello piatto / disco (monete, piatti della bilancia, aureole piatte)."""
    return DS.lathe(nome, [(r_int, 0.0), (r_est, 0.0), (r_est, h), (r_int, h)], mat, seg=seg, cap_bottom=False)


def toro(nome, R, r, mat, seg=64, sez=12, matrice=None, arco=1.0):
    """Toro (ciambella) attorno all'asse Z locale. UV: u lungo l'anello, v
    attorno al tubo. arco < 1 lascia l'anello aperto."""
    seg, sez = CL.det(seg, 16), CL.det(sez, 5)
    chiuso = arco >= 0.999
    n_u = seg if chiuso else seg + 1
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for i in range(n_u):
        a = TAU * arco * i / seg
        row = []
        for j in range(sez):
            b = TAU * j / sez
            row.append(bm.verts.new(((R + r * cos(b)) * cos(a), (R + r * cos(b)) * sin(a), r * sin(b))))
        grid.append(row)
    for i in range(seg if chiuso else seg):
        i2 = (i + 1) % n_u
        for j in range(sez):
            j2 = (j + 1) % sez
            f = bm.faces.new((grid[i][j], grid[i2][j], grid[i2][j2], grid[i][j2]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (a / seg, b / sez)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = CL.mesh_object(nome, bm, mat)
    if matrice is not None:
        ob.matrix_world = matrice
    return ob


def stella_mesh(nome, punte, r_est, r_int, h, mat, smusso=0.2):
    """Stella piatta a `punte` punte, estrusa (spessore h) con i bordi smussati."""
    bm = bmesh.new()
    pts = []
    for i in range(punte * 2):
        a = pi / 2 + pi * i / punte
        rr = r_est if i % 2 == 0 else r_int
        pts.append((rr * cos(a), rr * sin(a)))
    loops = []
    for z, s in ((-h / 2, 1.0 - smusso * 0.3), (-h / 4, 1.0), (h / 4, 1.0), (h / 2, 1.0 - smusso * 0.3)):
        loops.append([bm.verts.new((x * s, y * s, z)) for x, y in pts])
    for a, b in zip(loops, loops[1:]):
        n = len(pts)
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    c0 = bm.verts.new((0, 0, -h / 2 - h * 0.3))
    c1 = bm.verts.new((0, 0, h / 2 + h * 0.6))
    n = len(pts)
    for i in range(n):
        bm.faces.new((loops[0][(i + 1) % n], loops[0][i], c0))
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % n], c1))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return CL.mesh_object(nome, bm, mat, smooth=False)


def moneta_mesh(nome, r, h, mat, seg=16):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=CL.det(seg, 8), radius1=r, radius2=r,
                          depth=h)
    ob = CL.mesh_object(nome, bm, mat, smooth=False)
    return ob


def billboard(ob):
    """Il piano guarda sempre la camera attiva (vincolo Track To): il bersaglio
    viene collegato quando la camera della scena esiste."""
    con = ob.constraints.new('TRACK_TO')
    con.name = "Guarda_Camera"
    con.track_axis = 'TRACK_Z'
    con.up_axis = 'UP_Y'
    ob["billboard"] = 1
    return con


def collega_billboard():
    cam = bpy.context.scene.camera
    for ob in bpy.data.objects:
        if ob.get("billboard") and cam is not None:
            for con in ob.constraints:
                if con.type == 'TRACK_TO':
                    con.target = cam


# ============================================================================
# SCENA E RENDER (EEVEE Next)
# ============================================================================

SETUP = {
    # look AgX, esposizione, bloom (strength), dimensione bloom
    "angeli": dict(look="Medium High Contrast", esposizione=-0.5, bloom=0.4, size=7),
    "draghi": dict(look="Medium High Contrast", esposizione=-0.5, bloom=0.4, size=7),
    "inferno": dict(look="High Contrast", esposizione=-0.7, bloom=0.5, size=7, vignetta=0.35),
    "mostri": dict(look="Medium High Contrast", esposizione=-0.6, bloom=0.45, size=7, vignetta=0.3),
}


def setup_eevee(look="Medium High Contrast", esposizione=-0.5, bloom=0.4, size=7, streaks=None, vignetta=0.0,
                campioni=64):
    """Setup EEVEE Next comune richiesto per queste serie."""
    sc = bpy.context.scene
    CL.setup_render("EEVEE")
    for ident in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            sc.render.engine = ident
            break
        except TypeError:
            continue
    ev = sc.eevee
    for attr, val in (('taa_render_samples', campioni), ('taa_samples', 16),
                      ('use_raytracing', True), ('ray_tracing_method', 'SCREEN'),
                      ('use_shadows', True), ('shadow_ray_count', 1), ('shadow_step_count', 6),
                      ('light_threshold', 0.001),
                      ('volumetric_tile_size', '2'), ('volumetric_samples', 96),
                      ('volumetric_sample_distribution', 0.8), ('use_volumetric_shadows', True),
                      ('volumetric_end', 60.0), ('use_gtao', True), ('fast_gi_method', 'GLOBAL_ILLUMINATION')):
        if hasattr(ev, attr):
            try:
                setattr(ev, attr, val)
            except (TypeError, ValueError, AttributeError):
                pass
    try:
        rto = ev.ray_tracing_options
        rto.resolution_scale = '2'
        rto.use_denoise = True
    except (AttributeError, TypeError, ValueError):
        pass
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    for nome in ("AgX - " + look, look):
        try:
            vs.look = nome
            break
        except TypeError:
            continue
    vs.exposure = esposizione
    compositor(bloom, size, streaks, vignetta)


def compositor(bloom=0.4, size=7, streaks=None, vignetta=0.0):
    """Glare -> Bloom (Threshold 1.0), Glare -> Streaks (solo dove richiesto) e
    vignettatura leggera (Ellipse Mask + Blur)."""
    sc = bpy.context.scene
    try:
        if hasattr(sc, 'compositing_node_group'):          # Blender 5.x
            ng = bpy.data.node_groups.new("Bagliore", "CompositorNodeTree")
            sc.compositing_node_group = ng
            ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
            rl = ng.nodes.new("CompositorNodeRLayers")
            out = ng.nodes.new("NodeGroupOutput")
            cur = rl.outputs['Image']

            def glare(tipo, vals):
                gl = ng.nodes.new("CompositorNodeGlare")
                for key, val in (('Type', tipo),) + vals:
                    s = gl.inputs.get(key)
                    if s is not None:
                        try:
                            s.default_value = val
                        except (TypeError, ValueError):
                            pass
                return gl

            gl = glare('Bloom', (('Quality', 'High'), ('Threshold', 1.0), ('Strength', bloom),
                                 ('Size', max(0.1, min(1.0, (size - 4) * 0.2)))))
            ng.links.new(cur, gl.inputs['Image'])
            cur = gl.outputs['Image']
            if streaks:
                n, ang, forza = streaks
                gs = glare('Streaks', (('Quality', 'High'), ('Threshold', 1.5), ('Strength', forza),
                                       ('Streaks', n), ('Streaks Angle', radians(ang)), ('Fade', 0.9)))
                ng.links.new(cur, gs.inputs['Image'])
                cur = gs.outputs['Image']
            ng.links.new(cur, out.inputs[0])
        else:                                              # Blender 4.x
            sc.use_nodes = True
            nt = sc.node_tree
            nt.nodes.clear()
            rl = nt.nodes.new("CompositorNodeRLayers")
            gl = nt.nodes.new("CompositorNodeGlare")
            gl.glare_type = 'BLOOM'
            gl.quality = 'HIGH'
            gl.threshold = 1.0
            gl.size = int(max(6, min(9, size)))
            gl.mix = max(-1.0, min(1.0, bloom - 1.0))
            nt.links.new(rl.outputs['Image'], gl.inputs['Image'])
            cur = gl.outputs['Image']
            if streaks:
                n, ang, forza = streaks
                gs = nt.nodes.new("CompositorNodeGlare")
                gs.glare_type = 'STREAKS'
                gs.quality = 'HIGH'
                gs.threshold = 1.5
                gs.streaks = n
                gs.angle_offset = radians(ang)
                gs.fade = 0.9
                gs.mix = max(-1.0, min(1.0, forza - 1.0))
                nt.links.new(cur, gs.inputs['Image'])
                cur = gs.outputs['Image']
            if vignetta:
                em = nt.nodes.new("CompositorNodeEllipseMask")
                em.x, em.y = 0.5, 0.5
                em.mask_width, em.mask_height = 0.95, 0.85
                em.inputs['Value'].default_value = 1.0
                bl = nt.nodes.new("CompositorNodeBlur")
                bl.filter_type = 'FAST_GAUSS'
                bl.use_relative = True
                bl.factor_x = bl.factor_y = 25.0
                nt.links.new(em.outputs['Mask'], bl.inputs['Image'])
                mx = nt.nodes.new("CompositorNodeMixRGB")
                mx.blend_type = 'MULTIPLY'
                mx.inputs[0].default_value = vignetta
                nt.links.new(cur, mx.inputs[1])
                nt.links.new(bl.outputs['Image'], mx.inputs[2])
                cur = mx.outputs['Image']
            comp = nt.nodes.new("CompositorNodeComposite")
            nt.links.new(cur, comp.inputs['Image'])
            try:
                vw = nt.nodes.new("CompositorNodeViewer")
                nt.links.new(cur, vw.inputs['Image'])
            except Exception:
                pass
    except Exception as exc:
        print("[creature] compositor non configurato:", exc)


def mondo(colore_basso, colore_alto, forza=1.0, nome="Cielo"):
    """Sfondo a gradiente verticale."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new(nome)
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
    cr.elements[0].position = 0.45
    cr.elements[0].color = tuple(rgb(colore_basso)) + (1.0,)
    cr.elements[1].position = 0.85
    cr.elements[1].color = tuple(rgb(colore_alto)) + (1.0,)
    mp = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], mp.inputs['Value'])
    mp.inputs['From Min'].default_value = -1.0
    mp.inputs['From Max'].default_value = 1.0
    nt.links.new(mp.outputs[0], ramp.inputs[0])
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = forza
    nt.links.new(ramp.outputs[0], bg.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def pavimento(nome, c1, c2, scala=0.8, rough=(0.6, 0.9), size=200.0, bump=0.3, lucido=None):
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    nz = nb.noise(tc.outputs['Object'], scala, 6.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, rgb(c1)), (0.7, rgb(c2))])
    rg = nb.maprange(nz.outputs['Fac'], 0.3, 0.7, rough[0], rough[1])
    pb = nb.principled(base=col, rough=rg, spec=0.4)
    fine = nb.noise(tc.outputs['Object'], scala * 12, 6.0, 0.6)
    nb.set(pb, 'Normal', nb.bump(fine.outputs['Fac'], bump, 0.01))
    sh = pb.outputs[0]
    if lucido is not None:
        c, s, sc_ = lucido
        vo = nb.voronoi(tc.outputs['Object'], sc_, 'DISTANCE_TO_EDGE')
        m = nb.math('MULTIPLY', nb.maprange(vo.outputs['Distance'], 0.03, 0.0),
                    nb.maprange(nb.noise(tc.outputs['Object'], 0.3, 2.0, 0.5).outputs['Fac'], 0.45, 0.65))
        sh = nb.add_shader(sh, nb.emission(colore(nb, c), nb.math('MULTIPLY', m, s)))
    nb.output(sh)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    return CL.mesh_object("Terreno", bm, mat, smooth=False)


def luci_studio(which, chiave=6000, contro=(0.6, 0.7, 1.0), riempimento=(0.85, 0.88, 1.0), forza=1.0):
    """Tre luci d'area (chiave, controluce, riempimento) puntate sulla creatura
    (o sul centro del gruppo): servono a leggere le forme scure accanto agli
    organi luminosi."""
    gruppo = which == "tutte"
    t = V((0, 2.4, 0.8)) if gruppo else V((0, 0, 0.7))
    dist = 9.0 if gruppo else 4.5
    k = forza * (dist / 5.0) ** 2
    out = []
    for nome, off, P, c, size in (("Luce_Chiave", (-0.55, -0.75, 0.65), 700.0, chiave, 3.0),
                                   ("Luce_Controluce", (0.45, 0.85, 0.55), 1000.0, contro, 3.0),
                                   ("Luce_Riempimento", (0.85, -0.5, 0.2), 220.0, riempimento, 4.0)):
        ob = luce(nome, 'AREA', t + V(off).normalized() * dist, P * k, c, size * (1.6 if gruppo else 1.0))
        CL.aim(ob, t)
        out.append(ob)
    return out


def nebbia(nome, centro, dim, c, densita, luce_c=None, forza=0.0, anisotropia=0.3):
    """Cubo di foschia volumetrica (Volume Scatter) per la scena."""
    mat = CL.new_material(nome)
    nb = CL.NodeBuilder(mat)
    pv = nb.node('ShaderNodeVolumePrincipled')
    nb.set(pv, 'Color', rgb(c))
    nb.set(pv, 'Density', densita)
    nb.set(pv, 'Anisotropy', anisotropia)
    if luce_c is not None:
        nb.set(pv, 'Emission Color', colore(nb, luce_c))
        nb.set(pv, 'Emission Strength', forza)
    nb.link(pv.outputs[0], nb.out.inputs['Volume'])
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    ob = CL.mesh_object(nome, bm, mat, smooth=False)
    ob.location = centro
    ob.scale = dim
    ob.visible_shadow = False
    ob["rbx_drop"] = 1
    return ob


def build_serie(registro, disposizione, which, scena_gruppo, scene=None, camera_gruppo=None, setup=None,
                engine=None, clean=None):
    """Costruisce una creatura (o tutta la serie) con la sua scena."""
    which = (which or "tutte").lower()
    if clean if clean is not None else CL.PULISCI_SCENA:
        CL.clear_scene()
    setup_eevee(**(setup or {}))
    if engine and engine.upper() == "CYCLES":
        bpy.context.scene.render.engine = 'CYCLES'
    base = CL.new_collection("Scena")
    CL.set_collection(base)
    scena_gruppo(which)
    CL.set_collection(None)
    if which == "tutte":
        for k in registro:
            x, y, rz = disposizione[k]
            CL.build_one(k, (x, y, 0), rot_z=rz, registry=registro)
        CL.setup_camera(*camera_gruppo)
    else:
        if which not in registro:
            raise ValueError("Creatura sconosciuta: %s (scegli tra %s o 'tutte')" % (which, ", ".join(registro)))
        CL.build_one(which, registry=registro)
        tgt, dist, el, az, lens = registro[which][2]
        CL.setup_camera(tgt, dist, el, az, lens)
        if scene and which in scene:
            CL.set_collection(base)
            scene[which]()
            CL.set_collection(None)
    collega_billboard()
    CL.setup_viewport()
    bpy.context.scene.frame_set(1)


def main(build):
    """Come il main di creature_luminose.py, ma le anteprime si fanno con
    EEVEE Next (il motore del setup), con --campioni campioni TAA."""
    opts = CL._cli_args()
    if opts is None:
        build()
        return
    build(opts.get("creatura"), opts.get("motore"))
    sc = bpy.context.scene
    if opts.get("salva"):
        path = os.path.abspath(opts["salva"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print("[creature] salvato:", path)
    if opts.get("render"):
        path = os.path.abspath(opts["render"])
        n = int(opts.get("campioni", 64))
        if str(opts.get("motore-render", "eevee")).lower() == "cycles":
            sc.render.engine = 'CYCLES'
            sc.cycles.samples = n
            sc.cycles.use_denoising = True
        else:
            sc.eevee.taa_render_samples = n
        res = opts.get("risoluzione", "960x540").split("x")
        sc.render.resolution_x, sc.render.resolution_y = int(res[0]), int(res[1])
        sc.render.resolution_percentage = 100
        if opts.get("debug-luce"):
            bg = sc.world.node_tree.nodes.get('Background')
            bg.inputs['Strength'].default_value = 8.0
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("[creature] render:", path)


def verifica_statico():
    """Controllo: nessun driver e nessuna animazione nella scena."""
    n = 0
    for coll in (bpy.data.objects, bpy.data.materials, bpy.data.lights, bpy.data.node_groups):
        for idb in coll:
            ad = getattr(idb, "animation_data", None)
            if ad is not None and (ad.drivers or ad.action):
                n += 1
            nt = getattr(idb, "node_tree", None)
            if nt is not None and nt.animation_data is not None and nt.animation_data.drivers:
                n += 1
    return n
