"""
Reglas de evaluación de los indicadores de salud.

IMPORTANTE: los umbrales son valores de referencia para la DEMOSTRACIÓN del
prototipo. No son criterios clínicos validados; en una misión real los define
el equipo médico de vuelo.
"""

# indicador: (etiqueta, unidad, (min_normal, max_normal), (min_critico, max_critico))
UMBRALES = {
    "frecuencia_cardiaca": ("Frecuencia cardiaca", "lpm", (50, 95), (40, 120)),
    "presion_sistolica": ("Presión sistólica", "mmHg", (90, 135), (80, 160)),
    "presion_diastolica": ("Presión diastólica", "mmHg", (60, 88), (50, 100)),
    "spo2": ("Saturación de oxígeno", "%", (95, 100), (90, 100)),
    "temperatura": ("Temperatura", "°C", (36.0, 37.5), (35.0, 38.5)),
    "horas_sueno": ("Horas de sueño", "h", (6.0, 10.0), (4.0, 14.0)),
    "radiacion_msv": ("Dosis de radiación diaria", "mSv", (0.0, 1.0), (0.0, 2.0)),
    "animo": ("Estado de ánimo (1–5)", "", (3, 5), (2, 5)),
}

NIVELES = {"normal": 0, "atencion": 1, "critico": 2}


def evaluar_valor(indicador, valor):
    _, _, (n_min, n_max), (c_min, c_max) = UMBRALES[indicador]
    if valor < c_min or valor > c_max:
        return "critico"
    if valor < n_min or valor > n_max:
        return "atencion"
    return "normal"


def evaluar_registro(registro):
    """Devuelve (nivel_general, lista de alertas [(etiqueta, valor, unidad, nivel)])."""
    alertas = []
    for ind, (etiqueta, unidad, _, _) in UMBRALES.items():
        valor = registro[ind]
        nivel = evaluar_valor(ind, valor)
        if nivel != "normal":
            alertas.append((etiqueta, valor, unidad, nivel))
    nivel = max((a[3] for a in alertas), key=NIVELES.get, default="normal")
    return nivel, alertas
