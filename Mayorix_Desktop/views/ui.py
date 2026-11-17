"""
Mayorix Desktop · Vistas e interacciones
========================================
Interfaz del rol Empresa / Administración Central. Cada vista se construye
con componentes reutilizables y opera sobre los datos simulados de data.py.
"""

from __future__ import annotations

from datetime import datetime

import flet as ft

import data

# ---------------------------------------------------------------------------
# Tokens de diseño
# ---------------------------------------------------------------------------

BG = "#F4F5F6"
WHITE = "#FFFFFF"
INK = "#24303A"
MUTED = "#68737D"
MUTED_2 = "#98A1AA"
BORDER = "#E4E7EA"
SOFT = "#F8F9FA"
SOFT_2 = "#F1F3F4"
TEAL = "#0F766E"
TEAL_DARK = "#115E59"
TEAL_SOFT = "#F3FAF8"
TEAL_BORDER = "#D5EDE8"
ORANGE = "#C2410C"
ORANGE_SOFT = "#FFF7ED"
ORANGE_BORDER = "#FED7AA"
BLUE = "#4B5A6B"
BLUE_SOFT = "#F4F6F8"
PURPLE = "#6B7280"
PURPLE_SOFT = "#F4F5F6"
RED = "#B91C1C"
RED_SOFT = "#FEF2F2"
GREEN = "#15803D"
GREEN_SOFT = "#F3FAF5"
SKY = "#0369A1"
SKY_SOFT = "#F3F8FC"

W_400 = ft.FontWeight.W_400
W_500 = ft.FontWeight.W_500
W_600 = ft.FontWeight.W_600
W_700 = ft.FontWeight.W_700

ALIGN_LEFT = ft.Alignment.CENTER_LEFT
ALIGN_RIGHT = ft.Alignment.CENTER_RIGHT
ALIGN_CENTER = ft.Alignment.CENTER

MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic"]

ESTADOS_PEDIDO = {
    "Pendiente": (ORANGE, ORANGE_SOFT, ft.Icons.SCHEDULE),
    "En revisión": (SKY, SKY_SOFT, ft.Icons.VISIBILITY_OUTLINED),
    "Aprobado": (TEAL, TEAL_SOFT, ft.Icons.CHECK_CIRCLE_OUTLINED),
    "En despacho": (PURPLE, PURPLE_SOFT, ft.Icons.LOCAL_SHIPPING_OUTLINED),
    "Entregado": (GREEN, GREEN_SOFT, ft.Icons.DONE_ALL),
    "Rechazado": (RED, RED_SOFT, ft.Icons.CANCEL_OUTLINED),
}

ESTADOS_CLIENTE = {
    "Activo": (TEAL, TEAL_SOFT),
    "En riesgo": (ORANGE, ORANGE_SOFT),
    "Suspendido": (RED, RED_SOFT),
}

ESTADOS_VENDEDOR = {
    "Activo": (TEAL, TEAL_SOFT),
    "Vacaciones": (BLUE, BLUE_SOFT),
    "Inactivo": (MUTED, SOFT_2),
}

ESTADOS_ACTIVIDAD = {
    "Pendiente": (ORANGE, ORANGE_SOFT),
    "En revisión": (SKY, SKY_SOFT),
    "Confirmado": (TEAL, TEAL_SOFT),
    "Aprobado": (TEAL, TEAL_SOFT),
    "Revisado": (MUTED, SOFT_2),
    "Disponible": (PURPLE, PURPLE_SOFT),
    "Revisar": (ORANGE, ORANGE_SOFT),
    "En despacho": (PURPLE, PURPLE_SOFT),
    "Entregado": (GREEN, GREEN_SOFT),
    "Rechazado": (RED, RED_SOFT),
    "Liquidado": (TEAL, TEAL_SOFT),
    "Aplicado": (MUTED, SOFT_2),
}

AMBER = "#D97706"
AMBER_SOFT = "#FFFBEB"

CATEGORIA_ESTILO = {
    "Frenos": ("#DC2626", "#FEF2F2", ft.Icons.TIRE_REPAIR),
    "Filtros": (BLUE, BLUE_SOFT, ft.Icons.FILTER_ALT),
    "Motor": (TEAL, TEAL_SOFT, ft.Icons.CAR_REPAIR),
    "Suspensión": (PURPLE, PURPLE_SOFT, ft.Icons.TUNE),
    "Eléctrico": (AMBER, AMBER_SOFT, ft.Icons.BOLT),
    "Lubricantes": (SKY, SKY_SOFT, ft.Icons.OIL_BARREL_OUTLINED),
}

CATEGORIA_SKU = {
    "Frenos": "FRN",
    "Filtros": "FIL",
    "Motor": "MOT",
    "Suspensión": "SUS",
    "Eléctrico": "ELE",
    "Lubricantes": "LUB",
}


# ---------------------------------------------------------------------------
# Helpers visuales
# ---------------------------------------------------------------------------


def txt(
    valor,
    size=13,
    color=INK,
    weight=None,
    align=ft.TextAlign.START,
    max_lines=None,
    expand=False,
):
    return ft.Text(
        value=str(valor),
        size=size,
        color=color,
        weight=weight,
        text_align=align,
        max_lines=max_lines,
        overflow=ft.TextOverflow.ELLIPSIS if max_lines else ft.TextOverflow.CLIP,
        expand=expand,
    )


def money(valor, decimales=0):
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        numero = 0.0
    signo = "-" if numero < 0 else ""
    return f"{signo}$ {abs(numero):,.{decimales}f}"


def money_ves(valor, decimales=2):
    try:
        numero = float(valor or 0) * data.TASA_VES
    except (TypeError, ValueError):
        numero = 0.0
    signo = "-" if numero < 0 else ""
    return f"{signo}Bs. {abs(numero):,.{decimales}f}"


def monto_segun_moneda(valor_usd, moneda="USD", decimales=2):
    return money_ves(valor_usd, decimales) if moneda == "VES" else money(valor_usd, decimales)


def compacto(valor):
    numero = float(valor or 0)
    if abs(numero) >= 1_000_000:
        return f"$ {numero / 1_000_000:.2f}M"
    if abs(numero) >= 10_000:
        return f"$ {numero / 1_000:.1f}K"
    return money(numero)


def porcentaje(valor, decimales=0):
    return f"{valor:.{decimales}f}%"


def fecha_corta(iso):
    try:
        fecha = datetime.strptime(iso, "%Y-%m-%d")
        return f"{fecha.day} {MESES_CORTOS[fecha.month - 1]}"
    except (TypeError, ValueError):
        return str(iso)


def iniciales(nombre):
    partes = [p for p in str(nombre).replace(".", "").split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "MX"


def card(
    content,
    padding=18,
    expand=None,
    width=None,
    height=None,
    bgcolor=WHITE,
    border_color=BORDER,
    radius=10,
):
    return ft.Container(
        content=content,
        padding=padding,
        expand=expand,
        width=width,
        height=height,
        bgcolor=bgcolor,
        border=ft.Border.all(1, border_color),
        border_radius=radius,
    )


def pill(label, color=TEAL, bg=TEAL_SOFT, icon=None, dot=False, size=10.5):
    children = []
    if dot:
        children.append(ft.Container(width=6, height=6, border_radius=3, bgcolor=color))
    if icon is not None:
        children.append(ft.Icon(icon, size=12, color=color))
    children.append(txt(label, size, color, W_600))
    return ft.Container(
        content=ft.Row(children, spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=bg,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
    )


def icon_box(icono, color=TEAL, bg=TEAL_SOFT, size=36, icon_size=18, radius=8):
    return ft.Container(
        content=ft.Icon(icono, size=icon_size, color=color),
        width=size,
        height=size,
        bgcolor=bg,
        border_radius=radius,
        alignment=ALIGN_CENTER,
    )


def avatar(nombre, color=TEAL, size=36, font_size=None):
    return ft.Container(
        content=txt(
            iniciales(nombre),
            font_size or max(10, int(size * 0.33)),
            WHITE,
            W_700,
            align=ft.TextAlign.CENTER,
        ),
        width=size,
        height=size,
        bgcolor=color,
        border_radius=size / 2,
        alignment=ALIGN_CENTER,
    )


def barra(valor, color=TEAL, bg="#E2E8F0", height=6):
    return ft.ProgressBar(
        value=max(0.0, min(1.0, float(valor) / 100)),
        bar_height=height,
        color=color,
        bgcolor=bg,
        border_radius=height / 2,
    )


def primary_button(label, icon=None, on_click=None, width=None, height=40, disabled=False):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=15, color=WHITE))
    children.append(txt(label, 12.5, WHITE, W_600))
    return ft.Button(
        content=ft.Row(children, spacing=7, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click,
        bgcolor=TEAL,
        color=WHITE,
        elevation=0,
        width=width,
        height=height,
        disabled=disabled,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=14, vertical=0),
            overlay_color=ft.Colors.with_opacity(0.08, WHITE),
        ),
    )


def secondary_button(
    label,
    icon=None,
    on_click=None,
    width=None,
    height=40,
    color=INK,
    disabled=False,
):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=15, color=color))
    children.append(txt(label, 12.5, color, W_500))
    return ft.OutlinedButton(
        content=ft.Row(children, spacing=7, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click,
        width=width,
        height=height,
        disabled=disabled,
        style=ft.ButtonStyle(
            color=color,
            bgcolor=WHITE,
            side=ft.BorderSide(1, BORDER),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=13, vertical=0),
            overlay_color=ft.Colors.with_opacity(0.04, INK),
        ),
    )


