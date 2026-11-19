from pathlib import Path
import json, csv, hashlib, importlib.util, subprocess, html, sys
from collections import Counter
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
paths=json.loads(Path('lab67_paths.json').read_text())
out6,out7=(Path(paths[k]) for k in ('6','7'))
lab6,lab7=out6.parent.parent,out7.parent.parent
m6=json.loads((out6/'comparison/metrics.json').read_text())['runs']
m7=json.loads((out7/'comparison/summary.json').read_text())
expected=['button_01','touch_01','approach_01','clear_01','near_01','clear_02','button_02']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))
def table(headers, records):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|',*['| '+' | '.join(map(str,r))+' |' for r in records]])
def write(p,s): p.write_text(s,encoding='utf-8')
def outcome(r,id): return next(o for o in r['source_outcomes'] if o['input_id']==id)
def val(v): return 'N/A' if v is None else str(v)

# Validate original run hashes before deriving any report. Raw files stay immutable.
audit={}
for number,b in [(6,out6),(7,out7)]:
    manifest=json.loads((b/'comparison/manifest.json').read_text())
    hashes=manifest.get('sha256',manifest)
    checked=[]
    for rel,digest in hashes.items():
        if isinstance(digest,str) and len(digest)==64 and (b/'comparison'/rel).is_file():
            assert sha(b/'comparison'/rel)==digest,rel
            checked.append(rel)
    assert checked,'no manifest entries checked'
    audit[str(number)]={'manifest_files_verified':len(checked),'replay':{}}
for name in ['raw_C1_r01.csv','events_C1_r01.csv']:
    a,b=out6/'comparison'/name,out6/'replay'/name
    assert a.read_bytes()==b.read_bytes(),name
    audit['6']['replay'][name]=sha(a)
for name in ['command_trace.csv','events.csv']:
    a,b=out7/'comparison/C1_r02'/name,out7/'replay/C1_r01'/name
    assert a.read_bytes()==b.read_bytes(),name
    audit['7']['replay'][name]=sha(a)
for r in m7:
    assert r['published']==r['received']+r['transport_dropped']+r['censored_after_trial']
    assert r['received']==r['accepted']+r['discarded_out_of_order']
    assert len(r['source_outcomes'])==10
for r in m6:
    assert len(r['source_outcomes'])==10
    assert sum(o['primary_expected_both'] for o in r['source_outcomes'])==7

spec=importlib.util.spec_from_file_location('policy',lab6/'student_policy.py'); policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
states=['normal','interested','happy','afraid','sleepy']; events=['fault','near','clear','touch','button','approach','timeout','idle']
fsm_records=[[s,*[policy.transition(s,e) or 'hold' for e in events]] for s in states]
fsm=table(['state',*events],fsm_records)

def chart(data, output, key1, label1, key2, label2, maxima):
    im=Image.new('RGB',(1500,540),'white');dr=ImageDraw.Draw(im)
    font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',23)
    small=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',20)
    for panel,(key,label,top) in enumerate([(key1,label1,maxima[0]),(key2,label2,maxima[1])]):
        left=85+panel*750;right=left+570;y0=430;y1=85
        dr.text((left,20),label,font=font,fill='black')
        for k in range(5):
            y=y0-(y0-y1)*k/4;dr.line((left,y,right,y),fill='#dddddd',width=1)
            dr.text((left-55,y-10),f'{top*k/4:g}',font=small,fill='black')
        for c,color in [('C0','#3e6c91'),('C1','#bd622c')]:
            rr=[r for r in data if r['condition']==c];pts=[]
            for j,r in enumerate(rr):
                x=left+60+j*230;y=y0-r[key]/top*(y0-y1);pts.append((x,y))
                dr.ellipse((x-6,y-6,x+6,y+6),fill=color)
                dr.text((x-16,y-32 if c=='C0' else y+10),str(round(r[key],3)),font=small,fill=color)
            dr.line(pts,fill=color,width=4)
        for j,seed in enumerate([41,42,43]):dr.text((left+40+j*230,y0+14),str(seed),font=small,fill='black')
        dr.text((left+140,490),'Paired synthetic seed',font=small,fill='black')
        dr.text((right-140,52),'C0',font=small,fill='#3e6c91');dr.text((right-60,52),'C1',font=small,fill='#bd622c')
    im.save(output)
chart(m6,out6/'comparison_summary.png','state_transition_count','State transitions','primary_pass_1s_both_count','Primary passing inputs / 7',(80,8))
chart(m7,out7/'comparison_summary.png','primary_median_both_latency_s','Observed median both latency (s)','primary_missing_both_count','Primary missing inputs / 7',(.2,1.4))

