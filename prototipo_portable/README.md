# Detector para PC y Raspberry Pi

Adaptación local del programa `flicker_detector_v4.py` de Cristian7732, commit `055f888878471ded7b731611c08c344301ea7091`. Esta entrega conserva MediaPipe Face Mesh y las posiciones de ojos y boca del original. Los archivos originales se conservan en la raíz del repositorio.

Para continuar en una PC Fedora, sigue [FEDORA.md](FEDORA.md).

## Equipo objetivo

- Raspberry Pi 5 de 4 GB, fuente oficial de 27 W y refrigeración activa.
- Cámara web USB UVC; comenzar solicitando 640 × 480 píxeles.
- Parlante de audio USB seleccionado como salida predeterminada del sistema.
- microSD y monitor/teclado para la primera configuración. Después puede utilizarse `--no-display`.

También puede probarse en una PC Windows de 64 bits. No se han medido FPS ni exactitud en Raspberry Pi. La existencia de paquetes ARM64 permite preparar la instalación, pero no sustituye la prueba del equipo completo.

## Decisión de compatibilidad

Para reducir cambios se conserva la interfaz legacy `mp.solutions.face_mesh`, con **MediaPipe 0.10.18 y Python 3.11 o 3.12**. Hay paquetes oficiales para Windows x64 y Linux ARM64. No instalar este proyecto con Python 3.13/3.14 ni actualizar MediaPipe automáticamente.

La ruta propuesta para la placa es **Raspberry Pi OS Legacy de 64 bits, Debian Bookworm, con escritorio y Python 3.11**. Es una imagen distinta de la edición actual basada en Trixie. Verifica la versión mostrada por Imager; no asumas que la primera opción coincide. No se ha probado esta entrega en la placa.

Face Mesh es una interfaz antigua. Migrar a Face Landmarker es una opción de mantenimiento posterior; requiere probar de nuevo los indicadores y no proporciona automáticamente mayor precisión. Esta elección busca conservar el algoritmo de la tesis y facilitar una primera prueba reproducible.

## Instalación en Raspberry Pi

1. Preparar la microSD con Raspberry Pi Imager, seleccionando Bookworm de 64 bits con escritorio. Verifica que la tarjeta elegida es la destinada al prototipo: grabar el sistema borra esa tarjeta.
2. Conectar cámara, parlante, monitor y alimentación. Seleccionar el parlante USB en la configuración de sonido.
3. Extraer este paquete en una carpeta y abrir allí una terminal.
4. Comprobar sistema y preparar un entorno virtual:

```bash
uname -m
python3 --version
sudo apt update
sudo apt install python3-venv libgl1 libglib2.0-0 libportaudio2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip check
```

`uname -m` debe indicar `aarch64` y Python debe ser 3.11 o 3.12. No utilizar `sudo pip` ni `--break-system-packages`. Si la versión no coincide, revisar la imagen instalada antes de intentar forzar paquetes.

5. Comprobar por separado software, sonido y cámara:

```bash
python -m unittest -v test_detector
python detector.py --check
python detector.py --test-audio
python detector.py
```

`--check` ejecuta una inferencia sobre una imagen vacía, sin abrir cámara ni emitir sonido. `--test-audio` debe producir un tono en el parlante que vas a utilizar. El programa completo se detiene con `q` o Ctrl+C.

La primera prueba con rostro debe hacerse en una mesa, con iluminación suficiente. Comprueba que los valores cambian al abrir/cerrar ojos y boca, que la alerta suena y que perder el rostro produce `SIN DATOS`.

## Instalación en Windows

