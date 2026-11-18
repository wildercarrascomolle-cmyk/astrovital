"""Módulo de tripulación: CRUD de astronautas (ADMIN gestiona; MEDICO consulta)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .auth import AGENCIAS, roles_permitidos
from .db import get_db

bp = Blueprint("astronautas", __name__, url_prefix="/astronautas")


def validar(form, db):
    f = {k: " ".join(form.get(k, "").split())[:120] for k in ("nombre", "agencia", "especialidad", "mision_id")}
    errores = []
    if len(f["nombre"]) < 3:
        errores.append("El nombre es obligatorio.")
    if f["agencia"] not in AGENCIAS:
        errores.append("Seleccione una agencia.")
    if len(f["especialidad"]) < 3:
        errores.append("Indique la especialidad.")
    if f["mision_id"]:
        if not f["mision_id"].isdigit() or not db.execute("SELECT 1 FROM mision WHERE id = ?", (int(f["mision_id"]),)).fetchone():
            errores.append("La misión seleccionada no existe.")
        else:
            f["mision_id"] = int(f["mision_id"])
    else:
        f["mision_id"] = None
    return f, errores


@bp.route("/")
@roles_permitidos("ADMIN", "MEDICO")
def lista():
    filas = get_db().execute(
        "SELECT a.*, m.codigo AS mision_codigo, m.nombre AS mision, u.email,"
        " (SELECT COUNT(*) FROM registro_salud r WHERE r.astronauta_id = a.id) AS registros"
        " FROM astronauta a LEFT JOIN mision m ON m.id = a.mision_id LEFT JOIN usuario u ON u.id = a.usuario_id"
        " ORDER BY a.nombre").fetchall()
    return render_template("astronautas/lista.html", filas=filas)


@bp.route("/nuevo", methods=["GET", "POST"])
@bp.route("/<int:aid>/editar", methods=["GET", "POST"])
@roles_permitidos("ADMIN")
def editar(aid=None):
    db = get_db()
    actual = None
    if aid:
        actual = db.execute("SELECT * FROM astronauta WHERE id = ?", (aid,)).fetchone()
        if actual is None:
            abort(404)
    datos, errores = (dict(actual) if actual else {}), []
    if request.method == "POST":
        datos, errores = validar(request.form, db)
        if not errores:
            if actual:
                db.execute("UPDATE astronauta SET nombre = :nombre, agencia = :agencia, especialidad = :especialidad,"
                           " mision_id = :mision_id WHERE id = :id", {**datos, "id": aid})
                flash(f"Datos de {datos['nombre']} actualizados.", "exito")
            else:
                db.execute("INSERT INTO astronauta (nombre, agencia, especialidad, mision_id)"
                           " VALUES (:nombre, :agencia, :especialidad, :mision_id)", datos)
                flash(f"Astronauta {datos['nombre']} agregado a la tripulación.", "exito")
            db.commit()
            return redirect(url_for("astronautas.lista"))
    misiones = db.execute("SELECT id, codigo, nombre FROM mision ORDER BY fecha_inicio").fetchall()
    return render_template("astronautas/form.html", datos=datos, errores=errores, actual=actual,
                           agencias=AGENCIAS, misiones=misiones), (400 if errores else 200)


@bp.route("/<int:aid>/eliminar", methods=["POST"])
@roles_permitidos("ADMIN")
def eliminar(aid):
    db = get_db()
    a = db.execute("SELECT * FROM astronauta WHERE id = ?", (aid,)).fetchone()
    if a is None:
        abort(404)
    db.execute("DELETE FROM astronauta WHERE id = ?", (aid,))
    db.commit()
    flash(f"Astronauta {a['nombre']} y sus registros de salud eliminados.", "info")
    return redirect(url_for("astronautas.lista"))
