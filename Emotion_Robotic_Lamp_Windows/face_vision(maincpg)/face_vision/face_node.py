#!/usr/bin/env python3
"""ROS 2 Jazzy USB webcam -> facial-expression / head-pose / face-position topics.

Emotion is a lightweight blendshape heuristic, NOT a calibrated emotion model.
Pose is approximate (camera intrinsics are estimated without calibration).
"""
import math
import time
import json
import uuid
import sys

import cv2
import mediapipe as mp
import numpy as np
import rclpy
from geometry_msgs.msg import Vector3
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


from .vision_core import classify_expression, head_pose, face_position, clamp


class FaceVisionNode(Node):
    def __init__(self):
        super().__init__('face_vision_node')
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('model_path', '')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('show_preview', True)
        self.declare_parameter('smoothing_alpha', 0.35)
        camera_index = int(self.get_parameter('camera_index').value)
        model_path = str(self.get_parameter('model_path').value)
        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)
        fps = float(self.get_parameter('fps').value)
        self.show_preview = bool(self.get_parameter('show_preview').value)
        self.alpha = clamp(self.get_parameter('smoothing_alpha').value)
        if not model_path:
            raise ValueError('Please set -p model_path:=/absolute/path/face_landmarker.task')
        if fps <= 0:
            raise ValueError('fps must be positive')

        self.observation_seq = 0
        self.stream_id = uuid.uuid4().hex
        self.pub_observation = self.create_publisher(String, '/face/observation', 10)
        self.pub_emotion = self.create_publisher(String, '/face/emotion', 10)
        self.pub_conf = self.create_publisher(Float32, '/face/emotion_confidence', 10)
        self.pub_pose = self.create_publisher(Vector3, '/face/head_pose', 10)
        self.pub_pos = self.create_publisher(Vector3, '/face/position', 10)
        self.pub_detected = self.create_publisher(Bool, '/face/detected', 10)

        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.FaceLandmarker.create_from_options(opts)
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2 if sys.platform.startswith('linux') else cv2.CAP_ANY)
        if not self.cap.isOpened():
            self.detector.close()
            raise RuntimeError(f'Cannot open USB camera index {camera_index}')
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.previous_pose = None
        self.previous_position = None
        self.last_timestamp_ms = -1
        self.start_monotonic = time.monotonic()
        self.timer = self.create_timer(1.0 / fps, self.tick)
        self.get_logger().info(f'Face Vision started camera={camera_index}, fps={fps}')

    def smooth(self, current, previous):
        now = np.array(current, dtype=float)
        if previous is None:
            return now
        return self.alpha * now + (1.0 - self.alpha) * previous

    def tick(self):
        self.capture_stamp_ns = self.get_clock().now().nanoseconds
        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('Camera read failed')
            self.publish_not_detected()
            return
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        timestamp_ms = int((time.monotonic() - self.start_monotonic) * 1000)
        timestamp_ms = max(timestamp_ms, self.last_timestamp_ms + 1)
        self.last_timestamp_ms = timestamp_ms
        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        if not result.face_landmarks:
            self.publish_not_detected()
            self.previous_pose = None
            self.previous_position = None
            if self.show_preview:
                cv2.putText(frame, 'NO FACE', (12, 35), cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, (0, 0, 255), 2)
        else:
            landmarks = result.face_landmarks[0]
            blends = result.face_blendshapes[0] if result.face_blendshapes else []
            emotion, confidence = classify_expression(blends)
            position, bbox = face_position(landmarks)
            pose = head_pose(landmarks, width, height)

            self.publish_observation(True, emotion, confidence)
            self.pub_detected.publish(Bool(data=True))
            self.pub_emotion.publish(String(data=emotion))
            self.pub_conf.publish(Float32(data=float(confidence)))
            self.previous_position = self.smooth(position, self.previous_position)
            self.pub_pos.publish(Vector3(
                x=float(self.previous_position[0]),
                y=float(self.previous_position[1]),
                z=float(self.previous_position[2]),
            ))
            if pose is not None:
                self.previous_pose = self.smooth(pose, self.previous_pose)
                self.pub_pose.publish(Vector3(
                    x=float(self.previous_pose[0]),
                    y=float(self.previous_pose[1]),
                    z=float(self.previous_pose[2]),
                ))

            if self.show_preview:
                x0, y0, x1, y1 = bbox
                cv2.rectangle(frame, (int(x0 * width), int(y0 * height)),
                              (int(x1 * width), int(y1 * height)), (0, 255, 0), 2)
                cv2.putText(frame, f'{emotion} ({confidence:.2f})', (12, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame,
                            f'pos: {self.previous_position[0]:+.2f}, {self.previous_position[1]:+.2f}, {self.previous_position[2]:.2f}',
                            (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                if self.previous_pose is not None:
                    cv2.putText(frame,
                                f'pitch/yaw/roll: {self.previous_pose[0]:+.1f}, {self.previous_pose[1]:+.1f}, {self.previous_pose[2]:+.1f}',
                                (12, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if self.show_preview:
            cv2.imshow('ROS2 Face Vision (q to quit)', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                rclpy.shutdown()

    def publish_observation(self, detected, emotion, strength):
        # One atomic message avoids mixing confidence and emotion from different frames.
        payload = {"schema": 1, "stream_id": self.stream_id, "seq": self.observation_seq,
                   "stamp_ns": self.capture_stamp_ns,
                   "detected": detected, "emotion": emotion, "strength": strength}
        self.observation_seq += 1
        self.pub_observation.publish(String(data=json.dumps(payload, allow_nan=False)))

    def publish_not_detected(self):
        self.publish_observation(False, 'unknown', 0.0)
        self.pub_detected.publish(Bool(data=False))
        self.pub_emotion.publish(String(data='unknown'))
        self.pub_conf.publish(Float32(data=0.0))
        # Do not publish fake zero pose/position when tracking is lost.

    def destroy_node(self):
        self.cap.release()
        self.detector.close()
        if self.show_preview:
            cv2.destroyAllWindows()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = FaceVisionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
