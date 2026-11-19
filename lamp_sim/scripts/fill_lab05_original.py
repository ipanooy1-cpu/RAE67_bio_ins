from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import json,csv,shutil,hashlib
lab=Path(r'C:\Users\ittip\Downloads\RAE67_bio_ins-main\lab_05');latest=lab/'results/latest'
out=Path(r'C:\Users\ittip\Documents\ChatGPT\lamp\output\lab05_edit')
m=json.loads((latest/'comparison/metrics.json').read_text());cm=json.loads((latest/'contact/metrics.json').read_text())
doc=Document(lab/'Lab05_Student_Worksheet_TH.docx');p=doc.paragraphs
answers={
2:'ชื่อและรหัส อิทธิพล แป้นอ้อย / 6752500053   กลุ่ม ______   วันที่ทดลอง 09/11/2026',
14:'S → fixed/direct/hormone controller → R_used → bounded phi/stride → SO(2) CPG → tripod decoder → kinematic body',
15:'ยังไม่มี independent sensory feedback จาก terrain/body กลับสู่ controller; contact หลักมาจาก sign(o2) ใน decoder ส่วน contact demo ใช้ synthetic actual แยกจาก main runner',
17:'Hypothesis ก่อนรัน: B2 hormone จะมี max-step ของ phi/stride ต่ำกว่า B1 direct แต่ command latency และ recovery มากกว่า ไม่คาดว่า TV รวมต้องลดมากเสมอ',
18:'บันทึกแผนโดยผู้ช่วยก่อนรันใน results/latest/PREDICTIONS_BEFORE_RUN.md; source/proposed equations และ claim boundary อ้าง SOURCES.md ไม่ใช่ผล terrain ของ paper',
33:'B1 อ่าน S=1 และใช้ command ที่ 10.00 s ทันที จึง command latency=0 แต่ post-state บันทึกที่ 10.05 s จึง state latency=.05 s เป็น numerical scheduling ไม่ใช่ hardware latency',
34:'B2 ใช้ R ของ state ต้น interval: command10.00 ใช้ R=0 แล้ว H_end10.05=.04; command10.05 จึงใช้ phi=.208 rad และ stride=.0554 m',
36:'B3 ตัดเฉพาะ binding term k_bind=.2→0 แต่ยังมี H state, production และ clearance จึงยังมี memory; recovery=3.80 s ช้ากว่า B2=2.85 s อยู่ .95 s',
44:'สนับสนุน hypothesis: max-step phi ของ B2=.008 เทียบ B1=.20 rad/step ลด96%; max-step stride=.0004 เทียบ .010 m/step แต่ command latency เพิ่ม0→.15 s และ recovery0→2.85 s',
45:'Negative result: TV phi ใกล้กัน .399827 กับ .400000 rad ไม่สนับสนุนว่าฮอร์โมนต้องลด TV อย่างมาก จึงต้องใช้ max-step และ time trace ร่วมกัน',
47:'ไม่เท่ากัน: peak R_used ของ B0/B1/B2/B3 = 0/1/.999715/1 ทำให้ peak phi = .20/.40/.399943/.40 rad แม้ bounds เหมือนกัน และ command clamp count เป็น0ทุกcondition',
48:'TV ไม่ใช่ Harmony ของ paper และ support count=3 จาก decoder ไม่ใช่หลักฐานว่าหุ่นยนต์ไม่ล้ม',
50:'ต้องแยกช่วงเพราะมี transient และ memory: B2 frequency pre=.624878, on=1.202760, off=.698234 Hz; ค่าเฉลี่ย30 s จะกลบการเปลี่ยนช่วงเปิดและปิดสิ่งเร้า',
51:'ยังไม่เรียก on/off ว่า steady state โดยไม่มีหลักฐานว่าเข้าสู่ภาวะคงตัว ช่วง off ยังมี H เหลือและค่อย ๆ ลด',
53:'ไม่มี body dynamics, force/IMU/CoM, sensor indices และ task normalization ที่ตรงนิยาม จึงไม่วัด paper Stability/Harmony/Displacement; kinematic distance ไม่ใช่ paper Displacement',
64:'Fallback ทำก่อน command/CPG update ใน interval15.00–15.05: fault=1, h_used=r_used=0, phi=.20 rad, stride=.055 m; state15.05 H=0 และ state15.10 H=.04 หลัง input กลับปกติ',
65:'Policy นี้เป็น software fallback ไม่ใช่การรับรอง hardware safety ยังต้องมี actuator limits, slew-rate limiting, watchdog และ E-stop ที่ออกแบบตามกลไก',
66:'ตรวจ extreme เพิ่ม: zero คง H=0; one อยู่ใน bounds; spike เปิด S=1 เพียงหนึ่ง interval ที่10.00 s; timing ของ non-step profiles เป็น N/A ตามนิยาม',
75:'Pearson วัดความสัมพันธ์เชิงรูปคลื่น จึงไม่เปลี่ยนเมื่อ actual=a+b×expected ที่ b>0: gain-offset มี SI≈1 แต่ MAE=.162844 ไม่ใช่0',
76:'ควรดู absolute error ร่วมด้วย ไม่สรุปว่าความสัมพันธ์สูงเท่ากับแรงหรือขนาดสัญญาณถูกต้อง',
78:'ทุกขากลับเฟสมี SI≈−1 เท่ากัน จึง population SD≈0 เป็น common-mode blind spot; release เมื่อ SIF=0 เท่ากับ 1/(1+exp(0))=.5 เช่นเดียวกับ matched ที่ SI=1ทุกขา',
79:'SIF≈0 ไม่ได้แปลว่าทุกขาถูกต้อง ต้องดู global discrepancy หรือ MAE ร่วมกับความต่างระหว่างขา',
81:'SI/SIF/release เป็น N/A เพราะ variance=0 ทำให้ Pearson denominator เป็น0 ไม่แทนด้วย SI=0; MAE=0ก็ไม่ได้ทำให้ correlation นิยามได้',
83:'Last50 samples รวม current: first valid sample49 ที่2.45 s; NaNที่sample15.00 กระทบ50windows ช่วง15.00–17.45 s และกลับ valid17.50 s ไม่นับstartup49rows',
84:'fault case จึง unavailable99rows รวมstartup และ valid501/600; paired-product Pearson เป็น proposed course definition ไม่ใช่ verified Eq.(3) และยังไม่ต่อ C_g/HR/MI_H',
92:'Claim ที่รองรับ: ใน step profile ช่วง trial0–30 s B2 ลด phi_max_step_rad96% (.20→.008 rad/step) แลก command latency.15 s และ recovery2.85 s; อ้าง comparison/metrics.json',
93:'Claim ที่ยังไม่รองรับ: หุ่นยนต์ไม่ล้มหรือประหยัดพลังงาน ต้องเพิ่ม dynamics, IMU/CoM/force, motor current และ hardware trials ที่สอบเทียบ',
94:'วิธีรันซ้ำและ Python version ดู results/latest/README_REPRODUCE.md กับ RUN_MANIFEST.json; ตรวจเทียบ hormone จาก Lab04 ให้ตรงกับ course_model ทั้ง600updatesรวมfaultและratesB2/B3แล้ว',
}
for i,text in answers.items():p[i].text=text
with (latest/'comparison/B2_intervals.csv').open() as f:rr=list(csv.DictReader(f))
fmt=lambda x:'N/A' if x is None else f'{float(x):.6f}'
for i,t in enumerate([10,10.05,20],1):
 x=next(x for x in rr if float(x['command_time_s'])==t)
 for j,k in enumerate(['command_time_s','state_time_s','h_state_start','h_state_end','r_used','phi_rad']):doc.tables[1].cell(i,j).text=fmt(x[k])
