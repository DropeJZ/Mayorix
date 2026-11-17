"""
Mayorix · Verificación de MongoDB
=================================
Comprueba la conexión configurada y deja las colecciones vacías con sus
índices. No inserta datos de prueba: el contenido se carga manualmente desde
los módulos de la aplicación.

Uso:
    python setup_mongodb.py
    python setup_mongodb.py --uri "mongodb+srv://..." --db mayorix
    python setup_mongodb.py --vaciar
"""

from __future__ import annotations

import argparse
import sys

import database


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica y prepara MongoDB para Mayorix.")
    parser.add_argument("--uri", default=None, help="URI de MongoDB (por defecto: mongo_uri.txt)")
    parser.add_argument("--db", default=None, help="Nombre de la base de datos (por defecto: mayorix)")
    parser.add_argument("--vaciar", action="store_true",
                        help="Elimina inventario, vendedores y pedidos (no usuarios)")
    args = parser.parse_args()

    print("Mayorix · configuración de MongoDB")
    print("=" * 42)
    db = database.Database(uri=args.uri, db_name=args.db)
    print("Modo:", db.estado_texto)
    print("URI :", db.uri_visible)
    print("Base:", db.db_name)
    if not db.conectado:
        print("\nNo se pudo conectar a MongoDB.")
        print(db.detalle_estado)
        print(
            "\nRevisa:\n"
            "  1. Network Access en Atlas: agrega la IP pública de este equipo.\n"
            "  2. Usuario y contraseña de la URI, con permisos readWrite sobre la base.\n"
            "  3. Firewall/proxy de la red, que debe permitir TLS al puerto 27017.\n"
            "  4. El archivo mongo_uri.txt junto a la app o la variable MONGODB_URI."
        )
        return 1

    print("\nConexión establecida. Colecciones e índices:")
    if args.vaciar:
        for nombre, coleccion in (
            ("inventario", db.store.inventario),
            ("vendedores", db.store.vendedores),
            ("pedidos", db.store.pedidos),
        ):
            eliminados = coleccion.delete_many({}).deleted_count
            print(f"  - {nombre:10s} documentos eliminados: {eliminados}")
    for nombre, coleccion in (
        ("usuarios", db.store.usuarios),
        ("inventario", db.store.inventario),
        ("vendedores", db.store.vendedores),
        ("pedidos", db.store.pedidos),
    ):
        indices = [
            (idx.get("name"), idx.get("unique", False))
            for idx in coleccion.list_indexes()
            if idx.get("name") != "_id_"
        ]
        print(f"  - {nombre:10s} documentos={coleccion.count_documents({}):3d} índices={indices}")

    print("\nEsquemas esperados:")
    print("  inventario : codigo, descripcion, marca, precio (USD), foto_b64, ocr_text")
    print("  vendedores : codigo, nombre, cedula, telefono, ciudad, foto_b64, estado")
    print("  pedidos    : pedido_id, cliente_id, vendedor_id, items, estado, total")
    print("  usuarios   : email, nombre, rol, activo, salt, password_hash")
    if db.contar_usuarios() == 0:
        print("\nPrimer arranque: registra el administrador desde la pantalla de login.")
    else:
        print(f"\nAdministradores registrados: {db.contar_usuarios()}. El registro está bloqueado.")
    print("La aplicación guardará los cambios en MongoDB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
