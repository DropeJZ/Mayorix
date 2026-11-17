Ejecutable de Windows · Mayorix para Mayor Disluda
==================================================

El compilado autónomo se genera en la raíz del proyecto:

    D:\PROYECTOS\Mayorix\Mayorix.exe

Aplicación de escritorio exclusiva para la administración de la empresa.
Incluye Python, Flet 1.0.4, pymongo, pandas, openpyxl, pypdf, Pillow, la app
y los assets. La base de datos MongoDB no se incluye: se configura con
MONGODB_URI, un archivo mongo_uri.txt junto a Mayorix.exe, o se usa el modo
de respaldo local.

Regenerar desde Mayorix_Desktop:

    flet pack main.py --name Mayorix --icon assets/mayorix.ico --add-data "assets;assets" --hidden-import pandas --hidden-import openpyxl --hidden-import openpyxl.cell._writer --hidden-import pypdf --hidden-import pymongo --hidden-import dns --hidden-import dns.resolver --hidden-import PIL.Image --hidden-import fastapi --hidden-import starlette --hidden-import pydantic --hidden-import uvicorn --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --product-name "Mayorix" --file-description "Mayorix · Sistema de Gestión Mayorista" --company-name "DropeTech" --product-version "2.1.3" --file-version "2.1.3.0" --copyright "Copyright © 2026 DropeTech"

El artefacto resultante (dist/Mayorix.exe) se copia a la raíz como Mayorix.exe.

Notas:
- Versión 2.1.3.
- Ventana estándar de Windows de 1280 x 800: barra de título nativa,
  minimizar, maximizar/restaurar, redimensionar, mover y cerrar normalmente.
- Dashboard, Repuestos, Pedidos recibidos, Vendedores y Finanzas operativos.
  Ayuda, Configuración y el indicador de MongoDB también son interactivos.
- Inventario paginado de 20 en 20 con .skip()/.limit(20) y proyección ligera
  (sin foto_b64 ni ocr_text en el listado).
- Compilado con PyInstaller en modo onefile y sin consola.
- main.py refuerza stdout/stderr cuando no existen para que el logging de Flet/uvicorn funcione en el ejecutable.
- Icono: assets/mayorix.ico
- Contexto: Mayorix · Sistema de Gestión Mayorista para Mayor Disluda · Powered by DropeTech.
- Primer arranque: la app muestra "Registrar administrador" si la coleccion usuarios esta vacia.
- No incluye acceso de vendedores: es una app exclusiva de administración.

- Registros móviles: la barra superior muestra el botón Móvil con los códigos de verificación pendientes generados por la app Android.
