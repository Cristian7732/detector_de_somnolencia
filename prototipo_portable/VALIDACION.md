# Validación de esta entrega

5 de octubre de 2026. Comprobaciones realizadas sobre la variante portable antes de su publicación.

## Comprobado

- Instalación en entorno aislado Windows x64 con Python 3.12.14.
- MediaPipe 0.10.18, OpenCV 4.10.0.84, NumPy 1.26.4 y sounddevice 0.5.6.
- `pip check`: sin conflictos de dependencias.
- `python detector.py --check`: Face Mesh inicializa y ejecuta una inferencia CPU sobre imagen vacía sin detectar rostro.
- Seis pruebas automáticas aprobadas: geometría y escala, valores inválidos, cierre breve único, apertura bucal larga única, pérdida de datos y huecos temporales, porcentaje temporal a 10/20/30 observaciones por segundo y recorte de ventana.
- Resolución y descarga de paquetes con pip para Linux ARM64/Python 3.11, usando etiquetas manylinux compatibles con Bookworm. No requirió compilación de los paquetes Python seleccionados. El informe de pip es una comprobación de distribución de paquetes realizada desde Windows, no una instalación ni una ejecución sobre Linux.

## No comprobado

- Instalación y ejecución en la PC Fedora del usuario.

- Ejecución física en Raspberry Pi, instalación de bibliotecas del sistema y detección de un rostro real.
- Captura de cámara, salida audible, FPS en la placa, temperatura, consumo y latencia hasta el sonido.
- Exactitud, sensibilidad o utilidad preventiva en personas; los casos de prueba son sintéticos.

La prueba inicial de imports produjo avisos de permisos de la caché de Matplotlib en el entorno restringido. Se repitió `--check` con `MPLCONFIGDIR` dentro del espacio de trabajo: completó correctamente. Los mensajes de TensorFlow Lite sobre feedback tensors son informativos y no impidieron la inferencia.

Los umbrales temporales son propuestas nuevas y requieren calibración. No se afirma que reproduzcan las duraciones implícitas de la versión v4 original. Antes de incorporar esta variante a la tesis debe actualizarse la descripción del software.
