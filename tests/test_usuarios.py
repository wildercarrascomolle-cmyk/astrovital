"""Gestión de usuarios: registro, inicio y cierre de sesión, roles."""


def test_registro_crea_astronauta_con_clave_cifrada(client, consulta):
    r = client.post("/registro", data={"nombre": "Wily Mori", "email": "wily@correo.com", "agencia": "CONIDA (Perú)",
                                       "especialidad": "Ingeniero de sistemas", "clave": "Orion2026", "confirmar": "Orion2026"})
    assert r.status_code == 302
    u = consulta("SELECT * FROM usuario WHERE email = 'wily@correo.com'")[0]
    assert u["rol"] == "ASTRONAUTA"
    assert u["password_hash"] != "Orion2026" and u["password_hash"].startswith(("scrypt:", "pbkdf2:"))
    assert consulta("SELECT * FROM astronauta WHERE usuario_id = ?", (u["id"],))


def test_registro_rechaza_datos_invalidos_y_duplicados(client):
    r = client.post("/registro", data={"nombre": "X", "email": "malo", "agencia": "Ninguna", "especialidad": "",
                                       "clave": "corta", "confirmar": "otra"})
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "correo electrónico válido" in html and "no coinciden" in html
    r = client.post("/registro", data={"nombre": "Otro Andrés", "email": "andres@astrovital.dev", "agencia": "Otra",
                                       "especialidad": "Piloto", "clave": "Clave2026", "confirmar": "Clave2026"})
    assert "Ya existe una cuenta" in r.get_data(as_text=True)


def test_login_correcto_e_incorrecto(client, sesion):
    assert sesion.entrar("andres@astrovital.dev", "mala").status_code == 401
    r = sesion.astronauta()
    assert r.status_code == 302 and r.headers["Location"].endswith("/panel/")
    assert "Andrés Quispe" in client.get("/panel/").get_data(as_text=True)


def test_logout_cierra_la_sesion(client, sesion):
    sesion.medico()
    assert client.get("/panel/").status_code == 200
    client.post("/logout")
    assert client.get("/panel/").status_code == 302


def test_sin_sesion_redirige_al_login(client):
    for ruta in ("/panel/", "/salud/", "/misiones/", "/astronautas/", "/usuarios/"):
        r = client.get(ruta)
        assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_control_de_acceso_por_rol(client, sesion):
    sesion.astronauta()
    assert client.get("/usuarios/").status_code == 403
    assert client.get("/astronautas/").status_code == 403
    assert client.get("/misiones/nueva").status_code == 403
    client.post("/logout")
    sesion.medico()
    assert client.get("/astronautas/").status_code == 200       # el médico consulta la tripulación
    assert client.get("/misiones/nueva").status_code == 403     # pero no crea misiones
    assert client.get("/usuarios/").status_code == 403


def test_admin_cambia_rol_y_desactiva_cuenta(client, sesion, consulta):
    sesion.admin()
    uid = consulta("SELECT id FROM usuario WHERE email = 'kenji@astrovital.dev'")[0]["id"]
    client.post(f"/usuarios/{uid}/rol", data={"rol": "MEDICO"})
    assert consulta("SELECT rol FROM usuario WHERE id = ?", (uid,))[0]["rol"] == "MEDICO"
    client.post(f"/usuarios/{uid}/estado")
    client.post("/logout")
    assert sesion.entrar("kenji@astrovital.dev", "Astro2026").status_code == 401   # cuenta desactivada


def test_csrf_obligatorio(app):
    app.config["WTF_CSRF"] = True
    r = app.test_client().post("/login", data={"email": "admin@astrovital.dev", "clave": "Admin2026"})
    assert r.status_code == 400
