"""
Mayorix · Dashboard de la Empresa
=================================
Resumen ejecutivo calculado exclusivamente con los datos reales de MongoDB.
Sin pedidos, ventas ni inventario, todas las métricas se muestran en cero.
"""

from __future__ import annotations

from datetime import date

import flet as ft

import data
from database import normalizar_texto
from . import ui


ESTADOS_ACTIVOS = ("Pendiente", "En revisión", "Aprobado", "En despacho")


def _estado_orden(estado: str):
    return ui.ESTADOS_PEDIDO.get(estado, (ui.MUTED, ui.SOFT_2, ft.Icons.CIRCLE))


def _pid(pedido) -> str:
    return str(pedido.get("pedido_id") or pedido.get("id") or "—")


def _fecha_partes(fecha: str) -> tuple[int, int] | None:
    try:
        anio, mes, _ = str(fecha).split("-")
        return int(anio), int(mes)
    except (ValueError, AttributeError):
        return None


def _mes_desplazado(anio: int, mes: int, offset: int) -> tuple[int, int]:
    total = anio * 12 + (mes - 1) + offset
    return total // 12, total % 12 + 1


def _monto(valor: float) -> str:
    return ui.money(valor, 2) if abs(float(valor or 0)) < 10_000 else ui.compacto(valor)


def resumen_operativo(db) -> dict:
    """Datos mínimos para el dashboard y la barra lateral."""
    try:
        pedidos = db.listar_pedidos()
    except Exception:
        pedidos = []
    return {
        "pedidos": pedidos,
        "pendientes": len([p for p in pedidos
                           if p.get("estado") in ("Pendiente", "En revisión")]),
        "activos": len([p for p in pedidos if p.get("estado") in ESTADOS_ACTIVOS]),
    }


def _resumen(db) -> dict:
    operativo = resumen_operativo(db)
    pedidos = operativo["pedidos"]
    try:
        inventario = db.resumen_inventario()
    except Exception:
        inventario = {"total": 0, "marcas": 0, "con_foto": 0,
                      "valor_lista": 0.0}
    try:
        vendedores = db.listar_vendedores()
    except Exception:
        vendedores = []

    hoy = data.HOY
    ventas_mes = 0.0
    validos_mes = 0
    cxc = 0.0
    por_estado = {estado: 0 for estado in ui.ESTADOS_PEDIDO}
    for pedido in pedidos:
        estado = pedido.get("estado", "Pendiente")
        por_estado[estado] = por_estado.get(estado, 0) + 1
        partes = _fecha_partes(pedido.get("fecha", ""))
        total = float(pedido.get("total", 0) or 0)
        if estado != "Rechazado" and partes == (hoy.year, hoy.month):
            ventas_mes += total
            validos_mes += 1
        if (estado in ("Aprobado", "En despacho", "Entregado")
                and "credito" in normalizar_texto(pedido.get("condicion", ""))):
            cxc += total

    valores = [
        float(p.get("total", 0) or 0)
        for p in pedidos if p.get("estado") != "Rechazado"
    ]
    ticket = sum(valores) / len(valores) if valores else 0.0

    serie = []
    for offset in range(-6, 1):
        anio, mes = _mes_desplazado(hoy.year, hoy.month, offset)
        valor = sum(
            float(p.get("total", 0) or 0)
            for p in pedidos
            if p.get("estado") != "Rechazado"
            and _fecha_partes(p.get("fecha", "")) == (anio, mes)
        )
        serie.append({"mes": data.MESES[mes - 1], "valor": valor})

    return {
        **operativo,
        "inventario": inventario,
        "vendedores": vendedores,
        "ventas_mes": ventas_mes,
        "validos_mes": validos_mes,
        "cxc": cxc,
        "ticket": ticket,
        "serie": serie,
        "por_estado": por_estado,
        "vencido": 0.0,
    }


