"""
Mayorix · Microservicio de tasa BCV
===================================
FastAPI expone la tasa oficial del dólar del Banco Central de Venezuela con
caché persistente. Si el BCV no responde, conserva la última tasa válida para
no bloquear la operación de la empresa.

Ejecución independiente:
    python bcv_service.py
    uvicorn bcv_service:app --host 127.0.0.1 --port 8010
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI

try:
    import uvicorn
except ImportError:  # pragma: no cover
    uvicorn = None


PUERTO = 8010
HOST = "127.0.0.1"
TTL_SEGUNDOS = 1800
URL_BCV = "https://www.bcv.org.ve/"
URL_RESPALDO = "https://ve.dolarapi.com/v1/dolares/oficial"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Mayorix/1.8"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ARCHIVO_CACHE = _base_dir() / "tasa_bcv.json"
_lock = threading.Lock()


def _leer_cache() -> dict:
    try:
        if ARCHIVO_CACHE.is_file():
            return json.loads(ARCHIVO_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {}


def _guardar_cache(datos: dict) -> None:
    try:
        ARCHIVO_CACHE.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _parsear_numero(valor: str) -> float | None:
    texto = str(valor or "").strip().replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        numero = float(texto)
    except (TypeError, ValueError):
        return None
    return numero if 0.01 < numero < 1_000_000 else None


def _consultar_bcv() -> float:
    contexto = ssl._create_unverified_context()
    solicitud = urllib.request.Request(URL_BCV, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(solicitud, timeout=15, context=contexto) as respuesta:
        html = respuesta.read().decode("utf-8", errors="replace")
    coincidencia = re.search(
        r'id=["\']dolar["\'].*?<strong[^>]*>\s*([\d.,]+)\s*</strong>',
        html, re.S | re.I,
    )
    if not coincidencia:
        raise ValueError("No se encontró la tasa del dólar en la página del BCV.")
    tasa = _parsear_numero(coincidencia.group(1))
    if not tasa:
        raise ValueError("La tasa del BCV no es válida.")
    return tasa


def _consultar_respaldo() -> float:
    solicitud = urllib.request.Request(URL_RESPALDO, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(solicitud, timeout=12) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    tasa = _parsear_numero(
        datos.get("promedio") or datos.get("tasa") or datos.get("valor")
    )
    if not tasa:
        raise ValueError("La API de respaldo no devolvió una tasa válida.")
    return tasa


def consultar_tasa(forzar: bool = False) -> dict:
    with _lock:
        cache = _leer_cache()
        ahora = datetime.now(timezone.utc)
        if not forzar and cache.get("actualizado_epoch"):
            antiguedad = time.time() - float(cache["actualizado_epoch"])
            if 0 <= antiguedad < TTL_SEGUNDOS and cache.get("tasa"):
                return {
                    "tasa": float(cache["tasa"]),
                    "fuente": cache.get("fuente", "caché"),
                    "actualizado": cache.get("actualizado"),
                    "cache": True,
                    "stale": False,
                }

        errores = []
        for fuente, funcion in (("BCV", _consultar_bcv),
                                ("DolarAPI", _consultar_respaldo)):
            try:
                tasa = funcion()
                datos = {
                    "tasa": tasa,
                    "fuente": fuente,
                    "actualizado": ahora.isoformat(),
                    "actualizado_epoch": time.time(),
                }
                _guardar_cache(datos)
                return {
                    "tasa": tasa,
                    "fuente": fuente,
                    "actualizado": datos["actualizado"],
                    "cache": False,
                    "stale": False,
                }
            except Exception as exc:
                errores.append(f"{fuente}: {type(exc).__name__}")

        if cache.get("tasa"):
            return {
                "tasa": float(cache["tasa"]),
                "fuente": cache.get("fuente", "caché"),
                "actualizado": cache.get("actualizado"),
                "cache": True,
                "stale": True,
                "error": "; ".join(errores),
            }
        return {
            "tasa": None,
            "fuente": "sin datos",
            "actualizado": None,
            "cache": False,
            "stale": True,
            "error": "; ".join(errores) or "No hay conexión con el BCV.",
        }


app = FastAPI(title="Mayorix · Tasa BCV", version="1.0.0")


@app.get("/tasa")
def tasa_bcv(forzar: bool = False):
    return consultar_tasa(forzar=forzar)


@app.get("/salud")
def salud():
    return {"estado": "ok", "servicio": "mayorix-bcv"}


def _puerto_abierto() -> bool:
    try:
        with socket.create_connection((HOST, PUERTO), timeout=0.6):
            return True
    except OSError:
        return False


def iniciar_servicio() -> bool:
    """Arranca uvicorn en segundo plano. Devuelve True si el puerto responde."""
    if _puerto_abierto():
        return True
    if uvicorn is None:
        return False

    def ejecutar():
        config = uvicorn.Config(
            app, host=HOST, port=PUERTO, log_level="warning",
            lifespan="off", access_log=False,
        )
        servidor = uvicorn.Server(config)
        servidor.run()

    hilo = threading.Thread(target=ejecutar, name="mayorix-bcv", daemon=True)
    hilo.start()
    for _ in range(30):
        if _puerto_abierto():
            return True
        time.sleep(0.2)
    return False


if __name__ == "__main__":
    if uvicorn is None:
        raise SystemExit("Instala uvicorn para ejecutar el servicio BCV.")
    uvicorn.run(app, host=HOST, port=PUERTO, log_level="info")
