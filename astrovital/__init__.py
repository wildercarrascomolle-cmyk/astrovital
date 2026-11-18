"""AstroVital · Monitoreo de salud de astronautas (Flask + SQLite)."""
import os
import secrets

from flask import Flask, abort, render_template, request, session

from . import db


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE_PATH") or os.path.join(app.instance_path, "astrovital.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SEED_DEMO=True,
        WTF_CSRF=True,
    )
    if config:
        app.config.update(config)

    app.teardown_appcontext(db.close_db)

    # --- CSRF sencillo para todos los formularios ---
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_urlsafe(32)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def verificar_csrf():
        if request.method == "POST" and app.config.get("WTF_CSRF", True):
            token = request.form.get("_csrf", "")
            if not token or not secrets.compare_digest(token, session.get("_csrf", "")):
                abort(400)

    @app.after_request
    def cabeceras(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    from .auth import bp as auth_bp, cargar_usuario
    from .panel import bp as panel_bp
    from .misiones import bp as misiones_bp
    from .astronautas import bp as astronautas_bp
    from .salud import bp as salud_bp
    from .usuarios import bp as usuarios_bp
    from . import filtros

    app.before_request(cargar_usuario)
    for bp in (auth_bp, panel_bp, misiones_bp, astronautas_bp, salud_bp, usuarios_bp):
        app.register_blueprint(bp)
    filtros.registrar(app)

    @app.errorhandler(400)
    def e400(_):
        return render_template("error.html", codigo=400, titulo="Solicitud no válida",
                               detalle="El formulario expiró o tiene datos no válidos."), 400

    @app.errorhandler(403)
    def e403(_):
        return render_template("error.html", codigo=403, titulo="Acceso denegado",
                               detalle="Su rol no tiene permiso para esta sección."), 403

    @app.errorhandler(404)
    def e404(_):
        return render_template("error.html", codigo=404, titulo="Página no encontrada",
                               detalle="La dirección no existe en AstroVital."), 404

    db.init_db(app)
    return app