def _fila_pedido(pedido, on_click) -> ft.Container:
    color, bg, icono = _estado_orden(pedido.get("estado", "Pendiente"))
    nombre = pedido.get("cliente_nombre") or data.nombre_cliente(
        pedido.get("cliente_id", "")
    )
    return ft.Container(
        content=ft.Row(
            [
                ui.icon_box(icono, color, bg, 30, 14, 8),
                ft.Column(
                    [
                        ui.txt(_pid(pedido), 11, ui.INK, ui.W_600,
                               max_lines=1),
                        ui.txt(f"{nombre} · {ui.fecha_corta(pedido.get('fecha', ''))}",
                               9.3, ui.MUTED, max_lines=1),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.Column(
                    [
                        ui.txt(ui.money(pedido.get("total", 0), 2), 10.5, ui.INK,
                               ui.W_600),
                        ui.pill(pedido.get("estado", "Pendiente"), color, bg, size=8),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=4, vertical=6),
        border_radius=7,
        on_click=lambda e, p=pedido: on_click(p),
        ink=True,
    )


def dashboard_view(app) -> ft.Control:
    db = app.db
    resumen = _resumen(db)
    inventario = resumen["inventario"]
    total_repuestos = int(inventario.get("total", 0) or 0)
    marcas = int(inventario.get("marcas", 0) or 0)
    con_foto = int(inventario.get("con_foto", 0) or 0)
    valor_lista = float(inventario.get("valor_lista", 0) or 0)
    vendedores = resumen["vendedores"]
    pedidos = resumen["pedidos"]
    ventas_mes = resumen["ventas_mes"]
    total_pedidos = len(pedidos)
    recientes = sorted(
        pedidos, key=lambda p: p.get("fecha", ""), reverse=True
    )[:5]

    acciones = [
        ui.secondary_button("Actualizar", ft.Icons.REFRESH,
                            lambda e: (app.refresh(),
                                       app.toast("Panel actualizado.", "info"))),
        ui.primary_button("Revisar pedidos", ft.Icons.RECEIPT_LONG_OUTLINED,
                          lambda e: app.navigate("pedidos")),
    ]

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------
    kpis = ft.Row(
        [
            ui.kpi_card(
                "Ventas del mes", _monto(ventas_mes),
                ft.Icons.POINT_OF_SALE, ui.TEAL, ui.TEAL_SOFT,
                trend="sin movimientos" if ventas_mes == 0
                else f"{resumen['validos_mes']} pedidos",
                trend_icon=ft.Icons.TRENDING_UP,
                note="USD del mes",
            ),
            ui.kpi_card(
                "Pedidos activos", str(resumen["activos"]),
                ft.Icons.SHOPPING_BAG_OUTLINED, ui.BLUE, ui.BLUE_SOFT,
                trend=f"{resumen['pendientes']} por revisar",
                trend_icon=ft.Icons.VISIBILITY_OUTLINED,
                trend_color=ui.BLUE, trend_bg=ui.BLUE_SOFT,
                note="de la red",
            ),
            ui.kpi_card(
                "Cuentas por cobrar", _monto(resumen["cxc"]),
                ft.Icons.ACCOUNT_BALANCE_OUTLINED, ui.ORANGE, ui.ORANGE_SOFT,
                trend="sin saldos" if resumen["cxc"] == 0 else "crédito otorgado",
                trend_icon=ft.Icons.WARNING_AMBER_ROUNDED,
                trend_color=ui.ORANGE, trend_bg=ui.ORANGE_SOFT,
                note="crédito · USD",
            ),
            ui.kpi_card(
                "Repuestos en catálogo", str(total_repuestos),
                ft.Icons.CAR_REPAIR, ui.PURPLE, ui.PURPLE_SOFT,
                trend=f"{marcas} marcas", trend_icon=ft.Icons.SELL_OUTLINED,
                trend_color=ui.PURPLE, trend_bg=ui.PURPLE_SOFT,
                note="en MongoDB",
            ),
        ],
        spacing=14,
    )

    # ------------------------------------------------------------------
    # Ventas y pedidos por estado
    # ------------------------------------------------------------------
    ventas_card = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Ventas de la red", 15.5, ui.INK, ui.W_600),
                                ui.txt("Últimos 7 meses · USD",
                                       11, ui.MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ui.pill(
                            f"{data.MESES[data.HOY.month - 1]} · {ui.money(ventas_mes, 2)}",
                            ui.TEAL, ui.TEAL_SOFT, icon=ft.Icons.TRENDING_UP,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                ui._bar_chart(resumen["serie"]),
                ft.Divider(height=1, color=ui.BORDER),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Pedidos válidos", 9.5, ui.MUTED),
                                ui.txt(str(
                                    len([p for p in pedidos
                                         if p.get("estado") != "Rechazado"])
                                ), 12, ui.INK, ui.W_600),
                            ],
                            spacing=1, expand=1,
                        ),
                        ft.Column(
                            [
                                ui.txt("Ticket promedio", 9.5, ui.MUTED),
                                ui.txt(ui.money(resumen["ticket"], 2), 12, ui.INK,
                                       ui.W_600),
                            ],
                            spacing=1, expand=1,
                        ),
                        ft.Column(
                            [
                                ui.txt("Total histórico", 9.5, ui.MUTED),
                                ui.txt(ui.money(
                                    sum(float(p.get("total", 0) or 0)
                                        for p in pedidos
                                        if p.get("estado") != "Rechazado"), 2),
                                    12, ui.INK, ui.W_600),
                            ],
                            spacing=1, expand=1,
                        ),
                    ],
                    spacing=12,
                ),
                ui.txt(
                    "Aún no hay ventas registradas. Los pedidos aprobados de la "
                    "red aparecerán aquí." if total_pedidos == 0
                    else "Métricas calculadas con los pedidos reales de MongoDB.",
                    9.3, ui.MUTED, max_lines=2,
                ),
            ],
            spacing=13,
        ),
        padding=18,
        expand=1,
    )

    por_estado = resumen["por_estado"]
    total_estados = sum(por_estado.values())
    segmentos = ft.Row(
        [
            ft.Container(
                expand=max(1, cantidad),
                height=9,
                bgcolor=_estado_orden(estado)[0],
                border_radius=5,
                tooltip=f"{estado}: {cantidad}",
            )
            for estado, cantidad in por_estado.items()
            if cantidad > 0
        ],
        spacing=3,
    ) if total_estados else ft.Container(
        height=9, bgcolor=ui.SOFT_2, border_radius=5,
    )

    leyenda = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(width=7, height=7, bgcolor=_estado_orden(estado)[0],
                                 border_radius=4),
                    ui.txt(estado, 11, "#475569", ui.W_500, expand=True),
                    ui.txt(str(cantidad), 11.5, ui.INK, ui.W_600),
                    ui.txt(f"{cantidad / total_estados * 100:.0f}%"
                           if total_estados else "0%", 9.5, ui.MUTED, ui.W_500),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for estado, cantidad in por_estado.items()
        ],
        spacing=7,
    )

    estados_card = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ui.txt("Pedidos por estado", 14.5, ui.INK, ui.W_600, expand=True),
                        ui.pill(f"{total_estados} total", ui.MUTED, ui.SOFT_2),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                segmentos,
                leyenda,
                ft.Divider(height=1, color=ui.BORDER),
                ft.Row(
                    [
                        ui.text_button("Gestionar pedidos", ft.Icons.ARROW_FORWARD,
                                       lambda e: app.navigate("pedidos"), size=11),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=11,
        ),
        padding=17,
    )

    cobranza_card = ft.Container(
        content=ft.Row(
            [
                ui.icon_box(
                    ft.Icons.CHECK_CIRCLE_OUTLINE
                    if resumen["cxc"] == 0 else ft.Icons.PRIORITY_HIGH_OUTLINED,
                    ui.TEAL if resumen["cxc"] == 0 else ui.ORANGE,
                    ui.TEAL_SOFT if resumen["cxc"] == 0 else "#FFEDD5",
                    34, 17, 8,
                ),
                ft.Column(
                    [
                        ui.txt(
                            "Sin cuentas por cobrar" if resumen["cxc"] == 0
                            else "Cobranza pendiente",
                            12,
                            "#0F766E" if resumen["cxc"] == 0 else "#9A3412",
                            ui.W_600,
                        ),
                        ui.txt(
                            "Los pedidos a crédito aparecerán aquí."
                            if resumen["cxc"] == 0 else
                            f"{_monto(resumen['cxc'])} en pedidos a crédito",
                            10.5,
                            ui.MUTED if resumen["cxc"] == 0 else "#C2410C",
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ui.TEAL_SOFT if resumen["cxc"] == 0 else ui.ORANGE_SOFT,
        border=ft.Border.all(
            1, ui.TEAL_BORDER if resumen["cxc"] == 0 else ui.ORANGE_BORDER),
        border_radius=10,
        padding=12,
    )

    columna_derecha = ft.Column([estados_card, cobranza_card], spacing=14, expand=1)

    # ------------------------------------------------------------------
    # Operación
    # ------------------------------------------------------------------
    inventario_card = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Inventario conectado", 14.5, ui.INK, ui.W_600),
                                ui.txt("Catálogo de repuestos", 10.5,
                                       ui.MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ui.pill(
                            db.estado_texto,
                            ui.TEAL if db.conectado else ui.ORANGE,
                            ui.TEAL_SOFT if db.conectado else ui.ORANGE_SOFT,
                            size=8.5,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ui.mini_stat("Repuestos", str(total_repuestos), "en catálogo",
                                     ft.Icons.CAR_REPAIR, ui.TEAL, ui.TEAL_SOFT),
                        ui.mini_stat("Marcas", str(marcas), "fabricantes",
                                     ft.Icons.SELL_OUTLINED, ui.BLUE, ui.BLUE_SOFT),
                        ui.mini_stat("Con foto", str(con_foto), "OCR asociado",
                                     ft.Icons.IMAGE_SEARCH_OUTLINED, ui.ORANGE,
                                     ui.ORANGE_SOFT),
                    ],
                    spacing=10,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.PRICE_CHECK_OUTLINED, size=15,
                                    color=ui.TEAL),
                            ui.txt("Precio de lista acumulado", 10.5, ui.MUTED,
                                   expand=True),
                            ui.txt(ui.money(valor_lista, 2), 12, ui.INK, ui.W_700),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=ui.SOFT,
                    border=ft.Border.all(1, ui.BORDER),
                    border_radius=8,
                    padding=10,
                ),
                ft.Row(
                    [
                        ui.text_button("Abrir inventario", ft.Icons.ARROW_FORWARD,
                                       lambda e: app.navigate("inventario"), size=11),
                        ft.Container(expand=True),
                        ui.text_button("Importar Excel/PDF",
                                       ft.Icons.UPLOAD_FILE_OUTLINED,
                                       lambda e: app.navigate("inventario"), size=11),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=11,
        ),
        padding=17,
        expand=1,
    )

    pedidos_host = ft.Column(spacing=0)
    for pedido in recientes:
        pedidos_host.controls.append(_fila_pedido(
            pedido, lambda p: app.navigate("pedidos")))
    if not recientes:
        pedidos_host.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.REQUEST_QUOTE_OUTLINED, size=26,
                                color=ui.MUTED_2),
                        ui.txt("Aún no hay pedidos recibidos", 10.5, ui.MUTED),
                        ui.text_button("Ir a la bandeja", ft.Icons.ARROW_FORWARD,
                                       lambda e: app.navigate("pedidos"), size=10),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=18,
                alignment=ui.ALIGN_CENTER,
            )
        )

    pedidos_card = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ui.txt("Pedidos recientes", 14.5, ui.INK, ui.W_600, expand=True),
                        ui.pill(f"{resumen['pendientes']} por revisar",
                                ui.ORANGE, ui.ORANGE_SOFT, size=8.5),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                pedidos_host,
                ft.Divider(height=1, color=ui.BORDER),
                ft.Row(
                    [
                        ui.text_button("Ver bandeja completa", ft.Icons.ARROW_FORWARD,
                                       lambda e: app.navigate("pedidos"), size=11),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=6,
        ),
        padding=17,
        expand=1,
    )

    # ------------------------------------------------------------------
    # Red comercial
    # ------------------------------------------------------------------
    vendedores_host = ft.Column(spacing=8)
    for vendedor_obj in vendedores[:4]:
        nombre = vendedor_obj.get("nombre", "Vendedor")
        vendedores_host.controls.append(
            ft.Row(
                [
                    ui.avatar(nombre, ui.TEAL, 32),
                    ft.Column(
                        [
                            ui.txt(nombre, 11, ui.INK, ui.W_600, max_lines=1),
                            ui.txt(
                                f"{vendedor_obj.get('codigo', '—')} · "
                                f"{vendedor_obj.get('ciudad', 'Venezuela')}",
                                9, ui.MUTED, max_lines=1,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ui.pill(vendedor_obj.get("estado", "Activo"),
                            ui.TEAL, ui.TEAL_SOFT, size=8),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    if not vendedores:
        vendedores_host.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.BADGE_OUTLINED, size=26, color=ui.MUTED_2),
                        ui.txt("Aún no hay vendedores registrados", 10.5, ui.MUTED),
                        ui.text_button("Crear vendedor", ft.Icons.PERSON_ADD_ALT_1,
                                       lambda e: app.navigate("vendedores"), size=10),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=16,
                alignment=ui.ALIGN_CENTER,
            )
        )

    vendedores_card = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Red comercial", 14.5, ui.INK, ui.W_600),
                                ui.txt(f"{len(vendedores)} vendedores",
                                       10.5, ui.MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ui.pill("Activa" if vendedores else "Sin registros",
                                ui.TEAL if vendedores else ui.MUTED,
                                ui.TEAL_SOFT if vendedores else ui.SOFT_2,
                                dot=bool(vendedores), size=8.5),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                vendedores_host,
                ft.Divider(height=1, color=ui.BORDER),
                ft.Row(
                    [
                        ui.text_button("Gestionar vendedores", ft.Icons.ARROW_FORWARD,
                                       lambda e: app.navigate("vendedores"), size=11),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=9,
        ),
        padding=17,
        expand=1,
    )

    # ------------------------------------------------------------------
    # Actividad real
    # ------------------------------------------------------------------
    actividad_host = ft.Column(spacing=0)
    for pedido in recientes[:4]:
        color, bg, icono = _estado_orden(pedido.get("estado", "Pendiente"))
        nombre = pedido.get("cliente_nombre") or data.nombre_cliente(
            pedido.get("cliente_id", "")
        )
        actividad_host.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ui.icon_box(icono, color, bg, 30, 14, 8),
                        ft.Column(
                            [
                                ui.txt(f"Pedido {_pid(pedido)}",
                                       10.5, ui.INK, ui.W_600, max_lines=1),
                                ui.txt(f"{nombre} · {pedido.get('estado', '')}",
                                       9.3, ui.MUTED, max_lines=1),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ui.txt(ui.money(pedido.get("total", 0), 2), 9.5, ui.INK,
                               ui.W_500),
                    ],
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(vertical=5),
            )
        )
    if not recientes:
        actividad_host.controls.append(
            ft.Container(
                content=ui.txt("Sin actividad registrada.", 10, ui.MUTED),
                padding=ft.Padding.symmetric(vertical=16),
                alignment=ui.ALIGN_CENTER,
            )
        )

    actividad_card = ui.card(
        ft.Column(
            [
                ui.txt("Actividad reciente", 14.5, ui.INK, ui.W_600),
                actividad_host,
            ],
            spacing=6,
        ),
        padding=17,
    )

    return ft.Column(
        [
            ui.page_header(
                "Panel de administración",
                "Resumen operativo y financiero de Mayor Disluda.",
                acciones,
                eyebrow="MAYORIX · EMPRESA",
            ),
            kpis,
            ft.Row([ventas_card, columna_derecha], spacing=14,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([inventario_card, pedidos_card], spacing=14,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([vendedores_card, actividad_card], spacing=14,
                   vertical_alignment=ft.CrossAxisAlignment.START),
        ],
        spacing=16,
    )
