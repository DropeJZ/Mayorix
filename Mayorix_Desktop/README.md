# Mayorix Desktop · Mayor Disluda

**Mayorix — Sistema de Gestión Mayorista para Mayor Disluda (Powered by DropeTech).**

Aplicación de escritorio de producción, **exclusiva para la administración de la empresa**:
login corporativo, dashboard financiero, inventario paginado conectado a
MongoDB, importación de Excel/PDF, reconocimiento visual de repuestos, pedidos
recibidos, red comercial y finanzas. Todos los módulos están operativos en la
edición **2.1.3**.

## Ejecutar

### Ejecutable

```
D:\PROYECTOS\Mayorix\Mayorix.exe
```

### Código fuente

```bash
pip install -r requirements.txt
python main.py
```

La aplicación abre directamente en el **login administrativo**, sin pantalla
previa, con ventana estándar de **1280 × 800**.

### Ventana estándar de Windows

- Barra de título nativa con **minimizar, maximizar/restaurar y cerrar**.
- Ventana **redimensionable y movible**, con presencia normal en la barra de
  tareas.
- El cierre desde la barra de título o desde la barra de tareas finaliza la
  aplicación de forma ordinaria.
- Al iniciar sesión se abre el módulo **Repuestos**. Desde la barra lateral se
  accede a Dashboard, Pedidos recibidos, Vendedores y Finanzas; Ayuda,
  Configuración y el indicador de MongoDB también responden a clics.

## Acceso

### Primer arranque · registro del administrador

- Si la colección `usuarios` está **vacía**, el login muestra la opción
  **“Registrar administrador”**.
- El formulario solicita nombre, correo corporativo y contraseña (mínimo 8
  caracteres, con confirmación).
- La cuenta se guarda en MongoDB con **PBKDF2-SHA256 + salt**; nunca se
  almacena la contraseña en texto plano.
- En cuanto existe **un usuario**, la opción de registro desaparece de la
  interfaz y solo queda el inicio de sesión.
- El servidor vuelve a validar el conteo antes de insertar, por lo que no se
  pueden crear cuentas adicionales desde la app.

No existe acceso de vendedores en esta versión: la app está enfocada
exclusivamente en la administración central.

## Tasa BCV · FastAPI

La tasa oficial del dólar se obtiene mediante un microservicio FastAPI:

- Servicio local: `http://127.0.0.1:8010/tasa`
- Fuente principal: página oficial del **BCV**.
- Fuente de respaldo: API pública de tasa oficial.
- Caché persistente en `tasa_bcv.json` con vigencia de 30 minutos.
- Si el BCV o la red fallan, se conserva la última tasa válida y la app sigue
  operando sin bloquearse.
- La barra superior muestra `Bs. X / $`; al hacer clic se fuerza la
  actualización y se informa el resultado.
- También puede ejecutarse por separado:
  ```bash
  python bcv_service.py
  ```

## Codificación UTF-8

- Todos los archivos se leen y escriben en UTF-8.
- Los textos se normalizan a **Unicode NFC** antes de guardarse en MongoDB.
- `limpiar_texto()` corrige mojibake y palabras frecuentes con `?`
  (`Suspensi?n`, `Buj?as`, `categor?a`, `Pist?n`, etc.).
- Las categorías y familias se comparan sin acentos ni signos, por lo que
  `"Suspensi?n y Direcci?n"` se reclasifica correctamente.
- Para reparar datos existentes:
  ```bash
  python reparar_codificacion.py
  ```

## Módulos

> **Edición 2.1.3:** Dashboard, Repuestos, Pedidos recibidos, Vendedores y
> Finanzas están habilitados y conectados a MongoDB. Ayuda, Configuración y el
> indicador de conexión también son interactivos.

### Dashboard
- KPIs financieros en USD: ventas del mes, pedidos activos, cuentas por cobrar.
- Inventario en catálogo y precio de lista acumulado.
- Ventas de la red, meta mensual y pedidos por estado.
- Pedidos recientes, red comercial y actividad.

### Inventario de repuestos
- Vista principal en **lista limpia** con solo cuatro datos:
  **Código · Descripción · Marca · Precio (USD)**.
- **Paginación estricta de 20 en 20**: la interfaz nunca carga el catálogo
  completo. Cada página se resuelve en MongoDB con `.skip()` y `.limit(20)`.
- Controles **Anterior / Siguiente** y contador `Página X de Y` en la barra
  superior, junto al total filtrado.
- Consultas ligeras con proyección de solo las columnas visibles: no se
  transfieren `foto_b64` ni `ocr_text` al listado. El documento completo se
  carga únicamente al abrir el detalle.
