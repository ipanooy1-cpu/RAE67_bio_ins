from pathlib import Path
import csv,json,math,hashlib,sys,importlib.util,shutil,html,zipfile
sys.stdout.reconfigure(encoding='utf-8')
r=Path(Path(r'C:\Users\ittip\Documents\ChatGPT\lamp\lab05_result_path.txt').read_text());lab=r.parent.parent
checks=[]
def j(p):return json.loads((r/p).read_text(encoding='utf-8'))
def rows(folder,file):
 with (r/folder/file).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def near(a,b):assert math.isclose(float(a),b,abs_tol=1e-10),(a,b)
def at(a,k,t):return next(x for x in a if abs(float(x[k])-t)<1e-9)
# Verify all runner manifests before adding our report files.
for d in [p for p in r.iterdir() if p.is_dir()]:
 manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
 for name,h in manifest.items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==h,(d,name)
checks.append('All 9 runner/contact manifests verify against exact file SHA256')
m=j('comparison/metrics.json');contact=j('contact/metrics.json');config=j('comparison/config.json')
initials=list(config['initial_states'].values());assert all((a['o1'],a['o2'])==(initials[0]['o1'],initials[0]['o2']) for a in initials)
for c in m:
 states=rows('comparison',c+'_states.csv');intervals=rows('comparison',c+'_intervals.csv')
 assert len(states)==601 and len(intervals)==600
 assert sum(float(x['stimulus'])==1 for x in intervals)==200
 near(sum(x['distance_m'] for x in m[c]['segments'].values()),m[c]['distance_m'])
 assert all(.1<=float(x['phi_rad'])<=.45 and .04<=float(x['stride_half_m'])<=.07 for x in intervals)
 for field in ['paper_stability','paper_harmony','paper_displacement']:assert m[c][field] is None
checks.append('601 states/600 intervals per condition; common warmup, schedules, bounded commands, segment-distance additivity and N/A paper metrics verified')
intervals=rows('comparison','B2_intervals.csv');states=rows('comparison','B2_states.csv')
a=at(intervals,'command_time_s',10);b=at(intervals,'command_time_s',10.05)
near(a['r_used'],0);near(a['h_state_end'],.04);near(a['phi_rad'],.2);near(b['phi_rad'],.208);near(b['h_state_end'],.0784)
checks.append('B2 pre-state command scheduling at10.00/10.05 and end-state hormone updates verified')
for mode,fixed,key in [('phi_only',.055,'stride_half_m'),('stride_only',.20,'phi_rad')]:
 for c in m:assert all(math.isclose(float(x[key]),fixed,abs_tol=1e-12) for x in rows(mode,c+'_intervals.csv'))
checks.append('Both one-factor runs keep their declared fixed parameter unchanged in every interval')
for c in m:
 a=at(rows('fault',c+'_intervals.csv'),'command_time_s',15)
 assert int(a['fault'])==1;near(a['r_used'],0);near(a['phi_rad'],.2);near(a['stride_half_m'],.055)
 if c in ['B2','B3']:near(a['h_used'],0);near(a['h_state_end'],0)
