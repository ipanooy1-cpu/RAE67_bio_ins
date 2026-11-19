# กล้องตรวจสีหน้าเชื่อมฮอร์โมนและ CPG ของโคมไฟ

โค้ดที่รับต่อจากเพื่อนอยู่ใน `original/face_node.py` ฉบับที่เชื่อมแล้วใช้ตัวควบคุมเดียวกันสำหรับ Python ใน VS Code และ ROS 2 ตอนใช้งานจริง

```
Camera → MediaPipe blendshapes → expression heuristic
    → รอสีหน้าคงที่ → โหมดโคมไฟ
    → Hormone memory → SO(2) CPG → มุม J1–J4 และไฟ
```

## 1 ทดสอบด้วย Python บน VS Code

เปิดโฟลเดอร์นี้ใน VS Code แล้วเลือก Python interpreter ของ `.venv` ถ้ารับ ZIP ไปเครื่องอื่นให้สร้าง environment ใหม่ ไม่คัดลอก `.venv` ข้ามเครื่อง

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-camera.txt
.\.venv\Scripts\python.exe test_face_lamp.py
```

ไฟล์ `test_face_lamp.py` กด Run Python File ได้โดยไม่ต้องใส่ argument เมื่อเลือก interpreter ถูกต้อง จะเปิดกล้องหมายเลข 0 และหน้าต่าง preview พร้อมค่า H และ J1–J4 ใช้ `q` หรือ Ctrl+C เพื่อจบ บันทึกเฉพาะค่าตัวเลขใน `results/face_lamp_test.csv` และกราฟ `.png` ไม่บันทึกภาพใบหน้า ค่าเริ่มต้นให้ทดสอบได้นานสุด 600 วินาที

โมเดล `models/face_landmarker.task` ดาวน์โหลดจาก Google พร้อมที่มาและ SHA256 ใน `models/SOURCE.json` อยู่ในชุดนี้แล้ว

เลือกกล้องหมายเลขอื่น:

```powershell
.\.venv\Scripts\python.exe test_face_lamp.py --model-path models/face_landmarker.task --camera-index 1 --preview --duration 60 --plot
```

ถ้าไม่มี webcam ให้เล่นข้อมูลตัวอย่างก่อน:

```powershell
python test_face_lamp.py --replay examples/observations.jsonl
# ถ้ามี matplotlib เพิ่ม --plot เพื่อบันทึกกราฟ
python test_face_lamp.py --replay examples/observations.jsonl --plot
python -m unittest discover -s tests -v
```

Replay ใช้ standard library สำหรับ controller และ CSV; เฉพาะ `--plot` ต้องมี matplotlib ตัวอย่างนี้เป็นข้อมูลสังเคราะห์ 45 วินาที ไม่ใช่ผลตรวจใบหน้าหรือหุ่นยนต์จริง

## 2 จับคู่สีหน้าตามที่ตกลง

| ผลจากกล้อง | โหมดโคมไฟ | ฮอร์โมนเป้าหมาย |
|---|---|---|
| happy | Happy | H_happy → 1 |
| sad | Sad | H_sad → 1 |
| surprised | Confused | H_curious → 1 |
| angry | Confused | H_curious → 1 |
| neutral | Neutral | ทั้งสาม → 0 |
| unknown / ไม่พบหน้า / หมดเวลา | Neutral | ทั้งสามค่อย ๆ ลด |

`strength` เป็นคะแนน heuristic ของสีหน้า ไม่ใช่ความน่าจะเป็นของอารมณ์ทางจิตใจ ใช้เป็นเกณฑ์รับสัญญาณ ≥0.35; ไม่ได้นำคะแนนไปแทนมุมเซอร์โวโดยตรง ต้องมีอย่างน้อย 3 เฟรมและโหมดเดียวกันคงที่อย่างน้อย 0.30 วินาทีจึงยอมรับ การกระพริบสั้น ๆ ไม่เริ่มลำดับ Sad ใหม่ เมื่อข้อมูลขาดเกิน 0.50 วินาทีหรือไม่พบหน้า ให้เป้าหมายฮอร์โมนเป็น Neutral

คะแนนผ่านเกณฑ์แล้ว target ของฮอร์โมนโหมดนั้นเป็น 1; ตัวอื่นเป็น 0 ค่าจริง H ยังสะสม/สลายตาม tau ไม่ใช่เปลี่ยนเป็น 1 ทันที ถ้าสีหน้าสลับระหว่าง angry กับ surprised แต่ทั้งคู่ map เป็น Confused จะไม่รีเซ็ตเวลา Confused

## 3 สมการและสถานะที่เก็บต่อเนื่อง

ใช้ snapshot ของ `../../cpg_for_lamp.py` ใน `face_vision/lamp_model.py`; SHA ใน `MODEL_PROVENANCE.json` ถ้าแก้ preset ในไฟล์หลักภายหลังต้องอัปเดต snapshot อย่างตั้งใจแล้วทดสอบใหม่

`H_next = clamp(H_old + dt × (target − H_old) / tau, 0, 1)`

| H | tau เพิ่ม | tau ลด |
|---|---:|---:|
| Happy | 0.5 s | 1.5 s |
| Sad | 2.0 s | 3.0 s |
| Curious | 0.4 s | 1.0 s |

dt=0.05 s, alpha=1.10; H ปรับ gain, phi, มุมกลาง, สี และความสว่างตาม preset เดิม คำนวณ CPG ทั้งสองตัวจาก output เก่าชุดเดียวกัน เก็บ H/o1/o2 ตลอดการรัน ไม่เรียก simulate() และไม่ warmup ใหม่ทุกเฟรม ตัวจับกล้องใน standalone อยู่คนละ thread กับตัวควบคุม 20Hz เพื่อให้ timeout ทำงานแม้ inference ช้า

Sad ที่ยอมรับต่อเนื่องครบ 10 วินาที: J4 เป้าหมายถึง 60° และลดการแกว่งหัวเป็นศูนย์ เส้นทางเริ่มจากมุมปัจจุบัน ใช้สัดส่วนการก้มของ keyframes เดิม จึงไม่กระโดดไปเริ่มที่ 105° ถ้าเพิ่งก้มจากท่ากลาง 90° ส่วน H_sad ยังค่อย ๆ สะสมตามสมการ ถ้าเปลี่ยนโหมดก่อนครบ 10 วินาที จะออกจากลำดับ Sad และเก็บฮอร์โมนที่เหลือให้ค่อย ๆ ลด

มุมคำสั่งถูกจำกัด 60–120° และ slew ≤20°/s เป็นค่าทดลองสำหรับ simulation เท่านั้น ระดับ hardware ยังต้องสอบเทียบ neutral/ทิศหมุน/ข้อจำกัดเชิงกล/ความเร็ว คำว่า 60° หมายถึงมุมคำสั่ง ไม่ใช่ encoder ยืนยันตำแหน่งจริง ไฟส่ง RGB ที่ปรับ brightness แล้ว alpha=1

หาก controller ไม่ได้ถูกเรียกนานจนต้องตามเวลาเกิน 5 ticks จะ hold คำสั่งเดิมและตั้ง `scheduler_fault` ไม่เร่งเล่นคำสั่งที่พลาดทั้งหมดในครั้งเดียว จากนั้นค่อยฟื้นไป Neutral การ hold/Neutral นี้ไม่แทน driver watchdog หรือ E-stop

## 4 ใช้งานจริงด้วย ROS 2

เป้าหมายคือ Ubuntu 24.04 + ROS 2 Jazzy ตามโค้ดเดิม คัดลอกโฟลเดอร์นี้เป็น `~/ros2_ws/src/face_vision` แล้วเปิด terminal:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r src/face_vision/requirements-camera.txt
python -m colcon build --symlink-install --packages-select face_vision
source install/setup.bash
```

