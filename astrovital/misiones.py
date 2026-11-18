"""Módulo de misiones: CRUD completo (solo ADMIN crea, edita y elimina)."""
import re
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .auth import login_requerido, roles_permitidos
from .db import get_db

bp = Blueprint("misiones", __name__, url_prefix="/misiones")
DESTINOS = ["Órbita baja", "Luna", "Marte", "Espacio profundo"]
ESTADOS = ["Planificada", "En curso", "Finalizada"]


def validar(form):
    f = {k: " ".join(form.get(k, "").split()) for k in
         ("codigo", "nombre", "destino", "fecha_inicio", "fecha_fin", "estado", "descripcion")}
    f["codigo"] = f["codigo"].upper()[:10]
    errores = []
    if not re.fullmatch(r"[A-Z0-9-]{3,10}", f["codigo"]):
        errores.append("El código debe tener de 3 a 10 letras, números o guiones.")
    if len(f["nombre"]) < 3:
        errores.append("El nombre es obligatorio.")
    if f["destino"] not in DESTINOS:
        errores.append("Seleccione un destino válido.")
    if f["estado"] not in ESTADOS:
        errores.append("Seleccione un estado válido.")
    try:
        if date.fromisoformat(f["fecha_fin"]) < date.fromisoformat(f["fecha_inicio"]):
            errores.append("La fecha de fin no puede ser anterior a la de inicio.")
    except ValueError:
        errores.append("Ingrese fechas válidas.")
    f["descripcion"] = f["descripcion"][:500]
    return f, errores


@bp.route("/")
@login_requerido
def lista():
    misiones = get_db().execute(
        "SELECT m.*, (SELECT COUNT(*) FROM astronauta a WHERE a.mision_id = m.id) AS tripulantes"
        " FROM mision m ORDER BY m.fecha_inicio").fetchall()
    return render_template("misiones/lista.html", misiones=misiones)


@bp.route("/nueva", methods=["GET", "POST"])
@roles_permitidos("ADMIN")
def nueva():
    datos, errores = {}, []
    if request.method == "POST":
        datos, errores = validar(request.form)
        db = get_db()
        if not errores and db.execute("SELECT 1 FROM mision WHERE codigo = ?", (datos["codigo"],)).fetchone():
            errores.append("Ya existe una misión con ese código.")
        if not errores:
            db.execute("INSERT INTO mision (codigo, nombre, destino, fecha_inicio, fecha_fin, estado, descripcion)"
                       " VALUES (:codigo, :nombre, :destino, :fecha_inicio, :fecha_fin, :estado, :descripcion)", datos)
            db.commit()
            flash(f"Misión {datos['codigo']} creada.", "exito")
            return redirect(url_for("misiones.lista"))
    return render_template("misiones/form.html", datos=datos, errores=errores, destinos=DESTINOS,
                           estados=ESTADOS, mision=None), (400 if errores else 200)


@bp.route("/<int:mid>/editar", methods=["GET", "POST"])
@roles_permitidos("ADMIN")
def editar(mid):
    db = get_db()
    mision = db.execute("SELECT * FROM mision WHERE id = ?", (mid,)).fetchone()
    if mision is None:
        abort(404)
    datos, errores = dict(mision), []
    if request.method == "POST":
        datos, errores = validar(request.form)
        if not errores and db.execute("SELECT 1 FROM mision WHERE codigo = ? AND id <> ?", (datos["codigo"], mid)).fetchone():
            errores.append("Ya existe otra misión con ese código.")
        if not errores:
            db.execute("UPDATE mision SET codigo = :codigo, nombre = :nombre, destino = :destino, fecha_inicio = :fecha_inicio,"
                       " fecha_fin = :fecha_fin, estado = :estado, descripcion = :descripcion WHERE id = :id",
                       {**datos, "id": mid})
            db.commit()
            flash(f"Misión {datos['codigo']} actualizada.", "exito")
            return redirect(url_for("misiones.lista"))
    return render_template("misiones/form.html", datos=datos, errores=errores, destinos=DESTINOS,
                           estados=ESTADOS, mision=mision), (400 if errores else 200)


@bp.route("/<int:mid>/eliminar", methods=["POST"])
@roles_permitidos("ADMIN")
def eliminar(mid):
    db = get_db()
    mision = db.execute("SELECT * FROM mision WHERE id = ?", (mid,)).fetchone()
    if mision is None:
        abort(404)
    db.execute("DELETE FROM mision WHERE id = ?", (mid,))
    db.commit()
    flash(f"Misión {mision['codigo']} eliminada. Sus tripulantes quedaron sin misión asignada.", "info")
    return redirect(url_for("misiones.lista"))