for i,(c,x) in enumerate(m.items(),1):
 for j,k in enumerate(['condition','phi_total_variation_rad','phi_max_step_rad','command_latency_s','command_recovery_s']):doc.tables[2].cell(i,j).text=c if j==0 else fmt(x[k])
 doc.tables[3].cell(i,1).text=fmt(x['segments']['on']['frequency_hz']);doc.tables[3].cell(i,2).text=fmt(x['segments']['on']['distance_m'])
vals=['ทำทั้ง phi-only และ stride-only ตามแผนก่อนรัน','phi-only คง stride=.055 m ทุก interval; stride-only คง phi=.20 rad ทุก interval','Metric: on frequency Hz / on distance m; คาด phi-only เปลี่ยนจังหวะ ส่วน stride-only คง frequency แต่ระยะเปลี่ยน','B2 phi-only: on f=1.202760 Hz,d=1.467193 m; stride-only: f=.624877 Hz,d=.901666 m; both: f=1.202760 Hz,d=1.706250 m เป็นผลเฉพาะ kinematic model ไม่อ้าง terrain/แรงบิดจริง']
for i,v in enumerate(vals,1):doc.tables[4].cell(i,1).text=v
for i,v in enumerate(['1 / 0 / 0','.20 rad / .055 m','0 / .04'],1):doc.tables[5].cell(i,1).text=v
for i,(c,x) in enumerate(cm.items(),1):
 for j,v in enumerate([c,fmt(x['mean_si']['LF']),fmt(x['mean_sif']),fmt(x['mean_absolute_error']),str(x['valid_sif_rows'])+'/600']):doc.tables[6].cell(i,j).text=v