Terminal 1 เริ่ม controller (source ROS/venv/install ในทุก terminal):

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/.venv/bin/activate
source ~/ros2_ws/install/setup.bash
ros2 run face_vision lamp_node
```

Terminal 2 เริ่มกล้อง:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/.venv/bin/activate
source ~/ros2_ws/install/setup.bash
ros2 run face_vision face_node --ros-args \
  -p model_path:=$HOME/ros2_ws/src/face_vision/models/face_landmarker.task \
  -p show_preview:=true
```

Terminal 3 ตรวจผล:

```bash
ros2 topic echo /lamp/command
ros2 topic echo /lamp/joint_commands_deg
ros2 topic echo /lamp/hormones
```

หากระบบ Jazzy ใช้ Python 3.12 ให้สร้าง venv ด้วย Python 3.12 ของระบบนั้น ไม่ใช้ venv Windows/Python 3.13 ไปแทน interpreter ที่ build rclpy

### Topics ที่เชื่อม

| Topic | Type | ความหมาย |
|---|---|---|
| /face/observation | std_msgs/String | JSON atomic: schema, stream_id, seq, stamp_ns, detected, emotion, strength |
| /face/emotion และ topics เดิมอื่น ๆ | types เดิม | เก็บไว้เพื่อผู้ใช้เดิม แต่ controller ใหม่ไม่จับคู่หลาย topic แบบเดาเฟรม |
| /lamp/command | std_msgs/String | JSON debug/output รวม H, phi, q_deg, light, status |
| /lamp/joint_commands_deg | std_msgs/Float64MultiArray | [J1,J2,J3,J4] หน่วยองศาคำสั่งเซอร์โว |
| /lamp/hormones | std_msgs/Float32MultiArray | [H_happy,H_sad,H_curious] ช่วง 0–1 |
| /lamp/emotion | std_msgs/String | Neutral / Happy / Sad / Confused |
| /lamp/rgb_command | std_msgs/ColorRGBA | RGB normalized × brightness; alpha=1 |

