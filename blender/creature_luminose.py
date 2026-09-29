# -*- coding: utf-8 -*-
"""
CREATURE LUMINOSE - generatore procedurale di 8 creature bioluminescenti per Blender.

    01  MANTE-LUCE               (mantide religiosa con ali a vetrata)
    02  GATTOLUNA                (gatto nero con ali di pura luce)
    03  GUFO-SCINTILLA           (gufo con piume dai bordi al neon)
    04  RANABUIO                 (rana scura con sacca vocale luminosa)
    05  FARFALLA-GLOW            (farfalla zaffiro / smeraldo)
    06  LIBELLULA-FULMINE        (libellula con venature a circuito)
    07  LUPO-LUCE                (lupo spettrale semitrasparente)
    08  LA PICCOLA LUCINA FARFALLINA (il "brainrot moth" con la lampadina)

USO DENTRO BLENDER (3.6, 4.x, 5.x)
    1. Apri Blender, vai nel workspace "Scripting".
    2. Text > Open... e scegli questo file.
    3. Cambia CREATURA qui sotto (oppure lascia "tutte").
    4. Premi "Run Script" (Alt+P).
    Guarda il risultato in Material Preview o Rendered (Z > Rendered).

USO DA RIGA DI COMANDO
    blender --background --python creature_luminose.py -- \
            --creatura gatto --salva gatto.blend --render gatto.png

Le animazioni (pulsazioni, battito d'ali, lampadina che dondola) sono fatte
con driver "semplici" (sin(frame)), quindi funzionano anche senza abilitare
l'esecuzione automatica degli script Python. Premi Play (Spazio) per vederle.
"""

import bpy
import bmesh
import math
import os
import random
import sys
from math import cos, pi, radians, sin

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# "mantide", "gatto", "gufo", "rana", "farfalla", "libellula", "lupo",
# "falena" oppure "tutte"
CREATURA = "tutte"

# Cancella tutto quello che c'e' nella scena prima di costruire
PULISCI_SCENA = True

# "EEVEE" (veloce, ottimo per il viewport) oppure "CYCLES" (piu' realistico)
MOTORE = "EEVEE"

# Moltiplicatore globale di tutte le emissioni e delle luci delle creature.
# Alzalo (es. 1.5) per creature piu' abbaglianti, abbassalo (0.6) per un
# effetto piu' soffuso.
INTENSITA_LUCE = 1.0

# Livello di dettaglio delle mesh (1 = pieno). L'esportatore per Roblox lo
# abbassa automaticamente per restare sotto i 20.000 triangoli per creatura.
DETTAGLIO = 1.0

# Durata del ciclo di animazione (frame). Tutte le pulsazioni si ripetono
# perfettamente ogni ANIM_FRAMES frame.
ANIM_FRAMES = 120

# ============================================================================
# UTILITA' GENERALI
# ============================================================================

BL = bpy.app.version
TAU = 2.0 * pi
# coll: collezione corrente; texspace: oggetto (empty) le cui coordinate fanno
# da "spazio texture" per i materiali dei pezzi fissi (vedi NodeBuilder.texcoord)
_STATE = {"coll": None, "texspace": None}

# Registro delle animazioni create (usato dall'esportatore per Roblox)
ANIMAZIONI = []
# Valori "a riposo" delle proprieta' guidate da driver (prima dell'animazione)
VALORI_RIPOSO = []
_LAYOUT_RNG = random.Random(7)


def vec(v):
    return Vector(v)


def det(n, minimo):
    """Numero di suddivisioni scalato dal livello di DETTAGLIO."""
    return max(minimo, int(round(n * DETTAGLIO)))


def set_collection(coll):
    _STATE["coll"] = coll


def link(ob):
    coll = _STATE["coll"] or bpy.context.scene.collection
    coll.objects.link(ob)
    return ob


def new_collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def shade_smooth(me):
    try:
        me.shade_smooth()
    except AttributeError:
        for p in me.polygons:
            p.use_smooth = True


def mesh_object(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if mat is not None:
        me.materials.append(mat)
    if smooth:
        shade_smooth(me)
    return ob


def add_subsurf(ob, levels=1, render=2):
    md = ob.modifiers.new("Subdivision", 'SUBSURF')
    md.levels = levels
    md.render_levels = render
    return md


def no_shadow(ob):
    """Oggetti di pura luce: non proiettano ombre scure."""
    for attr in ("visible_shadow",):
        if hasattr(ob, attr):
            setattr(ob, attr, False)
    return ob


def sphere(name, loc, size, mat=None, rot=(0, 0, 0), seg=32, rings=16,
           subsurf=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=det(seg, 8), v_segments=det(rings, 5),
                              radius=1.0)
    ob = mesh_object(name, bm, mat)
    if isinstance(size, (int, float)):
        size = (size, size, size)
    ob.location = loc
    ob.scale = size
    ob.rotation_euler = [radians(a) for a in rot]
    if subsurf:
        add_subsurf(ob, subsurf, subsurf + 1)
    return ob


def cone_between(name, base, tip, r_base, r_tip=0.0, mat=None, seg=12):
    """Cono (o tronco di cono) dal punto base al punto tip."""
    base, tip = vec(base), vec(tip)
    d = tip - base
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=det(seg, 5),
                          radius1=r_base, radius2=max(r_tip, 0.0),
                          depth=d.length)
    bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=bm.verts)
    ob = mesh_object(name, bm, mat)
    ob.location = base
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return ob


def tube(name, pts, radii, mat=None, res=12, bevel_res=4, caps=True,
         poly=False):
    """Tubo morbido lungo una curva di Bezier; raggio diverso per ogni punto."""
    if isinstance(radii, (int, float)):
        radii = [radii] * len(pts)
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = det(bevel_res, 1) if bevel_res else 0
    cu.resolution_u = det(res, 2)
    try:
        cu.use_fill_caps = caps
    except AttributeError:
        pass
    if poly:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p, c, r in zip(sp.points, pts, radii):
            p.co = (c[0], c[1], c[2], 1.0)
            p.radius = r
    else:
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts) - 1)
        for bp, c, r in zip(sp.bezier_points, pts, radii):
            bp.co = c
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
            bp.radius = r
    ob = bpy.data.objects.new(name, cu)
    link(ob)
    if mat is not None:
        cu.materials.append(mat)
    return ob


def empty(name, loc=(0, 0, 0), size=0.2):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    ob.location = loc
    link(ob)
    return ob


def add_driver(owner, path, expr, index=-1, meta=None):
    """Driver con espressione semplice. `meta` descrive l'animazione in forma
    leggibile per l'esportazione (es. tipo='rot', amp, cyc, ph)."""
    try:
        cur = getattr(owner, path)
        VALORI_RIPOSO.append((owner, path, index, cur[index] if index >= 0 else cur))
    except (AttributeError, TypeError, IndexError):
        pass
    fc = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = expr
    if meta is not None:
        ANIMAZIONI.append(dict(owner=owner, path=path, index=index, **meta))
    return fc


def wave(lo, hi, cycles=1, phase=0.0, sharp=False):
    """Espressione driver che oscilla tra lo e hi, `cycles` volte ogni ANIM_FRAMES."""
    w = TAU * cycles / ANIM_FRAMES
    s = "(0.5+0.5*sin(frame*%.6f+%.4f))" % (w, phase)
    if sharp:
        s = "%s*%s" % (s, s)
    return "%.4f+%.4f*%s" % (lo, hi - lo, s)


# ----------------------------------------------------------------------------
# Metaball -> mesh (corpi organici morbidi)
# ----------------------------------------------------------------------------

def ball(co, r, **kw):
    d = dict(type='BALL', co=co, r=r)
    d.update(kw)
    return d


def ellipsoid(co, r, size, **kw):
    d = dict(type='ELLIPSOID', co=co, r=r, size=size)
    d.update(kw)
    return d


def capsule(a, b, r, **kw):
    """Capsula metaball dal punto a al punto b."""
    a, b = vec(a), vec(b)
    d = b - a
    q = Vector((1, 0, 0)).rotation_difference(d)
    out = dict(type='CAPSULE', co=(a + b) / 2, r=r, size=(d.length / 2, 1, 1),
               rot=q)
    out.update(kw)
    return out


def metaball_mesh(name, elems, mat=None, res=0.03, threshold=0.6):
    mb = bpy.data.metaballs.new(name + "_MB")
    res = res / max(DETTAGLIO, 0.1)
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = threshold
    for e in elems:
        el = mb.elements.new(type=e.get('type', 'BALL'))
        el.co = e['co']
        el.radius = e['r']
        if 'size' in e:
            el.size_x, el.size_y, el.size_z = e['size']
        if 'rot' in e:
            el.rotation = e['rot']
        if 'stiff' in e:
            el.stiffness = e['stiff']
        if e.get('neg'):
            el.use_negative = True
    tmp = bpy.data.objects.new(name.replace(".", "_") + "_MB", mb)
    link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.metaballs.remove(mb)
    me.name = name
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if mat is not None:
        me.materials.clear()
        me.materials.append(mat)
    shade_smooth(me)
    return ob


def bvh_of(ob):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def surface_hit(bvh, center, direction, far=6.0):
    """Punto sulla superficie colpendo dall'esterno verso `center`."""
    d = vec(direction).normalized()
    origin = vec(center) + d * far
    loc, nor, _i, _d = bvh.ray_cast(origin, -d)
    if loc is None:
        return None, None
    if nor.dot(d) < 0:
        nor = -nor
    return loc, nor


def frame_matrix(loc, y_axis, z_axis):
    """Matrice con asse Y lungo y_axis e asse Z lungo (circa) z_axis."""
    z = vec(z_axis).normalized()
    y = vec(y_axis)
    y = (y - z * y.dot(z)).normalized()
    x = y.cross(z).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = loc
    return m


def orient(ob, loc, normal, up=(0, 0, 1), scale=(1, 1, 1)):
    """Allinea l'asse Z locale dell'oggetto alla normale data."""
    m = frame_matrix(loc, up, normal)
    ob.matrix_world = m @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    return ob


def make_eye(prefix, bvh, center, direction, radius, iris_mat, pupil_mat=None,
             cornea_mat=None, pupil=(0.25, 0.8), sink=0.35, up=(0, 0, 1),
             flat=0.75):
    """Occhio posizionato sulla superficie (raycast dal centro della testa).
    pupil = (larghezza, altezza) relative al raggio (fessura se stretta)."""
    loc, nor = surface_hit(bvh, center, direction)
    if loc is None:
        loc, nor = vec(center) + vec(direction).normalized() * radius, vec(direction).normalized()
    nor = (nor + vec(direction).normalized()).normalized()
    c = loc - nor * radius * sink
    eye = sphere(prefix, (0, 0, 0), 1.0, iris_mat, seg=32, rings=16)
    orient(eye, c, nor, up, (radius, radius, radius * flat))
    obs = [eye]
    if pupil_mat is not None and pupil:
        pw, ph = pupil
        pp = sphere(prefix + "_Pupilla", (0, 0, 0), 1.0, pupil_mat, seg=24, rings=12)
        orient(pp, c + nor * radius * flat * 0.93, nor, up,
               (radius * pw, radius * ph, radius * 0.12))
        obs.append(pp)
    if cornea_mat is not None:
        co = sphere(prefix + "_Cornea", (0, 0, 0), 1.0, cornea_mat, seg=32, rings=16)
        orient(co, c + nor * radius * 0.04, nor, up,
               (radius * 1.04, radius * 1.04, radius * flat * 1.08))
        no_shadow(co)
        obs.append(co)
    return obs


# ----------------------------------------------------------------------------
# Ali (mesh a ventaglio con UV: u = lungo il bordo, v = dalla base al bordo)
# ----------------------------------------------------------------------------

def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def wing_outline(ctrl, n=64, scallop=None):
    """ctrl = [(angolo_gradi, raggio), ...] dal bordo d'attacco a quello d'uscita.
    Angolo 0 = +X (verso l'esterno), 90 = +Y (verso la coda)."""
    n = det(n, 16)
    angs = [radians(a) for a, _r in ctrl]
    rs = [r for _a, r in ctrl]
    k = len(ctrl)

    def g(arr, j):
        return arr[max(0, min(k - 1, j))]

    pts = []
    for i in range(n):
        f = i / (n - 1) * (k - 1)
        j = min(int(f), k - 2)
        s = f - j
        a = _catmull(g(angs, j - 1), g(angs, j), g(angs, j + 1), g(angs, j + 2), s)
        r = _catmull(g(rs, j - 1), g(rs, j), g(rs, j + 1), g(rs, j + 2), s)
        if scallop:
            amp, cnt = scallop
            t = i / (n - 1)
            r *= 1.0 - amp * (0.5 - 0.5 * cos(TAU * cnt * t)) * sin(pi * t)
        pts.append((r * cos(a), r * sin(a)))
    return pts


def wing_mesh(name, outline, mat=None, rings=14, cup=0.0, droop=0.0,
              mirror=False, r0=0.03):
    rings = det(rings, 3)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    n = len(outline)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + math.dist(outline[i], outline[i - 1]))
    us = [a / acc[-1] for a in acc]
    grid, uvs = [], {}
    for j in range(rings + 1):
        v = r0 + (1.0 - r0) * (j / rings)
        row = []
        for i, (x, y) in enumerate(outline):
            px, py = x * v, y * v
            rr = math.hypot(px, py)
            z = cup * v * v * sin(pi * us[i]) - droop * rr * rr
            if mirror:
                px = -px
            bv = bm.verts.new((px, py, z))
            uvs[bv] = (us[i], v)
            row.append(bv)
        grid.append(row)
    for j in range(rings):
        for i in range(n - 1):
            quad = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            if mirror:
                quad.reverse()
            f = bm.faces.new(quad)
            for loop in f.loops:
                loop[uv_layer].uv = uvs[loop.vert]
    ob = mesh_object(name, bm, mat)
    no_shadow(ob)
    return ob


def place_wing(ob, attach, elev, sweep, roll=0.0, left=False):
    s = -1.0 if left else 1.0
    ob.location = attach
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = (radians(roll), radians(-elev) * s, radians(sweep) * s)


def wing_pair(prefix, ctrl, mat, attach, elev, sweep, roll=0.0, rings=14,
              cup=0.0, droop=0.0, flap=None, n=64, scallop=None):
    """Crea ala destra e sinistra. flap = (ampiezza_gradi, cicli, fase)."""
    outline = wing_outline(ctrl, n, scallop)
    obs = []
    for left in (False, True):
        side = "L" if left else "R"
        ob = wing_mesh("%s_%s" % (prefix, side), outline, mat, rings=rings,
                       cup=cup, droop=droop, mirror=left)
        ax = vec(attach)
        if left:
            ax.x = -ax.x
        if flap:
            amp, cyc, ph = flap
            piv = empty("%s_Perno_%s" % (prefix, side), ax, 0.05)
            place_wing(ob, (0, 0, 0), elev, sweep, roll, left)
            ob.parent = piv
            sign = 1 if left else -1
            w = TAU * cyc / ANIM_FRAMES
            add_driver(piv, "rotation_euler",
                       "%d*radians(%.3f)*sin(frame*%.6f+%.3f)" % (sign, amp, w, ph), 1,
                       meta=dict(tipo='rot', amp=sign * radians(amp), cyc=cyc, ph=ph))
        else:
            place_wing(ob, ax, elev, sweep, roll, left)
        obs.append(ob)
    return obs


# ============================================================================
# MATERIALI (nodi) - compatibili con Blender 3.6 / 4.x / 5.x
# ============================================================================

PRINCIPLED_ALIASES = {
    'base': ('Base Color',),
    'metal': ('Metallic',),
    'rough': ('Roughness',),
    'alpha': ('Alpha',),
    'ior': ('IOR',),
    'sss': ('Subsurface Weight', 'Subsurface'),
    'sss_radius': ('Subsurface Radius',),
    'spec': ('Specular IOR Level', 'Specular'),
    'trans': ('Transmission Weight', 'Transmission'),
    'coat': ('Coat Weight', 'Clearcoat'),
    'coat_rough': ('Coat Roughness', 'Clearcoat Roughness'),
    'sheen': ('Sheen Weight', 'Sheen'),
    'sheen_tint': ('Sheen Tint',),
    'emit': ('Emission Color', 'Emission'),
    'emit_str': ('Emission Strength',),
    'normal': ('Normal',),
}


