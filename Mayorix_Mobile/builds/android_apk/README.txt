Mayorix Vendedor · APK Android 1.1.3
====================================

APK universal para Android 7.0+ (minSdk 24), conexión directa a MongoDB Atlas.

Archivo principal:
    D:\PROYECTOS\Mayorix\Mayorix_Vendedor.apk

Copia de build:
    D:\PROYECTOS\Mayorix\Mayorix_Mobile\build\apk\Mayorix Vendedor.apk

Datos del paquete:
- Nombre: Mayorix Vendedor
- Paquete: com.droptech.mayorix.vendedor
- Versión: 1.1.3 (versionCode 5)
- Tamaño: 142.858.011 bytes
- SHA-256: B28DD6D750629682CE625B54D773CD4B4B835995D4C84EFD4F9012568BEBC6B0
- Firma: debug (instalable por sideload; para producción usar keystore release)

Primer arranque
---------------
El APK NO contiene la URI de Atlas. En el primer arranque muestra una pantalla
de configuración para el administrador. Allí se pega la URI remota de MongoDB
Atlas y se guarda en el almacenamiento privado del dispositivo.

Usa preferentemente un usuario de Atlas con permisos mínimos sobre `mayorix`,
no una cuenta atlasAdmin.

Después de configurar, el vendedor sólo ve el login centrado con cédula,
contraseña y "Primer registro con mi cédula".

Funcionalidad
-------------
- Catálogo en vivo paginado de 20 en 20.
- Carrito, IVA opcional y tasa BCV.
- Historial y detalle de pedidos.
- Primer registro por cédula.
- Código único de 6 dígitos notificado al escritorio.
- Contraseña definitiva con PBKDF2-SHA256.
- Sesión directa contra Atlas con TLS.

APK preconfigurado (instalación asistida)
-----------------------------------------
    D:\PROYECTOS\Mayorix\Mayorix_Vendedor_preconfig.apk
- Versión: 1.1.3 (versionCode 5)
- Tamaño: 142.858.219 bytes
- SHA-256: 08DA960936A90DFB6E5FA6C5164B40A49785D23D9CC4B5B658724792DBFC2334
- Incluye atlas_config.pyc con la URI del clúster; abre directo al login.
- Se genera compilando con atlas_config.py presente y se excluye del APK
  genérico con --exclude atlas_config.py.

TLS tolerante
-------------
La conexión usa tls=True y tlsAllowInvalidCertificates=True para tolerar
operadores/proxies que interceptan el certificado del clúster. Esto desactiva
la validación de la cadena TLS: reduce la protección ante un intermediario.
Para volver al modo estricto, compilar con MAYORIX_TLS_ESTRICTO=1.
El TLS tolerante no sustituye la lista de acceso de Atlas: si la IP del
teléfono no está autorizada, la conexión seguirá rechazándose.

Red de Atlas
------------
Para que funcione desde cualquier red móvil, la lista de acceso de Atlas debe
incluir las IP públicas de los teléfonos. Para cobertura total se usa
0.0.0.0/0, idealmente con un usuario de Atlas de permisos mínimos.

Recompilar
----------
    cd D:\PROYECTOS\Mayorix\Mayorix_Mobile
    flet build apk . --project "Mayorix Vendedor" `
      --org com.droptech --bundle-id com.droptech.mayorix.vendedor `
      --build-version 1.1.3 --build-number 5 --yes

El APK incluye pymongo y extensiones nativas para arm64-v8a, armeabi-v7a y
x86_64. No incluye URI, `mongo_uri.txt` ni el backend local.
No habilita tráfico HTTP en claro: Atlas se usa por TLS.