ev6=rows(out6/'comparison/events_C1_r01.csv')
selected=[next(e for e in ev6 if e['input_id']==id) for id in ['button_01','touch_01']]
latencytable=table(['Input','Source','Recognized','Decision/queue','Apply','Motion','RGB','Both latency s'],[[e['input_id'],e['source_time_s'],e['recognized_time_s'],e['decision_time_s'],e['applied_time_s'],e['first_motion_s'],e['first_rgb_s'],e['both_latency_s']] for e in selected])
summary6=table(['Condition/seed','All sources','Both','≤1s both','No both','Max observed s','State transitions'],[[r['condition']+'/'+str(r['seed']),10,r['external_responded_both_count'],r['external_pass_1s_both_count'],r['external_no_both_onset_count'],r['max_both_latency_s'],r['state_transition_count']] for r in m6])
missing6=table(['Condition/seed','Input ID','Status'],[[r['condition']+'/'+str(r['seed']),o['input_id'],o['status']] for r in m6 for o in r['source_outcomes'] if o['both_latency_s'] is None])
policysha6=sha(lab6/'student_policy.py');policysha7=sha(lab7/'lamp_week07/student_policy.py')
identity='อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม: ยังไม่ระบุ | วันที่รัน 09/11/2026'
scope='ผลทั้งหมดเป็น simulation ด้วย virtual clock และ proposed course model ไม่มี learning และยังไม่ได้วัด ROS/DDS หรือการเคลื่อนไหวของหุ่นยนต์จริง'
commands6='''python check_submission.py --contract baseline
python check_submission.py --contract group
python lab06.py --policy student --condition all --repeats 3 --output-dir results/reproduce_01
python lab06.py --policy student --condition C1 --repeats 1 --replay results/completed_20261109/comparison/inputs_r01.csv --output-dir results/replay_reproduce_01'''
answers6=f'''# ใบงาน Lab06 ฉบับตอบพร้อมผลทดลอง

{identity}

{scope}

## 1 Prediction และ protocol
บันทึก prediction ก่อนรันใน results/completed_20261109/PREDICTION_BEFORE_RUN.json โดยผู้ช่วยเตรียมก่อน execute: C0 อาจสลับ state จาก bounce/noise บ่อยกว่า C1; C1 debounce/hysteresis เพิ่มเวลารอการยืนยัน แต่ลดคำสั่งที่ถูกแทรกก่อน apply สมมติฐานไม่ได้รับรองว่า latency สูงสุดของ C1 ต้องมากกว่า C0 เพราะ C0 อาจถูก preempt หลายครั้ง near ต้องมี priority เหนือ touch; fault ขณะ normal และ touch ระหว่าง afraid อาจไม่มี onset ใหม่

ใช้ baseline mapping เดียวกัน C0 raw และ C1 guarded, seeds 41/42/43 แบบจับคู่, dt=0.02 s, duration=22 s, scheduler=0.04 s; C1 debounce button/touch=0.06 s, near enter≤0.20/exit≥0.28 m, approach enter≤0.80/exit≥0.95 m; sample age>0.12 s หรือ invalid → fault คง bounds และ slew ทั้งสองเงื่อนไข Deadline=1 s; observation window=22 s เป็นสาม synthetic replications ไม่ใช่ผู้เล่นสามคน

Expected IDs ประกาศก่อนรัน 7 รายการ: {', '.join(expected)} คงทั้ง 10 sources ใน metrics โดยอีก 3 รายการคือ touch_conflict, invalid_01 และ stale_01 ไม่บังคับให้สร้าง expression ใหม่

## 2 FSM และ guard
ทุก state: fault→normal; near→afraid; clear→normal. เมื่อ afraid ให้ hold positive events และ timeout/idle จนได้รับ clear หรือ fault. State อื่น: touch→happy; button/approach→interested; interested/happy + timeout 2 s→normal; normal + idle 6 s→sleepy; อื่น ๆ hold

Priority: fault > near > clear > touch > button > approach > timeout > idle. Entry afraid เกิดจาก near; exit ต้อง clear/fault จึงไม่ถูก touch ดึงออกจากสถานะหลบอันตราย

{fsm}

## 3 Expression mapping และความปลอดภัย
q=[tilt,extend,nod] หน่วย rad เป็นแกนนามธรรม ไม่ใช่พิกัดข้อต่อจริงโดยอัตโนมัติ

| State | q target rad | RGB 0–255 | ความหมาย |
|---|---|---|---|
| normal | [0,0,0] | [60,90,140] | กลับท่ากลาง |
| interested | [0.22,0.18,0.06] | [255,180,0] | เอียงและยืดเข้าหา |
| happy | [0.10,0.10,0.18 sin(2π elapsed)] | [40,220,80] | พยักหน้า |
| afraid | [-0.22,-0.22,-0.16] | [230,30,30] | หดและก้มหลบ |
| sleepy | [0,-0.15,-0.20] | [50,40,100] | หดและก้มพัก |

Bounds tilt±0.35, extend±0.25, nod±0.30 rad; slew≤0.8 rad/s จาก course model ค่าพวกนี้ไม่ใช่ actuator limits ที่รับรองแล้ว ก่อนต่อจริงต้องวัด neutral/ทิศหมุน/หน่วย/อัตราทด/พื้นที่ชน/ขีดจำกัดแต่ละแกน, clamp+slew ใน driver, watchdog และ E-stop แยกจาก FSM. fault→normal อาจยังสั่งเคลื่อนกลับกลาง จึงไม่เท่ากับ emergency stop. ผู้ทดสอบเป็นผู้ควบคุมหยุด; ยังไม่มีผล calibration จริง

## 4 Checker และการแก้
Starter ตรวจ 40 transition pairs ไม่ผ่าน 7 กรณี ตัวอย่าง interested+timeout คืน None จึงไม่กลับ normal แก้โดยคืน normal เมื่อ current_state เป็น interested/happy และ event=timeout เพิ่ม normal+idle→sleepy และ touch→happy หลัง afraid guard ผล checker_baseline.txt และ checker_group.txt ผ่านทั้ง 40 คู่ ไม่ได้ปิด safety หรือเปลี่ยน engine

## 5 ผล C0/C1
{summary6}

![ผลเปรียบเทียบ](results/completed_20261109/comparison_summary.png)

รวม primary 21 input opportunities ต่อ condition: C0 ผ่าน 19/21 ขาด 2; C1 ผ่าน 21/21 ขาด 0. All sources=30 ต่อ condition; both C0=19/30, C1=21/30. C1 ลด transitions จาก 67/72/63 เป็น 9/10/9 ลดลง 58/62/54 ครั้งหรือ 86.57/86.11/85.71% ตามลำดับ ทั้งสองไม่มี command clamp แต่ไม่ได้แปลว่า hardware ปลอดภัยแล้ว

Negative results: C0 seed42 clear_01 ไม่ถูก recognize; seed43 clear_02 เป็น no_state_change จึงไม่มี both onset ไม่ใส่ latency=0. Latency สูงสุดที่สังเกต C0=0.24/0.18/0.04 s, C1=0.14/0.14/0.14 s จึงไม่มีหลักฐานว่า C1 ช้ากว่าเสมอ. C1 button_01 seed41 ช้ากว่า C0 0.10 s (0.14−0.04), แต่ approach C1=0.04 s เร็วกว่า C0=0.24 s เพราะ candidate ของ C0 ถูก preempt

## 6 ตรวจ latency จาก CSV
เลือก C1 seed41 จาก comparison/events_C1_r01.csv

{latencytable}

button: filter=1.10−1.00=0.10 s; decision=recognition; queue→actual apply=1.14−1.10=0.04 s; both=max(1.14,1.14)−1.00=0.14 s. Debounce ตั้งไว้ 0.06 s แต่ bounce ทำให้รอจนค่านิ่งจึงใช้จริง 0.10 s. touch: 3.10−3.00=0.10 s โดย recognition3.06, apply3.10. งบออกแบบก่อน hardware: sensor/transport≤0.20, filter/decision≤0.20, queue/physical output≤0.40 รวม≤0.80 s เผื่อ0.20 s; เป็นเป้าหมาย ไม่ใช่ผลวัดจริง

## 7 Conflict fault sleep recovery และ missing
C1 seed41 near7.00→afraid, touch recognize7.06 ถูก policy_held เพราะ afraid guard; C0 ที่ recognize พร้อมกันอาจ discarded_priority. clear9.00→normal; invalid11.00 และ stale12.00 รับ fault แต่ state เดิม normal จึง no_state_change; idle15.00→sleepy; button18.00 recognize18.06→interested และ output18.10; timeout20.06→normal, apply20.10

discarded_priority คือแพ้ event อื่นใน tick เดียว; policy_held คือ policy คืน None; no_state_change คือ target เท่า state เดิม; preempted_before_apply คือคำสั่งถูกแทนก่อน output; censored_end คือจบ trial ก่อนเห็น onset. กรณีไม่เห็นทั้งสองช่องเก็บ null/N/A พร้อมเหตุผล ไม่สรุปว่าทุก missing เป็น drop และไม่แทนด้วย0. เก็บรายการทั้งหมดดังนี้

{missing6}

## 8 Replay และไฟล์หลักฐาน
raw_C1_r01.csv และ events_C1_r01.csv ของ replay ตรงต้นฉบับ byte-for-byte และ SHA256; รายละเอียด analysis_validation.json. seed ใน replay config อาจเป็น null เพราะอ่าน fixture โดยตรง ไม่ใช่สุ่มใหม่. policy SHA256={policysha6}

ไฟล์อยู่ results/completed_20261109/comparison/: config.json, inputs_r01–03.csv, source_inputs_r01–03.csv, raw_C0/C1_r01–03.csv, events_C0/C1_r01–03.csv, metrics.json/csv, manifest.json, source_snapshot/, report.html และ trace SVG. Python version และคำสั่งจริงอยู่ RUN_MANIFEST.json. ใช้ output ใหม่เสมอเพื่อไม่เขียนทับ raw

```powershell
{commands6}
```

## 9 สรุปและ exit quiz
FSM ทำให้ตรวจได้ครบ40คู่และตรวจ priority/guard อย่างชัดเจน การคืน None ต่างจากคืน state เดิม. C1 สนับสนุน prediction ว่าลด chattering แต่ latency ต้องดูทั้ง misses และ candidate preemption ไม่อ้างจากค่ากลางเพียงอย่างเดียว กราฟและตัวเลขไม่พิสูจน์ physical responsiveness

Learning ต้องมี policy/parameter เปลี่ยนจากประสบการณ์ เช่นเรียนรู้ preference gain จาก feedbackพร้อม validation; FSM คงที่นี้ยังไม่เรียนรู้ งานต่อยอด sound/phone interaction แยกจาก mandatory lab. ก่อนยืนยัน real latency ต้องวัดต้นทางปุ่ม/สัมผัสด้วย triggerร่วมกับ encoder/กล้องสำหรับ motion และ photodiode สำหรับ RGB พร้อมระบุ clock mapping และ uncertainty

อ้างอิงภายใน: README.md, interface_contract.json, course_model.py และข้อมูลดิบ/metrics ของ run นี้ ค่าตัวเลข mapping/filter เป็น proposed course model ไม่ใช่ผลสอบเทียบจากหุ่นยนต์
'''
write(lab6/'worksheet.md',answers6)

