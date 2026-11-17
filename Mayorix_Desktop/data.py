"""
Mayorix · Configuración y utilidades de datos
=============================================
Este módulo ya no contiene datos de prueba. La información operativa vive
exclusivamente en MongoDB y se carga de forma manual desde los módulos de la
aplicación (inventario, vendedores y pedidos).
"""

from __future__ import annotations

from datetime import date

MONEDA = "$"
IVA = 0.16
HOY = date.today()
TASA_VES = 36.50
TASA_VES_FECHA = HOY.strftime("%d/%m/%Y")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGOS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

EMPRESA = {
    "nombre": "Mayor Disluda",
    "cliente": "Mayor Disluda",
    "desarrollador": "DropeTech",
    "rol": "Empresa · Administración central",
    "pais": "Venezuela",
    "moneda": "Dólares estadounidenses (USD)",
    "moneda_secundaria": "Bolívares (VES)",
    "tasa_ves": TASA_VES,
    "periodo": f"{MESES_LARGOS[HOY.month - 1]} {HOY.year}",
    "meta_mensual": 0.0,
}

# Categorías y familias del catálogo de repuestos.
CATEGORIA_SIN = "Sin categoría"
CATEGORIAS = [
    "Bujías y Cables",
    "Correas y Tensores",
    "Filtros",
    "Frenos",
    "Motor",
    "Suspensión y Dirección",
    "Transmisión y Embrague",
]
FAMILIAS = {
    "Bujías y Cables": ["Bujías", "Cables"],
    "Correas y Tensores": ["Correas", "Tensores"],
    "Filtros": ["Aceite", "Aire", "Combustible"],
    "Frenos": ["Pastillas", "Discos", "Bandas"],
    "Motor": ["Pistones", "Anillos", "Conchas", "Empacaduras"],
    "Suspensión y Dirección": ["Amortiguadores", "Rótulas", "Terminales", "Brazos"],
    "Transmisión y Embrague": ["Clutch", "Discos", "Collarines", "Cajas"],
}


def familias_de(categoria: str) -> list[str]:
    return FAMILIAS.get(categoria, [])


# Colecciones operativas: se llenan únicamente con datos reales.
PRODUCTOS: list[dict] = []
VENDEDORES: list[dict] = []
CLIENTES: list[dict] = []
PEDIDOS: list[dict] = []
FACTURAS_PENDIENTES: list[dict] = []
MOVIMIENTOS_BILLETERA: list[dict] = []
REPORTES: list[dict] = []
INGRESOS_MENSUALES: list[dict] = []
FINANZAS_PERIODOS: dict = {}
AGING_CARTERA: list[dict] = []
COMPOSICION_INGRESOS: list[dict] = []
ACTIVIDAD_RECIENTE: list[dict] = []
NOTIFICACIONES: list[dict] = []


# ---------------------------------------------------------------------------
# Utilidades de consulta (seguras ante datos vacíos)
# ---------------------------------------------------------------------------


def buscar(lista: list[dict], campo: str, valor):
    for elemento in lista:
        if elemento.get(campo) == valor:
            return elemento
    return None


def cliente(cliente_id: str) -> dict | None:
    return None


def vendedor(vendedor_id: str) -> dict | None:
    return None


def producto(producto_id: str) -> dict | None:
    return None


def pedido(pedido_id: str) -> dict | None:
    return None


def cliente_de(pedido_obj: dict) -> dict:
    return {}


def vendedor_de(pedido_obj: dict) -> dict:
    return {}


def nombre_cliente(cliente_id: str) -> str:
    return "Cliente"


def nombre_vendedor(vendedor_id: str) -> str:
    return "Sin asignar"


def clientes_de_vendedor(vendedor_id: str) -> list[dict]:
    return []


def pedidos_de_cliente(cliente_id: str) -> list[dict]:
    return []


def registrar_actividad(*args, **kwargs) -> None:
    """Reservado para auditoría futura; no genera datos simulados."""


def registrar_movimiento(*args, **kwargs) -> None:
    """Reservado para movimientos de billetera; no genera datos simulados."""


def recalcular_ventas() -> None:
    """Sin datos derivados en memoria: las métricas se calculan desde MongoDB."""
