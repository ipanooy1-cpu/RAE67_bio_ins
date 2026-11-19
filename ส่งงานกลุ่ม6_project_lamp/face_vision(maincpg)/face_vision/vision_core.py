"""Vision math from the user-supplied face_vision.zip; same heuristic scores."""
import math
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Canonical illustrative 3D facial points in millimeters for solvePnP.
# Nose tip, chin, left/right outer eyes, left/right mouth corners.
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -63.6, -12.5),
    (-43.3, 32.7, -26.0),
    (43.3, 32.7, -26.0),
    (-28.9, -28.9, -24.1),
    (28.9, -28.9, -24.1),
], dtype=np.float64)
LANDMARK_IDS = [1, 152, 33, 263, 61, 291]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def classify_expression(blendshapes):
    """Rule-based expression proxy; output scores are heuristic strengths."""
    if not blendshapes or any(not math.isfinite(float(cat.score)) or not 0 <= float(cat.score) <= 1 for cat in blendshapes):
        return 'unknown', 0.0
    b = {cat.category_name: float(cat.score) for cat in blendshapes}
    avg = lambda a, c: (b.get(a, 0.0) + b.get(c, 0.0)) / 2.0
    smile = avg('mouthSmileLeft', 'mouthSmileRight')
    frown = avg('mouthFrownLeft', 'mouthFrownRight')
    brow_down = avg('browDownLeft', 'browDownRight')
    brow_up = b.get('browInnerUp', 0.0)
    wide = avg('eyeWideLeft', 'eyeWideRight')
    jaw = b.get('jawOpen', 0.0)
    scores = {
        'happy': clamp(smile),
        'sad': clamp(0.55 * frown + 0.45 * brow_up),
        'angry': clamp(0.65 * brow_down + 0.35 * frown),
        'surprised': clamp(0.45 * jaw + 0.35 * wide + 0.20 * brow_up),
    }
    best = max(scores, key=scores.get)
    strength = scores[best]
    if strength < 0.35:
        return 'neutral', clamp(1.0 - strength)
    return best, strength


def head_pose(landmarks, width, height):
    image_points = np.array(
        [(landmarks[i].x * width, landmarks[i].y * height) for i in LANDMARK_IDS],
        dtype=np.float64,
    )
    # Approximate camera matrix; calibrate camera for improved accuracy.
    focal_length = float(width)
    camera_matrix = np.array([
        [focal_length, 0.0, width / 2.0],
        [0.0, focal_length, height / 2.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    distortion = np.zeros((4, 1), dtype=np.float64)
    ok, rotation_vector, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, distortion,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return None
    rot, _ = cv2.Rodrigues(rotation_vector)
    # OpenCV RQDecomp3x3 outputs approximate Euler angles in degrees (X,Y,Z).
    angles, *_ = cv2.RQDecomp3x3(rot)
    if not all(math.isfinite(float(v)) for v in angles):
        return None
    return tuple(float(v) for v in angles)


def face_position(landmarks):
    xs = np.array([p.x for p in landmarks], dtype=np.float32)
    ys = np.array([p.y for p in landmarks], dtype=np.float32)
    x0, x1 = clamp(np.min(xs)), clamp(np.max(xs))
    y0, y1 = clamp(np.min(ys)), clamp(np.max(ys))
    center_x = 0.5 * (x0 + x1)
    center_y = 0.5 * (y0 + y1)
    # x: right positive, y: up positive, z: relative face width.
    return (2.0 * center_x - 1.0, 1.0 - 2.0 * center_y, x1 - x0), (x0, y0, x1, y1)