# Mini-project proposal is a future experiment, independent of completed transport trials.
plan={
 'status':'PROPOSED ONLY; AHM-CPG integration, ROS/DDS, 600s human scenario and real robot NOT EXECUTED',
 'question':'การเพิ่มฮอร์โมน engagement ที่สะสมตามสิ่งเร้า ก่อนปรับ gain ของ SO(2) CPG ลดการเปลี่ยนคำสั่งฉับพลันและทำให้การฟื้นตัวหลังปิดสิ่งเร้าช้ากว่า direct stimulus หรือไม่ ในโคมไฟปฏิสัมพันธ์ 600 s?',
 'hypothesis':'C1 hormone จะลด peak command rate และเพิ่ม recovery time เทียบ C0 direct ภายใต้ fixture เดียวกัน; ไม่รับรอง both latency ดีขึ้น และไม่ใช้ state label เป็นหลักฐานอารมณ์จริง',
 'biological_inspiration_source':'การสะสมและสลายสัญญาณฮอร์โมนที่ทำให้ผลคงอยู่หลัง stimulus; ใช้สมการต้นทางในเอกสาร Week04 ของรายวิชา Hc(t)=beta Hc(t-1)+Hg(t)-Hr(t), Hg=alpha_h f(S), Hr=sum(gamma_i Receptor_i). SO(2) recurrent oscillator ตาม Lab03/course notation ของ Dr. Poramate; การเชื่อมและตัวเลขด้านล่างเป็น proposed course model ไม่ใช่ physiology calibration',
 'AHM_equation':'หนึ่ง hormone engagement H: R_old=clamp(H_old,0,1); P=.8*S; C=.6*H_old; B=.2*R_old; H_raw=H_old+dt_h*(P-C-B); H_new=clamp(H_raw,0,1); R_new=H_new, dt_h=.05s,H0=0. ทุก rate ใช้ OLD state แล้ว update ครั้งเดียว. beta ไม่เท่ากับ clear โดยตรง; โมเดลนี้เป็น Euler course adaptation',
 'SO2_CPG_equation':'[a1_next,a2_next]^T=alpha*[[cos(phi),sin(phi)],[-sin(phi),cos(phi)]]*[o1,o2]^T; o1_next=tanh(a1_next),o2_next=tanh(a2_next); คำนวณพร้อมกันจาก OLD o. alpha=1.10,phi=.20 rad/update,o1(0)=.10,o2(0)=0,dt_cpg=.02s; tanh และค่าพารามิเตอร์เป็น course choices ไม่ใช่ continuous-time frequency calibration',
 'integration_description':'Sensor validation/debounce→S=max(button,touch,approach_binary); AHM→R; C0 ใช้ R=S, C1 ใช้ R=H. ทั้งคู่ G=.02+.06*R rad และ q_target=q_neutral+G*[o1,o2,-o1], ผ่าน limits/slew/watchdog ก่อน driver. FSM แสดง emotion/RGB เดิม โดย near/fault override CPG; เมื่อไม่ปลอดภัยหยุด oscillator path. คง phi=.20 และalpha=1.10 เพื่อเปลี่ยนเพียงการมี hormone memory',
 'independent_variable':'มี/ไม่มี hormone memory ก่อน CPG gain เท่านั้น; C0/C1 ชื่อซ้ำกับ transport study แต่เป็นคนละการทดลอง ห้ามนำผลtransportมาแทนผลAHM',
 'conditions':[{'name':'C0 direct','baseline':True,'change':'R=S direct ไม่มี hormone memory; คง CPG, gain mapping, safety และ fixture เหมือน C1','repeats':3},{'name':'C1 hormone','baseline':False,'change':'R=H bounded Euler engagement; เปลี่ยนเฉพาะ memory stage','repeats':3}],
 'metrics':[{'name':'Peak command rate','unit':'rad/s','measurement':'max over joints,ticks |q_applied(t)-q_applied(t-dt)|/dt; report number of samples at slew cap too; higher smoothness expected lower peak but cap may cause tie','missing_rule':'ไม่มี traceหรือstop→N/Aพร้อมreason; ไม่ลบทิ้ง trial และไม่ใส่0; denominator=all planned3trials/condition/platform'}, {'name':'Recovery time','unit':'s','measurement':'จาก falling edgeของstimulus ถึง R<=.1 ต่อเนื่อง .5s; กลไกinternal ไม่ใช่physical onset; เทียบ C0/C1 ภายใต้ off intervalเดียวกัน','missing_rule':'ยังไม่ฟื้นก่อนจบoff interval→right censored พร้อมเวลาสังเกต; ห้ามแทน0'}, {'name':'Both physical latency','unit':'s','measurement':'max(first physical motion,first photodiodeRGB change)-hardware source trigger; simulationใช้ applied onsetแยกtable; deadline1s observation22s/event','missing_rule':'เก็บทุกexpectedID; ช่องใดไม่พบ→null/missing,พบครบแต่>1s→deadline fail; ห้ามรวมphysicalและcommand metrics'}],
 'controls':['baseline FSM/filter/topic contract and safety overrides identical; no online learning','same scripted input IDs/times/values paired seeds41/42/43 and identical dt,duration,reset H/o and oscillator phase','same neutral pose,limits,slew .8rad/s,RGB mapping,transport settings,sensor positions,lighting and supply; calibrate per platform'],
 'parameters':[{'name':'AHM prod/clear/bind','value':[.8,.6,.2],'unit':'normalized H per s, 1/s, normalized H per s','provenance':'Lab04 proposed course model; not biological measured constants'}, {'name':'H0 / H bounds / receptor bounds','value':[0,0,1,0,1],'unit':'dimensionless','provenance':'Lab04 normalization/reset convention'}, {'name':'dt_h / dt_cpg','value':[.05,.02],'unit':'s','provenance':'group proposed multi-rate schedule, hold R between hormone updates'}, {'name':'SO2 alpha/phi/o1_init/o2_init','value':[1.1,.2,.1,0],'unit':'dimensionless,rad/update,dimensionless,dimensionless','provenance':'Lab03 course oscillator and initialized trial; phi not Hz'}, {'name':'gain intercept/slope','value':[.02,.06],'unit':'rad','provenance':'group proposed low-amplitude simulation starting values; require hardware calibration'}, {'name':'tilt/extend/nod bounds','value':[.35,.25,.30],'unit':'rad absolute symmetric','provenance':'Lab06 software bounds only; hardware limits must measured and narrower limit wins'}, {'name':'slew cap / stale limit','value':[.8,.12],'unit':'rad/s, s','provenance':'Lab06 course safety/freshness constants, not certified hardware limits'}],
 'simulation_plan':'ยังไม่ได้รัน AHM-CPG600s: implement multi-rate AHMat.05s and CPGat.02s, same7topic adapter, log H/R/o/q/source IDs plus clocks; 2conditions x3pairedseeds x600s. Reset H=0,o=[.1,0] and FSM normal before each; warm-up excluded by fixed2s then start common trial clock. Keep raw/config/codeSHA and all aborted trials',
 'real_robot_plan':'ยังไม่ได้รัน: Ubuntu24.04/Jazzy host + tested MCU/Agent firmware (not supplied). Sensors button/touch/range and encoder+photodiode measurement. Confirm actual board,pins,power,neutral,sign,gear ratio and mechanical limits with instructor. Map abstract tilt/extend/nod to calibrated J2/J3/J4 only after linkage fit; J1 fixed neutral until a revised contract. Execute 2conditions x3trials x600s with one consenting operator/participant per pair and rests; report as repeated case study, not population inference',
 'clock_correlation_plan':'Wire7topics unchanged noHeader; use sidecar with trial_id/source_id/acquisition sequence at instrumented source. MCU source trigger and photodiode/encoder share acquisition clock when possible; otherwise two-way sync estimateoffset/drift with timestamps before/aftertrial, state residual+resolution uncertainty and reject cross-host subtraction when mapping unavailable. ROS bag/collector alone measures delivery or applied command not physical onset; source_latency null when identity ambiguous',
 'safety_stop_plan':'ก่อนจริงต้องให้ผู้สอนตรวจ wiring/limitsและกำหนดwatchdog deadlineจากcalibration; operatorเข้าถึงE-stopตัดenableได้ตลอด. near/fault/reconnect require validated neutral recovery; comm watchdog never hold stale moving trajectory. Stop trial immediately on unintended motion,collision risk,overcurrent/overtemperature or lowbattery using manufacturer thresholds verified for actual device; recordreasonandtimestamp then reset onlyafterinspection',
 'order_counterbalancing':'3 pairs perplatform order C0-C1,C1-C0,C0-C1 to reduce systematic order bias; only partial balance because3odd, disclose residual order effect. Reset H/o/FSM and pose between trials and rest participant',
 'paired_seed_or_participant_plan':'Simulation paired seeds41,42,43. Real P01 voluntary adult operator in3paired sessions using samepredeclaredscript, anonymized IDs and noface/audio recording; seek instructor approval/consent under course procedure before actual study. No participant recruited/results collected yet',
 'expected_input_ids_before_run':'Completed22s transport study uses button_01,touch_01,approach_01,clear_01,near_01,clear_02,button_02. Future600s study predeclares p_button_060,p_touch_180,p_approach_300,p_clear_420,p_button_540 (5expectedboth pertrial; retainallfault/conflictprobes separately). On intervals60-70,180-190,300-310,near400-420,button540-550; approachoff310 notprimary, clear420 recoveryprimary. motion/RGB expression must differ before each primary; if not, retain no-state-change asmiss not editIDsafterdata',
 'human_scenario_duration_s':600,
 'timeline':'Proposed after09Nov2026: D1 instructor reviews proposal/equations; D2 implementAHMCPG+unit/fixture checks; D3 calibrateandteststop/clock; D4 simulation6x600s; D5 real6x600safterreadinessgate; D6 analyzealltrialsandreport. Totalplannedtrialtime120min plussetup/reset/rest; exactcalendar dates require team availability',
}
write(lab7/'proposal.json',json.dumps(plan,ensure_ascii=False,indent=2))
summary7=table(['Pair/seed','C0 median s','C1 median s','C0 faults/1101','C1 faults/1101','Primary missing C0/C1'],[[i+1, *([])] for i in []]) if False else table(['Pair/seed','C0 median s','C1 median s','C0 faults/1101','C1 faults/1101','Primary missing C0/C1'],[[f'{i+1}/{seed}',m7[2*i]['primary_median_both_latency_s'],m7[2*i+1]['primary_median_both_latency_s'],m7[2*i]['fault_ticks'],m7[2*i+1]['fault_ticks'],f"{m7[2*i]['primary_missing_both_count']}/{m7[2*i+1]['primary_missing_both_count']}"] for i,seed in enumerate([41,42,43])])
transporttable=table(['C/seed','Published','Received','Accepted','Drop','Out-of-order','Censored','Mean age s'],[[r['condition']+'/'+str(r['seed']),r['published'],r['received'],r['accepted'],r['transport_dropped'],r['discarded_out_of_order'],r['censored_after_trial'],f"{r['mean_transport_age_s']:.6f}"] for r in m7])
topics=[['/lamp/input/button','std_msgs/Bool','bool','input_source→interaction'],['/lamp/input/touch','std_msgs/Bool','bool','input_source→interaction'],['/lamp/input/distance','std_msgs/Float32','m','input_source→interaction'],['/lamp/interaction','std_msgs/String','event','interaction→collector/logger'],['/lamp/emotion','std_msgs/String','state','interaction→collector/logger'],['/lamp/servo_command','std_msgs/Float32MultiArray','rad [tilt,extend,nod]','interaction→collector/driver'],['/lamp/rgb_command','std_msgs/ColorRGBA','r,g,b,a in [0,1]','interaction→collector/LED driver']]
topictable=table(['Topic','Type','Units','Publisher→subscriber'],topics)
commands7='''python check_submission.py --contract baseline
python check_submission.py --contract group
python offline_lab.py --condition all --repeats 3 --output-dir results/reproduce_01
python offline_lab.py --condition C1 --repeats 1 --replay results/completed_20261109/comparison/C1_r02/input_trace.csv --output-dir results/replay_reproduce_01
python check_proposal.py proposal.json'''
answers7=f'''# ใบงาน Lab07 ฉบับตอบพร้อมผล offline

{identity}

{scope} AHM–CPG และ scenarioคน600s ด้านล่างเป็น proposal ยังไม่ได้ implement/run ใน runner FSM นี้

Policy SHA256: {policysha7}

## 1 Architecture และ topic contract
ระบบ offline: synthetic input_source→validated/debounced interaction/FSM→servo/RGB commands→collector ในprocessเดียว ไม่มีDDS. ROS sourceที่มีอยู่แยกสามexecutable; driver/MCU firmware/Agentต้องเตรียมเพิ่ม

Graph โครงงานที่เสนอ: sensor driver→interaction→AHM(H)→SO(2)CPG(o1,o2)→output arbiter←FSM(state), จากนั้น clamp/slew/watchdog→motor/LED driver→encoder/photodiode logger. ให้ AHM/CPG/arbiter เป็น internalmodulesของinteractionก่อนเพื่อคง7topics; hostเก็บFSM,H,o; MCUเก็บacquisition sequenceและdriver watchdog. อิทธิพลรับผิดชอบcode/analysis; ผู้ควบคุมhardwareและผู้ตรวจsafetyต้องยืนยันก่อนทดลอง

{topictable}

QoS ทุกpublisher/subscriber: RELIABLE, KEEP_LAST depth10, VOLATILE ตามinterface_contract.json ทั้งหมดมีqueueจำกัดและต้องตรวจ stale แยก; reliable ไม่รับรองdeadlineหรือphysicalonset. ใช้ ros2 topic list -t, ros2 topic info -v และ ros2 topic echo ตรวจtype/QoS/namespaceเมื่อไม่เห็นmessage. เปลี่ยนเฉพาะsourceและdriver adapterเมื่อย้ายsimulation→robot

## 2 Units และ calibration
servo data=[tilt,extend,nod]rad เช่น interested=[.22,.18,.06]. RGB interested=[255,180,0]→ColorRGBA(1,0.705882,0,1); normal=[60/255,90/255,140/255,1]. เปลี่ยนจำนวนแกนหรือส่งdegreeตรง ๆ ไม่ได้ ต้องแปลงradเป็นjointจริงหลังcalibrate neutral,sign,gearing,linkage/bounds/velocity. J1ฐานตรึงneutralก่อน; mapping J2/J3/J4เป็นเพียงแผนรอตรวจกลไกจริง

Events=fault,near,clear,touch,button,approach,timeout,idle; states=normal,interested,happy,afraid,sleepy. safety priorityและafraid guardเหมือนLab06. Controllerdt=.02s/scheduler=.04s, freshness>.12s→fault. Driverwatchdog/MCUdeadlineต้องกำหนดจากhardwaretestก่อนenable; ไม่ถือ.12sเป็นmotorwatchdogที่สอบเทียบแล้ว

## 3 Hypothesis และ measurement boundary ก่อนรัน
PREDICTION_BEFORE_RUN.json ประกาศว่าC1composite delay/dropอาจเพิ่มage,latency,missingและfault เทียบC0ideal. Controls: FSM,guardedfilter,bounds/slew,22s,dt.02s,scheduler.04sและsourcefixturepairedseeds41/42/43เหมือนกัน. Expected7 IDs={', '.join(expected)}, retainall10sources; deadline1s, observation22s. Clockเป็นvirtualเดียวกัน; onsetคือappliedcommand ไม่ใช่motor/LEDจริง

C0delay0/drop0; C1delaychoices[0,.02,.04,.06,.10,.14,.18]s,randomdrop.08และburst12.50–12.70s. initialcheckerfail7pairs ตัวอย่าง interested+timeoutคืนNone แก้เช่นLab06 แล้วbaseline/groupผ่าน40pairsทั้งคู่

## 4 ผล3pairedrepeats และ denominator
{summary7}

![ผลเปรียบเทียบ](results/completed_20261109/comparison_summary.png)

Medianคำนวณเฉพาะprimaryที่พบboth จึงต้องอ่านคู่กับmissing: C0ผ่าน21/21; C1ผ่าน19/21 และmissing2 ไม่ใช่latency0. seed41clear_02ไม่มีboth; seed42button_02ไม่มีboth; seed43ครบ7. maxobservedC0=.14sทุกseed, C1=.20/.22/.18s. C1faultticks=54/81/56 เทียบC0=20/20/20 ต่อ1101ticks. การเพิ่มfaultไม่ใช่หลักฐานแยกสาเหตุdropเพียงอย่างเดียว

{transporttable}

3303published=3channels×1101ticks/trial. ตรวจ published=received+drop+censored และ received=accepted+out_of_order ทุกtrial. Censoredคือdeliveryหลังจบ22sไม่ใช่drop. Meanageใช้receivedmessagesรวมที่out_of_orderตามrunner. C0mean/maxage=0; C1mean=.076853/.077931/.076489s,max=.18s. ไม่อ้างเป็นROSnetworkbenchmark

ไฟล์repository-relative: results/completed_20261109/comparison/C0_r01..03 และC1_r01..03/ มีinput_trace.csv,command_trace.csv,events.csv,metrics.json,config.json; comparison/summary.json,manifest.json,source_snapshot/,report.html. RUN_MANIFEST.jsonเก็บPython/command/policySHA. ReplayC1seed42: command_trace.csvและevents.csvตรงต้นฉบับbyte-for-byteและSHA; analysis_validation.jsonเก็บผลตรวจ. คำสั่งรันซ้ำใช้outputใหม่

```powershell
{commands7}
```

## 5 Invalid/stale กับ communication stress
ทั้งสองconditionมีinvalid11sและstale12sเป็นbaselineprobes จึงC0ยังfault20ticksได้. C1เพิ่มjitter+dropพร้อมกันและทิ้งmessageเก่าตามsequenceในsidecar ทำให้age/missingเปลี่ยน. จะระบุผลjitterหรือdropแยกต้องเพิ่มdelay-only/drop-onlyโดยคงส่วนอื่นเหมือนกัน ห้ามเทียบC1กับC0แล้วสรุปสาเหตุเดี่ยว

## 6 Clock และ micro ROS
MCUclient(sensoracquisition/driver watchdog)→serialtransport→microROSAgent→hostinteraction→commandtopic→Agent→MCUdriver. ยังไม่ได้ต่อหรือรันAgent/firmware. Bool/String/Float32ไม่มีHeaderจึงไม่มีsourceacquisitiontime/IDบนwire; callback receiptสดอาจเป็นค่าเก่าซ้ำ. local_sequenceของคนละnodeไม่ใช่globalID และ perf_counterคนละhostหักตรง ๆ ไม่ได้

แผน: sidecartrial_id/source_id/sequenceจากจุดกำเนิด, hardwaretriggerร่วมกับencoder/photodiodeบนclockเดียวกัน หรือclockmappingoffset/driftที่วัดก่อน/หลังtrialพร้อมresidual+resolutionuncertainty. identityไม่ชัดหรือclockmappingไม่มีให้source_latency=N/A. ROSbagช่วยreplayและตรวจdelivery/config แต่ไม่พิสูจน์physicalonset; collectorreceiptไม่เท่ากับdriverapplyหรือmotion

## 7 Proposal และ exit quiz
proposal.jsonกรอกครบ, ฉบับอ่าน2–3หน้าอยู่results/completed_20261109/proposal.html และproposal.md. มีengagementAHM1ตัว,SO(2)CPG,AHM→CPGgain,baseline2conditions,metrics≥2,simulationและrealconditionละ3repeats,scenario600s,safety/calibration/clock/timeline. เป็นแผนอนาคตทั้งหมด แยกจากผลoffline22s. เช็กproposalยืนยันเพียงfieldครบไม่ใช่อนุมัติความถูกต้องวิทยาศาสตร์/การทดลองมนุษย์

Interfaceช่วยเปลี่ยนadapterโดยคงtype/หน่วย/ความหมาย. Baselineยุติธรรมต้องคงpolicy,fixture,reset,CPG,limits,transport,measurementเหมือนกัน เปลี่ยนเพียงhormonememoryในproject; เก็บทุกmissing/abortพร้อมเหตุผล. อ้างอิงภายใน: README.md,interface_contract.json,lamp_week07/course_model.py,Lab03และLab04coursematerials; โปรดให้ผู้สอนตรวจnotation/sourceก่อนทำprojectจริง
'''
write(lab7/'worksheet.md',answers7)

