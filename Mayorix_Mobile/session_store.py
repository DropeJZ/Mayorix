"""
Almacenamiento local de la sesión móvil de Mayorix.

Guarda únicamente un token aleatorio y el perfil público del vendedor.
Nunca guarda la contraseña. El archivo vive en el almacenamiento privado de
la aplicación (FLET_APP_STORAGE_DATA), con permisos restringidos.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

SESSION_FILE = "session.json"


def _directorio() -> Path:
    base = os.getenv("FLET_APP_STORAGE_DATA", "").strip()
    if base:
        return Path(base)
    return Path.home() / ".mayorix_vendedor"


def _ruta() -> Path:
    return _directorio() / SESSION_FILE


def guardar_sesion(token: str, vendedor: dict, expira_epoch: int,
                   tasa: float = 0.0) -> None:
    directorio = _directorio()
    directorio.mkdir(parents=True, exist_ok=True)
    archivo = _ruta()
    temporal = archivo.with_suffix(".tmp")
    datos = {
        "token": str(token or ""),
        "vendor": dict(vendedor or {}),
        "expira_epoch": int(expira_epoch or 0),
        "tasa": float(tasa or 0),
        "guardado_en": int(time.time()),
    }
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    try:
        os.chmod(temporal, 0o600)
    except OSError:
        pass
    os.replace(temporal, archivo)


def leer_sesion() -> dict | None:
    archivo = _ruta()
    if not archivo.is_file():
        return None
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        borrar_sesion()
        return None
    token = str(datos.get("token", "")).strip()
    vendor = datos.get("vendor")
    try:
        expira = int(datos.get("expira_epoch", 0) or 0)
    except (TypeError, ValueError):
        borrar_sesion()
        return None
    if not token or not isinstance(vendor, dict) or expira <= int(time.time()):
        borrar_sesion()
        return None
    return {
        "token": token,
        "vendor": vendor,
        "expira_epoch": expira,
        "tasa": float(datos.get("tasa", 0) or 0),
    }


def borrar_sesion() -> None:
    archivo = _ruta()
    try:
        if archivo.is_file():
            archivo.unlink()
        temporal = archivo.with_suffix(".tmp")
        if temporal.is_file():
            temporal.unlink()
    except OSError:
        pass
