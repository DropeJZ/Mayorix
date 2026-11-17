"""
Mayorix · Reparación de codificación
====================================
Normaliza los textos existentes en MongoDB (NFC/UTF-8), corrige secuencias
típicas con "?" y vuelve a clasificar categorías y familias conocidas.

Uso:
    python reparar_codificacion.py
"""

from __future__ import annotations

import database


def _cambios(original: dict, nuevos: dict) -> dict:
    return {
        campo: valor for campo, valor in nuevos.items()
        if original.get(campo) != valor
    }


def main() -> int:
    db = database.Database()
    print("Mayorix · reparación de codificación")
    print("Modo:", db.estado_texto)
    if not db.conectado:
        print(db.detalle_estado)
        return 1

    total_inventario = 0
    for doc in db.store.inventario.find({}):
        categoria = database.categoria_canonica(doc.get("categoria", ""))
        nuevos = {
            "codigo": database.limpiar_texto(doc.get("codigo", "")).upper(),
            "descripcion": database.limpiar_texto(doc.get("descripcion", "")),
            "marca": database.limpiar_texto(doc.get("marca", "")),
            "categoria": categoria,
            "familia": database.familia_canonica(doc.get("familia", ""), categoria),
        }
        cambios = _cambios(doc, nuevos)
        if cambios:
            db.store.inventario.update_one({"_id": doc["_id"]}, {"$set": cambios})
            total_inventario += 1

    total_vendedores = 0
    for doc in db.store.vendedores.find({}):
        nuevos = {
            "nombre": database.limpiar_texto(doc.get("nombre", "")),
            "cedula": database.limpiar_texto(doc.get("cedula", "")),
            "telefono": database.limpiar_texto(doc.get("telefono", "")),
            "ciudad": database.limpiar_texto(doc.get("ciudad", "")),
            "email": database.limpiar_texto(doc.get("email", "")).lower(),
            "estado": database.limpiar_texto(doc.get("estado", "Activo")),
        }
        cambios = _cambios(doc, nuevos)
        if cambios:
            db.store.vendedores.update_one({"_id": doc["_id"]}, {"$set": cambios})
            total_vendedores += 1

    total_pedidos = 0
    for doc in db.store.pedidos.find({}):
        nuevos = {
            "cliente_nombre": database.limpiar_texto(doc.get("cliente_nombre", "")),
            "vendedor_nombre": database.limpiar_texto(doc.get("vendedor_nombre", "")),
            "nota": database.limpiar_texto(doc.get("nota", "")),
            "condicion": database.limpiar_texto(doc.get("condicion", "")),
            "tipo_doc": database.limpiar_texto(doc.get("tipo_doc", "")),
        }
        cambios = _cambios(doc, nuevos)
        if cambios:
            db.store.pedidos.update_one({"_id": doc["_id"]}, {"$set": cambios})
            total_pedidos += 1

    total_usuarios = 0
    for doc in db.store.usuarios.find({}):
        nuevos = {"nombre": database.limpiar_texto(doc.get("nombre", ""))}
        cambios = _cambios(doc, nuevos)
        if cambios:
            db.store.usuarios.update_one({"_id": doc["_id"]}, {"$set": cambios})
            total_usuarios += 1

    print(f"Inventario corregido: {total_inventario}")
    print(f"Vendedores corregidos: {total_vendedores}")
    print(f"Pedidos corregidos: {total_pedidos}")
    print(f"Usuarios corregidos: {total_usuarios}")
    print("\nCategorías actuales:")
    for categoria in sorted(db.store.inventario.distinct("categoria")):
        print(" -", categoria)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
