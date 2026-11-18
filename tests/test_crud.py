"""Operaciones CRUD de misiones, tripulación y registros de salud."""
from datetime import datetime, timedelta

AHORA = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M")
NORMAL = {"fecha_hora": AHORA, "frecuencia_cardiaca": "68", "presion_sistolica": "118", "presion_diastolica": "76",
          "spo2": "98", "temperatura": "36.6", "horas_sueno": "7.5", "radiacion_msv": "0.4", "animo": "4", "sintomas": ""}


# ---------------- Misiones ----------------

def test_crud_mision(client, sesion, consulta):
    sesion.admin()
    nueva = {"codigo": "art-q2", "nombre": "Gateway Q2", "destino": "Luna", "fecha_inicio": "2027-01-10",
             "fecha_fin": "2027-03-10", "estado": "Planificada", "descripcion": "Misión de prueba"}
    assert client.post("/misiones/nueva", data=nueva).status_code == 302                     # Create
    m = consulta("SELECT * FROM mision WHERE codigo = 'ART-Q2'")[0]
    assert "Gateway Q2" in client.get("/misiones/").get_data(as_text=True)                   # Read
    client.post(f"/misiones/{m['id']}/editar", data={**nueva, "estado": "En curso"})          # Update
    assert consulta("SELECT estado FROM mision WHERE id = ?", (m["id"],))[0]["estado"] == "En curso"
    client.post(f"/misiones/{m['id']}/eliminar")                                              # Delete
    assert not consulta("SELECT 1 FROM mision WHERE id = ?", (m["id"],))


def test_mision_valida_fechas_y_codigo_duplicado(client, sesion):
    sesion.admin()
    base = {"codigo": "SEL-01", "nombre": "Duplicada", "destino": "Luna", "fecha_inicio": "2027-05-01",
            "fecha_fin": "2027-04-01", "estado": "Planificada"}
    html = client.post("/misiones/nueva", data=base).get_data(as_text=True)
    assert "no puede ser anterior" in html and "Ya existe" not in html
    html = client.post("/misiones/nueva", data={**base, "fecha_fin": "2027-06-01"}).get_data(as_text=True)
    assert "Ya existe una misión con ese código" in html


# ---------------- Tripulación ----------------

def test_crud_astronauta(client, sesion, consulta):
    sesion.admin()
    client.post("/astronautas/nuevo", data={"nombre": "Sofía Rojas", "agencia": "CSA (Canadá)",
                                            "especialidad": "Geóloga", "mision_id": "1"})
    a = consulta("SELECT * FROM astronauta WHERE nombre = 'Sofía Rojas'")[0]
    assert a["mision_id"] == 1
    client.post(f"/astronautas/{a['id']}/editar", data={"nombre": "Sofía Rojas", "agencia": "CSA (Canadá)",
                                                        "especialidad": "Geóloga planetaria", "mision_id": ""})
    a = consulta("SELECT * FROM astronauta WHERE id = ?", (a["id"],))[0]
    assert a["especialidad"] == "Geóloga planetaria" and a["mision_id"] is None
    client.post(f"/astronautas/{a['id']}/eliminar")
    assert not consulta("SELECT 1 FROM astronauta WHERE id = ?", (a["id"],))


# ---------------- Registros de salud ----------------

def test_astronauta_registra_y_edita_su_indicador(client, sesion, consulta):
    sesion.astronauta()
    r = client.post("/salud/nuevo", data=NORMAL)
    assert r.status_code == 302
    rid = int(r.headers["Location"].rstrip("/").split("/")[-1])
    fila = consulta("SELECT r.*, a.nombre FROM registro_salud r JOIN astronauta a ON a.id = r.astronauta_id WHERE r.id = ?", (rid,))[0]
    assert fila["nombre"] == "Andrés Quispe" and fila["frecuencia_cardiaca"] == 68
    client.post(f"/salud/{rid}/editar", data={**NORMAL, "horas_sueno": "6"})
    assert consulta("SELECT horas_sueno FROM registro_salud WHERE id = ?", (rid,))[0]["horas_sueno"] == 6
    client.post(f"/salud/{rid}/eliminar")
    assert not consulta("SELECT 1 FROM registro_salud WHERE id = ?", (rid,))


def test_registro_con_valores_criticos_genera_alerta(client, sesion):
    sesion.astronauta()
    r = client.post("/salud/nuevo", data={**NORMAL, "spo2": "88", "frecuencia_cardiaca": "125"}, follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "alerta(s)" in html and "Crítico" in html


def test_validacion_de_rangos_fisicos(client, sesion):
    sesion.astronauta()
    r = client.post("/salud/nuevo", data={**NORMAL, "spo2": "130", "temperatura": "abc", "presion_diastolica": "140"})
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "Saturación de oxígeno: el valor debe estar entre 50 y 100" in html
    assert "Temperatura: ingrese un número" in html


def test_astronauta_no_ve_registros_de_otro(client, sesion, consulta):
    ajeno = consulta("SELECT r.id FROM registro_salud r JOIN astronauta a ON a.id = r.astronauta_id"
                     " WHERE a.nombre = 'Kenji Tanaka' LIMIT 1")[0]["id"]
    sesion.astronauta()
    assert client.get(f"/salud/{ajeno}").status_code == 403
    assert "Kenji" not in client.get("/salud/").get_data(as_text=True)


def test_medico_revisa_y_el_astronauta_ya_no_puede_editar(client, sesion, consulta):
    sesion.astronauta()
    rid = int(client.post("/salud/nuevo", data=NORMAL).headers["Location"].rstrip("/").split("/")[-1])
    client.post("/logout")
    sesion.medico()
    client.post(f"/salud/{rid}/revisar", data={"nota_medica": "Valores normales, continuar rutina."})
    assert consulta("SELECT revisado FROM registro_salud WHERE id = ?", (rid,))[0]["revisado"] == 1
    client.post("/logout")
    sesion.astronauta()
    assert client.get(f"/salud/{rid}/editar").status_code == 403


def test_solo_el_medico_registra_revisiones(client, sesion):
    sesion.astronauta()
    assert client.post("/salud/1/revisar", data={"nota_medica": "Me autorrevisé"}).status_code == 403
