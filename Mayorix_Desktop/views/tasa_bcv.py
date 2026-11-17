"""
Mayorix · Tasa BCV en el escritorio
===================================
Consulta el microservicio FastAPI local, mantiene una caché persistente y
actualiza la tasa usada por las conversiones USD ↔ VES.
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime

import data
import bcv_service


def _leer_cache() -> dict:
    try:
        if bcv_service.ARCHIVO_CACHE.is_file():
            return json.loads(
                bcv_service.ARCHIVO_CACHE.read_text(encoding="utf-8")
            )
    except (OSError, ValueError):
        pass
    return {}


def _guardar_cache(resultado: dict) -> None:
    if not resultado.get("tasa"):
        return
    datos = {
        "tasa": float(resultado["tasa"]),
        "fuente": resultado.get("fuente", "BCV"),
        "actualizado": resultado.get("actualizado")
        or datetime.now().isoformat(),
        "actualizado_epoch": time.time(),
    }
    try:
        bcv_service.ARCHIVO_CACHE.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _aplicar(tasa, actualizado=None) -> None:
    try:
        valor = float(tasa)
    except (TypeError, ValueError):
        return
    if not (0.01 < valor < 1_000_000):
        return
    data.TASA_VES = valor
    if actualizado:
        try:
            fecha = datetime.fromisoformat(str(actualizado))
            data.TASA_VES_FECHA = fecha.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass


def inicializar() -> dict:
    cache = _leer_cache()
    if cache.get("tasa"):
        _aplicar(cache["tasa"], cache.get("actualizado"))
        return {
            "ok": True,
            "tasa": float(cache["tasa"]),
            "fuente": cache.get("fuente", "caché"),
            "actualizado": cache.get("actualizado"),
            "stale": True,
        }
    return {"ok": False, "tasa": data.TASA_VES, "error": "Sin caché de tasa."}


def actualizar(forzar: bool = False) -> dict:
    url = f"http://127.0.0.1:{bcv_service.PUERTO}/tasa"
    if forzar:
        url += "?forzar=true"
    try:
        solicitud = urllib.request.Request(url, headers={"User-Agent": "Mayorix"})
        with urllib.request.urlopen(solicitud, timeout=14) as respuesta:
            resultado = json.loads(respuesta.read().decode("utf-8"))
        if resultado.get("tasa"):
            _aplicar(resultado["tasa"], resultado.get("actualizado"))
            _guardar_cache(resultado)
            return {
                "ok": True,
                "tasa": float(resultado["tasa"]),
                "fuente": resultado.get("fuente", "BCV"),
                "actualizado": resultado.get("actualizado"),
                "stale": bool(resultado.get("stale")),
                "cache": bool(resultado.get("cache")),
            }
        error = resultado.get("error", "El servicio no devolvió una tasa válida.")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    cache = _leer_cache()
    if cache.get("tasa"):
        _aplicar(cache["tasa"], cache.get("actualizado"))
        return {
            "ok": True,
            "tasa": float(cache["tasa"]),
            "fuente": cache.get("fuente", "caché"),
            "actualizado": cache.get("actualizado"),
            "stale": True,
            "error": error,
        }
    return {"ok": False, "tasa": data.TASA_VES, "error": error}


def detalle() -> str:
    cache = _leer_cache()
    if not cache.get("tasa"):
        return "Tasa referencial sin conexión"
    actualizado = cache.get("actualizado", "")
    try:
        fecha = datetime.fromisoformat(actualizado).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        fecha = ""
    origen = cache.get("fuente", "caché")
    return f"Tasa {origen}" + (f" · {fecha}" if fecha else "")
