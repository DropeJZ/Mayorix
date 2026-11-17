# Mayorix · Web Service para Render

Proyecto de **Mayor Disluda** desarrollado por **DropeTech**. Incluye:

- Aplicación administrativa de escritorio convertida a **Web Service Flet**.
- App Android de vendedores en `Mayorix_Mobile` (APK separado).
- Conexión directa a **MongoDB Atlas**.

## Estructura

```text
Mayorix/
├── main.py                  # Punto de entrada web para Render
├── requirements.txt         # Dependencias del Web Service
├── render.yaml              # Blueprint de Render
├── .env.example             # Variables de entorno de ejemplo
├── .gitignore
├── Mayorix_Desktop/         # App administrativa Flet
└── Mayorix_Mobile/          # App Android de vendedores
```

## Ejecutar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:MONGO_URI = "mongodb+srv://usuario:clave@cluster.mongodb.net/mayorix"
$env:MONGO_DB = "mayorix"
$env:PORT = "8000"
python main.py
```

Abre `http://127.0.0.1:8000/`.

En Linux/Render, `main.py` fuerza el modo servidor web: no abre ventanas de
escritorio ni requiere pantalla gráfica.

## Variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `MONGO_URI` | Sí | URI de MongoDB Atlas |
| `MONGO_DB` | No | Base de datos; por defecto `mayorix` |
| `PORT` | Render | Render inyecta el puerto |
| `FLET_FORCE_WEB_SERVER` | Recomendado | `1` para modo web |
| `PYTHON_VERSION` | Render | `3.13.7` |

Para desarrollo local también se puede usar un `.env` basado en
`.env.example`. Los `.env` reales están excluidos por `.gitignore`.

## MongoDB Atlas

1. Crea un usuario de Atlas con permisos mínimos sobre `mayorix`.
2. En **Network Access**, permite la salida de Render. Si no se usan IPs
   estáticas, se necesita `0.0.0.0/0` o Private Endpoint.
3. Copia la URI en la variable **`MONGO_URI`** de Render.
4. No subas `mongo_uri.txt` al repositorio.

## Desplegar en Render

### Opción A · Blueprint

1. Sube el proyecto a GitHub.
2. En Render, elige **New → Blueprint**.
3. Selecciona el repositorio. Render leerá `render.yaml`.
4. Define el secreto **`MONGO_URI`** cuando lo solicite.
5. Despliega.

El servicio ejecutará:

```text
Build: pip install -r requirements.txt
Start: python main.py
```

### Opción B · Web Service manual

- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Health Check Path: `/`
- Variable `MONGO_URI`: tu URI de Atlas
- Variable `MONGO_DB`: `mayorix`

## Publicar en GitHub

```powershell
git init
git add .
git commit -m "Mayorix web service listo para Render"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

Antes de hacer commit, confirma que `mongo_uri.txt`, `.env`, `Mayorix.exe`,
`Mayorix_Vendedor.apk`, `build/` y `__pycache__/` no aparecen en `git status`.
El `.gitignore` raíz ya los excluye.

## Notas

- El APK Android no se despliega en Render; se distribuye aparte.
- La app administrativa web conserva login, inventario paginado, pedidos,
  vendedores, finanzas y el panel de registros móviles.
- La tasa BCV se obtiene mediante el servicio interno y caché; si falla, la
  interfaz conserva la última tasa válida.
- No hay rutas absolutas de Windows en el código de ejecución.
