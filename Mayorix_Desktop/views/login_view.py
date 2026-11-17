"""
Mayorix · Login de la Empresa
=============================
Acceso corporativo de Mayor Disluda. Las credenciales se validan contra la
colección `usuarios` de MongoDB.

Si la colección está vacía (primer arranque en producción), se habilita el
registro del administrador inicial. En cuanto existe al menos un usuario,
la opción de registro desaparece de la interfaz.
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import re
from pathlib import Path

import flet as ft

import database
from . import ui

ICONOS_LOGIN = Path(__file__).resolve().parent.parent / "iconos_desktop"
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _imagenes_login() -> list[str]:
    """Carga las imágenes locales como data URI para escritorio y web."""
    if not ICONOS_LOGIN.is_dir():
        return []
    imagenes = []
    for archivo in sorted(
        ICONOS_LOGIN.iterdir(), key=lambda p: p.name.lower()
    ):
        if not archivo.is_file() or archivo.suffix.lower() not in EXTENSIONES_IMAGEN:
            continue
        try:
            if archivo.stat().st_size > 8 * 1024 * 1024:
                continue
            mime = mimetypes.guess_type(str(archivo))[0] or "image/jpeg"
            contenido = base64.b64encode(archivo.read_bytes()).decode("ascii")
            imagenes.append(f"data:{mime};base64,{contenido}")
        except OSError:
            continue
    return imagenes


def _campo(hint: str, icono, password: bool = False) -> ft.TextField:
    return ft.TextField(
        hint_text=hint,
        border=ft.InputBorder.NONE,
        text_size=12.5,
        color=ui.INK,
        hint_style=ft.TextStyle(size=11.5, color=ui.MUTED_2),
        cursor_color=ui.TEAL,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=11),
        password=password,
        can_reveal_password=password,
        prefix_icon=icono,
        expand=True,
    )


def _envolver(label: str, campo: ft.TextField) -> ft.Column:
    return ft.Column(
        [
            ft.Text(
                label.upper(),
                size=8.5,
                color=ui.MUTED,
                weight=ui.W_700,
                style=ft.TextStyle(letter_spacing=0.6),
            ),
            ft.Container(
                content=campo,
                bgcolor=ui.SOFT,
                border=ft.Border.all(1, ui.BORDER),
                border_radius=9,
                height=44,
            ),
        ],
        spacing=5,
    )


def _email_valido(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def login_view(
    page: ft.Page,
    db: database.Database,
    on_empresa,
    email_inicial: str = "",
) -> ft.Control:
    page.bgcolor = ui.BG
    page.padding = 0

    email_field = _campo("nombre@mayordisluda.com.ve", ft.Icons.EMAIL_OUTLINED)
    email_field.value = email_inicial
    password_field = _campo("Contraseña", ft.Icons.LOCK_OUTLINE, password=True)
    error_lbl = ui.txt("", 9.5, ui.RED, ui.W_500, max_lines=2)

    try:
        total_usuarios = db.contar_usuarios()
    except Exception:
        total_usuarios = None
    puede_registrar = total_usuarios == 0

    def mostrar_aviso(mensaje: str, tono: str = "success"):
        color = {"success": ui.TEAL, "error": ui.RED, "info": ui.BLUE}.get(
            tono, ui.TEAL
        )
        icono = {
            "success": ft.Icons.CHECK_CIRCLE_OUTLINED,
            "error": ft.Icons.ERROR_OUTLINE,
            "info": ft.Icons.INFO_OUTLINE,
        }.get(tono, ft.Icons.INFO_OUTLINE)
        page.show_dialog(ft.SnackBar(
            content=ft.Row(
                [
                    ft.Icon(icono, size=16, color=color),
                    ui.txt(mensaje, 11.5, ui.WHITE, ui.W_500, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ui.INK,
            behavior=ft.SnackBarBehavior.FLOATING,
            width=440,
            duration=3600,
        ))

    # ------------------------------------------------------------------
    # Conexión MongoDB
    # ------------------------------------------------------------------

    def detalle_conexion(e=None):
        conectado = db.conectado
        dialogo = ft.AlertDialog(
            modal=True,
            scrollable=True,
            bgcolor=ui.WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Row(
                [
                    ui.icon_box(ft.Icons.STORAGE_OUTLINED, ui.TEAL, ui.TEAL_SOFT,
                                36, 18, 8),
                    ui.txt("Conexión MongoDB", 16, ui.INK, ui.W_700),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=450,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ui.txt("Estado", 10, ui.MUTED),
                                ft.Container(expand=True),
                                ui.pill(
                                    db.estado_texto,
                                    ui.TEAL if conectado else ui.ORANGE,
                                    ui.TEAL_SOFT if conectado else ui.ORANGE_SOFT,
                                ),
                            ]
                        ),
                        ft.Row(
                            [
                                ui.txt("Base de datos", 10, ui.MUTED),
                                ft.Container(expand=True),
                                ui.txt(db.db_name, 9.5, ui.INK, ui.W_500),
                            ]
                        ),
                        ft.Row(
                            [
                                ui.txt("Usuarios", 10, ui.MUTED),
                                ft.Container(expand=True),
                                ui.txt(
                                    "—" if total_usuarios is None else str(total_usuarios),
                                    9.5, ui.INK, ui.W_500,
                                ),
                            ]
                        ),
                        ui.info_box(
                            db.detalle_estado if not conectado else
                            "Conexión activa. Las cuentas y los datos se guardan "
                            "en MongoDB.",
                            ui.ORANGE if not conectado else ui.TEAL,
                            ui.ORANGE_SOFT if not conectado else ui.TEAL_SOFT,
                            ui.ORANGE_BORDER if not conectado else ui.TEAL_BORDER,
                            ft.Icons.INFO_OUTLINE,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            actions=[
                ui.text_button("Reconectar", ft.Icons.REFRESH, reconectar,
                               color=ui.TEAL, size=11.5),
                ui.text_button("Cerrar", None, lambda ev: page.pop_dialog(),
                               color=ui.MUTED, size=11.5),
            ],
        )
        page.show_dialog(dialogo)

    def reconectar(e=None):
        ok, mensaje = db.reconectar()
        page.pop_dialog()
        page.controls.clear()
        page.add(login_view(page, db, on_empresa, email_inicial=email_field.value or ""))
        page.update()
        mostrar_aviso(
            "MongoDB conectado correctamente." if ok else mensaje,
            "success" if ok else "error",
        )

    # ------------------------------------------------------------------
    # Registro del primer administrador
    # ------------------------------------------------------------------

    def abrir_registro(e=None):
        nombre_field = ui.base_text_field(hint="Nombre y apellido")
        correo_field = ui.base_text_field(hint="nombre@mayordisluda.com.ve")
        clave_field = ui.base_text_field(hint="Mínimo 8 caracteres", password=True)
        confirmar_field = ui.base_text_field(hint="Repite la contraseña", password=True)
        registro_error = ui.txt("", 9.5, ui.RED, ui.W_500, max_lines=2)

        def crear_cuenta(ev):
            nombre = str(nombre_field.value or "").strip()
            correo = str(correo_field.value or "").strip().lower()
            clave = str(clave_field.value or "")
            confirmar = str(confirmar_field.value or "")
            if not nombre or not correo:
                registro_error.value = "Completa el nombre y el correo corporativo."
                page.update()
                return
            if not _email_valido(correo):
                registro_error.value = "Ingresa un correo corporativo válido."
                page.update()
                return
            if len(clave) < 8:
                registro_error.value = "La contraseña debe tener al menos 8 caracteres."
                page.update()
                return
            if clave != confirmar:
                registro_error.value = "Las contraseñas no coinciden."
                page.update()
                return
            try:
                ok, mensaje, _ = db.crear_primer_usuario({
                    "nombre": nombre,
                    "email": correo,
                    "password": clave,
                })
            except Exception as exc:
                registro_error.value = f"No se pudo registrar en MongoDB: {exc}"
                page.update()
                return
            if not ok:
                registro_error.value = mensaje
                page.update()
                return
            page.pop_dialog()
            page.controls.clear()
            page.add(login_view(page, db, on_empresa, email_inicial=correo))
            page.update()
            mostrar_aviso(
                "Administrador creado. Ya puedes iniciar sesión con tu cuenta.",
                "success",
            )

        cuerpo = ft.Column(
            [
                _envolver("Nombre completo", nombre_field),
                _envolver("Correo corporativo", correo_field),
                _envolver("Contraseña", clave_field),
                _envolver("Confirmar contraseña", confirmar_field),
                registro_error,
                ui.info_box(
                    "Cuenta inicial del sistema. El registro se ocultará al "
                    "crear este administrador."
                    if db.conectado else
                    "Modo respaldo activo: la cuenta se conservará solo durante "
                    "esta sesión hasta restablecer MongoDB.",
                    ui.TEAL if db.conectado else ui.ORANGE,
                    ui.TEAL_SOFT if db.conectado else ui.ORANGE_SOFT,
                    ui.TEAL_BORDER if db.conectado else ui.ORANGE_BORDER,
                    ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                ),
            ],
            spacing=12,
        )
        page.show_dialog(ui._dialog_base(
            "Registrar administrador",
            "Cuenta inicial de administración · Mayor Disluda",
            cuerpo,
            [
                ui.text_button("Cancelar", None, lambda ev: page.pop_dialog(),
                               color=ui.MUTED, size=11.5),
                ui.primary_button("Crear cuenta", ft.Icons.PERSON_ADD_ALT_1,
                                  crear_cuenta, height=38),
            ],
            width=460,
            icono=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
            color=ui.TEAL,
            bg=ui.TEAL_SOFT,
        ))

    # ------------------------------------------------------------------
    # Inicio de sesión
    # ------------------------------------------------------------------

    def entrar(e=None):
        email = str(email_field.value or "").strip().lower()
        password = str(password_field.value or "")
        if not email or not password:
            error_lbl.value = "Ingresa tu correo y contraseña."
            page.update()
            return
        error_lbl.value = ""
        page.update()
        usuarios = total_usuarios
        if not db.conectado:
            # La PC pudo arrancar sin red: reintenta antes de validar credenciales.
            db.reconectar_rapido()
            try:
                usuarios = db.contar_usuarios()
            except Exception:
                usuarios = None
        if usuarios == 0:
            error_lbl.value = (
                "No hay administradores registrados. Crea la cuenta inicial."
                if db.conectado
                else db.detalle_estado
            )
            page.update()
            return
        try:
            usuario = db.autenticar_empresa(email, password)
        except Exception as exc:
            error_lbl.value = f"No se pudo validar el acceso: {exc}"
            page.update()
            return
        if usuario:
            on_empresa(usuario)
        else:
            error_lbl.value = "Correo o contraseña incorrectos."
            page.update()

    email_field.on_submit = entrar
    password_field.on_submit = entrar

    conectado = db.conectado
    estado_conexion = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    width=7, height=7,
                    bgcolor="#2DD4BF" if conectado else ui.ORANGE,
                    border_radius=4,
                ),
                ui.txt(
                    "MongoDB conectado" if conectado else "MongoDB sin conexión",
                    8.8, "#CBD5E1", ui.W_500, expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.INFO_OUTLINE,
                    icon_size=13,
                    icon_color="#94A3B8",
                    tooltip="Estado de la conexión",
                    on_click=detalle_conexion,
                    style=ft.ButtonStyle(padding=4),
                ),
            ],
            spacing=7,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        border=ft.Border.all(1, "#1E293B"),
        border_radius=8,
        padding=ft.Padding.only(left=10, right=2, top=2, bottom=2),
    )

    imagenes_login = _imagenes_login()

    def _capa_login(src: str, visible: bool) -> ft.Container:
        """Capa de fondo que siempre cubre el panel completo."""
        return ft.Container(
            expand=True,
            opacity=1.0 if visible else 0.0,
            animate_opacity=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT),
            image=ft.DecorationImage(src=src, fit=ft.BoxFit.COVER),
        )

    if imagenes_login:
        capa_a = _capa_login(imagenes_login[0], True)
        capa_b = _capa_login(imagenes_login[1 % len(imagenes_login)], False)
        galeria_login = ft.Stack([capa_a, capa_b], expand=True)
    else:
        galeria_login = ft.Container(expand=True, bgcolor=ui.INK)

    contenido_marca = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.LOCAL_MALL_OUTLINED, size=22,
                                            color=ui.WHITE),
                            width=40, height=40, bgcolor=ui.TEAL, border_radius=10,
                            alignment=ui.ALIGN_CENTER,
                        ),
                        ft.Column(
                            [
                                ui.txt("Mayorix", 22, ui.WHITE, ui.W_700),
                                ft.Text(
                                    "POWERED BY DROPTECH",
                                    size=7.5, color="#CBD5E1", weight=ui.W_700,
                                    style=ft.TextStyle(letter_spacing=1.2),
                                ),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                ft.Column(
                    [
                        ui.txt("Mayor Disluda", 24, ui.WHITE, ui.W_700),
                        ui.txt("Administración central", 11, "#E2E8F0"),
                    ],
                    spacing=6,
                ),
                ft.Container(expand=True),
                estado_conexion,
                ui.txt("Repuestos automotrices · Venezuela", 8.3, "#CBD5E1"),
            ],
            spacing=18,
            expand=True,
        ),
        padding=ft.Padding.symmetric(horizontal=34, vertical=32),
        expand=True,
    )

    capa_oscura = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.70, "#0B1220"),
    )

    panel_marca = ft.Container(
        width=360,
        bgcolor=ui.INK,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Stack(
            [galeria_login, capa_oscura, contenido_marca],
            expand=True,
        ),
    )

    if len(imagenes_login) > 1:
        async def rotar_imagenes_login():
            indice = 0
            mostrar_a = True
            while True:
                await asyncio.sleep(5.0)
                try:
                    indice = (indice + 1) % len(imagenes_login)
                    nueva = capa_b if mostrar_a else capa_a
                    anterior = capa_a if mostrar_a else capa_b
                    nueva.image = ft.DecorationImage(
                        src=imagenes_login[indice], fit=ft.BoxFit.COVER,
                    )
                    nueva.opacity = 1.0
                    anterior.opacity = 0.0
                    mostrar_a = not mostrar_a
                    page.update()
                except Exception:
                    break

        page.run_task(rotar_imagenes_login)

    registro_link = ft.Row(
        [
            ui.text_button(
                "Registrar administrador", ft.Icons.PERSON_ADD_ALT_1,
                abrir_registro, color=ui.TEAL, size=9.8, height=26,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    panel_login = ft.Container(
        expand=True,
        bgcolor=ui.WHITE,
        padding=ft.Padding.symmetric(horizontal=52, vertical=44),
        content=ft.Column(
            [
                ui.txt("Acceso de empresa", 25, ui.INK, ui.W_700),
                ui.txt("Ingresa con tus credenciales corporativas.", 11, ui.MUTED),
                ft.Container(height=10),
                _envolver("Correo corporativo", email_field),
                _envolver("Contraseña", password_field),
                error_lbl,
                ft.Container(height=2),
                ui.primary_button("Iniciar sesión", ft.Icons.ARROW_FORWARD, entrar,
                                  width=380, height=44),
                registro_link if puede_registrar else ft.Container(),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ui.txt("© 2026 DropeTech", 8.3, ui.MUTED_2),
                        ft.Container(expand=True),
                        ui.txt("Mayorix v2.1.5", 8.3, ui.MUTED_2),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=15,
            expand=True,
        ),
    )

    tarjeta = ft.Container(
        width=960,
        height=560,
        bgcolor=ui.WHITE,
        border=ft.Border.all(1, ui.BORDER),
        border_radius=18,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(
            blur_radius=38,
            color=ft.Colors.with_opacity(0.08, ui.INK),
            offset=ft.Offset(0, 12),
        ),
        content=ft.Row(
            [panel_marca, panel_login],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    return ft.Container(
        expand=True,
        bgcolor=ui.BG,
        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
        alignment=ui.ALIGN_CENTER,
        content=tarjeta,
    )
