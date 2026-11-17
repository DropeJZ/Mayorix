"""Acceso y primer registro por cédula con código de verificación."""

from __future__ import annotations

import time

import flet as ft

import config
import ui_mobile as ui


def login_view(app) -> ft.Control:
    modo = app.login_modo
    if modo not in ("login", "registro", "codigo"):
        modo = "login"

    mensaje = ui.txt("", 10.5, ui.MUTED, max_lines=3,
                     align=ft.TextAlign.CENTER)
    boton = None

    async def ejecutar(accion, texto_espera):
        nonlocal boton
        if boton is not None:
            boton.disabled = True
            boton.opacity = 0.6
        mensaje.value = texto_espera
        mensaje.color = ui.MUTED
        app.page.update()
        try:
            await accion()
        except Exception as exc:
            texto = str(exc) or "No se pudo completar la operación."
            mensaje.value = texto
            mensaje.color = ui.RED
            if boton is not None:
                boton.disabled = False
                boton.opacity = 1.0
            app.page.update()

    # ------------------------------------------------------------------
    # Marca centrada
    # ------------------------------------------------------------------
    marca = ft.Column(
        [
            ui.brand_mark(62, 29),
            ui.txt("Mayorix", 31, ui.INK, ui.W_700,
                   align=ft.TextAlign.CENTER),
            ui.txt("MAYOR DISLUDA · RED COMERCIAL", 8.8, ui.TEAL, ui.W_700,
                   align=ft.TextAlign.CENTER),
        ],
        spacing=7,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    campos = []
    subtitulo = ""

    if modo == "login":
        subtitulo = "Acceso de vendedor"
        cedula = ui.text_field(
            "Cédula del vendedor",
            on_submit=lambda e: app.page.run_task(
                ejecutar,
                lambda: app.login(
                    str(cedula.value or ""), str(password.value or "")
                ),
                "Validando credenciales…",
            ),
        )
        password = ui.text_field(
            "Contraseña",
            password=True,
            on_submit=lambda e: app.page.run_task(
                ejecutar,
                lambda: app.login(
                    str(cedula.value or ""), str(password.value or "")
                ),
                "Validando credenciales…",
            ),
        )
        campos = [
            ui.field_shell("CÉDULA", cedula),
            ui.field_shell("CONTRASEÑA", password),
        ]
        boton = ui.action_button(
            "Ingresar",
            ft.Icons.LOGIN,
            lambda e: app.page.run_task(
                ejecutar,
                lambda: app.login(
                    str(cedula.value or ""), str(password.value or "")
                ),
                "Validando credenciales…",
            ),
        )
        pie_modo = ui.secondary_button(
            "Primer registro con mi cédula",
            ft.Icons.PERSON_ADD_OUTLINED,
            lambda e: _cambiar_modo(app, "registro"),
        )

    elif modo == "registro":
        subtitulo = "Primer registro"
        cedula = ui.text_field(
            "Cédula registrada por la empresa",
            on_submit=lambda e: app.page.run_task(
                ejecutar,
                lambda: app.solicitar_registro(str(cedula.value or "")),
                "Validando cédula…",
            ),
        )
        campos = [
            ui.field_shell(
                "CÉDULA",
                cedula,
                "La cédula debe existir en la red comercial de Mayor Disluda.",
            ),
            ui.info_box(
                "Al validar la cédula se genera un código único. El "
                "administrador lo recibe en su panel de escritorio y te lo "
                "facilita para crear tu contraseña.",
                ui.TEAL, ui.TEAL_SOFT, ui.TEAL_BORDER,
                ft.Icons.PHONE_ANDROID,
            ),
        ]
        boton = ui.action_button(
            "Validar cédula",
            ft.Icons.VERIFIED_USER_OUTLINED,
            lambda e: app.page.run_task(
                ejecutar,
                lambda: app.solicitar_registro(str(cedula.value or "")),
                "Validando cédula…",
            ),
        )
        pie_modo = _enlace(
            "Volver al acceso",
            lambda e: _cambiar_modo(app, "login"),
            color=ui.MUTED,
        )

    else:  # código de verificación
        subtitulo = "Verifica tu identidad"
        vendedor = app.registro_vendor or {}
        restante = max(0, int(app.registro_expira - time.time()))
        minutos = max(1, (restante + 59) // 60) if restante else 0
        cédula_vendor = vendedor.get("cedula", app.registro_cedula)
        codigo = ui.text_field(
            "Código de 6 dígitos",
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
            on_submit=lambda e: app.page.run_task(
                ejecutar,
                lambda: app.confirmar_registro(
                    str(codigo.value or ""), str(password.value or "")
                ),
                "Creando acceso…",
            ),
        )
        password = ui.text_field("Nueva contraseña (8+ caracteres)",
                                 password=True)
        confirmar = ui.text_field("Confirmar contraseña", password=True)
        campos = [
            ft.Column(
                [
                    ui.pill("Solicitud enviada", ui.ORANGE, ui.ORANGE_SOFT,
                            dot=True, size=10),
                    ui.txt(vendedor.get("nombre", "Vendedor"), 16, ui.INK,
                           ui.W_700, align=ft.TextAlign.CENTER),
                    ui.txt(f"Cédula {cédula_vendor}", 10.5, ui.MUTED,
                           align=ft.TextAlign.CENTER),
                    ui.txt(
                        f"El código vence en {minutos} min. El administrador "
                        "lo ve en el panel de escritorio.",
                        9.5, ui.MUTED, align=ft.TextAlign.CENTER,
                        max_lines=3,
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ui.field_shell("CÓDIGO DE VERIFICACIÓN", codigo),
            ui.field_shell("CONTRASEÑA DEFINITIVA", password),
            ui.field_shell("CONFIRMAR CONTRASEÑA", confirmar),
        ]

        async def crear_clave():
            if str(password.value or "") != str(confirmar.value or ""):
                raise ValueError("Las contraseñas no coinciden.")
            if len(str(password.value or "")) < 8:
                raise ValueError(
                    "La contraseña debe tener al menos 8 caracteres."
                )
            await app.confirmar_registro(
                str(codigo.value or ""), str(password.value or "")
            )

        boton = ui.action_button(
            "Crear mi contraseña",
            ft.Icons.LOCK_OPEN_OUTLINED,
            lambda e: app.page.run_task(
                ejecutar, crear_clave, "Creando acceso…"
            ),
        )
        pie_modo = _enlace(
            "Volver al acceso",
            lambda e: _cambiar_modo(app, "login"),
            color=ui.MUTED,
        )

    formulario = ft.Column(
        [
            ui.txt(subtitulo, 19, ui.INK, ui.W_700,
                   align=ft.TextAlign.CENTER),
            ui.txt(
                "Identificación exclusiva para vendedores autorizados."
                if modo == "login" else
                "Completa los pasos para activar tu acceso móvil.",
                10.5, ui.MUTED, align=ft.TextAlign.CENTER, max_lines=2,
            ),
            ft.Container(height=4),
            *campos,
            mensaje,
            boton,
            pie_modo,
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    contenido = ft.Container(
        content=ft.Column(
            [
                marca,
                ft.Container(
                    content=formulario,
                    bgcolor=ui.WHITE,
                    border=ft.Border.all(1, ui.BORDER),
                    border_radius=18,
                    padding=ft.Padding.symmetric(horizontal=17, vertical=18),
                ),
                ui.txt(
                    "Conexión cifrada directa con MongoDB Atlas",
                    9, ui.MUTED_2, align=ft.TextAlign.CENTER,
                ),
                ui.txt(
                    f"Mayorix Vendedor v{config.APP_VERSION} · DropeTech",
                    9, ui.MUTED_2, align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        ),
        width=max(280, min(int(app.page.width or 380) - 40, 380)),
    )

    return ft.Container(
        content=ft.SafeArea(
            ft.Container(
                content=ft.Column(
                    [contenido],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=18),
                expand=True,
            ),
            expand=True,
        ),
        bgcolor=ui.BG,
        expand=True,
    )


def _cambiar_modo(app, modo: str):
    app.login_modo = modo
    app.refresh_login()


def _enlace(label, on_click, color=ui.TEAL):
    return ft.Container(
        content=ui.txt(label, 11.5, color, ui.W_600,
                       align=ft.TextAlign.CENTER),
        height=36,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        border_radius=8,
        bgcolor=ui.WHITE,
    )