- Índices en `codigo` (único) y `descripcion` para ordenar y paginar sin
  recorrer la colección completa.
- Sin miniaturas, categorías, familias ni tarjetas en la lista principal.
- Lectura y escritura en la colección `inventario` de MongoDB.
- Orden alfabético A-Z por descripción, resuelto desde MongoDB.
- Búsqueda por código, descripción o marca con **debounce de 0.28 s**, también
  paginada del lado del servidor.
- **Clic en el precio** para alternar **USD ↔ VES** con la tasa BCV vigente.
- Clic en la fila para ver el detalle, editar o eliminar. La foto del detalle
  se puede ampliar con un clic.
- Categoría y familia se conservan en la base de datos para clasificación
  interna y edición, pero no se muestran en la lista.
- Paleta neutra: el color se reserva para acciones principales y alertas.

### Carga inteligente de inventario
- **Importar Excel/PDF** con selector nativo y soporte para varios archivos.
- Excel (`.xlsx`): columnas obligatorias `Código`, `Descripción`, `Marca`, `Precio`.
  Opcionales: `Categoría` y `Familia`.
- PDF: líneas con formato `Código | Descripción | Marca | Precio`.
- **Diálogo modal con barra de progreso** durante el análisis y la inserción en
  MongoDB, con porcentaje, archivo en curso y contador de repuestos.
- Al llegar al **100%** el diálogo se cierra automáticamente, el inventario se
  recarga y se muestran los nuevos totales, categorías y precios.
- Upsert por código único: informa nuevos, actualizados y observaciones.

### Reconocimiento visual de repuestos
- **Foto + OCR**: selecciona una imagen de la pieza.
- Intenta OCR real con `pytesseract` si está instalado; si no, simula el
  reconocimiento de forma determinista.
- Asocia la foto al código detectado y guarda imagen comprimida + texto OCR.

### Vendedores
- Listado desde MongoDB con búsqueda y filtro por ciudad.
- Alta con nombre y apellido, cédula, teléfono, ciudad y foto opcional.
- Edición y eliminación de vendedores.
- Código interno generado automáticamente (`MD-VEN-###`).

### Registros móviles de vendedores
- La app Android solicita la cédula previamente registrada por el administrador.
- Al validarla, genera un código único de 6 dígitos con vigencia de 10 minutos.
- El escritorio muestra una notificación y el botón **Móvil** en la barra superior.
- El administrador abre el panel, lee el código y lo entrega al vendedor.
- El vendedor ingresa el código y crea su contraseña definitiva.
- El panel se actualiza cada 3 segundos y permite descartar solicitudes.

### Pedidos recibidos
- Bandeja de pedidos de la red externa, leída desde MongoDB.
- Filtros por estado y documento, búsqueda por pedido/cliente/vendedor.
- Detalle con líneas, subtotal, IVA, total y conversión USD ↔ VES.
- Aprobación, rechazo, paso a despacho y entrega; cada cambio se persiste en
  la colección `pedidos`.

### Finanzas
- Módulo visible en **Análisis**, calculado en tiempo real desde `pedidos`.
- Ingresos reconocidos: pedidos aprobados, en despacho y entregados.
- Cuentas por cobrar: pedidos a crédito en estados reconocidos.
- Ticket promedio, pedidos del periodo y total histórico.
- Gráfico de ingresos de los últimos 7 meses.
- Filtros de periodo: este mes, 3 meses, este año e histórico.
- Tabla de transacciones recientes con acceso a la bandeja de pedidos.

### Arranque en blanco
- No hay datos de prueba ni seed automático en ninguna colección.
- Sin registros, el dashboard muestra `0`, `$ 0.00` y estados vacíos.
- El inventario se carga manualmente o por Excel/PDF; los vendedores se crean
  desde su módulo; los pedidos llegan de la red externa.
- Las métricas se recalculan desde MongoDB en cada visita al panel.

## MongoDB

La conexión se centraliza en `database.py` con `pymongo` y un tiempo de
selección de servidor adaptativo: **2,5 s** para MongoDB local y **4,5 s**
para Atlas, de modo que una red lenta no bloquea la app y activa el respaldo.

### Atlas ya configurado

El proyecto incluye `mongo_uri.txt` (ignorado por Git) con la URI del clúster
`mayorix.oacz9lx.mongodb.net`, base de datos `mayorix`. El ejecutable lee el
archivo que esté junto a `Mayorix.exe`.

Para validar la conexión y crear colecciones/índices:

```bash
python setup_mongodb.py
```

El script es idempotente: crea las colecciones vacías y sus índices únicos,
sin insertar datos de prueba. La app hace lo mismo al iniciar sesión si la
conexión está disponible. Para vaciar inventario, vendedores y pedidos:

