# Klipa — módulo adicional Marty Roads

Estado 2026-10-26: PREPARADO, AUTENTICACIÓN Y DESCARGA REAL PENDIENTES.
Servidor verificado: https://mcp.klipa.ai/mcp devuelve HTTP 401 sin credencial. KLIPA_TOKEN no existe en este entorno. El directorio de plugins no devuelve Klipa. No se han gastado créditos ni descargado un vídeo con Klipa. No afirmar que el plan Pro habilita un descargador de originales sin verificarlo en el catálogo autenticado.

## Activación única

Opción ChatGPT Work: en https://chatgpt.com/plugins añadir servidor MCP personalizado, nombre Klipa, URL https://mcp.klipa.ai/mcp; completar el acceso OAuth y Permitir. Activar sus herramientas en la conversación. El asistente no puede completar la autorización personal sin intervención del titular.

Opción scripts/Codex: configurar KLIPA_TOKEN como secreto del entorno que realmente ejecuta el módulo. Una clave configurada en otro entorno no se transfiere a Work. No pegar contraseñas o tokens en el chat, código, manifiestos, argumentos CLI o Drive. Usar la clave personal que ofrece https://klipa.ai/es/mcp. Respetar caducidad y revocación; no prometer persistencia entre reinicios.

## Secuencia de producción

1. Reutilizar material verificado existente; usar yt-dlp como primera vía para originales, Klipa como alternativa cuando haya conexión autenticada y una herramienta adecuada comprobada.
2. Ejecutar `python klipa_bridge.py check` y `python klipa_bridge.py catalog /ruta/privada/catalog.json`. Inspeccionar nombres, descripciones y esquemas reales; nunca inventar endpoints ni nombres de herramientas. Consultar límites/consumo con las herramientas que anuncie el catálogo antes de procesar.
3. Preferir descarga/importación del original sin recodificar si se expone expresamente. Si solamente ofrece resultados procesados, registrar la transformación; no equipararla a la máxima calidad de la fuente. No generar subtítulos, clips verticales u otras transformaciones para obtener material horizontal sin necesidad editorial.
4. Preparar argumentos JSON según el esquema. `python klipa_bridge.py call NOMBRE argumentos.json` muestra esquema sin iniciar el trabajo; `--execute` llama la herramienta. Guardar ID del trabajo en checkpoint; consultar el mismo trabajo tras una interrupción, evitar duplicados. No existe reintento automático de una operación que consume créditos.
5. Cuando el trabajo termine, colocar únicamente la URL de resultado en un archivo local privado, fuera del repositorio y Drive. `python klipa_bridge.py receive /ruta/privada/result.url /cache/PROYECTO/klipa/ID/source.mp4` descarga por HTTPS sin enviar la credencial MCP al CDN, comprueba espacio, rechaza HTML, valida vídeo con ffprobe y decodificación completa, y guarda SHA256 y resolución. No sobrescribe archivos existentes. Las descargas interrumpidas quedan `.pending` para inspección; no se reutilizan como completas.
6. Importar el resultado mediante el campo `local_file` del manifiesto ya existente de ingest.py, conservando URL pública de procedencia, ubicación, época y nota de autorización. El archivo de URL temporal nunca se incorpora al manifiesto ni al respaldo. Ejecutar build/publish habituales; así se reutilizan organización por escena y controles ya probados.
7. Revisar visualmente resolución, encuadre, marcas de agua, recodificación y correspondencia documental antes de admitir el material. No inferir calidad original a partir de resolución solamente.
8. Retener los archivos hasta validar el render final técnica y perceptivamente. `ingest.py cleanup` gestiona únicamente sources/scenes bajo su caché; la descarga Klipa de staging se conserva y su retirada requiere comprobar el mismo FINAL_VALIDATED.json. No hay borrado por antigüedad. No subir vídeos descargados a Google Drive.

## Recuperación y límites

Checkpoint: proyecto/escena, fuente pública, ID de trabajo, estado, fichero local, SHA256, pruebas, bloqueo y siguiente operación. Nunca incluir tokens, cookies, sesiones o enlaces firmados. Código canónico en este repositorio; instrucciones/estado en Drive. El catálogo y la autorización pueden variar entre cuentas o planes.

Pruebas realizadas: HTTP 401 real; ausencia de secreto detectada correctamente; tres pruebas locales con transporte simulado (handshake/catálogo, transferencia sin credencial al CDN ni URL en recibo, protección de sobrescritura/HTTPS). Estas pruebas NO validan autenticación real, descarga externa, consumo, calidad máxima ni herramientas disponibles para la cuenta Pro.

Siguiente operación exacta: autorizar Klipa en ChatGPT y activar herramientas, o provisionar KLIPA_TOKEN en el entorno ejecutor; obtener catálogo autenticado; verificar herramienta para originales y límites; probar https://youtu.be/6AvoHnZx0Oo, medir integridad/resolución y pasar el mismo manifiesto a edición. Si no existe descarga de originales, marcar capacidad no disponible y continuar yt-dlp/MP4 manual sin fabricar conversiones innecesarias.
