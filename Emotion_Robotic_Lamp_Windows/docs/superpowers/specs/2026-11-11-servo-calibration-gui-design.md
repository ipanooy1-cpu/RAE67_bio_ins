# Servo Calibration GUI Design

Date: 2026-11-11

## Intent

สร้าง GUI บน Windows สำหรับทดสอบหุ่นโคมไฟ Feetech SCS15 จำนวน 4 ตัวโดยตรงผ่าน COM8 ก่อนเชื่อม ROS 2 ผู้ใช้ต้องสามารถสั่งท่า Home/Center, jog ทีละ ID ด้วยปุ่ม +/-, สังเกตและบันทึกทิศทางทางกายภาพ โดยทุกการเคลื่อนที่ต้องช้าและถูกจำกัดด้วยค่าที่คาลิเบรตไว้

## Goals

- ใช้ Python 3.12, Tkinter และ Feetech Python SDK ทางการ (`scservo_sdk.scscl`)
- เชื่อมต่อพอร์ตและตรวจพบ ID 0, 1, 2, 3 ก่อนอนุญาตให้ขยับ
- แสดง Present Position และสถานะการเชื่อมต่อของแต่ละ ID
- มีปุ่ม Home, Center, jog `-`/`+`, อ่านค่าปัจจุบัน และ Torque Off
- ใช้ความเร็วต่ำ ค่าเริ่มต้น `50 raw` และไม่ส่ง speed `0`
- บันทึกผลทิศทางและ log การทดสอบลงไฟล์ที่อ่านต่อได้
- มี mock mode เพื่อทดสอบ GUI โดยไม่ต่อหุ่น

## Non-goals

- ยังไม่เชื่อม ROS 2, CPG หรือ RViz
- ไม่แก้ EEPROM, ID, baud rate, PID หรือ min/max ของ Servo
- ไม่ทำ inverse kinematics หรือ collision planning
- ไม่รับรองว่าเส้นทางระหว่างทุกท่าปลอดการชน เพราะโปรเจกต์ยังไม่มี collision model
- ไม่ขยับ Servo อัตโนมัติเมื่อเปิดโปรแกรมหรือทันทีหลัง Connect

## Constraints and Known Calibration

| ID | Joint | Safe min | Safe max | Center | Home |
|---:|---|---:|---:|---:|---:|
| 0 | ฐาน | 0 | 870 | 410 | 404 |
| 1 | ไหล่ | 120 | 940 | 566 | 271 |
| 2 | ศอก | 165 | 1023 | 593 | 946 |
| 3 | หัว | 0 | 720 | 176 | 0 |

- Bus: TTL half-duplex ผ่าน CH343, Windows default `COM8`, `1000000` baud
- ต้องปิด Feetech FD ก่อน Connect เพราะ COM8 เปิดพร้อมกันไม่ได้
- Home ของ ID3 อยู่ที่ min พอดี และ Home ของ ID2 ห่าง max 77 counts; GUI ต้องแสดงคำเตือนนี้
- ปุ่มทุกปุ่มต้อง clamp target ให้อยู่ใน safe min/max

## Approaches Considered

### 1. Tkinter + official Feetech Python SDK — selected

เหมาะกับการทดสอบบน Windows ตอนนี้ ใช้ API `WritePos`, `ReadPosSpeed`, `ReadMoving`, `ping` และ register torque ของ SCSCL โดยไม่ผูกกับ Docker/ROS มี dependency เพิ่มหนึ่งรายการ แต่ลดความเสี่ยงจากการประกอบ packet เอง

### 2. Tkinter + raw pyserial packets

ลด dependency แต่ต้องสร้างและตรวจ checksum, timeout และ protocol เอง เสี่ยงกับฮาร์ดแวร์มากกว่าและขัดกับข้อมูลโครงการที่ให้ใช้ SDK ทางการหากทำได้ จึงไม่เลือก

### 3. ROS 2 node and GUI

เหมาะกับระยะรวมระบบ แต่เพิ่มความซับซ้อนเรื่อง Docker, USB passthrough และ lifecycle ก่อนข้อมูล calibration ครบ จึงเลื่อนไป Phase D