# A plain HTML rendering keeps complete worksheet answers readable without changing trace reports.
def md_html(md):
    # Small renderer supports exactly the paragraphs, tables, code and image blocks authored here.
    chunks=[]; lines=md.splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            chunks.append('<pre>'+html.escape('\n'.join(code))+'</pre>');i+=1;continue
        if line.startswith('|'):
            group=[]
            while i<len(lines) and lines[i].startswith('|'):group.append(lines[i]);i+=1
            chunks.append('<table>')
            for j,row in enumerate(group):
                if j==1:continue
                tag='th' if j==0 else 'td';chunks.append('<tr>'+''.join(f'<{tag}>'+html.escape(c.strip())+f'</{tag}>' for c in row.strip('|').split('|'))+'</tr>')
            chunks.append('</table>');continue
        if line.startswith('!['):
            src=line.split('](',1)[1].rstrip(')');src=Path(src).name
            chunks.append(f'<img src="{html.escape(src)}">');i+=1;continue
        level=len(line)-len(line.lstrip('#'))
        if level:chunks.append(f'<h{min(level,3)}>'+html.escape(line[level:].strip())+f'</h{min(level,3)}>')
        else:chunks.append('<p>'+html.escape(line)+'</p>')
        i+=1
    return '\n'.join(chunks)
