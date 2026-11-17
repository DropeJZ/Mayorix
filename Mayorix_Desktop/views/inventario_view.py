"""
Mayorix · Inventario de repuestos
=================================
Lista limpia y directa del catálogo conectado a MongoDB:

    Código · Descripción · Marca · Precio (USD)

La categoría y la familia se conservan en la base de datos para clasificación
interna, pero no se muestran en la vista principal para mantener el foco en el
stock y los precios. El listado se ordena alfabéticamente por descripción.
"""

from __future__ import annotations

import asyncio

import flet as ft

import data
from . import ui
from .importers import (
    bytes_de_archivo,
    comprimir_imagen_b64,
    parsear_excel,
    parsear_pdf,
    simular_ocr,
)


def inventario_view(app) -> ft.Control:
    db = app.db
    estado = {
        "q": "", "ves": set(), "pagina": 1, "por_pagina": 20,
        "total": 0, "total_paginas": 1, "version_busqueda": 0,
    }
    repuestos: list[dict] = []
    rows_host = ft.Column(spacing=0)
    count_label = ui.txt("", 10.5, ui.MUTED)
    footer_total = ui.txt("", 10.5, ui.INK, ui.W_600)
    pagina_label = ui.txt("", 10.5, ui.MUTED)
    boton_anterior = ui.secondary_button(
        "Anterior", ft.Icons.CHEVRON_LEFT,
        lambda e: cargar_pagina(estado["pagina"] - 1),
        height=30, disabled=True,
    )
    boton_siguiente = ui.secondary_button(
        "Siguiente", ft.Icons.CHEVRON_RIGHT,
        lambda e: cargar_pagina(estado["pagina"] + 1),
        height=30, disabled=True,
    )
    error_db = ""

    def moneda_de(repuesto) -> str:
        return "VES" if repuesto.get("codigo") in estado["ves"] else "USD"

    def alternar_moneda(codigo):
        if codigo in estado["ves"]:
            estado["ves"].remove(codigo)
        else:
            estado["ves"].add(codigo)
        render(update=True)

    def cargar_pagina(pagina=1, update=True):
        nonlocal repuestos, error_db
        busqueda = estado["q"].strip()
        try:
            total = db.contar_inventario_filtrado(busqueda)
            total_paginas = max(1, (total + estado["por_pagina"] - 1)
                                // estado["por_pagina"])
            pagina = max(1, min(int(pagina), total_paginas))
            docs = db.listar_inventario_pagina(
                (pagina - 1) * estado["por_pagina"],
                estado["por_pagina"],
                busqueda,
            )
            repuestos = docs
            estado["total"] = total
            estado["total_paginas"] = total_paginas
            estado["pagina"] = pagina
            error_db = ""
        except Exception as exc:
            repuestos = []
            estado["total"] = 0
            estado["total_paginas"] = 1
            estado["pagina"] = 1
            error_db = str(exc)
        render(update=update)

    # ------------------------------------------------------------------
    # Lista
    # ------------------------------------------------------------------

    def celda_precio(repuesto):
        codigo = repuesto.get("codigo", "")
        moneda = moneda_de(repuesto)
        precio = ui.monto_segun_moneda(repuesto.get("precio", 0), moneda)
        return ft.Container(
            content=ft.Column(
                [
                    ui.txt(precio, 11.5,
                           ui.TEAL_DARK if moneda == "VES" else ui.INK, ui.W_600),
                    ui.txt(moneda, 8, ui.MUTED, ui.W_500),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.END,
            ),
            on_click=lambda e, c=codigo: alternar_moneda(c),
            ink=True,
            tooltip="Alternar USD / VES",
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=5, vertical=2),
        )

    def fila_repuesto(repuesto):
        return ui.table_row(
            [
                ui.cell(ui.txt(repuesto.get("codigo", "—"), 10.5, "#4B5563",
                                ui.W_600), 1.6),
                ui.cell(ui.txt(repuesto.get("descripcion", "—"), 11.3,
                                ui.INK, ui.W_500, max_lines=2), 5.8),
                ui.cell(ui.txt(repuesto.get("marca", "—"), 10.5, "#4B5563",
                                ui.W_500, max_lines=1), 2.2),
                ui.cell(celda_precio(repuesto), 1.9, ui.ALIGN_RIGHT),
            ],
            on_click=lambda e, r=repuesto: abrir_detalle(r),
            padding_v=11,
        )

    def render(update=False):
        rows_host.controls = [fila_repuesto(r) for r in repuestos] or [
            ui.empty_state(
                "Aún no hay repuestos registrados." if estado["total"] == 0
                else "No hay repuestos para esta búsqueda.",
                ft.Icons.INVENTORY_2_OUTLINED if estado["total"] == 0
                else ft.Icons.SEARCH_OFF,
            )
        ]
        count_label.value = f"{len(repuestos)} de {estado['total']}"
        total = sum(float(r.get("precio", 0) or 0) for r in repuestos)
        footer_total.value = (
            f"{len(repuestos)} repuestos · {ui.money(total, 2)}"
            if repuestos else "Sin resultados"
        )
        pagina_label.value = (
            f"Página {estado['pagina']} de {estado['total_paginas']}"
        )
        boton_anterior.disabled = estado["pagina"] <= 1
        boton_siguiente.disabled = estado["pagina"] >= estado["total_paginas"]
        if update:
            app.page.update()

    async def _buscar_debounced(version, texto):
        await asyncio.sleep(0.28)
        if version != estado["version_busqueda"]:
            return
        estado["q"] = texto
        cargar_pagina(1)

    def buscar(e):
        estado["version_busqueda"] += 1
        app.page.run_task(
            _buscar_debounced, estado["version_busqueda"],
            e.control.value,
        )

    # ------------------------------------------------------------------
    # Importación con progreso
    # ------------------------------------------------------------------

    def _progreso_importacion(total_archivos: int):
        barra = ft.ProgressBar(
            value=0.02, bar_height=8, color=ui.TEAL, bgcolor=ui.TEAL_SOFT,
            border_radius=4,
        )
        porcentaje = ui.txt("2%", 10, ui.TEAL_DARK, ui.W_700)
        estado_txt = ui.txt("Preparando importación…", 12, ui.INK, ui.W_600)
        detalle = ui.txt(
            f"{total_archivos} archivo(s) seleccionado(s)", 9.5, ui.MUTED,
            max_lines=2,
        )
        dialogo = ft.AlertDialog(
            modal=True,
            scrollable=True,
            bgcolor=ui.WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Row(
                [
                    ui.icon_box(ft.Icons.UPLOAD_FILE_OUTLINED, ui.TEAL,
                                ui.TEAL_SOFT, 38, 19, 9),
                    ft.Column(
                        [
                            ui.txt("Importando inventario", 16, ui.INK, ui.W_700),
                            ui.txt("Análisis y guardado en MongoDB", 9.5, ui.MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=11,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                width=430,
                content=ft.Column(
                    [
                        ft.Row(
                            [estado_txt, ft.Container(expand=True), porcentaje],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        barra,
                        detalle,
                    ],
                    spacing=8,
                ),
            ),
        )
        app.show_dialog(dialogo)

        def actualizar(valor, mensaje=None, sub=None):
            avance = max(0.0, min(1.0, float(valor)))
            try:
                barra.value = avance
                porcentaje.value = f"{avance * 100:.0f}%"
                if mensaje:
                    estado_txt.value = mensaje
                if sub is not None:
                    detalle.value = sub
                app.page.update()
            except Exception:
                pass

        return actualizar

    def _analizar_archivo(archivo):
        nombre = getattr(archivo, "name", "archivo")
        extension = str(nombre).lower().rsplit(".", 1)[-1]
        contenido = bytes_de_archivo(archivo)
        if not contenido:
            return nombre, [], [f"{nombre}: no se pudo leer el archivo."]
        try:
            if extension == "xlsx":
                docs, errs = parsear_excel(contenido)
            elif extension == "pdf":
                docs, errs = parsear_pdf(contenido)
            else:
                docs, errs = [], ["Formato no soportado."]
            return nombre, docs, [f"{nombre}: {e}" for e in errs]
        except Exception as exc:
            return nombre, [], [f"{nombre}: {exc}"]

    async def importar_archivos(e):
        try:
            archivos = await app.file_picker.pick_files(
                dialog_title="Importar inventario",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx", "pdf"],
                allow_multiple=True,
                with_data=True,
            )
        except Exception as exc:
            app.toast(f"No se pudo abrir el selector: {exc}", "error")
            return
        if not archivos:
            return

        total_archivos = len(archivos)
        actualizar = _progreso_importacion(total_archivos)
        documentos: list[dict] = []
        errores: list[str] = []

        try:
            for indice, archivo in enumerate(archivos, start=1):
                nombre_visible = getattr(archivo, "name", "archivo")
                actualizar(
                    0.05 + 0.30 * (indice - 1) / total_archivos,
                    f"Analizando {nombre_visible}…",
                    f"Archivo {indice} de {total_archivos}",
                )
                _nombre, docs, errs = await asyncio.to_thread(
                    _analizar_archivo, archivo
                )
                documentos.extend(docs)
                errores.extend(errs)
                actualizar(
                    0.05 + 0.30 * indice / total_archivos,
                    "Archivo procesado",
                    f"{len(documentos)} repuestos detectados",
                )

            if not documentos:
                app.close_dialog()
                app.toast(
                    errores[0] if errores else "No se detectaron repuestos.",
                    "warning",
                )
                return

            actualizar(
                0.38, "Guardando en MongoDB…",
                f"{len(documentos)} repuestos en cola",
            )
            progreso_db = {"hechos": 0, "total": len(documentos)}

            def reportar(hechos, total, insertados_parcial, actualizados_parcial):
                progreso_db["hechos"] = hechos
                progreso_db["total"] = total

            tarea = asyncio.create_task(asyncio.to_thread(
                db.importar_repuestos, documentos, reportar
            ))
            while not tarea.done():
                await asyncio.sleep(0.07)
                total = progreso_db["total"] or len(documentos)
                hechos = progreso_db["hechos"]
                avance = (hechos / total) if total else 0
                actualizar(
                    0.40 + 0.55 * avance,
                    "Guardando repuestos…",
                    f"{hechos} de {total} procesados",
                )

            insertados, actualizados, errores_db = await tarea
            errores.extend(errores_db)
            actualizar(
                1.0,
                "Importación completada",
                f"{insertados} nuevos · {actualizados} actualizados",
            )
            await asyncio.sleep(0.5)
            app.close_dialog()
            app.refresh()
            _dialogo_importacion(
                app, insertados, actualizados, len(documentos), errores
            )
        except Exception as exc:
            app.close_dialog()
            app.toast(f"No se pudo completar la importación: {exc}", "error")

    # ------------------------------------------------------------------
    # Foto + OCR
    # ------------------------------------------------------------------

    async def cargar_foto_ocr(e):
        try:
            archivos = await app.file_picker.pick_files(
                dialog_title="Seleccionar foto del repuesto",
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
                with_data=True,
            )
        except Exception as exc:
            app.toast(f"No se pudo abrir la imagen: {exc}", "error")
            return
        if not archivos:
            return
        archivo = archivos[0]
        contenido = bytes_de_archivo(archivo)
        if not contenido:
            app.toast("No se pudo leer la imagen.", "warning")
            return

        progreso = ft.ProgressRing(width=28, height=28, stroke_width=3,
                                   color=ui.TEAL, bgcolor=ui.TEAL_SOFT)
        dialogo_progreso = ft.AlertDialog(
            modal=True,
            bgcolor=ui.WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                width=320,
                content=ft.Row(
                    [
                        progreso,
                        ft.Column(
                            [
                                ui.txt("Analizando imagen…", 12, ui.INK, ui.W_600),
                                ui.txt("Buscando el código del repuesto.", 9.5,
                                       ui.MUTED),
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )
        app.show_dialog(dialogo_progreso)
        await asyncio.sleep(0.9)
        try:
            resultado = simular_ocr(
                getattr(archivo, "name", "foto.jpg"), contenido,
                db.listar_referencias_ocr(),
            )
        except Exception as exc:
            app.close_dialog()
            app.toast(f"No se pudo procesar la imagen: {exc}", "error")
            return
        if not resultado.get("codigo"):
            app.close_dialog()
            app.toast("No se pudo asociar la foto.", "warning")
            return
        foto_b64 = comprimir_imagen_b64(contenido)
        try:
            db.actualizar_foto(resultado["codigo"], foto_b64,
                               resultado.get("texto", ""))
        except Exception as exc:
            app.close_dialog()
            app.toast(f"No se pudo guardar la foto: {exc}", "error")
            return
        app.close_dialog()
        app.refresh()
        app.toast(f"Foto asociada a {resultado['codigo']}.", "success")
        _dialogo_ocr(app, resultado, foto_b64)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def abrir_nuevo(e=None):
        _dialogo_repuesto(app, None, on_saved=lambda: app.refresh())

    def abrir_editar(repuesto):
        _dialogo_repuesto(app, repuesto, on_saved=lambda: app.refresh())

    def abrir_detalle(repuesto):
        completo = db.buscar_repuesto(repuesto.get("codigo", "")) or repuesto
        _dialogo_detalle(app, completo, abrir_editar, confirmar_eliminar)

    def confirmar_eliminar(repuesto):
        def eliminar(e):
            try:
                ok = db.eliminar_repuesto(repuesto.get("codigo", ""))
            except Exception as exc:
                app.close_dialog()
                app.toast(f"No se pudo eliminar: {exc}", "error")
                return
            app.close_dialog()
            if ok:
                app.refresh()
                app.toast(f"{repuesto.get('codigo', '')} eliminado.", "success")
            else:
                app.toast("No se encontró el repuesto.", "warning")

        app.show_dialog(ui._dialog_base(
            "Eliminar repuesto",
            "La acción se aplica en MongoDB",
            ft.Column(
                [
                    ui.info_box(
                        f"Se eliminará {repuesto.get('codigo', '')} · "
                        f"{repuesto.get('descripcion', '')}.",
                        ui.RED, ui.RED_SOFT, "#FECACA",
                        ft.Icons.WARNING_AMBER_ROUNDED,
                    ),
                    ui.txt("Esta operación no se puede deshacer.", 10.5, ui.MUTED),
                ],
                spacing=10,
            ),
            [
                ui.text_button("Cancelar", None, lambda e: app.close_dialog(),
                               color=ui.MUTED, size=11.5),
                ft.Button(
                    content=ui.txt("Eliminar", 11.5, ui.WHITE, ui.W_600),
                    on_click=eliminar,
                    bgcolor=ui.RED,
                    height=38,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=14),
                    ),
                ),
            ],
            width=460,
            icono=ft.Icons.DELETE_OUTLINE,
            color=ui.RED,
            bg=ui.RED_SOFT,
        ))

    # ------------------------------------------------------------------
    # Composición
    # ------------------------------------------------------------------

    toolbar = ft.Row(
        [
            ui.search_input("Buscar por código, descripción o marca…", buscar,
                            width=360),
            ft.Container(expand=True),
            count_label,
            pagina_label,
            boton_anterior,
            boton_siguiente,
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    footer = ui.table_footer(
        ft.Row(
            [
                footer_total,
                ft.Container(expand=True),
                ui.txt("Ordenado por descripción (A-Z)", 9.3, ui.MUTED),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    tabla = ui.table_container(
        [
            {"label": "Código", "flex": 1.6},
            {"label": "Descripción", "flex": 5.8},
            {"label": "Marca", "flex": 2.2},
            {"label": "Precio", "flex": 1.9, "align": ui.ALIGN_RIGHT},
        ],
        rows_host,
        footer,
    )

    cargar_pagina(1, update=False)

    contenido = [
        ui.page_header(
            "Inventario",
            "Código, descripción, marca y precio.",
            [
                ui.secondary_button("Importar", ft.Icons.UPLOAD_FILE_OUTLINED,
                                    importar_archivos),
                ui.secondary_button("Foto + OCR", ft.Icons.IMAGE_SEARCH_OUTLINED,
                                    cargar_foto_ocr),
                ui.primary_button("Nuevo repuesto", ft.Icons.ADD, abrir_nuevo),
            ],
        ),
    ]
    if error_db:
        contenido.append(ui.info_box(
            f"No se pudo consultar MongoDB: {error_db}", ui.RED, ui.RED_SOFT,
            "#FECACA", ft.Icons.ERROR_OUTLINE,
        ))
    elif not db.conectado:
        contenido.append(ui.info_box(
            f"{db.detalle_estado} Los cambios se guardan en el respaldo local.",
            ui.ORANGE, ui.ORANGE_SOFT, ui.ORANGE_BORDER,
            ft.Icons.CLOUD_OFF_OUTLINED,
        ))
    contenido.extend([toolbar, tabla])
    return ft.Column(contenido, spacing=14)


# ---------------------------------------------------------------------------
# Diálogos
# ---------------------------------------------------------------------------


def _dialogo_importacion(app, insertados, actualizados, total, errores):
    detalle_errores = ft.Column(spacing=3)
    for error in errores[:8]:
        detalle_errores.controls.append(ui.txt(f"• {error}", 9, ui.MUTED,
                                               max_lines=2))
    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    ui.mini_stat("Nuevos", str(insertados), "insertados",
                                 ft.Icons.ADD_CIRCLE_OUTLINE, ui.TEAL, ui.TEAL_SOFT),
                    ui.mini_stat("Actualizados", str(actualizados), "por código",
                                 ft.Icons.SYNC, ui.BLUE, ui.BLUE_SOFT),
                ],
                spacing=10,
            ),
            ui.info_box(
                f"{total} repuestos procesados y sincronizados con MongoDB.",
                ui.TEAL, ui.TEAL_SOFT, ui.TEAL_BORDER,
                ft.Icons.CHECK_CIRCLE_OUTLINED,
            ),
            ft.Column(
                [
                    ui.txt("Observaciones", 10.5, ui.INK, ui.W_600),
                    detalle_errores,
                ],
                spacing=5,
            ) if errores else ft.Container(),
        ],
        spacing=12,
    )
    app.show_dialog(ui._dialog_base(
        "Importación completada",
        "Inventario actualizado",
        cuerpo,
        [ui.text_button("Cerrar", ft.Icons.CHECK, lambda e: app.close_dialog(),
                        color=ui.TEAL, size=11.5)],
        width=480,
        icono=ft.Icons.UPLOAD_FILE_OUTLINED,
        color=ui.TEAL,
        bg=ui.TEAL_SOFT,
    ))


def _dialogo_ocr(app, resultado, foto_b64):
    repuesto = resultado.get("repuesto") or {}
    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Image(src=foto_b64, width=150, height=110,
                                         fit=ft.BoxFit.COVER),
                        width=150,
                        height=110,
                        border_radius=10,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.Column(
                        [
                            ui.pill("OCR simulado" if resultado.get("simulado")
                                    else "OCR real",
                                    ui.ORANGE if resultado.get("simulado")
                                    else ui.TEAL,
                                    ui.ORANGE_SOFT if resultado.get("simulado")
                                    else ui.TEAL_SOFT, size=9),
                            ui.txt(resultado.get("codigo", "—"), 16, ui.INK,
                                   ui.W_700),
                            ui.txt(repuesto.get("descripcion", ""), 10.5, ui.MUTED,
                                   max_lines=2),
                            ui.txt(f"Marca: {repuesto.get('marca', '—')}", 9.5,
                                   ui.MUTED),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ui.info_box(
                f"Foto asociada al código. Confianza: "
                f"{resultado.get('confianza', 88)}%.",
                ui.TEAL, ui.TEAL_SOFT, ui.TEAL_BORDER,
                ft.Icons.IMAGE_SEARCH_OUTLINED,
            ),
            ft.Column(
                [
                    ui.txt("Texto reconocido", 10, ui.INK, ui.W_600),
                    ft.Container(
                        content=ui.txt(resultado.get("texto", ""), 9, ui.MUTED,
                                       max_lines=5),
                        bgcolor=ui.SOFT,
                        border=ft.Border.all(1, ui.BORDER),
                        border_radius=8,
                        padding=9,
                    ),
                ],
                spacing=4,
            ),
        ],
        spacing=12,
    )
    app.show_dialog(ui._dialog_base(
        "Foto asociada por OCR",
        "Reconocimiento visual",
        cuerpo,
        [ui.text_button("Cerrar", None, lambda e: app.close_dialog(),
                        color=ui.MUTED, size=11.5)],
        width=510,
        icono=ft.Icons.IMAGE_SEARCH_OUTLINED,
        color=ui.ORANGE,
        bg=ui.ORANGE_SOFT,
    ))


def _dialogo_foto(app, repuesto, on_editar):
    foto = repuesto.get("foto_b64", "")
    if foto:
        imagen = ft.Image(src=foto, fit=ft.BoxFit.CONTAIN, expand=True)
    else:
        imagen = ft.Column(
            [
                ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_OUTLINED, size=42,
                        color=ui.MUTED_2),
                ui.txt("Sin foto asociada", 11, ui.MUTED),
                ui.txt("Usa Foto + OCR para agregar una imagen.", 9,
                       ui.MUTED_2),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    cuerpo = ft.Column(
        [
            ft.Container(
                content=imagen,
                height=360,
                bgcolor=ui.SOFT,
                border=ft.Border.all(1, ui.BORDER),
                border_radius=10,
                alignment=ui.ALIGN_CENTER,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                padding=8,
            ),
            ft.Row(
                [
                    ft.Column(
                        [
                            ui.txt(repuesto.get("descripcion", "—"), 14, ui.INK,
                                   ui.W_700, max_lines=2),
                            ui.txt(
                                f"{repuesto.get('marca', '—')} · "
                                f"{repuesto.get('categoria', 'Sin categoría')}"
                                + (f" · {repuesto['familia']}"
                                   if repuesto.get("familia") else ""),
                                9.8, ui.MUTED,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ui.txt(ui.money(repuesto.get("precio", 0), 2), 16,
                           ui.TEAL_DARK, ui.W_700),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=12,
    )

    acciones = [ui.text_button("Cerrar", None, lambda e: app.close_dialog(),
                               color=ui.MUTED, size=11.5)]
    if foto:
        acciones.insert(0, ui.text_button(
            "Editar repuesto", ft.Icons.EDIT_OUTLINED,
            lambda e: (app.close_dialog(), on_editar(repuesto)),
            color=ui.TEAL, size=10.5,
        ))

    app.show_dialog(ui._dialog_base(
        f"Foto · {repuesto.get('codigo', '')}",
        "Vista ampliada del repuesto",
        cuerpo,
        acciones,
        width=660,
        icono=ft.Icons.IMAGE_OUTLINED,
        color=ui.TEAL,
        bg=ui.TEAL_SOFT,
    ))


def _dialogo_repuesto(app, repuesto, on_saved):
    editando = repuesto is not None
    codigo_field = ui.base_text_field(
        value=repuesto.get("codigo", "") if repuesto else "", hint="MD-FRN-014")
    desc_field = ui.base_text_field(
        value=repuesto.get("descripcion", "") if repuesto else "",
        hint="Descripción del repuesto")
    marca_field = ui.base_text_field(
        value=repuesto.get("marca", "") if repuesto else "", hint="Fabricante")
    precio_field = ui.base_text_field(
        value=f"{float(repuesto.get('precio', 0)):.2f}" if repuesto else "0.00",
        hint="0.00")
    categoria_inicial = (
        repuesto.get("categoria") if repuesto else data.CATEGORIAS[2]
    ) or data.CATEGORIA_SIN
    if categoria_inicial not in data.CATEGORIAS + [data.CATEGORIA_SIN]:
        categoria_inicial = data.CATEGORIA_SIN
    familia_inicial = (repuesto.get("familia", "") if repuesto else "") or ""
    estado_form = {"categoria": categoria_inicial, "familia": familia_inicial}
    error_lbl = ui.txt("", 10, ui.RED, ui.W_500, max_lines=2)

    familia_dropdown = ft.Dropdown(
        options=[ft.DropdownOption(key=f, text=f)
                 for f in data.familias_de(categoria_inicial)]
        + ([ft.DropdownOption(key=familia_inicial, text=familia_inicial)]
           if familia_inicial and familia_inicial not in
           data.familias_de(categoria_inicial) else []),
        value=familia_inicial,
        on_select=lambda e: _elegir_familia(e),
        border=ft.InputBorder.NONE,
        text_size=12,
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        expand=True,
    )

    def _elegir_familia(e):
        estado_form["familia"] = e.control.value
        app.page.update()

    def elegir_categoria(e):
        estado_form["categoria"] = e.control.value
        estado_form["familia"] = ""
        familia_dropdown.options = [
            ft.DropdownOption(key=f, text=f)
            for f in data.familias_de(estado_form["categoria"])
        ]
        familia_dropdown.value = ""
        app.page.update()

    def guardar(e):
        try:
            precio = float(str(precio_field.value).replace(",", "."))
        except (TypeError, ValueError):
            precio = 0
        doc = {
            "codigo": str(codigo_field.value or "").strip(),
            "descripcion": str(desc_field.value or "").strip(),
            "marca": str(marca_field.value or "").strip(),
            "categoria": estado_form["categoria"],
            "familia": estado_form["familia"],
            "precio": precio,
        }
        if not doc["codigo"] or not doc["descripcion"] or not doc["marca"]:
            error_lbl.value = "Código, descripción y marca son obligatorios."
            app.page.update()
            return
        if precio <= 0:
            error_lbl.value = "El precio debe ser mayor que cero."
            app.page.update()
            return
        try:
            ok, mensaje = app.db.guardar_repuesto(doc)
        except Exception as exc:
            error_lbl.value = f"No se pudo guardar: {exc}"
            app.page.update()
            return
        if not ok:
            error_lbl.value = mensaje
            app.page.update()
            return
        app.close_dialog()
        on_saved()
        app.toast(mensaje, "success")

    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    ui.field_shell("Código", codigo_field, expand=True),
                    ui.field_shell("Marca", marca_field, expand=True),
                ],
                spacing=12,
            ),
            ui.field_shell("Descripción", desc_field),
            ft.Row(
                [
                    ui.labeled_dropdown(
                        "Categoría",
                        [(c, c) for c in data.CATEGORIAS + [data.CATEGORIA_SIN]],
                        estado_form["categoria"], elegir_categoria, expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Text("FAMILIA", size=8.5, color=ui.MUTED,
                                    weight=ui.W_700,
                                    style=ft.TextStyle(letter_spacing=0.6)),
                            ft.Container(
                                content=familia_dropdown,
                                bgcolor=ui.SOFT,
                                border=ft.Border.all(1, ui.BORDER),
                                border_radius=9,
                                height=42,
                            ),
                        ],
                        spacing=5,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            ui.field_shell("Precio USD", precio_field),
            error_lbl,
            ui.info_box(
                "Código, descripción, marca, categoría y precio se guardan en "
                "MongoDB.",
                ui.BLUE, ui.BLUE_SOFT, "#BFDBFE", ft.Icons.INFO_OUTLINE,
            ),
        ],
        spacing=12,
    )
    app.show_dialog(ui._dialog_base(
        "Editar repuesto" if editando else "Nuevo repuesto",
        "Información del catálogo",
        cuerpo,
        [
            ui.text_button("Cancelar", None, lambda e: app.close_dialog(),
                           color=ui.MUTED, size=11.5),
            ui.primary_button("Guardar", ft.Icons.SAVE_OUTLINED, guardar,
                              height=38),
        ],
        width=540,
        icono=ft.Icons.CAR_REPAIR,
    ))


def _dialogo_detalle(app, repuesto, on_editar, on_eliminar):
    foto = repuesto.get("foto_b64", "")
    modo = {"moneda": "USD"}
    categoria = repuesto.get("categoria") or data.CATEGORIA_SIN
    familia = repuesto.get("familia", "")

    def precio_actual():
        return ui.monto_segun_moneda(repuesto.get("precio", 0), modo["moneda"], 2)

    precio_text = ui.txt(precio_actual(), 24, ui.TEAL_DARK, ui.W_700)
    etiqueta_moneda = ui.txt("Ver en bolívares", 10.5, ui.TEAL, ui.W_600)

    def alternar(e):
        modo["moneda"] = "VES" if modo["moneda"] == "USD" else "USD"
        precio_text.value = precio_actual()
        etiqueta_moneda.value = ("Ver en dólares" if modo["moneda"] == "VES"
                                 else "Ver en bolívares")
        app.page.update()

    toggle = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.SWAP_HORIZ, size=14, color=ui.TEAL),
             etiqueta_moneda],
            spacing=6,
            tight=True,
        ),
        on_click=alternar,
        height=32,
        style=ft.ButtonStyle(
            color=ui.TEAL,
            bgcolor=ui.WHITE,
            side=ft.BorderSide(1, ui.TEAL_BORDER),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=10, vertical=0),
        ),
    )

    cuerpo = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Image(src=foto, width=150, height=120,
                                         fit=ft.BoxFit.COVER)
                        if foto else ui.icon_box(ft.Icons.IMAGE_NOT_SUPPORTED_OUTLINED,
                                                 ui.MUTED_2, ui.SOFT, 54, 26, 12),
                        width=150,
                        height=120,
                        bgcolor=ui.SOFT,
                        border=ft.Border.all(1, ui.BORDER),
                        border_radius=10,
                        alignment=ui.ALIGN_CENTER,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        on_click=(lambda e: _dialogo_foto(app, repuesto, on_editar))
                        if foto else None,
                        ink=bool(foto),
                        tooltip="Ampliar foto" if foto else None,
                    ),
                    ft.Column(
                        [
                            ui.txt(repuesto.get("descripcion", "—"), 14, ui.INK,
                                   ui.W_700, max_lines=2),
                            ui.txt(f"{repuesto.get('marca', '—')} · "
                                   f"{repuesto.get('codigo', '—')}", 10, ui.MUTED),
                            ft.Row(
                                [
                                    ui.pill(categoria, ui.BLUE, ui.BLUE_SOFT,
                                            size=9),
                                    ui.pill(familia or "Sin familia", ui.MUTED,
                                            ui.SOFT_2, size=9),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Precio", 9.5, ui.MUTED),
                                precio_text,
                                ui.txt(f"Tasa Bs. {data.TASA_VES:,.2f} / $", 8.5,
                                       ui.MUTED_2),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        toggle,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ui.TEAL_SOFT,
                border=ft.Border.all(1, ui.TEAL_BORDER),
                border_radius=10,
                padding=12,
            ),
            ft.Column(
                [
                    ui.txt("Texto OCR / observaciones", 10, ui.INK, ui.W_600),
                    ft.Container(
                        content=ui.txt(
                            repuesto.get("ocr_text") or "Sin texto OCR asociado.",
                            9.2, ui.MUTED, max_lines=4),
                        bgcolor=ui.SOFT,
                        border=ft.Border.all(1, ui.BORDER),
                        border_radius=8,
                        padding=9,
                    ),
                ],
                spacing=4,
            ),
        ],
        spacing=13,
    )
    app.show_dialog(ui._dialog_base(
        f"Repuesto {repuesto.get('codigo', '')}",
        "Detalle del catálogo",
        cuerpo,
        [
            ui.text_button("Eliminar", ft.Icons.DELETE_OUTLINE,
                           lambda e: (app.close_dialog(), on_eliminar(repuesto)),
                           color=ui.RED, size=10.5),
            ui.text_button("Editar", ft.Icons.EDIT_OUTLINED,
                           lambda e: (app.close_dialog(), on_editar(repuesto)),
                           color=ui.TEAL, size=10.5),
            ui.text_button("Cerrar", None, lambda e: app.close_dialog(),
                           color=ui.MUTED, size=11.5),
        ],
        width=550,
        icono=ft.Icons.CAR_REPAIR,
        color=ui.TEAL,
        bg=ui.TEAL_SOFT,
    ))
