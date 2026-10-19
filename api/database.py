import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def connect(path: str | Path):
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
        if connection.in_transaction:
            connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: str | Path, seed_path: str | Path | None = None) -> None:
    source = Path(seed_path or os.getenv("DATABASE_SEED_PATH", PROJECT_ROOT / "material" / "datos_prueba.sql"))
    with connect(path) as db:
        existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"clientes", "productos", "solicitudes"}
        if not required.issubset(existing):
            if existing.intersection(required):
                raise RuntimeError("La base está incompleta; no se ejecuta una semilla destructiva sobre datos existentes")
            if not source.is_file():
                raise RuntimeError(f"No se encontró la semilla SQLite: {source}")
            db.executescript(source.read_text(encoding="utf-8"))

        request_columns = {row[1] for row in db.execute("PRAGMA table_info(solicitudes)")}
        additions = {
            "recepcion_id": "INTEGER REFERENCES recepciones(id)",
            "resumen": "TEXT",
            "requiere_revision": "INTEGER NOT NULL DEFAULT 0 CHECK (requiere_revision IN (0,1))",
            "motivos_revision_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        # Create the referenced table before adding its foreign key on a fresh database.
        db.execute("""CREATE TABLE IF NOT EXISTS recepciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT NOT NULL UNIQUE,
            payload_hash TEXT NOT NULL,
            cliente_email TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN ('recibida','procesando','registrada','revision_manual')),
            clasificacion_json TEXT,
            motivos_revision_json TEXT NOT NULL DEFAULT '[]',
            intentos_llm INTEGER NOT NULL DEFAULT 0 CHECK (intentos_llm BETWEEN 0 AND 2),
            ultimo_error TEXT,
            resultado_json TEXT,
            solicitud_id INTEGER UNIQUE REFERENCES solicitudes(id),
            fecha_creacion TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            fecha_actualizacion TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")
        for name, declaration in additions.items():
            if name not in request_columns:
                db.execute(f"ALTER TABLE solicitudes ADD COLUMN {name} {declaration}")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_solicitudes_recepcion_id ON solicitudes(recepcion_id) WHERE recepcion_id IS NOT NULL")
        db.execute("""CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitud_id INTEGER NOT NULL UNIQUE REFERENCES solicitudes(id),
            motivos_json TEXT NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN ('pendiente','enviando','enviada','fallida','incierta')),
            intentos INTEGER NOT NULL DEFAULT 0,
            ultimo_error TEXT,
            message_id TEXT,
            fecha_creacion TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            fecha_actualizacion TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS ix_solicitudes_estado_fecha ON solicitudes(estado, fecha_creacion, id)")
