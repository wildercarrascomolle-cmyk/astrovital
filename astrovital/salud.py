"""Módulo de salud: CRUD de registros de indicadores y revisión médica."""
from datetime import datetime

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import astronauta_actual, login_requerido, roles_permitidos
from .db import ahora, get_db
from .salud_reglas import UMBRALES, evaluar_registro

bp = Blueprint("salud", __name__, url_prefix="/salud")

# campo: (tipo, mínimo físico aceptado, máximo físico aceptado)
CAMPOS = {
    "frecuencia_cardiaca": (int, 25, 230),
    "presion_sistolica": (int, 60, 250),
    "presion_diastolica": (int, 30, 150),
    "spo2": (int, 50, 100),
    "temperatura": (float, 32, 43),
    "horas_sueno": (float, 0, 24),
    "radiacion_msv": (float, 0, 100),
    "animo": (int, 1, 5),
}


def validar(form):
    datos, errores = {}, []
    for campo, (tipo, lo, hi) in CAMPOS.items():
        etiqueta = UMBRALES[campo][0]
        txt = form.get(campo, "").strip().replace(",", ".")
        try:
            valor = tipo(float(txt)) if tipo is int else round(float(txt), 2)
        except ValueError:
            errores.append(f"{etiqueta}: ingrese un número.")
            continue
        if not lo <= valor <= hi:
            errores.append(f"{etiqueta}: el valor debe estar entre {lo} y {hi}.")
        datos[campo] = valor
    if not errores and datos["presion_diastolica"] >= datos["presion_sistolica"]:
        errores.append("La presión diastólica debe ser menor que la sistólica.")
    fh = form.get("fecha_hora", "").strip()
    try:
        d = datetime.fromisoformat(fh)
        if d > datetime.now():
            errores.append("La fecha y hora no puede ser futura.")
        datos["fecha_hora"] = d.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        errores.append("Ingrese una fecha y hora válidas.")
        datos["fecha_hora"] = fh
    datos["sintomas"] = " ".join(form.get("sintomas", "").split())[:300]
    return datos, errores


def obtener(rid):
    r = get_db().execute(
        "SELECT r.*, a.nombre AS astronauta, a.usuario_id FROM registro_salud r"
        " JOIN astronauta a ON a.id = r.astronauta_id WHERE r.id = ?", (rid,)).fetchone()
    if r is None:
        abort(404)
    # Un astronauta solo puede ver sus propios registros
    if g.usuario["rol"] == "ASTRONAUTA" and r["usuario_id"] != g.usuario["id"]:
        abort(403)
    return r


def puede_modificar(r):
    if g.usuario["rol"] in ("MEDICO", "ADMIN"):
        return True
    return r["usuario_id"] == g.usuario["id"] and not r["revisado"]


@bp.route("/")
@login_requerido
def lista():
    db = get_db()
    sql = ("SELECT r.*, a.nombre AS astronauta FROM registro_salud r JOIN astronauta a ON a.id = r.astronauta_id WHERE 1 = 1")
    params = []
    astronautas = []
    if g.usuario["rol"] == "ASTRONAUTA":
        ficha = astronauta_actual()
        sql += " AND a.id = ?"
        params.append(ficha["id"] if ficha else -1)
    else:
        astronautas = db.execute("SELECT id, nombre FROM astronauta ORDER BY nombre").fetchall()
        aid = request.args.get("astronauta", "")
        if aid.isdigit():
            sql += " AND a.id = ?"
            params.append(int(aid))
        if request.args.get("pendientes") == "1":
            sql += " AND r.revisado = 0"
    registros = db.execute(sql + " ORDER BY r.fecha_hora DESC LIMIT 200", params).fetchall()
    nivel_f = request.args.get("nivel", "")
    filas = []
    for r in registros:
        nivel, alertas = evaluar_registro(r)
        if nivel_f and nivel != nivel_f:
            continue
        filas.append({"r": r, "nivel": nivel, "alertas": alertas})
    return render_template("salud/lista.html", filas=filas, astronautas=astronautas, args=request.args)


