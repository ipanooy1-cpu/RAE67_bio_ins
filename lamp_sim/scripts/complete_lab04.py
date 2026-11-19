"""Run the student's Lab04 without replacing any previous experiment outputs."""
from pathlib import Path
import subprocess, sys, json, hashlib, datetime, csv, shutil
sys.stdout.reconfigure(encoding='utf-8')
lab=Path(r'C:\Users\ittip\Downloads\RAE67_bio_ins-main\lab_04')
python=lab.parent/'.venv/Scripts/python.exe'
base=lab/'results'/'completed_20261109'
run=base
n=2
while run.exists():
 run=base.with_name(base.name+f'_{n:02}')
 n+=1
run.mkdir(parents=True)
commands=[]
def execute(args, log):
 commands.append([str(python),*args])
 result=subprocess.run([str(python),*args],cwd=lab,capture_output=True,text=True,encoding='utf-8',errors='replace')
 (run/log).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 if result.returncode: raise RuntimeError(f'{log} failed: {result.stderr} {result.stdout}')
 return result.stdout
checker=json.loads(execute(['check_submission.py','--student-file','student_hormone.py'],'checker.txt'))
assert len(checker)==13 and all(r['passed'] for r in checker)
for profile in ['step','zero','one','spike','fault']:
 name='comparison' if profile=='step' else profile
 execute(['lab04.py','--controller-source','student','--condition','all' if profile=='step' else 'C1','--profile',profile,'--output-dir',str(run/name)],name+'_run.txt')
contract=lab.parent/'lab_03/results/week4_bridge/handoff_contract.json'
execute(['lab04.py','--controller-source','student','--condition','C1','--profile','step','--contract',str(contract),'--output-dir',str(run/'week03_handoff')],'handoff_run.txt')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=lab,text=True).strip()
status=subprocess.check_output(['git','status','--short'],cwd=lab,text=True)
manifest={'created_local':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),'code_commit':head,'git_status_at_run':status,'commands':commands,'source_sha256':{p:hashlib.sha256((lab/p).read_bytes()).hexdigest() for p in ['student_hormone.py','lab04.py','check_submission.py','handoff_contract.json']},'week03_contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest()}
(run/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
snapshot=run/'source_snapshot';snapshot.mkdir()
for name in ['student_hormone.py','lab04.py','check_submission.py','handoff_contract.json','README.md','worksheet.md']:
 shutil.copy2(lab/name,snapshot/name)
shutil.copy2(contract,snapshot/'week03_handoff_contract.json')
metrics=json.loads((run/'comparison/metrics.json').read_text(encoding='utf-8'))
print('RESULT_PATH='+str(run))
print(json.dumps(metrics,indent=2))