## UI and Interaction

หน้าต่างเดียว แบ่งเป็นส่วนต่อไปนี้:

1. Connection
   - ช่อง Port (default COM8), Baud (default 1000000)
   - Connect/Disconnect
   - สถานะของ ID 0-3 และข้อความเตือนให้ปิด FD
2. Safety
   - ปุ่ม `ENABLE MOTION` ต้องกดหลัง Connect จึงเปิดปุ่มขยับ
   - ปุ่มแดง `TORQUE OFF ALL` ใช้ได้ทันทีเมื่อเชื่อมต่อ
   - ปิดหน้าต่างแล้วพยายาม Torque Off และปิดพอร์ตเสมอ
3. Pose
   - `GO HOME` ส่งเป้าหมาย 404, 271, 946, 0
   - `GO CENTER` ส่งเป้าหมาย 410, 566, 593, 176
   - แสดงกล่องยืนยันก่อนสั่งท่าหลายแกน
   - ใช้ sync write หาก SDK รองรับและตรวจพบครบทุก ID; ถ้าเตรียม packet ไม่ครบ ห้ามส่ง
4. Single-joint jog
   - เลือก ID ได้ครั้งละหนึ่งตัว
   - ปุ่ม `-` และ `+` อ่าน Present Position ใหม่แล้วบวก/ลบ Step
   - Step เลือกได้ 1, 5, 10, 20; default 10; ห้ามเกิน 20
   - Speed เลือกได้ 20, 50, 100; default 50; ห้ามเป็น 0 หรือเกิน 100 ในเครื่องมือนี้
   - หลังคำสั่งให้อ่าน feedback ซ้ำและแสดง target/present/error
5. Direction observation
   - ID0: ซ้าย / ขวา
   - ID1: ยกขึ้น / ลดลง
   - ID2: งอเข้า / กางออก
   - ID3: ก้มลง / เงยขึ้น
   - ผู้ใช้ระบุว่าผลที่เห็นเกิดหลัง jog `+` หรือ `-`; GUI เก็บ `raw_increase_motion` และ `raw_decrease_motion`
   - บันทึกผลลง `calibration_results.json`; ยังไม่เขียน EEPROM
6. Log
   - แสดงเวลา, operation, ID, before, target, present, speed, communication result
   - บันทึกเพิ่มใน `servo_test_log.csv`

## Motion and Safety Rules

- Connect ทำเพียงเปิดพอร์ต, set baud, ping และ read-only; ไม่เปิด torque และไม่ส่ง position
- Connect อ่าน torque register ด้วย ถ้าพบว่า Servo ใดเปิด torque มาจากโปรแกรมอื่น ให้แสดงคำเตือนและบังคับกด Torque Off ก่อน Enable Motion
- Motion controls เปิดได้เมื่อ ID 0-3 ping ผ่านครบและผู้ใช้กด Enable Motion
- Enable Motion ต้องอ่าน Present Position ใหม่ทุก ID, ตรวจว่าอยู่ใน safe range, sync-write Goal เท่ากับ Present Position ก่อน แล้วจึงเปิด torque ทีละ ID; ถ้าขั้นใดล้มเหลวให้ Torque Off ทุก ID
- ถ้า Present Position อยู่นอก safe range ให้เข้า fault และห้ามขยับ ห้ามสั่ง recovery/clamp อัตโนมัติ
- ทุก target ผ่าน pure validation function: ID ต้องรู้จัก, speed 1-100, step 1-20 และ target อยู่ใน safe limits
- Jog คำนวณจาก Present Position ล่าสุด ไม่ใช้ค่าหน้าจอเก่า
- Home/Center ใช้ speed 50 กับทุก ID และต้องได้รับการยืนยันจากผู้ใช้
- Home/Center ต้องใช้ `SyncWritePos` เตรียมครบทั้ง 4 ID แล้วเรียก `groupSyncWrite.txPacket()`; ถ้า SDK/API ใช้ไม่ได้หรือเพิ่ม parameter ไม่ครบ ให้ปิดปุ่มท่าและห้าม fallback เป็น sequential write
- คำสั่งสื่อสารทำใน worker thread/queue เดียวเพื่อไม่ให้เปิด bus พร้อมกันหลายคำสั่งและไม่ค้าง Tkinter
- Torque Off เป็น high-priority operation: ยกเลิก motion ที่ยังไม่เริ่มทั้งหมด แล้วทำทันทีหลัง SDK transaction ที่กำลังทำอยู่จบ โดยไม่เปิด serial พร้อมกันอีก thread
- หลัง WritePos ให้ poll ทุก 100 ms จน `Moving=0` และ position error ไม่เกิน 8 counts; timeout คำนวณจาก `max_delta/speed + 3 s` จำกัดช่วง 5-30 s
- เมื่อ timeout, SDK error, ID ขาด หรืออ่าน position ไม่ได้: ยกเลิก motion, disable controls และพยายาม Torque Off ทุก ID
- ปุ่ม Torque Off ไม่รอ queue งานเคลื่อนที่ใหม่; หลังสั่งแล้ว motion controls ถูกปิดจนกด Enable Motion อีกครั้ง
- ห้ามเขียนค่าลง EEPROM ในเครื่องมือนี้

