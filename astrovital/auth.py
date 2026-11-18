"""Módulo de usuarios: registro, inicio y cierre de sesión, y control de acceso por rol."""
import re
from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import ahora, get_db

bp = Blueprint("auth", __name__)

RE_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,120}\.[A-Za-z]{2,10}$")
AGENCIAS = ["CONIDA (Perú)", "NASA (EE. UU.)", "ESA (Europa)", "AEE (España)", "JAXA (Japón)",
            "CSA (Canadá)", "ISRO (India)", "Otra"]


def cargar_usuario():
    g.usuario = None
    uid = session.get("usuario_id")
    if uid:
        g.usuario = get_db().execute("SELECT * FROM usuario WHERE id = ? AND activo = 1", (uid,)).fetchone()
        if g.usuario is None:
            session.clear()


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            flash("Inicie sesión para continuar.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)
    return envoltura


def roles_permitidos(*roles):
    """Decorador de control de acceso: otro rol recibe HTTP 403."""
    def decorador(vista):
        @wraps(vista)
        @login_requerido
        def envoltura(*args, **kwargs):
            if g.usuario["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def astronauta_actual():
    """Ficha de astronauta vinculada al usuario en sesión (o None)."""
    return get_db().execute("SELECT * FROM astronauta WHERE usuario_id = ?", (g.usuario["id"],)).fetchone()


def validar_clave(clave):
    errores = []
    if len(clave) < 8:
        errores.append("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
        errores.append("La contraseña debe combinar letras y números.")
    return errores


@bp.route("/")
def inicio():
    return redirect(url_for("panel.inicio") if g.usuario else url_for("auth.login"))


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Registro público: crea una cuenta de ASTRONAUTA con su ficha de tripulante."""
    if request.method == "GET":
        return render_template("auth/registro.html", datos={}, errores=[], agencias=AGENCIAS)
    f = {k: " ".join(request.form.get(k, "").split())[:120] for k in ("nombre", "email", "agencia", "especialidad")}
    f["email"] = f["email"].lower()
    clave, confirmar = request.form.get("clave", ""), request.form.get("confirmar", "")
    errores = []
    if len(f["nombre"]) < 3:
        errores.append("Ingrese su nombre completo.")
    if not RE_EMAIL.match(f["email"]):
        errores.append("Ingrese un correo electrónico válido.")
    if f["agencia"] not in AGENCIAS:
        errores.append("Seleccione una agencia.")
    if len(f["especialidad"]) < 3:
        errores.append("Indique su especialidad.")
    errores += validar_clave(clave)
    if clave != confirmar:
        errores.append("Las contraseñas no coinciden.")
    db = get_db()
    if not errores and db.execute("SELECT 1 FROM usuario WHERE email = ?", (f["email"],)).fetchone():
        errores.append("Ya existe una cuenta con ese correo.")
    if errores:
        return render_template("auth/registro.html", datos=f, errores=errores, agencias=AGENCIAS), 400
    uid = db.execute("INSERT INTO usuario (nombre, email, password_hash, rol, creado_en) VALUES (?, ?, ?, 'ASTRONAUTA', ?)",
                     (f["nombre"], f["email"], generate_password_hash(clave), ahora())).lastrowid
    db.execute("INSERT INTO astronauta (usuario_id, nombre, agencia, especialidad) VALUES (?, ?, ?, ?)",
               (uid, f["nombre"], f["agencia"], f["especialidad"]))
    db.commit()
    flash("Cuenta creada. Ya puede iniciar sesión.", "exito")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html", email="")
    email = request.form.get("email", "").strip().lower()
    clave = request.form.get("clave", "")
    u = get_db().execute("SELECT * FROM usuario WHERE email = ? AND activo = 1", (email,)).fetchone()
    if u is None or not check_password_hash(u["password_hash"], clave):
        flash("Correo o contraseña incorrectos.", "error")
        return render_template("auth/login.html", email=email), 401
    session.clear()
    session["usuario_id"] = u["id"]
    session["rol"] = u["rol"]
    flash(f"Bienvenido(a), {u['nombre']}.", "exito")
    destino = request.args.get("next", "")
    return redirect(destino if destino.startswith("/") and not destino.startswith("//") else url_for("panel.inicio"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