css='''body{font-family:"Leelawadee UI",Tahoma,sans-serif;color:#111;max-width:1050px;margin:30px auto;line-height:1.55}h1,h2,h3{color:black}table{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0}td,th{border:1px solid #bbb;padding:6px;vertical-align:top}th{background:#eee}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}img{max-width:100%}@page{size:A4;margin:16mm} @media print{body{margin:0;font-size:11pt;max-width:none}.page{page-break-after:always}.page:last-child{page-break-after:auto}h2{break-after:avoid}tr{break-inside:avoid}}'''
def html_doc(title,body):return '<!doctype html><html lang="th"><meta charset="utf-8"><title>'+html.escape(title)+'</title><style>'+css+'</style><body>'+body+'</body></html>'
write(out6/'worksheet_answers.html',html_doc('Lab06 answers',md_html(answers6)))
write(out7/'worksheet_answers.html',html_doc('Lab07 answers',md_html(answers7)))

# Concise two-page report and three-page project proposal, with explicit print boundaries.
short6=[f'''# Lab06 FSM และผลการป้องกันสัญญาณรบกวน
{identity}
{scope}
## Prediction และ protocol
C1ควรลดการสลับstateจากnoiseแต่เพิ่มเวลารอfilter; predictionเก็บก่อนรันในPREDICTION_BEFORE_RUN.json. ใช้baselinepolicyเดียวกัน,seeds41/42/43,dt.02s,duration22s,scheduler.04s,7expectedIDsและ10allsource/trial; deadline1s. C1debounce.06s,near.20/.28m,approach.80/.95m; bounds±[.35,.25,.30]rad,slew.8rad/sเหมือนกัน
## FSM
fault→normal,near→afraid,clear→normalจากทุกstate; afraidholdpositiveevents; อื่นtouch→happy,button/approach→interested; interested/happytimeout2s→normal; normalidle6s→sleepy. Priorityfault>near>clear>touch>button>approach>timeout>idle
{fsm}
normalกลางRGB60/90/140; interestedเอียงยืด.22/.18/.06RGB255/180/0; happyพยักnod=.18sin(2πt)RGB40/220/80; afraidหดก้ม−.22/−.22/−.16RGB230/30/30; sleepy0/−.15/−.20RGB50/40/100. qเป็นradนามธรรม
## Checker
40pairsผ่านbaselineและgroup; ก่อนแก้7failures เช่นinterested+timeoutคืนNone แก้กลับnormal. ตารางเต็มและคำตอบครบในworksheet.md
''',f'''# ผลทดลองและข้อจำกัด Lab06
{summary6}
![เปรียบเทียบ](comparison_summary.png)
PrimaryC0=19/21,C1=21/21. transitionsลด58/62/54ครั้ง; C0seed42clear_01ไม่recognize,seed43clear_02no_state_change; missingไม่แทน0. C1สูงสุด.14sทุกseed,C0.24/.18/.04s จึงไม่สรุปC1ช้ากว่าเสมอ
## ตรวจ latency C1 seed41
{latencytable}
button1.00→recognize1.10→queue1.10→apply/motion/RGB1.14 ดังนั้นboth=.14s,filter=.10s,queue=.04s. near7→afraid,touch7.06policy_held; clear9→normal; fault11/12เดิมnormalจึงไม่มีonsetใหม่; idle15→sleepy; button18.06→interestedและapply18.10
## หลักฐานและขอบเขต
Replayraw/eventsตรงbyteและSHA; หลักฐานcomparison/metrics.json,events/rawCSV,config,manifest,source_snapshotและanalysis_validation.json. policySHA={policysha6[:16]}…;Python/คำสั่งจริงในRUN_MANIFEST.json. รันซ้ำจากlab_06ด้วย python lab06.py --policy student --condition all --repeats 3 --output-dir results/reproduce_01
เป็นvirtualcommandonsetเท่านั้น ก่อนจริงต้องcalibratejoint/clockและวัดencoder+photodiodeร่วมtrigger; softwareboundsไม่แทนE-stop/driverwatchdog.FSMคงที่ไม่ใช่learning. อ้างอิงREADME.md,course_model.pyและworksheet.md
''']
write(out6/'student_report.html',html_doc('รายงาน Lab06', ''.join('<section class="page">'+md_html(s)+'</section>' for s in short6)))

