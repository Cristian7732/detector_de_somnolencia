"""Adaptación de flicker_detector_v4.py, commit 055f888878471ded7b731611c08c344301ea7091.

Python 3.11/3.12 de 64 bits; cámara USB. Parámetros experimentales, no clínicos.
"""
import argparse
from collections import deque
from dataclasses import dataclass
import math
import sys
import time

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH_UPPER = [13, 312, 82, 81, 80, 191]
MOUTH_LOWER = [14, 317, 87, 178, 88, 95]


def ratios(landmarks, width, height):
    # Coordenadas flotantes: evitar el redondeo a píxeles antes del cociente.
    pts = [(p.x * width, p.y * height) for p in landmarks]
    if len(pts) <= max(LEFT_EYE + RIGHT_EYE + MOUTH_UPPER + MOUTH_LOWER + [291]):
        return None
    selected = set(LEFT_EYE + RIGHT_EYE + MOUTH_UPPER + MOUTH_LOWER + [61, 291])
    if not all(math.isfinite(v) for i in selected for v in pts[i]):
        return None
    eyes = []
    for indices in (LEFT_EYE, RIGHT_EYE):
        p1, p2, p3, p4, p5, p6 = (pts[i] for i in indices)
        horizontal = math.dist(p1, p4)
        if horizontal <= 1e-6:
            return None
        eyes.append((math.dist(p2, p6) + math.dist(p3, p5)) / (2 * horizontal))
    mouth_width = math.dist(pts[61], pts[291])
    if mouth_width <= 1e-6:
        return None
    mar = sum(math.dist(pts[u], pts[l]) for u, l in zip(MOUTH_UPPER, MOUTH_LOWER)) / (6 * mouth_width)
    return sum(eyes) / 2, mar


@dataclass
class Settings:
    ear: float = 0.18
    mar: float = 0.6
    closed_seconds: float = 1.0
    mouth_seconds: float = 2.0
    window_seconds: float = 60.0
    closure_percent: float = 50.0
    max_gap: float = 0.5
    cooldown: float = 5.0


class DetectorState:
    """Reglas temporales separadas de cámara y sonido para poder probarlas."""

    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.history = deque()
        self.eye_start = self.mouth_start = self.last_time = None
        self.blinks = self.mouth_events = 0

    def update(self, now, ear, mar):
        cfg = self.settings
        valid = ear is not None and mar is not None and math.isfinite(ear) and math.isfinite(mar)
        gap = self.last_time is not None and not 0 < now - self.last_time <= cfg.max_gap
        if not valid or gap:
            # No prolongar un cierre a través de un intervalo sin observaciones.
            self.history.clear()
            self.eye_start = self.mouth_start = None
        self.last_time = now
        if not valid:
            return {'valid': False, 'alert': False, 'reason': 'SIN DATOS', 'closure': None, 'observed': 0.0}

        closed, mouth_open = ear < cfg.ear, mar > cfg.mar
        if closed:
            if self.eye_start is None:
                self.eye_start = now
        elif self.eye_start is not None:
            duration = now - self.eye_start
            # Candidatos breves: un cierre largo no cuenta como varios parpadeos.
            if 0.06 <= duration <= 0.8:
                self.blinks += 1
            self.eye_start = None
        if mouth_open:
            if self.mouth_start is None:
                self.mouth_start = now
        elif self.mouth_start is not None:
            if now - self.mouth_start >= cfg.mouth_seconds:
                self.mouth_events += 1
            self.mouth_start = None

        self.history.append((now, closed))
        cutoff = now - cfg.window_seconds
        while len(self.history) > 1 and self.history[1][0] <= cutoff:
            self.history.popleft()
        observed = now - max(cutoff, self.history[0][0])
        closed_time = sum(
            max(0.0, end[0] - max(start[0], cutoff))
            for start, end in zip(self.history, list(self.history)[1:]) if start[1]
        )
        # Aproximación temporal por EAR; incluye parpadeos, no PERCLOS validado.
        closure = 100 * closed_time / observed if observed >= cfg.window_seconds - 1e-6 else None
        reasons = []
        if self.eye_start is not None and now - self.eye_start >= cfg.closed_seconds:
            reasons.append('CIERRE OCULAR')
        if self.mouth_start is not None and now - self.mouth_start >= cfg.mouth_seconds:
            reasons.append('APERTURA BUCAL')
        if closure is not None and closure > cfg.closure_percent:
            reasons.append('CIERRE ACUMULADO')
        return {'valid': True, 'alert': bool(reasons), 'reason': ' + '.join(reasons) or 'OBSERVANDO',
                'closure': closure, 'observed': observed}


