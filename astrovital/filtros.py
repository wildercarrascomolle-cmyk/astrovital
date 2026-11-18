"""Filtros y utilidades para las plantillas."""
from datetime import datetime

from .salud_reglas import UMBRALES, evaluar_registro, evaluar_valor

ROLES = {"ADMIN": "Administrador", "MEDICO": "Médico de vuelo", "ASTRONAUTA": "Astronauta"}
NIVEL_TXT = {"normal": "Normal", "atencion": "Atención", "critico": "Crítico"}


def fecha(valor, con_hora=False):
    if not valor:
        return "—"
    v = str(valor)
    try:
        d = datetime.fromisoformat(v)
    except ValueError:
        return v
    return d.strftime("%d/%m/%Y %H:%M") if con_hora and len(v) > 10 else d.strftime("%d/%m/%Y")


def numero(v):
    if v is None:
        return "—"
    return f"{v:g}" if isinstance(v, float) else str(v)


def sparkline(valores, ancho=120, alto=32):
    """Mini gráfico SVG (polilínea) generado en el servidor."""
    if len(valores) < 2:
        return '<span class="sin-tendencia">Se necesitan al menos 2 registros</span>'
    lo, hi = min(valores), max(valores)
    rango = (hi - lo) or 1
    paso = ancho / max(len(valores) - 1, 1)
    pts = " ".join(f"{i * paso:.1f},{alto - 3 - (v - lo) / rango * (alto - 6):.1f}" for i, v in enumerate(valores))
    ult_x, ult_y = pts.split(" ")[-1].split(",")
    return (f'<svg class="spark" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>'
            f'<circle cx="{ult_x}" cy="{ult_y}" r="2.6" fill="currentColor"/></svg>')


def registrar(app):
    app.jinja_env.filters["fecha"] = fecha
    app.jinja_env.filters["numero"] = numero
    app.jinja_env.filters["rol"] = lambda r: ROLES.get(r, r)
    app.jinja_env.filters["nivel"] = lambda n: NIVEL_TXT.get(n, n)
    app.jinja_env.globals.update(evaluar_registro=evaluar_registro, evaluar_valor=evaluar_valor,
                                 UMBRALES=UMBRALES, sparkline=sparkline)
