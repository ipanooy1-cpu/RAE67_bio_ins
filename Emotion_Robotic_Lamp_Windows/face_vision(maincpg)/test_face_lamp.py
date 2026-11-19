"""Open in VS Code and Run Python File to test the camera without ROS.

Stop the preview with q. Reuse the same controller on ROS with lamp_node.
Offline check: python test_face_lamp.py --replay examples/observations.jsonl --plot
"""
from pathlib import Path
import sys
from face_vision.live_lamp import main


if __name__ == '__main__':
    base = Path(__file__).resolve().parent
    if len(sys.argv) == 1:
        sys.argv += ['--model-path', str(base / 'models/face_landmarker.task'),
                     '--preview', '--duration', '600', '--plot']
    if '--output' not in sys.argv:
        sys.argv += ['--output', str(base / 'results/face_lamp_test.csv')]
    main()
