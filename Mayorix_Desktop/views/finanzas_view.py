"""
Mayorix · Finanzas
==================
Control financiero central calculado en tiempo real desde la colección de
pedidos: ingresos reconocidos, cuentas por cobrar, ticket promedio y
transacciones de la red comercial.
"""

from __future__ import annotations

from datetime import date

import flet as ft

import data
from database import normalizar_texto
from . import ui


ESTADOS_RECONOCIDOS = ("Aprobado", "En despacho", "Entregado")
PERIODOS = [("mes", "Este mes"), ("trimestre", "3 meses"),
            ("anio", "Este año"), ("todo", "Histórico")]


def _mes_offset(anio: int, mes: int, offset: int) -> tuple[int, int]:
    total = anio * 12 + (mes - 1) + offset
    return total // 12, total % 12 + 1


def _fecha(fecha: str) -> date | None:
    try:
        anio, mes, dia = str(fecha).split("-")
        return date(int(anio), int(mes), int(dia))
    except (ValueError, AttributeError):
        return None


def _pid(pedido) -> str:
    return str(pedido.get("pedido_id") or pedido.get("id") or "—")


def _cliente(pedido) -> str:
    return pedido.get("cliente_nombre") or "Cliente sin registrar"


def _en_periodo(pedido, periodo: str, hoy: date) -> bool:
    fecha = _fecha(pedido.get("fecha", ""))
    if fecha is None:
        return False
    if periodo == "mes":
        return (fecha.year, fecha.month) == (hoy.year, hoy.month)
    if periodo == "trimestre":
        limite = _mes_offset(hoy.year, hoy.month, -2)
        return (fecha.year, fecha.month) >= limite
    if periodo == "anio":
        return fecha.year == hoy.year
    return True


