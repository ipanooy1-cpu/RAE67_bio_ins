from pathlib import Path
import json,csv,hashlib,math,sys,html
sys.stdout.reconfigure(encoding='utf-8')
r=Path(r'C:\Users\ittip\Downloads\RAE67_bio_ins-main\lab_04\results\completed_20261109')
lab=r.parent.parent
manifest=json.loads((r/'manifest.json').read_text(encoding='utf-8'))
metrics=json.loads((r/'comparison/metrics.json').read_text(encoding='utf-8'))
by={x['condition']:x for x in metrics}
def load(folder,filename):
 with (r/folder/filename).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def at(rows,t):return next(x for x in rows if math.isclose(float(x['time_s']),t,abs_tol=1e-9))
def near(a,b):assert math.isclose(float(a),b,abs_tol=1e-10),(a,b)
checks=[]
for condition in by:
 rows=load('comparison',condition+'_step.csv');assert len(rows)==601
 assert all(float(x['time_s'])==round(i*.05,8) for i,x in enumerate(rows))
 assert sum(float(x['stimulus'])==1 for x in rows[1:])==200
 if condition=='C0':assert all(x['h']=='' for x in rows)
 else:assert all(0<=float(x['h'])<=1 for x in rows)
 config=json.loads((r/'comparison/config.json').read_text(encoding='utf-8'))
 assert config['controller_sha256']==manifest['source_sha256']['student_hormone.py']
 checks.append(f'{condition}: 601 rows, 600 updates, shared stimulus verified')
a=load('comparison','C1_step.csv')
for t,h in [(10.05,.04),(10.1,.0784)]:near(at(a,t)['h'],h)
checks.append('C1 first two on updates: H=.04, .0784 verified')
zero=load('zero','C1_zero.csv');assert all(float(x['h'])==0 for x in zero)
spike=load('spike','C1_spike.csv');assert sum(float(x['stimulus'])==1 for x in spike[1:])==1
near(at(spike,10.05)['h'],.04)
fault=load('fault','C1_fault.csv');f=at(fault,15.05);g=at(fault,15.1)
assert sum(int(x['fault']) for x in fault)==1 and f['fault']=='1'
for k in ['h','r','p','c','b','raw']:near(f[k],0)
near(f['phi_rad'],.2);near(f['stride_half_m'],.055);near(g['h'],.04)
for p in ['zero','one','spike','fault']:
 m=json.loads((r/p/'metrics.json').read_text())[0]
 assert all(m[k] is None for k in ['latency_s','rise_10_90_s','recovery_s'])