def text_button(label, icon=None, on_click=None, color=TEAL, size=11.5, height=30):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=14, color=color))
    children.append(txt(label, size, color, W_600))
    return ft.TextButton(
        content=ft.Row(children, spacing=5, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click,
        height=height,
        style=ft.ButtonStyle(
            color=color,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.Padding.symmetric(horizontal=8, vertical=0),
            overlay_color=ft.Colors.with_opacity(0.05, color),
        ),
    )


def icon_button(icono, tooltip, on_click, color=MUTED, size=18):
    return ft.IconButton(
        icon=icono,
        icon_size=size,
        icon_color=color,
        tooltip=tooltip,
        on_click=on_click,
        style=ft.ButtonStyle(
            padding=6,
            shape=ft.RoundedRectangleBorder(radius=6),
            overlay_color=ft.Colors.with_opacity(0.05, INK),
        ),
    )


def _sincronizar_valor(e=None):
    """Fuerza el envío del valor del campo al servidor de Flet."""
    return None


def base_text_field(
    value="",
    hint="",
    on_change=None,
    password=False,
    multiline=False,
    max_length=None,
    on_submit=None,
):
    return ft.TextField(
        value=str(value),
        hint_text=hint,
        border=ft.InputBorder.NONE,
        text_size=13,
        color=INK,
        hint_style=ft.TextStyle(size=12.5, color=MUTED_2),
        cursor_color=TEAL,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=11),
        password=password,
        can_reveal_password=password,
        multiline=multiline,
        min_lines=3 if multiline else None,
        max_lines=5 if multiline else None,
        max_length=max_length,
        on_change=on_change or _sincronizar_valor,
        on_submit=on_submit,
        expand=True,
    )


def field_shell(label, control, width=None, expand=False):
    return ft.Column(
        [
            txt(label, 10.5, MUTED, W_600),
            ft.Container(
                content=control,
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=2, vertical=1),
            ),
        ],
        spacing=5,
        width=width,
        expand=expand,
    )


def labeled_field(
    label,
    value="",
    hint="",
    on_change=None,
    password=False,
    multiline=False,
    suffix=None,
    width=None,
    expand=False,
    on_submit=None,
):
    field = base_text_field(
        value=value,
        hint=hint,
        on_change=on_change,
        password=password,
        multiline=multiline,
        on_submit=on_submit,
    )
    if suffix is not None:
        field.suffix = ft.Text(suffix, size=11.5, color=MUTED)
        field.suffix_style = ft.TextStyle(size=11.5, color=MUTED)
    return field_shell(label, field, width=width, expand=expand)


def labeled_dropdown(
    label,
    options,
    value=None,
    on_select=None,
    width=None,
    expand=False,
):
    dropdown = ft.Dropdown(
        options=[ft.DropdownOption(key=k, text=v) for k, v in options],
        value=value,
        on_select=on_select,
        border=ft.InputBorder.NONE,
        text_size=12.5,
        text_style=ft.TextStyle(size=12.5, color=INK),
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        expand=True,
    )
    return field_shell(label, dropdown, width=width, expand=expand)


def search_input(placeholder, on_change=None, width=290):
    field = ft.TextField(
        hint_text=placeholder,
        border=ft.InputBorder.NONE,
        text_size=12.5,
        hint_style=ft.TextStyle(size=12.5, color=MUTED_2),
        cursor_color=TEAL,
        content_padding=ft.Padding.symmetric(horizontal=2, vertical=9),
        on_change=on_change,
        expand=True,
    )
    return ft.Container(
        content=ft.Row(
            [ft.Icon(ft.Icons.SEARCH, size=16, color=MUTED), field],
            spacing=7,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=width,
        height=40,
        padding=ft.Padding.symmetric(horizontal=11),
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
    )


def toolbar_dropdown(options, value, on_select, width=190):
    dropdown = ft.Dropdown(
        options=[ft.DropdownOption(key=k, text=v) for k, v in options],
        value=value,
        on_select=on_select,
        border=ft.InputBorder.NONE,
        text_size=12,
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=7),
        expand=True,
    )
    return ft.Container(
        content=dropdown,
        width=width,
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=ft.Padding.only(left=6, right=2),
        alignment=ALIGN_CENTER,
    )


def filter_chip(label, active, on_click, count=None):
    children = [txt(label, 11.5, WHITE if active else "#475569", W_600)]
    if count is not None:
        children.append(
            ft.Container(
                content=txt(count, 9.5, TEAL if active else MUTED, W_700),
                bgcolor=WHITE if active else "#E2E8F0",
                border_radius=9,
                padding=ft.Padding.symmetric(horizontal=5, vertical=1),
            )
        )
    return ft.Container(
        content=ft.Row(children, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=on_click,
        bgcolor=TEAL if active else WHITE,
        border=ft.Border.all(1, TEAL if active else BORDER),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=11, vertical=7),
        ink=True,
    )