fs=rows('fault','B2_states.csv');near(at(fs,'state_time_s',15.05)['h'],0);near(at(fs,'state_time_s',15.1)['h'],.04)
checks.append('Fault fallback applied before command at15.00 for all4conditions, B2/B3 reset and subsequent recovery verified')
assert all(float(x['h'])==0 for x in rows('zero','B2_states.csv'))
assert sum(float(x['stimulus'])==1 for x in rows('spike','B2_intervals.csv'))==1
assert all(0<=float(x['h'])<=1 for x in rows('one','B2_states.csv'))
checks.append('Zero, one and single-interval spike verified')
fr=rows('contact','fault.csv');invalid=[x for x in fr[49:] if x['sif']=='']
assert len(invalid)==50;near(invalid[0]['sample_time_s'],15);near(invalid[-1]['sample_time_s'],17.45)
assert all(x['sif']=='' for x in rows('contact','constant.csv'))
near(contact['matched']['first_valid_sample_s'],2.45)
near(contact['all-inverted']['mean_si']['LF'],-1)
assert abs(contact['all-inverted']['mean_sif'])<1e-12
near(float(rows('contact','all-inverted.csv')[49]['release_eq1_ci1']),.5)
checks.append('Contact: first valid2.45 s, constantN/A, all-inverted SI−1/SIF≈0/release.5 and exactly50 fault-contaminated rows verified')
assert rows('lab04_handoff','B2_states.csv')==states and rows('lab04_handoff','B2_intervals.csv')==intervals
checks.append('Actual Lab04 handoff contract reproduces default B2 raw states and intervals exactly')
# Repeat in memory from unchanged course scaffold, compare deterministic metrics.
sys.path.insert(0,str(lab));import lab05 as runner
contract_data=runner.load_contract(lab/'handoff_contract.json')
for c in m:
 ss,ii,initial=runner.simulate(c,'step','both',30,10,contract_data)
 assert runner.metrics(ss,ii,c,'step','both',contract_data)==m[c]