def finanzas_view(app) -> ft.Control:
    db = app.db
    hoy = data.HOY
    estado = {"periodo": "mes", "cargando": False}

    try:
        pedidos = db.listar_pedidos()
        error_db = ""
    except Exception as exc:
        pedidos = []
        error_db = str(exc)

    kpis_host = ft.Row(spacing=14)
    grafico_host = ft.Column(spacing=0)
    estados_host = ft.Column(spacing=7)
    tabla_host = ft.Column(spacing=0)
    chips_host = ft.Row(spacing=6, wrap=True)
    resumen_host = ft.Column(spacing=0)

    def _credito(pedido) -> bool:
        return "credito" in normalizar_texto(pedido.get("condicion", ""))

    def _cxc() -> tuple[float, int]:
        deuda = sum(
            float(p.get("total", 0) or 0)
            for p in pedidos
            if _credito(p) and p.get("estado") in ESTADOS_RECONOCIDOS
        )
        cantidad = len([
            p for p in pedidos
            if _credito(p) and p.get("estado") in ESTADOS_RECONOCIDOS
        ])
        return deuda, cantidad

    def _serie() -> list[dict]:
        serie = []
        for offset in range(-6, 1):
            anio, mes = _mes_offset(hoy.year, hoy.month, offset)
            valor = sum(
                float(p.get("total", 0) or 0)
                for p in pedidos
                if p.get("estado") in ESTADOS_RECONOCIDOS
                and (_fecha(p.get("fecha", "")) or date(1900, 1, 1)).year == anio
                and (_fecha(p.get("fecha", "")) or date(1900, 1, 1)).month == mes
            )
            serie.append({"mes": data.MESES[mes - 1], "valor": valor})
        return serie

    def _periodo_actual() -> list[dict]:
        return [p for p in pedidos
                if _en_periodo(p, estado["periodo"], hoy)
                and p.get("estado") != "Rechazado"]

    def _render_chips():
        chips_host.controls = [
            ui.filter_chip(
                etiqueta,
                estado["periodo"] == clave,
                lambda e, c=clave: _seleccionar(c),
            )
            for clave, etiqueta in PERIODOS
        ]

    def _seleccionar(periodo: str):
        estado["periodo"] = periodo
        render()
        app.page.update()

    def _kpi(etiqueta, valor, nota, icono, accent, bg):
        return ui.kpi_card(etiqueta, valor, icono, accent, bg, note=nota)

    def render():
        seleccion = _periodo_actual()
        reconocidos = [p for p in seleccion if p.get("estado") in ESTADOS_RECONOCIDOS]
        ingresos = sum(float(p.get("total", 0) or 0) for p in reconocidos)
        ticket = ingresos / len(reconocidos) if reconocidos else 0.0
        cxc, cantidad_cxc = _cxc()

        kpis_host.controls = [
            _kpi("Ingresos del periodo", ui.money(ingresos, 2),
                 "pedidos aprobados y despachados", ft.Icons.TRENDING_UP,
                 ui.TEAL, ui.TEAL_SOFT),
            _kpi("Cuentas por cobrar", ui.money(cxc, 2),
                 f"{cantidad_cxc} pedidos a crédito", ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                 ui.ORANGE, ui.ORANGE_SOFT),
            _kpi("Ticket promedio", ui.money(ticket, 2),
                 f"{len(reconocidos)} pedidos reconocidos", ft.Icons.RECEIPT_LONG_OUTLINED,
                 ui.BLUE, ui.BLUE_SOFT),
            _kpi("Pedidos del periodo", str(len(seleccion)),
                 "sin rechazados", ft.Icons.SHOPPING_BAG_OUTLINED,
                 ui.PURPLE, ui.PURPLE_SOFT),
        ]

        serie = _serie()
        total_serie = sum(item["valor"] for item in serie)
        grafico_host.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ui.txt("Ingresos reconocidos", 14.5, ui.INK, ui.W_600),
                            ui.txt("Últimos 7 meses · USD", 10.5, ui.MUTED),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ui.pill(f"{ui.money(total_serie, 2)} · 7 meses",
                            ui.TEAL, ui.TEAL_SOFT, size=9),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=4),
            ui._bar_chart(serie),
            ui.txt(
                "Aún no hay ingresos reconocidos." if total_serie == 0 else
                "Calculado con pedidos aprobados, en despacho y entregados.",
                9.3, ui.MUTED,
            ),
        ]

        por_estado = {}
        for pedido in seleccion:
            nombre_estado = pedido.get("estado", "Pendiente")
            por_estado[nombre_estado] = por_estado.get(nombre_estado, 0) + 1
        total_estados = max(1, len(seleccion))
        estados_host.controls = [
            ft.Row(
                [
                    ft.Container(width=7, height=7,
                                 bgcolor=ui.ESTADOS_PEDIDO.get(
                                     nombre, (ui.MUTED,))[0],
                                 border_radius=4),
                    ui.txt(nombre, 10.5, "#475569", ui.W_500, expand=True),
                    ui.txt(str(cantidad), 10.5, ui.INK, ui.W_600),
                    ui.txt(f"{cantidad / total_estados * 100:.0f}%", 9, ui.MUTED),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for nombre, cantidad in por_estado.items()
        ] or [ui.txt("Sin pedidos en el periodo.", 10, ui.MUTED)]

        transacciones = sorted(
            seleccion, key=lambda p: p.get("fecha", ""), reverse=True
        )[:12]
        tabla_host.controls = [
            ui.table_row(
                [
                    ui.cell(ui.txt(_pid(p), 10.3, ui.INK, ui.W_600), 1.8),
                    ui.cell(ui.txt(ui.fecha_corta(p.get("fecha", "")), 9.6,
                                    ui.MUTED), 1.5),
                    ui.cell(ui.txt(_cliente(p), 10, "#475569", ui.W_500,
                                    max_lines=1), 3.1),
                    ui.cell(ui.txt(p.get("tipo_doc", "—"), 9.6, "#475569"), 1.9),
                    ui.cell(ui.txt(ui.money(p.get("total", 0), 2), 10.3, ui.INK,
                                    ui.W_600), 1.7, ui.ALIGN_RIGHT),
                    ui.cell(ui.estado_pedido_pill(p.get("estado", "Pendiente")), 1.6),
                ],
                on_click=lambda e: app.navigate("pedidos"),
                padding_v=8,
            )
            for p in transacciones
        ] or [ui.empty_state("Sin transacciones en el periodo.",
                             ft.Icons.RECEIPT_LONG_OUTLINED)]

        resumen_host.controls = [
            ui.txt("Resumen", 10.5, ui.INK, ui.W_600),
            ft.Row(
                [
                    ui.txt("Total histórico", 9.5, ui.MUTED, expand=True),
                    ui.txt(ui.money(sum(
                        float(p.get("total", 0) or 0) for p in pedidos
                        if p.get("estado") != "Rechazado"), 2), 10.5, ui.INK,
                        ui.W_600),
                ]
            ),
            ft.Row(
                [
                    ui.txt("Pedidos registrados", 9.5, ui.MUTED, expand=True),
                    ui.txt(str(len(pedidos)), 10.5, ui.INK, ui.W_600),
                ]
            ),
            ft.Row(
                [
                    ui.txt("Cuentas por cobrar", 9.5, ui.MUTED, expand=True),
                    ui.txt(ui.money(cxc, 2), 10.5, ui.ORANGE, ui.W_600),
                ]
            ),
        ]
        _render_chips()

    _render_chips()
    render()

    tabla = ui.table_container(
        [
            {"label": "Pedido", "flex": 1.8},
            {"label": "Fecha", "flex": 1.5},
            {"label": "Cliente", "flex": 3.1},
            {"label": "Documento", "flex": 1.9},
            {"label": "Total USD", "flex": 1.7, "align": ui.ALIGN_RIGHT},
            {"label": "Estado", "flex": 1.6},
        ],
        tabla_host,
    )

    contenido = [
        ui.page_header(
            "Finanzas",
            "Ingresos, cuentas por cobrar y transacciones de la red.",
            [
                ui.secondary_button("Actualizar", ft.Icons.REFRESH,
                                    lambda e: (app.refresh(),
                                               app.toast("Finanzas actualizadas.",
                                                         "info"))),
            ],
            eyebrow="ANÁLISIS FINANCIERO",
        ),
        kpis_host,
        ft.Row(
            [
                ui.card(grafico_host, padding=17, expand=1),
                ui.card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ui.txt("Pedidos por estado", 13.5, ui.INK,
                                           ui.W_600, expand=True),
                                    ui.pill("Periodo", ui.MUTED, ui.SOFT_2,
                                            size=8.5),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            estados_host,
                            ft.Divider(height=1, color=ui.BORDER),
                            resumen_host,
                        ],
                        spacing=9,
                    ),
                    padding=17,
                    expand=1,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        chips_host,
        ui.card(
            ft.Column(
                [
                    ui.txt("Transacciones recientes", 13.5, ui.INK, ui.W_600),
                    tabla,
                ],
                spacing=8,
            ),
            padding=14,
        ),
    ]
    if error_db:
        contenido.insert(2, ui.info_box(
            f"No se pudieron cargar los pedidos: {error_db}",
            ui.RED, ui.RED_SOFT, "#FECACA", ft.Icons.ERROR_OUTLINE,
        ))
    return ft.Column(contenido, spacing=16)