Usar Python 3.11 o 3.12 de 64 bits. En una terminal PowerShell ubicada en la carpeta extraída:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python.exe -m unittest -v test_detector
.\.venv\Scripts\python.exe detector.py --check
.\.venv\Scripts\python.exe detector.py --test-audio
.\.venv\Scripts\python.exe detector.py
```

Si instalaste 3.11, cambia `py -3.12` por `py -3.11`. No se necesita cambiar la política de ejecución de PowerShell.

## Uso y parámetros

```bash
python detector.py --camera 1
python detector.py --no-display
python detector.py --mute
python detector.py --ear 0.18 --mar 0.6 --closed-seconds 1.0 --mouth-seconds 2.0
python detector.py --help
```

| Parámetro | Valor inicial | Interpretación |
|---|---:|---|
| EAR | 0,18 | Muestra ocular cerrada por debajo del valor |
| MAR | 0,60 | Muestra de boca abierta por encima del valor |
| Cierre sostenido | 1 segundo | Activa la regla ocular |
| Apertura bucal sostenida | 2 segundos | Activa la regla bucal |
| Ventana temporal | 60 segundos | Historia continua necesaria para calcular porcentaje |
| Porcentaje de cierre | Más del 50 % | Activa la regla de cierre acumulado |
| Pausa entre sonidos | 5 segundos | Limita repeticiones mientras persiste el aviso |
| Intervalo máximo entre observaciones | 0,5 segundos | Por encima se reinician ventana y eventos en curso |

Todos son parámetros experimentales. Los valores temporales nuevos no son equivalentes a las reglas por fotogramas de v4 ni están validados clínicamente. La apertura bucal puede confundirse con hablar o reír.

El porcentaje temporal integra el estado ocular entre observaciones y recorta a la ventana configurada. Incluye cierres breves: por ello se muestra como **cierre temporal**, no como PERCLOS validado. Espera una ventana completa antes de activar esa regla. Las alertas por duración de ojos/boca sí pueden funcionar durante esa espera.

Una pérdida del rostro, dato no finito o intervalo largo reinicia los eventos en curso y la ventana. Conserva los conteos completos anteriores. Si la tasa de procesamiento cae por debajo de unas dos observaciones por segundo, la ventana puede reiniciarse continuamente con el intervalo máximo predeterminado. Medir rendimiento antes de ampliar ese intervalo: aumentar la tolerancia no recupera eventos que la cámara no observó.

## Cambios frente a v4

- Sonido con `sounddevice`/PortAudio en ambos sistemas, generando un tono local. Elimina la dependencia Windows `winsound` y del archivo de audio vacío. `sounddevice` ya forma parte de las dependencias de MediaPipe.
- Usa tiempo monotónico y segundos en las reglas de duración.
- Cuenta candidatos a parpadeo una sola vez al reabrir (duración observada entre 0,06 y 0,8 segundos). Los cierres largos no se convierten en múltiples parpadeos.
- Cuenta aperturas bucales largas al terminar; el conteo acumulado ya no dispara alertas inmediatas ante cualquier nueva apertura.
- Invalida mediciones geométricas degeneradas y reinicia estados al perder seguimiento.
- Solicita resolución baja y elimina el dibujo de toda la malla. La mejora real de rendimiento debe medirse en la placa.
- Incluye modo sin ventana, mensajes de error y cierre de recursos.
- Presenta FPS medios y tiempo de procesamiento por imagen. Este tiempo no es la latencia total desde la escena hasta el sonido.

NumPy se utiliza para preparar imágenes y audio; las distancias se calculan con `math.dist`. No se ha añadido registro de video ni CSV, inicio automático, visión nocturna ni control del vehículo. El conteo por minuto y el dibujo de puntos del original se omiten en esta primera variante.

## Comprobaciones pendientes en el equipo físico

1. Instalación y `pip check` en la placa; confirmar versión de sistema y Python.
2. Captura continua y resolución efectiva de la cámara elegida.
3. Emisión audible por el parlante USB durante una alerta real del programa.
4. FPS, calentamiento y estabilidad en sesiones prolongadas.
5. Calibración de umbrales con datos separados de la evaluación final.
6. Registro de resultados y anotación independiente para la tesis.

No se atribuye precisión de detección a las pruebas sintéticas del software. La salida `OBSERVANDO` indica seguimiento, no confirma que una persona esté despierta.

## Si algo falla

- **No matching distribution / falta `mp.solutions`:** revisar Python, arquitectura y `requirements.txt`; utilizar un entorno nuevo.
- **No encuentra PortAudio en Linux:** instalar `libportaudio2`.
- **No hay salida de audio:** seleccionar el parlante USB predeterminado y ejecutar `python -m sounddevice` para ver dispositivos. `--mute` solo sirve para diagnóstico visual.
- **No abre cámara:** cerrar aplicaciones que la usen y probar `--camera 1`.
- **Error de ventana en SSH:** ejecutar `--no-display`, o abrir una terminal dentro del escritorio de la placa.
- **Fallo de cámara durante ejecución:** el programa se detiene con error; no continúa mostrando un estado anterior como si fuera válido.

## Fuentes técnicas

- Código original: https://github.com/Cristian7732/detector_de_somnolencia/blob/055f888878471ded7b731611c08c344301ea7091/flicker_detector_v4.py
- Paquetes ARM64 de MediaPipe: https://pypi.org/project/mediapipe/0.10.18/#files
- Face Mesh: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md
- Sistemas oficiales: https://www.raspberrypi.com/software/operating-systems/
- Audio PortAudio: https://python-sounddevice.readthedocs.io/en/0.5.3/installation.html

La tesis Word entregada antes de esta adaptación describe v4. Si se adopta esta variante, actualizar las secciones de sonido, reglas temporales, conteo y cálculos para conservar coherencia.
