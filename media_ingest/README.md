# Marty Roads — módulo permanente de adquisición v1

Un único módulo para Work y el repositorio Codex existente. No depende de Klipa ni de servicios con créditos. No modifica voz, compositores ni SHOT_PLAN existente.

## Instalación
Python 3.10+, FFmpeg/ffprobe y Node compatible con yt-dlp. En Linux ejecutar `sh setup.sh` desde este directorio. El instalador crea un entorno aislado y fija las dependencias comprobadas. Node y FFmpeg deben estar instalados por el entorno. TLS usa truststore y certificados del sistema; nunca se desactiva la verificación. Usar `.venv/bin/python` en los comandos siguientes. En Work se verificó Python 3.12, FFmpeg 6.1 y Node; pip funciona.

## Flujo de producción
1. `python doctor.py URL` comprueba herramientas y metadatos. No confundir metadatos accesibles con vídeo descargable.
2. `python ingest.py discover "SH130 opening day road" candidates.json` localiza hasta cinco candidatos. El agente comprueba correspondencia con escena, fecha/lugar y autorización; la búsqueda por sí sola no autoriza descargas ni verifica autenticidad. También se aceptan URLs ya autorizadas directamente.
3. Crear un manifiesto como test_youtube.json: proyecto, fuentes autorizadas, escenas, intervalo y salida. `max_height: null` solicita máxima resolución anunciada; para producción puede fijarse 1080/2160 según recorte y render. No escala una fuente pequeña para fingir definición. La mejor resolución accesible se valida con bytes reales: un fallo no se degrada silenciosamente a baja calidad.
4. `python ingest.py build request.json --cache /ruta/temporal/media_cache`. Descarga la fuente una vez por proyecto, conserva los originales temporales, prepara escenas H.264 y valida ffprobe + decodificación completa + duración + SHA256. Sin audio ajeno salvo use_source_audio=true. Salidas por proyecto/sources/ID y proyecto/scenes/ESCENA.
5. Si falla, STATUS.json conserva causa; continuar otras escenas/proyectos. Solicitar al usuario URL concreta y MP4. Añadir `local_file` a esa fuente: utiliza exactamente el mismo flujo de validación y edición. No enviar estos vídeos a Drive.
6. `python ingest.py publish /cache/PROYECTO/EDIT_MEDIA.json /ruta/SH130_PRODUCCION`. Copia assets a assets/clips/INGEST_Sxxx.mp4 y crea INGEST_SHOT_PLAN_PATCH.json; aplicar la selección al plan de la nueva revisión. Nunca sobrescribe el plan ni un asset distinto existente. Cambios de voz no forman parte de este módulo.
7. Tras render final completo y revisión audiovisual efectiva: `python ingest.py validate-final INDEX FINAL.mp4 --reviewed`. Registra hash del render y del índice. El flag confirma una revisión realizada; no la realiza ni debe usarse para simularla.
8. `python ingest.py cleanup INDEX` solo muestra cachés elegibles. `--execute` elimina únicamente sources y scenes de ese proyecto tras validar recibo y hash actual del render. Conserva copias de edición y render. Sin limpieza por edad, cuotas o fallo de descarga. No borrar antes de validación final. Los tests usan una confirmación simulada sobre una fixture propia para probar el bloqueo.

Los archivos de audio/vídeo, cookies, URLs CDN firmadas y secretos no se guardan en Git ni Drive. Persistir solo scripts, requisitos, manifiestos sin secretos, índices/recibos y resultados textuales. Antes de procesos costosos actualizar ESTADO_ACTUAL.md. Las rutas temporales pueden desaparecer con la sesión: conservar URL/intervalos/receta permite readquirirlos, pero no promete recuperar un vídeo retirado de Internet.

## Pruebas y estado 26/10/2026
`python test_module.py`: dos tests pasan. Se crea material propio de 3 s, se sirve por HTTP local, se descarga realmente con yt-dlp, se valida, recorta, publica al editor, genera un render y comprueban limpieza bloqueada antes de validación, modo simulación y limpieza después. Reutilización de caché, rechazo de HTML, rutas inseguras y fuente no autorizada incluidos. Es una prueba local completa; NO certifica acceso a un CDN externo.

Prueba externa solicitada: https://www.youtube.com/watch?v=6AvoHnZx0Oo — título «Nadie veía mis videos, hasta que hice esto.», Veloz Redes, 478 s. Metadatos y JS funcionan. Máximo anunciado 1920×1080/30; intento 137+251-drc devuelve HTML Site Unavailable de 195 bytes por flujo. Un intento 360p/18 da el mismo HTML. No hay vídeo descargado válido ni máxima calidad descargada que entregar. El bloqueo observado está en la entrega CDN desde este Work; la página no identifica quién lo impone. No atribuirlo sin pruebas a copyright, credenciales o fallo universal de yt-dlp.

Alternativa sin duplicación: este mismo directorio en `trabajosuvalvaro-stack/youtube.auto.download`, ejecutado en su entorno Codex con acceso a YouTube/CDN y disco suficiente. Se comprobó el repositorio y permisos; no se ha ejecutado su entorno remoto ni se afirma que ese CDN funcione allí. Ejecutar setup.sh, doctor.py URL y build test_youtube.json. No requiere KLIPA_TOKEN. No se activan workflows de pago ni se consumen créditos externos.

Fuentes técnicas: https://github.com/yt-dlp/yt-dlp y https://github.com/yt-dlp/yt-dlp/wiki/EJS . Las dependencias y TLS se validaron en el entorno, no solo por documentación.