@bp.route("/nuevo", methods=["GET", "POST"])
@login_requerido
def nuevo():
    db = get_db()
    es_astro = g.usuario["rol"] == "ASTRONAUTA"
    ficha = astronauta_actual() if es_astro else None
    if es_astro and ficha is None:
        abort(403)
    astronautas = [] if es_astro else db.execute("SELECT id, nombre FROM astronauta ORDER BY nombre").fetchall()
    datos, errores = {"fecha_hora": datetime.now().strftime("%Y-%m-%dT%H:%M")}, []
    if request.method == "POST":
        datos, errores = validar(request.form)
        if es_astro:
            aid = ficha["id"]
        else:
            aid = request.form.get("astronauta_id", "")
            if not aid.isdigit() or not db.execute("SELECT 1 FROM astronauta WHERE id = ?", (int(aid),)).fetchone():
                errores.append("Seleccione un astronauta.")
            datos["astronauta_id"] = aid
        if not errores:
            rid = db.execute(
                "INSERT INTO registro_salud (astronauta_id, fecha_hora, frecuencia_cardiaca, presion_sistolica,"
                " presion_diastolica, spo2, temperatura, horas_sueno, radiacion_msv, animo, sintomas, registrado_por, creado_en)"
                " VALUES (:aid, :fecha_hora, :frecuencia_cardiaca, :presion_sistolica, :presion_diastolica, :spo2,"
                " :temperatura, :horas_sueno, :radiacion_msv, :animo, :sintomas, :uid, :creado)",
                {**datos, "aid": int(aid), "uid": g.usuario["id"], "creado": ahora()}).lastrowid
            db.commit()
            nivel, alertas = evaluar_registro(db.execute("SELECT * FROM registro_salud WHERE id = ?", (rid,)).fetchone())
            if nivel == "normal":
                flash("Registro guardado. Todos los indicadores están en rango normal.", "exito")
            else:
                flash(f"Registro guardado con {len(alertas)} alerta(s). El equipo médico lo revisará.", "alerta")
            return redirect(url_for("salud.detalle", rid=rid))
    return render_template("salud/form.html", datos=datos, errores=errores, astronautas=astronautas,
                           ficha=ficha, registro=None), (400 if errores else 200)


@bp.route("/<int:rid>")
@login_requerido
def detalle(rid):
    r = obtener(rid)
    nivel, alertas = evaluar_registro(r)
    historial = get_db().execute("SELECT * FROM registro_salud WHERE astronauta_id = ? ORDER BY fecha_hora DESC LIMIT 14",
                                 (r["astronauta_id"],)).fetchall()
    return render_template("salud/detalle.html", r=r, nivel=nivel, alertas=alertas,
                           historial=list(reversed(historial)), puede_modificar=puede_modificar(r))


@bp.route("/<int:rid>/editar", methods=["GET", "POST"])
@login_requerido
def editar(rid):
    r = obtener(rid)
    if not puede_modificar(r):
        abort(403)
    datos = dict(r)
    datos["fecha_hora"] = r["fecha_hora"].replace(" ", "T")
    errores = []
    if request.method == "POST":
        datos, errores = validar(request.form)
        if not errores:
            db = get_db()
            db.execute("UPDATE registro_salud SET fecha_hora = :fecha_hora, frecuencia_cardiaca = :frecuencia_cardiaca,"
                       " presion_sistolica = :presion_sistolica, presion_diastolica = :presion_diastolica, spo2 = :spo2,"
                       " temperatura = :temperatura, horas_sueno = :horas_sueno, radiacion_msv = :radiacion_msv,"
                       " animo = :animo, sintomas = :sintomas WHERE id = :id", {**datos, "id": rid})
            db.commit()
            flash("Registro actualizado.", "exito")
            return redirect(url_for("salud.detalle", rid=rid))
    return render_template("salud/form.html", datos=datos, errores=errores, astronautas=[],
                           ficha=None, registro=r), (400 if errores else 200)


@bp.route("/<int:rid>/revisar", methods=["POST"])
@roles_permitidos("MEDICO")
def revisar(rid):
    obtener(rid)
    nota = " ".join(request.form.get("nota_medica", "").split())[:500]
    if len(nota) < 5:
        flash("Escriba una nota médica de al menos 5 caracteres.", "error")
        return redirect(url_for("salud.detalle", rid=rid))
    db = get_db()
    db.execute("UPDATE registro_salud SET nota_medica = ?, revisado = 1 WHERE id = ?", (nota, rid))
    db.commit()
    flash("Revisión médica registrada.", "exito")
    return redirect(url_for("salud.detalle", rid=rid))


@bp.route("/<int:rid>/eliminar", methods=["POST"])
@login_requerido
def eliminar(rid):
    r = obtener(rid)
    if not puede_modificar(r):
        abort(403)
    db = get_db()
    db.execute("DELETE FROM registro_salud WHERE id = ?", (rid,))
    db.commit()
    flash("Registro eliminado.", "info")
    return redirect(url_for("salud.lista"))
