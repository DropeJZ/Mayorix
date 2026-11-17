"""
Mayorix Vendedor · Acceso directo a MongoDB Atlas
=================================================
Esta capa se ejecuta dentro del APK y se conecta a Atlas por internet.
Incluye catálogo, pedidos, autenticación por cédula y registro con código.

La URI del clúster vive en `atlas_config.py` (generado al compilar el APK
preconfigurado) y no se pide al usuario en ningún momento.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
import unicodedata
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

PASSWORD_ITERATIONS = 160000
CODIGO_TTL_SEGUNDOS = 10 * 60
MAX_INTENTOS_CODIGO = 5
SESSION_TTL_DIAS = 30
DB_POR_DEFECTO = "mayorix"

# TLS tolerante para redes móviles: algunos operadores interceptan el
# certificado del clúster y rompen la validación de la cadena. Desactivar la
# validación reduce la seguridad (riesgo de intermediario), por eso se puede
# volver al modo estricto con MAYORIX_TLS_ESTRICTO=1 en el entorno.
TLS_TOLERANTE = os.getenv("MAYORIX_TLS_ESTRICTO", "").strip() != "1"


def opciones_conexion() -> dict:
    """Opciones comunes de pymongo, con TLS tolerante en redes móviles."""
    opciones: dict = {"tls": True}
    if TLS_TOLERANTE:
        opciones["tlsAllowInvalidCertificates"] = True
    return opciones


def leer_uri_configurada() -> str:
    """URI fija del clúster Atlas, incluida en el APK desde atlas_config.py."""
    try:
        from atlas_config import MONGO_URI
    except ImportError:
        return ""
    return str(MONGO_URI or "").strip()


def leer_db_configurada() -> str:
    return (
        os.getenv("MONGO_DB", "").strip()
        or os.getenv("MONGODB_DB", "").strip()
        or DB_POR_DEFECTO
    )


def limpiar_texto(valor) -> str:
    return re.sub(r"\s+", " ", str(valor or "")).strip()


def normalizar_texto(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def normalizar_cedula(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def ahora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


class MobileStore:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.uri = (uri or leer_uri_configurada()).strip()
        self.db_name = db_name or leer_db_configurada()
        self.client = None
        self.db = None
        self.inventario = None
        self.pedidos = None
        self.vendedores = None
        self.accesos = None
        self.solicitudes = None
        self.sesiones = None
        self._indices_listos = False
        self._connection_error = ""
        if self.uri:
            try:
                self._conectar()
            except Exception as exc:
                self._connection_error = str(exc)
                self.client = None
                self.db = None
                self.inventario = None
                self.pedidos = None
                self.vendedores = None
                self.accesos = None
                self.solicitudes = None
                self.sesiones = None

    @property
    def configurado(self) -> bool:
        return bool(self.uri)

    def _asegurar_conexion(self) -> None:
        if self.client is not None and self.vendedores is not None:
            return
        if not self.uri:
            raise ValueError(
                "La aplicación no tiene configurada una URI de MongoDB."
            )
        try:
            self._conectar()
            self._connection_error = ""
        except Exception as exc:
            self._connection_error = str(exc)
            self.client = None
            self.db = None
            self.inventario = None
            self.pedidos = None
            self.vendedores = None
            self.accesos = None
            self.solicitudes = None
            self.sesiones = None
            raise ValueError(
                "No se pudo conectar con MongoDB Atlas. Revisa la red del "
                "teléfono y la lista de acceso del clúster."
            ) from exc

    def _conectar(self):
        self.client = MongoClient(
            self.uri,
            **opciones_conexion(),
            serverSelectionTimeoutMS=9000,
            connectTimeoutMS=9000,
            socketTimeoutMS=20000,
            appname="MayorixVendedor",
        )
        self.db = self.client[self.db_name]
        self.inventario = self.db["inventario"]
        self.pedidos = self.db["pedidos"]
        self.vendedores = self.db["vendedores"]
        self.accesos = self.db["accesos_vendedor"]
        self.solicitudes = self.db["solicitudes_registro"]
        self.sesiones = self.db["sesiones_movil"]

    @property
    def conectado(self) -> bool:
        if self.client is None:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except PyMongoError:
            return False

    def asegurar_indices(self) -> None:
        if self._indices_listos or self.accesos is None:
            return
        try:
            self.accesos.create_index([("email", ASCENDING)], unique=True)
            self.accesos.create_index(
                [("cedula_norm", ASCENDING)], unique=True, sparse=True
            )
            self.solicitudes.create_index(
                [("cedula_norm", ASCENDING), ("estado", ASCENDING),
                 ("created_at", DESCENDING)]
            )
            self.solicitudes.create_index(
                [("codigo", ASCENDING)], unique=True, name="codigo_1"
            )
            self.solicitudes.create_index(
                [("expira_en", ASCENDING)], expireAfterSeconds=0,
                name="expira_ttl",
            )
            self.pedidos.create_index(
                [("vendedor_id", ASCENDING), ("fecha", DESCENDING)]
            )
            self.inventario.create_index([("codigo", ASCENDING)], unique=True)
            self.inventario.create_index([("descripcion", ASCENDING)])
            self.sesiones.create_index(
                [("token_hash", ASCENDING)], unique=True
            )
            self.sesiones.create_index(
                [("vendedor_codigo", ASCENDING), ("activo", ASCENDING)]
            )
            self.sesiones.create_index(
                [("expira_en", ASCENDING)], expireAfterSeconds=0,
                name="sesion_ttl",
            )
        except PyMongoError:
            pass
        self._indices_listos = True

    # ------------------------------------------------------------------
    # Vendedores y accesos
    # ------------------------------------------------------------------

    def buscar_vendedor_por_cedula(self, cedula: str) -> dict | None:
        self._asegurar_conexion()
        norm = normalizar_cedula(cedula)
        if len(norm) < 5:
            return None
        vendedor = self.vendedores.find_one(
            {"cedula_norm": norm},
            {"_id": 0, "codigo": 1, "nombre": 1, "cedula": 1,
             "cedula_norm": 1, "telefono": 1, "ciudad": 1, "estado": 1},
        )
        if not vendedor:
            vendedor = self.vendedores.find_one(
                {"cedula": {"$regex": f"^{re.escape(str(cedula).strip())}$",
                            "$options": "i"}},
                {"_id": 0, "codigo": 1, "nombre": 1, "cedula": 1,
                 "cedula_norm": 1, "telefono": 1, "ciudad": 1, "estado": 1},
            )
        if not vendedor:
            return None
        if not vendedor.get("cedula_norm"):
            vendedor["cedula_norm"] = normalizar_cedula(
                vendedor.get("cedula", "")
            )
        return vendedor

    def _acceso_de(self, vendedor: dict) -> dict | None:
        norm = vendedor.get("cedula_norm") or normalizar_cedula(
            vendedor.get("cedula", "")
        )
        acceso = self.accesos.find_one(
            {"cedula_norm": norm, "activo": True}
        )
        if not acceso:
            acceso = self.accesos.find_one(
                {"vendedor_codigo": vendedor.get("codigo", ""),
                 "activo": True}
            )
        return acceso

    def autenticar_vendedor(self, cedula: str, password: str) -> dict:
        vendedor = self.buscar_vendedor_por_cedula(cedula)
        if not vendedor:
            raise ValueError(
                "La cédula no está registrada por la administración."
            )
        if normalizar_texto(vendedor.get("estado", "Activo")) not in (
            "activo", "activa"
        ):
            raise ValueError("El vendedor no está activo en la red comercial.")
        acceso = self._acceso_de(vendedor)
        if not acceso:
            raise ValueError(
                "Aún no tienes acceso móvil. Usa “Primer registro”."
            )
        if not verificar_password(
            password,
            acceso.get("salt", ""),
            acceso.get("password_hash", ""),
        ):
            raise ValueError("Cédula o contraseña incorrectas.")
        self.asegurar_indices()
        return self._vendedor_publico(vendedor)

    # ------------------------------------------------------------------
    # Sesiones persistentes del dispositivo
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def crear_sesion(self, vendedor: dict) -> dict:
        self._asegurar_conexion()
        self.asegurar_indices()
        token = secrets.token_urlsafe(48)
        ahora = datetime.now(timezone.utc)
        expira = ahora + timedelta(days=SESSION_TTL_DIAS)
        documento = {
            "token_hash": self._hash_token(token),
            "vendedor_codigo": vendedor.get("codigo", ""),
            "cedula_norm": vendedor.get("cedula_norm", ""),
            "nombre": vendedor.get("nombre", ""),
            "activo": True,
            "creado_en": ahora.isoformat(timespec="seconds"),
            "ultima_actividad": ahora.isoformat(timespec="seconds"),
            "expira_en": expira,
            "expira_epoch": int(expira.timestamp()),
            "origen": "android",
        }
        self.sesiones.insert_one(documento)
        return {
            "token": token,
            "expira_epoch": documento["expira_epoch"],
            "vendor": self._vendedor_publico(vendedor),
        }

    def validar_sesion(self, token: str) -> dict | None:
        self._asegurar_conexion()
        if not token:
            return None
        ahora = int(time.time())
        sesion = self.sesiones.find_one(
            {"token_hash": self._hash_token(token), "activo": True}
        )
        if not sesion:
            return None
        if int(sesion.get("expira_epoch", 0)) < ahora:
            self.sesiones.update_one(
                {"_id": sesion["_id"]},
                {"$set": {"activo": False, "revocado_en": ahora_iso()}},
            )
            return None
        vendedor = self.vendedores.find_one(
            {"codigo": sesion.get("vendedor_codigo", "")},
            {"_id": 0, "codigo": 1, "nombre": 1, "cedula": 1,
             "cedula_norm": 1, "telefono": 1, "ciudad": 1, "estado": 1},
        )
        if not vendedor or normalizar_texto(
            vendedor.get("estado", "Activo")
        ) not in ("activo", "activa"):
            self._revocar_documento(sesion)
            return None
        if not self._acceso_de(vendedor):
            self._revocar_documento(sesion)
            return None
        self.sesiones.update_one(
            {"_id": sesion["_id"]},
            {"$set": {"ultima_actividad": ahora_iso()}},
        )
        return self._vendedor_publico(vendedor)

    def _revocar_documento(self, sesion: dict) -> None:
        try:
            self.sesiones.update_one(
                {"_id": sesion["_id"]},
                {"$set": {"activo": False, "revocado_en": ahora_iso()}},
            )
        except PyMongoError:
            pass

    def revocar_sesion(self, token: str) -> None:
        if not token or self.client is None:
            return
        self.sesiones.update_one(
            {"token_hash": self._hash_token(token)},
            {"$set": {"activo": False, "revocado_en": ahora_iso()}},
        )

    def revocar_sesiones_vendedor(self, vendedor_codigo: str) -> None:
        if not vendedor_codigo or self.client is None:
            return
        self.sesiones.update_many(
            {"vendedor_codigo": vendedor_codigo, "activo": True},
            {"$set": {"activo": False, "revocado_en": ahora_iso()}},
        )

    def estado_registro(self, cedula: str) -> dict:
        vendedor = self.buscar_vendedor_por_cedula(cedula)
        if not vendedor:
            raise ValueError(
                "La cédula no está registrada por la administración."
            )
        acceso = self._acceso_de(vendedor)
        if acceso:
            return {"vendedor": self._vendedor_publico(vendedor),
                    "tiene_acceso": True, "solicitud": None}
        pendiente = self.solicitudes.find_one(
            {
                "cedula_norm": vendedor["cedula_norm"],
                "estado": "pendiente",
                "expira_epoch": {"$gt": int(time.time())},
            },
            {"_id": 0, "solicitud_id": 1, "expira_epoch": 1,
             "created_at": 1},
            sort=[("created_at", DESCENDING)],
        )
        return {
            "vendedor": self._vendedor_publico(vendedor),
            "tiene_acceso": False,
            "solicitud": pendiente,
        }

    def crear_solicitud_registro(self, cedula: str) -> dict:
        self._asegurar_conexion()
        self.asegurar_indices()
        estado = self.estado_registro(cedula)
        vendedor = estado["vendedor"]
        if estado["tiene_acceso"]:
            raise ValueError(
                "Esta cédula ya tiene acceso móvil. Inicia sesión con tu "
                "contraseña."
            )
        if estado["solicitud"]:
            return {
                "vendedor": vendedor,
                "expira_epoch": estado["solicitud"]["expira_epoch"],
                "solicitud_id": estado["solicitud"]["solicitud_id"],
                "reutilizada": True,
            }

        ahora = int(time.time())
        recientes = self.solicitudes.count_documents({
            "cedula_norm": vendedor["cedula_norm"],
            "created_epoch": {"$gt": ahora - 900},
        })
        if recientes >= 3:
            raise ValueError(
                "Se generaron varios códigos recientemente. Espera 15 minutos "
                "o solicita ayuda al administrador."
            )

        codigo = ""
        for _ in range(20):
            candidato = f"{secrets.randbelow(900000) + 100000}"
            if not self.solicitudes.find_one({"codigo": candidato}):
                codigo = candidato
                break
        if not codigo:
            raise ValueError("No se pudo generar un código único. Intenta de nuevo.")

        expira_epoch = ahora + CODIGO_TTL_SEGUNDOS
        solicitud = {
            "solicitud_id": secrets.token_hex(8),
            "cedula_norm": vendedor["cedula_norm"],
            "vendedor_codigo": vendedor.get("codigo", ""),
            "nombre": vendedor.get("nombre", ""),
            "cedula": vendedor.get("cedula", ""),
            "codigo": codigo,
            "estado": "pendiente",
            "intentos": 0,
            "created_at": ahora_iso(),
            "created_epoch": ahora,
            "expira_epoch": expira_epoch,
            "expira_en": datetime.now(timezone.utc) + timedelta(
                seconds=CODIGO_TTL_SEGUNDOS
            ),
            "origen": "android",
        }
        try:
            self.solicitudes.insert_one(solicitud)
        except DuplicateKeyError as exc:
            raise ValueError(
                "Hubo una solicitud simultánea. Intenta validar de nuevo."
            ) from exc
        return {
            "vendedor": vendedor,
            "expira_epoch": expira_epoch,
            "solicitud_id": solicitud["solicitud_id"],
            "reutilizada": False,
        }

    def confirmar_registro(self, cedula: str, codigo: str,
                           password: str) -> dict:
        self._asegurar_conexion()
        self.asegurar_indices()
        vendedor = self.buscar_vendedor_por_cedula(cedula)
        if not vendedor:
            raise ValueError("La cédula no está registrada.")
        if len(str(password or "")) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        norm = vendedor["cedula_norm"]
        solicitud = self.solicitudes.find_one(
            {"cedula_norm": norm, "estado": "pendiente"},
            sort=[("created_at", DESCENDING)],
        )
        if not solicitud:
            raise ValueError(
                "No hay una solicitud pendiente. Valida la cédula nuevamente."
            )
        if int(solicitud.get("expira_epoch", 0)) < int(time.time()):
            self.solicitudes.update_one(
                {"solicitud_id": solicitud["solicitud_id"]},
                {"$set": {"estado": "expirado"}},
            )
            raise ValueError("El código expiró. Genera uno nuevo.")
        if int(solicitud.get("intentos", 0)) >= MAX_INTENTOS_CODIGO:
            self.solicitudes.update_one(
                {"solicitud_id": solicitud["solicitud_id"]},
                {"$set": {"estado": "bloqueado"}},
            )
            raise ValueError(
                "Se superaron los intentos. Solicita un código nuevo."
            )
        if not hmac.compare_digest(
            str(codigo or "").strip(), str(solicitud.get("codigo", ""))
        ):
            intentos = int(solicitud.get("intentos", 0)) + 1
            self.solicitudes.update_one(
                {"solicitud_id": solicitud["solicitud_id"]},
                {"$set": {"intentos": intentos}},
            )
            restantes = MAX_INTENTOS_CODIGO - intentos
            raise ValueError(
                f"Código incorrecto. Intentos restantes: {max(0, restantes)}."
            )

        sal, digest = _hash_password(password)
        correo = f"{vendedor.get('codigo', 'vendedor').lower()}@movil.mayordisluda.local"
        existente = self.accesos.find_one({
            "$or": [
                {"cedula_norm": norm},
                {"vendedor_codigo": vendedor.get("codigo", "")},
            ]
        })
        datos = {
            "cedula_norm": norm,
            "vendedor_codigo": vendedor.get("codigo", ""),
            "nombre": vendedor.get("nombre", ""),
            "rol": "vendedor",
            "activo": True,
            "salt": sal,
            "password_hash": digest,
            "updated_at": ahora_iso(),
        }
        if existente:
            if not existente.get("email"):
                datos["email"] = correo
            self.accesos.update_one(
                {"_id": existente["_id"]}, {"$set": datos}
            )
        else:
            datos["email"] = correo
            datos["created_at"] = ahora_iso()
            self.accesos.insert_one(datos)
        self.revocar_sesiones_vendedor(vendedor.get("codigo", ""))
        self.solicitudes.update_one(
            {"solicitud_id": solicitud["solicitud_id"]},
            {"$set": {"estado": "usado", "usado_at": ahora_iso()}},
        )
        return self._vendedor_publico(vendedor)

    @staticmethod
    def _vendedor_publico(vendedor: dict) -> dict:
        return {
            "codigo": vendedor.get("codigo", ""),
            "nombre": vendedor.get("nombre", ""),
            "cedula": vendedor.get("cedula", ""),
            "cedula_norm": vendedor.get("cedula_norm", ""),
            "telefono": vendedor.get("telefono", ""),
            "ciudad": vendedor.get("ciudad", ""),
            "estado": vendedor.get("estado", "Activo"),
            "rol": "vendedor",
        }

    # ------------------------------------------------------------------
    # Catálogo paginado
    # ------------------------------------------------------------------

    @staticmethod
    def _filtro_catalogo(q: str = "") -> dict:
        texto = limpiar_texto(q)
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

    def catalogo(self, q: str = "", skip: int = 0, limit: int = 20) -> dict:
        self._asegurar_conexion()
        inicio = max(0, int(skip))
        cantidad = max(1, min(50, int(limit)))
        filtro = self._filtro_catalogo(q)
        total = self.inventario.count_documents(filtro)
        cursor = (
            self.inventario.find(
                filtro,
                {"_id": 0, "codigo": 1, "descripcion": 1, "marca": 1,
                 "precio": 1, "categoria": 1, "familia": 1},
            )
            .sort([("descripcion", ASCENDING), ("codigo", ASCENDING)])
            .collation({"locale": "es", "strength": 1})
            .skip(inicio)
            .limit(cantidad)
        )
        items = [
            {
                "codigo": doc.get("codigo", ""),
                "descripcion": doc.get("descripcion", ""),
                "marca": doc.get("marca", ""),
                "precio": float(doc.get("precio", 0) or 0),
                "categoria": doc.get("categoria", ""),
                "familia": doc.get("familia", ""),
            }
            for doc in cursor
        ]
        return {
            "items": items,
            "total": total,
            "skip": inicio,
            "limit": cantidad,
            "page": inicio // cantidad + 1,
            "pages": max(1, (total + cantidad - 1) // cantidad),
        }

    # ------------------------------------------------------------------
    # Pedidos
    # ------------------------------------------------------------------

    def crear_pedido(self, vendedor: dict, datos: dict) -> dict:
        self._asegurar_conexion()
        cliente = limpiar_texto(datos.get("cliente_nombre", ""))
        ciudad = limpiar_texto(datos.get("cliente_ciudad", ""))
        condicion = limpiar_texto(datos.get("condicion", "Contado"))
        tipo_doc = limpiar_texto(datos.get("tipo_doc", "Nota de entrega"))
        notas = limpiar_texto(datos.get("notas", ""))
        items_entrada = datos.get("items") or []
        if len(cliente) < 2:
            raise ValueError("Indica el nombre del cliente.")
        if not items_entrada:
            raise ValueError("El pedido no tiene repuestos.")
        cond_norm = normalizar_texto(condicion)
        if cond_norm not in ("contado", "credito 30 dias"):
            raise ValueError("Condición de pago no válida.")
        condicion = "Contado" if cond_norm == "contado" else "Crédito 30 días"
        tipo_norm = normalizar_texto(tipo_doc)
        if tipo_norm not in ("nota de entrega", "factura fiscal"):
            raise ValueError("Tipo de documento no válido.")
        tipo_doc = ("Nota de entrega" if tipo_norm == "nota de entrega"
                    else "Factura fiscal")

        solicitados = {}
        for item in items_entrada:
            codigo = limpiar_texto(item.get("codigo", "")).upper()
            try:
                cantidad = int(item.get("cantidad", 1))
            except (TypeError, ValueError):
                cantidad = 0
            if not codigo or cantidad < 1 or cantidad > 999:
                raise ValueError("Hay una línea con código o cantidad inválida.")
            solicitados[codigo] = solicitados.get(codigo, 0) + cantidad

        docs = self.inventario.find(
            {"codigo": {"$in": list(solicitados.keys())}},
            {"_id": 0, "codigo": 1, "descripcion": 1, "marca": 1, "precio": 1},
        )
        por_codigo = {str(d.get("codigo", "")).upper(): d for d in docs}
        faltantes = [c for c in solicitados if c not in por_codigo]
        if faltantes:
            raise ValueError(
                "Repuestos no disponibles: " + ", ".join(sorted(faltantes)[:5])
            )

        items = []
        subtotal = 0.0
        for codigo, cantidad in solicitados.items():
            doc = por_codigo[codigo]
            precio = float(doc.get("precio", 0) or 0)
            importe = round(precio * cantidad, 2)
            subtotal += importe
            items.append({
                "producto_id": codigo,
                "codigo": codigo,
                "descripcion": doc.get("descripcion", ""),
                "marca": doc.get("marca", ""),
                "cantidad": cantidad,
                "precio": round(precio, 2),
                "importe": importe,
            })
        subtotal = round(subtotal, 2)
        iva = round(subtotal * 0.16, 2) \
            if tipo_doc == "Factura fiscal" else 0.0
        total = round(subtotal + iva, 2)
        try:
            from rate import consultar_tasa
            tasa = float(consultar_tasa().get("tasa", 0) or 0)
        except Exception:
            try:
                from atlas_config import TASA_INICIAL
                tasa = float(TASA_INICIAL or 0)
            except Exception:
                tasa = 0.0
        fecha = datetime.now()
        vencimiento = ""
        if condicion == "Crédito 30 días":
            vencimiento = (fecha + timedelta(days=30)).date().isoformat()
        pedido = {
            "pedido_id": f"MD-{fecha:%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}",
            "cliente_id": "",
            "cliente_nombre": cliente,
            "cliente_ciudad": ciudad,
            "vendedor_id": vendedor.get("codigo", ""),
            "vendedor_nombre": vendedor.get("nombre", ""),
            "vendedor_zona": vendedor.get("ciudad", ""),
            "fecha": fecha.isoformat(timespec="seconds"),
            "estado": "Pendiente",
            "condicion": condicion,
            "tipo_doc": tipo_doc,
            "subtotal": subtotal,
            "iva": iva,
            "total": total,
            "tasa_bcv": tasa,
            "subtotal_ves": round(subtotal * tasa, 2),
            "total_ves": round(total * tasa, 2),
            "vencimiento": vencimiento,
            "notas": notas,
            "items": items,
            "origen": "app_vendedor",
            "created_at": ahora_iso(),
            "updated_at": ahora_iso(),
        }
        self.pedidos.insert_one(dict(pedido))
        return pedido

    def listar_pedidos(self, vendedor_codigo: str, limit: int = 100) -> list[dict]:
        self._asegurar_conexion()
        cursor = (
            self.pedidos.find({"vendedor_id": vendedor_codigo}, {"_id": 0})
            .sort([("fecha", DESCENDING), ("pedido_id", DESCENDING)])
            .limit(max(1, min(200, int(limit))))
        )
        return [dict(doc) for doc in cursor]

    def resumen_vendedor(self, vendedor_codigo: str) -> dict:
        self._asegurar_conexion()
        pipeline = [
            {"$match": {"vendedor_id": vendedor_codigo}},
            {"$group": {
                "_id": "$estado",
                "cantidad": {"$sum": 1},
                "total": {"$sum": {"$ifNull": ["$total", 0]}},
            }},
        ]
        por_estado = {}
        total = 0.0
        cantidad = 0
        for fila in self.pedidos.aggregate(pipeline):
            estado = fila.get("_id") or "Pendiente"
            por_estado[estado] = int(fila.get("cantidad", 0))
            total += float(fila.get("total", 0) or 0)
            cantidad += int(fila.get("cantidad", 0))
        return {
            "total_pedidos": cantidad,
            "total_usd": round(total, 2),
            "por_estado": por_estado,
        }