Joint topic เป็น 4 แกนหน่วย degree ชัดเจน ไม่ใช่ `/lamp/servo_command` แบบ 3 แกน rad ของ Lab07 ต้องเพิ่ม driver adapter ที่รู้ mapping และขีดจำกัดจริงก่อนต่อ SCS15 ไม่มีคำสั่ง Serial/TTL หรือ motor enable ในชุดนี้

ใช้ ROS queue depth10 ตาม node เดิม ข้อความ atomic ป้องกัน emotion จากเฟรมหนึ่งจับคู่กับ confidence อีกเฟรม ข้าม duplicate/out-of-order seq และเริ่ม debounce ใหม่เมื่อ stream เปลี่ยน `stamp_ns` วัดก่อนอ่านกล้องโดย ROS clock ไม่ใช่เวลาสัมผัสแสงจริง ต้องใช้ clock/ROS time ที่สอดคล้องกันทั้งสอง node จะปฏิเสธ source age >0.50s หรืออนาคตเกิน0.10s; receipt timeout ใช้ monotonic ภายใน process แยกจาก ROS clock

`head_pose` และ `position` ยังคง publish จากกล้องเดิม แต่ยังไม่นำมาสั่ง J1–J4 เพราะต้องตรวจทิศ/หน่วยและสอบเทียบ camera geometry ก่อน งานนี้เชื่อมเฉพาะ expression→hormone→CPG

## 5 ขอบเขตการตรวจ

ผลตรวจจริงอยู่ `VERIFICATION.json` ทดสอบ Python core, expression mapping, debounce, stale/duplicate/restart, hormone decay, scheduler และ bounds/slew พร้อม replay 901 samples นอกจากนี้โหลดโมเดล MediaPipe และรัน inference กับภาพเปล่าผ่านแล้ว ใช้ proposed settings เดิม ยังไม่เปิด webcam และยังไม่มีผล ROS/servo จริง Python dependencies ที่ทดสอบบน Windows อยู่ใน `requirements-windows-tested.txt`; Linux/ROS ใช้ `requirements-camera.txt` และตรวจ environment ของเครื่องจริงอีกครั้ง

แหล่งอ้างอิง API และ model:

- MediaPipe Face Landmarker: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python
- Model artifact: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
- ROS rclpy: https://docs.ros.org/en/jazzy/p/rclpy/api/node.html

ค่า heuristic ต้นทางมาจาก face_vision.zip ของเพื่อน; mapping angry/surprised→Confused เป็นข้อกำหนดของโปรเจกต์นี้ ไม่ใช่ข้อสรุปว่าผู้ใช้ที่โกรธกำลังสงสัย
