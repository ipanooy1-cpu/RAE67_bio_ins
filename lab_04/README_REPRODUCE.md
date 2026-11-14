# วิธีตรวจหลักฐานและรันซ้ำ

ผลชุดนี้รัน09/11/2026ด้วยโค้ดจริงของผู้เรียน ไม่แก้student_hormone.py โค้ดcommitเดิมบันทึกในmanifest.jsonและhashของcontroller/runnerอยู่ในทุกconfig.json ข้อมูลเป็นการจำลอง ไม่ใช่ผลฮาร์ดแวร์ การรันซ้ำdeterministicไม่ใช่independent repeated trials

เปิด REPORT_TH.html เพื่ออ่านรายงานพร้อมพิมพ์ และ WORKSHEET_COMPLETED_TH.md สำหรับคำตอบทุกข้อ A–E เปิด comparison/report.html เพื่อดูกราฟต้นฉบับ

## รันซ้ำจาก ZIP โดยใช้โค้ด snapshot

แตกZIPแล้วเปิดTerminalที่โฟลเดอร์หลักของชุดส่งงาน ใช้Python3.10ขึ้นไป ไม่ต้องติดตั้งpackage:

```powershell
cd source_snapshot
python check_submission.py --student-file student_hormone.py
python lab04.py --controller-source student --condition all --profile step --output-dir ../replay/comparison
python lab04.py --controller-source student --condition C1 --profile zero --output-dir ../replay/zero
python lab04.py --controller-source student --condition C1 --profile one --output-dir ../replay/one
python lab04.py --controller-source student --condition C1 --profile spike --output-dir ../replay/spike
python lab04.py --controller-source student --condition C1 --profile fault --output-dir ../replay/fault
python lab04.py --controller-source student --condition C1 --profile step --contract week03_handoff_contract.json --output-dir ../replay/week03_handoff
```

ใช้ชื่อreplayใหม่ถ้ามีอยู่แล้ว ห้ามใช้overwriteเพื่อรักษาหลักฐานเดิม เทียบmetrics.jsonของreplayกับผลเดิมโดยไม่แก้CSVย้อนหลัง

## ต้นทาง

- https://github.com/potiwat/RAE67_bio_ins/tree/main/lab_04
- https://doi.org/10.1109/IROS40897.2019.8968580 (บทความที่READMEอ้าง; ตัวเลขEulerของLabเป็นproposed course model)

source_snapshot/README.mdและworksheet.mdเป็นเอกสารรายวิชาที่ใช้จริง ไม่ใช่รายงานที่กรอกแล้ว
