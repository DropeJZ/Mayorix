"""
Almacenamiento local de la sesión móvil de Mayorix.

Usa `ft.SharedPreferences` (almacenamiento persistente de Flet 1.0, equivalente
a `client_storage` de versiones anteriores). Guarda únicamente un token
aleatorio y el perfil público del vendedor. Nunca guarda la contraseña.
"""

from __future__ import annotations

import json
import time

SESSION_KEY = "mayorix.sesion_movil"


async def guardar_sesion(prefs, token: str, vendedor: dict, expira_epoch: int,
                         tasa: float = 0.0) -> None:
    datos = {
        "token": str(token or ""),
        "vendor": dict(vendedor or {}),
        "expira_epoch": int(expira_epoch or 0),
        "tasa": float(tasa or 0),
        "guardado_en": int(time.time()),
    }
    await prefs.set(
        SESSION_KEY,
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")),
    )


async def leer_sesion(prefs) -> dict | None:
    try:
        crudo = await prefs.get(SESSION_KEY)
    except Exception:
        return None
    if not crudo:
        return None
    try:
        datos = json.loads(str(crudo))
    except (ValueError, TypeError):
        await borrar_sesion(prefs)
        return None
    if not isinstance(datos, dict):
        await borrar_sesion(prefs)
        return None
    token = str(datos.get("token", "")).strip()
    vendor = datos.get("vendor")
    try:
        expira = int(datos.get("expira_epoch", 0) or 0)
    except (TypeError, ValueError):
        await borrar_sesion(prefs)
        return None
    if not token or not isinstance(vendor, dict) or expira <= int(time.time()):
        await borrar_sesion(prefs)
        return None
    return datos


async def borrar_sesion(prefs) -> None:
    try:
        await prefs.remove(SESSION_KEY)
    except Exception:
        pass