class NodeBuilder:
    def __init__(self, mat):
        if BL < (5, 0, 0):
            mat.use_nodes = True
        elif mat.node_tree is None:
            mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')
        self.out.location = (900, 0)
        self._x = -1200

    def node(self, typ, inputs=None, **props):
        nd = self.nt.nodes.new(typ)
        nd.location = (self._x, _LAYOUT_RNG.uniform(-600, 600))
        self._x = min(self._x + 60, 600)
        for k, v in props.items():
            setattr(nd, k, v)
        for k, v in (inputs or {}).items():
            self.set(nd, k, v)
        return nd

    def socket(self, node, key):
        if isinstance(key, int):
            return node.inputs[key]
        names = key if isinstance(key, tuple) else (key,)
        for nm in names:
            s = node.inputs.get(nm)
            if s is not None:
                return s
        return None

    def set(self, node, key, val):
        s = self.socket(node, key)
        if s is None:
            return None
        if isinstance(val, bpy.types.NodeSocket):
            self.nt.links.new(val, s)
        else:
            if getattr(s, 'type', '') == 'RGBA' and len(val) == 3:
                val = (val[0], val[1], val[2], 1.0)
            try:
                s.default_value = val
            except (TypeError, ValueError):
                pass
        return s

    def link(self, a, b):
        self.nt.links.new(a, b)

    def output(self, shader_socket):
        self.link(shader_socket, self.out.inputs['Surface'])

    # ---- matematica ------------------------------------------------------
    def math(self, op, a, b=0.0, clamp=False):
        nd = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, nd.inputs[i])
            else:
                nd.inputs[i].default_value = v
        return nd.outputs[0]

    def maprange(self, val, fmin, fmax, tmin=0.0, tmax=1.0, smooth=True):
        nd = self.node('ShaderNodeMapRange', clamp=True)
        if smooth:
            nd.interpolation_type = 'SMOOTHSTEP'
        self.set(nd, 'Value', val)
        self.set(nd, 'From Min', fmin)
        self.set(nd, 'From Max', fmax)
        self.set(nd, 'To Min', tmin)
        self.set(nd, 'To Max', tmax)
        return nd.outputs[0]

    def ramp(self, fac, stops, interp='LINEAR'):
        nd = self.node('ShaderNodeValToRGB')
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        for i, (pos, col) in enumerate(stops):
            el = cr.elements[0] if i == 0 else cr.elements.new(pos)
            el.position = pos
            el.color = (col[0], col[1], col[2], col[3] if len(col) > 3 else 1.0)
        self.link(fac, nd.inputs[0])
        return nd.outputs[0]

    def glow(self, strength, pulse=None):
        """Valore di emissione (scalato da INTENSITA_LUCE), eventualmente pulsante."""
        k = INTENSITA_LUCE
        if pulse:
            lo, hi = pulse[0], pulse[1]
            rest = tuple(pulse[2:])
            if "rbx_pulse" not in self.mat:
                cyc = rest[0] if rest else 1
                ph = rest[1] if len(rest) > 1 else 0.0
                self.mat["rbx_pulse"] = [lo / max(hi, 1e-6), 1.0, float(cyc), float(ph)]
            return self.value(strength * k, wave(lo * k, hi * k, *rest))
        return self.value(strength * k)

    def value(self, v, driver=None):
        nd = self.node('ShaderNodeValue')
        nd.outputs[0].default_value = v
        if driver:
            add_driver(nd.outputs[0], "default_value", driver)
        return nd.outputs[0]

    def principled(self, **kw):
        nd = self.node('ShaderNodeBsdfPrincipled')
        for k, v in kw.items():
            if v is None:
                continue
            self.set(nd, PRINCIPLED_ALIASES.get(k, (k,)), v)
        return nd

    def emission(self, color, strength):
        return self.node('ShaderNodeEmission',
                         {'Color': color, 'Strength': strength}).outputs[0]

    def bake_output(self, name, shader_socket):
        """Uscita non collegata, usata solo per 'cuocere' le texture per Roblox.
        Non cambia il render in Blender."""
        nd = shader_socket.node
        nd.name = name
        nd.label = name + " (bake Roblox)"
        return nd

    def mix_shader(self, fac, a, b):
        nd = self.node('ShaderNodeMixShader')
        self.set(nd, 0, fac)
        self.link(a, nd.inputs[1])
        self.link(b, nd.inputs[2])
        return nd.outputs[0]

    def add_shader(self, a, b):
        nd = self.node('ShaderNodeAddShader')
        self.link(a, nd.inputs[0])
        self.link(b, nd.inputs[1])
        return nd.outputs[0]

    def transparent(self):
        return self.node('ShaderNodeBsdfTransparent').outputs[0]

    def facing(self, blend=0.5):
        return self.node('ShaderNodeLayerWeight', {'Blend': blend}).outputs['Facing']

    def fresnel(self, blend=0.3):
        return self.node('ShaderNodeLayerWeight', {'Blend': blend}).outputs['Fresnel']

    def texcoord(self, use_space=True):
        """Coordinate texture. Se e' impostato uno spazio texture comune
        (_STATE['texspace']), le coordinate 'Object' sono misurate rispetto a
        quello: cosi' i pattern restano uguali anche dopo aver unito i pezzi
        (utile per l'esportazione con texture cotte)."""
        nd = self.node('ShaderNodeTexCoord')
        if use_space and _STATE.get("texspace") is not None:
            nd.object = _STATE["texspace"]
        return nd

    def bump(self, height, strength=0.3, distance=0.02):
        nd = self.node('ShaderNodeBump', {'Strength': strength, 'Distance': distance})
        self.link(height, nd.inputs['Height'])
        return nd.outputs['Normal']

    def noise(self, vector, scale=5.0, detail=4.0, rough=0.5):
        nd = self.node('ShaderNodeTexNoise', {'Scale': scale, 'Detail': detail,
                                              'Roughness': rough})
        if vector is not None:
            self.link(vector, nd.inputs['Vector'])
        return nd

    def voronoi(self, vector, scale=5.0, feature='F1', randomness=1.0):
        nd = self.node('ShaderNodeTexVoronoi', feature=feature)
        self.set(nd, 'Scale', scale)
        self.set(nd, 'Randomness', randomness)
        if vector is not None:
            self.link(vector, nd.inputs['Vector'])
        return nd


def new_material(name):
    return bpy.data.materials.new(name)


def set_transparent(mat, blended=True):
    """Impostazioni di trasparenza per EEVEE (legacy e Next)."""
    if hasattr(mat, 'surface_render_method'):
        try:
            mat.surface_render_method = 'BLENDED' if blended else 'DITHERED'
        except (TypeError, ValueError):
            pass
    elif hasattr(mat, 'blend_method'):
        try:
            mat.blend_method = 'BLEND' if blended else 'HASHED'
        except (TypeError, ValueError):
            pass
    if hasattr(mat, 'shadow_method'):
        try:
            mat.shadow_method = 'NONE'
        except (TypeError, ValueError):
            pass
    for attr, val in (('use_backface_culling', False),
                      ('show_transparent_back', True),
                      ('use_transparent_shadow', True)):
        if hasattr(mat, attr):
            try:
                setattr(mat, attr, val)
            except (TypeError, ValueError, AttributeError):
                pass
    return mat


def diffuse_display(mat, color):
    """Colore visibile nel viewport in modalita' Solid."""
    try:
        mat.diffuse_color = (color[0], color[1], color[2], 1.0)
    except Exception:
        pass


def m_emit(name, color, strength, pulse=None):
    """Emissione pura. pulse = (min, max, cicli, fase)."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    s = nb.glow(strength, pulse)
    nb.output(nb.emission(color, s))
    diffuse_display(mat, color)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(color[:3])
    return mat


def m_body(name, base, rough=0.45, metal=0.0, coat=0.0, coat_rough=0.05,
           sss=0.0, sss_radius=None, sheen=0.0, sheen_tint=None, spec=0.5,
           emit=None, emit_str=0.0, emit_pulse=None, emit_center=False,
           rim=None, rim_str=0.0, rim_power=0.35,
           bump=None, mottle=None, alpha=None, transparent_blend=False):
    """Materiale organico generico.
    emit_pulse = (min, max, cicli, fase) -> emissione pulsante.
    emit_center = emissione piu' forte al centro (effetto lanterna).
    rim = colore del bagliore sui contorni (riflessi / aura).
    bump = (scala, forza, tipo) tipo in {'noise', 'warts', 'scales'}.
    mottle = (colore2, scala) -> macchie di colore.
    alpha = opacita' (per corpi semitrasparenti)."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord()
    base_col = base
    if mottle:
        col2, msc = mottle
        nz = nb.noise(tc.outputs['Object'], msc, 6.0, 0.6)
        base_col = nb.ramp(nz.outputs['Fac'], [(0.35, base), (0.65, col2)])
    normal = None
    if bump:
        bsc, bstr, kind = bump
        if kind == 'warts':
            vo = nb.voronoi(tc.outputs['Object'], bsc)
            h = nb.maprange(vo.outputs['Distance'], 0.0, 0.5, 1.0, 0.0)
            nz = nb.noise(tc.outputs['Object'], bsc * 3.0, 8.0, 0.6)
            h = nb.math('ADD', h, nb.math('MULTIPLY', nz.outputs['Fac'], 0.6))
        elif kind == 'scales':
            vo = nb.voronoi(tc.outputs['Object'], bsc, 'DISTANCE_TO_EDGE')
            h = nb.maprange(vo.outputs['Distance'], 0.0, 0.08, 0.0, 1.0)
        else:
            h = nb.noise(tc.outputs['Object'], bsc, 8.0, 0.6).outputs['Fac']
        normal = nb.bump(h, bstr, 0.01)
    bsdf = nb.principled(base=base_col, rough=rough, metal=metal, coat=coat,
                         coat_rough=coat_rough, sss=sss, sss_radius=sss_radius,
                         sheen=sheen, sheen_tint=sheen_tint, spec=spec)
    if normal is not None:
        nb.set(bsdf, 'Normal', normal)
        if coat:
            nb.set(bsdf, ('Coat Normal', 'Clearcoat Normal'), normal)
    shader = bsdf.outputs[0]
    if alpha is not None:
        shader = nb.mix_shader(alpha, nb.transparent(), shader)
        set_transparent(mat, blended=transparent_blend)
    if emit is not None and (emit_str or emit_pulse):
        s = nb.glow(emit_str, emit_pulse)
        if emit_center:
            f = nb.facing(0.45)
            core = nb.maprange(f, 0.0, 0.85, 1.0, 0.15)
            s = nb.math('MULTIPLY', s, core)
        shader = nb.add_shader(shader, nb.emission(emit, s))
    if rim is not None and rim_str:
        f = nb.facing(0.5)
        r = nb.maprange(f, rim_power, 1.0, 0.0, rim_str * INTENSITA_LUCE)
        shader = nb.add_shader(shader, nb.emission(rim, r))
    nb.output(shader)
    diffuse_display(mat, base)
    # descrizione per l'esportazione Roblox
    top = max(emit_str, emit_pulse[1] if emit_pulse else 0.0) if emit is not None else 0.0
    mat["rbx_color"] = list(base[:3])
    mat["rbx_rough"] = float(rough)
    mat["rbx_metal"] = float(metal)
    if top >= 1.0:
        mat["rbx_kind"] = "neon"
        mat["rbx_color"] = list(emit[:3])
        if alpha is not None:
            mat["rbx_transp"] = round(1.0 - alpha, 3)
    elif mottle:
        mat["rbx_kind"] = "bake"
        nb.bake_output("RBX_COLOR", nb.emission(base_col, 1.0))
        if bump:
            mat["rbx_normal"] = 1
    else:
        mat["rbx_kind"] = "solid"
        if emit is not None and top > 0:
            mat["rbx_glow"] = list(emit[:3])
    if rim is not None and rim_str >= 1.0:
        mat["rbx_highlight"] = list(rim[:3])
    return mat


def m_glass_eye(name, tint=(1, 1, 1)):
    """Cornea lucida: quasi trasparente con riflessi."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    gl = nb.node('ShaderNodeBsdfGlossy', {'Color': tint, 'Roughness': 0.03})
    fr = nb.fresnel(0.15)
    fac = nb.maprange(fr, 0.0, 1.0, 0.12, 1.0, smooth=False)
    nb.output(nb.mix_shader(fac, nb.transparent(), gl.outputs[0]))
    set_transparent(mat)
    diffuse_display(mat, (0.8, 0.9, 1.0))
    mat["rbx_kind"] = "drop"          # le cornee non servono su Roblox
    return mat


def m_halo(name, color, strength, pulse=None, softness=2.0):
    """Aura luminosa morbida: volume che emette luce, piu' denso al centro.
    Funziona su sfere (anche schiacciate): sfuma a zero sul bordo."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    vm = nb.node('ShaderNodeVectorMath', operation='LENGTH')
    nb.link(tc.outputs['Object'], vm.inputs[0])
    fall = nb.maprange(vm.outputs['Value'], 0.0, 1.0, 1.0, 0.0, smooth=False)
    fall = nb.math('POWER', fall, softness)
    s = nb.glow(strength, pulse)
    st = nb.math('MULTIPLY', fall, s)
    nb.output(nb.transparent())
    vol = nb.emission(color, st)
    nb.link(vol, nb.out.inputs['Volume'])
    set_transparent(mat)
    diffuse_display(mat, color)
    mat["rbx_kind"] = "aura"
    mat["rbx_color"] = list(color[:3])
    return mat


