# Mayorix Vendedor · Android

Aplicación móvil de la **Red Comercial** de Mayor Disluda, desarrollada por
DropeTech con Python + Flet. Se conecta **directamente a MongoDB Atlas por
internet**, sin depender de la red Wi-Fi del escritorio.

## Módulos

- **Catálogo en vivo:** búsqueda por código, descripción o marca, paginación de
  20 en 20, precio USD y conversión a bolívares con la tasa BCV.
- **Carrito:** cantidades, subtotal, IVA opcional para factura fiscal, condición
  de pago y envío del pedido.
- **Pedidos:** historial del vendedor, estados y detalle.
- **Perfil:** datos del vendedor, tasa BCV y cierre de sesión.
- **Registro por cédula:** validación contra los vendedores pre-cargados desde
  el escritorio, código único notificado al administrador y creación de la
  contraseña definitiva.

## Sesión persistente

- Al iniciar sesión o completar el registro, la app crea un **token aleatorio**
  y lo guarda en el almacenamiento privado del dispositivo.
- El token se guarda hasheado en la colección `sesiones_movil` de Atlas.
- La contraseña nunca se guarda en el teléfono.
- Al volver a abrir la app, si el token local sigue vigente, entra directamente
  al catálogo sin mostrar el login.
- La sesión dura 30 días y se valida en segundo plano contra Atlas.
- Si el token fue revocado o expiró, la app limpia la sesión y vuelve al login.
- Si no hay internet, conserva la sesión local y muestra los errores de
  conexión sin obligar a iniciar sesión.
- Cerrar sesión borra el archivo local y revoca el token en Atlas.

## Flujo de primer registro

1. El administrador registra al vendedor con su cédula en el escritorio.
2. En el móvil, el vendedor abre **Primer registro con mi cédula**.
3. El móvil valida la cédula y crea una solicitud en `solicitudes_registro`.
4. El escritorio muestra una notificación y el botón **Móvil** con el código
   único de 6 dígitos, vigente por 10 minutos.
5. El administrador entrega el código al vendedor.
6. El vendedor ingresa el código y crea su contraseña.
7. El acceso queda en `accesos_vendedor` para los siguientes inicios de sesión
   por cédula y contraseña.

## Arquitectura

```
APK Android (Flet + pymongo)
        │  TLS
        ▼
MongoDB Atlas · base mayorix
```

El APK se conecta directamente a Atlas. La URI **no viaja dentro del APK**:
en el primer arranque se muestra una pantalla de **Configuración del
dispositivo** para que el administrador la pegue una sola vez. Se guarda en el
almacenamiento privado de la aplicación (`FLET_APP_STORAGE_DATA`).

**Importante:** para que funcione desde cualquier red móvil, Atlas debe
permitir las IP de los teléfonos en **Network Access**. Para uso fuera de la red
fija, agrega `0.0.0.0/0` o usa Private Endpoint/VPN según la política de la
empresa.

### TLS tolerante en redes móviles

La app abre la conexión con `tls=True` y `tlsAllowInvalidCertificates=True`
para tolerar operadores o proxies que interceptan el certificado del clúster.
Eso evita que el login se quede bloqueado por una cadena de certificados
inválida, pero **desactiva la validación TLS**: reduce la protección frente a
un intermediario. Para volver al modo estricto, compila con:

```powershell
$env:MAYORIX_TLS_ESTRICTO = "1"
```

o define esa variable antes de abrir la app en desarrollo. Si el clúster exige
IP permitida, TLS tolerante no sustituye la lista de acceso de Atlas: si la IP
del teléfono no está autorizada, la conexión seguirá rechazándose.

La URI configurada es una credencial del dispositivo. Se recomienda:

- Crear un usuario de Atlas exclusivo para la app móvil, con permisos mínimos
  sobre `mayorix`.
- No usar el usuario administrador del clúster.
- Rotar la credencial si un teléfono se pierde.
- Para una distribución masiva, usar una API HTTPS intermedia.

## Ejecutar en desarrollo

```powershell
cd D:\PROYECTOS\Mayorix\Mayorix_Mobile
python main.py
```

## Compilar APK

```powershell
cd D:\PROYECTOS\Mayorix\Mayorix_Mobile
flet build apk . --project "Mayorix Vendedor" `
  --org com.droptech --bundle-id com.droptech.mayorix.vendedor `
  --build-version 1.1.3 --build-number 5 --yes
```

El APK queda en `build/apk/Mayorix Vendedor.apk`.

## Rendimiento

- Catálogo paginado con `skip`/`limit` de 20 y proyección sin fotos.
- Sin caché local del catálogo completo.
- El carrito vive en memoria durante la sesión.
- El servidor de tasas BCV se consulta con timeout y respaldo local.

## Estructura

```
Mayorix_Mobile/
├── main.py            # Shell, sesión y registro
├── login_view.py      # Login centrado y flujo de código
├── catalog_view.py    # Catálogo paginado
├── cart_view.py       # Carrito y envío
├── orders_view.py     # Historial y detalle
├── profile_view.py    # Perfil del vendedor
├── data_mobile.py     # Acceso directo a Atlas
├── rate.py            # Tasa BCV
├── ui_mobile.py       # Componentes táctiles
├── assets/
├── pyproject.toml
└── requirements.txt
```
