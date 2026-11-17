"""
Mayorix · Gestión de vendedores
===============================
La empresa crea, lista, edita y elimina los vendedores de su red comercial.
Todos los datos (incluida la foto opcional) se guardan en MongoDB.
"""

from __future__ import annotations

from datetime import date

import flet as ft

import data
import database
from . import ui
from .importers import bytes_de_archivo, comprimir_imagen_b64


COLORES = ["#0D9488", "#F97316", "#2563EB", "#7C3AED",
           "#0EA5E9", "#DB2777", "#D97706", "#4F46E5"]

CIUDADES = [
    "Barinas", "Caracas", "Maracaibo", "Valencia", "Barquisimeto",
    "Maracay", "San Cristóbal", "Puerto Ordaz", "Mérida", "Cumaná",
]


def _siguiente_id_local() -> str:
    numeros = []
    for vendedor_obj in data.VENDEDORES:
        try:
            numeros.append(int(vendedor_obj["id"].split("-")[1]))
        except (KeyError, ValueError):
            continue
    return f"VEN-{max(numeros, default=0) + 1:02d}"


def sincronizar_vendedores(db: database.Database) -> int:
    """Refleja los vendedores de MongoDB en la capa local de apoyo."""
    agregados = 0
    try:
        vendedores_db = db.listar_vendedores()
    except Exception:
        return 0
    por_codigo = {str(v.get("codigo", "")).upper(): v for v in data.VENDEDORES}
    for doc in vendedores_db:
        codigo = str(doc.get("codigo", "")).upper()
        if not codigo:
            continue
        existente = por_codigo.get(codigo)
        if existente:
            existente.update({
                "nombre": doc.get("nombre", existente.get("nombre", "")),
                "cedula": doc.get("cedula", existente.get("cedula", "")),
                "email": doc.get("email", existente.get("email", "")),
                "telefono": doc.get("telefono", existente.get("telefono", "")),
                "zona": doc.get("ciudad", existente.get("zona", "Venezuela")),
                "ciudad": doc.get("ciudad", existente.get("ciudad", "Venezuela")),
                "estado": doc.get("estado", existente.get("estado", "Activo")),
                "foto_b64": doc.get("foto_b64", existente.get("foto_b64", "")),
            })
            continue
        nombre = doc.get("nombre", "Vendedor")
        nuevo = {
            "id": _siguiente_id_local(),
            "nombre": nombre,
            "codigo": codigo,
            "cedula": doc.get("cedula", ""),
            "email": doc.get("email", ""),
            "telefono": doc.get("telefono", ""),
            "zona": doc.get("ciudad", "Venezuela"),
            "ciudad": doc.get("ciudad", "Venezuela"),
            "estado": doc.get("estado", "Activo"),
            "iniciales": ui.iniciales(nombre),
            "color": COLORES[len(data.VENDEDORES) % len(COLORES)],
            "ventas_mes": 0.0,
            "meta_mes": 40000.0,
            "comision_pct": 3.0,
            "comision_mes": 0.0,
            "saldo_billetera": 0.0,
            "liquidado_mes": 0.0,
            "ultima_actividad": "Recién registrado",
            "ingreso": date.today().isoformat(),
            "metodo_pago": "Pendiente de registro",
            "foto_b64": doc.get("foto_b64", ""),
        }
        data.VENDEDORES.append(nuevo)
        por_codigo[codigo] = nuevo
        agregados += 1
    return agregados


def _quitar_vendedor_local(codigo: str) -> None:
    data.VENDEDORES[:] = [
        v for v in data.VENDEDORES
        if str(v.get("codigo", "")).upper() != str(codigo).upper()
    ]


def _rendimiento(codigo: str) -> dict:
    for vendedor_obj in data.VENDEDORES:
        if str(vendedor_obj.get("codigo", "")).upper() == str(codigo).upper():
            return vendedor_obj
    return {}