## Software Structure

```text
tools/servo_calibration_gui/
  app.py                    # Tkinter UI and event wiring
  controller.py             # state machine, validation, motion orchestration
  feetech_bus.py            # official SDK adapter and mock adapter interface
  servo_config.json         # IDs, limits, Center, Home, labels, port defaults
  requirements.txt          # ftservo-python-sdk and pyserial
  START_SERVO_GUI.bat       # Windows launcher
  tests/
    test_controller.py
    test_config.py
```

SDK adapter ทำให้ unit tests ใช้ mock bus ได้โดยไม่เปิด COM8 ส่วน GUI จะไม่เรียก SDK โดยตรง

## Testing and Acceptance

- Unit tests ยืนยัน clamp, reject unknown ID, speed/step limits, pose target tables และ fault state
- Mock smoke test เปิด GUI ได้และจำลอง Connect/jog/Home/Center/Torque Off โดยไม่มีฮาร์ดแวร์
- Syntax/import test ผ่านบน Python 3.12
- Hardware acceptance ทำทีละขั้น: ปิด FD, Connect read-only, ตรวจ Position, Enable Motion, jog ทีละ ID, จากนั้นจึงลอง Center/Home
- สำเร็จเมื่อผู้ใช้กด `+/-` แล้ว Servo ที่เลือกขยับช้าไม่เกินช่วง, กด Home/Center ได้หลังยืนยัน, Torque Off หยุดการถือแรง และบันทึกทิศทาง/CSV/JSON ได้

## Builder Decisions

- ใช้ speed raw 50 เป็นค่าเริ่มต้นตามคำขอ “ความเร็วน้อย ๆ”; ผู้ใช้เลือกได้สูงสุด 100 เฉพาะเครื่องมือนี้
- ใช้ dynamic direction labels ตามชนิด joint แทนปุ่มหน้า/หลัง/ซ้าย/ขวาชุดเดียว เพราะช่วยลดการบันทึกผิดแกน
- มี optional `--mock`; โหมดจริงเป็นค่าเริ่มต้นแต่ยัง disconnected จนผู้ใช้กด Connect
- ไม่แก้ `ROBOT_TEST_DATA.txt` อัตโนมัติจาก GUI; เก็บผลแยกก่อนเพื่อให้ตรวจแล้วค่อยยืนยันลง source of truth
- Reviewer call: Servo นอก safe range ทำให้ fault โดยไม่ขยับกลับเอง
- Reviewer call: multi-joint pose ไม่มี sequential fallback เพื่อป้องกัน partial pose
- Reviewer call: Torque Off แทรกก่อนงานค้างแต่ไม่แย่ง serial transaction ที่กำลังทำอยู่
- Reviewer call: settle tolerance 8 counts และ dynamic timeout 5-30 วินาที