proposalpages=[f'''# โครงงานโคมไฟปฏิสัมพันธ์ด้วย AHM และ SO2 CPG
{identity}
สถานะ proposal ยังไม่ได้ทดลอง AHM–CPG,ROSหรือหุ่นยนต์จริง ผลoffline22sอยู่worksheet.mdคนละการทดลอง
## คำถามและแรงบันดาลใจ
{plan['question']}
{plan['hypothesis']}
{plan['biological_inspiration_source']}
## สมการและการเชื่อมระบบ
{plan['AHM_equation']}
{plan['SO2_CPG_equation']}
{plan['integration_description']}
## Architecture
sensor→validation/debounce→interaction/FSM→AHM→CPG→safetyarbiter→servo/RGBdriver; safetyFSMoverrideAHMCPG. Hostเก็บH,o,FSM;MCUacquisition/driverwatchdog. ใช้AHMCPGเป็นinternalmodulesก่อนเพื่อคง7topics; ROSและMCU/Agentยังต้องสร้าง/ทดสอบ
## ที่มาพารามิเตอร์
Lab04ให้prod=.8,clear=.6,bind=.2,H∈[0,1]; Lab03ให้SO(2)notationและcoursealpha1.1,phi.2,o0=[.1,0]. GroupเสนอG=.02+.06Rradและmulti-ratedt_h=.05/dt_cpg=.02s.ค่าเหล่านี้ไม่ใช่ผลสอบเทียบชีววิทยาหรือmechanicalhardware
''',f'''# Interface และการทดลองโครงงาน
{topictable}
QoSทุกtopicRELIABLE,KEEP_LASTdepth10,VOLATILE; servoหน่วยradและRGB/255,a=1.คงmeaningทั้งsimulation/robot. Headerไม่มีบนwireจึงต้องsidecaridentity/clock
## Conditions และ controls
C0directใช้R=S; C1hormoneใช้R=H เปลี่ยนเพียงmemory stage. คงalpha,phi,Gmapping,sourcefixture,FSM,RGB,safety,dtและtransport. resetH=0,o=[.1,0],FSMnormalและneutralทุกtrial; 2ssetupก่อนเริ่มclock. near/faultoverrideเสมอ
Simulation2conditions×3pairedseeds41/42/43×600s และreal2conditions×3pairedsessions×600s รวม12trial/120minเฉพาะเวลารัน. ลำดับpairsC0–C1,C1–C0,C0–C1เป็นpartialcounterbalanceเพราะจำนวนคี่;ไม่อ้างว่ากำจัดorderbiasหมด. RealP01สมัครใจoperatorคนเดียวซ้ำ3session ไม่ใช่3independentparticipants
## Scenario 600 s และ denominator
0–150sท่ากลางและbutton60–70s;150–300s touch180–190s;300–450s approach300–310s,near400–420sและclear420s;450–600sbutton540–550sแล้วพัก. Expectedก่อนรัน5IDs:p_button_060,p_touch_180,p_approach_300,p_clear_420,p_button_540 เก็บfault/conflictเพิ่มทั้งหมดแม้ไม่มีexpressionใหม่; ไม่แก้subsetหลังเห็นผล. ก่อนprimaryต้องวางstateให้expressionเปลี่ยน ถ้าไม่สำเร็จเก็บno-state-change/missตามจริง
## Metrics
M1 peakcommandrate=max|Δq|/dt rad/sทุกแกน พร้อมจำนวนsamplesชนslewcap; C1คาดลดแต่capอาจทำให้เท่ากัน. M2 recoveryจากSoffถึงR≤.1ต่อเนื่อง.5s;ไม่ฟื้นในoffwindowให้right-censored. M3bothlatency=max(motion,RGB)−source; deadline1s,observation22s/event. Physicalใช้encoder/photodiode,simulationใช้appliedcommandแยกกัน. Missingnull/abortพร้อมreason เก็บplanned3trial/condition/platformในdenominator
''',f'''# การวัด ความปลอดภัย และแผนดำเนินงาน
## Clock และไฟล์หลักฐาน
{plan['clock_correlation_plan']}
Logtrial_id,condition,seed/participantID,source_id,acquisition/receive/decision/queue/apply/physicalonset,H/R/o/q,codeSHA,config,calibrationID. เก็บROSbagและsidecarCSV+manifestSHA256ทุกtrial รวมfailed/aborted;ห้ามใช้collectorreceiptแทนphysicalonset. Fitclockmappingก่อน/หลังtrialและรายงานuncertaintyจากresolution+mappingresidual;ถ้ายังวัดไม่ได้ให้N/A
## Robot และ calibration
{plan['real_robot_plan']}
{plan['safety_stop_plan']}
## ความเสี่ยงและการควบคุม
Slewcapอาจบังผลhormoneจึงรายงานcapfractionร่วม; order/participantfatigueอาจbiasจึงreset,restและpartialcounterbalance; derivative/physicalnoiseใช้sampling/filterเดียวกันทั้งconditionsและเก็บraw. ไม่ถือcolor/stateชื่อemotionว่าเป็นหลักฐานความรู้สึกจริง. การทดลองมนุษย์ต้องให้ผู้สอนตรวจแผนและขอconsentก่อน ไม่มีผู้เข้าร่วมหรือข้อมูลจริงตอนนี้
## Timeline และผู้รับผิดชอบ
{plan['timeline']}
อิทธิพลรับผิดชอบcode/analysis/report;ผู้ควบคุมhardwareและผู้ตรวจsafetyต้องยืนยันกับทีมก่อนD3. วันที่ปฏิทินรอยืนยันavailability ไม่รายงานแผนเป็นผลสำเร็จแล้ว
## เกณฑ์ส่งและที่มา
proposal.jsonมีparameter/provenance/metricmissingrulesครบ; check_proposal.pyตรวจเพียงcompletenessต้องให้ผู้สอนทบทวนvalidity. อ้างอิงLab03SO(2),Lab04AHM,Lab06course_model.py,Lab07README.mdและinterface_contract.json. Numericaltransportและmappingทั้งหมดเป็นproposedcoursemodel. Offline22s6runsที่ทำแล้วไม่แทน12trial600sและไม่แทนAHMCPGimplementation
''']
write(out7/'proposal.md','\n\n---\n\n'.join(proposalpages))
write(out7/'proposal.html',html_doc('โครงงานโคมไฟ AHM SO2 CPG',''.join('<section class="page">'+md_html(s)+'</section>' for s in proposalpages)))

# Complete every answer field in original DOCX templates; instructor prompts/rubrics remain.
def setcell(cell,text):
    cell.text=str(text)
    for p in cell.paragraphs:
        p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(10)
def para(d,index,text):
    d.paragraphs[index].text=text
    for r in d.paragraphs[index].runs:r.font.size=Pt(11)
def fill_answers(d,answers):
    for idx,text in answers.items():para(d,idx,text)
    # Remove only remaining empty answer rules, not meaningful blanks such as group ID.
    for p in d.paragraphs:
        if p.text and set(p.text.strip())=={'_'}:p.text='รายละเอียดและหลักฐาน: worksheet.md และ results/completed_20261109'
def fillcol(t,values,col=1):
    for row,value in zip(t.rows[1:],values):setcell(row.cells[col],value)

