import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time

# Inicializamos MediaPipe Face Mesh
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)
mp_drawing = mp.solutions.drawing_utils

# Landmarks de los ojos
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

def euclid(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))

def eye_aspect_ratio(landmarks, idxs, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in idxs]
    p1,p2,p3,p4,p5,p6 = pts
    ear = (euclid(p2,p6) + euclid(p3,p5)) / (2.0 * euclid(p1,p4) + 1e-6)
    return ear, pts

# Variables
ear_history = deque(maxlen=60)  # historial de EAR
CLOSED_THRESHOLD = 0.18
FRAMES_CLOSED = 3  # cantidad de frames para contar como parpadeo
blink_count = 0
last_blink_time = time.time()
blink_times = []

# Captura de cámara
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

        # Dibujar todos los landmarks del rostro
        mp_drawing.draw_landmarks(frame, res.multi_face_landmarks[0], mp_face.FACEMESH_TESSELATION,
                                  landmark_drawing_spec=None,
                                  connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0), thickness=1, circle_radius=1))

        # Calcular EAR
        left_ear, left_pts = eye_aspect_ratio(lm, LEFT_EYE, w, h)
        right_ear, right_pts = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
        ear = (left_ear + right_ear) / 2.0
        ear_history.append(ear)

        # Dibujar puntos de los ojos
        for pt in left_pts + right_pts:
            cv2.circle(frame, pt, 2, (0,0,255), -1)

        # Detectar parpadeo
        if len(ear_history) > FRAMES_CLOSED:
            recent = list(ear_history)[-FRAMES_CLOSED:]
            if all(e < CLOSED_THRESHOLD for e in recent):
                # Evitar contar múltiples frames del mismo parpadeo
                if time.time() - last_blink_time > 0.3:  # 300 ms de cooldown
                    blink_count += 1
                    last_blink_time = time.time()
                    blink_times.append(last_blink_time)

        # Calcular parpadeos por minuto
        current_time = time.time()
        # solo blinks últimos 60s
        blink_times = [t for t in blink_times if current_time - t <= 60]
        bpm = len(blink_times)

        # Mostrar info en pantalla
        cv2.putText(frame, f"EAR: {ear:.2f}", (30,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Parpadeos totales: {blink_count}", (30,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Parpadeos/min: {bpm}", (30,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
        cv2.putText(frame, f"Tiempo ultimo parpadeo: {int(current_time - last_blink_time)} s", (30,120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)

        # Alerta de somnolencia simple
        if ear < CLOSED_THRESHOLD and all(e < CLOSED_THRESHOLD for e in recent):
            cv2.putText(frame, "ALERTA: Posible somnolencia!", (30,150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),2)

    cv2.imshow("Detector de Somnolencia", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
