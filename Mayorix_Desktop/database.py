"""
Mayorix Desktop · Capa central de datos
=======================================
Conexión a MongoDB Atlas / local con modo de respaldo automático.

Colecciones:
- usuarios    → credenciales de la empresa (hash PBKDF2)
- inventario  → repuestos: código, descripción, marca y precio USD
- vendedores  → red comercial administrada por la empresa
- pedidos     → pedidos recibidos de la red externa

Si MongoDB no está disponible o requiere autenticación, la aplicación usa
un almacén en memoria vacío para que el prototipo siga siendo navegable y
permita registrar datos durante la sesión. El estado se muestra en la UI.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import os
import re
import secrets
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import data

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
    from pymongo.errors import DuplicateKeyError

    PYMONGO_DISPONIBLE = True
except ImportError:  # pragma: no cover - solo si falta la dependencia
    ASCENDING = 1
    DuplicateKeyError = Exception
    PYMONGO_DISPONIBLE = False


PROJECT_DIR = Path(__file__).parent
DEFAULT_URI = "mongodb://localhost:27017/"
DEFAULT_DB = "mayorix"
PASSWORD_ITERATIONS = 160000


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def ahora_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalizar_codigo(valor: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(valor or "").upper())


def normalizar_cedula(valor: str) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def normalizar_texto(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


REEMPLAZOS_CODIFICACION = {
    "Suspensi?n": "Suspensión", "Direcci?n": "Dirección",
    "Transmisi?n": "Transmisión", "Buj?as": "Bujías", "Buj?a": "Bujía",
    "buj?as": "bujías", "buj?a": "bujía", "Pist?n": "Pistón",
    "pist?n": "pistón", "Categor?a": "Categoría", "categor?a": "categoría",
    "Gen?rico": "Genérico", "gen?rico": "genérico", "Cr?dito": "Crédito",
    "cr?dito": "crédito", "D?as": "Días", "d?as": "días",
    "El?ctrico": "Eléctrico", "el?ctrico": "eléctrico",
    "Mec?nica": "Mecánica", "mec?nica": "mecánica",
    "Autom?vil": "Automóvil", "autom?vil": "automóvil",
    "C?digo": "Código", "c?digo": "código",
    "Descripci?n": "Descripción", "descripci?n": "descripción",
    "N?mero": "Número", "n?mero": "número", "Tel?fono": "Teléfono",
    "tel?fono": "teléfono", "C?dula": "Cédula", "c?dula": "cédula",
    "Jos?": "José", "Mar?a": "María", "M?rida": "Mérida", "Cuman?": "Cumaná",
    "San Crist?bal": "San Cristóbal", "Panam?": "Panamá", "M?xico": "México",
    "Per?": "Perú", "Bogot?": "Bogotá", "P?rez": "Pérez", "G?mez": "Gómez",
    "L?pez": "López", "Rodr?guez": "Rodríguez", "Hern?ndez": "Hernández",
    "Mart?nez": "Martínez", "Rep?blica": "República", "Veh?culo": "Vehículo",
    "veh?culo": "vehículo", "A?o": "Año", "a?o": "año",
    "Se?or": "Señor", "se?or": "señor",
    "R?tulas": "Rótulas", "r?tulas": "rótulas",
    "R?tula": "Rótula", "r?tula": "rótula",
}


def limpiar_texto(valor) -> str:
    """Normaliza Unicode y corrige secuencias típicas de codificación rota."""
    texto = str(valor or "")
    if "Ã" in texto or "Â" in texto:
        try:
            texto = texto.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    texto = unicodedata.normalize("NFC", texto)
    for roto, correcto in REEMPLAZOS_CODIFICACION.items():
        texto = texto.replace(roto, correcto)
    return texto.strip()


def clave_texto(valor) -> str:
    return re.sub(r"[^a-z0-9]", "", normalizar_texto(valor))


def categoria_canonica(valor) -> str:
    clave = clave_texto(valor)
    if not clave or clave == "sincategoria":
        return data.CATEGORIA_SIN
    for categoria in data.CATEGORIAS:
        if clave == clave_texto(categoria):
            return categoria
    return limpiar_texto(valor) or data.CATEGORIA_SIN


def familia_canonica(valor, categoria: str) -> str:
    texto = limpiar_texto(valor)
    clave = clave_texto(texto)
    for familia in data.familias_de(categoria):
        if clave == clave_texto(familia):
            return familia
    return texto


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    sal = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        bytes.fromhex(sal),
        PASSWORD_ITERATIONS,
    ).hex()
    return sal, digest


def verificar_password(password: str, salt: str, password_hash: str) -> bool:
    if not salt or not password_hash:
        return False
    _, candidato = _hash_password(password, salt)
    return hmac.compare_digest(candidato, password_hash)


def uri_visible(uri: str) -> str:
    """Oculta usuario:contraseña antes de mostrar la URI en la UI."""
    return re.sub(r"(mongodb(?:\+srv)?://)[^/@]+@", r"\1***@", str(uri))


def _leer_uri() -> str:
    uri = os.getenv("MONGO_URI", "").strip()
    if uri:
        return uri
    candidatos = [PROJECT_DIR / "mongo_uri.txt"]
    if getattr(sys, "frozen", False):
        candidatos.insert(0, Path(sys.executable).resolve().parent / "mongo_uri.txt")
    for archivo in candidatos:
        if archivo.is_file():
            try:
                contenido = archivo.read_text(encoding="utf-8").strip()
                if contenido:
                    return contenido
            except OSError:
                pass
    return DEFAULT_URI


def _mensaje_conexion(error: Exception, uri: str = "") -> str:
    texto = str(error)
    minusculas = texto.lower()
    es_atlas = "mongodb+srv://" in uri or ".mongodb.net" in uri
    if "authentication" in minusculas or "requires authentication" in minusculas:
        return (
            "MongoDB rechazó las credenciales. Revisa usuario y contraseña de la URI."
        )
    if ("ssl handshake" in minusculas or "no replica set members" in minusculas
            or "handshake" in minusculas):
        if es_atlas:
            return (
                "Atlas no respondió al handshake TLS. Agrega la IP pública de este "
                "equipo en Network Access del clúster y verifica el firewall. Si el "
                "clúster está pausado, reactívalo en Atlas."
            )
        return "No se pudo completar la conexión TLS con MongoDB. Revisa la red."
    if "serverselectiontimeout" in minusculas or "timed out" in minusculas:
        return "No se pudo conectar a MongoDB. Revisa la URI, la red o la lista de IP."
    if "dns" in minusculas or "name or service not known" in minusculas:
        return "No se pudo resolver el host de MongoDB. Revisa la URI o el DNS."
    return f"No se pudo conectar a MongoDB: {texto}"


def _timeout_conexion(uri: str) -> int:
    """Atlas necesita más margen que una instancia local para el handshake TLS."""
    if "mongodb+srv://" in uri or ".mongodb.net" in uri:
        return 4500
    return 2500



# ---------------------------------------------------------------------------
# Almac?n en memoria (modo respaldo)
# ---------------------------------------------------------------------------


class MemoryStore:
    modo = "fallback"

    def __init__(self):
        self.usuarios: list[dict] = []
        self.vendedores: list[dict] = []
        self.inventario: list[dict] = []
        self.pedidos: list[dict] = []
        self.solicitudes_registro: list[dict] = []

    # Autenticación -----------------------------------------------------
    def autenticar_empresa(self, email: str, password: str) -> dict | None:
        buscado = str(email or "").strip().lower()
        for usuario in self.usuarios:
            if usuario.get("email", "").lower() == buscado and usuario.get("activo", True):
                if verificar_password(password, usuario.get("salt", ""),
                                      usuario.get("password_hash", "")):
                    return {
                        "email": usuario["email"],
                        "nombre": usuario.get("nombre", "Administrador"),
                        "rol": "empresa",
                    }
        return None

    def contar_usuarios(self) -> int:
        return len(self.usuarios)

    def crear_primer_usuario(self, doc: dict) -> tuple[bool, str, dict | None]:
        if self.usuarios:
            return False, "Ya existe un administrador registrado.", None
        email = limpiar_texto(doc.get("email", "")).lower()
        nombre = limpiar_texto(doc.get("nombre", ""))
        password = str(doc.get("password", ""))
        if not nombre or not email or len(password) < 8:
            return False, "Completa el nombre, el correo y una contraseña de 8 caracteres.", None
        if "@" not in email or "." not in email.split("@")[-1]:
            return False, "Ingresa un correo corporativo válido.", None
        sal, password_hash = _hash_password(password)
        nuevo = {
            "email": email,
            "nombre": nombre,
            "rol": "empresa",
            "activo": True,
            "salt": sal,
            "password_hash": password_hash,
            "created_at": ahora_iso(),
        }
        self.usuarios.append(nuevo)
        return True, "Administrador registrado correctamente.", {
            "email": email, "nombre": nombre, "rol": "empresa",
        }

    # Vendedores --------------------------------------------------------
    def listar_vendedores(self) -> list[dict]:
        return sorted(
            (dict(x) for x in self.vendedores),
            key=lambda x: normalizar_texto(x.get("nombre", "")),
        )

    def listar_solicitudes_registro(self) -> list[dict]:
        ahora = int(time.time())
        pendientes = [
            dict(s) for s in self.solicitudes_registro
            if s.get("estado") == "pendiente"
            and int(s.get("expira_epoch", 0)) > ahora
        ]
        return sorted(
            pendientes, key=lambda s: s.get("created_at", ""), reverse=True
        )

    def descartar_solicitud_registro(self, solicitud_id: str) -> bool:
        for solicitud in self.solicitudes_registro:
            if solicitud.get("solicitud_id") == solicitud_id:
                solicitud["estado"] = "descartado"
                solicitud["descartado_at"] = ahora_iso()
                return True
        return False

    def buscar_vendedor(self, identificador: str) -> dict | None:
        cedula_norm = normalizar_cedula(identificador)
        codigo_norm = normalizar_codigo(identificador)
        for vendedor_obj in self.vendedores:
            if (vendedor_obj.get("cedula_norm") and
                    vendedor_obj["cedula_norm"] == cedula_norm):
                return dict(vendedor_obj)
            if vendedor_obj.get("codigo_norm") == codigo_norm:
                return dict(vendedor_obj)
        return None

    def siguiente_codigo_vendedor(self) -> str:
        usados = {v.get("codigo") for v in self.vendedores}
        numero = len(self.vendedores) + 1
        while f"MD-VEN-{numero:03d}" in usados:
            numero += 1
        return f"MD-VEN-{numero:03d}"

    def crear_vendedor(self, doc: dict) -> tuple[bool, str, dict | None]:
        cedula_norm = normalizar_cedula(doc.get("cedula", ""))
        if not doc.get("nombre") or not cedula_norm:
            return False, "Nombre y cédula son obligatorios.", None
        for vendedor_obj in self.vendedores:
            if vendedor_obj.get("cedula_norm") == cedula_norm:
                return False, "Ya existe un vendedor con esa cédula.", None
        codigo = doc.get("codigo") or self.siguiente_codigo_vendedor()
        if any(v.get("codigo_norm") == normalizar_codigo(codigo) for v in self.vendedores):
            return False, "El código de vendedor ya existe.", None
        nuevo = {
            "codigo": codigo,
            "codigo_norm": normalizar_codigo(codigo),
            "nombre": limpiar_texto(doc["nombre"]),
            "cedula": limpiar_texto(doc.get("cedula", "")),
            "cedula_norm": cedula_norm,
            "telefono": limpiar_texto(doc.get("telefono", "")),
            "ciudad": limpiar_texto(doc.get("ciudad", "")),
            "email": limpiar_texto(doc.get("email", "")).lower(),
            "foto_b64": doc.get("foto_b64", ""),
            "estado": "Activo",
            "created_at": ahora_iso(),
            "origen": "manual",
        }
        self.vendedores.append(nuevo)
        return True, "Vendedor creado correctamente.", dict(nuevo)

    def actualizar_vendedor(self, doc: dict) -> tuple[bool, str, dict | None]:
        codigo = str(doc.get("codigo", "")).strip()
        cedula_norm = normalizar_cedula(doc.get("cedula", ""))
        if not doc.get("nombre") or not cedula_norm:
            return False, "Nombre y cédula son obligatorios.", None
        for vendedor_obj in self.vendedores:
            if (vendedor_obj.get("codigo") != codigo and
                    vendedor_obj.get("cedula_norm") == cedula_norm):
                return False, "Otra persona ya tiene esa cédula.", None
        for vendedor_obj in self.vendedores:
            if vendedor_obj.get("codigo") == codigo:
                vendedor_obj.update({
                    "nombre": str(doc.get("nombre", "")).strip(),
                    "cedula": limpiar_texto(doc.get("cedula", "")),
                    "cedula_norm": cedula_norm,
                    "telefono": limpiar_texto(doc.get("telefono", "")),
                    "ciudad": limpiar_texto(doc.get("ciudad", "")),
                    "email": limpiar_texto(doc.get("email", "")).lower(),
                    "foto_b64": doc.get("foto_b64", vendedor_obj.get("foto_b64", "")),
                    "estado": str(doc.get("estado", vendedor_obj.get("estado", "Activo"))),
                    "updated_at": ahora_iso(),
                })
                return True, "Vendedor actualizado.", dict(vendedor_obj)
        return False, "No se encontró el vendedor.", None

    def eliminar_vendedor(self, codigo: str) -> tuple[bool, str]:
        antes = len(self.vendedores)
        self.vendedores = [v for v in self.vendedores if v.get("codigo") != codigo]
        if len(self.vendedores) < antes:
            return True, "Vendedor eliminado."
        return False, "No se encontró el vendedor."

    # Inventario --------------------------------------------------------
    def listar_inventario(self) -> list[dict]:
        return sorted(
            (dict(x) for x in self.inventario),
            key=lambda x: (
                normalizar_texto(x.get("descripcion", "")),
                normalizar_codigo(x.get("codigo", "")),
            ),
        )

    def resumen_inventario(self) -> dict:
        marcas = {
            str(x.get("marca", "")).strip()
            for x in self.inventario
            if str(x.get("marca", "")).strip()
        }
        valor = 0.0
        for x in self.inventario:
            try:
                valor += float(x.get("precio", 0) or 0)
            except (TypeError, ValueError):
                pass
        return {
            "total": len(self.inventario),
            "marcas": len(marcas),
            "con_foto": sum(1 for x in self.inventario if x.get("foto_b64")),
            "valor_lista": valor,
        }

    def _inventario_filtrado(self, busqueda: str = "") -> list[dict]:
        q = normalizar_texto(busqueda)
        elementos = [
            dict(x) for x in self.inventario
            if not q
            or q in normalizar_texto(x.get("codigo", ""))
            or q in normalizar_texto(x.get("descripcion", ""))
            or q in normalizar_texto(x.get("marca", ""))
        ]
        return sorted(
            elementos,
            key=lambda x: (
                normalizar_texto(x.get("descripcion", "")),
                normalizar_codigo(x.get("codigo", "")),
            ),
        )

    def contar_inventario_filtrado(self, busqueda: str = "") -> int:
        return len(self._inventario_filtrado(busqueda))

    def listar_inventario_pagina(self, skip: int = 0, limit: int = 20,
                                 busqueda: str = "") -> list[dict]:
        inicio = max(0, int(skip))
        cantidad = max(1, min(200, int(limit)))
        return self._inventario_filtrado(busqueda)[inicio:inicio + cantidad]

    def listar_referencias_ocr(self) -> list[dict]:
        return [
            {"codigo": x.get("codigo", ""),
             "descripcion": x.get("descripcion", ""),
             "marca": x.get("marca", "")}
            for x in self.inventario
        ]


    def buscar_repuesto(self, codigo: str) -> dict | None:
        codigo_norm = normalizar_codigo(codigo)
        for repuesto in self.inventario:
            if normalizar_codigo(repuesto.get("codigo")) == codigo_norm:
                return dict(repuesto)
        return None

    def guardar_repuesto(self, doc: dict) -> tuple[bool, str]:
        codigo = limpiar_texto(doc.get("codigo", "")).upper()
        descripcion = limpiar_texto(doc.get("descripcion", ""))
        marca = limpiar_texto(doc.get("marca", ""))
        if not codigo or not descripcion or not marca:
            return False, "Código, descripción y marca son obligatorios."
        try:
            precio = float(doc.get("precio", 0))
        except (TypeError, ValueError):
            return False, "El precio debe ser numérico."
        if precio <= 0:
            return False, "El precio debe ser mayor que cero."

        existente = self.buscar_repuesto(codigo)
        base = existente or {}
        categoria = categoria_canonica(
            doc.get("categoria", base.get("categoria", ""))
        )
        familia = familia_canonica(
            doc.get("familia", base.get("familia", "")), categoria
        )
        base.update({
            "codigo": codigo,
            "descripcion": descripcion,
            "marca": marca,
            "categoria": categoria,
            "familia": familia,
            "precio": round(precio, 2),
            "foto_b64": doc.get("foto_b64", base.get("foto_b64", "")),
            "ocr_text": doc.get("ocr_text", base.get("ocr_text", "")),
            "updated_at": ahora_iso(),
            "created_at": base.get("created_at", ahora_iso()),
        })
        if existente:
            self.inventario = [
                r for r in self.inventario
                if normalizar_codigo(r.get("codigo")) != normalizar_codigo(codigo)
            ]
            self.inventario.append(base)
            return True, "Repuesto actualizado."
        self.inventario.append(base)
        return True, "Repuesto creado."

    def importar_repuestos(self, docs: list[dict], on_progress=None) -> tuple[int, int, list[str]]:
        insertados = 0
        actualizados = 0
        errores = []
        total = len(docs)
        for indice, doc in enumerate(docs, start=1):
            ya_existe = self.buscar_repuesto(doc.get("codigo", "")) is not None
            ok, mensaje = self.guardar_repuesto(doc)
            if not ok:
                errores.append(f"{doc.get('codigo', '?')}: {mensaje}")
            elif ya_existe:
                actualizados += 1
            else:
                insertados += 1
            if on_progress is not None:
                try:
                    on_progress(indice, total, insertados, actualizados)
                except Exception:
                    pass
        return insertados, actualizados, errores

    def actualizar_foto(self, codigo: str, foto_b64: str, ocr_text: str = "") -> bool:
        repuesto = self.buscar_repuesto(codigo)
        if not repuesto:
            return False
        repuesto["foto_b64"] = foto_b64
        repuesto["ocr_text"] = ocr_text
        repuesto["updated_at"] = ahora_iso()
        self.inventario = [
            r for r in self.inventario
            if normalizar_codigo(r.get("codigo")) != normalizar_codigo(codigo)
        ]
        self.inventario.append(repuesto)
        return True

    def eliminar_repuesto(self, codigo: str) -> bool:
        antes = len(self.inventario)
        self.inventario = [
            r for r in self.inventario
            if normalizar_codigo(r.get("codigo")) != normalizar_codigo(codigo)
        ]
        return len(self.inventario) < antes

    def contar_inventario(self) -> int:
        return len(self.inventario)

    def contar_vendedores(self) -> int:
        return len(self.vendedores)

    # Pedidos -----------------------------------------------------------
    def listar_pedidos(self) -> list[dict]:
        return sorted(
            (copy.deepcopy(x) for x in self.pedidos),
            key=lambda x: (x.get("fecha", ""), x.get("pedido_id", "")),
            reverse=True,
        )

    def actualizar_estado_pedido(self, pedido_id: str, estado: str) -> bool:
        for pedido_obj in self.pedidos:
            if pedido_obj.get("pedido_id") == pedido_id:
                pedido_obj["estado"] = estado
                pedido_obj["updated_at"] = ahora_iso()
                return True
        return False

    def contar_pedidos(self) -> int:
        return len(self.pedidos)


# ---------------------------------------------------------------------------
# Almacén MongoDB
# ---------------------------------------------------------------------------


class MongoStore:
    modo = "mongodb"

    def __init__(self, uri: str, db_name: str, timeout_ms: int = 2500):
        if not PYMONGO_DISPONIBLE:
            raise RuntimeError("pymongo no está instalado.")
        self.uri = uri
        self.db_name = db_name
        self.client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        self.db = self.client[db_name]
        # Esta operación requiere autenticación y valida el acceso real.
        self.db.list_collection_names()
        self.usuarios = self.db["usuarios"]
        self.vendedores = self.db["vendedores"]
        self.inventario = self.db["inventario"]
        self.pedidos = self.db["pedidos"]
        self.solicitudes_registro = self.db["solicitudes_registro"]
        self._asegurar_colecciones()
        self._asegurar_indices()

    def _asegurar_colecciones(self):
        """Crea las colecciones vacías si aún no existen."""
        existentes = set(self.db.list_collection_names())
        for nombre in ("usuarios", "inventario", "vendedores", "pedidos",
                       "solicitudes_registro"):
            if nombre not in existentes:
                try:
                    self.db.create_collection(nombre)
                except Exception:
                    pass

    def _asegurar_indices(self):
        self.usuarios.create_index([("email", ASCENDING)], unique=True)
        self.vendedores.create_index([("cedula_norm", ASCENDING)], unique=True)
        self.vendedores.create_index([("codigo_norm", ASCENDING)], unique=True)
        self.inventario.create_index([("codigo", ASCENDING)], unique=True)
        self.inventario.create_index(
            [("descripcion", ASCENDING)], name="descripcion_1"
        )
        self.pedidos.create_index([("pedido_id", ASCENDING)], unique=True)
        try:
            self.solicitudes_registro.create_index(
                [("estado", ASCENDING), ("expira_epoch", ASCENDING)]
            )
        except Exception:
            pass

    # Autenticación -----------------------------------------------------
    def autenticar_empresa(self, email: str, password: str) -> dict | None:
        buscado = str(email or "").strip().lower()
        usuario = self.usuarios.find_one({"email": buscado})
        if not usuario or not usuario.get("activo", True):
            return None
        if verificar_password(password, usuario.get("salt", ""),
                              usuario.get("password_hash", "")):
            return {
                "email": usuario["email"],
                "nombre": usuario.get("nombre", "Administrador"),
                "rol": "empresa",
            }
        return None

    def contar_usuarios(self) -> int:
        return self.usuarios.count_documents({})

    def crear_primer_usuario(self, doc: dict) -> tuple[bool, str, dict | None]:
        if self.usuarios.count_documents({}) > 0:
            return False, "Ya existe un administrador registrado.", None
        email = limpiar_texto(doc.get("email", "")).lower()
        nombre = limpiar_texto(doc.get("nombre", ""))
        password = str(doc.get("password", ""))
        if not nombre or not email or len(password) < 8:
            return False, "Completa el nombre, el correo y una contraseña de 8 caracteres.", None
        if "@" not in email or "." not in email.split("@")[-1]:
            return False, "Ingresa un correo corporativo válido.", None
        sal, password_hash = _hash_password(password)
        nuevo = {
            "email": email,
            "nombre": nombre,
            "rol": "empresa",
            "activo": True,
            "salt": sal,
            "password_hash": password_hash,
            "created_at": ahora_iso(),
        }
        try:
            self.usuarios.insert_one(nuevo)
        except DuplicateKeyError:
            return False, "Ya existe un usuario con ese correo.", None
        return True, "Administrador registrado correctamente.", {
            "email": email, "nombre": nombre, "rol": "empresa",
        }

    # Vendedores --------------------------------------------------------
    def listar_vendedores(self) -> list[dict]:
        return [
            dict(x)
            for x in self.vendedores.find({}, {"_id": 0}).sort("nombre", ASCENDING)
        ]

    def listar_solicitudes_registro(self) -> list[dict]:
        ahora = int(time.time())
        cursor = (
            self.solicitudes_registro.find(
                {"estado": "pendiente", "expira_epoch": {"$gt": ahora}},
                {"_id": 0},
            )
            .sort("created_at", DESCENDING)
        )
        return [dict(doc) for doc in cursor]

    def descartar_solicitud_registro(self, solicitud_id: str) -> bool:
        resultado = self.solicitudes_registro.update_one(
            {"solicitud_id": solicitud_id, "estado": "pendiente"},
            {"$set": {"estado": "descartado", "descartado_at": ahora_iso()}},
        )
        return resultado.modified_count > 0

    def buscar_vendedor(self, identificador: str) -> dict | None:
        cedula_norm = normalizar_cedula(identificador)
        codigo_norm = normalizar_codigo(identificador)
        vendedor_obj = self.vendedores.find_one(
            {"$or": [{"cedula_norm": cedula_norm}, {"codigo_norm": codigo_norm}]},
            {"_id": 0},
        )
        return dict(vendedor_obj) if vendedor_obj else None

    def siguiente_codigo_vendedor(self) -> str:
        numero = self.vendedores.count_documents({}) + 1
        while True:
            codigo = f"MD-VEN-{numero:03d}"
            if not self.vendedores.find_one({"codigo_norm": normalizar_codigo(codigo)}):
                return codigo
            numero += 1

    def crear_vendedor(self, doc: dict) -> tuple[bool, str, dict | None]:
        cedula_norm = normalizar_cedula(doc.get("cedula", ""))
        if not doc.get("nombre") or not cedula_norm:
            return False, "Nombre y cédula son obligatorios.", None
        if self.vendedores.find_one({"cedula_norm": cedula_norm}):
            return False, "Ya existe un vendedor con esa cédula.", None
        codigo = doc.get("codigo") or self.siguiente_codigo_vendedor()
        if self.vendedores.find_one({"codigo_norm": normalizar_codigo(codigo)}):
            return False, "El código de vendedor ya existe.", None
        nuevo = {
            "codigo": codigo,
            "codigo_norm": normalizar_codigo(codigo),
            "nombre": limpiar_texto(doc["nombre"]),
            "cedula": limpiar_texto(doc.get("cedula", "")),
            "cedula_norm": cedula_norm,
            "telefono": limpiar_texto(doc.get("telefono", "")),
            "ciudad": limpiar_texto(doc.get("ciudad", "")),
            "email": limpiar_texto(doc.get("email", "")).lower(),
            "foto_b64": doc.get("foto_b64", ""),
            "estado": "Activo",
            "created_at": ahora_iso(),
            "origen": "manual",
        }
        try:
            self.vendedores.insert_one(nuevo)
        except DuplicateKeyError:
            return False, "Ya existe un vendedor con esa cédula o código.", None
        nuevo.pop("_id", None)
        return True, "Vendedor creado correctamente.", nuevo

    def actualizar_vendedor(self, doc: dict) -> tuple[bool, str, dict | None]:
        codigo = str(doc.get("codigo", "")).strip()
        cedula_norm = normalizar_cedula(doc.get("cedula", ""))
        if not doc.get("nombre") or not cedula_norm:
            return False, "Nombre y cédula son obligatorios.", None
        otro = self.vendedores.find_one({"cedula_norm": cedula_norm, "codigo": {"$ne": codigo}})
        if otro:
            return False, "Otra persona ya tiene esa cédula.", None
        cambios = {
            "nombre": str(doc.get("nombre", "")).strip(),
            "cedula": limpiar_texto(doc.get("cedula", "")),
            "cedula_norm": cedula_norm,
            "telefono": limpiar_texto(doc.get("telefono", "")),
            "ciudad": limpiar_texto(doc.get("ciudad", "")),
            "email": limpiar_texto(doc.get("email", "")).lower(),
            "estado": str(doc.get("estado", "Activo")),
            "updated_at": ahora_iso(),
        }
        if "foto_b64" in doc:
            cambios["foto_b64"] = doc.get("foto_b64", "")
        resultado = self.vendedores.update_one({"codigo": codigo}, {"$set": cambios})
        if resultado.matched_count == 0:
            return False, "No se encontró el vendedor.", None
        actualizado = self.vendedores.find_one({"codigo": codigo}, {"_id": 0})
        return True, "Vendedor actualizado.", dict(actualizado) if actualizado else None

    def eliminar_vendedor(self, codigo: str) -> tuple[bool, str]:
        resultado = self.vendedores.delete_one({"codigo": codigo})
        if resultado.deleted_count:
            return True, "Vendedor eliminado."
        return False, "No se encontró el vendedor."

    # Inventario --------------------------------------------------------
    def listar_inventario(self) -> list[dict]:
        cursor = (
            self.inventario.find({}, {"_id": 0})
            .sort([("descripcion", ASCENDING), ("codigo", ASCENDING)])
            .collation({"locale": "es", "strength": 1})
        )
        return [dict(x) for x in cursor]

    def resumen_inventario(self) -> dict:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "marcas": {"$addToSet": "$marca"},
                    "con_foto": {
                        "$sum": {
                            "$cond": [
                                {"$ne": [
                                    {"$ifNull": ["$foto_b64", ""]}, ""
                                ]},
                                1,
                                0,
                            ]
                        }
                    },
                    "valor_lista": {
                        "$sum": {"$ifNull": ["$precio", 0]}
                    },
                }
            }
        ]
        documento = next(self.inventario.aggregate(pipeline), None)
        if not documento:
            return {"total": 0, "marcas": 0, "con_foto": 0,
                    "valor_lista": 0.0}
        marcas = {
            str(m).strip() for m in documento.get("marcas", [])
            if str(m or "").strip()
        }
        try:
            valor = float(documento.get("valor_lista", 0) or 0)
        except (TypeError, ValueError):
            valor = 0.0
        return {
            "total": int(documento.get("total", 0) or 0),
            "marcas": len(marcas),
            "con_foto": int(documento.get("con_foto", 0) or 0),
            "valor_lista": valor,
        }

    def _filtro_inventario(self, busqueda: str = "") -> dict:
        texto = str(busqueda or "").strip()
        if not texto:
            return {}
        patron = re.escape(texto)
        return {
            "$or": [
                {"codigo": {"$regex": patron, "$options": "i"}},
                {"descripcion": {"$regex": patron, "$options": "i"}},
                {"marca": {"$regex": patron, "$options": "i"}},
            ]
        }

    def contar_inventario_filtrado(self, busqueda: str = "") -> int:
        return self.inventario.count_documents(self._filtro_inventario(busqueda))

    def listar_inventario_pagina(self, skip: int = 0, limit: int = 20,
                                 busqueda: str = "") -> list[dict]:
        inicio = max(0, int(skip))
        cantidad = max(1, min(200, int(limit)))
        proyeccion = {
            "_id": 0,
            "codigo": 1,
            "descripcion": 1,
            "marca": 1,
            "precio": 1,
            "categoria": 1,
            "familia": 1,
        }
        cursor = (
            self.inventario.find(self._filtro_inventario(busqueda), proyeccion)
            .sort([("descripcion", ASCENDING), ("codigo", ASCENDING)])
            .collation({"locale": "es", "strength": 1})
            .skip(inicio)
            .limit(cantidad)
        )
        return [dict(x) for x in cursor]

    def listar_referencias_ocr(self) -> list[dict]:
        cursor = self.inventario.find(
            {}, {"_id": 0, "codigo": 1, "descripcion": 1, "marca": 1}
        )
        return [dict(x) for x in cursor]


    def buscar_repuesto(self, codigo: str) -> dict | None:
        buscado = limpiar_texto(codigo).upper()
        if not buscado:
            return None
        documento = self.inventario.find_one({"codigo": buscado}, {"_id": 0})
        if documento:
            return dict(documento)
        documento = self.inventario.find_one(
            {"codigo": {"$regex": f"^{re.escape(buscado)}$", "$options": "i"}},
            {"_id": 0},
        )
        return dict(documento) if documento else None

    def existe_repuesto(self, codigo: str) -> bool:
        buscado = limpiar_texto(codigo).upper()
        if not buscado:
            return False
        if self.inventario.find_one({"codigo": buscado}, {"_id": 1}):
            return True
        return self.inventario.find_one(
            {"codigo": {"$regex": f"^{re.escape(buscado)}$", "$options": "i"}},
            {"_id": 1},
        ) is not None

    def guardar_repuesto(self, doc: dict) -> tuple[bool, str]:
        codigo = limpiar_texto(doc.get("codigo", "")).upper()
        descripcion = limpiar_texto(doc.get("descripcion", ""))
        marca = limpiar_texto(doc.get("marca", ""))
        if not codigo or not descripcion or not marca:
            return False, "Código, descripción y marca son obligatorios."
        try:
            precio = float(doc.get("precio", 0))
        except (TypeError, ValueError):
            return False, "El precio debe ser numérico."
        if precio <= 0:
            return False, "El precio debe ser mayor que cero."

        existente = self.buscar_repuesto(codigo)
        categoria = categoria_canonica(
            doc.get("categoria", (existente or {}).get("categoria", ""))
        )
        familia = familia_canonica(
            doc.get("familia", (existente or {}).get("familia", "")), categoria
        )
        actualizado = {
            "codigo": codigo,
            "descripcion": descripcion,
            "marca": marca,
            "categoria": categoria,
            "familia": familia,
            "precio": round(precio, 2),
            "foto_b64": doc.get("foto_b64", (existente or {}).get("foto_b64", "")),
            "ocr_text": doc.get("ocr_text", (existente or {}).get("ocr_text", "")),
            "updated_at": ahora_iso(),
        }
        try:
            resultado = self.inventario.update_one(
                {"codigo": codigo},
                {
                    "$set": actualizado,
                    "$setOnInsert": {"created_at": ahora_iso()},
                },
                upsert=True,
            )
        except DuplicateKeyError:
            return False, "Ya existe un repuesto con ese código."
        return True, "Repuesto actualizado." if resultado.matched_count else "Repuesto creado."

    def importar_repuestos(self, docs: list[dict], on_progress=None) -> tuple[int, int, list[str]]:
        insertados = 0
        actualizados = 0
        errores = []
        total = len(docs)
        for indice, doc in enumerate(docs, start=1):
            existente = self.existe_repuesto(doc.get("codigo", ""))
            ok, mensaje = self.guardar_repuesto(doc)
            if not ok:
                errores.append(f"{doc.get('codigo', '?')}: {mensaje}")
            elif existente:
                actualizados += 1
            else:
                insertados += 1
            if on_progress is not None:
                try:
                    on_progress(indice, total, insertados, actualizados)
                except Exception:
                    pass
        return insertados, actualizados, errores

    def actualizar_foto(self, codigo: str, foto_b64: str, ocr_text: str = "") -> bool:
        resultado = self.inventario.update_one(
            {"codigo": codigo},
            {"$set": {
                "foto_b64": foto_b64,
                "ocr_text": ocr_text,
                "updated_at": ahora_iso(),
            }},
        )
        return resultado.matched_count > 0

    def eliminar_repuesto(self, codigo: str) -> bool:
        resultado = self.inventario.delete_one({"codigo": codigo})
        return resultado.deleted_count > 0

    def contar_inventario(self) -> int:
        return self.inventario.count_documents({})

    def contar_vendedores(self) -> int:
        return self.vendedores.count_documents({})

    # Pedidos -----------------------------------------------------------
    def listar_pedidos(self) -> list[dict]:
        return [
            dict(x)
            for x in self.pedidos.find({}, {"_id": 0}).sort(
                [("fecha", -1), ("pedido_id", -1)]
            )
        ]

    def actualizar_estado_pedido(self, pedido_id: str, estado: str) -> bool:
        resultado = self.pedidos.update_one(
            {"pedido_id": pedido_id},
            {"$set": {"estado": estado, "updated_at": ahora_iso()}},
        )
        return resultado.matched_count > 0

    def contar_pedidos(self) -> int:
        return self.pedidos.count_documents({})


# ---------------------------------------------------------------------------
# Fachada de base de datos
# ---------------------------------------------------------------------------


class Database:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.uri = uri or _leer_uri()
        self.db_name = (
            db_name
            or os.getenv("MONGO_DB", "").strip()
            or os.getenv("MONGODB_DB", "").strip()
            or DEFAULT_DB
        )
        self.modo = "fallback"
        self.error = ""
        self.error_legible = ""
        self.store = MemoryStore()
        self._conectar()

    def _conectar(self, timeout_ms: int | None = None):
        if not PYMONGO_DISPONIBLE:
            self.modo = "fallback"
            self.error = "pymongo no está instalado"
            self.error_legible = "pymongo no está instalado. Se usa respaldo local."
            return
        try:
            mongo = MongoStore(
                self.uri,
                self.db_name,
                timeout_ms=timeout_ms or _timeout_conexion(self.uri),
            )
            self.store = mongo
            self.modo = "mongodb"
            self.error = ""
            self.error_legible = ""
        except Exception as exc:  # conexión, autenticación o permisos
            self.modo = "fallback"
            self.error = f"{type(exc).__name__}: {exc}"
            self.error_legible = _mensaje_conexion(exc, self.uri)
            self.store = MemoryStore()

    def reconectar(self) -> tuple[bool, str]:
        """Nuevo intento manual con un margen mayor para redes lentas."""
        self._conectar(timeout_ms=max(12000, _timeout_conexion(self.uri)))
        if self.modo == "mongodb":
            return True, "MongoDB conectado correctamente."
        return False, self.error_legible

    # Delegaciones ------------------------------------------------------
    def __getattr__(self, nombre):
        return getattr(self.store, nombre)

    @property
    def conectado(self) -> bool:
        return self.modo == "mongodb"

    @property
    def estado_texto(self) -> str:
        if self.conectado:
            return f"MongoDB · {self.db_name}"
        return "Modo respaldo local"

    @property
    def detalle_estado(self) -> str:
        if self.conectado:
            return f"Conectado a {uri_visible(self.uri)}"
        return self.error_legible or "Usando datos en memoria."

    @property
    def uri_visible(self) -> str:
        return uri_visible(self.uri)


_DATABASE: Database | None = None


def get_database() -> Database:
    global _DATABASE
    if _DATABASE is None:
        _DATABASE = Database()
    return _DATABASE


def reset_database_instance() -> None:
    """Útil para probar una nueva URI en caliente."""
    global _DATABASE
    _DATABASE = None
