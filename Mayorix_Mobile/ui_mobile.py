"""
Mayorix · Componentes visuales móviles
=====================================
Paleta neutra, tipografía compacta y controles táctiles de 44+ px.
"""

from __future__ import annotations

from datetime import datetime

import flet as ft

INK = "#18212B"
INK_SOFT = "#334155"
MUTED = "#64748B"
MUTED_2 = "#94A3B8"
BG = "#F5F6F7"
WHITE = "#FFFFFF"
BORDER = "#E3E7EA"
SOFT = "#F1F3F4"
TEAL = "#0F766E"
TEAL_DARK = "#115E59"
TEAL_SOFT = "#E7F5F2"
TEAL_BORDER = "#CDE9E3"
ORANGE = "#C2410C"
ORANGE_SOFT = "#FFF3E8"
ORANGE_BORDER = "#FED7AA"
RED = "#B91C1C"
RED_SOFT = "#FEF2F2"
RED_BORDER = "#FECACA"
BLUE = "#1D4ED8"
BLUE_SOFT = "#EFF6FF"
GREEN = "#15803D"

W_500 = ft.FontWeight.W_500
W_600 = ft.FontWeight.W_600
W_700 = ft.FontWeight.W_700
ALIGN_CENTER = ft.Alignment.CENTER
ALIGN_RIGHT = ft.Alignment.CENTER_RIGHT

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

ESTADOS = {
    "Pendiente": (ORANGE, ORANGE_SOFT),
    "En revisión": (ORANGE, ORANGE_SOFT),
    "Aprobado": (TEAL, TEAL_SOFT),
    "En despacho": (BLUE, BLUE_SOFT),
    "Entregado": (GREEN, "#ECFDF5"),
    "Rechazado": (RED, RED_SOFT),
}


def txt(valor, size=13, color=INK, weight=None, max_lines=None,
        align=None, expand=False):
    return ft.Text(
        str(valor if valor is not None else ""),
        size=size,
        color=color,
        weight=weight,
        max_lines=max_lines,
        overflow=ft.TextOverflow.ELLIPSIS if max_lines else None,
        text_align=align,
        expand=expand,
    )


def money(valor, decimales=2) -> str:
    try:
        return f"$ {float(valor or 0):,.{decimales}f}"
    except (TypeError, ValueError):
        return "$ 0.00"


def bolivares(valor, decimales=2) -> str:
    try:
        return f"Bs. {float(valor or 0):,.{decimales}f}"
    except (TypeError, ValueError):
        return "Bs. 0,00"


def fecha_corta(valor) -> str:
    texto = str(valor or "")
    try:
        fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        return f"{fecha.day:02d} {MESES[fecha.month - 1]} {fecha.year}"
    except (ValueError, TypeError):
        return texto[:10] or "—"


def brand_mark(size=40, font=18):
    return ft.Container(
        content=txt("M", font, WHITE, W_700, align=ft.TextAlign.CENTER),
        width=size,
        height=size,
        bgcolor=TEAL,
        border_radius=size * 0.27,
        alignment=ALIGN_CENTER,
    )


def card(content, padding=14, radius=16, bgcolor=WHITE, border=True):
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border=ft.Border.all(1, BORDER) if border else None,
        border_radius=radius,
        padding=padding,
    )


def field_shell(label, control, hint=""):
    children = [txt(label, 11, MUTED, W_600)]
    children.append(
        ft.Container(
            content=control,
            bgcolor=SOFT,
            border=ft.Border.all(1, BORDER),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=4, vertical=1),
        )
    )
    if hint:
        children.append(txt(hint, 9.5, MUTED_2, max_lines=2))
    return ft.Column(children, spacing=5)


def text_field(hint="", value="", password=False, on_change=None,
               on_submit=None, keyboard_type=None, max_length=None):
    return ft.TextField(
        value=str(value or ""),
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        border=ft.InputBorder.NONE,
        text_size=14,
        color=INK,
        hint_style=ft.TextStyle(size=13, color=MUTED_2),
        cursor_color=TEAL,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=13),
        on_change=on_change,
        on_submit=on_submit,
        keyboard_type=keyboard_type,
        max_length=max_length,
        expand=True,
    )


def primary_button(label, icon=None, on_click=None, height=48,
                   disabled=False, bgcolor=TEAL):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=18, color=WHITE))
    children.append(txt(label, 14, WHITE, W_600, align=ft.TextAlign.CENTER))
    boton = ft.Button(
        content=ft.Row(
            children,
            spacing=8,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        bgcolor=bgcolor,
        color=WHITE,
        elevation=0,
        height=height,
        disabled=disabled,
        expand=True,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=14),
        ),
    )
    fila = ft.Row([boton], spacing=0)
    fila.data = boton
    return fila


def secondary_button(label, icon=None, on_click=None, height=42,
                     color=TEAL, disabled=False):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=17, color=color))
    children.append(txt(label, 12.5, color, W_600, align=ft.TextAlign.CENTER))
    boton = ft.Button(
        content=ft.Row(
            children,
            spacing=7,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        bgcolor=WHITE,
        color=color,
        elevation=0,
        height=height,
        disabled=disabled,
        expand=True,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=11),
            side=ft.BorderSide(1, BORDER),
            padding=ft.Padding.symmetric(horizontal=12),
        ),
    )
    fila = ft.Row([boton], spacing=0)
    fila.data = boton
    return fila


