"""Acceso a SQLite, esquema y datos de demostración."""
import random
import sqlite3
from datetime import date, datetime, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('ADMIN', 'MEDICO', 'ASTRONAUTA')),
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mision (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo       TEXT NOT NULL UNIQUE,
    nombre       TEXT NOT NULL,
    destino      TEXT NOT NULL CHECK (destino IN ('Órbita baja', 'Luna', 'Marte', 'Espacio profundo')),
    fecha_inicio TEXT NOT NULL,
    fecha_fin    TEXT NOT NULL,
    estado       TEXT NOT NULL CHECK (estado IN ('Planificada', 'En curso', 'Finalizada')),
    descripcion  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS astronauta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER UNIQUE REFERENCES usuario(id) ON DELETE SET NULL,
    nombre       TEXT NOT NULL,
    agencia      TEXT NOT NULL,
    especialidad TEXT NOT NULL,
    mision_id    INTEGER REFERENCES mision(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS registro_salud (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    astronauta_id       INTEGER NOT NULL REFERENCES astronauta(id) ON DELETE CASCADE,
    fecha_hora          TEXT    NOT NULL,
    frecuencia_cardiaca INTEGER NOT NULL CHECK (frecuencia_cardiaca BETWEEN 25 AND 230),
    presion_sistolica   INTEGER NOT NULL CHECK (presion_sistolica BETWEEN 60 AND 250),
    presion_diastolica  INTEGER NOT NULL CHECK (presion_diastolica BETWEEN 30 AND 150),
    spo2                INTEGER NOT NULL CHECK (spo2 BETWEEN 50 AND 100),
    temperatura         REAL    NOT NULL CHECK (temperatura BETWEEN 32 AND 43),
    horas_sueno         REAL    NOT NULL CHECK (horas_sueno BETWEEN 0 AND 24),
    radiacion_msv       REAL    NOT NULL CHECK (radiacion_msv BETWEEN 0 AND 100),
    animo               INTEGER NOT NULL CHECK (animo BETWEEN 1 AND 5),
    sintomas            TEXT    NOT NULL DEFAULT '',
    nota_medica         TEXT    NOT NULL DEFAULT '',
    revisado            INTEGER NOT NULL DEFAULT 0,
    registrado_por      INTEGER REFERENCES usuario(id),
    creado_en           TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_registro_astronauta ON registro_salud(astronauta_id, fecha_hora);
"""


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    con = sqlite3.connect(app.config["DATABASE"], timeout=30, isolation_level=None)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    # BEGIN IMMEDIATE bloquea la base: si varios procesos arrancan a la vez
    # (p. ej. varios workers de gunicorn), solo uno carga los datos de ejemplo.
    con.execute("BEGIN IMMEDIATE")
    try:
        if con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0 and app.config.get("SEED_DEMO", True):
            sembrar(con)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


# ----------------------------------------------------------------------
# Datos de demostración (personas y misiones ficticias)
# ----------------------------------------------------------------------

USUARIOS_DEMO = [
    ("Administrador AstroVital", "admin@astrovital.dev", "Admin2026", "ADMIN"),
    ("Dra. Elena Paredes", "medico@astrovital.dev", "Medico2026", "MEDICO"),
    ("Andrés Quispe", "andres@astrovital.dev", "Astro2026", "ASTRONAUTA"),
    ("Lucía Fernández", "lucia@astrovital.dev", "Astro2026", "ASTRONAUTA"),
    ("Kenji Tanaka", "kenji@astrovital.dev", "Astro2026", "ASTRONAUTA"),
]


def sembrar(con):
    hoy = date.today()
    for nombre, email, clave, rol in USUARIOS_DEMO:
        con.execute("INSERT INTO usuario (nombre, email, password_hash, rol, creado_en) VALUES (?, ?, ?, ?, ?)",
                    (nombre, email, generate_password_hash(clave), rol, ahora()))
    misiones = [
        ("SEL-01", "Selene I", "Luna", hoy - timedelta(days=20), hoy + timedelta(days=25), "En curso",
         "Estancia de 45 días en una base lunar simulada cerca del polo sur."),
        ("LEO-26", "Estación Orbital 26", "Órbita baja", hoy - timedelta(days=60), hoy + timedelta(days=120), "En curso",
         "Expedición de seis meses en una estación en órbita baja."),
        ("ARE-T1", "Ares Tránsito 1", "Marte", hoy + timedelta(days=200), hoy + timedelta(days=900), "Planificada",
         "Tránsito de larga duración hacia Marte, en fase de planificación."),
    ]
    for c, n, d, i, f, e, desc in misiones:
        con.execute("INSERT INTO mision (codigo, nombre, destino, fecha_inicio, fecha_fin, estado, descripcion)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)", (c, n, d, i.isoformat(), f.isoformat(), e, desc))
    ids = {r[1]: r[0] for r in con.execute("SELECT id, email FROM usuario")}
    mis = {r[1]: r[0] for r in con.execute("SELECT id, codigo FROM mision")}
    tripulacion = [
        ("andres@astrovital.dev", "Andrés Quispe", "CONIDA (Perú)", "Ingeniero de vuelo", "SEL-01"),
        ("lucia@astrovital.dev", "Lucía Fernández", "AEE (España)", "Comandante", "SEL-01"),
        ("kenji@astrovital.dev", "Kenji Tanaka", "JAXA (Japón)", "Especialista de misión", "LEO-26"),
    ]
    for email, nombre, agencia, esp, mcod in tripulacion:
        con.execute("INSERT INTO astronauta (usuario_id, nombre, agencia, especialidad, mision_id) VALUES (?, ?, ?, ?, ?)",
                    (ids[email], nombre, agencia, esp, mis[mcod]))
    con.execute("INSERT INTO astronauta (nombre, agencia, especialidad, mision_id) VALUES (?, ?, ?, ?)",
                ("Amara Okafor", "NASA (EE. UU.)", "Médica de a bordo", mis["LEO-26"]))

    rnd = random.Random(2026)
    medico = ids["medico@astrovital.dev"]
    for aid, in con.execute("SELECT id FROM astronauta").fetchall():
        for d in range(13, -1, -1):
            dia = datetime.combine(hoy - timedelta(days=d), datetime.min.time()).replace(hour=7, minute=30)
            fc, sis, dia_p, spo2 = rnd.randint(58, 82), rnd.randint(108, 128), rnd.randint(68, 82), rnd.randint(96, 99)
            temp, sueno, rad = round(rnd.uniform(36.3, 37.0), 1), round(rnd.uniform(6.2, 8.0), 1), round(rnd.uniform(0.3, 0.7), 2)
            animo, sint = rnd.randint(3, 5), ""
            # Casos que deben generar alertas en la demostración
            if aid == 1 and d <= 2:
                sueno, fc, animo, sint = round(rnd.uniform(4.2, 5.0), 1), rnd.randint(96, 104), 2, "Cansancio y dificultad para concentrarse"
            if aid == 3 and d == 0:
                spo2, rad, sint = 89, 1.3, "Leve mareo tras actividad extravehicular"
            con.execute(
                "INSERT INTO registro_salud (astronauta_id, fecha_hora, frecuencia_cardiaca, presion_sistolica, presion_diastolica,"
                " spo2, temperatura, horas_sueno, radiacion_msv, animo, sintomas, revisado, nota_medica, registrado_por, creado_en)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, dia.strftime("%Y-%m-%d %H:%M"), fc, sis, dia_p, spo2, temp, sueno, rad, animo, sint,
                 1 if d > 2 else 0, "Valores dentro de lo esperado." if d > 2 else "", medico, ahora()))