checks.append('Full B0-B3 deterministic metrics reproduce exactly on a second run')
(r/'VERIFICATION.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
f=lambda x:'N/A' if x is None else f'{x:.6f}'
def table(headers,data):return '| '+' | '.join(headers)+' |\n|'+'---|'*len(headers)+'\n'+''.join('| '+' | '.join(str(v) for v in row)+' |\n' for row in data)
main_table=table(['Condition','TV phi rad','maxΔphi rad/step','TV stride m','cmd latency s','cmd recovery s','on frequency Hz','on distance m'],[[c,*[f(m[c][k]) for k in ['phi_total_variation_rad','phi_max_step_rad','stride_total_variation_m','command_latency_s','command_recovery_s']],f(m[c]['segments']['on']['frequency_hz']),f(m[c]['segments']['on']['distance_m'])] for c in m])
time_table=table(['command/input s','state end s','H_start','H_end','R_used','phi rad','stride_half m'],[[f(float(x[k])) for k in ['command_time_s','state_time_s','h_state_start','h_state_end','r_used','phi_rad','stride_half_m']] for x in [at(intervals,'command_time_s',t) for t in [10,10.05,20]]])
one_rows=[]
for mode in ['comparison','phi_only','stride_only']:
 mm=j(mode+'/metrics.json')
 for c in ['B1','B2']:one_rows.append([mode,c,f(mm[c]['segments']['on']['frequency_hz']),f(mm[c]['segments']['on']['distance_m']),f(mm[c]['distance_m'])])
one_table=table(['Mapping','Condition','on frequency Hz','on distance m','total distance m'],one_rows)
contact_table=table(['Case','Mean SI LF','Mean SI RF','Mean SIF','MAE','valid SIF rows /600'],[[case,f(x['mean_si']['LF']),f(x['mean_si']['RF']),f(x['mean_sif']),f(x['mean_absolute_error']),str(x['valid_sif_rows'])+'/600'] for case,x in contact.items()])
identity='ชื่อ/รหัส อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม __________ | วันที่ทดลอง 09/11/2026'
architecture='''```text
Scheduled stimulus S → fixed/direct/hormone controller → R_used
    → bounded phi/stride → SO(2) CPG → tripod decoder → kinematic body
```
Main runner ไม่มี independent sensory feedback จาก terrain/body กลับเข้าcontroller contactในdecoderมาจากsign(o2)เอง ส่วนcontact demoเป็นการทดลองสังเคราะห์แยก ไม่ป้อนกลับไปสร้างฮอร์โมน
'''
provenance=table(['ประเภท','ตัวอย่างและสถานะ'],[
['Source equation','SIF เป็น populationSDของ6SI และ release=CI/(1+exp(−SIF)), CI=1 ตาม paper Eqs.(1)–(2)'],
['Proposed course equation','Euler H_new=clamp(H+dt(k_prod S−k_clear H−k_bind R),0,1); affine phi/stride; paired-product Pearson ของdemo'],
['Expected vs measured proxy','expected sine1Hz เทียบ synthetic actual contact-proxy; ไม่ใช่force sensorหรือfeedbackฮาร์ดแวร์'],
['วัดไม่ได้','Stability/Harmony/Displacement ตามpaperเป็นN/A; ไม่มีdynamics/sensorindices/normalizationที่ตรงนิยาม']])
intro='Lab05เป็นworking scaffoldเชื่อม hormone→SO(2)CPG→kinematic walking ไม่โหลดstudent codeโดยตรง ผู้ช่วยตรวจเทียบhormone_stepกับstudent_hormone.pyจากLab04ที่ย้ายไว้แล้ว ครบ600updatesรวมfaultและratesB2/B3ให้ผลh/r/raw/p/c/b/faultตรงกันทุกค่า ไม่แก้sourceของLab04หรือLab05'
interpret='B2ลด maxΔphi จากB1 .200000 เป็น .008000 rad/step (ลด96%) และ maxΔstride จาก.010000เป็น.000400 m/step แต่ command latencyเพิ่ม0→.15 s และrecovery0→2.85 s สนับสนุนhypothesisด้านความค่อยเป็นค่อยไป ไม่ใช่การรับรองความเร่ง/แรงหรือความปลอดภัยมอเตอร์ TVphiยังใกล้กัน .400000กับ.399827 rad จึงไม่สนับสนุนคำกล่าวว่าhormoneต้องลดTVอย่างมาก B3ไม่มีbindingแต่ยังมีH state/clearance จึงมีmemoryและrecovery3.80 s ช้ากว่าB2 .95 s'
limitations='Boundsเหมือนกันไม่ได้ทำให้amplitudeเท่ากัน B0 peakR_used=0, B1=1, B2=.999715, B3=1; phi peakตามลำดับ .20/.40/.399943/.40 rad และไม่มีcommandclampทั้ง4condition จำนวนsupportlegs=3มาจากdecoder ไม่พิสูจน์stability/ไม่ล้ม TVไม่ใช่Harmony และdistanceที่วัดไม่ใช่paperDisplacement การแบ่งpre/on/offสำคัญเพราะมีtransient: B2frequencypre=.624878,on=1.202760,off=.698234 Hz ไม่ควรแทนด้วยค่าเฉลี่ย30sและเรียกทุกช่วงsteady state ไม่มีforce/mass/friction/CoM/energyหรือterrainfeedback'
contact_text='gain-offset: SI≈1แม้MAE=.162844 เพราะPearsonไม่ไวต่อpositive scaleและoffset; all-inverted: SI≈−1ทุกขาแต่populationSD≈0และrelease=.5เหมือนmatched เป็นcommon-mode blind spot; mixed-delay: LF/RM/LH≈1 ส่วนRF/LM/RH≈0และSIF≈.499995; constant: variance0จึงSI/SIF/release=N/A ไม่ใช่0 แม้MAE=0; faultที่15.00กระทบ50rollingwindowsช่วง15.00–17.45 s ไม่นับstartup49rows รวมunavailable99rows และกลับvalid17.50 s ทั้งนี้Pearsonเป็นproposed course definitionที่ประกาศชัด ไม่ใช่การอ้างว่าimplement Eq.(3)ของpaperตรงตามพิมพ์ และยังไม่ต่อCg/HR/MI_H'
fault_text='ในfaultprofile ทุกconditionfallbackก่อนCPG updateที่command15.00 s: fault1,R_used0,phi=.20 rad,stride=.055 m สำหรับB2 H_used=0,state15.05 H=0 และstate15.10 H=.04หลังinputกลับปกติ ไม่freezeตัวกรอง เป็นsoftwarefallback ไม่ใช่actuatorlimits/watchdog/E-stop'
# Graphs derived directly from raw CSV, no third-party library.
fig=r/'figures';fig.mkdir()
def svg(name,title,kind):
 colors=['#526476','#087e8b','#c56a16','#8b51a7'];w=1000;h=340;left=75;top=38;pw=890;ph=235
 data=[]
 for c in m:
  rr=rows('comparison',c+('_intervals.csv' if kind=='phi_rad' else '_states.csv'))
  tx='command_time_s' if kind=='phi_rad' else 'state_time_s';data.append((c,[(float(x[tx]),float(x[kind])) for x in rr]))
 low,high=(.18,.42) if kind=='phi_rad' else (0,3.6)
 p=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img"><title>{title}</title><rect width="100%" height="100%" fill="white"/>',f'<text x="75" y="24" font-size="18">{title}</text>',f'<rect x="{left+pw/3}" y="{top}" width="{pw/3}" height="{ph}" fill="#edf5f4"/>']
 for i in range(5):
  yy=top+ph-i*ph/4;val=low+(high-low)*i/4
  p.append(f'<path d="M{left},{yy}h{pw}" stroke="#ddd"/><text x="12" y="{yy+5}" font-size="13">{val:.2f}</text>')
 for t in range(0,31,5):p.append(f'<text x="{left+t/30*pw-5}" y="{top+ph+22}" font-size="13">{t}</text>')
 for i,(c,points) in enumerate(data):
  coords=' '.join(f'{left+t/30*pw:.2f},{top+ph-(v-low)/(high-low)*ph:.2f}' for t,v in points)
  p.extend([f'<polyline points="{coords}" fill="none" stroke="{colors[i]}" stroke-width="2.2"/>',f'<text x="{80+190*i}" y="330" fill="{colors[i]}" font-size="16">{c}</text>'])
 p.append('<text x="850" y="310" font-size="13">time (s)</text></svg>');(fig/name).write_text(''.join(p),encoding='utf-8')
svg('phi_commands.svg','Command phi (rad) from raw interval CSV','phi_rad')
svg('body_distance.svg','Body position (m), kinematic model only','body_x_m')
worksheet='# ใบงาน Lab05 ฉบับกรอกผลจริง\n\n'+identity+'\n\n'+intro+'''

## 1 ก่อนรัน hypothesis และ architecture

ดูPREDICTIONS_BEFORE_RUN.md บันทึกโดยผู้ช่วยก่อนรัน ไม่ใช่การอ้างว่าเป็นpredictionที่ผู้เรียนเขียนเอง H1:B2 max-stepต่ำกว่าB1แต่latency/recoveryสูงกว่า; H2:B3ยังมีmemoryและฟื้นช้ากว่าB2; H3:phi-onlyเปลี่ยนจังหวะ ส่วนstride-onlyคงfrequencyแต่เปลี่ยนระยะในmodel

'''+architecture+'\n'+provenance+'''

## 2 Comparison และ timing

'''+time_table+'''
B1command10.00ใช้S=1ทันทีจึงlatency0 s ส่วนstateหลังupdateเริ่ม10.05จึงstate latency.05 s เป็นnumerical scheduling ไม่ใช่hardware latency B2ใช้Rจากstateต้นช่วง จึงcommand10.00ยังbaselineและcommand10.05จึงphi=.208

config.jsonทุกcondition warmup10 s/200steps phi=.20 alpha1.10 จาก(.10,0) ได้initialo1=−.026965330782974153,o2=−.5608626776309884เหมือนกัน resetH/R/body origin/footanchors/log หลังwarmupแต่คงoscillatorไว้

## 3 ผลเปรียบเทียบ

'''+main_table+'\n'+interpret+'\n\n'+limitations+'''

## 4 One-factor และ fault

ก่อนรันประกาศว่าจะทำทั้งphi-onlyและstride-onlyโดยคงdt/alpha/warmup/schedule/decoderเหมือนเดิม metricหลักคือonfrequency/ondistance/max-step ตรวจCSVแล้วphi-onlyทุกintervalstride=.055 และstride-onlyทุกintervalphi=.20

'''+one_table+'''
stride-only B1/B2 onfrequency=.624877 HzเหมือนB0 แต่ondistance=.914717/.901666 mสูงกว่าB0 .778743 m ส่วนphi-only onfrequencyของB1/B2เท่ากับbothที่1.268366/1.202760 Hz แต่ondistanceน้อยกว่าboth เพราะไม่มีการเพิ่มstride ข้อสรุปเชิงสาเหตุจำกัดในแบบจำลองนี้ไม่อ้างterrainหรือphysicalperformance

'''+fault_text+'''

Extremeเพิ่มเติม: zero B2H=0ตลอด; oneHอยู่ในboundsตลอด; spikeS=1เพียงinterval10.00 s; non-step timingmetricsเป็นN/Aตามนิยาม ไม่แทนด้วย0

## 5 Contact mini-lab

'''+contact_table+'\n'+contact_text+'''

## 6 สรุปส่งงานและ exit ticket

Claimที่ข้อมูลรองรับ: ภายใต้step scheduleนี้ hormone B2ลดmax-stepของคำสั่งphi96%จาก.20เป็น.008rad/step แลกcommandlatency.15sและrecovery2.85s อ้างcomparison/metrics.json

Claimที่ยังรองรับไม่ได้: หุ่นยนต์เดินไม่ล้มหรือใช้พลังงานน้อยลง ต้องเพิ่มbodydynamics/IMU/CoM/forces/motorcurrentและhardware trialsก่อน ไม่มีpaperStability/Harmony/Displacementที่วัดได้ในชุดนี้

ใช้PythonversionและsourcehashตามRUN_MANIFEST.json ผลซ้ำdeterministicไม่ใช่independenttrials และไม่ได้สร้างlearningจากประสบการณ์ ทุกค่าตัวเลขในตารางปัด6ตำแหน่ง เก็บค่าดิบเต็มในCSV/JSON

Checklist: comparison+onefactor+fault raw/config/manifestครบ; contactmetrics/CSVครบ6cases; ตารางtimingและmetricsครบ; staticกราฟ2รูปในfigures; interactive reportทุกrun; snapshotsและคำสั่งรันซ้ำครบ ผู้เรียนยังต้องเติมกลุ่ม อ่านอธิบายผล และตรวจชื่อก่อนส่ง

อ้างอิง: README.md, worksheet.md และSOURCES.mdของLab05; Ngamkajornwiwat et al.(2020), DOI10.1109/ACCESS.2020.2992794ตามที่SOURCESอธิบาย ใช้แนวคิดและsource-equationที่ระบุ ไม่อ้างreproductionของpaper
'''
(r/'WORKSHEET_COMPLETED_TH.md').write_text(worksheet,encoding='utf-8')
report='# รายงาน Lab05 Hormone SO2 CPG และ Kinematic Walking\n\n'+identity+'\n\n'+intro+'\n\n## วัตถุประสงค์และสถาปัตยกรรม\n\n'+architecture+'\n'+provenance+'\n\n## Protocol และเวลา\n\ndt=.05 s,duration30 s,warmup10 s,alpha1.10,lift.03 m,initial(.1,0); S0/1/0ที่0/10/20 s ทุกconditionใช้scheduleและwarmupร่วมกัน 601states/600intervals ไม่มีrandomnoise\n\n'+time_table+'\nB1commandlatency0แต่statelatency.05 s ส่วนB2ใช้Hต้นช่วงจึงcommand10.05ใช้H=.04 บันทึกHปลายช่วง=.0784 ไม่ใช่physical latency\n\n## ผลและข้อค้นพบ\n\n'+main_table+'\n'+interpret+'\n\n'+one_table+'\n'+limitations+'\n\n## Fault และcontact\n\n'+fault_text+'\n\n'+contact_table+'\n'+contact_text+'\n\n## ข้อสรุปและทำซ้ำ\n\nหลักฐานรองรับการลดmax-stepของคำสั่ง แต่ไม่ยืนยันstability/energy/hardware safety รายละเอียดคำตอบครบทุกข้ออยู่WORKSHEET_COMPLETED_TH.md; Pythonversion/commands/hashอยู่RUN_MANIFEST.json; คำสั่งทำซ้ำREADME_REPRODUCE.md; แผนก่อนรันPREDICTIONS_BEFORE_RUN.md; หลักฐานตรวจVERIFICATION.txt\n\nอ้างอิง README/worksheet/SOURCES ของLab05 และNgamkajornwiwat et al.(2020) DOI10.1109/ACCESS.2020.2992794 ตามขอบเขตproposed course model\n'
(r/'REPORT_TH.md').write_text(report,encoding='utf-8')
# Include complete portable source plus the preceding student controller as provenance.
snap=r/'reproduce_source';snap.mkdir()
for p in lab.iterdir():
 if p.is_file():shutil.copy2(p,snap/p.name)
shutil.copy2(lab.parent/'Lab04/source_snapshot/student_hormone.py',snap/'lab04_student_hormone.py')
repro='''# วิธีเปิดผลและรันซ้ำ Lab05

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
'''
(r/'README_REPRODUCE.md').write_text(repro,encoding='utf-8')
# Simple HTML report, preserving tables and linking actual figures. Printing is user-controlled.
def md_html(text):
 lines=text.splitlines();out=[];in_table=False;in_code=False
 for line in lines:
  if line.startswith('```'):
   if in_table:out.append('</table>');in_table=False
   out.append('</pre>' if in_code else '<pre>');in_code=not in_code;continue
  if in_code:out.append(html.escape(line)+'\n');continue
  if line.startswith('|'):
   if set(line.replace('|','').strip())<=set('-: '):continue
   cells=[x.strip() for x in line.strip('|').split('|')]
   tag='td' if in_table else 'th'
   if not in_table:out.append('<table>');in_table=True
   out.append('<tr>'+''.join(f'<{tag}>{html.escape(c)}</{tag}>' for c in cells)+'</tr>');continue
  if in_table:out.append('</table>');in_table=False
  if line.startswith('# '):out.append('<h1>'+html.escape(line[2:])+'</h1>')
  elif line.startswith('## '):out.append('<h2>'+html.escape(line[3:])+'</h2>')
  elif line:out.append('<p>'+html.escape(line)+'</p>')
 if in_table:out.append('</table>')
 return ''.join(out)
style='''@page{size:A4;margin:15mm}body{font:11pt/1.55 Tahoma,"Leelawadee UI",sans-serif;color:#18252c;max-width:1050px;margin:30px auto;padding:0 15px}h1{font-size:19pt}h2{font-size:13pt;margin-top:20px;break-after:avoid}table{border-collapse:collapse;width:100%;font-size:8.5pt;margin:12px 0}th,td{border:1px solid #b7c4ca;padding:6px;text-align:left}th{background:#edf2f4}tr{break-inside:avoid}pre{font:10pt/1.4 Consolas,monospace;white-space:pre-wrap}img{width:100%;max-height:280px;object-fit:contain}p{margin:9px 0}a{color:#17677d}@media print{body{margin:0;padding:0;max-width:none;font-size:10pt}table{font-size:8pt}img{max-height:180px}}'''
body=md_html(report)
body=body.replace('<h2>ผลและข้อค้นพบ</h2>','<h2>ผลและข้อค้นพบ</h2><img src="figures/phi_commands.svg" alt="Command phi from raw CSV"><img src="figures/body_distance.svg" alt="Kinematic body position from raw CSV">')
(r/'REPORT_TH.html').write_text('<!doctype html><html lang="th"><meta charset="utf-8"><title>Lab05 Report</title><style>'+style+'</style><p><a href="comparison/report.html">Interactive comparison</a> · <a href="contact/report.html">Contact report</a></p>'+body+'</html>',encoding='utf-8')
print('Completed worksheet, report, two raw-data SVG charts and portable reproduction sources.')
print('\n'.join(checks))