def page_header(title, subtitle, actions=None, eyebrow=None):
    columna = []
    if eyebrow:
        columna.append(
            ft.Text(
                eyebrow,
                size=9.5,
                color=TEAL,
                weight=W_700,
                style=ft.TextStyle(letter_spacing=0.9),
            )
        )
    columna.extend([txt(title, 23, INK, W_700), txt(subtitle, 12.5, MUTED)])
    return ft.Row(
        [
            ft.Column(columna, spacing=3, expand=True),
            ft.Row(actions or [], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def section_header(title, subtitle=None, trailing=None):
    column = [txt(title, 15.5, INK, W_600)]
    if subtitle:
        column.append(txt(subtitle, 11.5, MUTED))
    return ft.Row(
        [ft.Column(column, spacing=2, expand=True), trailing or ft.Container()],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def table_header(columns):
    cells = []
    for col in columns:
        cells.append(
            ft.Container(
                content=ft.Text(
                    col["label"].upper(),
                    size=9.5,
                    color=MUTED_2,
                    weight=W_700,
                    style=ft.TextStyle(letter_spacing=0.6),
                ),
                expand=max(1, int(round(float(col.get("flex", 1)) * 10))),
                alignment=col.get("align", ALIGN_LEFT),
            )
        )
    return ft.Container(
        content=ft.Row(cells, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(horizontal=16, vertical=11),
        bgcolor=SOFT,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
    )


def cell(content, flex, align=ALIGN_LEFT):
    return ft.Container(
        content=content,
        expand=max(1, int(round(float(flex) * 10))),
        alignment=align,
    )


def table_row(cells, on_click=None, padding_v=11):
    row = ft.Row(cells, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor = ft.Container(
        content=row,
        padding=ft.Padding.symmetric(horizontal=16, vertical=padding_v),
        bgcolor=WHITE,
        border=ft.Border(bottom=ft.BorderSide(1, "#F1F5F9")),
        on_click=on_click,
    )
    if on_click is not None:
        def cambiar_hover(e, c=contenedor):
            c.bgcolor = SOFT if str(e.data).lower() == "true" else WHITE
            c.update()

        contenedor.on_hover = cambiar_hover
    return contenedor


def table_footer(content):
    return ft.Container(
        content=content,
        padding=ft.Padding.symmetric(horizontal=16, vertical=11),
        bgcolor="#FCFDFE",
        border=ft.Border(top=ft.BorderSide(1, BORDER)),
    )


def table_container(columns, rows_host, footer=None):
    children = [table_header(columns), rows_host]
    if footer is not None:
        children.append(footer)
    return ft.Container(
        content=ft.Column(children, spacing=0),
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def empty_state(mensaje, icono=ft.Icons.INBOX_OUTLINED):
    return ft.Container(
        content=ft.Column(
            [
                icon_box(icono, MUTED_2, SOFT_2, 44, 21),
                txt(mensaje, 12, MUTED, W_500),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=42),
        alignment=ALIGN_CENTER,
    )


def info_box(mensaje, color=BLUE, bg=BLUE_SOFT, border_color="#BFDBFE", icono=ft.Icons.INFO_OUTLINE):
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icono, size=16, color=color), txt(mensaje, 11, color, W_500, expand=True)],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=bg,
        border=ft.Border.all(1, border_color),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=11, vertical=9),
    )


def kpi_card(label, value, icono, accent=TEAL, bg=TEAL_SOFT, trend=None,
             trend_icon=None, trend_color=None, trend_bg=None, note=""):
    trend_color = trend_color or accent
    trend_bg = trend_bg or bg
    bottom = []
    if trend:
        bottom.append(pill(trend, trend_color, trend_bg, icon=trend_icon))
    if note:
        bottom.append(txt(note, 10.5, MUTED, W_400, max_lines=1, expand=True))
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        txt(label.upper(), 9.5, MUTED, W_700, max_lines=1, expand=True),
                        icon_box(icono, accent, bg, 32, 16, 8),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                txt(value, 22.5, INK, W_700, max_lines=1),
                ft.Row(bottom, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER) if bottom else ft.Container(),
            ],
            spacing=8,
        ),
        padding=15,
        expand=1,
        height=118,
    )


def mini_stat(label, value, sub, icono, accent=TEAL, bg=TEAL_SOFT):
    return card(
        ft.Row(
            [
                icon_box(icono, accent, bg, 34, 17, 8),
                ft.Column(
                    [
                        txt(label, 10, MUTED, W_500),
                        txt(value, 16, INK, W_700),
                        txt(sub, 9.5, MUTED, W_400, max_lines=1),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=13,
        expand=1,
    )


def doc_pill(tipo):
    if tipo == "Factura fiscal":
        return pill("Factura fiscal", TEAL, TEAL_SOFT, icon=ft.Icons.RECEIPT_LONG_OUTLINED)
    return pill("Nota de entrega", ORANGE, ORANGE_SOFT, icon=ft.Icons.LOCAL_SHIPPING_OUTLINED)


def estado_pedido_pill(estado):
    color, bg, icono = ESTADOS_PEDIDO.get(estado, (MUTED, SOFT_2, ft.Icons.CIRCLE))
    return pill(estado, color, bg, icon=icono)


def estado_cliente_pill(estado):
    color, bg = ESTADOS_CLIENTE.get(estado, (MUTED, SOFT_2))
    return pill(estado, color, bg, dot=True)


def estado_vendedor_pill(estado):
    color, bg = ESTADOS_VENDEDOR.get(estado, (MUTED, SOFT_2))
    return pill(estado, color, bg, dot=True)


def fecha_chip(texto, icono=ft.Icons.CALENDAR_MONTH_OUTLINED):
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icono, size=14, color=MUTED), txt(texto, 11, MUTED, W_500)],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=10, vertical=7),
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def _activity_style(tipo):
    estilos = {
        "pedido": (ft.Icons.SHOPPING_BAG_OUTLINED, TEAL, TEAL_SOFT),
        "pago": (ft.Icons.PAYMENTS_OUTLINED, BLUE, BLUE_SOFT),
        "cliente": (ft.Icons.PERSON_ADD_ALT_1, PURPLE, PURPLE_SOFT),
        "billetera": (ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, SKY, SKY_SOFT),
        "inventario": (ft.Icons.CAR_REPAIR, TEAL, TEAL_SOFT),
        "alerta": (ft.Icons.WARNING_AMBER_ROUNDED, ORANGE, ORANGE_SOFT),
    }
    return estilos.get(tipo, (ft.Icons.NOTIFICATIONS_NONE, MUTED, SOFT_2))


def _bar_chart(serie, height=126):
    maximo = max(1, max((item["valor"] for item in serie), default=0))
    columnas = []
    for indice, item in enumerate(serie):
        alto = max(7, item["valor"] / maximo * (height - 8))
        es_actual = indice == len(serie) - 1
        columnas.append(
            ft.Column(
                [
                    ft.Container(
                        content=ft.Container(
                            width=26,
                            height=alto,
                            bgcolor=TEAL if es_actual else "#99F6E4",
                            border_radius=5,
                            tooltip=f"{item['mes']}: {money(item['valor'])}",
                        ),
                        height=height,
                        alignment=ft.Alignment.BOTTOM_CENTER,
                    ),
                    txt(item["mes"], 10, MUTED, W_500),
                ],
                spacing=7,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=1,
            )
        )
    return ft.Row(columnas, spacing=8, vertical_alignment=ft.CrossAxisAlignment.END)


def clients_view(app):
    estado = {"q": "", "estado": "Todos"}
    rows_host = ft.Column(spacing=0)
    chips_host = ft.Row(spacing=6, wrap=True)
    footer_label = txt("", 10.5, MUTED)
    footer_total = txt("", 10.5, INK, W_600)

    limite_total = sum(c["limite"] for c in data.CLIENTES)
    saldo_total = sum(c["saldo"] for c in data.CLIENTES)
    utilizacion = (saldo_total / limite_total * 100) if limite_total else 0
    score_promedio = sum(c["score"] for c in data.CLIENTES) / len(data.CLIENTES)
    activos = len([c for c in data.CLIENTES if c["estado"] == "Activo"])

    def credito_celda(c):
        uso = (c["saldo"] / c["limite"] * 100) if c["limite"] else 0
        color = RED if uso >= 85 else (ORANGE if uso >= 65 else TEAL)
        return ft.Column(
            [
                ft.Row(
                    [
                        txt(money(c["limite"]), 10.5, INK, W_600),
                        txt(f"{uso:.0f}%", 9, MUTED, W_500),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                barra(min(100, uso), color, "#E2E8F0", 4),
            ],
            spacing=3,
        )

    def puntualidad_celda(c):
        score = c["score"]
        if score >= 85:
            color, bg = TEAL, TEAL_SOFT
        elif score >= 70:
            color, bg = ORANGE, ORANGE_SOFT
        else:
            color, bg = RED, RED_SOFT
        return pill(f"{score}%", color, bg, icon=ft.Icons.SPEED)

    def fila_cliente(c):
        vendedor = data.vendedor(c["vendedor_id"]) or {}
        return table_row(
            [
                cell(
                    ft.Row(
                        [
                            avatar(c["negocio"], TEAL if c["estado"] == "Activo" else (ORANGE if c["estado"] == "En riesgo" else RED), 32),
                            ft.Column(
                                [
                                    txt(c["negocio"], 11.5, INK, W_600, max_lines=1),
                                    txt(f"{c['tipo']} · {c['ciudad']}", 9.5, MUTED, W_400, max_lines=1),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=9,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    4,
                ),
                cell(
                    ft.Column(
                        [
                            txt(c["contacto"], 11, INK, W_500, max_lines=1),
                            txt(c["telefono"], 9.5, MUTED, W_400),
                        ],
                        spacing=1,
                    ),
                    2.8,
                ),
                cell(
                    ft.Column(
                        [
                            txt(vendedor.get("nombre", "Sin asignar"), 10.5, "#475569", W_500, max_lines=1),
                            txt(vendedor.get("zona", ""), 9.5, MUTED, W_400, max_lines=1),
                        ],
                        spacing=1,
                    ),
                    2.4,
                ),
                cell(credito_celda(c), 2.4),
                cell(
                    ft.Column(
                        [
                            txt(money(c["saldo"], 2), 11.5, INK, W_600),
                            txt("saldo actual", 9.5, MUTED, W_400),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    2,
                    ALIGN_RIGHT,
                ),
                cell(puntualidad_celda(c), 1.6),
                cell(estado_cliente_pill(c["estado"]), 1.7),
                cell(ft.Icon(ft.Icons.CHEVRON_RIGHT, size=17, color=MUTED_2), 0.7, ALIGN_RIGHT),
            ],
            on_click=lambda e, cliente=c: open_client_dialog(app, cliente),
            padding_v=9,
        )

    def render_chips():
        opciones = ["Todos", "Activo", "En riesgo", "Suspendido"]
        chips = []
        for opcion in opciones:
            cantidad = len(data.CLIENTES) if opcion == "Todos" else len(
                [c for c in data.CLIENTES if c["estado"] == opcion]
            )
            chips.append(
                filter_chip(
                    opcion,
                    estado["estado"] == opcion,
                    lambda e, valor=opcion: seleccionar_estado(valor),
                    count=cantidad,
                )
            )
        chips_host.controls = chips

    def seleccionar_estado(valor):
        estado["estado"] = valor
        render_chips()
        render()
        app.page.update()

    def render(update=False):
        q = estado["q"].strip().lower()
        filtrados = []
        for c in data.CLIENTES:
            coincide_estado = estado["estado"] == "Todos" or c["estado"] == estado["estado"]
            coincide_q = (
                q in c["negocio"].lower()
                or q in c["contacto"].lower()
                or q in c["ciudad"].lower()
                or q in c["id"].lower()
            )
            if coincide_estado and coincide_q:
                filtrados.append(c)
        rows_host.controls = [fila_cliente(c) for c in filtrados] or [
            empty_state("No encontramos clientes con esos filtros.", ft.Icons.PEOPLE_OUTLINE)
        ]
        footer_label.value = f"{len(filtrados)} de {len(data.CLIENTES)} clientes · {len([c for c in filtrados if c['estado'] == 'En riesgo'])} en riesgo"
        footer_total.value = f"Cartera filtrada: {money(sum(c['saldo'] for c in filtrados), 2)}"
        if update:
            app.page.update()

    def buscar(e):
        estado["q"] = e.control.value
        render(update=True)

    render_chips()
    render()

    toolbar = ft.Row(
        [
            search_input("Buscar negocio, contacto o ciudad…", buscar, width=300),
            chips_host,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )

    footer = table_footer(
        ft.Row([footer_label, ft.Container(expand=True), footer_total],
               vertical_alignment=ft.CrossAxisAlignment.CENTER)
    )

    tabla = table_container(
        [
            {"label": "Negocio", "flex": 4},
            {"label": "Contacto", "flex": 2.8},
            {"label": "Vendedor", "flex": 2.4},
            {"label": "Límite de crédito", "flex": 2.4},
            {"label": "Saldo actual", "flex": 2, "align": ALIGN_RIGHT},
            {"label": "Puntualidad", "flex": 1.6},
            {"label": "Estado", "flex": 1.7},
            {"label": "", "flex": 0.7, "align": ALIGN_RIGHT},
        ],
        rows_host,
        footer,
    )

    kpis = ft.Row(
        [
            kpi_card(
                "Clientes activos", str(activos), ft.Icons.PEOPLE_OUTLINE,
                TEAL, TEAL_SOFT, trend="+3 este mes", trend_icon=ft.Icons.TRENDING_UP,
                note=f"de {len(data.CLIENTES)} cuentas",
            ),
            kpi_card(
                "Límite otorgado", compacto(limite_total), ft.Icons.CREDIT_CARD_OUTLINED,
                BLUE, BLUE_SOFT, trend=f"{len(data.CLIENTES)} cuentas",
                trend_icon=ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                trend_color=BLUE, trend_bg=BLUE_SOFT, note="red comercial",
            ),
            kpi_card(
                "Cartera utilizada", porcentaje(utilizacion, 1), ft.Icons.DONUT_LARGE_OUTLINED,
                ORANGE, ORANGE_SOFT, trend=f"{compacto(saldo_total)}", trend_icon=ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                trend_color=ORANGE, trend_bg=ORANGE_SOFT, note="saldo pendiente",
            ),
            kpi_card(
                "Puntualidad promedio", porcentaje(score_promedio, 0), ft.Icons.SPEED,
                PURPLE, PURPLE_SOFT, trend="Excelente", trend_icon=ft.Icons.TRENDING_UP,
                trend_color=PURPLE, trend_bg=PURPLE_SOFT, note="score de pago",
            ),
        ],
        spacing=14,
    )

    return ft.Column(
        [
            page_header(
                "Clientes · Talleres y tiendas",
                "Cartera de talleres, tiendas y servicios de repuestos en Venezuela: crédito y comportamiento de pago.",
                [
                    secondary_button("Exportar cartera", ft.Icons.DOWNLOAD,
                                    lambda e: app.toast("Cartera de clientes exportada (demo).", "success")),
                ],
                eyebrow="RED COMERCIAL · VENEZUELA",
            ),
            kpis,
            toolbar,
            tabla,
        ],
        spacing=16,
    )


# ---------------------------------------------------------------------------
# Vendedores y billetera
# ---------------------------------------------------------------------------


def sellers_view(app):
    rows_host = ft.Column(spacing=0)
    saldo_total = sum(v["saldo_billetera"] for v in data.VENDEDORES)
    comision_total = sum(v["comision_mes"] for v in data.VENDEDORES)
    liquidado_total = sum(v["liquidado_mes"] for v in data.VENDEDORES)
    activos = len([v for v in data.VENDEDORES if v["estado"] == "Activo"])

    def fila_movimiento(m):
        vendedor = data.vendedor(m["vendedor_id"]) or {}
        colores = {
            "Comisión": (TEAL, TEAL_SOFT),
            "Liquidación": (BLUE, BLUE_SOFT),
            "Bono": (PURPLE, PURPLE_SOFT),
            "Ajuste": (ORANGE, ORANGE_SOFT),
        }
        color, bg = colores.get(m["tipo"], (MUTED, SOFT_2))
        return table_row(
            [
                cell(
                    ft.Row(
                        [
                            avatar(vendedor.get("nombre", "?"), vendedor.get("color", MUTED), 26, 9),
                            txt(vendedor.get("nombre", "—"), 10.5, INK, W_500, max_lines=1),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    2.7,
                ),
                cell(pill(m["tipo"], color, bg, size=9.5), 1.5),
                cell(txt(m["concepto"], 10.5, MUTED, W_400, max_lines=1), 4),
                cell(txt(fecha_corta(m["fecha"]), 10.5, MUTED, W_400), 1.2),
                cell(
                    txt(money(m["monto"], 2), 11, RED if m["monto"] < 0 else INK, W_600),
                    1.7,
                    ALIGN_RIGHT,
                ),
                cell(pill(m["estado"], TEAL if m["estado"] == "Disponible" else MUTED,
                          TEAL_SOFT if m["estado"] == "Disponible" else SOFT_2, size=9.5), 1.5),
            ],
            padding_v=9,
        )

    for movimiento in data.MOVIMIENTOS_BILLETERA[:8]:
        rows_host.controls.append(fila_movimiento(movimiento))

    movimientos = table_container(
        [
            {"label": "Vendedor", "flex": 2.7},
            {"label": "Tipo", "flex": 1.5},
            {"label": "Concepto", "flex": 4},
            {"label": "Fecha", "flex": 1.2},
            {"label": "Monto", "flex": 1.7, "align": ALIGN_RIGHT},
            {"label": "Estado", "flex": 1.5},
        ],
        rows_host,
        table_footer(
            ft.Row(
                [
                    txt(f"{len(data.MOVIMIENTOS_BILLETERA)} movimientos registrados", 10.5, MUTED),
                    ft.Container(expand=True),
                    txt(f"Disponible: {money(saldo_total, 2)}", 10.5, TEAL_DARK, W_600),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ),
    )

    tarjetas = []
    for vendedor in data.VENDEDORES:
        cumplimiento = (vendedor["ventas_mes"] / vendedor["meta_mes"] * 100) if vendedor["meta_mes"] else 0
        n_clientes = len(data.clientes_de_vendedor(vendedor["id"]))
        puede_liquidar = vendedor["saldo_billetera"] > 0
        tarjetas.append(
            card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                avatar(vendedor["nombre"], vendedor["color"], 38),
                                ft.Column(
                                    [
                                        txt(vendedor["nombre"], 12.5, INK, W_600, max_lines=1),
                                        txt(f"{vendedor['codigo']} · {vendedor['zona']}", 9.5, MUTED, W_400, max_lines=1),
                                    ],
                                    spacing=1,
                                    expand=True,
                                ),
                                estado_vendedor_pill(vendedor["estado"]),
                            ],
                            spacing=9,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=13, color=MUTED_2),
                                txt(f"{n_clientes} clientes asignados", 9.5, MUTED, W_500),
                                ft.Container(expand=True),
                                txt(vendedor["ultima_actividad"], 9, MUTED_2),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column(
                            [
                                ft.Row(
                                    [txt("Meta mensual", 10, MUTED), txt(porcentaje(cumplimiento, 0), 10, TEAL, W_600)],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                barra(min(100, cumplimiento), TEAL, "#E2E8F0", 5),
                                ft.Row(
                                    [txt(money(vendedor["ventas_mes"]), 11, INK, W_600),
                                     txt(f"/ {money(vendedor['meta_mes'])}", 9.5, MUTED)],
                                    spacing=4,
                                ),
                            ],
                            spacing=5,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Column(
                                        [
                                            txt("Saldo en billetera", 9, MUTED, W_500),
                                            txt(money(vendedor["saldo_billetera"], 2), 16, TEAL_DARK, W_700),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                    ft.Column(
                                        [
                                            txt("Comisión del mes", 9, MUTED, W_500),
                                            txt(money(vendedor["comision_mes"], 2), 10.5, INK, W_600),
                                        ],
                                        spacing=1,
                                        horizontal_alignment=ft.CrossAxisAlignment.END,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor=SOFT,
                            border=ft.Border.all(1, BORDER),
                            border_radius=8,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                        ),
                        ft.Row(
                            [
                                text_button("Ver perfil", None, lambda e, v=vendedor: open_seller_dialog(app, v), size=10.5, height=28),
                                ft.Container(expand=True),
                                secondary_button(
                                    "Liquidar" if puede_liquidar else "Al día",
                                    ft.Icons.PAYMENTS_OUTLINED if puede_liquidar else ft.Icons.CHECK,
                                    lambda e, v=vendedor: open_liquidation_dialog(app, [v]),
                                    width=92, height=32, color=TEAL, disabled=not puede_liquidar,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=11,
                ),
                padding=14,
                width=303,
            )
        )

    kpis = ft.Row(
        [
            kpi_card(
                "Vendedores activos", f"{activos} / {len(data.VENDEDORES)}",
                ft.Icons.BADGE_OUTLINED, TEAL, TEAL_SOFT,
                trend=f"{len({v.get('ciudad') for v in data.VENDEDORES if v.get('ciudad')})} ciudades",
                trend_icon=ft.Icons.LOCATION_ON_OUTLINED,
                note="red nacional activa",
            ),
            kpi_card(
                "Disponible en billeteras", compacto(saldo_total),
                ft.Icons.WALLET_OUTLINED, PURPLE, PURPLE_SOFT,
                trend="Listo", trend_icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
                trend_color=PURPLE, trend_bg=PURPLE_SOFT, note="para liquidar",
            ),
            kpi_card(
                "Comisiones del mes", compacto(comision_total),
                ft.Icons.PERCENT, BLUE, BLUE_SOFT,
                trend="+8.6%", trend_icon=ft.Icons.TRENDING_UP,
                trend_color=BLUE, trend_bg=BLUE_SOFT, note="vs. mes anterior",
            ),
            kpi_card(
                "Liquidado este mes", compacto(liquidado_total),
                ft.Icons.PAYMENTS_OUTLINED, ORANGE, ORANGE_SOFT,
                trend=f"{len([v for v in data.VENDEDORES if v['liquidado_mes'] > 0])} pagos",
                trend_icon=ft.Icons.DONE_ALL,
                trend_color=ORANGE, trend_bg=ORANGE_SOFT, note="transferencias",
            ),
        ],
        spacing=14,
    )

    disponibles = [v for v in data.VENDEDORES if v["saldo_billetera"] > 0]
    accion_liquidar = (
        primary_button(
            "Liquidar todas", ft.Icons.PAYMENTS_OUTLINED,
            lambda e: open_liquidation_dialog(app, disponibles),
        )
        if disponibles
        else secondary_button("Todo liquidado", ft.Icons.CHECK, None, disabled=True)
    )

    return ft.Column(
        [
            page_header(
                "Red comercial y billetera",
                f"{len(data.VENDEDORES)} vendedores en Venezuela, carteras de talleres y tiendas, comisiones y liquidaciones en USD.",
                [
                    secondary_button("Historial", ft.Icons.HISTORY,
                                    lambda e: open_wallet_history_dialog(app)),
                    accion_liquidar,
                ],
                eyebrow=f"FUERZA DE VENTAS · {len(data.VENDEDORES)} VENDEDORES",
            ),
            kpis,
            section_header(
                "Equipo comercial",
                f"{len(data.VENDEDORES)} vendedores · {sum(len(data.clientes_de_vendedor(v['id'])) for v in data.VENDEDORES)} clientes asignados",
                pill(f"{len(disponibles)} con saldo disponible", TEAL, TEAL_SOFT),
            ),
            ft.Row(tarjetas, spacing=14, run_spacing=14, wrap=True, vertical_alignment=ft.CrossAxisAlignment.START),
            section_header(
                "Movimientos de billetera",
                "Comisiones, bonos y liquidaciones de la red comercial.",
                text_button("Ver historial completo", ft.Icons.ARROW_FORWARD, lambda e: open_wallet_history_dialog(app), size=11),
            ),
            movimientos,
        ],
        spacing=16,
    )


# ---------------------------------------------------------------------------
# Finanzas y reportes
# ---------------------------------------------------------------------------


def _grouped_chart(serie):
    maximo = max(max(item["ingresos"], item["egresos"]) for item in serie) or 1
    columnas = []
    for item in serie:
        alto_ing = max(5, item["ingresos"] / maximo * 112)
        alto_egr = max(5, item["egresos"] / maximo * 112)
        columnas.append(
            ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(width=10, height=alto_ing, bgcolor=TEAL, border_radius=3,
                                             tooltip=f"Ingresos {item['label']}: {money(item['ingresos'])}"),
                                ft.Container(width=10, height=alto_egr, bgcolor="#CBD5E1", border_radius=3,
                                             tooltip=f"Egresos {item['label']}: {money(item['egresos'])}"),
                            ],
                            spacing=3,
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        height=116,
                        alignment=ft.Alignment.BOTTOM_CENTER,
                    ),
                    txt(item["label"], 9.5, MUTED, W_500),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=1,
            )
        )
    return ft.Row(columnas, spacing=5, vertical_alignment=ft.CrossAxisAlignment.END)


def finance_view(app):
    periodo = app.finance_period if app.finance_period in data.FINANZAS_PERIODOS else "Este mes"
    finanzas = data.FINANZAS_PERIODOS[periodo]
    kpis_data = finanzas["kpis"]
    serie = finanzas["series"]

    periodo_chips = ft.Row(
        [
            filter_chip(
                nombre,
                nombre == periodo,
                lambda e, valor=nombre: app.set_finance_period(valor),
            )
            for nombre in data.FINANZAS_PERIODOS
        ],
        spacing=6,
    )

    total_ingresos = sum(item["ingresos"] for item in serie)
    total_egresos = sum(item["egresos"] for item in serie)
    flujo_neto = total_ingresos - total_egresos
    cxc_actual = sum(c["saldo"] for c in data.CLIENTES)
    total_aging = sum(tramo["monto"] for tramo in data.AGING_CARTERA) or 1
    factor_cartera = cxc_actual / total_aging
    aging_actual = [
        {**tramo, "monto": round(tramo["monto"] * factor_cartera, 2)}
        for tramo in data.AGING_CARTERA
    ]
    vencido_actual = sum(
        tramo["monto"] for tramo in aging_actual if not tramo["rango"].startswith("0")
    )

    chart_card = card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                txt("Flujo de caja", 15.5, INK, W_600),
                                txt(finanzas["nota"], 10.5, MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Row(
                            [
                                ft.Row([ft.Container(width=7, height=7, bgcolor=TEAL, border_radius=4), txt("Ingresos", 10, MUTED)], spacing=5),
                                ft.Row([ft.Container(width=7, height=7, bgcolor="#CBD5E1", border_radius=4), txt("Egresos", 10, MUTED)], spacing=5),
                            ],
                            spacing=12,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=2),
                _grouped_chart(serie),
                ft.Divider(height=1, color=BORDER),
                ft.Row(
                    [
                        ft.Column([txt("Ingresos", 9.5, MUTED), txt(money(total_ingresos), 13, INK, W_700)], spacing=1, expand=1),
                        ft.Column([txt("Egresos", 9.5, MUTED), txt(money(total_egresos), 13, INK, W_700)], spacing=1, expand=1),
                        ft.Column([txt("Flujo neto", 9.5, MUTED), txt(money(flujo_neto), 13, TEAL_DARK, W_700)], spacing=1, expand=1),
                        pill("Saludable", TEAL, TEAL_SOFT, icon=ft.Icons.TRENDING_UP),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=13,
        ),
        padding=18,
        expand=1,
    )

    aging_rows = []
    for tramo in aging_actual:
        aging_rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=8, height=8, bgcolor=tramo["color"], border_radius=4),
                            txt(tramo["rango"], 10.5, INK, W_500, expand=True),
                            txt(money(tramo["monto"]), 10.5, INK, W_600),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.Container(content=barra(tramo["porcentaje"], tramo["color"], "#F1F5F9", 4), expand=True),
                            txt(f"{tramo['porcentaje']:.1f}%", 9, MUTED, W_500),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=3,
            )
        )

    aging_card = card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                txt("Antigüedad de cartera", 15, INK, W_600),
                                txt("Distribución de cuentas por cobrar", 10.5, MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        pill("Riesgo medio", ORANGE, ORANGE_SOFT, icon=ft.Icons.WARNING_AMBER_ROUNDED),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Container(
                            expand=max(1, int(tramo["porcentaje"] * 10)),
                            height=9,
                            bgcolor=tramo["color"],
                            border_radius=5,
                            tooltip=f"{tramo['rango']}: {money(tramo['monto'])}",
                        )
                        for tramo in aging_actual
                    ],
                    spacing=3,
                ),
                ft.Column(aging_rows, spacing=9),
                ft.Divider(height=1, color=BORDER),
                ft.Row(
                    [
                        txt("Total por cobrar", 10.5, MUTED, W_500),
                        ft.Container(expand=True),
                        txt(money(cxc_actual, 2), 14, INK, W_700),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                info_box(
                    f"{compacto(vencido_actual)} con más de 30 días de atraso.",
                    ORANGE, ORANGE_SOFT, ORANGE_BORDER, ft.Icons.PRIORITY_HIGH_OUTLINED,
                ),
            ],
            spacing=13,
        ),
        padding=17,
        expand=1,
    )

    cobros_host = ft.Column(spacing=0)
    pendientes = [f for f in data.FACTURAS_PENDIENTES if f["estado"] != "Pagada"]
    for factura in pendientes:
        cliente = data.cliente(factura["cliente_id"]) or {}
        es_vencida = factura["estado"] == "Vencida"
        cobros_host.controls.append(
            table_row(
                [
                    cell(
                        ft.Row(
                            [
                                avatar(cliente.get("negocio", "?"), RED if es_vencida else TEAL, 28, 9),
                                ft.Column(
                                    [
                                        txt(cliente.get("negocio", "Cliente"), 10.5, INK, W_600, max_lines=1),
                                        txt(cliente.get("contacto", ""), 9.5, MUTED, W_400),
                                    ],
                                    spacing=1,
                                    expand=True,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        3.2,
                    ),
                    cell(txt(factura["id"], 10.5, "#475569", W_500), 1.4),
                    cell(txt(fecha_corta(factura["vence"]), 10.5, MUTED, W_500), 1.3),
                    cell(
                        txt(f"{factura['dias']} d" if factura["dias"] else "—", 10.5,
                            RED if factura["dias"] else MUTED, W_600 if factura["dias"] else W_400),
                        1,
                        ALIGN_RIGHT,
                    ),
                    cell(txt(money(factura["monto"], 2), 11, INK, W_600), 1.7, ALIGN_RIGHT),
                    cell(
                        pill(factura["estado"], RED if es_vencida else ORANGE,
                             RED_SOFT if es_vencida else ORANGE_SOFT, size=9.5),
                        1.4,
                    ),
                    cell(
                        text_button(
                            "Cobrar", ft.Icons.PAYMENTS_OUTLINED,
                            lambda e, f=factura: open_payment_dialog(app, data.cliente(f["cliente_id"]), f, parent_dialogs=1),
                            size=10.5, height=27,
                        ),
                        1.1,
                        ALIGN_RIGHT,
                    ),
                ],
                padding_v=9,
            )
        )

    cobros_card = table_container(
        [
            {"label": "Cliente", "flex": 3.2},
            {"label": "Factura", "flex": 1.4},
            {"label": "Vence", "flex": 1.3},
            {"label": "Atraso", "flex": 1, "align": ALIGN_RIGHT},
            {"label": "Monto", "flex": 1.7, "align": ALIGN_RIGHT},
            {"label": "Estado", "flex": 1.4},
            {"label": "", "flex": 1.1, "align": ALIGN_RIGHT},
        ],
        cobros_host,
        table_footer(
            ft.Row(
                [
                    txt(f"{len(pendientes)} facturas pendientes", 10.5, MUTED),
                    ft.Container(expand=True),
                    txt(f"Total: {money(sum(f['monto'] for f in pendientes), 2)}", 10.5, ORANGE, W_600),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ),
    )

    reportes = []
    for reporte in data.REPORTES:
        iconos = {
            "trending": ft.Icons.TRENDING_UP,
            "finance": ft.Icons.ACCOUNT_BALANCE_OUTLINED,
            "inventory": ft.Icons.INVENTORY_2_OUTLINED,
            "wallet": ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
            "report": ft.Icons.DESCRIPTION_OUTLINED,
        }
        reportes.append(
            card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                icon_box(iconos.get(reporte["icono"], ft.Icons.DESCRIPTION_OUTLINED),
                                         reporte["color"], reporte["bg"], 34, 17, 8),
                                ft.Column(
                                    [
                                        txt(reporte["nombre"], 11.5, INK, W_600, max_lines=1),
                                        txt(reporte["descripcion"], 9.5, MUTED, W_400, max_lines=2),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=9,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Row(
                            [
                                pill(reporte["formato"], MUTED, SOFT_2, size=8.5),
                                ft.Container(expand=True),
                                txt(reporte["actualizado"], 8.5, MUTED_2),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                text_button("Generar reporte", ft.Icons.AUTO_AWESOME_OUTLINED,
                                            lambda e, r=reporte: open_report_dialog(app, r), size=10.5),
                                ft.Container(expand=True),
                                icon_button(ft.Icons.DOWNLOAD, "Descargar",
                                            lambda e, r=reporte: app.toast(f"Descarga simulada de {r['nombre']}.", "success"),
                                            size=16),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=9,
                ),
                padding=13,
                width=303,
            )
        )

    kpis = ft.Row(
        [
            kpi_card(
                "Ingresos del periodo", compacto(total_ingresos),
                ft.Icons.PAYMENTS_OUTLINED, TEAL, TEAL_SOFT,
                trend="+9.8%", trend_icon=ft.Icons.TRENDING_UP, note=periodo.lower(),
            ),
            kpi_card(
                "Cuentas por cobrar", compacto(cxc_actual),
                ft.Icons.ACCOUNT_BALANCE_OUTLINED, BLUE, BLUE_SOFT,
                trend=f"{len([f for f in data.FACTURAS_PENDIENTES if f['estado'] != 'Pagada'])} facturas",
                trend_icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                trend_color=BLUE, trend_bg=BLUE_SOFT, note="cartera total",
            ),
            kpi_card(
                "Cartera vencida", compacto(vencido_actual),
                ft.Icons.WARNING_AMBER_ROUNDED, ORANGE, ORANGE_SOFT,
                trend=porcentaje(
                    (vencido_actual / cxc_actual * 100) if cxc_actual else 0, 1
                ),
                trend_icon=ft.Icons.TRENDING_DOWN,
                trend_color=ORANGE, trend_bg=ORANGE_SOFT, note="de la cartera",
            ),
            kpi_card(
                "Margen bruto", porcentaje(kpis_data["margen"], 1),
                ft.Icons.INSIGHTS_OUTLINED, PURPLE, PURPLE_SOFT,
                trend="+1.2 pts", trend_icon=ft.Icons.TRENDING_UP,
                trend_color=PURPLE, trend_bg=PURPLE_SOFT, note="vs. mes anterior",
            ),
        ],
        spacing=14,
    )

    return ft.Column(
        [
            page_header(
                "Finanzas y reportes",
                "Flujo de caja en USD, cartera de talleres, cobros y reportes de Mayor Disluda.",
                [
                    periodo_chips,
                    secondary_button("Exportar", ft.Icons.DOWNLOAD,
                                    lambda e: app.toast("Estado financiero exportado (demo).", "success")),
                ],
                eyebrow="ANÁLISIS · MAYOR DISLUDA",
            ),
            kpis,
            ft.Row([chart_card, aging_card], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
            section_header(
                "Cobros pendientes",
                "Facturas con seguimiento de vencimiento y acciones de cobro.",
                pill(f"{len(pendientes)} pendientes", ORANGE, ORANGE_SOFT),
            ),
            cobros_card,
            section_header(
                "Reportes generales",
                "Documentos listos para generar y compartir con la dirección.",
                text_button("Ver todos", None, lambda e: app.toast("Todos los reportes están disponibles en la lista.", "info"), size=11),
            ),
            ft.Row(reportes, spacing=14, run_spacing=14, wrap=True, vertical_alignment=ft.CrossAxisAlignment.START),
        ],
        spacing=16,
    )


# ---------------------------------------------------------------------------
# Diálogos y acciones compartidas
# ---------------------------------------------------------------------------


def _dialog_base(title, subtitle, body, actions, width=540, icono=ft.Icons.AUTO_AWESOME_OUTLINED,
                 color=TEAL, bg=TEAL_SOFT, subtitle_control=None):
    return ft.AlertDialog(
        modal=True,
        bgcolor=WHITE,
        shape=ft.RoundedRectangleBorder(radius=14),
        inset_padding=28,
        scrollable=True,
        title=ft.Row(
            [
                icon_box(icono, color, bg, 38, 19, 9),
                ft.Column(
                    [
                        txt(title, 17, INK, W_700),
                        subtitle_control or txt(subtitle, 10.5, MUTED),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(content=body, width=width),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
        title_padding=ft.Padding.only(left=22, right=22, top=20, bottom=6),
        content_padding=ft.Padding.only(left=22, right=22, top=4, bottom=6),
        actions_padding=ft.Padding.only(left=22, right=22, top=10, bottom=18),
    )


def open_payment_dialog(app, cliente, factura=None, parent_dialogs=1):
    if not cliente:
        app.toast("No se encontró el cliente seleccionado.", "error")
        return
    saldo = float(cliente["saldo"])
    if saldo <= 0:
        app.toast("Este cliente no tiene saldo pendiente.", "info")
        return

    sugerido = min(saldo, factura["monto"]) if factura else saldo
    monto_state = {"valor": f"{sugerido:.2f}"}
    amount_field = base_text_field(
        value=f"{sugerido:.2f}",
        hint="0.00",
        on_change=lambda e: monto_state.update(valor=e.control.value),
    )
    amount_field.suffix = ft.Text("$", size=11.5, color=MUTED)
    amount_field.suffix_style = ft.TextStyle(size=11.5, color=MUTED)
    method_dd = ft.Dropdown(
        options=[
            ft.DropdownOption(key="Transferencia bancaria", text="Transferencia bancaria"),
            ft.DropdownOption(key="Efectivo", text="Efectivo"),
            ft.DropdownOption(key="Cheque", text="Cheque"),
        ],
        value="Transferencia bancaria",
        border=ft.InputBorder.NONE,
        dense=True,
        text_size=12.5,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        expand=True,
    )
    reference_field = base_text_field(value="", hint="N.º de referencia (opcional)")
    estado = {"metodo": "Transferencia bancaria"}

    def elegir_metodo(e):
        estado["metodo"] = e.control.value
        app.page.update()

    method_dd.on_select = elegir_metodo

    def confirmar(e):
        try:
            monto = float(str(monto_state["valor"]).replace(",", ".").strip())
        except (TypeError, ValueError):
            monto = 0
        if monto <= 0:
            amount_field.error = "Ingresa un monto válido."
            app.page.update()
            return
        if monto > saldo:
            amount_field.error = f"El saldo disponible es {money(saldo, 2)}."
            app.page.update()
            return
        cliente["saldo"] = round(saldo - monto, 2)
        if factura and factura in data.FACTURAS_PENDIENTES:
            data.FACTURAS_PENDIENTES.remove(factura)
        data.registrar_actividad(
            "pago", "Pago registrado",
            f"{cliente['negocio']} · {estado['metodo']}",
            monto, "Confirmado",
        )
        app.close_dialogs(parent_dialogs)
        app.refresh()
        app.toast(f"Pago de {money(monto, 2)} registrado para {cliente['negocio']}.", "success")

    body = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        avatar(cliente["negocio"], TEAL, 38),
                        ft.Column(
                            [
                                txt(cliente["negocio"], 12.5, INK, W_600),
                                txt(f"{cliente['contacto']} · {cliente['telefono']}", 10, MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Column(
                            [
                                txt("Saldo actual", 9, MUTED),
                                txt(money(saldo, 2), 13, ORANGE, W_700),
                            ],
                            spacing=1,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=11,
            ),
            info_box(
                f"Factura {factura['id']} · vence {fecha_corta(factura['vence'])}" if factura
                else "Pago a cuenta del saldo total del cliente.",
                BLUE, BLUE_SOFT, "#BFDBFE", ft.Icons.RECEIPT_LONG_OUTLINED,
            ),
            field_shell("Monto a cobrar", amount_field),
            labeled_dropdown("Método de pago",
                             [("Transferencia bancaria", "Transferencia bancaria"),
                              ("Efectivo", "Efectivo"),
                              ("Cheque", "Cheque")],
                             "Transferencia bancaria", elegir_metodo, expand=True),
            field_shell("Referencia", reference_field),
            info_box(
                "El saldo del cliente y la cartera por cobrar se actualizarán al confirmar.",
                TEAL, TEAL_SOFT, TEAL_BORDER, ft.Icons.CHECK_CIRCLE_OUTLINED,
            ),
        ],
        spacing=13,
    )

    app.show_dialog(_dialog_base(
        "Registrar pago",
        "Aplica un cobro a la cuenta del cliente.",
        body,
        [
            text_button("Cancelar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5),
            primary_button("Confirmar pago", ft.Icons.CHECK, confirmar, height=38),
        ],
        width=480,
        icono=ft.Icons.PAYMENTS_OUTLINED,
    ))


def open_client_dialog(app, cliente):
    vendedor = data.vendedor(cliente["vendedor_id"]) or {}
    uso = cliente["saldo"] / cliente["limite"] * 100 if cliente["limite"] else 0
    disponible = max(0, cliente["limite"] - cliente["saldo"])
    pedidos = data.pedidos_de_cliente(cliente["id"])[:3]

    if cliente["score"] >= 85:
        score_color, score_bg, score_label = TEAL, TEAL_SOFT, "Excelente"
    elif cliente["score"] >= 70:
        score_color, score_bg, score_label = ORANGE, ORANGE_SOFT, "Regular"
    else:
        score_color, score_bg, score_label = RED, RED_SOFT, "Bajo"

    datos = ft.Row(
        [
            ft.Column(
                [
                    txt("Contacto", 9.5, MUTED, W_500),
                    txt(cliente["contacto"], 11.5, INK, W_600),
                    txt(cliente["telefono"], 10.5, MUTED),
                    txt(cliente["email"], 10.5, MUTED, max_lines=1),
                ],
                spacing=2, expand=True,
            ),
            ft.Column(
                [
                    txt("Vendedor asignado", 9.5, MUTED, W_500),
                    txt(vendedor.get("nombre", "—"), 11.5, INK, W_600),
                    txt(vendedor.get("zona", ""), 10.5, MUTED),
                    txt(f"Cliente desde {fecha_corta(cliente['desde'])}", 10, MUTED),
                ],
                spacing=2, expand=True,
            ),
            ft.Column(
                [
                    txt("Datos fiscales", 9.5, MUTED, W_500),
                    txt(f"RIF {cliente['rtn']}", 10.5, INK, W_500),
                    txt(cliente["direccion"], 10.5, MUTED, max_lines=2),
                    txt(cliente["tipo"], 10, MUTED),
                ],
                spacing=2, expand=True,
            ),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    credito_box = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        txt("Crédito disponible", 10, MUTED, W_500),
                        ft.Container(expand=True),
                        pill(f"{uso:.0f}% utilizado", ORANGE if uso >= 65 else TEAL,
                             ORANGE_SOFT if uso >= 65 else TEAL_SOFT, size=9),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Column([txt("Límite", 9, MUTED), txt(money(cliente["limite"]), 12, INK, W_600)], spacing=1, expand=1),
                        ft.Column([txt("Saldo", 9, MUTED), txt(money(cliente["saldo"]), 12, ORANGE, W_600)], spacing=1, expand=1),
                        ft.Column([txt("Disponible", 9, MUTED), txt(money(disponible), 12, TEAL, W_600)], spacing=1, expand=1),
                    ],
                    spacing=10,
                ),
                barra(min(100, uso), ORANGE if uso >= 65 else TEAL, "#E2E8F0", 6),
            ],
            spacing=7,
        ),
        bgcolor=SOFT,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=12,
    )

    mini_metrics = ft.Row(
        [
            ft.Container(
                content=ft.Column(
                    [
                        txt("Puntualidad", 9.5, MUTED, W_500),
                        ft.Row([txt(f"{cliente['score']}%", 20, score_color, W_700),
                                pill(score_label, score_color, score_bg, size=8.5)], spacing=6,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ],
                    spacing=2,
                ),
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=11,
                expand=1,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        txt("Compras del mes", 9.5, MUTED, W_500),
                        txt(money(cliente["compras_mes"]), 17, INK, W_700),
                    ],
                    spacing=2,
                ),
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=11,
                expand=1,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        txt("Último pago", 9.5, MUTED, W_500),
                        txt(fecha_corta(cliente["ultimo_pago"]), 17, INK, W_700),
                    ],
                    spacing=2,
                ),
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=11,
                expand=1,
            ),
        ],
        spacing=9,
    )

    pedidos_host = ft.Column(spacing=0)
    for pedido in pedidos:
        pedidos_host.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        txt(pedido["id"], 10.5, INK, W_600),
                        txt(fecha_corta(pedido["fecha"]), 9.5, MUTED),
                        ft.Container(expand=True),
                        doc_pill(pedido["tipo_doc"]),
                        txt(money(pedido["total"], 2), 10.5, INK, W_600),
                        estado_pedido_pill(pedido["estado"]),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=7),
                border=ft.Border(bottom=ft.BorderSide(1, "#F1F5F9")),
            )
        )
    if not pedidos:
        pedidos_host.controls.append(txt("Sin pedidos registrados.", 10.5, MUTED))

    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    avatar(cliente["negocio"], TEAL if cliente["estado"] == "Activo" else ORANGE, 46),
                    ft.Column(
                        [
                            txt(cliente["negocio"], 15, INK, W_700),
                            txt(f"{cliente['tipo']} · {cliente['ciudad']}", 10.5, MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    estado_cliente_pill(cliente["estado"]),
                ],
                spacing=11,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            datos,
            credito_box,
            mini_metrics,
            ft.Column(
                [
                    txt("Pedidos recientes", 11, INK, W_600),
                    ft.Container(
                        content=pedidos_host,
                        border=ft.Border.all(1, BORDER),
                        border_radius=8,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                ],
                spacing=6,
            ),
            info_box(
                "Cliente suspendido: no se pueden registrar nuevos pedidos a crédito hasta regularizar la cartera."
                if cliente["estado"] == "Suspendido"
                else f"Score de puntualidad {cliente['score']}% · condición {cliente['condicion']}.",
                RED if cliente["estado"] == "Suspendido" else BLUE,
                RED_SOFT if cliente["estado"] == "Suspendido" else BLUE_SOFT,
                "#FECACA" if cliente["estado"] == "Suspendido" else "#BFDBFE",
                ft.Icons.WARNING_AMBER_ROUNDED if cliente["estado"] == "Suspendido" else ft.Icons.SHIELD_OUTLINED,
            ),
        ],
        spacing=13,
    )

    acciones = [text_button("Cerrar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5)]
    if cliente["saldo"] > 0:
        acciones.append(primary_button(
            "Registrar pago", ft.Icons.PAYMENTS_OUTLINED,
            lambda e: open_payment_dialog(app, cliente, None, parent_dialogs=2),
            height=38,
        ))

    app.show_dialog(_dialog_base(
        "Ficha del cliente",
        f"{cliente['id']} · {cliente['ciudad']}",
        cuerpo,
        acciones,
        width=650,
        icono=ft.Icons.STORE_OUTLINED,
    ))


def open_liquidation_dialog(app, vendedores, parent_dialogs=1):
    vendedores = [v for v in vendedores if v["saldo_billetera"] > 0]
    if not vendedores:
        app.toast("No hay saldos pendientes por liquidar.", "info")
        return
    total = sum(v["saldo_billetera"] for v in vendedores)
    cuerpo = ft.Column(spacing=13)
    acciones = ft.Row([], spacing=8, alignment=ft.MainAxisAlignment.END)
    subtitulo = txt("Paso 1 de 2 · Verificación y autorización.", 10.5, MUTED)

    def paso_uno():
        subtitulo.value = "Paso 1 de 2 · Verificación y autorización."
        filas = []
        for v in vendedores:
            filas.append(
                ft.Row(
                    [
                        avatar(v["nombre"], v["color"], 28, 9),
                        ft.Column(
                            [
                                txt(v["nombre"], 10.5, INK, W_600),
                                txt(v["metodo_pago"], 9, MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        txt(money(v["saldo_billetera"], 2), 11, INK, W_600),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        cuerpo.controls = [
            txt("Revisa el desglose antes de autorizar la transferencia.", 11, MUTED),
            ft.Container(
                content=ft.Column(filas, spacing=9),
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=12,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column([txt("Total a liquidar", 10, MUTED, W_500),
                                   txt(money(total, 2), 20, TEAL_DARK, W_700)], spacing=1, expand=True),
                        pill(f"{len(vendedores)} vendedor(es)", TEAL, TEAL_SOFT),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=TEAL_SOFT,
                border=ft.Border.all(1, TEAL_BORDER),
                border_radius=8,
                padding=12,
            ),
            info_box(
                "La liquidación se enviará a la cuenta registrada de cada vendedor y quedará en el historial.",
                BLUE, BLUE_SOFT, "#BFDBFE", ft.Icons.INFO_OUTLINE,
            ),
        ]
        acciones.controls = [
            text_button("Cancelar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5),
            primary_button("Continuar", ft.Icons.ARROW_FORWARD, lambda e: paso_dos(), height=38),
        ]
        app.page.update()

    codigo_state = {"valor": ""}
    code_field = base_text_field(
        value="",
        hint="••••",
        password=True,
        max_length=4,
        on_change=lambda e: codigo_state.update(valor=e.control.value),
    )

    def sincronizar_codigo(e):
        codigo_state["valor"] = e.control.value
        if code_field.error:
            code_field.error = None
            app.page.update()

    code_field.on_change = sincronizar_codigo

    def confirmar(e=None):
        if str(codigo_state["valor"] or "").strip() != "2468":
            code_field.error = "Clave incorrecta. Usa 2468 en esta demo."
            app.page.update()
            return
        for v in vendedores:
            monto = v["saldo_billetera"]
            v["saldo_billetera"] = 0.0
            v["liquidado_mes"] = round(v["liquidado_mes"] + monto, 2)
            data.registrar_movimiento(
                v["id"], "Liquidación",
                "Liquidación de comisiones · Transferencia bancaria",
                monto, "Liquidado",
            )
            data.registrar_actividad(
                "billetera", "Liquidación completada",
                f"{v['nombre']} · {v['metodo_pago']}", monto, "Liquidado",
            )
        app.close_dialogs(parent_dialogs)
        app.refresh()
        app.toast(f"Liquidación de {money(total, 2)} completada correctamente.", "success")

    def paso_dos():
        subtitulo.value = "Paso 2 de 2 · Confirmación de seguridad."
        code_field.value = ""
        code_field.error = None
        codigo_state["valor"] = ""
        cuerpo.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        txt("Monto autorizado", 10, MUTED, W_500),
                        txt(money(total, 2), 28, TEAL_DARK, W_700),
                        txt(f"para {len(vendedores)} vendedor(es)", 10, MUTED),
                    ],
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=TEAL_SOFT,
                border=ft.Border.all(1, TEAL_BORDER),
                border_radius=8,
                padding=16,
                alignment=ALIGN_CENTER,
            ),
            field_shell("Clave de seguridad", code_field),
            info_box(
                "Doble confirmación requerida. Clave de demostración: 2468.",
                ORANGE, ORANGE_SOFT, ORANGE_BORDER, ft.Icons.LOCK_OUTLINE,
            ),
        ]
        acciones.controls = [
            text_button("Atrás", ft.Icons.ARROW_BACK, lambda e: paso_uno(), color=MUTED, size=11.5),
            primary_button("Confirmar liquidación", ft.Icons.SHIELD_OUTLINED, confirmar, height=38),
        ]
        code_field.on_submit = confirmar
        app.page.update()

    paso_uno()
    dialogo = _dialog_base(
        "Liquidar comisiones",
        "Paso 1 de 2 · Verificación y autorización.",
        cuerpo,
        [acciones],
        width=480,
        icono=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        color=PURPLE,
        bg=PURPLE_SOFT,
        subtitle_control=subtitulo,
    )
    app.show_dialog(dialogo)


def open_seller_dialog(app, vendedor):
    clientes = data.clientes_de_vendedor(vendedor["id"])
    movimientos = [m for m in data.MOVIMIENTOS_BILLETERA if m["vendedor_id"] == vendedor["id"]][:4]
    cumplimiento = vendedor["ventas_mes"] / vendedor["meta_mes"] * 100 if vendedor["meta_mes"] else 0

    cliente_rows = []
    for c in clientes:
        cliente_rows.append(
            ft.Row(
                [
                    avatar(c["negocio"], TEAL, 24, 9),
                    txt(c["negocio"], 10, INK, W_500, expand=True, max_lines=1),
                    txt(money(c["saldo"]), 9.5, MUTED, W_500),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    mov_rows = []
    for m in movimientos:
        mov_rows.append(
            ft.Row(
                [
                    pill(m["tipo"], TEAL if m["tipo"] == "Comisión" else BLUE,
                         TEAL_SOFT if m["tipo"] == "Comisión" else BLUE_SOFT, size=8.5),
                    txt(m["concepto"], 9.5, MUTED, W_400, expand=True, max_lines=1),
                    txt(money(m["monto"], 2), 9.5, INK, W_600),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    avatar(vendedor["nombre"], vendedor["color"], 46),
                    ft.Column(
                        [
                            txt(vendedor["nombre"], 15, INK, W_700),
                            txt(f"{vendedor['codigo']} · {vendedor['zona']}", 10.5, MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    estado_vendedor_pill(vendedor["estado"]),
                ],
                spacing=11,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    mini_stat("Clientes", str(len(clientes)), "cartera asignada", ft.Icons.PEOPLE_OUTLINE, BLUE, BLUE_SOFT),
                    mini_stat("Ventas mes", compacto(vendedor["ventas_mes"]), f"{cumplimiento:.0f}% de meta", ft.Icons.TRENDING_UP, TEAL, TEAL_SOFT),
                ],
                spacing=10,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                txt("Saldo disponible en billetera", 10, MUTED, W_500),
                                ft.Container(expand=True),
                                txt(money(vendedor["saldo_billetera"], 2), 17, TEAL_DARK, W_700),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                txt("Comisión del mes", 9.5, MUTED),
                                txt(money(vendedor["comision_mes"], 2), 10, INK, W_600),
                                ft.Container(expand=True),
                                txt(f"{vendedor['comision_pct']}% comisión", 9.5, MUTED),
                            ],
                            spacing=7,
                        ),
                        barra(min(100, cumplimiento), TEAL, "#E2E8F0", 5),
                    ],
                    spacing=8,
                ),
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=12,
            ),
            ft.Column([txt("Clientes asignados", 11, INK, W_600), ft.Column(cliente_rows, spacing=7)], spacing=6),
            ft.Column([txt("Movimientos recientes", 11, INK, W_600), ft.Column(mov_rows, spacing=7)], spacing=6),
        ],
        spacing=13,
    )

    acciones = [text_button("Cerrar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5)]
    if vendedor["saldo_billetera"] > 0:
        acciones.append(primary_button(
            "Liquidar comisiones", ft.Icons.PAYMENTS_OUTLINED,
            lambda e: open_liquidation_dialog(app, [vendedor], parent_dialogs=2),
            height=38,
        ))

    app.show_dialog(_dialog_base(
        "Perfil del vendedor",
        vendedor["email"],
        cuerpo,
        acciones,
        width=560,
        icono=ft.Icons.BADGE_OUTLINED,
        color=vendedor["color"],
        bg=SOFT_2,
    ))


def open_wallet_history_dialog(app):
    filas = []
    for m in data.MOVIMIENTOS_BILLETERA:
        vendedor = data.vendedor(m["vendedor_id"]) or {}
        color = TEAL if m["tipo"] == "Comisión" else (BLUE if m["tipo"] == "Liquidación" else PURPLE)
        bg = TEAL_SOFT if m["tipo"] == "Comisión" else (BLUE_SOFT if m["tipo"] == "Liquidación" else PURPLE_SOFT)
        filas.append(
            ft.Container(
                content=ft.Row(
                    [
                        avatar(vendedor.get("nombre", "?"), vendedor.get("color", MUTED), 28, 9),
                        ft.Column(
                            [
                                txt(vendedor.get("nombre", "—"), 10.5, INK, W_600),
                                txt(m["concepto"], 9, MUTED, W_400, max_lines=1),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        pill(m["tipo"], color, bg, size=8.5),
                        txt(money(m["monto"], 2), 10, INK, W_600),
                        txt(fecha_corta(m["fecha"]), 9, MUTED),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=7),
                border=ft.Border(bottom=ft.BorderSide(1, "#F1F5F9")),
            )
        )
    cuerpo = ft.Column(
        [
            info_box(
                "Historial simulado de comisiones, bonos y liquidaciones de la billetera digital.",
                BLUE, BLUE_SOFT, "#BFDBFE", ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
            ),
            ft.Container(
                content=ft.Column(filas, spacing=0),
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
        ],
        spacing=12,
    )
    app.show_dialog(_dialog_base(
        "Historial de billetera",
        f"{len(data.MOVIMIENTOS_BILLETERA)} movimientos registrados",
        cuerpo,
        [text_button("Cerrar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5)],
        width=620,
        icono=ft.Icons.HISTORY,
        color=PURPLE,
        bg=PURPLE_SOFT,
    ))


def open_report_dialog(app, reporte):
    cuerpo = ft.Column(
        [
            info_box(
                "Vista previa del reporte. En esta versión prototipo la generación y descarga son simuladas.",
                BLUE, BLUE_SOFT, "#BFDBFE", ft.Icons.INFO_OUTLINE,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                icon_box(ft.Icons.DESCRIPTION_OUTLINED, TEAL, TEAL_SOFT, 38, 19, 9),
                                ft.Column(
                                    [
                                        txt(reporte["nombre"], 12, INK, W_600),
                                        txt(reporte["descripcion"], 10, MUTED, W_400, max_lines=2),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=1, color=BORDER),
                        ft.Row([txt("Periodo", 9.5, MUTED), ft.Container(expand=True), txt("Noviembre 2026", 9.5, INK, W_500)]),
                        ft.Row([txt("Formato", 9.5, MUTED), ft.Container(expand=True), txt(reporte["formato"], 9.5, INK, W_500)]),
                        ft.Row([txt("Actualizado", 9.5, MUTED), ft.Container(expand=True), txt(reporte["actualizado"], 9.5, INK, W_500)]),
                    ],
                    spacing=7,
                ),
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=13,
            ),
            info_box(
                "Reporte generado correctamente. Listo para descargar y compartir.",
                TEAL, TEAL_SOFT, TEAL_BORDER, ft.Icons.CHECK_CIRCLE_OUTLINED,
            ),
        ],
        spacing=12,
    )
    app.show_dialog(_dialog_base(
        "Generar reporte",
        reporte["nombre"],
        cuerpo,
        [
            text_button("Cerrar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5),
            primary_button(
                "Descargar", ft.Icons.DOWNLOAD,
                lambda e: app.toast(f"Descarga simulada: {reporte['nombre']}.", "success"),
                height=38,
            ),
        ],
        width=520,
        icono=ft.Icons.AUTO_AWESOME_OUTLINED,
        color=reporte["color"],
        bg=reporte["bg"],
    ))


def open_notifications_dialog(app):
    filas = []
    for n in data.NOTIFICACIONES:
        tipo = n["tipo"]
        icono, color, bg = {
            "alerta": (ft.Icons.WARNING_AMBER_ROUNDED, ORANGE, ORANGE_SOFT),
            "pedido": (ft.Icons.SHOPPING_BAG_OUTLINED, TEAL, TEAL_SOFT),
            "billetera": (ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, PURPLE, PURPLE_SOFT),
        }.get(tipo, (ft.Icons.NOTIFICATIONS_NONE, MUTED, SOFT_2))
        filas.append(
            ft.Row(
                [
                    icon_box(icono, color, bg, 32, 15, 8),
                    ft.Column(
                        [
                            txt(n["titulo"], 10.5, INK, W_600, max_lines=1),
                            txt(n["detalle"], 9.5, MUTED, W_400, max_lines=2),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    txt(n["hace"], 8.5, MUTED_2),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    cuerpo = ft.Column(filas, spacing=12)
    app.show_dialog(_dialog_base(
        "Notificaciones",
        "Novedades de la red comercial",
        cuerpo,
        [text_button("Marcar como leídas", None,
                    lambda e: (app.close_dialog(), app.toast("Notificaciones marcadas como leídas.", "info")),
                    color=TEAL, size=11),
         text_button("Cerrar", None, lambda e: app.close_dialog(), color=MUTED, size=11.5)],
        width=520,
        icono=ft.Icons.NOTIFICATIONS_NONE,
        color=BLUE,
        bg=BLUE_SOFT,
    ))


def open_company_dialog(app):
    detalle = [
        ("Cliente", data.EMPRESA["cliente"]),
        ("Desarrollador", data.EMPRESA["desarrollador"]),
        ("Rol activo", data.EMPRESA["rol"]),
        ("País", data.EMPRESA["pais"]),
        ("Moneda base", data.EMPRESA["moneda"]),
        ("Moneda secundaria", data.EMPRESA["moneda_secundaria"]),
        ("Tasa de referencia", f"Bs. {data.TASA_VES:,.2f} por USD"),
        ("Periodo contable", data.EMPRESA["periodo"]),
        ("Versión", "Mayorix Desktop v2.1.3"),
    ]
    filas = [
        ft.Row([txt(label, 9.5, MUTED), ft.Container(expand=True), txt(valor, 9.5, INK, W_500)])
        for label, valor in detalle
    ]
    cuerpo = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.LOCAL_MALL_OUTLINED, size=24, color=WHITE),
                            width=48, height=48, bgcolor=TEAL, border_radius=12, alignment=ALIGN_CENTER,
                        ),
                        ft.Column(
                            [
                                txt("Mayorix", 18, INK, W_700),
                                txt("Sistema de Gestión Mayorista para Mayor Disluda", 10.5, MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        pill("Mayor Disluda", TEAL, TEAL_SOFT),
                    ],
                    spacing=11,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=SOFT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=12,
            ),
            ft.Column(filas, spacing=8),
            info_box(
                "Los datos de Mayor Disluda se almacenan en MongoDB. "
                "El registro de inventario, vendedores y pedidos es manual y "
                "progresivo. Powered by DropeTech.",
                BLUE, BLUE_SOFT, "#BFDBFE", ft.Icons.INFO_OUTLINE,
            ),
        ],
        spacing=13,
    )
    app.show_dialog(_dialog_base(
        "Perfil de la empresa",
        "Mayor Disluda · Administración central",
        cuerpo,
        [
            text_button("Cerrar", None, lambda e: app.close_dialog(),
                        color=MUTED, size=11.5),
        ],
        width=500,
        icono=ft.Icons.BUSINESS_CENTER_OUTLINED,
    ))