class Alarm:
    """PortAudio ya es dependencia de MediaPipe; funciona en Windows y Linux."""

    def __init__(self):
        import numpy as np
        import sounddevice as sd
        self.sd = sd
        self.rate = int(sd.query_devices(kind='output')['default_samplerate'])
        sd.check_output_settings(channels=1, samplerate=self.rate, dtype='float32')
        t = np.arange(int(self.rate * 0.6)) / self.rate
        # Tono local; evita depender del alerta.mp3 vacío del repositorio.
        self.tone = (0.2 * np.sin(2 * np.pi * 880 * t) * np.sin(np.pi * t / 0.6)**2).astype('float32')

    def play(self, wait=False):
        self.sd.play(self.tone, self.rate, blocking=wait)

    def close(self):
        self.sd.stop()


def arguments(argv=None):
    parser = argparse.ArgumentParser(description='Detector facial para PC y Raspberry Pi de 64 bits')
    parser.add_argument('--camera', type=int, default=0, help='Índice de cámara USB')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--no-display', action='store_true', help='Sin ventana; detener con Ctrl+C')
    parser.add_argument('--mute', action='store_true', help='Prueba sin salida sonora')
    parser.add_argument('--test-audio', action='store_true', help='Emitir un tono y salir; sin cámara')
    parser.add_argument('--check', action='store_true', help='Probar imports e inferencia con imagen vacía; sin cámara ni sonido')
    for name, default in vars(Settings()).items():
        parser.add_argument('--' + name.replace('_', '-'), type=float, default=default)
    args = parser.parse_args(argv)
    for name in vars(Settings()):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            parser.error(f'{name} debe ser un número finito mayor que cero')
    if args.closure_percent > 100 or args.width <= 0 or args.height <= 0 or args.camera < 0:
        parser.error('Porcentaje máximo 100; resolución positiva; cámara no negativa')
    return args


def main(argv=None):
    args = arguments(argv)
    if args.test_audio:
        alarm = Alarm()
        try:
            alarm.play(wait=True)
            print('Tono enviado. Confirma que se escucha en el parlante seleccionado.')
        finally:
            alarm.close()
        return

    import cv2
    import mediapipe as mp
    import numpy as np
    if not hasattr(mp, 'solutions'):
        raise RuntimeError('Esta variante usa Face Mesh legacy. Instala requirements.txt en un entorno nuevo.')
    print(f'Python {sys.version.split()[0]} | MediaPipe {mp.__version__} | OpenCV {cv2.__version__} | NumPy {np.__version__}')
    cap = alarm = None
    try:
        with mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True) as mesh:
            if args.check:
                result = mesh.process(np.zeros((480, 640, 3), dtype=np.uint8))
                if result.multi_face_landmarks:
                    raise RuntimeError('La imagen vacía produjo una detección inesperada')
                print('OK: Face Mesh ejecutó inferencia CPU. No comprueba cámara, rostro real ni audio.')
                return
            alarm = None if args.mute else Alarm()
            cap = cv2.VideoCapture(args.camera)
            if not cap.isOpened():
                raise RuntimeError(f'No se pudo abrir la cámara {args.camera}; prueba --camera 1')
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Puede ser ignorado por el controlador.
            state = DetectorState(Settings(**{name: getattr(args, name) for name in vars(Settings())}))
            last_sound = last_print = float('-inf')
            started, frames = time.monotonic(), 0
            while True:
                ok, frame = cap.read()
                captured = time.monotonic()
                if not ok:
                    raise RuntimeError('Se perdió la captura de cámara; el programa se detuvo')
                result = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                values = None
                if result.multi_face_landmarks:
                    h, w = frame.shape[:2]
                    values = ratios(result.multi_face_landmarks[0].landmark, w, h)
                ear, mar = values if values is not None else (None, None)
                status = state.update(captured, ear, mar)
                now = time.monotonic()
                frames += 1
                if status['alert'] and now - last_sound >= args.cooldown:
                    if alarm:
                        alarm.play()
                    last_sound = now
                fps = frames / max(now - started, 1e-6)
                closure = status['closure']
                progress = f"espera {status['observed']:.1f}/{args.window_seconds:g}s"
                lines = [status['reason'],
                         f'EAR {ear:.3f} | MAR {mar:.3f}' if values else 'Rostro no disponible',
                         f'Cierre temporal: {closure:.1f}%' if closure is not None else f'Cierre temporal: {progress}',
                         f'Parpadeos candidatos: {state.blinks}', f'Aperturas largas completas: {state.mouth_events}',
                         f'FPS medios: {fps:.1f} | proceso: {(now-captured)*1000:.0f} ms',
                         'SIN SONIDO' if args.mute else 'Audio habilitado | q para salir']
                if now - last_print >= 1:
                    print(' | '.join(lines), flush=True)
                    last_print = now
                if not args.no_display:
                    color = (0, 0, 255) if status['alert'] else (0, 220, 255)
                    for i, line in enumerate(lines):
                        cv2.putText(frame, line, (10, 25 + i * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                    cv2.imshow('Detector de somnolencia experimental', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
    finally:
        if cap is not None:
            cap.release()
        if alarm is not None:
            alarm.close()
        if not args.no_display:
            cv2.destroyAllWindows()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nDetector detenido.')
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        print('Consulta README.md. Usa --check para software y --test-audio para el parlante.', file=sys.stderr)
        sys.exit(1)