d=Document(lab6/'archive/completed_20261109/Week06_Student_Worksheet_TH.docx')
fill_answers(d,{
2:identity+'\nPolicy SHA256 '+policysha6,
18:'Prediction ก่อนรัน: near มี priority สูงกว่า touch จึงเข้าสู่ afraid; touch ที่ debounce ตามมาจะถูก afraid guard hold. C1 ควรลด noise-driven transitions แต่เพิ่ม recognition delay. ดู PREDICTION_BEFORE_RUN.json',
19:'ใช้ baseline mapping; expected 7 IDs ประกาศก่อนรัน; retain 10 sources/condition/repeat. ไม่มีการเรียนรู้ policy จากประสบการณ์',
27:'ทุก state ─fault/clear→normal; ทุก state ─near→afraid; afraid ─positive/timeout/idle→hold',
28:'state อื่น ─touch→happy; ─button/approach→interested',
29:'interested/happy ─timeout 2 s→normal; normal ─idle 6 s→sleepy',
30:'sleepy ─button/approach→interested; ─touch→happy; เหตุการณ์ที่ไม่ระบุ hold. รูปและตารางใน worksheet.md',
41:'เก็บ JSON null/CSV blank และ status/reason; both ต้องเห็นครบ motion และ RGB ภายใน observation window22s. พบครบแต่>1sเป็น deadline fail แยกจาก missing',
42:'0 s หมายถึงตอบทันทีซึ่งต่างจากไม่ได้วัด/ไม่เปลี่ยน/ถูก preempt. All10 sources คงไว้ รวม3 intentional non-onset probes',
54:'C1 transitions 9/10/9 เทียบ C0 67/72/63; primary≤1s C1=21/21,C0=19/21. อ้าง comparison/metrics.json และ events_C*_r*.csv',
62:'C1 seed41 button queue1.10s, apply1.14s; scheduler/queue ทำให้เพิ่ม.04s. source1.00→filter1.10 ใช้.10s รวมboth.14s',
64:'ลด transitions 58/62/54 ครั้ง; button seed41 .14−.04=.10sช้าขึ้น แต่ approach .04เทียบ.24sเร็วขึ้นเพราะ C0preemption. จึงไม่สรุปช้ากว่าเสมอ',
66:'ต้องวัด source trigger+encoder/กล้อง motion+photodiode RGB และ clock mapping/uncertainty. ยังไม่มี hardware calibration/physical data',
75:'ตาราง5×8บังคับตรวจทุกคู่ state/event, แยก hold/stateเดิม, ตรวจ priority และ reachable states ได้ก่อนใช้if-else',
77:'nearเข้าafraid; clear/faultออก; nearชนะtouchและguardไม่ให้positiveeventพาออกจากอันตราย. fault→normalยังไม่ใช่E-stop',
79:'Learningต้องupdatepolicy/parameterจากfeedbackเช่นpreferencegainพร้อมvalidation. งานเสริมsound/phoneแยกจากFSMmandatorylab',
})
fillcol(d.tables[0],[json.loads((out6/'RUN_MANIFEST.json').read_text())['python_version']+'; อิทธิพล code/analysis, ผู้ดูแลhardwareรอยืนยัน','Offlineหยุดprocessได้; hardwareต้องoperator+E-stop/driverwatchdogก่อนenable','N/A ยังไม่ต่อจริง; ต้องneutral/sign/units/limits/slewและclockcalibration'])
for row,values in zip(d.tables[1].rows[1:],fsm_records):
    for c,v in zip(row.cells,values):setcell(c,v)
fillcol(d.tables[2],['fault > near > clear > touch > button > approach > timeout > idle','Entry near; exit clear/fault; afraidholdpositiveevents','2 s หลังเข้า interested/happy →normal','6 s ไม่มีinteractionขณะnormal→sleepy','.06sdebounceลดbounce; hysteresisnear.20/.28m,approach.80/.95mลดthresholdchatter'])
expression=[['[0,0,0]rad กลับกลาง','60,90,140','fault/clear/timeout recovery'],['[.22,.18,.06]rad เอียง/ยืด','255,180,0','button/approach'],['[.10,.10,.18sin(2πt)]rad พยัก','40,220,80','touch; timeout2s→normal'],['[-.22,-.22,-.16]rad หด/ก้ม','230,30,30','near; exitclear/fault'],['[0,-.15,-.20]rad หด/ก้มพัก','50,40,100','idle6s; button/touchrecover']]
for row,values in zip(d.tables[3].rows[1:],expression):
    for c,v in zip(row.cells[1:],values):setcell(c,v)
for row,values in zip(d.tables[4].rows[1:],[['≤.20 (target)','source→sensorreceive; hardwareยังN/A'],['≤.20 (target)','recognition/decision−source; offlinebutton.10'],['≤.40 (target)','queue→physical; offlinequeue.04'],['≤.80 + .20margin','งบก่อนhardware ไม่ใช่ผลphysicalวัดจริง']]):
    for c,v in zip(row.cells[1:],values):setcell(c,v)
fillcol(d.tables[6],['near7.00→afraid; C1touch7.06policy_held','clear9.00→normal,apply9.04','fault11/12รับแล้วstateเดิมnormal;no_state_change','idle15→sleepy;button18.06→interested,apply18.10','invalid11s→normalเดิมnormalจึงไม่มีonsetใหม่'])
for row,e in zip(d.tables[7].rows[1:],[ev6[0],ev6[1],ev6[4],ev6[10]]):
    for c,v in zip(row.cells,[e['source_time_s'],e['kind'],e['old_state'],e['decision_time_s'],e['new_state']]):setcell(c,v)
for row,(id,c) in zip(d.tables[9].rows[1:],[(id,c) for id in ['button_01','touch_01','approach_01'] for c in ['C0','C1']]):
    r=next(r for r in m6 if r['condition']==c and r['seed']==41);o=outcome(r,id)
    for cell,v in zip(row.cells[1:],[o['motion_latency_s'],o['rgb_latency_s'],o['both_latency_s'],'seed41; source→onset latency, responded']):setcell(cell,v)
summarycells=[['30sources;both19','30sources;both21'],['19/21passes;2misses','21/21passes;0misses'],['11motionmissing/11RGBmissing','9motionmissing/9RGBmissing'],['primaryclear_01(seed42)notrecognized;clear_02(seed43)nochange;9intendednononset','9intendednononset:touchheld/faultalreadyneutral']]
for row,values in zip(d.tables[10].rows[1:],summarycells):
    for c,v in zip(row.cells[1:],values):setcell(c,v)
fillcol(d.tables[11],['ครบ40pairs','ครบ; diagramในworksheet.md','ครบcomparison/','ครบRUN_MANIFEST.json','ครบ;missingคงnull','ครบเฉพาะsimulation;hardwareN/A'])
# Actual per-modality missing counts, rather than assuming both-missing implies each is absent.
for j,c in enumerate(['C0','C1'],1):
    oo=[o for r in m6 if r['condition']==c for o in r['source_outcomes']]
    setcell(d.tables[10].rows[3].cells[j],f"motion missing={sum(o['first_motion_s'] is None for o in oo)}; RGB missing={sum(o['first_rgb_s'] is None for o in oo)} /30")
d.save(lab6/'Week06_Student_Worksheet_TH.docx')

