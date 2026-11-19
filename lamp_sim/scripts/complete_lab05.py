from pathlib import Path
import subprocess,sys,json,hashlib,datetime,importlib.util
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'C:\Users\ittip\Downloads\RAE67_bio_ins-main');lab=root/'lab_05'
python=root/'.venv/Scripts/python.exe'
base=lab/'results/completed_20261109';out=base;n=2
while out.exists():out=base.with_name(base.name+f'_{n:02}');n+=1
out.mkdir(parents=True)
# Lock predictions before running or opening outcomes. Authorship is explicit.
prediction='''# แผนการทดลองก่อนรัน

จัดทำโดยผู้ช่วยตามคำขอให้ทำLab05ต่อ ไม่ใช่การบันทึกความคิดเดิมของผู้เรียน และเขียนก่อนรันผลชุดนี้

H1: B2 hormone จะมี max-step ของ phi/stride ต่ำกว่า B1 direct แต่ command latency/recovery มากกว่า ไม่คาดว่า TV ต้องลดมากเพราะช่วงการเปลี่ยนแปลงรวมใกล้กัน
H2: B3ตัดเฉพาะbinding term จึงยังมีH state/clearanceและmemory คาดว่าฟื้นช้ากว่าB2และอาจชนเพดานมากขึ้น
H3 phi-only: คงstride=.055 m คาดว่าเปลี่ยนจังหวะfrequency; stride-only: คงphi=.20 rad คาดว่าfrequencyใกล้B0แต่distanceเปลี่ยนในkinematic model ไม่อ้างแรง/พลังงาน
Contact: matched SI1/SIF0; gain-offset SI1แต่MAE>0; all-inverted SI−1แต่SIF0; constant SI=N/A; NaNหนึ่งsampleจะกระทบหลายwindows ไม่แทนN/Aด้วย0

Protocol: dt=.05 s, duration30 s, commonCPGwarmup10 s phi=.20 alpha1.10, initial(.1,0), S0/1/0ที่0/10/20 s ทุกconditionใช้scheduleเดียวกัน ไม่มีrandom independent repetitions
'''
(out/'PREDICTIONS_BEFORE_RUN.md').write_text(prediction,encoding='utf-8')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,str(lab))
student=module('lab04_student_actual',root/'Lab04/source_snapshot/student_hormone.py')
model=module('lab05_course_actual',lab/'course_model.py')
for rates in [(.8,.6,.2),(.8,.6,0)]:
 h=0.
 for i in range(600):
  s=float(200<=i<400) if i!=300 else float('nan')
  a=student.step(h,s,.05,*rates);b=model.hormone_step(h,s,.05,rates)
  for key in ['h','r','raw','p','c','b','fault']:assert a[key]==b[key],(i,key)
  h=a['h']
print('Lab04 student dynamics match Lab05 course dynamics for both rates and fault scenario.')
commands=[]
jobs=[('comparison',['--condition','all','--profile','step','--mapping','both']),('phi_only',['--mapping','phi-only']),('stride_only',['--mapping','stride-only']),('zero',['--condition','B2','--profile','zero']),('one',['--condition','B2','--profile','one']),('spike',['--condition','B2','--profile','spike']),('fault',['--condition','all','--profile','fault'])]
for label,args in jobs:
 cmd=[str(python),'lab05.py',*args,'--output-dir',str(out/label)]
 commands.append(cmd)
 p=subprocess.run(cmd,cwd=lab,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(label+'_run.txt')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 print('Completed '+label)
cmd=[str(python),'contact_demo.py','--output-dir',str(out/'contact')];commands.append(cmd)
p=subprocess.run(cmd,cwd=lab,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/'contact_run.txt').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
if p.returncode:raise RuntimeError(p.stdout+p.stderr)
# Verify actual handoff from preceding Lab04, not a replacement local contract.
contract=root/'Lab04/source_snapshot/handoff_contract.json'
cmd=[str(python),'lab05.py','--condition','B2','--contract',str(contract),'--output-dir',str(out/'lab04_handoff')];commands.append(cmd)
p=subprocess.run(cmd,cwd=lab,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/'handoff_run.txt').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
if p.returncode:raise RuntimeError(p.stdout+p.stderr)
manifest={'created':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),'python_version':subprocess.check_output([str(python),'--version'],text=True).strip(),'commands':commands,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in lab.iterdir() if p.is_file()},'lab04_controller_sha256':hashlib.sha256((root/'Lab04/source_snapshot/student_hormone.py').read_bytes()).hexdigest(),'lab04_contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),'lab04_agreement':'600 sequential updates with stimulus step and one NaN; rates B2/B3; all h/r/raw/p/c/b/fault equal','prediction_sha256':hashlib.sha256((out/'PREDICTIONS_BEFORE_RUN.md').read_bytes()).hexdigest()}
(out/'RUN_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
Path(r'C:\Users\ittip\Documents\ChatGPT\lamp\lab05_result_path.txt').write_text(str(out),encoding='utf-8')
print('RESULT_PATH='+str(out))
print(json.dumps(json.loads((out/'comparison/metrics.json').read_text()),indent=2))
