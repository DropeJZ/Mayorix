# Mayorix · Proyecto

Sistema de gestión mayorista de **Mayor Disluda**, desarrollado por **DropeTech**.

- Aplicación administrativa de escritorio (**Flet + PyMongo**), con Web Service
  para Render.
- App Android de vendedores (**Flet + PyMongo**), con URI fija de Atlas.
- Conexión directa a **MongoDB Atlas**, base `mayorix`.

## Estructura

La raíz del proyecto queda limpia con solo los tres artefactos de distribución
y las carpetas de trabajo ordenadas:

```text
Mayorix/
├── Mayorix.exe              # Ejecutable de escritorio (2.1.5)
├── Mayorix.apk              # App Android preconfigurada (1.1.4)
├── Mayorix_Setup.exe        # Instalador de escritorio (Inno Setup)
├── .gitignore               # (solo metadatos de Git)
├── src/
│   ├── Mayorix_Desktop/     # Código fuente de la app de escritorio
│   └── Mayorix_Mobile/      # Código fuente de la app Android
├── builds/
│   ├── windows_setup/       # Script Inno Setup (mayorix.iss)
│   └── *.apk                # APK legados/genérico (ignorados por Git)
├── config/                  # Secretos y configuración local (ignorados)
│   ├── mongo_uri.txt
│   └── tasa_bcv.json
├── deploy/                  # Web Service para Render
│   ├── main.py
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env.example
└── docs/                    # Documentación
    └── README.md
```

`config/`, `builds/*.apk`, `*.exe`, `.env` y `mongo_uri.txt` quedan excluidos
por `.gitignore`.

## Conexión MongoDB

La URI se resuelve (orden de prioridad) desde:

1. Variable de entorno `MONGO_URI` (o `MONGODB_URI`).
2. `.env` junto al ejecutable, en `src/Mayorix_Desktop` o en la raíz.
3. `mongo_uri.txt` junto al ejecutable, en `config/` o en el directorio actual.

El ejecutable de escritorio (`Mayorix.exe`) y el instalador usan esta cadena
para conectar con Atlas. El APK lleva la URI fija dentro (`atlas_config.py`,
no versionado) con TLS tolerante.

## Web Service para Render

```powershell
cd deploy
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MONGO_URI = "mongodb+srv://usuario:clave@cluster.mongodb.net/mayorix"
$env:MONGO_DB = "mayorix"
$env:PORT = "8000"
python main.py
```

El blueprint vive en `deploy/render.yaml` (build: `pip install -r
deploy/requirements.txt`, start: `python deploy/main.py`).

## Variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `MONGO_URI` | Sí | URI de MongoDB Atlas |
| `MONGO_DB` | No | Base de datos; por defecto `mayorix` |
| `PORT` | Render | Render inyecta el puerto |
| `FLET_FORCE_WEB_SERVER` | Recomendado | `1` para modo web |

## MongoDB Atlas

1. Crea un usuario de Atlas con permisos mínimos sobre `mayorix`.
2. En **Network Access**, permite la IP del equipo y de los teléfonos; para
   uso móvil se suele usar `0.0.0.0/0`.
3. No subas `mongo_uri.txt`, `.env` ni `atlas_config.py` al repositorio.

## Notas

- El APK Android no se despliega en Render; se distribuye aparte.
- La app administrativa conserva login, inventario paginado, pedidos,
  vendedores, finanzas y el panel de registros móviles.
- La tasa BCV se obtiene mediante el servicio interno y caché; si falla, la
  interfaz conserva la última tasa válida.
