# Marty Roads — almacenamiento de producción y concurrencia

## Política operativa

- El disco local es área de trabajo; conservar allí código/configuración, recursos actualmente necesarios y resultados todavía no respaldados. Los documentos pesan poco: priorizar pesos de modelos, duplicados de archivos grandes y derivados regenerables.
- Consultar `python storage_budget.py status` antes de descargar paquetes, descomprimir y renderizar. Registrar cada carpeta de proyecto con `reserve ID RUTA --peak-gib N`. N representa el máximo estimado de TODO su conjunto local (fuentes, copias descomprimidas, proxies, audio, bloques y máster); no es tamaño del MP4 final.
- Reservar 4 GiB libres como margen común. Al admitir otro proyecto se descuentan también las necesidades futuras de los proyectos ya registrados. Si falta espacio, esperar o reducir su conjunto de trabajo, sin empezar escrituras condenadas a fallar. Volver a comprobar antes de cada lote; procesos externos pueden consumir disco.
- Registro coordinado local: /workspace/scratch/MARTY_STORAGE/reservations.json, con bloqueo flock y escrituras atómicas. No es una cuota del sistema ni limita procesos que lo ignoren. Cada Work debe aplicar el protocolo; las sesiones ya en curso no se actualizan automáticamente. `release ID` retira únicamente la reserva, nunca los archivos. No hay caducidad automática de proyectos activos.
- Valores iniciales orientativos: 5 GiB por proyecto QHD, ajustables a lo que mida su receta. No garantizar un número fijo de vídeos paralelos: depende del material y del método. Se pueden investigar/editar varios; espaciar descargas, descompresión y renders de mayor consumo si no caben juntos.

## Evitar multiplicar el material

- Una sola copia de cada fuente dentro del proyecto; las escenas referencian origen, entrada y salida. No descargar el mismo vídeo para cada escena.
- Proxies 720p solo para trabajo/selección, generación a demanda. El render final usa originales y gráficos/texto/3D a resolución objetivo. No mejorar resolución reduciendo la calidad de las fuentes.
- Renderizar bloques comprimidos con recibos; evitar secuencias de PNG o vídeo sin comprimir para minutos completos. Hacer fluir fotogramas al codificador cuando el motor lo permita. Conservar la escena/modelo/cámara y la configuración que regeneran el resultado.
- Mantener una versión buena y la versión en curso; los tanteos fallidos o duplicados se retiran después de comprobar que no son necesarios. No acumular ZIP empaquetado + ZIP bajado + descompresión duplicada sin función.
- Guardar código, decisiones, modelos propios, audio y checkpoints externos por hitos; verificar la copia antes de desalojar resultados únicos. Un enlace sin transferencia confirmada no cuenta como copia.
- Vídeos descargados: NO subirlos a Drive. Conservarlos localmente hasta validar el render final según el protocolo vigente. Reducir descargas al material seleccionado; si estas fuentes superan el presupuesto, serializar esos trabajos o usar un almacenamiento aprobado de mayor capacidad. No inventar otra ubicación ni borrar fuentes de proyectos activos para forzar concurrencia.
- Al terminar: decodificación, revisión audiovisual, máster/editables respaldados y recibos verificados; después retirar cachés/locales redundantes. Nunca borrar originales únicos, datos de otro proyecto activo ni checkpoints necesarios para restaurar una cadena incremental.

## Modelos y dependencias

- Los pesos públicos de experimentos concluidos/descartados son caché reproducible. Antes de retirarlos conservar repositorio, revisión exacta, inventario/recibos, configuración y resultados; comprobar archivos abiertos en los procesos visibles. Nunca retirar un modelo usado por producción activa.
- No cargar modelos locales de varios GB por rutina para tareas ya resueltas por herramientas existentes. No volver a descargar los evaluadores narrativos descartados para cada vídeo.
- Reutilizar entornos compatibles de dependencias ya probados. No fusionar ni borrar dependencias de proyectos activos sin comprobar compatibilidad.
- Si una caché se elimina, registrar ubicación y procedimiento de restauración. El aprendizaje vive en scripts/resultados/manuales; no requiere mantener sus pesos cargados en disco.

## Uso

```sh
python storage_budget.py status
python storage_budget.py reserve EPISODE /ruta/proyecto --peak-gib 5
python storage_budget.py check --next-write-gib 0.5
# Ejecutar un lote y volver a comprobar antes del siguiente.
python storage_budget.py release EPISODE
```

## Pruebas

`python -m unittest discover -s . -p test_storage_budget.py -v`
Cubre admisión conjunta, incremento de reservas contabilizando datos existentes, rechazo sin corromper el registro, raíces solapadas y liberación sin borrar archivos.
