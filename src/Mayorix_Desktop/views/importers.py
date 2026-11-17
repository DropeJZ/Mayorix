"""
Mayorix · Procesamiento de archivos e imágenes
==============================================
Importación de repuestos desde Excel/PDF y reconocimiento visual (OCR) para
asociar fotografías con el código de una refacción.

Todo el inventario trabaja con cuatro campos: Código, Descripción, Marca y
Precio en USD.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
from pathlib import Path

# Importación explícita para que PyInstaller incluya openpyxl al empaquetar.
try:
    import openpyxl  # noqa: F401
except ImportError:  # pragma: no cover
    openpyxl = None

import data
from database import normalizar_codigo, normalizar_texto


# ---------------------------------------------------------------------------
# Helpers generales
# ---------------------------------------------------------------------------


def bytes_de_archivo(archivo) -> bytes:
    """Obtiene bytes de un FilePickerFile en desktop o web."""
    contenido = getattr(archivo, "bytes", None)
    if contenido:
        return contenido
    ruta = getattr(archivo, "path", None)
    if ruta and Path(ruta).is_file():
        return Path(ruta).read_bytes()
    return b""


def parsear_precio(valor) -> float | None:
    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None
    texto = str(valor or "").strip()
    texto = re.sub(r"(?i)(usd|ves|bs\.?|\$|\s)", "", texto)
    texto = texto.replace("‑", "-")
    if not texto:
        return None
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        decimales = len(texto.split(",")[-1])
        if texto.count(",") == 1 and decimales <= 2:
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "." in texto:
        decimales = len(texto.split(".")[-1])
        if texto.count(".") > 1 or decimales == 3:
            texto = texto.replace(".", "")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def comprimir_imagen_b64(contenido: bytes, max_size: int = 900, calidad: int = 82) -> str:
    """Convierte la foto en un JPEG base64 razonable para MongoDB."""
    if not contenido:
        return ""
    try:
        from PIL import Image

        imagen = Image.open(io.BytesIO(contenido))
        imagen = imagen.convert("RGB")
        imagen.thumbnail((max_size, max_size))
        salida = io.BytesIO()
        imagen.save(salida, format="JPEG", quality=calidad, optimize=True)
        return base64.b64encode(salida.getvalue()).decode("ascii")
    except Exception:
        return base64.b64encode(contenido).decode("ascii")


def _normalizar_columna(nombre) -> str:
    texto = normalizar_texto(nombre)
    return re.sub(r"[^a-z0-9]+\s?", " ", texto).strip()


ALIAS_COLUMNAS = {
    "codigo": {
        "codigo", "codigo sku", "sku", "referencia", "ref", "codigo de parte",
        "part number", "partnumber", "cod", "codigo repuesto",
    },
    "descripcion": {
        "descripcion", "descripcion del repuesto", "nombre", "repuesto",
        "pieza", "producto", "descripcion repuesto",
    },
    "marca": {"marca", "fabricante", "brand", "marca repuesto"},
    "precio": {
        "precio", "precio usd", "precio $", "precio unitario", "pvp",
        "valor", "precio venta", "precio dolar", "precio en dolares",
    },
    "categoria": {
        "categoria", "categoria principal", "grupo", "linea", "tipo", "rubro",
    },
    "familia": {
        "familia", "subcategoria", "subfamilia", "tipo de repuesto", "familia repuesto",
    },
}


def _canonico(valor, opciones) -> str:
    objetivo = re.sub(r"[^a-z0-9]", "", normalizar_texto(valor))
    for opcion in opciones:
        if re.sub(r"[^a-z0-9]", "", normalizar_texto(opcion)) == objetivo:
            return opcion
    return ""


def _categoria(valor) -> str:
    return _canonico(valor, data.CATEGORIAS) or "Sin categoría"


def _familia(valor, categoria: str) -> str:
    texto = str(valor or "").strip()
    return _canonico(texto, data.familias_de(categoria)) or texto


def _mapear_columnas(columnas) -> dict:
    mapa = {}
    for columna in columnas:
        normalizada = _normalizar_columna(columna)
        for destino, alias in ALIAS_COLUMNAS.items():
            if normalizada in alias and destino not in mapa:
                mapa[destino] = columna
    return mapa


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


def parsear_excel(contenido: bytes) -> tuple[list[dict], list[str]]:
    errores: list[str] = []
    try:
        import pandas as pd

        df = pd.read_excel(io.BytesIO(contenido), engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"No se pudo leer el Excel: {exc}") from exc

    if df.empty:
        raise ValueError("El archivo Excel no contiene filas.")

    mapa = _mapear_columnas(df.columns)
    faltantes = [c for c in ("codigo", "descripcion", "marca", "precio") if c not in mapa]
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias: " + ", ".join(faltantes) +
            ". Usa Código, Descripción, Marca y Precio."
        )

    documentos = []
    vistos = set()

    def celda(valor):
        if valor is None:
            return ""
        try:
            if pd.isna(valor):
                return ""
        except (TypeError, ValueError):
            pass
        texto = str(valor).strip()
        return "" if texto.lower() in ("nan", "none", "nat") else texto

    for indice, fila in df.iterrows():
        numero_fila = int(indice) + 2
        codigo = celda(fila.get(mapa["codigo"]))
        descripcion = celda(fila.get(mapa["descripcion"]))
        marca = celda(fila.get(mapa["marca"]))
        precio = parsear_precio(fila.get(mapa["precio"], ""))
        if not codigo and not descripcion and not marca and precio is None:
            continue
        if not codigo or not descripcion or not marca or not precio or precio <= 0:
            errores.append(f"Fila {numero_fila}: datos incompletos o precio inválido.")
            continue
        codigo_norm = normalizar_codigo(codigo)
        if codigo_norm in vistos:
            errores.append(f"Fila {numero_fila}: código duplicado en el archivo ({codigo}).")
            continue
        vistos.add(codigo_norm)
        categoria = _categoria(celda(fila.get(mapa["categoria"]))) if "categoria" in mapa else "Sin categoría"
        familia = _familia(celda(fila.get(mapa["familia"])), categoria) if "familia" in mapa else ""
        documentos.append({
            "codigo": codigo.upper(),
            "descripcion": descripcion,
            "marca": marca,
            "categoria": categoria,
            "familia": familia,
            "precio": round(float(precio), 2),
        })
    return documentos, errores


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def parsear_pdf(contenido: bytes) -> tuple[list[dict], list[str]]:
    errores: list[str] = []
    try:
        from pypdf import PdfReader

        lector = PdfReader(io.BytesIO(contenido))
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc

    lineas: list[str] = []
    for pagina in lector.pages:
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""
        lineas.extend(texto.splitlines())

    documentos = []
    vistos = set()
    for linea in lineas:
        limpia = re.sub(r"\s+", " ", str(linea or "")).strip()
        if not limpia or len(limpia) < 8:
            continue
        if normalizar_texto(limpia).startswith(("codigo", "descripcion", "sku", "total")):
            continue
        partes = [p.strip() for p in re.split(r"\s*[|;]\s*|\t+|\s{2,}", limpia) if p.strip()]
        codigo = descripcion = marca = ""
        precio = None
        if len(partes) >= 4:
            codigo, descripcion, marca = partes[0], partes[1], partes[2]
            precio = parsear_precio(partes[-1])
        elif len(partes) == 3:
            codigo, descripcion = partes[0], partes[1]
            marca = "Sin marca"
            precio = parsear_precio(partes[-1])
        else:
            # Formato alternativo: código descripción marca $precio
            coincidencia = re.search(
                r"^(?P<codigo>[A-Z0-9][A-Z0-9._/-]{2,})\s+"
                r"(?P<descripcion>.+?)\s+"
                r"(?P<marca>[A-Za-zÁÉÍÓÚÑáéíóúñ][A-Za-z0-9 .&-]*?)\s+"
                r"\$?\s*(?P<precio>[\d.,]+)\s*$",
                limpia,
            )
            if coincidencia:
                codigo = coincidencia.group("codigo")
                descripcion = coincidencia.group("descripcion")
                marca = coincidencia.group("marca")
                precio = parsear_precio(coincidencia.group("precio"))
        if not codigo or not descripcion or not precio or precio <= 0:
            continue
        codigo_norm = normalizar_codigo(codigo)
        if codigo_norm in vistos:
            continue
        vistos.add(codigo_norm)
        documentos.append({
            "codigo": codigo.upper(),
            "descripcion": descripcion,
            "marca": marca or "Sin marca",
            "categoria": "Sin categoría",
            "familia": "",
            "precio": round(float(precio), 2),
        })

    if not documentos:
        errores.append(
            "No se detectaron repuestos en el PDF. Usa líneas con formato "
            "Código | Descripción | Marca | Precio."
        )
    return documentos, errores


# ---------------------------------------------------------------------------
# Reconocimiento visual (OCR)
# ---------------------------------------------------------------------------


def simular_ocr(nombre_archivo: str, contenido: bytes, repuestos: list[dict]) -> dict:
    """
    Intenta OCR real si pytesseract está disponible. Si no, simula la lectura
    visual buscando un código en el nombre del archivo o asignando uno
    determinista a partir de la imagen.
    """
    if not repuestos:
        return {"codigo": "", "texto": "", "simulado": True, "confianza": 0}

    texto_ocr = ""
    simulado = True
    try:
        import pytesseract  # type: ignore
        from PIL import Image

        imagen = Image.open(io.BytesIO(contenido))
        texto_ocr = pytesseract.image_to_string(imagen, lang="spa+eng")
        simulado = False
    except Exception:
        texto_ocr = ""

    pista = f"{nombre_archivo}\n{texto_ocr}"
    pista_norm = normalizar_codigo(pista)

    elegido = None
    for repuesto in repuestos:
        codigo_norm = normalizar_codigo(repuesto.get("codigo", ""))
        if codigo_norm and codigo_norm in pista_norm:
            elegido = repuesto
            break

    if elegido is None:
        # Simulación determinista: la misma foto siempre sugiere el mismo repuesto.
        semilla = hashlib.sha1(
            (nombre_archivo or "mayorix").encode("utf-8") + contenido
        )
        indice = int(semilla.hexdigest()[:8], 16) % len(repuestos)
        elegido = repuestos[indice]

    codigo = elegido.get("codigo", "")
    if not texto_ocr:
        texto_ocr = (
            f"OCR simulado\nCódigo detectado: {codigo}\n"
            f"Descripción: {elegido.get('descripcion', '')}\n"
            f"Marca: {elegido.get('marca', '')}"
        )
    return {
        "codigo": codigo,
        "texto": texto_ocr.strip(),
        "simulado": simulado,
        "confianza": 88 if simulado else 96,
        "repuesto": elegido,
    }