checks.append('Extreme tests: zero baseline, one finite, one-interval spike, fault reset/recovery, N/A timing verified')
assert load('week03_handoff','C1_step.csv')==a
checks.append('Actual Week03 contract produces identical C1 raw trace')
# Reproduce in memory without mutating source or replacing original outputs.
import importlib.util
spec=importlib.util.spec_from_file_location('verified_runner',r/'source_snapshot/lab04.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
controller=runner.load_controller(r/'source_snapshot/student_hormone.py')
contract=runner.load_contract(r/'source_snapshot/handoff_contract.json')
for c in by:
 repeated=runner.simulate(controller,c,'step',contract)
 assert runner.metrics(repeated,c,'step')==by[c]
checks.append('Independent rerun of all five deterministic conditions reproduces metrics exactly')
(r/'verification.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
def fmt(x):return 'N/A' if x is None else f'{x:.6f}'
headers=['Condition','peak_H','AUC_H (H·s)','latency (s)','rise (s)','recovery (s)','upper clamp fraction','phi TV (rad)']
keys=['condition','peak_h','auc_h_left','latency_s','rise_10_90_s','recovery_s','upper_clamp_fraction','phi_total_variation_rad']
mdtable='| '+' | '.join(headers)+' |\n|'+'---|'*len(headers)+'\n'
for m in metrics:mdtable+='| '+m['condition']+' | '+' | '.join(fmt(m[k]) for k in keys[1:])+' |\n'
identity=f'ชื่อ/รหัส: อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม: __________ | วันที่รันจริง: 09/11/2026 | code commit: {manifest["code_commit"][:7]}'
provenance='อ้างอิง README/worksheet ของ Lab04 รายวิชา RAE67 Bio-Inspired Robotics ซึ่งอธิบายสมการต้นทาง Hc(t)=βHc(t−1)+Hg(t)−Hr(t), Hg(t)=αf(S(t)), Hr(t)=ΣγᵢReceptorᵢ(t) และอ้าง Homchanthanakul et al. (2019), DOI 10.1109/IROS40897.2019.8968580 แบบจำลองที่รันเป็น proposed course model แบบ Euler ไม่ใช่การทำซ้ำผลของบทความ และไม่แทน β ด้วย k_clear โดยตรง'
para1='กลไกฮอร์โมนใช้ S กระตุ้น P=k_prod S ขณะที่ C=k_clear H_old และ B=k_bind R_old เป็นอัตรากำจัดที่คำนวณจากสถานะเก่าชุดเดียวกัน ก่อนอัปเดต H_new=clamp(H_old+dt(P−C−B),0,1) และอ่าน receptor ใหม่ R=H ภายใต้ bounds 0–1 จึงเก็บประวัติของสิ่งเร้าและค่อย ๆ กลับสู่ปกติ ต่างจาก C0 ซึ่ง R=S โดยตรง จากนั้น bounded mapping ส่ง phi=clamp(.20+.20R,.10,.45) rad และ stride=clamp(.055+.010R,.040,.070) m โดยไม่สั่งมอเตอร์ตรง '+provenance
para2='ข้อมูลสนับสนุน prediction ที่บันทึกไว้ก่อนการรันชุดนี้: C2 เพิ่ม production ทำให้ latency ลดจาก C1 .15 เป็น .10 s และ rise ลดจาก 2.70 เป็น 1.05 s; C3 ลด clearance ทำให้ recovery เพิ่มจาก 2.85 เป็น 5.10 s (ช้ากว่า 2.25 s); C4 ตัด binding ทำให้ recovery เป็น 3.80 s (ช้ากว่า C1 .95 s) C2/C3 มี peak_H=1 เท่ากันเพราะ saturation แต่ AUC ต่างกัน 10.672410 กับ 11.389145 H·s และ upper-clamp fraction ต่างกัน .290000 กับ .273333 จึงต้องใช้หลาย metric ส่วน C0 ไม่มี H ทำให้ peak_H/AUC/clamp fraction เป็น N/A ไม่ใช่ศูนย์ ค่า latency/recovery .05 s ของ C0 เป็นผลของ post-update sampling ไม่ใช่ความหน่วงทางกายภาพ'
para3='ขอบเขตหลักฐานจำกัดที่ hormone subsystem แบบ deterministic; TV ต่ำกว่าไม่ได้พิสูจน์ gait ที่ดีขึ้น โดย phi TV ของ C3=.397890 rad ต่ำกว่า C1=.399829 rad เล็กน้อยส่วนหนึ่งเพราะ H ของ C3 ยังเหลือมากกว่าที่ปลาย trial ไม่ใช่หลักฐานว่าหุ่นยนต์เดินดีกว่า ผล zero คง H=0; spike มี S=1 หนึ่ง interval ที่ 10.00 s ให้ H=.04 ที่ 10.05 s; fault NaN ที่ input15.00 ทำให้ H=R=0 และ phi=.20/stride=.055 ที่ state15.05 ก่อนสะสมใหม่ H=.04 ที่15.10 s ขอบเขตซอฟต์แวร์และ fallback นี้ไม่ใช่ actuator limits, watchdog หรือ E-stop การทดลอง Lab05 ควรเชื่อม hormone–CPG เปรียบเทียบ fixed/direct/hormone/binding-ablation ใช้ schedule และ warmup เดียวกัน และแยก phi-only/stride-only เพื่อศึกษาสาเหตุ ก่อนขยายสู่ contact feedback และการทดลองฮาร์ดแวร์ที่สอบเทียบแล้ว'
report='# รายงาน Lab04 Artificial Hormone Mechanism\n\n'+identity+'\n\n'+ '\n\n'.join([para1,para2,para3])+'\n\n## ผล Controlled comparison\n\n'+mdtable+'\nโปรโตคอล: dt=.05 s, duration30 s, H0=0; S=0 ที่[0,10), S=1 ที่[10,20), S=0 ที่[20,30); 601 states/600 updates ทุกเงื่อนไข ข้อมูลจาก comparison/metrics.json; ค่าตารางปัด6ตำแหน่ง เก็บค่าดิบเต็มใน JSON\n\n## หลักฐานและคำสั่งรัน\n\nChecker13/13; ดู checker.txt, verification.txt, manifest.json, source_snapshot และ README_REPRODUCE.md กราฟอยู่ comparison/report.html และ extreme reports ตามแต่ละโฟลเดอร์ วันที่เอกสารร่างเดิม29/10/2026ไม่ใช่วันที่รันชุดนี้ ช่องกลุ่มเว้นให้ผู้เรียนเติม\n'
(r/'REPORT_TH.md').write_text(report,encoding='utf-8')
# Complete worksheet, distinguish prior user predictions from measured evidence.
worksheet='''# ใบงาน Lab04 ฉบับกรอกผลจริง

'''+identity+'''

## A ก่อนรัน

Prediction ในส่วนนี้มาจากร่างที่ผู้เรียนส่งไว้ในแชตก่อนผู้ช่วยรันชุด completed_20261109 ไม่ได้อ้างว่าเป็น prediction ที่คิดขึ้นใหม่หลังเห็นผล

```text
S → P ─────────────────────┐
H_old → C ────────────────(−) → H_new = clamp(H_old + dt(P−C−B))
H_old → R_old → B ────────(−)                ↓
                                          R_new → bounded phi/stride
H_new ถูกเก็บเป็น H_old ของรอบถัดไป
```

S เพิ่ม P; H_old เพิ่ม clearance C; receptor จาก H_old เพิ่ม binding B; ผลสุทธิเปลี่ยน H แล้ว receptor อ่านสถานะใหม่ก่อน mapping จึงมีความจำเชิงเวลา

|Comparison|Prediction ก่อนรัน|เหตุผลจากสมการ|ผลจริงหลังรัน|
|---|---|---|---|
|C2 vs C1|เพิ่มเร็วและอาจชนเพดาน|prod .8→1.2 เพิ่ม P|latency .10 vs .15 s; rise1.05 vs2.70 s; peak1 vs .999715; clamp .29 vs0|
|C3 vs C1|สะสมมากและลดช้า|clear .6→.25 ลด C|AUC11.389145 vs9.999644; recovery5.10 vs2.85 s|
|C4 vs C1|สะสมมากและลดช้า|bind .2→0 ทำให้ B=0|AUC10.754720 vs9.999644; recovery3.80 vs2.85 s|
|C0 vs C1|ตอบตรง ไม่มีความจำ|R=S ไม่มี H|latency .05 vs.15 s; recovery .05 vs2.85 s; C0 H=N/A|

C2/C3 peak เท่ากันที่1เนื่องจาก upper bound ต้องดู AUC/recovery/clamp fraction ร่วมด้วย C1 peak .999715 ยังไม่ถูก upper-clamp

## B โค้ดและคำนวณมือ

'''+provenance+'''

receptor(.2,.1,.5)=(.2−.1)/(.5−.1)=.25; function ตรวจ finite และ h_max>h_min แล้วจำกัดผล0–1

C1: prod=.8, clear=.6, bind=.2, dt=.05, S=1 ใช้สถานะเก่าสำหรับทุกอัตรา

|input_time_s|time_s|P|C|B|H_raw|H|R|phi rad|stride m|
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|10.00|10.05|.8|0|0|.04|.04|.04|.208|.0554|
|10.05|10.10|.8|.024|.008|.0784|.0784|.0784|.21568|.055784|

รอบ1: H=0+.05(.8−0−0)=.04; รอบ2: H=.04+.05(.8−.024−.008)=.0784 ตรวจตรงกับ CSV แล้ว input_time_s เป็นต้นช่วงอ่านinput ส่วน time_s เป็นสถานะหลังupdate ต่างกัน dt=.05 s ไม่ใช่การวัดเวลาตอบสนองมอเตอร์จริง

Checker ผ่าน13/13 เก็บ output ใน checker.txt; ไม่เปลี่ยนโค้ด student_hormone.py ในการรันครั้งนี้

## C Controlled comparison

'''+mdtable+'''
AUC ใช้ left rectangle ΣH(t_k)dt 600 intervals ไม่รวม endpoint เพิ่มอีก dt; upper clamp fraction มี denominator600 updates; riseวัด10→90%ของ peak_R ใน on-window[10,20]; recoveryวัดหลัง20 sจนR≤10%ของ peakก่อนปิด

C3 ฟื้นช้ากว่า C1=5.10−2.85=2.25 s; C2/C3 peak=1เท่ากัน แต่ AUC ต่าง .716735 H·s, recovery ต่าง2.25 s และ clamp fractionต่าง .016667 แยกระบบได้ C0ไม่มีสถานะH จึงใช้ N/A ไม่แทน0 TVต่ำไม่ยืนยัน gait เพราะLabนี้ไม่รันCPG/body และค่าปลายtrialมีผลต่อTV

## D Extreme tests และ handoff

|Profile C1|หลักฐานจาก CSV/metrics|ผล|
|---|---|---|
|zero|ทุก601states H=R=0; phi=.20 stride=.055; fault0|ผ่าน|
|one|S=1ครบ600updates; peak_H=.999999999977; upper clamp0; AUC28.750000 H·s|ผ่าน เข้าใกล้1แต่ไม่ได้เกิดupper clamp|
|spike|S=1เพียงinterval input10.00; state10.05 H=.04 และค่อยลด; peak_H=.04|ผ่าน|
|fault|NaN1sample input15.00; state15.05 fault1 H/R/raw/P/C/B=0 phi=.20 stride=.055; state15.10 fault0 H=.04|ผ่าน|

Timing latency/rise/recovery ของทั้ง4 extreme profiles เป็น N/A ตามนิยาม Lab เพราะไม่ใช่ step protocol ไม่ใช้ศูนย์แทน N/A สำหรับ fault input เก็บ nan ใน CSV เป็นสิ่งเร้าที่จงใจฉีด แต่ controller output ไม่เป็นNaN

ใช้ contract เดิมจริงจาก lab_03/results/week4_bridge/handoff_contract.json โดยระบุ --contract แล้ว C1 CSV ตรงกับการใช้ contract ของLab04ทุกแถว

|R|phi rad|stride_half m|
|---:|---:|---:|
|0|.20|.055|
|1|.40|.065|

คง alpha=1.10, dt=.05, lift=.03; bounds phi[.10,.45], stride[.040,.070] ซอฟต์แวร์clampนี้ไม่ใช่ขอบเขตมุม/ความเร็ว/แรงบิดเซอร์โว ไม่ทดแทนwatchdog/E-stop Lab04ยังไม่ทดสอบgait, energy, terrain, stability, physical latencyหรือhardware safety

## E สรุปสามย่อหน้า

'''+ '\n\n'.join([para1,para2,para3])+'''

## Checklist และไฟล์หลักฐาน

- [x] โค้ด student_hormone.py และ source snapshot
- [x] comparison CSV 5ไฟล์ ใน comparison/
- [x] extreme CSV 4ไฟล์ ใน zero/one/spike/fault
- [x] config.json ทุกrun และ manifest.json พร้อมSHA256/commit
- [x] กราฟSVGและ report.html ทุกrun
- [x] metrics.json/metrics.csv ทุกrun
- [x] รายงาน REPORT_TH.md และ REPORT_TH.html
- [x] คำสั่งรันซ้ำ README_REPRODUCE.md
- [ ] ผู้เรียนเติมกลุ่ม ตรวจความถูกต้องของชื่อ/วันที่ และอ่านอธิบายผลด้วยตนเองก่อนส่ง
'''
(r/'WORKSHEET_COMPLETED_TH.md').write_text(worksheet,encoding='utf-8')
# Portable reproduction instructions: immutable snapshots, new output locations.
repro='''# วิธีตรวจหลักฐานและรันซ้ำ

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
'''
(r/'README_REPRODUCE.md').write_text(repro,encoding='utf-8')
# Printable two-page report with full references and three-paragraph conclusion.
tr='<tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in ['C','peak H','AUC H·s','latency s','rise s','recovery s','clamp','phi TV'])+'</tr>'
for m in metrics:tr+='<tr><td>'+m['condition']+'</td>'+''.join('<td>'+fmt(m[k])+'</td>' for k in keys[1:])+'</tr>'
style='''@page{size:A4;margin:15mm}*{box-sizing:border-box}body{font-family:Tahoma,"Leelawadee UI",sans-serif;color:#111;margin:0;font-size:10.5pt;line-height:1.5}.page{max-width:180mm;margin:10mm auto;padding:0}h1{font-size:17pt;margin:0 0 8px}h2{font-size:12pt;margin:12px 0 5px}p{margin:7px 0}table{width:100%;border-collapse:collapse;font-size:8pt;margin:8px 0}td,th{border:1px solid #bbb;padding:5px;text-align:center}th{background:#e8edf0}code{font-family:Consolas,monospace;font-size:9pt}.meta{font-size:9pt}.plot{width:100%;height:46mm;object-fit:contain}.foot{font-size:8pt;color:#444}.page+.page{break-before:page}@media print{.page{margin:0;max-width:none}.no-print{display:none}}'''
page1=f'''<h1>รายงาน Lab04 Artificial Hormone Mechanism</h1><p class="meta">{html.escape(identity)}</p><h2>การทดลองและการตรวจโค้ด</h2><p>เปรียบเทียบ C0 direct, C1 baseline(.8/.6/.2), C2 productionเพิ่ม(1.2/.6/.2), C3 clearanceลด(.8/.25/.2), C4ไม่มีbinding(.8/.6/0) โดยใช้ dt=.05 s, H0=0, duration30 s เหมือนกัน S=0ช่วง0–10 s, S=1ช่วง10–20 s แล้วปิด20–30 s; ทุกcondition601states/600updates Checkerผ่าน13/13</p><h2>สมการและการตรวจสองรอบแรก</h2><p><code>P=k_prod S; C=k_clear H_old; B=k_bind R_old<br>H_new=clamp(H_old+dt(P−C−B),0,1); R_new=receptor(H_new)</code></p><p>receptor(.2,.1,.5)=.25; C1จากH=0ให้H=.0400ที่10.05 s แล้ว .0784ที่10.10 s ตรงกับCSV input_timeคือเวลาต้นช่วง ส่วนtime_sคือสถานะหลังupdate ไม่ใช่physical latency</p><h2>ผลจาก comparison/metrics.json</h2><table>{tr}</table><p class="foot">AUCใช้left rectangle600intervals; clamp fractionหาร600updates; rise10–90%อิงpeakในon-window; N/AของC0เพราะไม่มีH ค่าตารางปัด6ตำแหน่ง C0 latency.05 sเกิดจากpost-update logging</p><img class="plot" src="comparison/r.svg" alt="กราฟ receptor R ทุกเงื่อนไข"><p class="foot">กราฟต้นฉบับ comparison/r.svg; ช่วงพื้นสีคือเปิดstimulus10–20 s</p>'''
page2=f'''<h1>สรุปผลและขอบเขตหลักฐาน</h1><p>{html.escape(para1)}</p><p>{html.escape(para2)}</p><p>{html.escape(para3)}</p><h2>Handoff และการทำซ้ำ</h2><p>ทดสอบcontractเดิมจากLab03จริงแล้ว: R=0ให้phi=.20 rad/stride=.055 m และR=1ให้phi=.40 rad/stride=.065 m; trace C1ตรงกับcontractLab04ทุกแถว รันซ้ำแบบdeterministicทั้ง5conditionsให้metricsตรงกัน ดูverification.txt</p><p class="foot">Code commit {manifest['code_commit']}<br>Controller SHA256: {manifest['source_sha256']['student_hormone.py']}<br>คำสั่งรันซ้ำ: README_REPRODUCE.md; คำสั่งที่รันจริง: manifest.json; raw/config/metrics/graphs: comparison,zero,one,spike,fault,week03_handoff; snapshotโค้ดและเอกสาร: source_snapshot</p><p class="foot">อ้างอิง: READMEและworksheetของรายวิชา https://github.com/potiwat/RAE67_bio_ins/tree/main/lab_04 และ Homchanthanakul et al.(2019) DOI10.1109/IROS40897.2019.8968580 ตามที่READMEระบุ ค่าทั้งหมดเป็นproposed course model รายงานจัดจากผลรัน09/11/2026 ช่องกลุ่มให้ผู้เรียนเติมก่อนส่ง</p>'''
(r/'REPORT_TH.html').write_text('<!doctype html><html lang="th"><meta charset="utf-8"><title>รายงาน Lab04</title><style>'+style+'</style><section class="page">'+page1+'</section><section class="page">'+page2+'</section></html>',encoding='utf-8')
print('Verified '+str(len(checks))+' evidence checks; completed worksheet, report and reproduction guide generated in '+str(r))
