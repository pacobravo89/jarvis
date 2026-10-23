# JARVIS 1.0 — Aplicación local para Windows

Proyecto integral **experimental**, no producto de producción. Se ha comprobado la sintaxis y pruebas unitarias básicas, pero no se ha probado el hardware de tu Windows desde este entorno.

## Requisitos
- Windows 11; Python 3.12; Ollama instalado y modelo `qwen2.5:1.5b` descargado.
- Micrófono y altavoces. Voz Piper `es_ES-davefx-medium.onnx` y `.onnx.json` que ya descargaste en v0.4.
- Conexión a Internet para instalar paquetes y para noticias, Wikipedia, búsquedas y tiempo.

## Instalación conservando tu JARVIS actual
1. **No sobrescribas** `C:\JARVIS` sin copia. Extrae este ZIP en `C:\JARVIS_NUEVO`.
2. Copia `C:\JARVIS\es_ES-davefx-medium.onnx` y `C:\JARVIS\es_ES-davefx-medium.onnx.json` a `C:\JARVIS_NUEVO\voices\`.
3. Abre PowerShell en `C:\JARVIS_NUEVO` y ejecuta `instalar.bat` (o `py -3.12 -m venv .venv` seguido de `.venv\Scripts\python.exe -m pip install -r requirements.txt`).
4. Confirma que Ollama está funcionando: `ollama list` y, si es necesario, `ollama serve` en otra terminal.
5. Ejecuta `iniciar_jarvis.bat` y abre `http://127.0.0.1:8765`.
6. Prueba **primero por texto**. Para usar la voz pulsa **Activar voz**. El micrófono predeterminado del código es `1`.

## Configuración
Variables de entorno opcionales (PowerShell, antes de ejecutar):
```powershell
$env:JARVIS_MIC='1'
$env:JARVIS_MODEL='qwen2.5:1.5b'
$env:JARVIS_ALLOWED_DIRS="$HOME\Documents;$HOME\Desktop"
$env:JARVIS_VOICE='C:\JARVIS_NUEVO\voices\es_ES-davefx-medium.onnx'
```
Por seguridad, el servidor escucha exclusivamente en `127.0.0.1`, no está publicado en la red local. No lo expongas a Internet: no incluye autenticación.

## Funciones implementadas
- Chat local con Ollama, conversación histórica y recuerdos explícitos en SQLite.
- Activación «Jarvis» y preguntas de seguimiento mediante Whisper Base; Piper para voz.
- Interfaz visual con tarjetas para noticias, biografías, enlaces, documentos y listas.
- Noticias por Google News RSS; búsquedas web básicas con HTML público (pueden fallar si cambia el buscador), Wikipedia, lectura de páginas públicas y Open-Meteo.
- Búsqueda por nombre y lectura de PDF, DOCX, XLSX, TXT y archivos de código en carpetas autorizadas.
- Procesos Windows, abrir únicamente bloc de notas/calculadora/explorador con confirmación; abrir URL con confirmación.
- Git status de un repositorio autorizado, sin ejecutar comandos arbitrarios.
- Tareas y recordatorios guardados en SQLite. **Los recordatorios se registran y se pueden consultar, pero todavía no hay notificaciones persistentes en segundo plano**.

## Límites conocidos (importante)
- **No hay navegador autónomo Playwright ni control general de ventanas/volumen/VLC**: son integraciones pendientes. Tampoco se incluye control de Home Assistant ni visión.
- No hay índice vectorial ni embeddings todavía; la memoria es explícita y la recuperación usa coincidencia textual.
- La extracción web es parcial y no evita paywalls; noticias RSS proporcionan titulares, no artículos completos. Búsqueda web pública puede fallar o bloquearse.
- Qwen2.5 1.5B puede elegir mal una herramienta o interpretar mal fechas/argumentos; revisa los resultados.
- La voz puede tardar en cargar; el navegador consulta periódicamente el estado. No hay transmisión de audio desde el navegador: el micrófono es el del ordenador donde corre Python.
- El código de lectura de URL bloquea direcciones privadas y redirecciones, pero **no es un navegador endurecido para contenidos hostiles**. No lo expongas a usuarios no confiables.
- No se migran automáticamente los mensajes de `jarvis_memory.db` anterior: se conserva intacto y se crea una nueva base `data/jarvis.db`.

## Seguridad
- Sin shell arbitraria. Lista permitida de aplicaciones.
- Archivos limitados a directorios configurados, máximo 12 MB.
- Las acciones `open_app` y `open_url` requieren confirmación en interfaz.
- Los datos de internet se incorporan como contexto, no como órdenes; aun así, un modelo pequeño puede equivocarse.

## Desarrollo
Ejecuta `python -m compileall -q .` y `python -m unittest discover -s tests` para comprobaciones básicas. La estructura está separada en `jarvis/` (servidor, herramientas, motor, audio, almacenamiento) y `web/` (interfaz).
