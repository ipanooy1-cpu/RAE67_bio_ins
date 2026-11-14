# วิธีเปิดผลและรันซ้ำ Lab05

เปิดREPORT_TH.htmlหรือREPORT_TH.mdเป็นรายงาน; WORKSHEET_COMPLETED_TH.mdสำหรับคำตอบทุกข้อ; comparison/report.htmlและcontact/report.htmlเป็นinteractive reportsต้นฉบับ กราฟstaticอยู่figures/

ใช้Python3.10ขึ้นไป standardlibraryเท่านั้น Pythonversionจริงและcommandsที่รันอยู่RUN_MANIFEST.json โค้ดหลักcourse_model.pyเป็นscaffoldรายวิชา ไม่ได้โหลดstudent codeตรง แต่ตรวจเทียบกับLab04แล้ว ไม่แก้sourceเดิม การรันซ้ำไม่มีrandomnoiseจึงเป็นreproducibility ไม่ใช่independent trials

แตกZIP เปิดTerminalที่โฟลเดอร์หลัก แล้วรันโดยเลือกreplayใหม่ที่ยังไม่มี:

```powershell
cd reproduce_source
python lab05.py --condition all --profile step --mapping both --output-dir ../replay/comparison
python lab05.py --mapping phi-only --output-dir ../replay/phi_only
python lab05.py --mapping stride-only --output-dir ../replay/stride_only
python lab05.py --condition B2 --profile zero --output-dir ../replay/zero
python lab05.py --condition B2 --profile one --output-dir ../replay/one
python lab05.py --condition B2 --profile spike --output-dir ../replay/spike
python lab05.py --condition all --profile fault --output-dir ../replay/fault
python contact_demo.py --output-dir ../replay/contact
```

แต่ละrunเก็บsource_snapshot/config/manifestแล้ว ห้ามแก้rawCSVย้อนหลัง กลุ่มยังเว้นว่างให้ผู้เรียนเติม ผู้ช่วยบันทึกhypothesisก่อนรันในPREDICTIONS_BEFORE_RUN.md ไม่ได้อ้างว่าเป็นpredictionของผู้เรียน

Source: https://github.com/potiwat/RAE67_bio_ins/tree/main/lab_05
Paper roleตามSOURCES.md: https://doi.org/10.1109/ACCESS.2020.2992794 ไม่ได้reproduceMNLC/terrainfeedbackหรือhardwareperformance
