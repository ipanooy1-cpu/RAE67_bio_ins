# โปรแกรมทดสอบ Feetech SCS15 แบบปลอดภัย

โปรแกรมนี้ใช้ทดสอบหุ่นโคมไฟ 4 แกนบน Windows ก่อนเชื่อม ROS 2

## ติดตั้งครั้งแรก

เปิด PowerShell ที่โฟลเดอร์โปรเจกต์แล้วรัน:

```powershell
python -m pip install -r tools\servo_calibration_gui\requirements.txt
```

หรือดับเบิลคลิก `INSTALL_DEPENDENCIES.bat` หนึ่งครั้ง

## เปิดโปรแกรมจริง

1. ปิดโปรแกรม Feetech FD ให้หมด เพราะ COM8 เปิดพร้อมกันสองโปรแกรมไม่ได้
2. เปิดไฟเลี้ยง Servo และตรวจว่าสาย/วงจรถูกต้อง
3. รองรับแขนและหัวไว้ โดยเฉพาะก่อนกด Torque Off
4. ดับเบิลคลิก `START_SERVO_GUI.bat`
5. กด Connect โปรแกรมจะ ping และอ่านอย่างเดียว ยังไม่ขยับ
6. ตรวจว่า ID 0, 1, 2, 3 แสดง Position ถูกต้อง
7. กด ENABLE MOTION โปรแกรมจะตั้ง Goal เท่ากับ Position ปัจจุบันก่อนเปิด Torque
8. เริ่มจากเลือก Servo ทีละ ID แล้วกด `+` หรือ `-` ด้วย Step 10, Speed 50
9. หลังขยับ ให้กดปุ่มทิศที่มองเห็น เช่น ซ้าย/ขวา หรือก้ม/เงย
10. ลอง Home/Center หลังจาก jog ทีละแกนผ่านแล้วเท่านั้น

## ปุ่มสำคัญ

- `+` / `-`: ขยับ Servo ที่เลือกเท่านั้น
- `GO HOME`: ID0=404, ID1=271, ID2=946, ID3=0
- `GO CENTER`: ID0=410, ID1=566, ID2=593, ID3=176
- `TORQUE OFF ALL`: ปลดแรง Servo ทั้งหมด แขนหรือหัวอาจตกตามแรงโน้มถ่วง

`TORQUE OFF ALL` เป็นคำสั่ง software ไม่ใช่ E-stop แบบตัดไฟ หากเกิดเหตุฉุกเฉินและ software ไม่ตอบสนอง ให้ใช้วิธีตัดไฟ hardware ที่ปลอดภัย

## ข้อจำกัดความเร็ว

- Speed: 20, 50 หรือ 100 เท่านั้น; ค่าเริ่มต้น 50
- Step: 1, 5, 10 หรือ 20 counts; ค่าเริ่มต้น 10
- โปรแกรมไม่ส่ง Speed 0
- ทุก target ถูกจำกัดด้วย safe range ของแต่ละ ID

## คำเตือนท่า Home

- ID3 Home=0 เท่ากับ min limit พอดี ไม่มีระยะเผื่อ
- ID2 Home=946 ห่าง max limit 77 counts

## โหมดจำลอง

ดับเบิลคลิก `START_SERVO_GUI_MOCK.bat` เพื่อทดลองปุ่มโดยไม่เปิด COM8 และไม่ขยับหุ่น

## ไฟล์ผลลัพธ์

โปรแกรมสร้างไฟล์ใน `tools\servo_calibration_gui\output\`:

- `servo_test_log.csv`: ประวัติ Connect, Jog, Home, Center และ error
- `calibration_results.json`: ทิศทางที่ผู้ใช้กดบันทึก
- `mock_servo_test_log.csv`: log จากโหมดจำลอง แยกจากข้อมูลจริง
- `mock_calibration_results.json`: ทิศทางจากโหมดจำลอง แยกจากข้อมูลจริง