d=Document(lab7/'archive/completed_20261109/Week07_Student_Worksheet_TH.docx')
fill_answers(d,{
2:identity+'\nPolicy SHA256 '+policysha7,
10:'sensor driver→interaction/FSM→AHM(H)→SO(2)CPG(o)→safetyarbiter→servo/RGBdriver→logger',
11:'AHM/CPG/arbiterเป็นinternalmodulesในinteractionเพื่อคง7topics; FSM safetyoverride near/fault',
12:'Host:interaction/FSM/AHM/CPG/logger;MCU:acquisitionsequence/driver/watchdog;Agentเป็นtransportbridge',
13:'Simulationสลับinputsource/outputcollector;จริงสลับsensorและmotor/LEDdriverหลังcalibration ยังไม่ได้รันROS/MCU',
14:'FSM,H,o1/o2เป็นstate;อิทธิพลรับผิดชอบcode/analysis ผู้ตรวจhardware/safetyรอยืนยัน',
15:'ข้อเสนอนี้เลือกAHM→CPGgain;ทั้งHmemoryและCPGphaseต้องมี ไม่ใช้stateชื่อemotionแทนAHM/CPG',
24:'ros2 topic list -t / info -v / echo;ตรวจnamespace,typeและQoScompatibilityทั้งpublisher/subscriberก่อนโทษnetwork',
25:'Eventsfault/near/clear/touch/button/approach/timeout/idle;statesnormal/interested/happy/afraid/sleepy',
26:'invalid/stale→fault→normalตามcourse; near→afraid,clear→normal;driverwatchdog/E-stopแยกจากFSM',
31:'MCUclient(sensor/driver)→serial→microROSAgent→hostinteraction→commandtopics→Agent→MCUactuator;firmware/Agentยังไม่มีผลทดสอบ',
36:'Latencyจากsourcehardwaretriggerถึงmax(encoder/กล้องmotion,photodiodeRGB);offlineใช้sourcevirtual→appliedcommandแยกจากphysical',
37:'clockร่วมดีที่สุด;ถ้าคนละclockวัดoffset/driftก่อนหลังtrial+residual/resolutionuncertainty;identity/mappingไม่มีให้N/A',
48:plan['question'],49:'Offline22sเป็นtransportprofilecomparisonแยกจากAHM600sproject;ไม่มีผลAHM/human/robotตอนนี้',
50:plan['hypothesis'],
66:'results/completed_20261109/comparison/<C>_rNN/:input_trace,command_trace,events,config,metrics;summary.jsonและmanifest;codeSHAในRUN_MANIFEST',
67:'ReplayC1seed42command/eventsตรงbyteและSHA;analysis_validation.json. Human600slogsแยกplatform/condition/trial/sourceIDs',
68:'คุมseed/inputschedule/policy/bounds/resetเท่ากัน;SHAconfig/source_snapshotกำกับ;realต้องcalibrationIDและclockmappingเพิ่ม',
69:'OfflineC0primary21/21,C1=19/21;C1seed41clear_02และseed42button_02missingไม่แทน0. Fulltablesอยู่worksheet.md',
76:'คง7topicnames/types/units/meaningแล้วสลับsensor/driveradapter;ต้องcalibratejointจริงเพราะabstractradไม่รับรองmechanicalmapping',
78:'ROSbagช่วยตรวจdelivery/replayและเหตุการณ์;ไม่ยืนยันphysicalmotion/RGBหากไม่มีencoder/photodiodeและsourceclockcorrelation',
80:'คงfixture,reset,CPG,gainmapping,safety,transport,measurement;เปลี่ยนhormonememoryอย่างเดียวในproject. เก็บmissingnullและabortedreasonทุกtrial',
83:'แผนหลัง09/11/2026:D1proposalreview,D2code,D3calibration,D4simulation,D5real,D6analysis;วันจริงรอยืนยันทีม',
84:'AHMCPG/ROS/MCU/600s/physicalยังไม่รัน;ต้องตรวจclock,limits,stopและconsentก่อนenable. Proposalรายละเอียดในresults/completed_20261109/proposal.html',
})
for row,topic in zip(d.tables[1].rows[1:],topics):setcell(row.cells[3],topic[3]+'; RELIABLE KEEP_LAST10 VOLATILE')
for row in d.tables[2].rows[1:]:
    setcell(row.cells[1],'RELIABLE / KEEP_LAST depth10');setcell(row.cells[2],'VOLATILE;coursefreshness>.12s→fault;receipt≠acquisition')
fillcol(d.tables[3],['แผนESP32หรือboardที่ผู้สอนยืนยัน;button/touch/range,firmwareยังไม่ทดสอบ','serial→microROSAgent→Ubuntu24.04/Jazzy;ยังไม่รันจริง','source/interaction/outputcollector;AHM/CPGinternalและsidecarlogger','dropoldsequenceในoffline;hardwarewatchdog/reconnectvalidatedneutral;E-stopoperator'])
fillcol(d.tables[4],['source_id+acquisitionsequence/hardwaretrigger;clocksource','receive/decisionlogsมีtrial_id/source_id;clockmapped','simvirtualclock;driverapplylogยังไม่ใช่physical','encoder/กล้องmotion+photodiodeRGBร่วมtrigger;uncertaintyต้องวัด'])
fillcol(d.tables[5],['Project:directR=S vs hormonememoryR=Hเพียงfactorเดียว','peakcommandrate rad/s,recoverytime s,bothlatency sพร้อมmissing','H0=0,o0=[.1,0],FSMnormal;dt,fixture,limits,CPGเท่ากัน','C0directและC1AHMใช้gainmapping/CPGเดียวกัน;transportstudyเป็นคนละexperiment'])
equations=[[plan['AHM_equation'],'prod=.8,clear=.6,bind=.2,dt_h=.05s,H0=0;Lab04course'],[plan['SO2_CPG_equation'],'alpha1.10,phi.20rad/update,dt.02s,o0=.1/0;Lab03course'],[plan['integration_description'],'G=.02+.06Rrad;groupproposed,softwarelimits±.35/.25/.30rad,slew.8rad/s']]
for row,values in zip(d.tables[6].rows[1:],equations):
    for c,v in zip(row.cells[1:],values):setcell(c,v)
for row,values in zip(d.tables[7].rows[1:],[['R=Sdirectไม่มีmemory','sameCPG,gain,FSM,fixture,safety,clock'],['R=HboundedEuler','sameCPG,gain,FSM,fixture,safety,clock']]):
    for c,v in zip(row.cells[1:],values):setcell(c,v)
for row,metric in zip(d.tables[8].rows[1:],plan['metrics'][:2]):
    for c,v in zip(row.cells,[metric['name'],metric['measurement'],metric['unit'],metric['missing_rule']]):setcell(c,v)
scenario=[['0–2.5','button60–70s;neutralก่อน','p_button_060;เก็บsource/output;stopถ้าunsafe'],['2.5–5','touch180–190s','p_touch_180;R/H/o/qและRGB'],['5–7.5','approach300–310;near400–420;clear420','p_approach_300,p_clear_420;nearoverride'],['7.5–10','button540–550sและพัก','p_button_540;recovery;เก็บmiss/abort']]
for row,values in zip(d.tables[9].rows[1:],scenario):
    for c,v in zip(row.cells,values):setcell(c,v)
for row in d.tables[10].rows[1:]:setcell(row.cells[2],'600s/trial;3pairsorderC0C1/C1C0/C0C1;simseeds41–43;realP01pairedsessions;ยังไม่รัน')
fillcol(d.tables[11],['ครบในproposal;coursemodel','ครบสมการ;ยังไม่implementในrunner','AHM→CPGgain','ครบ7topics/QoS','ครบแผน;แยกtransportผลเดิม','ครบแผน600s;ยังไม่มีhuman/robotresult','ครบแผน;ต้องvalidateก่อนจริง','ครบD1–D6;ผู้ตรวจhardwareรอยืนยัน'])
d.save(lab7/'Week07_Student_Worksheet_TH.docx')

for n,b,lab in [(6,out6,lab6),(7,out7,lab7)]:
    write(b/'analysis_validation.json',json.dumps(audit[str(n)],ensure_ascii=False,indent=2))
    readme=lab/'README.md';base=readme.read_text(encoding='utf-8')
    marker='\n## ผลที่ทำเสร็จ 09 พฤศจิกายน 2026\n'
    if marker in base:base=base.split(marker)[0]
    write(readme,base+marker+f'\nเติม student policy และใบงานชื่อเดิมแล้ว; checker baseline/group ผ่าน; C0/C1 conditionละ3pairedseeds41/42/43; replayตรวจbyteและSHAผ่าน\n\nเปิด worksheet.md และ results/completed_20261109/worksheet_answers.html สำหรับคำตอบพร้อมตัวเลข; รายงาน'+(' 2หน้า student_report.html' if n==6 else ' และproposal3หน้า proposal.html / proposal.json')+' อยู่ results/completed_20261109/ ส่วนraw/config/metrics/source snapshotอยู่ comparison/\n\nผลเป็น offline simulation เท่านั้น ROS/DDS,MCU,AHM–CPG600sและhardwareยังไม่ได้รัน; ต้นฉบับก่อนแก้อยู่ archive/completed_20261109/\n')
    files=[p for p in b.rglob('*') if p.is_file() and p.name!='DELIVERY_SHA256.json']+[lab/'worksheet.md',next(lab.glob('*.docx')),lab/'README.md']
    if n==7:files.append(lab/'proposal.json')
    write(b/'DELIVERY_SHA256.json',json.dumps({str(p.relative_to(lab)):sha(p) for p in files},ensure_ascii=False,indent=2))
print('Completed worksheets, reports, proposal, charts, replay/hash validation in original lab folders.')
