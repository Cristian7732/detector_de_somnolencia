# Continuar desde Fedora

Guía para Fedora Workstation de 64 bits. Esta instalación todavía debe verificarse en la PC de destino. Si usas Silverblue/Kinoite, estos comandos de dnf no corresponden al sistema anfitrión: prepara un entorno de desarrollo adecuado antes de continuar.

## Primera instalación

En una terminal de Fedora:

```bash
sudo dnf install git python3.12 portaudio mesa-libGL glib2
git clone https://github.com/Cristian7732/detector_de_somnolencia.git
cd detector_de_somnolencia/prototipo_portable
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip check
python -m unittest -v test_detector
python detector.py --check
python detector.py --test-audio
python detector.py
```

Usamos Python 3.12 de forma explícita por compatibilidad con MediaPipe Face Mesh. Conserva el Python predeterminado de Fedora. No copies el entorno .venv de Windows. Si el repositorio ya está clonado, usa su carpeta existente en lugar de volver a clonarlo.

La prueba de cámara se realiza desde el escritorio, con webcam y salida de audio disponibles. Salir con q o Ctrl+C. Consulta README.md para parámetros y diagnóstico.

## Al volver al proyecto

Desde la carpeta detector_de_somnolencia:

```bash
git status
git pull --ff-only
cd prototipo_portable
source .venv/bin/activate
python detector.py
```

Si hay modificaciones locales, revísalas y guárdalas antes de actualizar. Para compartir cambios entre computadoras debes crear un commit y enviarlo a GitHub; guardar un archivo solo lo guarda en esa PC. Para enviar cambios, configura tu autenticación de GitHub. No subas contraseñas, entornos virtuales ni documentos personales al repositorio público.

## Tesis y contexto

El Word y PDF de la tesis se transfieren por separado de forma privada. La copia completa incluye CONTEXTO_TESIS.md para retomar el trabajo en otro chat. Leer ese archivo al iniciar una nueva sesión y actualizarlo después de cambios importantes.

La tesis revisada del 4 de octubre describe v4. La adaptación portable cambia sonido y reglas temporales: falta actualizar esos apartados si se adopta esta variante como implementación final. No hay resultados experimentales ni validación clínica.

## Fuentes

- Python 3.12 en Fedora: https://packages.fedoraproject.org/pkgs/python3.12/python3.12/
- PortAudio en Fedora: https://packages.fedoraproject.org/pkgs/portaudio/portaudio/
- OpenGL en Fedora: https://packages.fedoraproject.org/pkgs/mesa/mesa-libGL/
