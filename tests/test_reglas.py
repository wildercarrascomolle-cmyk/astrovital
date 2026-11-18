"""Reglas de evaluación de indicadores (sin servidor)."""
from astrovital.salud_reglas import evaluar_registro, evaluar_valor


def test_niveles_por_indicador():
    assert evaluar_valor("spo2", 98) == "normal"
    assert evaluar_valor("spo2", 92) == "atencion"
    assert evaluar_valor("spo2", 85) == "critico"
    assert evaluar_valor("horas_sueno", 5) == "atencion"
    assert evaluar_valor("radiacion_msv", 2.5) == "critico"


def test_nivel_general_es_el_peor_indicador():
    registro = {"frecuencia_cardiaca": 70, "presion_sistolica": 118, "presion_diastolica": 76, "spo2": 97,
                "temperatura": 36.6, "horas_sueno": 5.0, "radiacion_msv": 2.4, "animo": 4}
    nivel, alertas = evaluar_registro(registro)
    assert nivel == "critico"
    assert {a[0] for a in alertas} == {"Horas de sueño", "Dosis de radiación diaria"}


def test_registro_normal_sin_alertas():
    registro = {"frecuencia_cardiaca": 64, "presion_sistolica": 115, "presion_diastolica": 74, "spo2": 98,
                "temperatura": 36.5, "horas_sueno": 7.5, "radiacion_msv": 0.4, "animo": 4}
    assert evaluar_registro(registro) == ("normal", [])
