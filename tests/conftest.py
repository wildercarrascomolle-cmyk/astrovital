import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astrovital import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """Aplicación con una base SQLite temporal y los datos de demostración."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "WTF_CSRF": False,
                       "SECRET_KEY": "pruebas"})


@pytest.fixture
def client(app):
    return app.test_client()


class Sesion:
    def __init__(self, client):
        self.client = client

    def entrar(self, email, clave):
        return self.client.post("/login", data={"email": email, "clave": clave})

    def admin(self):
        return self.entrar("admin@astrovital.dev", "Admin2026")

    def medico(self):
        return self.entrar("medico@astrovital.dev", "Medico2026")

    def astronauta(self, email="andres@astrovital.dev"):
        return self.entrar(email, "Astro2026")


@pytest.fixture
def sesion(client):
    return Sesion(client)


@pytest.fixture
def consulta(app):
    """Ejecuta una consulta directa a la base de datos de la prueba."""
    import sqlite3

    def _q(sql, params=()):
        con = sqlite3.connect(app.config["DATABASE"])
        con.row_factory = sqlite3.Row
        filas = con.execute(sql, params).fetchall()
        con.close()
        return filas
    return _q