for i in range(1,len(doc.tables[7].rows)):doc.tables[7].cell(i,1).text='ครบ'
# Preserve template styles and page structure; allow answer rows to expand.
for table in doc.tables:
 for row in table.rows:
  trpr=row._tr.get_or_add_trPr()
  for e in list(trpr):
   if e.tag==qn('w:trHeight'):trpr.remove(e)
# Add final compact source and raw-evidence references without changing instructor prompts.
doc.add_paragraph('หลักฐานผลจริง: results/latest/comparison, phi_only, stride_only, fault, contact และ figures; ตรวจ hashes และการรันซ้ำแล้ว ดู VERIFICATION.txt และ RUN_MANIFEST.json กลุ่มยังเว้นให้ผู้เรียนเติม')
doc.save(out/'Lab05_Student_Worksheet_TH.docx')
# Markdown answer replaces worksheet in place only after QA, no fabricated authorship.
text=(latest/'WORKSHEET_COMPLETED_TH.md').read_text(encoding='utf-8-sig')
text=text.replace('# ใบงาน Lab05 ฉบับกรอกผลจริง','# ใบงาน Lab 05 Prediction timing evidence')
(out/'worksheet.md').write_text(text,encoding='utf-8')
# Root README keeps the full course instructions, adds real completed output entry points.
readme=(lab/'README.md').read_text(encoding='utf-8-sig')
intro='''# Lab 05 ผลการทดลองและคู่มือ

ทำ comparison B0–B3, phi-only, stride-only, fault, zero/one/spike และ contact mini-lab แล้ว วันที่09/11/2026

- ใบงานที่กรอกแล้ว: [worksheet.md](worksheet.md), [Word](Lab05_Student_Worksheet_TH.docx), [PDF](Lab05_Student_Worksheet_TH.pdf)
- รายงานพร้อมกราฟ: [results/latest/REPORT_TH.html](results/latest/REPORT_TH.html)
- Raw data และ interactive comparison: [results/latest/comparison/report.html](results/latest/comparison/report.html)
- Contact report: [results/latest/contact/report.html](results/latest/contact/report.html)
- รันซ้ำและที่มาของผล: [results/latest/README_REPRODUCE.md](results/latest/README_REPRODUCE.md)

โค้ดหลักเป็น working scaffold ของรายวิชา ไม่ได้มี TODO ให้เขียนใหม่ ผลเป็นการจำลอง ไม่ใช่ hardware verification

'''
(out/'README.md').write_text(intro+readme,encoding='utf-8')
print(out)
