import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time
import winsound  # <-- Usamos winsound para alerta sonora

# --- Función para reproducir alerta sonora ---
def play_alert():
    winsound.PlaySound(r"alerta", winsound.SND_FILENAME | winsound.SND_ASYNC)

# --- Inicializar MediaPipe Face Mesh ---
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)
mp_drawing = mp.solutions.drawing_utils

# --- Landmarks de ojos y boca ---
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH_UPPER = [13, 312, 82, 81, 80, 191]
MOUTH_LOWER = [14, 317, 87, 178, 88, 95]

# --- Funciones ---
def euclid(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))

def eye_aspect_ratio(landmarks, idxs, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in idxs]
    p1,p2,p3,p4,p5,p6 = pts
    ear = (euclid(p2,p6) + euclid(p3,p5)) / (2.0 * euclid(p1,p4) + 1e-6)
    return ear, pts

def mouth_aspect_ratio(landmarks, upper_idxs, lower_idxs, w, h):
    upper = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in upper_idxs]
    lower = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in lower_idxs]
    vertical = sum([euclid(u, l) for u, l in zip(upper, lower)])/len(upper)
    left_corner = (int(landmarks[61].x*w), int(landmarks[61].y*h))
    right_corner = (int(landmarks[291].x*w), int(landmarks[291].y*h))
    horizontal = euclid(left_corner, right_corner)
    mar = vertical / (horizontal + 1e-6)
    return mar, upper + lower + [left_corner, right_corner]

# --- Variables ---
ear_history = deque(maxlen=60)
closed_threshold = 0.18
frames_closed_threshold = 10  # frames consecutivos para alerta
closed_counter = 0

blink_count = 0
last_blink_time = time.time()
blink_times = []

mar_history = deque(maxlen=10)
mar_threshold = 0.6
yawn_count = 0
last_yawn_time = time.time()
frames_yawn = 3

alert_cooldown = 5  # segundos entre alertas
last_alert_time = 0

# --- Captura de cámara ---
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)

    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark

        # Dibujar rostro
        mp_drawing.draw_landmarks(frame, res.multi_face_landmarks[0], mp_face.FACEMESH_TESSELATION,
                                  landmark_drawing_spec=None,
                                  connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0), thickness=1, circle_radius=1))

        # EAR
        left_ear, left_pts = eye_aspect_ratio(lm, LEFT_EYE, w, h)
        right_ear, right_pts = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
        ear = (left_ear + right_ear) / 2.0
        ear_history.append(ear)

        # MAR
        mar, mouth_pts = mouth_aspect_ratio(lm, MOUTH_UPPER, MOUTH_LOWER, w, h)
        mar_history.append(mar)

        # Dibujar puntos ojos y boca
        for pt in left_pts + right_pts:
            cv2.circle(frame, pt, 2, (0,0,255), -1)
        for pt in mouth_pts:
            cv2.circle(frame, pt, 2, (255,0,0), -1)

        # Parpadeos
        if len(ear_history) > 3:
            recent = list(ear_history)[-3:]
            if all(e < closed_threshold for e in recent):
                if time.time() - last_blink_time > 0.3:
                    blink_count += 1
                    last_blink_time = time.time()
                    blink_times.append(last_blink_time)

        # PERCLOS
        perclos = sum(e < closed_threshold for e in ear_history)/len(ear_history) * 100

        # Parpadeos por minuto
        current_time = time.time()
        blink_times = [t for t in blink_times if current_time - t <= 60]
        bpm = len(blink_times)

        # Bostezos
        if len(mar_history) >= frames_yawn:
            recent_mar = list(mar_history)[-frames_yawn:]
            if all(m > mar_threshold for m in recent_mar):
                if time.time() - last_yawn_time > 2.0:
                    yawn_count += 1
                    last_yawn_time = time.time()

        # --- Lógica de alerta ---
        if ear < closed_threshold:
            closed_counter += 1
        else:
            closed_counter = 0

        alert_condition = (closed_counter >= frames_closed_threshold) or (perclos > 50) or (mar > mar_threshold and yawn_count > 0)
        if alert_condition and (current_time - last_alert_time) > alert_cooldown:
            play_alert()
            last_alert_time = current_time

        # Mostrar información en pantalla
        cv2.putText(frame, f"EAR: {ear:.2f}", (30,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"PERCLOS: {perclos:.1f}%", (30,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Parpadeos totales: {blink_count}", (30,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Parpadeos/min: {bpm}", (30,120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Tiempo ultimo parpadeo: {int(current_time - last_blink_time)} s", (30,150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Bostezo detectados: {yawn_count}", (30,180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"MAR actual: {mar:.2f}", (30,210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0),2)
        cv2.putText(frame, f"Umbral MAR: {mar_threshold}", (30,240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0),2)
        if alert_condition:
            cv2.putText(frame, "ALERTA: Posible somnolencia!", (30,270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),2)

    cv2.imshow("Detector de Somnolencia", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
