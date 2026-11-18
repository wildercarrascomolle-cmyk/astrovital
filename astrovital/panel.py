"""Módulo de panel: resumen según el rol."""
from flask import Blueprint, g, render_template

from .auth import astronauta_actual, login_requerido
from .db import get_db
from .salud_reglas import evaluar_registro

bp = Blueprint("panel", __name__, url_prefix="/panel")


def estado_tripulacion(filtro_id=None):
    """Último registro y nivel de alerta de cada astronauta."""
    db = get_db()
    sql = ("SELECT a.*, m.nombre AS mision, m.destino FROM astronauta a LEFT JOIN mision m ON m.id = a.mision_id")
    params = []
    if filtro_id:
        sql += " WHERE a.id = ?"
        params.append(filtro_id)
    filas = []
    for a in db.execute(sql + " ORDER BY a.nombre", params):
        regs = db.execute("SELECT * FROM registro_salud WHERE astronauta_id = ? ORDER BY fecha_hora DESC LIMIT 14",
                          (a["id"],)).fetchall()
        ultimo = regs[0] if regs else None
        nivel, alertas = evaluar_registro(ultimo) if ultimo else ("normal", [])
        serie = list(reversed(regs))
        filas.append({"a": a, "ultimo": ultimo, "nivel": nivel, "alertas": alertas,
                      "serie_fc": [r["frecuencia_cardiaca"] for r in serie],
                      "serie_sueno": [r["horas_sueno"] for r in serie]})
    return filas


@bp.route("/")
@login_requerido
def inicio():
    db = get_db()
    if g.usuario["rol"] == "ASTRONAUTA":
        ficha = astronauta_actual()
        filas = estado_tripulacion(ficha["id"]) if ficha else []
    else:
        filas = estado_tripulacion()
    pendientes = db.execute("SELECT COUNT(*) FROM registro_salud WHERE revisado = 0").fetchone()[0]
    resumen = {
        "misiones": db.execute("SELECT COUNT(*) FROM mision WHERE estado = 'En curso'").fetchone()[0],
        "astronautas": db.execute("SELECT COUNT(*) FROM astronauta").fetchone()[0],
        "criticos": sum(1 for f in filas if f["nivel"] == "critico"),
        "atencion": sum(1 for f in filas if f["nivel"] == "atencion"),
        "pendientes": pendientes,
    }
    return render_template("panel.html", filas=filas, resumen=resumen)
