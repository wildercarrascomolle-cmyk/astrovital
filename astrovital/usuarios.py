"""Módulo de administración de usuarios y roles (solo ADMIN)."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import roles_permitidos
from .db import get_db

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")
ROLES = ("ADMIN", "MEDICO", "ASTRONAUTA")


@bp.route("/")
@roles_permitidos("ADMIN")
def lista():
    usuarios = get_db().execute(
        "SELECT u.*, a.nombre AS ficha FROM usuario u LEFT JOIN astronauta a ON a.usuario_id = u.id ORDER BY u.rol, u.nombre"
    ).fetchall()
    return render_template("usuarios/lista.html", usuarios=usuarios, roles=ROLES)


@bp.route("/<int:uid>/rol", methods=["POST"])
@roles_permitidos("ADMIN")
def cambiar_rol(uid):
    if uid == g.usuario["id"]:
        abort(400)
    rol = request.form.get("rol", "")
    if rol not in ROLES:
        abort(400)
    db = get_db()
    u = db.execute("SELECT * FROM usuario WHERE id = ?", (uid,)).fetchone()
    if u is None:
        abort(404)
    db.execute("UPDATE usuario SET rol = ? WHERE id = ?", (rol, uid))
    db.commit()
    flash(f"{u['nombre']} ahora tiene el rol {rol}.", "exito")
    return redirect(url_for("usuarios.lista"))


@bp.route("/<int:uid>/estado", methods=["POST"])
@roles_permitidos("ADMIN")
def cambiar_estado(uid):
    if uid == g.usuario["id"]:
        abort(400)
    db = get_db()
    u = db.execute("SELECT * FROM usuario WHERE id = ?", (uid,)).fetchone()
    if u is None:
        abort(404)
    db.execute("UPDATE usuario SET activo = ? WHERE id = ?", (0 if u["activo"] else 1, uid))
    db.commit()
    flash(f"Cuenta de {u['nombre']} {'desactivada' if u['activo'] else 'activada'}.", "info")
    return redirect(url_for("usuarios.lista"))