def m_radial_glow(name, stops, strength, axes=('X', 'Y'), pulse=None):
    """Emissione con sfumatura radiale (iridi, occhi-faro).
    stops: rampa colore dal centro (0) al bordo (1) in coordinate oggetto."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['Object'], sep.inputs[0])
    a = nb.math('MULTIPLY', sep.outputs[axes[0]], sep.outputs[axes[0]])
    b = nb.math('MULTIPLY', sep.outputs[axes[1]], sep.outputs[axes[1]])
    d = nb.math('SQRT', nb.math('ADD', a, b))
    col = nb.ramp(d, stops)
    s = nb.glow(strength, pulse)
    nb.output(nb.emission(col, s))
    diffuse_display(mat, stops[len(stops) // 2][1])
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(stops[1][1][:3])
    return mat


def m_ghost(name, base, glow, alpha=0.35, core=0.15, rim=1.4, pulse=None, wisps=True,
            core_color=(0.75, 0.9, 1.0)):
    """Corpo spettrale semitrasparente che pulsa di luce (piu' forte sui contorni)."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord()
    bsdf = nb.principled(base=base, rough=0.3, sss=0.3, sss_radius=(0.4, 1.0, 1.0),
                         sheen=0.6, sheen_tint=glow, coat=0.4)
    shader = nb.mix_shader(alpha, nb.transparent(), bsdf.outputs[0])
    f = nb.facing(0.45)
    edge = nb.maprange(f, 0.2, 1.0, 0.0, 1.0)
    edge = nb.math('MULTIPLY', edge, edge)
    amt = nb.math('MULTIPLY', edge, rim)
    cr = nb.value(core)
    if wisps:
        mp = nb.node('ShaderNodeMapping')
        nb.link(tc.outputs['Object'], mp.inputs['Vector'])
        nb.set(mp, 'Scale', (1.0, 0.35, 1.0))
        nz = nb.noise(mp.outputs[0], 7.0, 8.0, 0.6)
        w = nb.maprange(nz.outputs['Fac'], 0.35, 0.7, 0.55, 1.35)
        amt = nb.math('MULTIPLY', amt, w)
        cr = nb.math('MULTIPLY', cr, w)
    s = nb.glow(1.0, pulse)
    shader = nb.add_shader(shader, nb.emission(glow, nb.math('MULTIPLY', amt, s)))
    shader = nb.add_shader(shader, nb.emission(core_color, nb.math('MULTIPLY', cr, s)))
    nb.output(shader)
    set_transparent(mat, blended=False)
    diffuse_display(mat, base)
    mat["rbx_kind"] = "ghost"
    mat["rbx_color"] = list(core_color[:3])
    mat["rbx_highlight"] = list(glow[:3])
    return mat


def m_wing(name, ramp, alpha=0.3, membrane_str=1.5, vein_ramp=None,
           vein_str=10.0, radial=(9, 0.10), cross=None, edge=0.07,
           side_edge=True, cells=None, cell_mix=0.0, v_mix=1.0, facing_mix=0.0,
           distort=0.0, spots=None, dots=None, pulse=None, shiny=True,
           cell_color=None, cell_str=None):
    """Ala luminosa procedurale.
    ramp       : rampa colori della membrana (fattore = v, facing, celle)
    alpha      : opacita' della membrana (0 = pura luce, 1 = opaca)
    radial     : (numero, larghezza) venature radiali dalla base
    cross      : (numero, larghezza) venature trasversali (anelli)
    edge       : spessore del bordo luminoso
    cells      : (scala, larghezza, forza) rete di cellette tipo vetrata/libellula
    cell_mix   : quanto il colore casuale delle celle entra nel colore
    distort    : ondulazione delle venature (effetto fulmine / organico)
    spots      : [(u, v, raggio, anello?)] macchie ocellari
    dots       : (n, v, raggio) fila di puntini vicino al bordo
    pulse      : (min, max, cicli, fase) moltiplicatore dell'emissione."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    obj = tc.outputs['Object']

    if distort:
        nz = nb.noise(obj, 7.0, 3.0, 0.55)
        du = nb.math('MULTIPLY', nb.math('SUBTRACT', nz.outputs['Fac'], 0.5), distort)
        u_d = nb.math('ADD', u, du)
        v_d = nb.math('ADD', v, nb.math('MULTIPLY', du, 0.6))
    else:
        u_d, v_d = u, v

    def lines(coord, count, width):
        x = nb.math('FRACT', nb.math('MULTIPLY', coord, count))
        x = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', x, 0.5)), 2.0)
        return nb.maprange(x, 1.0 - width, 1.0)

    masks = []
    if radial:
        rm = lines(u_d, radial[0], radial[1])
        # le venature si assottigliano verso il bordo
        masks.append(nb.math('MULTIPLY', rm, nb.maprange(v, 0.0, 1.0, 1.0, 0.75)))
    if cross:
        masks.append(nb.math('MULTIPLY', lines(v_d, cross[0], cross[1]),
                             nb.maprange(v, 0.1, 0.3)))
    if edge:
        masks.append(nb.maprange(v, 1.0 - edge, 1.0 - edge * 0.25))
        if side_edge:
            mn = nb.math('MINIMUM', u, nb.math('SUBTRACT', 1.0, u))
            masks.append(nb.maprange(mn, edge * 0.35, edge * 0.08))
    cell_rand = None
    cell_mask = None
    if cells:
        csc, cw, cstr = cells
        vo = nb.voronoi(obj, csc, 'DISTANCE_TO_EDGE')
        cm = nb.math('MULTIPLY', nb.maprange(vo.outputs['Distance'], cw, cw * 0.2), cstr)
        if cell_color is not None:
            cell_mask = cm          # rete di celle con un suo colore
        else:
            masks.append(cm)
        vo1 = nb.voronoi(obj, csc, 'F1')
        bw = nb.node('ShaderNodeRGBToBW')
        nb.link(vo1.outputs['Color'], bw.inputs[0])
        cell_rand = bw.outputs[0]
    if spots:
        for (su, sv, sr, ring) in spots:
            dx = nb.math('MULTIPLY', nb.math('SUBTRACT', u, su), 2.2)
            dy = nb.math('SUBTRACT', v, sv)
            d = nb.math('SQRT', nb.math('ADD', nb.math('MULTIPLY', dx, dx),
                                        nb.math('MULTIPLY', dy, dy)))
            if ring:
                dd = nb.math('ABSOLUTE', nb.math('SUBTRACT', d, sr))
                masks.append(nb.maprange(dd, sr * 0.28, sr * 0.08))
            masks.append(nb.maprange(d, sr * 0.55, sr * 0.3))
    if dots:
        dn, dv, dr = dots
        fx = nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', u, dn)), 0.5)
        dx = nb.math('MULTIPLY', fx, 1.0 / dn * 2.2)
        dy = nb.math('SUBTRACT', v, dv)
        d = nb.math('SQRT', nb.math('ADD', nb.math('MULTIPLY', dx, dx),
                                    nb.math('MULTIPLY', dy, dy)))
        masks.append(nb.maprange(d, dr, dr * 0.45))

    mask = masks[0]
    for m in masks[1:]:
        mask = nb.math('MAXIMUM', mask, m)

    # fattore colore: base->bordo, angolo di vista (iridescenza), celle
    fac = nb.math('MULTIPLY', v, v_mix)
    if facing_mix:
        fac = nb.math('ADD', fac, nb.math('MULTIPLY', nb.facing(0.35), facing_mix))
    if cell_rand is not None and cell_mix:
        fac = nb.math('ADD', fac, nb.math('MULTIPLY', cell_rand, cell_mix))
    fac = nb.math('ADD', fac, 0.0, clamp=True)
    col = nb.ramp(fac, ramp)
    vcol = nb.ramp(fac, vein_ramp) if vein_ramp else col

    pm = nb.glow(1.0, pulse)
    ms = nb.math('MULTIPLY', pm, membrane_str)
    vs = nb.math('MULTIPLY', pm, vein_str)

    if alpha > 0:
        if shiny:
            surf = nb.principled(base=col, rough=0.12, spec=0.6, coat=0.5).outputs[0]
        else:
            surf = nb.node('ShaderNodeBsdfDiffuse', {'Color': col}).outputs[0]
        membrane = nb.mix_shader(alpha, nb.transparent(), surf)
    else:
        membrane = nb.transparent()
    membrane = nb.add_shader(membrane, nb.emission(col, ms))
    if cell_mask is not None:
        cs = nb.math('MULTIPLY', pm, cell_str if cell_str is not None else vein_str)
        membrane = nb.mix_shader(cell_mask, membrane, nb.emission(cell_color, cs))
    veins = nb.emission(vcol, vs)
    nb.output(nb.mix_shader(mask, membrane, veins))
    set_transparent(mat)
    diffuse_display(mat, ramp[len(ramp) // 2][1])

    # --- uscite per le texture Roblox (colore, emissione, opacita') ---------
    c_str = cell_str if cell_str is not None else vein_str
    top = max(vein_str, membrane_str, c_str if cell_mask is not None else 0.0)
    c_col = nb.emission(col, 1.0)
    c_emi = nb.emission(col, membrane_str / top)
    a_val = max(0.12, min(1.0, alpha + membrane_str * 0.6))
    c_alp = nb.emission((1, 1, 1), a_val)
    if cell_mask is not None:
        c_col = nb.mix_shader(cell_mask, c_col, nb.emission(cell_color, 1.0))
        c_emi = nb.mix_shader(cell_mask, c_emi, nb.emission(cell_color, c_str / top))
        c_alp = nb.mix_shader(cell_mask, c_alp, nb.emission((1, 1, 1), 1.0))
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, c_col, nb.emission(vcol, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(mask, c_emi, nb.emission(vcol, 1.0)))
    nb.bake_output("RBX_ALPHA", nb.mix_shader(mask, c_alp, nb.emission((1, 1, 1), 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_alpha"] = 1
    mat["rbx_wing"] = 1
    mat["rbx_emit_strength"] = float(top)
    return mat


def m_feather(name, base, base_tip, glow, glow_str, edge_w=0.16,
              rachis_w=0.07, barbs=14, pulse=None):
    """Piuma: marrone ricco con bordi e rachide al neon.
    UV: u attraverso la piuma (0..1), v dalla radice (0) alla punta (1)."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord(use_space=False)
    sep = nb.node('ShaderNodeSeparateXYZ')
    nb.link(tc.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    au = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5)), 2.0)
    edge = nb.maprange(au, 1.0 - edge_w, 1.0 - edge_w * 0.3)
    edge = nb.math('MULTIPLY', edge, nb.maprange(v, 0.15, 0.45))
    rachis = nb.math('MULTIPLY', nb.maprange(au, rachis_w, rachis_w * 0.3),
                     nb.maprange(v, 0.95, 0.55))
    b = nb.math('FRACT', nb.math('MULTIPLY', nb.math('ADD', v, nb.math('MULTIPLY', au, 0.35)), barbs))
    b = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', b, 0.5)), 2.0)
    barb = nb.math('MULTIPLY', nb.maprange(b, 0.8, 1.0), 0.45)
    barb = nb.math('MULTIPLY', barb, nb.maprange(v, 0.2, 0.5))
    mask = nb.math('MAXIMUM', nb.math('MAXIMUM', edge, rachis), barb)
    col = nb.ramp(v, [(0.0, base), (1.0, base_tip)])
    bsdf = nb.principled(base=col, rough=0.55, sheen=0.5, spec=0.3)
    s = nb.glow(glow_str, pulse)
    em = nb.emission(glow, s)
    nb.output(nb.mix_shader(mask, bsdf.outputs[0], em))
    diffuse_display(mat, base)
    nb.bake_output("RBX_COLOR", nb.mix_shader(mask, nb.emission(col, 1.0), nb.emission(glow, 1.0)))
    nb.bake_output("RBX_EMIT", nb.mix_shader(mask, nb.emission((0, 0, 0), 1.0), nb.emission(glow, 1.0)))
    mat["rbx_kind"] = "bake"
    mat["rbx_uv_only"] = 1
    mat["rbx_emit_strength"] = float(glow_str)
    return mat


def m_bark(name, base=(0.09, 0.05, 0.025), dark=(0.03, 0.017, 0.01)):
    mat = new_material(name)
    nb = NodeBuilder(mat)
    tc = nb.texcoord()
    wv = nb.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z')
    nb.set(wv, 'Scale', 3.0)
    nb.set(wv, 'Distortion', 6.0)
    nb.set(wv, 'Detail', 4.0)
    nb.link(tc.outputs['Object'], wv.inputs['Vector'])
    nz = nb.noise(tc.outputs['Object'], 12.0, 8.0, 0.6)
    h = nb.math('ADD', nb.math('MULTIPLY', wv.outputs['Fac'], 0.6),
                nb.math('MULTIPLY', nz.outputs['Fac'], 0.5))
    col = nb.ramp(h, [(0.25, dark), (0.75, base)])
    bsdf = nb.principled(base=col, rough=0.85)
    nb.set(bsdf, 'Normal', nb.bump(h, 0.6, 0.02))
    nb.output(bsdf.outputs[0])
    diffuse_display(mat, base)
    nb.bake_output("RBX_COLOR", nb.emission(col, 1.0))
    mat["rbx_kind"] = "bake"
    mat["rbx_normal"] = 1
    mat["rbx_rough"] = 0.85
    return mat


# ============================================================================
# SCENA: mondo notturno, pavimento, luci, camera, render
# ============================================================================

def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                  bpy.data.lights, bpy.data.cameras, bpy.data.metaballs,
                  bpy.data.particles, bpy.data.worlds, bpy.data.node_groups):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass


def setup_world(color=(0.0025, 0.0035, 0.009), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Notte")
    sc.world = w
    if BL < (5, 0, 0):
        w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get('Background') or nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (color[0], color[1], color[2], 1.0)
    bg.inputs['Strength'].default_value = strength
    out = nt.nodes.get('World Output') or nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def setup_ground(size=40.0):
    mat = new_material("Terreno_Notte")
    nb = NodeBuilder(mat)
    tc = nb.texcoord()
    nz = nb.noise(tc.outputs['Object'], 0.6, 6.0, 0.6)
    col = nb.ramp(nz.outputs['Fac'], [(0.3, (0.025, 0.028, 0.035)), (0.7, (0.045, 0.05, 0.06))])
    rough = nb.maprange(nz.outputs['Fac'], 0.3, 0.7, 0.25, 0.6)
    bsdf = nb.principled(base=col, rough=rough, spec=0.5)
    nb.output(bsdf.outputs[0])
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    ob = mesh_object("Terreno", bm, mat, smooth=False)
    return ob


def add_light(name, kind, loc, energy, color=(1, 1, 1), size=0.1, rot=None,
              pulse=None, spot_size=None, creature_light=True):
    ld = bpy.data.lights.new(name, kind)
    k = INTENSITA_LUCE if creature_light else 1.0
    ld.energy = energy * k
    ld.color = color
    if kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = size
    elif kind == 'AREA':
        ld.size = size
    elif kind == 'SUN':
        ld.angle = radians(size)
    if kind == 'SPOT' and spot_size:
        ld.spot_size = radians(spot_size)
        ld.spot_blend = 0.6
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if hasattr(ob, 'visible_camera') and kind != 'SUN':
        ob.visible_camera = False       # la luce illumina ma non si vede come una sfera
    if rot is not None:
        ob.rotation_euler = [radians(a) for a in rot]
    link(ob)
    if pulse:
        add_driver(ld, "energy", wave(pulse[0] * k, pulse[1] * k, *pulse[2:]),
                   meta=dict(tipo='luce', lo=pulse[0] * k, hi=pulse[1] * k,
                             cyc=pulse[2] if len(pulse) > 2 else 1,
                             ph=pulse[3] if len(pulse) > 3 else 0.0))
    return ob


def aim(ob, target):
    d = vec(target) - ob.location
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def setup_camera(target, dist, elev, azim, lens=50.0, name="Camera"):
    sc = bpy.context.scene
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.05
    cam.clip_end = 500
    ob = bpy.data.objects.new(name, cam)
    t = vec(target)
    e, a = radians(elev), radians(azim)
    ob.location = t + Vector((sin(a) * cos(e), -cos(a) * cos(e), sin(e))) * dist
    aim(ob, t)
    bpy.context.scene.collection.objects.link(ob)
    sc.camera = ob
    return ob


def setup_moonlight():
    add_light("Luna", 'SUN', (0, 0, 10), 0.8, (0.55, 0.65, 1.0), 3.0,
              rot=(50, 0, -35), creature_light=False)
    add_light("Controluce", 'AREA', (3, 6, 4), 60.0, (0.35, 0.45, 1.0), 4.0,
              rot=(-60, 0, 150), creature_light=False)


def setup_compositor():
    """Bagliore (bloom) in compositing: rende le parti luminose 'accese'."""
    sc = bpy.context.scene
    try:
        if hasattr(sc, 'compositing_node_group'):          # Blender 5.x
            ng = bpy.data.node_groups.new("Bagliore", "CompositorNodeTree")
            sc.compositing_node_group = ng
            ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
            rl = ng.nodes.new("CompositorNodeRLayers")
            gl = ng.nodes.new("CompositorNodeGlare")
            out = ng.nodes.new("NodeGroupOutput")
            for key, val in (('Type', 'Bloom'), ('Quality', 'High'), ('Threshold', 1.0),
                             ('Strength', 0.45), ('Size', 0.7), ('Saturation', 1.1)):
                s = gl.inputs.get(key)
                if s is not None:
                    try:
                        s.default_value = val
                    except (TypeError, ValueError):
                        pass
            ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
            ng.links.new(gl.outputs['Image'], out.inputs[0])
        else:                                              # Blender 3.x / 4.x
            sc.use_nodes = True
            nt = sc.node_tree
            nt.nodes.clear()
            rl = nt.nodes.new("CompositorNodeRLayers")
            gl = nt.nodes.new("CompositorNodeGlare")
            types = [i.identifier for i in gl.bl_rna.properties['glare_type'].enum_items]
            gl.glare_type = 'BLOOM' if 'BLOOM' in types else 'FOG_GLOW'
            gl.quality = 'HIGH'
            gl.threshold = 1.0
            gl.size = 7
            gl.mix = -0.8
            comp = nt.nodes.new("CompositorNodeComposite")
            nt.links.new(rl.outputs['Image'], gl.inputs['Image'])
            nt.links.new(gl.outputs['Image'], comp.inputs['Image'])
            try:
                vw = nt.nodes.new("CompositorNodeViewer")
                nt.links.new(gl.outputs['Image'], vw.inputs['Image'])
            except Exception:
                pass
    except Exception as exc:                               # non bloccare lo script
        print("[creature] compositor non configurato:", exc)


def setup_viewport():
    """Viewport 3D con luci e mondo della scena, vista dalla camera.
    In Blender aperto: modalita' Rendered. Nei file salvati da riga di comando:
    Material Preview con luci/mondo della scena (Blender non conserva 'Rendered'
    nei file salvati in background)."""
    mode = 'MATERIAL' if bpy.app.background else 'RENDERED'
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type != 'VIEW_3D':
                continue
            for sp in area.spaces:
                if sp.type != 'VIEW_3D':
                    continue
                for attr, val in (('type', mode), ('use_compositor', 'ALWAYS'),
                                  ('use_scene_lights', True), ('use_scene_world', True),
                                  ('use_scene_lights_render', True), ('use_scene_world_render', True)):
                    try:
                        setattr(sp.shading, attr, val)
                    except (AttributeError, TypeError, ValueError):
                        pass
                try:
                    sp.region_3d.view_perspective = 'CAMERA'
                except (AttributeError, TypeError):
                    pass


def setup_render(engine=None):
    sc = bpy.context.scene
    engine = (engine or MOTORE).upper()
    if engine == "CYCLES":
        sc.render.engine = 'CYCLES'
    else:
        for ident in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
            try:
                sc.render.engine = ident
                break
            except TypeError:
                continue
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.film_transparent = False
    sc.frame_start = 1
    sc.frame_end = ANIM_FRAMES
    sc.render.fps = 24
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Punchy'
    except TypeError:
        try:
            sc.view_settings.look = 'Punchy'
        except TypeError:
            pass
    # Cycles
    try:
        sc.cycles.samples = 256
        sc.cycles.preview_samples = 64
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 8
        sc.cycles.transparent_max_bounces = 32
    except AttributeError:
        pass
    # EEVEE (legacy e Next)
    ev = sc.eevee
    for attr, val in (('taa_render_samples', 128), ('taa_samples', 32),
                      ('use_bloom', True), ('bloom_threshold', 0.8),
                      ('bloom_intensity', 0.08), ('bloom_radius', 6.0),
                      ('use_gtao', True), ('use_ssr', True),
                      ('use_ssr_refraction', True), ('use_soft_shadows', True),
                      ('use_raytracing', True), ('use_shadows', True)):
        if hasattr(ev, attr):
            try:
                setattr(ev, attr, val)
            except (TypeError, AttributeError):
                pass
    setup_compositor()


# ============================================================================
# 01  MANTE-LUCE (Mantis-Light)
# ============================================================================

def build_mantis():
    green = (0.005, 0.28, 0.07)
    m_green = m_body("Mantide_Smeraldo", green, rough=0.3, coat=0.6, sss=0.15,
                     sss_radius=(0.2, 1.0, 0.3), rim=(0.2, 1.0, 0.45), rim_str=0.8,
                     bump=(40.0, 0.08, 'noise'))
    m_abd = m_body("Mantide_Addome_Pulsante", (0.02, 0.22, 0.03), rough=0.25,
                   coat=0.8, sss=0.1, sss_radius=(1.0, 0.6, 0.2),
                   emit=(1.0, 0.3, 0.02), emit_pulse=(0.4, 2.6, 2, 0.0),
                   emit_center=True, rim=(0.25, 1.0, 0.3), rim_str=0.6)
    m_eye = m_body("Mantide_Occhi", (0.25, 0.6, 0.05), rough=0.1, coat=1.0,
                   emit=(0.5, 1.0, 0.2), emit_str=0.6)
    m_spine = m_body("Mantide_Spine", (0.35, 0.55, 0.08), rough=0.3,
                     emit=(1.0, 0.7, 0.2), emit_str=1.5)
    m_tip = m_emit("Mantide_Punte", (1.0, 0.75, 0.3), 8.0)

    glass_hot = [(0.0, (1.0, 0.12, 0.0)), (0.3, (1.0, 0.28, 0.0)),
                 (0.6, (1.0, 0.45, 0.01)), (0.85, (0.95, 0.62, 0.03)), (1.0, (0.8, 0.7, 0.05))]
    m_hind = m_wing("Mantide_Ala_Vetrata", glass_hot, alpha=0.18,
                    membrane_str=0.4, vein_ramp=[(0.0, (1.0, 0.38, 0.02)), (1.0, (1.0, 0.55, 0.06))],
                    vein_str=1.8, radial=(12, 0.09), cross=(4, 0.06), edge=0.05,
                    cells=(4.5, 0.03, 1.0), cell_mix=0.8, v_mix=0.3, shiny=False,
                    pulse=(0.8, 1.15, 1, 0.0))
    glass_gold = [(0.0, (0.35, 0.5, 0.02)), (0.3, (1.0, 0.5, 0.0)),
                  (0.65, (1.0, 0.62, 0.02)), (1.0, (0.85, 0.75, 0.05))]
    m_fore = m_wing("Mantide_Ala_Anteriore", glass_gold, alpha=0.2,
                    membrane_str=0.4, vein_ramp=[(0.0, (1.0, 0.42, 0.03)), (1.0, (1.0, 0.6, 0.08))],
                    vein_str=1.8, radial=(8, 0.09), cross=(6, 0.06), edge=0.06,
                    cells=(7.0, 0.035, 1.0), cell_mix=0.75, v_mix=0.3, shiny=False,
                    pulse=(0.8, 1.15, 1, 1.5))

    # --- addome segmentato (pulsa di luce calda) --------------------------
    widths = [0.115, 0.145, 0.165, 0.172, 0.165, 0.145, 0.115, 0.08]
    for i, w in enumerate(widths):
        s = i / (len(widths) - 1)
        y = 0.24 + 1.05 * s
        z = 0.62 + 0.06 * sin(pi * s) - 0.05 * s
        sphere("Mantide_Addome_%02d" % i, (0, y, z), (w, 0.1, w * 0.82), m_abd,
               rot=(-6 + 10 * s, 0, 0))
    for sx in (-1, 1):
        cone_between("Mantide_Cerco_%s" % ("L" if sx < 0 else "R"),
                     (0.02 * sx, 1.36, 0.6), (0.06 * sx, 1.5, 0.66), 0.012, 0.0, m_green)

    # --- torace -----------------------------------------------------------
    sphere("Mantide_Mesotorace", (0, 0.1, 0.64), (0.085, 0.17, 0.08), m_green)
    tube("Mantide_Protorace",
         [(0, 0.04, 0.66), (0, -0.08, 0.84), (0, -0.2, 1.02), (0, -0.29, 1.16), (0, -0.34, 1.24)],
         [0.07, 0.048, 0.042, 0.062, 0.05], m_green, bevel_res=6)

    # --- testa triangolare -----------------------------------------------
    H = Vector((0, -0.4, 1.3))
    head = sphere("Mantide_Testa", H, (0.13, 0.07, 0.1), m_green, rot=(-25, 0, 0))
    td = head.modifiers.new("Triangolo", 'SIMPLE_DEFORM')
    td.deform_method = 'TAPER'
    td.deform_axis = 'Z'
    td.factor = 0.9
    for sx in (-1, 1):
        sphere("Mantide_Occhio_%s" % ("L" if sx < 0 else "R"),
               H + Vector((0.118 * sx, -0.01, 0.05)), (0.055, 0.05, 0.065), m_eye)
    cone_between("Mantide_Bocca", H + Vector((0, -0.035, -0.07)),
                 H + Vector((0, -0.07, -0.15)), 0.03, 0.006, m_green)
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        pts = [H + Vector((0.025 * sx, -0.05, 0.07)), (0.06 * sx, -0.5, 1.46),
               (0.16 * sx, -0.62, 1.62), (0.3 * sx, -0.66, 1.72), (0.44 * sx, -0.62, 1.76)]
        tube("Mantide_Antenna_" + side, pts, [0.009, 0.007, 0.006, 0.005, 0.004], m_green,
             bevel_res=2)
        sphere("Mantide_AntennaPunta_" + side, pts[-1], 0.012, m_tip)

    # --- zampe raptatorie (spinose ma eleganti) ---------------------------
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        c0 = Vector((0.045 * sx, -0.26, 1.08))
        c1 = Vector((0.075 * sx, -0.37, 0.86))
        fm = Vector((0.088 * sx, -0.47, 0.99))
        f1 = Vector((0.085 * sx, -0.53, 1.13))
        t1 = Vector((0.08 * sx, -0.5, 0.93))
        t2 = Vector((0.085 * sx, -0.57, 0.86))
        t3 = Vector((0.09 * sx, -0.6, 0.8))
        tube("Mantide_Coxa_" + side, [c0, (c0 + c1) / 2 + Vector((0, -0.02, 0)), c1],
             [0.036, 0.034, 0.028], m_green)
        tube("Mantide_Femore_" + side, [c1, fm, f1], [0.03, 0.043, 0.028], m_green)
        tube("Mantide_Tibia_" + side, [f1, (f1 + t1) / 2 + Vector((0, -0.03, 0)), t1],
             [0.024, 0.02, 0.017], m_green)
        tube("Mantide_Tarso_" + side, [t1, t2, t3], [0.012, 0.009, 0.006], m_green)
        # spine sul femore (verso la tibia) e sulla tibia (verso il femore)
        fdir = (f1 - c1).normalized()
        perp = Vector((0, -fdir.z, fdir.y)).normalized()
        if perp.y > 0:
            perp = -perp
        for k in range(7):
            t = 0.15 + 0.7 * k / 6
            p = c1.lerp(f1, t) + perp * 0.02
            ln = 0.035 if k % 2 == 0 else 0.022
            tip = p + (perp + Vector((0.25 * sx, 0, -0.35))).normalized() * ln
            cone_between("Mantide_SpinaF_%s_%d" % (side, k), p, tip, 0.008, 0.0, m_spine, 8)
        tdir = (t1 - f1).normalized()
        tperp = Vector((0, -tdir.z, tdir.y)).normalized()
        if tperp.y < 0:
            tperp = -tperp
        for k in range(5):
            t = 0.2 + 0.65 * k / 4
            p = f1.lerp(t1, t) + tperp * 0.012
            tip = p + (tperp + Vector((0, 0, 0.4))).normalized() * 0.025
            cone_between("Mantide_SpinaT_%s_%d" % (side, k), p, tip, 0.006, 0.0, m_spine, 8)

    # --- zampe medie e posteriori (lunghe e sottili) ----------------------
    legs = {
        "Media": [(0.05, 0.02, 0.6), (0.3, -0.14, 0.76), (0.42, -0.3, 0.03), (0.47, -0.4, 0.0)],
        "Posteriore": [(0.05, 0.16, 0.58), (0.36, 0.4, 0.78), (0.5, 0.72, 0.03), (0.54, 0.84, 0.0)],
    }
    for leg, pts in legs.items():
        for sx in (-1, 1):
            side = "L" if sx < 0 else "R"
            p = [Vector((x * sx, y, z)) for x, y, z in pts]
            tube("Mantide_Zampa%sFem_%s" % (leg, side), [p[0], p[0].lerp(p[1], 0.5) + Vector((0, 0, 0.04)), p[1]],
                 [0.022, 0.02, 0.016], m_green)
            tube("Mantide_Zampa%sTib_%s" % (leg, side), [p[1], p[1].lerp(p[2], 0.5), p[2]],
                 [0.015, 0.012, 0.009], m_green)
            tube("Mantide_Zampa%sTar_%s" % (leg, side), [p[2], p[3]], [0.008, 0.005], m_green)
            sphere("Mantide_Ginocchio%s_%s" % (leg, side), p[1], 0.022, m_green)

    # --- ali grandi e spiegate (pannelli a vetrata) -----------------------
    hind_ctrl = [(-10, 0.3), (0, 0.9), (12, 1.25), (28, 1.45), (45, 1.5), (62, 1.42),
                 (78, 1.25), (92, 0.9), (102, 0.4), (108, 0.15)]
    fore_ctrl = [(-7, 0.3), (-4, 0.85), (1, 1.3), (6, 1.5), (12, 1.42), (19, 1.05),
                 (26, 0.6), (31, 0.25)]
    # posa di "parata": ventagli quasi verticali rivolti in avanti
    wing_pair("Mantide_AlaPosteriore", hind_ctrl, m_hind, (0.05, 0.24, 0.7), elev=-4,
              sweep=22, roll=78, rings=16, cup=-0.08, flap=(3, 1, 0.0), scallop=(0.035, 9))
    wing_pair("Mantide_AlaAnteriore", fore_ctrl, m_fore, (0.05, 0.12, 0.74), elev=38,
              sweep=14, roll=80, rings=14, cup=-0.05, flap=(3, 1, 0.4))

    # luce calda che pulsa dentro l'addome
    add_light("Mantide_LuceAddome", 'POINT', (0, 0.75, 0.62), 25.0, (1.0, 0.5, 0.12),
              0.25, pulse=(3.0, 15.0, 2, 0.0))
    add_light("Mantide_LuceAli", 'POINT', (0, 0.1, 1.3), 3.0, (1.0, 0.55, 0.2), 0.6,
              pulse=(2.0, 4.0, 1, 0.0))


# ============================================================================
# 02  GATTOLUNA (Moon-Cat)
# ============================================================================

def build_cat():
    K = 1.65   # raggio metaball / raggio visibile
    m_fur = m_body("Gatto_Pelo_Notte", (0.006, 0.005, 0.011), rough=0.42,
                   sheen=0.8, sheen_tint=(0.45, 0.3, 1.0), coat=0.25, coat_rough=0.25,
                   rim=(0.32, 0.22, 1.0), rim_str=1.1, rim_power=0.5,
                   bump=(160.0, 0.12, 'noise'))
    m_ear_in = m_body("Gatto_Orecchio_Interno", (0.03, 0.01, 0.06), rough=0.5,
                      emit=(0.45, 0.25, 1.0), emit_str=0.9, emit_pulse=(0.5, 1.2, 1, 0.5))
    m_iris = m_radial_glow("Gatto_Iride", [(0.0, (1.0, 0.95, 0.55)), (0.45, (1.0, 0.72, 0.12)),
                                           (0.85, (0.85, 0.35, 0.02)), (1.0, (0.2, 0.05, 0.0))], 2.2)
    m_pupil = m_body("Gatto_Pupilla", (0.0, 0.0, 0.0), rough=0.1, coat=1.0)
    m_cornea = m_glass_eye("Gatto_Cornea")
    m_whisk = m_emit("Gatto_Baffi_Luce", (0.55, 0.65, 1.0), 1.6, pulse=(1.0, 2.0, 2, 0.0))
    m_tail = m_emit("Gatto_Coda_Luce", (0.45, 0.35, 1.0), 2.5, pulse=(1.4, 3.2, 1, 0.0))
    m_moon = m_emit("Gatto_Luna_Fronte", (0.75, 0.8, 1.0), 2.0)
    m_nose = m_body("Gatto_Naso", (0.05, 0.02, 0.06), rough=0.2, coat=0.8)
    wing_cols = [(0.0, (0.05, 0.15, 1.0)), (0.4, (0.15, 0.3, 1.0)), (0.65, (0.45, 0.2, 1.0)),
                 (0.88, (0.3, 0.6, 1.0)), (1.0, (0.6, 0.9, 1.0))]
    m_wing_f = m_wing("Gatto_Ala_Luce", wing_cols, alpha=0.0, membrane_str=0.22,
                      vein_str=1.4, radial=(9, 0.07), cross=(3, 0.04), edge=0.06,
                      v_mix=0.7, facing_mix=0.45, distort=0.03,
                      spots=[(0.55, 0.62, 0.11, True)], dots=(11, 0.9, 0.022),
                      pulse=(0.75, 1.2, 1, 0.0))
    m_wing_h = m_wing("Gatto_Ala_Luce_Post", wing_cols, alpha=0.0, membrane_str=0.2,
                      vein_str=1.3, radial=(7, 0.07), cross=(2, 0.04), edge=0.07,
                      v_mix=0.6, facing_mix=0.5, distort=0.03,
                      spots=[(0.5, 0.6, 0.12, True)], pulse=(0.75, 1.2, 1, 1.0))

    E = []
    # tronco slanciato
    E.append(ellipsoid((0, -0.3, 0.62), 0.145 * K, (1.0, 1.25, 1.2)))
    E.append(ellipsoid((0, 0.0, 0.6), 0.11 * K, (1.0, 2.2, 1.0)))
    E.append(ellipsoid((0, 0.3, 0.62), 0.125 * K, (1.0, 1.3, 1.1)))
    # collo e testa
    E.append(capsule((0, -0.38, 0.68), (0, -0.5, 0.84), 0.09 * K))
    E.append(ball((0, -0.58, 0.92), 0.15 * K))
    E.append(ellipsoid((0, -0.64, 0.87), 0.1 * K, (1.45, 0.9, 0.85)))
    E.append(ball((0, -0.73, 0.85), 0.055 * K))
    for sx in (-1, 1):
        E.append(ball((0.03 * sx, -0.745, 0.845), 0.045 * K))
    E.append(ball((0, -0.71, 0.8), 0.04 * K))
    for sx in (-1, 1):
        # zampe anteriori
        E.append(capsule((0.085 * sx, -0.33, 0.52), (0.08 * sx, -0.36, 0.28), 0.065 * K))
        E.append(capsule((0.08 * sx, -0.36, 0.28), (0.075 * sx, -0.39, 0.07), 0.042 * K))
        E.append(ellipsoid((0.075 * sx, -0.42, 0.035), 0.045 * K, (1.0, 1.35, 0.7)))
        # zampe posteriori
        E.append(capsule((0.1 * sx, 0.32, 0.56), (0.1 * sx, 0.22, 0.32), 0.075 * K))
        E.append(capsule((0.1 * sx, 0.22, 0.32), (0.095 * sx, 0.42, 0.17), 0.042 * K))
        E.append(capsule((0.095 * sx, 0.42, 0.17), (0.09 * sx, 0.4, 0.05), 0.034 * K))
        E.append(ellipsoid((0.09 * sx, 0.37, 0.035), 0.043 * K, (1.0, 1.35, 0.7)))
    body = metaball_mesh("Gatto_Corpo", E, m_fur, res=0.022)
    bvh = bvh_of(body)
    head_c = Vector((0, -0.6, 0.9))

    # orecchie a punta con interno luminoso
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        base = Vector((0.085 * sx, -0.58, 1.0))
        tipv = Vector((0.13 * sx, -0.6, 1.2))
        ear = cone_between("Gatto_Orecchio_" + side, base, tipv, 0.075, 0.004, m_fur, 16)
        ear.scale = (1.0, 0.5, 1.0)
        inner = cone_between("Gatto_OrecchioInt_" + side, base + Vector((0, -0.022, 0.01)),
                             tipv + Vector((-0.006 * sx, -0.016, -0.03)), 0.055, 0.003, m_ear_in, 16)
        inner.scale = (1.0, 0.35, 1.0)

    # occhi grandi e luminosi (pupilla a fessura)
    for sx in (-1, 1):
        make_eye("Gatto_Occhio_" + ("L" if sx < 0 else "R"), bvh, head_c,
                 (0.42 * sx, -1.0, 0.28), 0.052, m_iris, m_pupil, m_cornea,
                 pupil=(0.16, 0.78), sink=0.45)
    # naso
    nloc, nnor = surface_hit(bvh, head_c, (0, -1, -0.12))
    sphere("Gatto_Naso", nloc + nnor * 0.004, (0.022, 0.014, 0.014), m_nose)

    # falce di luna luminosa sulla fronte
    floc, fnor = surface_hit(bvh, head_c, (0, -0.8, 0.75))
    fr = frame_matrix(floc + fnor * 0.006, (0, 0, 1), fnor)
    pts, rad = [], []
    for i in range(9):
        a = radians(-120 + 240 * i / 8)
        pts.append(fr @ Vector((0.035 * cos(a) - 0.01, 0.035 * sin(a), 0.0)))
        rad.append(0.003 + 0.009 * sin(pi * i / 8))
    tube("Gatto_Luna_Fronte", pts, rad, m_moon, bevel_res=2)

    # baffi luminosi
    for sx in (-1, 1):
        for k, (dz, dy) in enumerate(((0.02, 0.0), (0.0, 0.02), (-0.02, 0.04))):
            st = Vector((0.045 * sx, -0.755, 0.84 + dz * 0.4))
            pts = [st, st + Vector((0.12 * sx, -0.03 + dy, dz)),
                   st + Vector((0.26 * sx, 0.0 + dy * 2, dz * 2 - 0.035))]
            tube("Gatto_Baffo_%s%d" % ("L" if sx < 0 else "R", k), pts, [0.0035, 0.0025, 0.0012],
                 m_whisk, bevel_res=1)

    # coda sinuosa con punta luminosa
    tpts = [(0, 0.42, 0.64), (0.03, 0.6, 0.68), (0.12, 0.76, 0.84), (0.22, 0.8, 1.04), (0.3, 0.72, 1.16)]
    tube("Gatto_Coda", tpts, [0.05, 0.042, 0.038, 0.033, 0.029], m_fur, bevel_res=5)
    tip = [(0.3, 0.72, 1.16), (0.345, 0.64, 1.19), (0.37, 0.57, 1.17)]
    tube("Gatto_Coda_Punta", tip, [0.029, 0.021, 0.008], m_tail, bevel_res=4)
    halo = sphere("Gatto_Coda_Aura", (0.35, 0.62, 1.18), 0.09,
                  m_halo("Gatto_Aura_Coda", (0.4, 0.3, 1.0), 1.2, pulse=(0.8, 1.8, 1, 0.0)))
    no_shadow(halo)

    # ali da falena fatte di pura luce
    fore = [(-12, 0.25), (-5, 0.75), (5, 1.02), (16, 1.1), (32, 0.98), (52, 0.8), (72, 0.55), (86, 0.25)]
    hind = [(35, 0.25), (52, 0.55), (75, 0.72), (100, 0.74), (125, 0.62), (145, 0.4), (158, 0.18)]
    wing_pair("Gatto_AlaAnt", fore, m_wing_f, (0.06, -0.2, 0.74), elev=48, sweep=30,
              roll=35, rings=14, cup=0.05, flap=(7, 1, 0.0))
    wing_pair("Gatto_AlaPost", hind, m_wing_h, (0.06, -0.12, 0.72), elev=28, sweep=36,
              roll=40, rings=12, cup=0.04, flap=(7, 1, 0.25))
    add_light("Gatto_LuceAli", 'POINT', (0, -0.05, 1.05), 4.0, (0.4, 0.3, 1.0), 0.5,
              pulse=(2.5, 5.0, 1, 0.0))


# ============================================================================
# 03  GUFO-SCINTILLA (Sparkle-Owl)
# ============================================================================

def feather_mesh(name, length, width, mat, rows=10, cols=6, curl=0.2, shape='round'):
    """Piuma (o foglia) piatta. UV: u attraverso, v dalla radice alla punta.
    shape='round' -> punta arrotondata (piuma), 'pointed' -> punta a lancia (foglia)."""
    rows, cols = det(rows, 3), det(cols, 2)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid, uvs = [], {}
    for j in range(rows + 1):
        v = j / rows
        if shape == 'round':
            if v < 0.6:
                w = width * (0.4 + 0.6 * sin(0.5 * pi * v / 0.6))
            else:
                q = (v - 0.6) / 0.4
                w = width * math.sqrt(max(0.0, 1.0 - q * q))
        else:
            w = width * sin(pi * v) ** 0.7
        w = max(w, width * 0.05)
        row = []
        for i in range(cols + 1):
            u = i / cols
            x = (u - 0.5) * w
            z = curl * length * v * v + 0.18 * (1.0 - (2 * u - 1) ** 2) * w * 0.5
            bv = bm.verts.new((x, v * length, z))
            uvs[bv] = (u, v)
            row.append(bv)
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for lp in f.loops:
                lp[uvl].uv = uvs[lp.vert]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    shade_smooth(me)
    return me


def scatter_feathers(prefix, bvh, center, meshes, rows, zr, cols, skip=None,
                     lift=12.0, jitter=0.03, scale=1.0, yaw_out=0.0, stretch=None):
    """Distribuisce piume sulla superficie a file sfalsate (come tegole).
    zr = (z_alto, z_basso) della zona; skip(dir) -> True per saltare."""
    c = vec(center)
    count = 0
    for r in range(rows):
        t = r / max(1, rows - 1)
        z = zr[0] + (zr[1] - zr[0]) * t
        n = cols(t) if callable(cols) else cols
        for k in range(n):
            a = TAU * (k + 0.5 * (r % 2)) / n + random.uniform(-jitter, jitter)
            d = Vector((sin(a), -cos(a), (z - c.z)))
            if skip and skip(d, z):
                continue
            loc, nor = surface_hit(bvh, Vector((c.x, c.y, z)), (sin(a), -cos(a), 0.0))
            if loc is None:
                continue
            down = Vector((0, 0, -1)) + Vector((sin(a), -cos(a), 0)) * yaw_out
            m = frame_matrix(loc - nor * 0.01, down, nor)
            m = m @ Matrix.Rotation(radians(lift + random.uniform(-4, 4)), 4, 'X')
            me = random.choice(meshes)
            ob = bpy.data.objects.new("%s_%03d" % (prefix, count), me)
            sc_ = scale * random.uniform(0.9, 1.1) * (stretch(t) if stretch else 1.0)
            ob.matrix_world = m @ Matrix.Diagonal((sc_, sc_, sc_, 1.0))
            link(ob)
            count += 1
    return count


def build_owl():
    K = 1.65
    brown = (0.16, 0.065, 0.022)
    m_down = m_body("Gufo_Piumino", (0.12, 0.05, 0.018), rough=0.7, sheen=0.8,
                    sheen_tint=(1.0, 0.7, 0.3), rim=(1.0, 0.7, 0.15), rim_str=0.35,
                    bump=(90.0, 0.2, 'noise'))
    m_f = m_feather("Gufo_Piuma_Neon", brown, (0.2, 0.08, 0.025), (1.0, 0.72, 0.1), 2.6,
                    edge_w=0.12, rachis_w=0.05, pulse=(0.75, 1.1, 2, 0.0))
    m_f2 = m_feather("Gufo_Piuma_Chiara", (0.22, 0.11, 0.04), (0.3, 0.16, 0.06),
                     (1.0, 0.8, 0.22), 2.0, edge_w=0.1, rachis_w=0.05, barbs=10,
                     pulse=(0.75, 1.1, 2, 1.0))
    m_disc = m_body("Gufo_Disco_Facciale", (0.3, 0.18, 0.08), rough=0.75, sheen=0.6,
                    sheen_tint=(1.0, 0.8, 0.4), bump=(40.0, 0.25, 'scales'),
                    rim=(1.0, 0.8, 0.2), rim_str=0.6)
    m_ring = m_emit("Gufo_Anello_Occhio", (1.0, 0.65, 0.08), 1.5)
    m_eye = m_radial_glow("Gufo_Occhio_Faro", [(0.0, (1.0, 1.0, 0.92)), (0.3, (1.0, 0.95, 0.5)),
                                               (0.65, (1.0, 0.78, 0.12)), (0.9, (1.0, 0.5, 0.02)),
                                               (1.0, (0.4, 0.12, 0.0))], 3.0,
                          pulse=(2.4, 3.8, 1, 0.0))
    m_cornea = m_glass_eye("Gufo_Cornea")
    m_beak = m_body("Gufo_Becco", (0.25, 0.2, 0.12), rough=0.3, coat=0.6,
                    emit=(1.0, 0.7, 0.2), emit_str=0.15)
    m_claw = m_body("Gufo_Artigli", (0.06, 0.05, 0.045), rough=0.25, coat=0.8)
    m_foot = m_body("Gufo_Zampe", (0.35, 0.28, 0.12), rough=0.6, bump=(60.0, 0.3, 'scales'))
    m_wood = m_bark("Gufo_Corteccia")
    m_leaf = m_body("Gufo_Foglia", (0.02, 0.07, 0.02), rough=0.4, sss=0.2,
                    rim=(0.5, 0.9, 0.2), rim_str=0.25)
    m_aura = m_halo("Gufo_Aura_Ali", (1.0, 0.62, 0.1), 6.0, pulse=(3.0, 9.0, 2, 0.5))

    # --- ramo e tronco ------------------------------------------------------
    tube("Gufo_Tronco", [(-1.45, 0.55, -0.05), (-1.4, 0.53, 0.8), (-1.38, 0.54, 1.6), (-1.42, 0.56, 2.6)],
         [0.22, 0.19, 0.18, 0.17], m_wood, bevel_res=6)
    tube("Gufo_Ramo", [(-1.3, 0.48, 1.02), (-0.6, 0.18, 0.92), (0.1, 0.05, 0.9), (0.7, 0.02, 0.95),
                       (1.25, 0.0, 1.05)], [0.1, 0.075, 0.065, 0.05, 0.03], m_wood, bevel_res=5)
    tube("Gufo_Rametto", [(0.75, 0.02, 0.96), (0.95, -0.05, 1.18), (1.05, -0.08, 1.35)],
         [0.025, 0.017, 0.008], m_wood, bevel_res=3)
    leaf = feather_mesh("Gufo_Foglia", 0.22, 0.1, m_leaf, rows=8, cols=4, curl=-0.15,
                        shape='pointed')
    leaves = ((1.05, -0.08, 1.35, 60, 160), (1.24, 0.0, 1.05, 80, 70), (0.96, -0.05, 1.2, 40, -60),
              (-0.62, 0.18, 0.95, 70, 200), (0.5, 0.03, 0.93, 100, 20))
    for i, (x, y, z, rx, rz) in enumerate(leaves):
        lf = bpy.data.objects.new("Gufo_Foglia_%d" % i, leaf)
        lf.location = (x, y, z)
        lf.rotation_euler = (radians(rx), 0, radians(rz))
        link(lf)

    # --- corpo (uovo) + testa grande -----------------------------------------
    base_z = 0.95                        # altezza del ramo sotto le zampe
    E = [ellipsoid((0, 0.02, base_z + 0.36), 0.26 * K, (1.0, 0.92, 1.18)),
         ellipsoid((0, 0.0, base_z + 0.22), 0.22 * K, (1.05, 0.95, 0.8)),
         ellipsoid((0, -0.01, base_z + 0.78), 0.26 * K, (1.12, 0.95, 0.9))]
    body = metaball_mesh("Gufo_Corpo", E, m_down, res=0.025)
    bvh = bvh_of(body)
    head_c = Vector((0, -0.01, base_z + 0.78))
    body_c = Vector((0, 0.02, base_z + 0.36))

    # --- piume a tegola con bordi al neon --------------------------------------
    f_big = feather_mesh("Gufo_Piuma_M", 0.17, 0.13, m_f, curl=0.12)
    f_small = feather_mesh("Gufo_Piuma_S", 0.13, 0.11, m_f, curl=0.12)
    f_chest = feather_mesh("Gufo_Piuma_Petto", 0.12, 0.11, m_f2, curl=0.1)

    def face_zone(d, z):
        # lascia libero il disco facciale (davanti alla testa)
        dd = Vector((d.x, d.y, 0)).normalized()
        return z > base_z + 0.58 and dd.y < -0.35

    def chest_zone(d, z):
        dd = Vector((d.x, d.y, 0)).normalized()
        return dd.y < -0.55

    random.seed(3)
    scatter_feathers("Gufo_PiumaTesta", bvh, head_c, [f_small], rows=6,
                     zr=(base_z + 1.0, base_z + 0.62), cols=lambda t: int(10 + 14 * t),
                     skip=face_zone, lift=5, scale=1.0)
    scatter_feathers("Gufo_PiumaDorso", bvh, body_c, [f_big, f_small], rows=8,
                     zr=(base_z + 0.62, base_z + 0.12), cols=24, skip=chest_zone,
                     lift=6, scale=1.05)
    scatter_feathers("Gufo_PiumaPetto", bvh, body_c, [f_chest], rows=9,
                     zr=(base_z + 0.6, base_z + 0.1), cols=28,
                     skip=lambda d, z: not chest_zone(d, z), lift=4, scale=0.95)

    # ciuffi auricolari (stilizzati)
    for sx in (-1, 1):
        for k in range(3):
            loc, nor = surface_hit(bvh, head_c, (0.55 * sx, -0.15 + 0.1 * k, 0.8))
            m = frame_matrix(loc, Vector((0.35 * sx, 0.1, 1.0)), nor)
            m = m @ Matrix.Rotation(radians(30 + 8 * k), 4, 'X')
            ob = bpy.data.objects.new("Gufo_Ciuffo_%s%d" % ("L" if sx < 0 else "R", k), f_big)
            ob.matrix_world = m @ Matrix.Diagonal((0.8, 1.1 - 0.15 * k, 0.8, 1.0))
            link(ob)

    # --- ali semiaperte a ventaglio (remiganti + copritrici) -------------------
    f_prim = feather_mesh("Gufo_Remigante", 0.5, 0.15, m_f, rows=14, curl=0.06)
    f_cov = feather_mesh("Gufo_Copritrice", 0.26, 0.14, m_f, rows=10, curl=0.06)
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        out = Vector((sx * 1.0, 0.45, 0.0)).normalized()
        up = Vector((0, 0, 1))
        nrm = Vector((out.y, -out.x, 0.0))
        if nrm.y > 0:
            nrm = -nrm
        nrm = (nrm + Vector((0, 0, 0.25))).normalized()
        sh, _n = surface_hit(bvh, body_c + Vector((0, 0.04, 0.2)), out)
        sh = sh - out * 0.05
        tips = []
        for k in range(8):
            t = k / 7
            phi = radians(-78 + 60 * t)
            d = (out * cos(phi) + up * sin(phi)).normalized()
            ln = 0.85 + 0.25 * sin(pi * min(1.0, t * 1.3))
            m = frame_matrix(sh + nrm * (0.012 * (7 - k)) + d * 0.02, d, nrm)
            ob = bpy.data.objects.new("Gufo_Remigante_%s_%d" % (side, k), f_prim)
            ob.matrix_world = m @ Matrix.Diagonal((1.0, ln, 1.0, 1.0))
            link(ob)
            tips.append(sh + d * 0.5 * ln)
        for k in range(6):
            t = k / 5
            phi = radians(-70 + 55 * t)
            d = (out * cos(phi) + up * sin(phi)).normalized()
            m = frame_matrix(sh + nrm * (0.1 + 0.01 * k) - d * 0.02, d, nrm)
            ob = bpy.data.objects.new("Gufo_Copritrice_%s_%d" % (side, k), f_cov)
            ob.matrix_world = m
            link(ob)
        # aura luminosa attorno alle punte delle ali
        tip = sum(tips[1:6], Vector()) / 5.0 + out * 0.02
        halo = sphere("Gufo_AuraPunta_" + side, tip, (0.26, 0.26, 0.3), m_aura)
        no_shadow(halo)
        add_light("Gufo_LucePunta_" + side, 'POINT', tip, 1.5, (1.0, 0.75, 0.25), 0.1,
                  pulse=(0.5, 2.5, 2, 0.5))

    # --- disco facciale + occhi-faro enormi -------------------------------------
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        d = Vector((0.5 * sx, -1.0, 0.05))
        loc, nor = surface_hit(bvh, head_c, d)
        disc = sphere("Gufo_Disco_" + side, (0, 0, 0), 1.0, m_disc, seg=32, rings=16)
        orient(disc, loc - nor * 0.035, (nor + Vector((0, -0.6, 0))).normalized(),
               scale=(0.2, 0.2, 0.06))
        c = loc + nor * 0.005
        eye = sphere("Gufo_Occhio_" + side, (0, 0, 0), 1.0, m_eye, seg=48, rings=24)
        dirv = (nor + Vector((0, -0.8, 0))).normalized()
        orient(eye, c, dirv, scale=(0.125, 0.125, 0.05))
        cor = sphere("Gufo_Cornea_" + side, (0, 0, 0), 1.0, m_cornea, seg=48, rings=24)
        orient(cor, c + dirv * 0.005, dirv, scale=(0.13, 0.13, 0.07))
        no_shadow(cor)
        # anello dorato attorno all'occhio
        fr = frame_matrix(c + dirv * 0.004, (0, 0, 1), dirv)
        pts = [fr @ Vector((0.132 * cos(a), 0.132 * sin(a), 0.0))
               for a in [TAU * i / 24 for i in range(24)]]
        tube("Gufo_AnelloOcchio_" + side, pts + [pts[0]], 0.009, m_ring, bevel_res=2, poly=True)
        # fari: luce spot proiettata in avanti
        sp = add_light("Gufo_Faro_" + side, 'SPOT', c + dirv * 0.05, 18.0, (1.0, 0.85, 0.4), 0.05,
                       spot_size=38, pulse=(12.0, 20.0, 1, 0.0))
        aim(sp, c + dirv * 3.0 + Vector((0, 0, -1.2)))

    # becco
    bl, bn = surface_hit(bvh, head_c, (0, -1.0, -0.35))
    cone_between("Gufo_Becco", bl - bn * 0.02, bl + Vector((0, -0.06, -0.08)), 0.035, 0.002, m_beak, 12)

    # zampe con artigli che stringono il ramo
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        top = Vector((0.1 * sx, -0.06, base_z + 0.12))
        sphere("Gufo_Zampa_" + side, top, (0.05, 0.05, 0.06), m_foot)
        for k, ang in enumerate((-25, 0, 25)):
            a = radians(ang)
            p0 = top + Vector((0.02 * sin(a), -0.02, -0.04))
            p1 = Vector((p0.x + 0.05 * sin(a), -0.11, base_z + 0.03))
            p2 = Vector((p0.x + 0.06 * sin(a), -0.08, base_z - 0.06))
            tube("Gufo_Dito_%s%d" % (side, k), [p0, p1, p2], [0.018, 0.014, 0.01], m_foot, bevel_res=2)
            cone_between("Gufo_Artiglio_%s%d" % (side, k), p2, p2 + Vector((0, 0.04, -0.03)),
                         0.01, 0.0, m_claw, 8)

    add_light("Gufo_Luce_Piume", 'POINT', (0, -0.6, base_z + 0.6), 1.0, (1.0, 0.8, 0.35), 0.4,
              pulse=(0.6, 1.4, 2, 0.0))


# ============================================================================
# 04  RANABUIO (Dark-Frog)
# ============================================================================

def build_frog():
    K = 1.65
    m_skin = m_body("Rana_Pelle_Bagnata", (0.01, 0.045, 0.015), rough=0.22, coat=1.0,
                    coat_rough=0.03, spec=0.6, sss=0.08, sss_radius=(0.3, 1.0, 0.3),
                    bump=(28.0, 0.35, 'warts'), mottle=((0.028, 0.085, 0.025), 5.0),
                    rim=(0.2, 0.6, 0.25), rim_str=0.25)
    m_belly = m_body("Rana_Ventre", (0.06, 0.08, 0.035), rough=0.3, coat=0.8,
                     bump=(40.0, 0.2, 'warts'))
    m_spots = [m_emit("Rana_Punto_Luce_%d" % i, (1.0, 0.3, 0.01), 2.0,
                      pulse=(0.5, 2.6, 2, i * 2.1)) for i in range(3)]
    m_sac = m_body("Rana_Sacca_Vocale", (0.9, 0.22, 0.01), rough=0.12, coat=1.0,
                   sss=0.6, sss_radius=(1.0, 0.3, 0.05), emit=(1.0, 0.28, 0.01),
                   emit_pulse=(0.5, 3.2, 2, 0.0), emit_center=True, alpha=0.9)
    m_bulb = m_emit("Rana_Bulbilli", (1.0, 0.55, 0.08), 2.5, pulse=(1.5, 3.0, 2, 1.0))
    m_iris = m_radial_glow("Rana_Iride", [(0.0, (1.0, 0.6, 0.1)), (0.6, (0.9, 0.35, 0.02)),
                                          (1.0, (0.25, 0.08, 0.0))], 0.9)
    m_pupil = m_body("Rana_Pupilla", (0.0, 0.0, 0.0), rough=0.05, coat=1.0)
    m_cornea = m_glass_eye("Rana_Cornea")
    m_wing_r = m_wing("Rana_Ali_Insetto",
                      [(0.0, (0.2, 0.8, 0.3)), (0.5, (1.0, 0.55, 0.05)), (1.0, (1.0, 0.35, 0.02))],
                      alpha=0.06, membrane_str=0.1, vein_str=1.8, radial=(6, 0.07),
                      cross=None, edge=0.07, cells=(14.0, 0.025, 0.55), v_mix=1.0,
                      facing_mix=0.2, distort=0.02, pulse=(0.7, 1.2, 2, 0.0))

    E = [ellipsoid((0, 0.12, 0.3), 0.3 * K, (1.15, 1.3, 0.78)),
         ellipsoid((0, -0.22, 0.34), 0.25 * K, (1.2, 0.95, 0.7)),
         ellipsoid((0, -0.43, 0.3), 0.14 * K, (1.35, 0.85, 0.62)),
         ball((0, -0.3, 0.2), 0.14 * K)]
    for sx in (-1, 1):
        E.append(ball((0.17 * sx, -0.3, 0.5), 0.1 * K))
        # zampe anteriori
        E.append(capsule((0.2 * sx, -0.22, 0.24), (0.27 * sx, -0.32, 0.12), 0.055 * K))
        E.append(capsule((0.27 * sx, -0.32, 0.12), (0.26 * sx, -0.43, 0.035), 0.04 * K))
        # zampe posteriori ripiegate
        E.append(ellipsoid((0.3 * sx, 0.3, 0.2), 0.14 * K, (0.85, 1.4, 0.85)))
        E.append(capsule((0.4 * sx, 0.05, 0.13), (0.36 * sx, 0.42, 0.07), 0.065 * K))
        E.append(capsule((0.36 * sx, 0.42, 0.07), (0.42 * sx, 0.0, 0.03), 0.042 * K))
    body = metaball_mesh("Rana_Corpo", E, m_skin, res=0.022)
    bvh = bvh_of(body)
    body_c = Vector((0, 0.05, 0.3))

    # ventre chiaro (leggermente sotto)
    sphere("Rana_Ventre", (0, 0.02, 0.2), (0.32, 0.42, 0.13), m_belly)

    # occhi sporgenti
    for sx in (-1, 1):
        make_eye("Rana_Occhio_" + ("L" if sx < 0 else "R"), bvh, Vector((0.17 * sx, -0.3, 0.46)),
                 (0.75 * sx, -0.55, 0.6), 0.075, m_iris, m_pupil, m_cornea,
                 pupil=(0.62, 0.22), sink=0.3, flat=0.85)

    # sacca vocale sotto la gola (pulsa e si gonfia)
    sac = sphere("Rana_SaccaVocale", (0, -0.44, 0.16), (0.14, 0.12, 0.11), m_sac)
    no_shadow(sac)
    w = TAU * 2 / ANIM_FRAMES
    for i, base in enumerate((0.14, 0.12, 0.11)):
        add_driver(sac, "scale", "%.4f*(0.82+0.3*(0.5+0.5*sin(frame*%.6f)))" % (base, w), i,
                   meta=dict(tipo='scala', lo=0.82, hi=1.12, cyc=2, ph=0.0) if i == 0 else None)
    add_light("Rana_LuceGola", 'POINT', (0, -0.62, 0.16), 6.0, (1.0, 0.4, 0.05), 0.08,
              pulse=(1.0, 12.0, 2, 0.0))

    # punti luminosi su schiena e fianchi (posizionati sulla superficie)
    random.seed(11)
    spots = []
    tries = 0
    while len(spots) < 22 and tries < 500:
        tries += 1
        a = random.uniform(0, TAU)
        el = random.uniform(radians(10), radians(80))
        d = Vector((cos(a) * cos(el), sin(a) * cos(el) * 1.2 + 0.2, sin(el)))
        if d.y < -0.35 and d.z > 0.3:
            continue        # niente punti sulla testa
        loc, nor = surface_hit(bvh, body_c, d)
        if loc is None or loc.z < 0.18 or any((loc - q).length < 0.1 for q in spots):
            continue
        spots.append(loc)
        r = random.uniform(0.022, 0.042)
        sp = sphere("Rana_Punto_%02d" % len(spots), (0, 0, 0), 1.0,
                    m_spots[len(spots) % 3], seg=16, rings=8)
        orient(sp, loc - nor * r * 0.2, nor, scale=(r, r, r * 0.45))

    # dita con bulbili luminosi
    feet = [((0.26, -0.43, 0.03), (0.0, -1.0), 0.12), ((0.42, 0.0, 0.03), (0.3, -1.0), 0.2)]
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        for fi, (base, fdir, ln) in enumerate(feet):
            b = Vector((base[0] * sx, base[1], base[2]))
            ang0 = math.atan2(fdir[0] * sx, fdir[1])
            for k in range(4):
                a = ang0 + radians((-36 + 24 * k) * sx)
                d = Vector((sin(a), cos(a), 0.0))
                toe = ln * (0.8 + 0.25 * (1 - abs(k - 1.5) / 1.5))
                p1 = b + d * toe * 0.55 + Vector((0, 0, 0.012))
                p2 = b + d * toe
                tube("Rana_Dito_%s%d%d" % (side, fi, k), [b, p1, p2], [0.016, 0.011, 0.009],
                     m_skin, bevel_res=2)
                sphere("Rana_Bulbillo_%s%d%d" % (side, fi, k), p2 + Vector((0, 0, 0.006)), 0.017, m_bulb,
                       seg=16, rings=8)

    # ali da insetto sulla schiena e lungo i fianchi
    fore = [(-6, 0.15), (-3, 0.55), (0, 0.72), (4, 0.7), (9, 0.5), (13, 0.15)]
    wing_pair("Rana_AlaDorso", fore, m_wing_r, (0.1, 0.05, 0.5), elev=42, sweep=38, roll=-10,
              rings=10, flap=(10, 4, 0.0))
    wing_pair("Rana_AlaDorso2", fore, m_wing_r, (0.1, 0.18, 0.5), elev=30, sweep=58, roll=-10,
              rings=10, flap=(10, 4, 0.8))
    side_w = [(-8, 0.12), (-4, 0.38), (0, 0.48), (5, 0.45), (10, 0.3), (14, 0.1)]
    wing_pair("Rana_AlaFianco", side_w, m_wing_r, (0.34, 0.12, 0.3), elev=14, sweep=62, roll=-55,
              rings=8, flap=(8, 4, 1.6))
    add_light("Rana_LuceDorso", 'POINT', (0, 0.15, 0.7), 2.0, (1.0, 0.45, 0.08), 0.3,
              pulse=(1.0, 3.0, 2, 2.1))


# ============================================================================
# 05  FARFALLA-GLOW (Glow-Butterfly)
# ============================================================================

def build_butterfly():
    H = 0.95
    m_dark = m_body("Farfalla_Corpo_Scuro", (0.008, 0.01, 0.018), rough=0.45, sheen=1.0,
                    sheen_tint=(0.2, 0.5, 1.0), rim=(0.1, 0.5, 1.0), rim_str=0.6,
                    bump=(200.0, 0.15, 'noise'))
    m_tip = m_emit("Farfalla_Punte_Antenne", (0.3, 1.0, 0.7), 5.0, pulse=(3.0, 6.0, 2, 0.0))
    m_core = m_halo("Farfalla_Cuore_Luce", (0.1, 0.55, 1.0), 12.0, pulse=(4.0, 20.0, 2, 0.0))
    m_eye = m_body("Farfalla_Occhi", (0.02, 0.05, 0.1), rough=0.1, coat=1.0,
                   emit=(0.1, 0.6, 1.0), emit_str=0.8)
    sapph = [(0.0, (0.0, 0.01, 0.06)), (0.3, (0.02, 0.12, 0.9)), (0.55, (0.0, 0.35, 1.0)),
             (0.8, (0.0, 0.8, 0.55)), (1.0, (0.2, 1.0, 0.55))]
    veins = [(0.0, (0.1, 0.35, 1.0)), (0.6, (0.1, 0.7, 1.0)), (1.0, (0.1, 1.0, 0.6))]
    m_fore = m_wing("Farfalla_Ala_Anteriore", sapph, alpha=0.7, membrane_str=0.45,
                    vein_ramp=veins, vein_str=2.2, radial=(12, 0.06), cross=(5, 0.035),
                    edge=0.045, cells=(9.0, 0.02, 0.35), v_mix=0.8, facing_mix=0.35,
                    distort=0.015, dots=(16, 0.86, 0.018),
                    spots=[(0.3, 0.55, 0.07, True), (0.62, 0.6, 0.05, True)],
                    pulse=(0.8, 1.15, 2, 0.5))
    m_hind = m_wing("Farfalla_Ala_Posteriore", sapph, alpha=0.7, membrane_str=0.45,
                    vein_ramp=veins, vein_str=2.2, radial=(9, 0.06), cross=(4, 0.035),
                    edge=0.05, cells=(9.0, 0.02, 0.35), v_mix=0.8, facing_mix=0.35,
                    distort=0.015, dots=(12, 0.84, 0.022),
                    spots=[(0.45, 0.62, 0.09, True)], pulse=(0.8, 1.15, 2, 1.0))

    # corpo sottile e scuro
    sphere("Farfalla_Testa", (0, -0.3, H + 0.02), 0.055, m_dark)
    for sx in (-1, 1):
        sphere("Farfalla_Occhio_%s" % ("L" if sx < 0 else "R"), (0.035 * sx, -0.33, H + 0.035),
               0.03, m_eye)
    sphere("Farfalla_Torace", (0, -0.17, H), (0.065, 0.13, 0.07), m_dark)
    tube("Farfalla_Addome", [(0, -0.05, H), (0, 0.15, H - 0.02), (0, 0.35, H - 0.05), (0, 0.52, H - 0.09)],
         [0.055, 0.045, 0.03, 0.01], m_dark, bevel_res=5)
    # proboscide arrotolata
    pr = [(0, -0.34, H - 0.02)]
    for i in range(1, 10):
        a = i * 0.7
        r = 0.035 * (1 - i / 12)
        pr.append((0, -0.36 - r * sin(a), H - 0.05 - r * (1 - cos(a))))
    tube("Farfalla_Proboscide", pr, 0.004, m_dark, bevel_res=1)
    # antenne lunghe con punte luminose
    m_ant_halo = m_halo("Farfalla_Aura_Antenna", (0.2, 1.0, 0.7), 8.0, pulse=(4.0, 10.0, 2, 0.0))
    for sx in (-1, 1):
        side = "L" if sx < 0 else "R"
        pts = [(0.02 * sx, -0.33, H + 0.06), (0.08 * sx, -0.5, H + 0.2), (0.18 * sx, -0.66, H + 0.34),
               (0.3 * sx, -0.76, H + 0.42)]
        tube("Farfalla_Antenna_" + side, pts, [0.006, 0.005, 0.004, 0.005], m_dark, bevel_res=1)
        sphere("Farfalla_AntennaPunta_" + side, pts[-1], (0.016, 0.03, 0.016), m_tip)
        no_shadow(sphere("Farfalla_AntennaAura_" + side, pts[-1], 0.06, m_ant_halo))
    # zampe sottili ripiegate
    for sx in (-1, 1):
        for k in range(3):
            y = -0.24 + 0.08 * k
            tube("Farfalla_Zampa_%s%d" % ("L" if sx < 0 else "R", k),
                 [(0.03 * sx, y, H - 0.05), (0.12 * sx, y - 0.05, H - 0.1), (0.14 * sx, y + 0.04, H - 0.2)],
                 [0.007, 0.005, 0.003], m_dark, bevel_res=1)
    # bagliore pulsante al centro del corpo
    core = sphere("Farfalla_Cuore", (0, -0.15, H), (0.2, 0.26, 0.18), m_core)
    no_shadow(core)
    add_light("Farfalla_LuceCuore", 'POINT', (0, -0.15, H + 0.12), 6.0, (0.15, 0.5, 1.0), 0.15,
              pulse=(2.0, 14.0, 2, 0.0))

    # ali imponenti
    fore = [(-20, 0.2), (-12, 0.8), (-4, 1.3), (6, 1.58), (16, 1.5), (32, 1.2), (50, 1.0),
            (66, 0.85), (80, 0.5), (88, 0.2)]
    hind = [(50, 0.2), (64, 0.62), (84, 0.98), (104, 1.08), (122, 1.0), (134, 1.02), (141, 1.42),
            (148, 1.0), (160, 0.72), (172, 0.3)]
    wing_pair("Farfalla_AlaAnt", fore, m_fore, (0.04, -0.2, H + 0.03), elev=18, sweep=-4,
              roll=-4, rings=16, cup=0.06, flap=(16, 2, 0.0), n=80)
    wing_pair("Farfalla_AlaPost", hind, m_hind, (0.04, -0.1, H), elev=12, sweep=0,
              roll=-4, rings=14, cup=0.05, flap=(16, 2, 0.15), n=80)


# ============================================================================
# 06  LIBELLULA-FULMINE (Lightning-Dragonfly)
# ============================================================================

def build_dragonfly():
    H = 0.95
    m_azure = m_body("Libellula_Azzurro", (0.05, 0.45, 0.9), rough=0.25, metal=0.25, coat=1.0,
                     coat_rough=0.03, emit=(0.1, 0.5, 1.0), emit_str=0.25,
                     rim=(0.3, 0.8, 1.0), rim_str=0.8)
    m_gold = m_body("Libellula_Oro", (1.0, 0.62, 0.12), rough=0.2, metal=1.0,
                    emit=(1.0, 0.6, 0.1), emit_str=1.2, emit_pulse=(0.6, 2.0, 3, 0.0))
    m_eye = m_body("Libellula_Occhi", (0.02, 0.3, 0.7), rough=0.15, coat=1.0, metal=0.2,
                   bump=(90.0, 0.5, 'scales'), emit=(0.05, 0.45, 1.0), emit_str=0.5,
                   rim=(0.3, 0.85, 1.0), rim_str=0.4)
    m_bulb = m_emit("Libellula_Bulbo", (1.0, 0.8, 0.35), 8.0, pulse=(2.0, 12.0, 2, 0.0))
    m_bulb_halo = m_halo("Libellula_Aura_Bulbo", (1.0, 0.7, 0.2), 10.0, pulse=(2.0, 16.0, 2, 0.0))
    m_leg = m_body("Libellula_Zampe", (0.02, 0.03, 0.05), rough=0.3)
    m_wng = m_wing("Libellula_Ala_Circuito",
                   [(0.0, (0.3, 0.6, 1.0)), (1.0, (0.4, 0.8, 1.0))],
                   alpha=0.03, membrane_str=0.05,
                   vein_ramp=[(0.0, (1.0, 0.65, 0.08)), (0.5, (1.0, 0.8, 0.2)), (1.0, (0.2, 0.55, 1.0))],
                   vein_str=4.0, radial=(6, 0.045), cross=None, edge=0.035,
                   cells=(16.0, 0.022, 1.0), cell_color=(0.1, 0.45, 1.0), cell_str=1.6,
                   v_mix=1.0, distort=0.06, spots=[(0.04, 0.84, 0.05, False)],
                   pulse=(0.7, 1.3, 3, 0.0))

    # testa con enormi occhi composti
    for sx in (-1, 1):
        sphere("Libellula_Occhio_%s" % ("L" if sx < 0 else "R"), (0.065 * sx, -0.78, H + 0.04),
               (0.085, 0.08, 0.085), m_eye)
    sphere("Libellula_Faccia", (0, -0.82, H - 0.01), (0.07, 0.05, 0.06), m_azure)
    # torace robusto con strisce d'oro
    sphere("Libellula_Torace", (0, -0.58, H), (0.095, 0.16, 0.11), m_azure, rot=(-12, 0, 0))
    for sx in (-1, 1):
        tube("Libellula_Striscia_%s" % ("L" if sx < 0 else "R"),
             [(0.08 * sx, -0.68, H + 0.05), (0.095 * sx, -0.58, H + 0.02), (0.08 * sx, -0.47, H - 0.04)],
             0.012, m_gold, bevel_res=2)
    # addome lungo e segmentato (azzurro con anelli dorati)
    n = 10
    for i in range(n):
        t = i / (n - 1)
        y = -0.42 + 1.45 * t
        z = H - 0.02 - 0.05 * t * t
        r = 0.045 - 0.012 * t
        sphere("Libellula_Segmento_%02d" % i, (0, y, z), (r, 0.085, r), m_azure)
        sphere("Libellula_Anello_%02d" % i, (0, y + 0.078, z), (r * 1.08, 0.014, r * 1.08), m_gold)
    tip_y = -0.42 + 1.45 + 0.1
    sphere("Libellula_BulboLuce", (0, tip_y, H - 0.08), (0.055, 0.07, 0.055), m_bulb)
    halo = sphere("Libellula_AuraBulbo", (0, tip_y, H - 0.08), 0.2, m_bulb_halo)
    no_shadow(halo)
    add_light("Libellula_LuceBulbo", 'POINT', (0, tip_y, H - 0.08), 6.0, (1.0, 0.75, 0.3), 0.06,
              pulse=(1.0, 10.0, 2, 0.0))
    # zampe ripiegate sotto il torace
    for sx in (-1, 1):
        for k in range(3):
            y = -0.66 + 0.08 * k
            tube("Libellula_Zampa_%s%d" % ("L" if sx < 0 else "R", k),
                 [(0.03 * sx, y, H - 0.09), (0.1 * sx, y - 0.04, H - 0.16), (0.08 * sx, y - 0.12, H - 0.24)],
                 [0.008, 0.006, 0.004], m_leg, bevel_res=1)

    # quattro ali lunghe, trasparenti, con venature a circuito
    fore = [(-5, 0.15), (-3, 0.75), (-1, 1.2), (2, 1.34), (6, 1.24), (10, 0.75), (13, 0.2)]
    hind = [(-6, 0.15), (-3, 0.7), (0, 1.15), (4, 1.26), (10, 1.1), (16, 0.55), (21, 0.15)]
    wing_pair("Libellula_AlaAnt", fore, m_wng, (0.05, -0.62, H + 0.07), elev=4, sweep=-10,
              roll=0, rings=14, droop=0.03, flap=(10, 6, 0.0), n=72)
    wing_pair("Libellula_AlaPost", hind, m_wng, (0.05, -0.5, H + 0.07), elev=2, sweep=14,
              roll=0, rings=14, droop=0.03, flap=(10, 6, 1.2), n=72)
    add_light("Libellula_LuceAli", 'POINT', (0, -0.55, H + 0.35), 3.0, (0.3, 0.6, 1.0), 0.4,
              pulse=(1.5, 4.0, 3, 0.0))


# ============================================================================
# 07  LUPO-LUCE (Light-Wolf)
# ============================================================================

def build_wolf():
    K = 1.65
    turq = (0.05, 1.0, 0.82)
    m_spirit = m_ghost("Lupo_Corpo_Spettrale", (0.85, 0.9, 0.95), turq, alpha=0.28,
                       core=0.12, rim=2.2, pulse=(0.45, 1.4, 1, 0.0),
                       core_color=(0.6, 0.95, 1.0))
    m_eye = m_radial_glow("Lupo_Occhi", [(0.0, (1.0, 1.0, 1.0)), (0.5, (0.5, 1.0, 0.95)),
                                         (1.0, (0.0, 0.8, 0.7))], 6.0, pulse=(4.0, 7.0, 1, 0.0))
    m_nose = m_ghost("Lupo_Naso", (0.3, 0.5, 0.55), turq, alpha=0.8, core=0.3, rim=0.8)
    m_wing_w = m_wing("Lupo_Ali_Delicate",
                      [(0.0, (0.05, 1.0, 0.8)), (1.0, (0.4, 1.0, 0.95))],
                      alpha=0.04, membrane_str=0.25, vein_str=3.0, radial=(5, 0.08),
                      edge=0.08, cells=(26.0, 0.03, 0.6), v_mix=1.0, facing_mix=0.3,
                      pulse=(0.6, 1.3, 1, 0.8))
    m_mote = m_emit("Lupo_Lucciole", (0.5, 1.0, 0.85), 6.0, pulse=(2.0, 8.0, 3, 0.0))

    E = [ellipsoid((0, -0.36, 0.82), 0.19 * K, (0.8, 1.15, 1.25)),
         ellipsoid((0, -0.02, 0.86), 0.12 * K, (0.85, 2.1, 0.85)),
         ellipsoid((0, 0.34, 0.85), 0.145 * K, (0.85, 1.2, 0.95)),
         capsule((0, -0.46, 0.95), (0, -0.62, 1.14), 0.11 * K),
         ellipsoid((0, -0.55, 1.0), 0.15 * K, (1.05, 0.85, 1.2)),
         ellipsoid((0, -0.72, 1.21), 0.115 * K, (1.15, 1.1, 0.9)),
         capsule((0, -0.8, 1.18), (0, -0.95, 1.14), 0.056 * K),
         capsule((0, -0.95, 1.14), (0, -1.07, 1.12), 0.04 * K),
         capsule((0, -0.8, 1.11), (0, -1.0, 1.085), 0.034 * K)]
    for sx in (-1, 1):
        E += [capsule((0.1 * sx, -0.4, 0.72), (0.09 * sx, -0.43, 0.36), 0.058 * K),
              capsule((0.09 * sx, -0.43, 0.36), (0.09 * sx, -0.45, 0.07), 0.037 * K),
              ellipsoid((0.09 * sx, -0.48, 0.03), 0.045 * K, (1.0, 1.4, 0.65)),
              capsule((0.1 * sx, 0.36, 0.78), (0.11 * sx, 0.26, 0.46), 0.07 * K),
              capsule((0.11 * sx, 0.26, 0.46), (0.1 * sx, 0.5, 0.21), 0.043 * K),
              capsule((0.1 * sx, 0.5, 0.21), (0.095 * sx, 0.47, 0.05), 0.034 * K),
              ellipsoid((0.095 * sx, 0.44, 0.03), 0.045 * K, (1.0, 1.4, 0.65))]
    body = metaball_mesh("Lupo_Corpo", E, m_spirit, res=0.024)
    bvh = bvh_of(body)
    head_c = Vector((0, -0.74, 1.22))

    # orecchie a punta
    for sx in (-1, 1):
        e = cone_between("Lupo_Orecchio_%s" % ("L" if sx < 0 else "R"),
                         (0.07 * sx, -0.69, 1.28), (0.1 * sx, -0.66, 1.47), 0.058, 0.003, m_spirit, 16)
        e.scale = (1.0, 0.55, 1.0)
    # coda folta
    tube("Lupo_Coda", [(0, 0.48, 0.9), (0.02, 0.7, 0.82), (0.05, 0.88, 0.62), (0.08, 0.97, 0.4)],
         [0.05, 0.1, 0.09, 0.025], m_spirit, bevel_res=6)
    # occhi che brillano
    for sx in (-1, 1):
        make_eye("Lupo_Occhio_" + ("L" if sx < 0 else "R"), bvh, head_c, (0.5 * sx, -1.0, 0.3),
                 0.032, m_eye, None, None, sink=0.4, flat=0.6)
    nl, nn = surface_hit(bvh, Vector((0, -0.95, 1.13)), (0, -1, 0.25))
    sphere("Lupo_Naso", nl, (0.03, 0.022, 0.022), m_nose)

    # minuscole ali da insetto sulla schiena
    small = [(-8, 0.1), (-4, 0.28), (0, 0.36), (5, 0.34), (10, 0.22), (14, 0.08)]
    wing_pair("Lupo_Ali", small, m_wing_w, (0.07, -0.3, 1.02), elev=38, sweep=40, roll=20,
              rings=8, flap=(14, 5, 0.0))
    wing_pair("Lupo_Ali2", small, m_wing_w, (0.07, -0.2, 1.0), elev=24, sweep=58, roll=20,
              rings=8, flap=(14, 5, 0.9))

    # lucciole che fluttuano intorno
    random.seed(21)
    w = TAU * 1 / ANIM_FRAMES
    for i in range(28):
        a = random.uniform(0, TAU)
        r = random.uniform(0.55, 1.2)
        loc = (cos(a) * r * 0.8, sin(a) * r, random.uniform(0.2, 1.6))
        m = sphere("Lupo_Lucciola_%02d" % i, loc, random.uniform(0.008, 0.016), m_mote,
                   seg=12, rings=6)
        no_shadow(m)
        cyc = random.choice((1, 2))
        ph = random.uniform(0, TAU)
        add_driver(m, "location", "%.4f+0.06*sin(frame*%.6f+%.3f)" % (loc[2], w * cyc, ph), 2,
                   meta=dict(tipo='bob', amp=0.06, cyc=cyc, ph=ph))
    add_light("Lupo_LuceInterna", 'POINT', (0, -0.2, 0.85), 6.0, (0.1, 1.0, 0.85), 0.4,
              pulse=(3.0, 9.0, 1, 0.0))
    add_light("Lupo_LuceTerra", 'POINT', (0, -0.1, 0.25), 4.0, (0.1, 1.0, 0.85), 0.5,
              pulse=(2.0, 6.0, 1, 0.0))


# ============================================================================
# 08  LA PICCOLA LUCINA FARFALLINA (The Brainrot Moth)
# ============================================================================

def add_fur(ob, mat_index, count=2600, length=0.1, children=14, radius=0.012, clump=0.25):
    """Pelo soffice con sistema particellare (hair)."""
    try:
        md = ob.modifiers.new("Pelo_Soffice", 'PARTICLE_SYSTEM')
        ps = md.particle_system.settings
        ps.type = 'HAIR'
    except Exception as exc:
        print("[creature] pelo non disponibile:", exc)
        return None
    for attr, val in (('count', count), ('hair_length', length), ('use_advanced_hair', True),
                      ('material', mat_index + 1), ('child_type', 'INTERPOLATED'),
                      ('child_percent', 4), ('child_nbr', 4), ('rendered_child_count', children),
                      ('clump_factor', clump), ('roughness_1', 0.02), ('roughness_2', 0.03),
                      ('roughness_endpoint', 0.02), ('display_step', 3), ('render_step', 4),
                      ('root_radius', 1.0), ('tip_radius', 0.1), ('radius_scale', radius),
                      ('use_hair_bspline', True)):
        if hasattr(ps, attr):
            try:
                setattr(ps, attr, val)
            except (TypeError, ValueError, AttributeError):
                pass
    md.particle_system.seed = 7
    return md


def build_moth():
    R = 0.42
    C = Vector((0, 0, R + 0.1))
    warm = (1.0, 0.72, 0.28)
    m_fluff = m_body("Lucina_Pelo_Soffice", (1.0, 0.76, 0.22), rough=0.6, sheen=1.0,
                     sheen_tint=(1.0, 0.8, 0.4), sss=0.2, sss_radius=(1.0, 0.6, 0.2),
                     emit=(1.0, 0.72, 0.2), emit_str=0.2, emit_pulse=(0.12, 0.32, 1, 0.0),
                     rim=(1.0, 0.75, 0.25), rim_str=0.35)
    m_white = m_body("Lucina_Occhio_Bianco", (0.95, 0.95, 0.92), rough=0.15, coat=1.0,
                     emit=(1.0, 0.95, 0.85), emit_str=0.25)
    m_pupil = m_body("Lucina_Pupilla", (0.005, 0.005, 0.01), rough=0.05, coat=1.0)
    m_spark = m_emit("Lucina_Luccichio", (1.0, 1.0, 1.0), 6.0)
    m_smile = m_body("Lucina_Sorriso", (0.08, 0.02, 0.02), rough=0.3)
    m_blush = m_emit("Lucina_Guance", (1.0, 0.35, 0.35), 0.8)
    m_ant = m_body("Lucina_Antenna", (0.25, 0.18, 0.1), rough=0.4, emit=warm, emit_str=0.3)
    m_metal = m_body("Lucina_Attacco_Metallo", (0.8, 0.75, 0.6), rough=0.25, metal=1.0)
    m_glass = m_glass_eye("Lucina_Vetro_Lampadina", (1.0, 0.95, 0.85))
    # su Roblox il vetro della lampadina diventa Neon caldo semitrasparente
    m_glass["rbx_kind"] = "neon"
    m_glass["rbx_color"] = [1.0, 0.8, 0.45]
    m_glass["rbx_transp"] = 0.45
    m_glass["rbx_pulse"] = [0.7, 1.0, 1.0, 0.0]
    m_bulb_glow = m_halo("Lucina_Luce_Lampadina", (1.0, 0.75, 0.3), 14.0, pulse=(11.0, 16.0, 1, 0.0),
                         softness=1.4)
    m_fil = m_emit("Lucina_Filamento", (1.0, 0.7, 0.25), 40.0, pulse=(32.0, 46.0, 1, 0.0))
    m_wing_m = m_wing("Lucina_Alette_Luce",
                      [(0.0, (1.0, 0.45, 0.02)), (0.6, (1.0, 0.65, 0.08)), (1.0, (1.0, 0.8, 0.2))],
                      alpha=0.1, membrane_str=0.9, vein_str=3.0, radial=(6, 0.1), edge=0.1,
                      v_mix=1.0, spots=[(0.5, 0.58, 0.12, True)], pulse=(0.8, 1.3, 2, 0.0))

    # --- la "polpetta" pelosa ---------------------------------------------------
    body = sphere("Lucina_Corpo", C, (R, R * 0.96, R * 0.92), m_fluff, seg=48, rings=24)
    add_fur(body, 0, count=3000, length=0.085, children=16)

    def front(d):
        return C + Vector((d[0] * R, d[1] * R * 0.96, d[2] * R * 0.92))

    # piedini
    for sx in (-1, 1):
        sphere("Lucina_Piedino_%s" % ("L" if sx < 0 else "R"), (0.16 * sx, -0.18, 0.07),
               (0.08, 0.1, 0.06), m_fluff)

    # occhioni ninnolo (googly eyes) che sporgono dal pelo
    for sx, (py, pz) in ((-1, (0.02, -0.03)), (1, (-0.02, -0.035))):
        side = "L" if sx < 0 else "R"
        d = Vector((0.36 * sx, -1.0, 0.32)).normalized()
        p = front(d) + d * 0.075
        er = 0.13 if sx < 0 else 0.145
        eye = sphere("Lucina_Occhio_" + side, (0, 0, 0), 1.0, m_white, seg=40, rings=20)
        orient(eye, p, d, scale=(er, er, er * 0.62))
        pc = p + d * er * 0.5 + Vector((py, 0, pz))
        pup = sphere("Lucina_Pupilla_" + side, (0, 0, 0), 1.0, m_pupil, seg=32, rings=16)
        orient(pup, pc, d, scale=(er * 0.52, er * 0.52, er * 0.25))
        spk = sphere("Lucina_Luccichio_" + side, (0, 0, 0), 1.0, m_spark, seg=16, rings=8)
        orient(spk, pc + d * er * 0.13 + Vector((0.03 * -sx, 0, 0.035)), d,
               scale=(er * 0.13, er * 0.13, er * 0.06))
        # guance rosa
        bd = Vector((0.62 * sx, -0.85, -0.05)).normalized()
        bl = sphere("Lucina_Guancia_" + side, (0, 0, 0), 1.0, m_blush, seg=16, rings=8)
        orient(bl, front(bd) + bd * 0.07, bd, scale=(0.06, 0.04, 0.015))

    # sorriso semplice e innocente
    pts = []
    for i in range(9):
        t = i / 8
        a = radians(-40 + 80 * t)
        d = Vector((sin(a) * 0.45, -1.0, -0.2 - 0.12 * cos(a * 2.2))).normalized()
        pts.append(front(d) + d * 0.08)
    tube("Lucina_Sorriso", pts, [0.008, 0.011, 0.012, 0.013, 0.013, 0.013, 0.012, 0.011, 0.008],
         m_smile, bevel_res=2)

    # alette minuscole, luminosissime
    wing_f = [(-30, 0.1), (-15, 0.3), (0, 0.4), (15, 0.42), (30, 0.34), (45, 0.2), (55, 0.08)]
    wing_h = [(45, 0.08), (60, 0.22), (80, 0.3), (100, 0.28), (118, 0.18), (130, 0.06)]
    wing_pair("Lucina_AlettaAnt", wing_f, m_wing_m, (0.37, 0.1, C.z + 0.08), elev=28, sweep=32,
              roll=70, rings=8, cup=0.03, flap=(22, 8, 0.0))
    wing_pair("Lucina_AlettaPost", wing_h, m_wing_m, (0.37, 0.12, C.z + 0.02), elev=28, sweep=32,
              roll=70, rings=8, cup=0.03, flap=(22, 8, 0.3))

    # --- antenna flessibile + LAMPADINA che dondola -----------------------------
    w = TAU / ANIM_FRAMES
    top = C + Vector((0, 0.0, R * 0.9))
    ant_piv = empty("Lucina_Antenna_Perno", top, 0.08)
    add_driver(ant_piv, "rotation_euler", "radians(7)*sin(frame*%.6f)" % (w * 2), 0,
               meta=dict(tipo='rot', amp=radians(7), cyc=2, ph=0.0))
    add_driver(ant_piv, "rotation_euler", "radians(5)*sin(frame*%.6f+1.3)" % (w * 1), 1,
               meta=dict(tipo='rot', amp=radians(5), cyc=1, ph=1.3))
    apts = [Vector(p) for p in ((0, 0.0, -0.05), (0, 0.02, 0.18), (0, -0.05, 0.4), (0, -0.2, 0.55),
                                (0, -0.36, 0.56), (0, -0.46, 0.48))]
    ant = tube("Lucina_Antenna", apts, [0.022, 0.018, 0.015, 0.013, 0.012, 0.011], m_ant, bevel_res=3)
    ant.location = top
    ant.parent = ant_piv
    ant.location = (0, 0, 0)
    tipw = top + apts[-1]
    bulb_piv = empty("Lucina_Lampadina_Perno", apts[-1], 0.06)
    bulb_piv.parent = ant_piv
    add_driver(bulb_piv, "rotation_euler", "radians(24)*sin(frame*%.6f+0.6)" % (w * 2), 0,
               meta=dict(tipo='rot', amp=radians(24), cyc=2, ph=0.6))
    add_driver(bulb_piv, "rotation_euler", "radians(10)*sin(frame*%.6f)" % (w * 1), 1,
               meta=dict(tipo='rot', amp=radians(10), cyc=1, ph=0.0))

    def bulb_part(ob):
        # figlio del perno della lampadina, lasciandolo dov'e' nello spazio
        ob.parent = bulb_piv
        ob.matrix_parent_inverse = Matrix.Translation(-tipw)
        return ob

    # attacco a vite (in alto), collo e vetro (in basso)
    bulb_part(cone_between("Lucina_Attacco", tipw + Vector((0, 0, 0.0)),
                           tipw + Vector((0, 0, -0.09)), 0.042, 0.042, m_metal, 24))
    for k in range(4):
        z = -0.015 - 0.02 * k
        ring = [tipw + Vector((0.046 * cos(TAU * i / 20), 0.046 * sin(TAU * i / 20), z)) for i in range(20)]
        bulb_part(tube("Lucina_Filetto_%d" % k, ring + [ring[0]], 0.006, m_metal, bevel_res=1, poly=True))
    bulb_part(sphere("Lucina_Contatto", tipw + Vector((0, 0, 0.005)), (0.02, 0.02, 0.012), m_metal))
    bulb_part(cone_between("Lucina_Collo", tipw + Vector((0, 0, -0.09)), tipw + Vector((0, 0, -0.14)),
                           0.042, 0.06, m_glass, 24))
    g = bulb_part(sphere("Lucina_Vetro", tipw + Vector((0, 0, -0.23)), (0.11, 0.11, 0.12), m_glass))
    no_shadow(g)
    zigzag = ((-0.015, -0.1), (-0.02, -0.19), (-0.01, -0.21), (0.0, -0.195), (0.01, -0.21),
              (0.02, -0.19), (0.015, -0.1))
    fil = [tipw + Vector((x, 0, z)) for x, z in zigzag]
    bulb_part(tube("Lucina_Filamento", fil, 0.004, m_fil, bevel_res=1))
    glow = bulb_part(sphere("Lucina_Bagliore", tipw + Vector((0, 0, -0.22)), 0.1, m_bulb_glow))
    no_shadow(glow)
    lamp = add_light("Lucina_Luce_Lampadina", 'POINT', tipw + Vector((0, 0, -0.22)), 18.0,
                     (1.0, 0.72, 0.35), 0.05, pulse=(14.0, 22.0, 1, 0.0))
    bulb_part(lamp)
    add_light("Lucina_Luce_Calda", 'POINT', C + Vector((0, -0.7, 0.3)), 2.0, warm, 0.6,
              pulse=(1.5, 2.5, 1, 0.0))


# ============================================================================
# STRUMENTI AGGIUNTIVI (usati dalle serie della neve e dell'oceano)
# ============================================================================

# Tinte pure dell'arcobaleno, nell'ordine della ruota dei colori: passando
# dall'una all'altra si ottiene lo stesso ciclo del nodo Hue/Saturation.
ARCOBALENO = [(1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
              (0.0, 1.0, 1.0), (0.0, 0.0, 1.0), (1.0, 0.0, 1.0)]


def hue_expr(cycles, phase, channel):
    """Espressione driver per un canale (0=R, 1=G, 2=B) di una tinta che fa il
    giro completo dell'arcobaleno `cycles` volte ogni ANIM_FRAMES.
    phase e' in giri (0..1)."""
    h = "fmod(frame*%.6f+%.4f,1.0)" % (cycles / ANIM_FRAMES, phase)
    if channel == 0:
        return "min(max(abs(6*%s-3)-1,0),1)" % h
    return "min(max(2-abs(6*%s-%d),0),1)" % (h, 2 if channel == 1 else 4)


def color_cycle_light(ob, cycles, phase=0.0):
    """Luce che cambia colore passando per tutto l'arcobaleno."""
    ld = ob.data
    for i in range(3):
        add_driver(ld, "color", hue_expr(cycles, phase, i), i)
    ANIMAZIONI.append(dict(owner=ld, path="color", index=-1, tipo='colore',
                           pal=[list(c) for c in ARCOBALENO], cyc=cycles, ph=phase))
    return ob


def m_hue_cycle(name, strength, cycles, phase=0.0, sat=1.0):
    """Emissione che scorre su tutti i colori: il nodo Hue/Saturation/Value ha
    la tonalita' guidata da un driver su #frame."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    hs = nb.node('ShaderNodeHueSaturation')
    nb.set(hs, 'Color', (1.0, 0.0, 0.0))
    nb.set(hs, 'Saturation', sat)
    nb.set(hs, 'Fac', 1.0)
    # Hue = 0.5 lascia il colore invariato: si parte dal rosso e si gira
    add_driver(hs.inputs['Hue'], "default_value",
               "fmod(frame*%.6f+%.4f,1.0)" % (cycles / ANIM_FRAMES, phase + 0.5))
    s = nb.glow(strength)
    nb.output(nb.emission(hs.outputs['Color'], s))
    diffuse_display(mat, (1.0, 0.2, 0.6))
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = [1.0, 0.0, 0.0]
    mat["rbx_cycle"] = {"pal": [list(c) for c in ARCOBALENO], "cyc": float(cycles), "ph": float(phase)}
    return mat


def m_sparkle(name, color, strength, twinkle=6.0):
    """Granelli luminosi che scintillano ognuno col suo ritmo (per le
    particelle: il valore casuale di Object Info e' diverso per ogni istanza)."""
    mat = new_material(name)
    nb = NodeBuilder(mat)
    oi = nb.node('ShaderNodeObjectInfo')
    t = nb.value(0.0, "frame*%.6f" % (TAU * twinkle / ANIM_FRAMES))
    x = nb.math('ADD', nb.math('MULTIPLY', oi.outputs['Random'], 97.0), t)
    tw = nb.maprange(nb.math('SINE', x), -1.0, 1.0, 0.15, 1.0)
    s = nb.glow(strength)
    nb.output(nb.emission(color, nb.math('MULTIPLY', tw, s)))
    diffuse_display(mat, color)
    mat["rbx_kind"] = "neon"
    mat["rbx_color"] = list(color[:3])
    return mat


def particle_scatter(emitter, inst_ob, count, size=1.0, size_random=0.6, emit_from='VOLUME', seed=3):
    """Sistema particellare che istanzia `inst_ob` dentro (o sopra)
    l'emettitore. E' di tipo HAIR, quindi le particelle sono fisse e si vedono
    subito, in ogni frame, senza simulazione. L'emettitore resta invisibile."""
    try:
        md = emitter.modifiers.new("Particelle", 'PARTICLE_SYSTEM')
        ps = md.particle_system.settings
        ps.type = 'HAIR'
    except Exception as exc:
        print("[creature] particelle non disponibili:", exc)
        return None
    for attr, val in (('count', count), ('hair_length', 0.05), ('emit_from', emit_from),
                      ('use_emit_random', True), ('render_type', 'OBJECT'),
                      ('instance_object', inst_ob), ('particle_size', size),
                      ('size_random', size_random), ('use_rotations', True),
                      ('rotation_factor_random', 1.0), ('use_advanced_hair', True)):
        if hasattr(ps, attr):
            try:
                setattr(ps, attr, val)
            except (TypeError, ValueError, AttributeError):
                pass
    md.particle_system.seed = seed
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False
    emitter["rbx_drop"] = 1           # su Roblox non esistono particelle
    inst_ob["rbx_drop"] = 1
    return md


def vgroup_from_uv(ob, name, fn):
    """Gruppo di vertici con peso fn(u, v) calcolato dalle UV (es. densita'
    del pelo solo alla base delle ali)."""
    me = ob.data
    uvl = me.uv_layers.active
    w = {}
    for lp in me.loops:
        u, v = uvl.data[lp.index].uv
        w[lp.vertex_index] = max(w.get(lp.vertex_index, 0.0), float(fn(u, v)))
    vg = ob.vertex_groups.new(name=name)
    for i, val in w.items():
        if val > 0:
            vg.add([i], min(1.0, val), 'REPLACE')
    return vg


def float_all(name, center, amp, cycles=1, phase=0.0, sway=None):
    """Tutta la creatura galleggia: un perno che sale e scende (e, se richiesto,
    oscilla: sway = (gradi_x, gradi_y)) a cui si attacca tutto quello che e'
    stato costruito finora."""
    center = vec(center)
    coll = _STATE["coll"]
    obs = [o for o in coll.objects if o.parent is None]
    piv = empty(name, center, 0.12)
    inv = Matrix.Translation(-center)
    for o in obs:
        o.parent = piv
        o.matrix_parent_inverse = inv
    w = TAU * cycles / ANIM_FRAMES
    add_driver(piv, "location", "%.4f+%.4f*sin(frame*%.6f+%.3f)" % (center.z, amp, w, phase), 2,
               meta=dict(tipo='mov', amp=amp, cyc=cycles, ph=phase))
    if sway:
        for i, deg in enumerate(sway):
            if deg:
                ph = phase + 1.1 * (i + 1)
                add_driver(piv, "rotation_euler", "radians(%.3f)*sin(frame*%.6f+%.3f)" % (deg, w, ph), i,
                           meta=dict(tipo='rot', amp=radians(deg), cyc=cycles, ph=ph))
    return piv


# ============================================================================
# REGISTRO DELLE CREATURE
# ============================================================================

CREATURE = {
    #  chiave      (nome collezione,              funzione,        camera: target, dist, elev, azim, lente)
    "mantide":   ("01_Mante-Luce",               build_mantis,    ((0, 0.3, 1.1), 7.2, 10, 16, 50)),
    "gatto":     ("02_Gattoluna",                build_cat,       ((0.12, 0.0, 0.85), 5.4, 12, 38, 50)),
    "gufo":      ("03_Gufo-Scintilla",           build_owl,       ((0, 0, 1.4), 5.2, 8, 22, 50)),
    "rana":      ("04_Ranabuio",                 build_frog,      ((0, 0.0, 0.45), 4.4, 18, 32, 50)),
    "farfalla":  ("05_Farfalla-Glow",            build_butterfly, ((0, 0.1, 0.9), 6.6, 52, 25, 50)),
    "libellula": ("06_Libellula-Fulmine",        build_dragonfly, ((0, 0.15, 0.9), 5.4, 30, 30, 50)),
    "lupo":      ("07_Lupo-Luce",                build_wolf,      ((0, -0.05, 0.85), 5.8, 10, 40, 50)),
    "falena":    ("08_La-Piccola-Lucina-Farfallina", build_moth,  ((0, -0.15, 0.82), 4.6, 10, 25, 50)),
}


# Disposizione nella scena "tutte": (x, y, rotazione_z_gradi)
DISPOSIZIONE = {
    "gufo":      (-5.5, 4.6, 10),
    "mantide":   (-2.0, 4.4, 0),
    "farfalla":  (1.7, 4.8, 0),
    "libellula": (5.4, 4.6, -30),
    "gatto":     (-3.8, 0.4, 20),
    "rana":      (-1.1, -0.2, 10),
    "falena":    (1.4, -0.1, -10),
    "lupo":      (4.3, 0.4, -25),
}


def build_one(key, offset=(0, 0, 0), parent_coll=None, rot_z=0.0, registry=None):
    title, fn, _cam = (registry or CREATURE)[key]
    coll = new_collection(title, parent_coll)
    set_collection(coll)
    random.seed(sum(ord(c) for c in key))
    del ANIMAZIONI[:]
    del VALORI_RIPOSO[:]
    _STATE["texspace"] = None
    fn()
    _STATE["texspace"] = None
    root = empty(title.split("_", 1)[1] + "_Radice", (0, 0, 0), 0.5)
    for ob in list(coll.objects):
        if ob is not root and ob.parent is None:
            ob.parent = root
    root.location = offset
    root.rotation_euler = (0, 0, radians(rot_z))
    set_collection(None)
    return root


def build(which=None, engine=None, clean=None):
    which = (which or CREATURA).lower()
    if clean if clean is not None else PULISCI_SCENA:
        clear_scene()
    setup_world()
    setup_render(engine)
    base = new_collection("Scena")
    set_collection(base)
    setup_ground()
    setup_moonlight()
    set_collection(None)
    if which == "tutte":
        for k in CREATURE:
            x, y, rz = DISPOSIZIONE[k]
            build_one(k, (x, y, 0), rot_z=rz)
        setup_camera((0.0, 2.3, 0.9), 14.5, 21, 0, 32)
    else:
        if which not in CREATURE:
            raise ValueError("Creatura sconosciuta: %s (scegli tra %s o 'tutte')"
                             % (which, ", ".join(CREATURE)))
        build_one(which)
        tgt, dist, el, az, lens = CREATURE[which][2]
        setup_camera(tgt, dist, el, az, lens)
    setup_viewport()
    bpy.context.scene.frame_set(1)


# ============================================================================
# AVVIO
# ============================================================================

def _cli_args():
    if "--" not in sys.argv:
        return None
    args = sys.argv[sys.argv.index("--") + 1:]
    opts = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opts[key] = args[i + 1]
                i += 2
            else:
                opts[key] = True
                i += 1
        else:
            i += 1
    return opts


def main():
    opts = _cli_args()
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
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = int(opts.get("campioni", 64))
        sc.cycles.use_denoising = True
        res = opts.get("risoluzione", "960x540").split("x")
        sc.render.resolution_x, sc.render.resolution_y = int(res[0]), int(res[1])
        sc.render.resolution_percentage = 100
        if opts.get("frame"):
            sc.frame_set(int(opts["frame"]))
        if opts.get("debug-luce"):
            bg = sc.world.node_tree.nodes.get('Background')
            bg.inputs['Color'].default_value = (0.6, 0.6, 0.65, 1.0)
            bg.inputs['Strength'].default_value = 1.0
        if opts.get("senza-bagliore"):
            if hasattr(sc, 'compositing_node_group'):
                sc.compositing_node_group = None
            else:
                sc.use_nodes = False
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("[creature] render:", path)


if __name__ == "__main__":
    main()