def _avatar_vendedor(doc: dict, size=34):
    foto = doc.get("foto_b64", "")
    if foto:
        return ft.Container(
            content=ft.Image(src=foto, width=size, height=size, fit=ft.BoxFit.COVER),
            width=size,
            height=size,
            border_radius=size / 2,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
    rendimiento = _rendimiento(doc.get("codigo", ""))
    color = rendimiento.get("color", ui.TEAL)
    return ui.avatar(doc.get("nombre", "Vendedor"), color, size)


def vendedores_view(app) -> ft.Control:
    db = app.db
    estado = {"q": "", "ciudad": "Todas"}
    rows_host = ft.Column(spacing=0)
    count_label = ui.txt("", 10.5, ui.MUTED)
    total_footer = ui.txt("", 10.5, ui.INK, ui.W_600)

    try:
        vendedores = db.listar_vendedores()
        error_db = ""
    except Exception as exc:
        vendedores = []
        error_db = str(exc)

    if db.conectado:
        status_pill = ui.pill(db.estado_texto, ui.TEAL, ui.TEAL_SOFT,
                             icon=ft.Icons.CLOUD_DONE_OUTLINED, size=9.5)
    else:
        status_pill = ui.pill(db.estado_texto, ui.ORANGE, ui.ORANGE_SOFT,
                             icon=ft.Icons.CLOUD_OFF_OUTLINED, size=9.5)

    def recargar(update=True):
        nonlocal vendedores, error_db
        try:
            vendedores = db.listar_vendedores()
            error_db = ""
        except Exception as exc:
            error_db = str(exc)
        render(update=update)

    def menu_acciones(doc):
        return ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(
                    content=ui.txt("Ver perfil", 12),
                    icon=ft.Icons.VISIBILITY_OUTLINED,
                    on_click=lambda e, d=doc: abrir_detalle(d),
                ),
                ft.PopupMenuItem(
                    content=ui.txt("Editar vendedor", 12),
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=lambda e, d=doc: abrir_editar(d),
                ),
                ft.PopupMenuItem(
                    content=ui.txt("Eliminar", 12, ui.RED),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda e, d=doc: confirmar_eliminar(d),
                ),
            ],
            icon=ft.Icons.MORE_HORIZ,
            icon_size=18,
            icon_color=ui.MUTED,
            tooltip="Acciones",
            style=ft.ButtonStyle(padding=5, shape=ft.RoundedRectangleBorder(radius=6)),
        )

    def fila_vendedor(doc):
        rendimiento = _rendimiento(doc.get("codigo", ""))
        cliente_count = 0
        if rendimiento:
            cliente_count = len(data.clientes_de_vendedor(rendimiento.get("id", "")))
        return ui.table_row(
            [
                ui.cell(
                    ft.Row(
                        [
                            _avatar_vendedor(doc, 32),
                            ft.Column(
                                [
                                    ui.txt(doc.get("nombre", "—"), 11.5, ui.INK,
                                           ui.W_600, max_lines=1),
                                    ui.txt(
                                        f"{doc.get('cedula', 'Sin cédula')} · "
                                        f"{cliente_count} clientes",
                                        9.5, ui.MUTED, max_lines=1,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=9,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    3.6,
                ),
                ui.cell(ui.txt(doc.get("telefono", "—"), 10.5, "#475569",
                                ui.W_500), 2),
                ui.cell(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=12,
                                    color=ui.MUTED_2),
                            ui.txt(doc.get("ciudad", "—"), 10.5, "#475569", ui.W_500),
                        ],
                        spacing=3,
                        tight=True,
                    ),
                    1.8,
                ),
                ui.cell(ui.pill(doc.get("codigo", "—"), ui.BLUE, ui.BLUE_SOFT,
                                size=8.5), 1.5),
                ui.cell(ui.estado_vendedor_pill(doc.get("estado", "Activo")), 1.2),
                ui.cell(menu_acciones(doc), 1.0, ui.ALIGN_RIGHT),
            ],
            on_click=lambda e, d=doc: abrir_detalle(d),
            padding_v=9,
        )

    def render(update=False):
        q = estado["q"].strip().lower()
        filtrados = []
        for doc in vendedores:
            coincide_ciudad = (
                estado["ciudad"] == "Todas" or doc.get("ciudad") == estado["ciudad"]
            )
            coincide_q = (
                q in str(doc.get("nombre", "")).lower()
                or q in str(doc.get("cedula", "")).lower()
                or q in str(doc.get("codigo", "")).lower()
                or q in str(doc.get("ciudad", "")).lower()
                or q in str(doc.get("telefono", "")).lower()
            )
            if coincide_ciudad and coincide_q:
                filtrados.append(doc)
        rows_host.controls = [fila_vendedor(d) for d in filtrados] or [
            ui.empty_state("No hay vendedores que coincidan con el filtro.",
                           ft.Icons.BADGE_OUTLINED)
        ]
        count_label.value = f"{len(filtrados)} de {len(vendedores)} vendedores"
        clientes_total = sum(
            len(data.clientes_de_vendedor(_rendimiento(d.get("codigo", "")).get("id", "")))
            for d in filtrados
        )
        total_footer.value = f"{clientes_total} clientes asignados en la red"
        if update:
            app.page.update()

    def buscar(e):
        estado["q"] = e.control.value
        render(update=True)

    def filtrar_ciudad(e):
        estado["ciudad"] = e.control.value
        render(update=True)

    def abrir_crear(e=None):
        _dialogo_vendedor(app, None, on_saved=lambda: app.refresh())

    def abrir_editar(doc):
        _dialogo_vendedor(app, doc, on_saved=lambda: app.refresh())

    def abrir_detalle(doc):
        _dialogo_detalle(app, doc, abrir_editar, confirmar_eliminar)

    def confirmar_eliminar(doc):
        def eliminar(e):
            try:
                ok, mensaje = db.eliminar_vendedor(doc.get("codigo", ""))
            except Exception as exc:
                app.close_dialog()
                app.toast(f"No se pudo eliminar en MongoDB: {exc}", "error")
                return
            app.close_dialog()
            if ok:
                _quitar_vendedor_local(doc.get("codigo", ""))
                data.recalcular_ventas()
                app.refresh()
                app.toast(f"{doc.get('nombre', 'Vendedor')} eliminado de la red.",
                          "success")
            else:
                app.toast(mensaje, "warning")

        app.show_dialog(ui._dialog_base(
            "Eliminar vendedor",
            "Esta acción se aplica directamente en MongoDB",
            ft.Column(
                [
                    ui.info_box(
                        f"Se eliminará a {doc.get('nombre', '')} "
                        f"({doc.get('codigo', '')}) de la red comercial.",
                        ui.RED, ui.RED_SOFT, "#FECACA",
                        ft.Icons.WARNING_AMBER_ROUNDED,
                    ),
                    ui.txt("Los pedidos históricos se conservan.", 10.5, ui.MUTED),
                ],
                spacing=10,
            ),
            [
                ui.text_button("Cancelar", None, lambda e: app.close_dialog(),
                               color=ui.MUTED, size=11.5),
                ft.Button(
                    content=ui.txt("Eliminar vendedor", 11.5, ui.WHITE, ui.W_600),
                    on_click=eliminar,
                    bgcolor=ui.RED,
                    height=38,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=14),
                    ),
                ),
            ],
            width=470,
            icono=ft.Icons.DELETE_OUTLINE,
            color=ui.RED,
            bg=ui.RED_SOFT,
        ))

    opciones_ciudades = ["Todas"] + sorted({
        d.get("ciudad", "") for d in vendedores if d.get("ciudad")
    })
    toolbar = ft.Row(
        [
            ui.search_input("Buscar por nombre, cédula, código o ciudad…", buscar,
                            width=330),
            ui.toolbar_dropdown(
                [(c, c) for c in opciones_ciudades],
                estado["ciudad"], filtrar_ciudad, width=180,
            ),
            ft.Container(expand=True),
            count_label,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    footer = ui.table_footer(
        ft.Row(
            [
                ui.txt(f"Base de datos: {db.estado_texto}", 9.5, ui.MUTED),
                ft.Container(expand=True),
                total_footer,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    tabla = ui.table_container(
        [
            {"label": "Vendedor", "flex": 3.6},
            {"label": "Teléfono", "flex": 2},
            {"label": "Ciudad", "flex": 1.8},
            {"label": "Código", "flex": 1.5},
            {"label": "Estado", "flex": 1.2},
            {"label": "", "flex": 1.0, "align": ui.ALIGN_RIGHT},
        ],
        rows_host,
        footer,
    )

    render()

    total_ciudades = len({d.get("ciudad") for d in vendedores if d.get("ciudad")})
    activos = len([d for d in vendedores if d.get("estado", "Activo") == "Activo"])
    con_foto = len([d for d in vendedores if d.get("foto_b64")])

    stats = ft.Row(
        [
            ui.mini_stat("Vendedores", str(len(vendedores)),
                         "en MongoDB" if db.conectado else "en respaldo local",
                         ft.Icons.BADGE_OUTLINED, ui.TEAL, ui.TEAL_SOFT),
            ui.mini_stat("Ciudades cubiertas", str(total_ciudades),
                         "red nacional", ft.Icons.LOCATION_ON_OUTLINED,
                         ui.BLUE, ui.BLUE_SOFT),
            ui.mini_stat("Activos", str(activos),
                         "disponibles en la red", ft.Icons.VERIFIED_OUTLINED,
                         ui.PURPLE, ui.PURPLE_SOFT),
            ui.mini_stat("Perfiles con foto", str(con_foto),
                         "imagen opcional", ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                         ui.ORANGE, ui.ORANGE_SOFT),
        ],
        spacing=14,
    )

    contenido = [
        ui.page_header(
            "Gestión de vendedores",
            "Red comercial: nombre, cédula, teléfono, ciudad y foto opcional.",
            [
                ui.secondary_button("Actualizar", ft.Icons.REFRESH,
                                    lambda e: recargar(update=True)),
                ui.primary_button("Crear vendedor", ft.Icons.PERSON_ADD_ALT_1,
                                  abrir_crear),
            ],
            eyebrow="MONGODB · RED COMERCIAL",
        ),
        stats,
    ]
    if error_db:
        contenido.append(ui.info_box(
            f"No se pudo consultar vendedores: {error_db}", ui.RED, ui.RED_SOFT,
            "#FECACA", ft.Icons.ERROR_OUTLINE,
        ))
    elif not db.conectado:
        contenido.append(ui.info_box(
            f"{db.detalle_estado} Los vendedores creados se guardan en el respaldo "
            "local mientras MongoDB no esté disponible.",
            ui.ORANGE, ui.ORANGE_SOFT, ui.ORANGE_BORDER, ft.Icons.CLOUD_OFF_OUTLINED,
        ))
    contenido.extend([
        ft.Row([status_pill, ft.Container(expand=True)],
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        toolbar,
        tabla,
    ])
    return ft.Column(contenido, spacing=16)


# ---------------------------------------------------------------------------
# Diálogo de creación / edición
# ---------------------------------------------------------------------------


def _dialogo_vendedor(app, doc, on_saved):
    editando = doc is not None
    foto_state = {"b64": doc.get("foto_b64", "") if doc else ""}
    nombre_field = ui.base_text_field(
        value=doc.get("nombre", "") if doc else "", hint="Nombre y apellido")
    cedula_field = ui.base_text_field(
        value=doc.get("cedula", "") if doc else "", hint="V-14.256.789")
    telefono_field = ui.base_text_field(
        value=doc.get("telefono", "") if doc else "", hint="+58 414-000 0000")
    ciudad_inicial = doc.get("ciudad", "Barinas") if doc else "Barinas"
    if ciudad_inicial not in CIUDADES:
        CIUDADES.append(ciudad_inicial)
    ciudad_state = {"ciudad": ciudad_inicial}
    estado_state = {"estado": doc.get("estado", "Activo") if doc else "Activo"}
    error_lbl = ui.txt("", 10, ui.RED, ui.W_500, max_lines=2)

    contenido_preview = (
        ft.Image(src=foto_state["b64"], width=96, height=96, fit=ft.BoxFit.COVER)
        if foto_state["b64"] else ft.Column(
            [
                ft.Icon(ft.Icons.ADD_A_PHOTO_OUTLINED, size=24, color=ui.MUTED_2),
                ui.txt("Foto opcional", 9, ui.MUTED),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )
    foto_preview = ft.Container(
        content=contenido_preview,
        width=96,
        height=96,
        bgcolor=ui.SOFT,
        border=ft.Border.all(1, ui.BORDER),
        border_radius=10,
        alignment=ui.ALIGN_CENTER,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        padding=0 if foto_state["b64"] else 8,
    )

    async def elegir_foto(e):
        try:
            archivos = await app.file_picker.pick_files(
                dialog_title="Seleccionar foto del vendedor",
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
                with_data=True,
            )
        except Exception as exc:
            app.toast(f"No se pudo abrir la imagen: {exc}", "error")
            return
        if not archivos:
            return
        contenido = bytes_de_archivo(archivos[0])
        if not contenido:
            app.toast("No se pudo leer la imagen seleccionada.", "warning")
            return
        foto_state["b64"] = comprimir_imagen_b64(contenido)
        foto_preview.content = ft.Image(
            src=foto_state["b64"], width=96, height=96, fit=ft.BoxFit.COVER)
        foto_preview.padding = 0
        app.page.update()

    def elegir_ciudad(e):
        ciudad_state["ciudad"] = e.control.value
        app.page.update()

    def elegir_estado(e):
        estado_state["estado"] = e.control.value
        app.page.update()

    def guardar(e):
        nombre = str(nombre_field.value or "").strip()
        cedula = str(cedula_field.value or "").strip()
        telefono = str(telefono_field.value or "").strip()
        if not nombre or not cedula or not telefono:
            error_lbl.value = "Nombre, cédula y teléfono son obligatorios."
            app.page.update()
            return
        if not any(c.isdigit() for c in cedula):
            error_lbl.value = "Ingresa una cédula válida."
            app.page.update()
            return
        datos = {
            "nombre": nombre,
            "cedula": cedula,
            "telefono": telefono,
            "ciudad": ciudad_state["ciudad"],
            "foto_b64": foto_state["b64"],
            "estado": estado_state["estado"],
        }
        if editando:
            datos["codigo"] = doc.get("codigo", "")
        try:
            if editando:
                ok, mensaje, guardado = app.db.actualizar_vendedor(datos)
            else:
                ok, mensaje, guardado = app.db.crear_vendedor(datos)
        except Exception as exc:
            error_lbl.value = f"No se pudo guardar en MongoDB: {exc}"
            app.page.update()
            return
        if not ok:
            error_lbl.value = mensaje
            app.page.update()
            return
        sincronizar_vendedores(app.db)
        app.close_dialog()
        on_saved()
        if editando:
            app.toast("Vendedor actualizado correctamente.", "success")
        else:
            app.toast(
                f"Vendedor creado. Código {guardado.get('codigo', '')} · "
                "acceso con su cédula o código.", "success",
            )

    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    foto_preview,
                    ft.Column(
                        [
                            ui.secondary_button("Adjuntar foto",
                                                ft.Icons.UPLOAD_FILE_OUTLINED,
                                                elegir_foto, height=34, width=150),
                            ui.txt("Opcional · JPG/PNG. Se guarda en MongoDB.",
                                   8.5, ui.MUTED, max_lines=2),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ui.field_shell("Nombre y apellido", nombre_field),
            ft.Row(
                [
                    ui.field_shell("Cédula", cedula_field, expand=True),
                    ui.field_shell("Teléfono", telefono_field, expand=True),
                ],
                spacing=12,
            ),
            ft.Row(
                [
                    ui.labeled_dropdown(
                        "Ciudad", [(c, c) for c in CIUDADES],
                        ciudad_state["ciudad"], elegir_ciudad, expand=True,
                    ),
                ],
                spacing=12,
            ),
            ui.labeled_dropdown(
                "Estado", [(e, e) for e in ("Activo", "Vacaciones", "Inactivo")],
                estado_state["estado"], elegir_estado, expand=True,
            ) if editando else ft.Container(),
            error_lbl,
            ui.info_box(
                "El vendedor queda registrado en la red comercial con un código "
                "único generado automáticamente." if not editando else
                f"Editando {doc.get('codigo', '')} · los cambios se aplican en MongoDB.",
                ui.BLUE, ui.BLUE_SOFT, "#BFDBFE", ft.Icons.INFO_OUTLINE,
            ),
        ],
        spacing=12,
    )

    app.show_dialog(ui._dialog_base(
        "Editar vendedor" if editando else "Registrar vendedor",
        "Red comercial de Mayor Disluda · MongoDB",
        cuerpo,
        [
            ui.text_button("Cancelar", None, lambda e: app.close_dialog(),
                           color=ui.MUTED, size=11.5),
            ui.primary_button(
                "Guardar cambios" if editando else "Guardar vendedor",
                ft.Icons.PERSON_ADD_ALT_1, guardar, height=38,
            ),
        ],
        width=520,
        icono=ft.Icons.BADGE_OUTLINED,
        color=ui.TEAL,
        bg=ui.TEAL_SOFT,
    ))


# ---------------------------------------------------------------------------
# Diálogo de detalle
# ---------------------------------------------------------------------------


def _dialogo_detalle(app, doc, on_editar, on_eliminar):
    rendimiento = _rendimiento(doc.get("codigo", ""))
    clientes = []
    if rendimiento:
        clientes = data.clientes_de_vendedor(rendimiento.get("id", ""))
    color = rendimiento.get("color", ui.TEAL)
    foto = doc.get("foto_b64", "")

    cabecera = ft.Row(
        [
            ft.Container(
                content=ft.Image(src=foto, width=64, height=64, fit=ft.BoxFit.COVER)
                if foto else ui.avatar(doc.get("nombre", "V"), color, 64),
                width=64,
                height=64,
                border_radius=32,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
            ft.Column(
                [
                    ui.txt(doc.get("nombre", "—"), 16, ui.INK, ui.W_700),
                    ui.txt(f"{doc.get('codigo', '—')} · {doc.get('ciudad', '—')}",
                           10.5, ui.MUTED),
                    ft.Row(
                        [
                            ui.pill(doc.get("estado", "Activo"), ui.TEAL, ui.TEAL_SOFT,
                                    dot=True, size=9),
                            ui.pill(f"Cédula {doc.get('cedula', '—')}", ui.MUTED,
                                    ui.SOFT_2, size=9),
                        ],
                        spacing=6,
                    ),
                ],
                spacing=3,
                expand=True,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    datos = ft.Row(
        [
            ft.Column(
                [
                    ui.txt("Teléfono", 9.5, ui.MUTED),
                    ui.txt(doc.get("telefono", "—"), 11.5, ui.INK, ui.W_600),
                ],
                spacing=1, expand=1,
            ),
            ft.Column(
                [
                    ui.txt("Ciudad", 9.5, ui.MUTED),
                    ui.txt(doc.get("ciudad", "—"), 11.5, ui.INK, ui.W_600),
                ],
                spacing=1, expand=1,
            ),
            ft.Column(
                [
                    ui.txt("Código interno", 9.5, ui.MUTED),
                    ui.txt(doc.get("codigo", "—"), 11.5, ui.TEAL_DARK, ui.W_600),
                ],
                spacing=1, expand=1,
            ),
        ],
        spacing=12,
    )

    mini = ft.Row(
        [
            ui.mini_stat("Clientes", str(len(clientes)), "cartera asignada",
                         ft.Icons.PEOPLE_OUTLINE, ui.BLUE, ui.BLUE_SOFT),
            ui.mini_stat("Ventas mes", ui.compacto(rendimiento.get("ventas_mes", 0)),
                         "red comercial", ft.Icons.TRENDING_UP, ui.TEAL, ui.TEAL_SOFT),
            ui.mini_stat("Comisión", ui.compacto(rendimiento.get("comision_mes", 0)),
                         "del mes en curso", ft.Icons.PERCENT, ui.PURPLE, ui.PURPLE_SOFT),
        ],
        spacing=10,
    )

    clientes_host = ft.Column(spacing=7)
    for cliente in clientes:
        clientes_host.controls.append(
            ft.Row(
                [
                    ui.avatar(cliente["negocio"], ui.TEAL, 24, 9),
                    ui.txt(cliente["negocio"], 10, ui.INK, ui.W_500, expand=True,
                           max_lines=1),
                    ui.txt(ui.money(cliente["saldo"]), 9.5, ui.MUTED, ui.W_500),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    if not clientes:
        clientes_host.controls.append(
            ui.txt("Aún no tiene cartera asignada.", 10, ui.MUTED))

    cuerpo = ft.Column(
        [
            cabecera,
            datos,
            mini,
            ft.Column(
                [
                    ui.txt("Clientes asignados", 10.5, ui.INK, ui.W_600),
                    clientes_host,
                ],
                spacing=6,
            ),
        ],
        spacing=13,
    )

    app.show_dialog(ui._dialog_base(
        "Perfil del vendedor",
        f"{doc.get('codigo', '')} · Red comercial Mayor Disluda",
        cuerpo,
        [
            ui.text_button("Eliminar", ft.Icons.DELETE_OUTLINE,
                           lambda e: (app.close_dialog(), on_eliminar(doc)),
                           color=ui.RED, size=10.5),
            ui.text_button("Editar", ft.Icons.EDIT_OUTLINED,
                           lambda e: (app.close_dialog(), on_editar(doc)),
                           color=ui.TEAL, size=10.5),
            ui.text_button("Cerrar", None, lambda e: app.close_dialog(),
                           color=ui.MUTED, size=11.5),
        ],
        width=560,
        icono=ft.Icons.BADGE_OUTLINED,
        color=color,
        bg=ui.SOFT,
    ))