def action_button(label, icon=None, on_click=None, bgcolor=TEAL,
                  disabled=False, height=52):
    children = []
    if icon is not None:
        children.append(ft.Icon(icon, size=19, color=WHITE))
    children.append(txt(label, 14, WHITE, W_700,
                        align=ft.TextAlign.CENTER))
    return ft.Container(
        content=ft.Row(
            children,
            spacing=8,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        height=height,
        bgcolor=bgcolor,
        border_radius=12,
        alignment=ALIGN_CENTER,
        on_click=on_click if not disabled else None,
        ink=not disabled,
        opacity=1.0 if not disabled else 0.5,
    )


def pill(label, color=TEAL, bg=TEAL_SOFT, dot=False, size=10.5):
    children = []
    if dot:
        children.append(ft.Container(width=6, height=6, bgcolor=color,
                                     border_radius=3))
    children.append(txt(label, size, color, W_600))
    return ft.Container(
        content=ft.Row(children, spacing=5, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=bg,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=9, vertical=4),
    )


def status_pill(estado):
    color, bg = ESTADOS.get(estado, (MUTED, SOFT))
    return pill(estado or "Pendiente", color, bg, dot=True, size=9.5)


def section_title(titulo, subtitulo="", trailing=None):
    fila = [
        ft.Column(
            [
                txt(titulo, 18, INK, W_700),
                txt(subtitulo, 11, MUTED, max_lines=1) if subtitulo else None,
            ],
            spacing=2,
            expand=True,
        )
    ]
    if trailing is not None:
        fila.append(trailing)
    return ft.Row(
        [c for c in fila if c is not None],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def empty_state(mensaje, icono=ft.Icons.INBOX_OUTLINED, detalle=""):
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icono, size=34, color=MUTED_2),
                txt(mensaje, 13, INK, W_600, align=ft.TextAlign.CENTER),
                txt(detalle, 10.5, MUTED, max_lines=3,
                    align=ft.TextAlign.CENTER) if detalle else None,
            ],
            spacing=7,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=26, horizontal=14),
        alignment=ALIGN_CENTER,
    )


def info_box(mensaje, color=TEAL, bg=TEAL_SOFT, border_color=TEAL_BORDER,
             icono=ft.Icons.INFO_OUTLINE):
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icono, size=18, color=color),
                txt(mensaje, 9.8, color, W_500, max_lines=5, expand=True),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=bg,
        border=ft.Border.all(1, border_color),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=11, vertical=9),
    )


def error_state(mensaje, on_retry=None):
    children = [
        ft.Icon(ft.Icons.ERROR_OUTLINE, size=30, color=RED),
        txt(mensaje, 12, RED, W_500, align=ft.TextAlign.CENTER),
    ]
    if on_retry is not None:
        children.append(secondary_button("Reintentar", ft.Icons.REFRESH,
                                         on_retry, color=RED))
    return ft.Container(
        content=ft.Column(children, spacing=9,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=RED_SOFT,
        border=ft.Border.all(1, RED_BORDER),
        border_radius=14,
        padding=14,
    )


def loader(texto="Cargando…"):
    return ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=28, height=28, stroke_width=3,
                                color=TEAL),
                txt(texto, 11, MUTED),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=24),
        alignment=ALIGN_CENTER,
    )


def metric(label, valor, icon=None, color=TEAL, bg=TEAL_SOFT):
    children = []
    if icon is not None:
        children.append(
            ft.Container(
                content=ft.Icon(icon, size=15, color=color),
                width=28, height=28, bgcolor=bg, border_radius=8,
                alignment=ALIGN_CENTER,
            )
        )
    children.append(
        ft.Column(
            [txt(valor, 17, INK, W_700), txt(label, 9.5, MUTED, max_lines=1)],
            spacing=0,
            expand=True,
        )
    )
    return card(ft.Row(children, spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10, radius=12)


def top_bar(app, title, subtitle="", show_logout=True):
    return ft.Container(
        content=ft.Row(
            [
                brand_mark(38, 17),
                ft.Column(
                    [
                        txt(title, 17, INK, W_700, max_lines=1),
                        txt(subtitle or "Red comercial", 9.5, MUTED,
                            max_lines=1),
                    ],
                    spacing=0,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    icon_size=19,
                    icon_color=MUTED,
                    tooltip="Cerrar sesión",
                    on_click=lambda e: app.logout(),
                ) if show_logout else None,
            ],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=WHITE,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
        padding=ft.Padding.symmetric(horizontal=14, vertical=9),
    )


def bottom_nav(app, items, active):
    controles = []
    for key, label, icon in items:
        activo = key == active
        contenido = [
            ft.Stack(
                [
                    ft.Icon(icon, size=22,
                            color=TEAL if activo else MUTED),
                    ft.Container(
                        content=txt(str(len(app.cart)), 8, WHITE, W_700,
                                    align=ft.TextAlign.CENTER),
                        bgcolor=ORANGE,
                        border_radius=8,
                        width=15, height=15,
                        alignment=ALIGN_CENTER,
                        right=-8, top=-6,
                        visible=(key == "carrito" and bool(app.cart)),
                    ),
                ],
                width=26,
                height=24,
            ),
            txt(label, 9.5, TEAL_DARK if activo else MUTED,
                W_600 if activo else W_500),
        ]
        controles.append(
            ft.Container(
                content=ft.Column(
                    contenido,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                padding=ft.Padding.symmetric(vertical=7),
                on_click=lambda e, k=key: app.set_tab(k),
                ink=True,
                border_radius=10,
            )
        )
    return ft.Container(
        content=ft.Row(controles, spacing=2),
        bgcolor=WHITE,
        border=ft.Border(top=ft.BorderSide(1, BORDER)),
        padding=ft.Padding.only(left=6, right=6, bottom=4, top=2),
    )
