"""
Tasa oficial BCV para la app móvil.
Obtiene la tasa desde BCV o DolarAPI y conserva una tasa de respaldo incluida
en el APK para funcionar sin conexión.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.request

URL_BCV = "https://www.bcv.org.ve/"
URL_RESPALDO = "https://ve.dolarapi.com/v1/dolares/oficial"
USER_AGENT = "Mozilla/5.0 (Linux; Android 13) MayorixVendedor/1.1"
TTL = 1800

_cache = {"tasa": 0.0, "fuente": "", "actualizado": 0.0}


def _parsear(valor) -> float | None:
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


def _desde_bcv() -> float:
    contexto = ssl._create_unverified_context()
    solicitud = urllib.request.Request(
        URL_BCV, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(
        solicitud, timeout=9, context=contexto
    ) as respuesta:
        html = respuesta.read().decode("utf-8", errors="replace")
    coincidencia = re.search(
        r'id=["\']dolar["\'].*?<strong[^>]*>\s*([\d.,]+)\s*</strong>',
        html, re.S | re.I,
    )
    if not coincidencia:
        raise ValueError("Tasa no encontrada en BCV.")
    tasa = _parsear(coincidencia.group(1))
    if not tasa:
        raise ValueError("Tasa BCV inválida.")
    return tasa


def _desde_respaldo() -> float:
    solicitud = urllib.request.Request(
        URL_RESPALDO, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(solicitud, timeout=8) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    tasa = _parsear(
        datos.get("promedio") or datos.get("tasa") or datos.get("valor")
    )
    if not tasa:
        raise ValueError("Tasa de respaldo inválida.")
    return tasa


def _fallback() -> float:
    try:
        from atlas_config import TASA_INICIAL
        return float(TASA_INICIAL or 0)
    except Exception:
        return 0.0


def consultar_tasa(forzar: bool = False) -> dict:
    ahora = time.time()
    if (not forzar and _cache["tasa"] > 0
            and ahora - _cache["actualizado"] < TTL):
        return dict(_cache)
    for fuente, funcion in (("BCV", _desde_bcv),
                            ("DolarAPI", _desde_respaldo)):
        try:
            tasa = funcion()
            _cache.update({
                "tasa": tasa,
                "fuente": fuente,
                "actualizado": ahora,
            })
            return dict(_cache)
        except Exception:
            continue
    if _cache["tasa"] > 0:
        return dict(_cache)
    return {
        "tasa": _fallback(),
        "fuente": "respaldo local",
        "actualizado": ahora,
    }