```bash
python setup_mongodb.py --vaciar
```

> **Si aparece “Atlas no respondió al handshake TLS”**: agrega la IP pública
> del equipo en **Atlas → Network Access → Add Current IP Address**. El
> clúster debe estar activo. Después usa **Reconectar** en el diálogo de
> conexión o reinicia la app. Un cambio de red/VPN cambia la IP pública.

### Configuración manual

Variable de entorno:

```bash
set MONGO_URI=mongodb+srv://usuario:clave@cluster.mongodb.net/
set MONGO_DB=mayorix
python main.py
```

También se puede editar `mongo_uri.txt` junto a `database.py` (código fuente)
o junto a `Mayorix.exe`, copiando `mongo_uri.example.txt`.

Si no hay URI configurada se intenta `mongodb://localhost:27017/mayorix`.
Si la conexión falla, tarda o el servidor exige autenticación, la app activa
el **modo de respaldo local** y lo indica en Login, Dashboard, Inventario,
Pedidos y Vendedores.

### Colecciones

| Colección | Campos principales |
| --- | --- |
| `usuarios` | `email`, `nombre`, `rol`, `activo`, `salt`, `password_hash` |
| `inventario` | `codigo`, `descripcion`, `marca`, `categoria`, `familia`, `precio`, `foto_b64`, `ocr_text` |
| `vendedores` | `codigo`, `nombre`, `cedula`, `telefono`, `ciudad`, `foto_b64`, `estado` |
| `pedidos` | `pedido_id`, `cliente_id`, `vendedor_id`, `items`, `estado`, `total` |

Las contraseñas se almacenan con **PBKDF2-SHA256 + salt**; nunca en texto plano.
Ninguna colección se siembra automáticamente. `usuarios` comienza vacía y el
primer administrador se registra desde la interfaz; a partir de ahí el registro
queda bloqueado. El resto de colecciones se llenan de forma manual.

### Modo respaldo

El respaldo mantiene los datos en memoria durante la sesión. Permite operar
sin conexión, pero los cambios no sobreviven al cierre ni se sincronizan.

## Estructura

```
Mayorix_Desktop/
├── main.py                     # Login de empresa y navegación principal
├── database.py                 # MongoDB + UTF-8 + respaldo local
├── bcv_service.py              # Microservicio FastAPI de tasa BCV
├── setup_mongodb.py            # Verificación, colecciones vacías e índices
├── reparar_codificacion.py     # Normalización de textos existentes
├── requirements.txt
├── data.py                     # Configuración y utilidades sin datos de prueba
├── mongo_uri.example.txt       # Plantilla de configuración de MongoDB
├── views/
│   ├── login_view.py           # Login exclusivo de empresa
│   ├── dashboard_view.py       # Dashboard administrativo
│   ├── empresa_view.py         # Shell, navegación y sesión
│   ├── inventario_view.py      # Inventario, catálogo/lista, foto y OCR
│   ├── pedidos_view.py         # Pedidos recibidos y cambios de estado
│   ├── finanzas_view.py        # Ingresos, cobranza y transacciones
│   ├── vendedores_view.py      # Alta, edición y eliminación de vendedores
│   ├── importers.py            # Parsers Excel/PDF y OCR
│   ├── tasa_bcv.py             # Cliente y caché de la tasa BCV
│   ├── ui.py                   # Componentes y módulos administrativos
│   └── __init__.py
├── assets/
│   ├── mayorix.ico
│   ├── mayorix.png
│   └── README.md
├── builds/
│   ├── windows_exe/
│   └── android_apk/
└── README.md
```

## Compilación

```bash
flet pack main.py \
  --name Mayorix \
  --icon assets/mayorix.ico \
  --add-data "assets;assets" \
  --hidden-import pandas \
  --hidden-import openpyxl \
  --hidden-import openpyxl.cell._writer \
  --hidden-import pypdf \
  --hidden-import pymongo \
  --hidden-import dns \
  --hidden-import dns.resolver \
  --hidden-import PIL.Image \
  --hidden-import fastapi \
  --hidden-import starlette \
  --hidden-import pydantic \
  --hidden-import uvicorn \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --product-name "Mayorix" \
  --file-description "Mayorix · Sistema de Gestión Mayorista" \
  --company-name "DropeTech" \
  --product-version "2.1.3" \
  --file-version "2.1.3.0" \
  --copyright "Copyright © 2026 DropeTech"
```

El artefacto `dist/Mayorix.exe` se copia a la raíz como `Mayorix.exe`.

> El ejecutable no incluye MongoDB: utiliza la URI configurada o el modo de
> respaldo local.
