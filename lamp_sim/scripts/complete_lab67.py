from pathlib import Path
import subprocess,json,hashlib,datetime,shutil,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'C:\Users\ittip\Downloads\RAE67_bio_ins-main');py=root/'.venv/Scripts/python.exe'
baseplans={}
policy='''"""Lab06/07 completed baseline FSM; proposed course model, no learning.
Safety and output limits remain in the original course engine.
"""
def transition(current_state: str, event: str) -> str | None:
    # Safety events override all other transitions, including afraid guard.
    if event == "fault":
        return "normal"
    if event == "near":
        return "afraid"
    if event == "clear":
        return "normal"
    # Do not leave danger state on a delayed positive interaction.
    if current_state == "afraid":
        return None
    if event == "touch":
        return "happy"
    if event in ("button", "approach"):
        return "interested"
    if event == "timeout" and current_state in ("interested", "happy"):
        return "normal"
    if event == "idle" and current_state == "normal":
        return "sleepy"
    return None
'''
expected=['button_01','touch_01','approach_01','clear_01','near_01','clear_02','button_02']
for number in [6,7]:
 lab=root/f'lab_0{number}';out=lab/'results/completed_20261109';n=2
 while out.exists():out=lab/f'results/completed_20261109_{n:02}';n+=1
 out.mkdir(parents=True);backup=lab/'archive'/out.name;backup.mkdir(parents=True)
 for p in lab.iterdir():
  if p.is_file():shutil.copy2(p,backup/p.name)
 if number==7:shutil.copytree(lab/'lamp_week07',backup/'lamp_week07',ignore=shutil.ignore_patterns('__pycache__'))
 pred={'author':'assistant prepared before execution; not attributed to student unaided work','date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),'expected_input_ids_before_run':expected,'contract':'baseline, also checked group','deadline_s':1,'observation_window_s':22,'hypothesis':('C1 debounce/hysteresis reduces noise-driven transitions but adds recognition delay; all10sources retained; positive7 expected both outputs; conflict touch and already-neutral fault may have no new onset' if number==6 else 'C1 composite modeled jitter+drop increases transport age and may increase latency/missing/fault versus ideal C0; cannot separate effects of jitter and drop; not ROS or physical latency'),'controls':'same completed baseline policy, sources paired seeds41/42/43,dt.02,duration22,scheduler.04,bounds/slew/fallback unchanged'}
 (out/'PREDICTION_BEFORE_RUN.json').write_text(json.dumps(pred,ensure_ascii=False,indent=2),encoding='utf-8')
 commands=[]
 def run(args,label,allow_fail=False):
  cmd=[str(py),*args];commands.append(cmd)
  p=subprocess.run(cmd,cwd=lab,capture_output=True,text=True,encoding='utf-8',errors='replace')
  (out/(label+'.txt')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
  if p.returncode and not allow_fail:raise RuntimeError(label+': '+p.stdout+p.stderr)
  return p
 before=run(['check_submission.py'],'checker_before',True)
 target=lab/('student_policy.py' if number==6 else 'lamp_week07/student_policy.py')
 target.write_text(policy,encoding='utf-8')
 run(['check_submission.py'],'checker_baseline')
 run(['check_submission.py','--contract','group'],'checker_group')
 if number==6:
  run(['lab06.py','--policy','student','--condition','all','--repeats','3','--output-dir',str(out/'comparison')],'comparison_run')
  run(['lab06.py','--policy','student','--condition','C1','--repeats','1','--replay',str(out/'comparison/inputs_r01.csv'),'--output-dir',str(out/'replay')],'replay_run')
 else:
  run(['offline_lab.py','--condition','all','--repeats','3','--output-dir',str(out/'comparison')],'comparison_run')
  run(['offline_lab.py','--condition','C1','--repeats','1','--replay',str(out/'comparison/C1_r02/input_trace.csv'),'--output-dir',str(out/'replay')],'replay_run')
 manifest={'created':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),'python_version':subprocess.check_output([str(py),'--version'],text=True).strip(),'commands':commands,'policy_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'hardware_status':'not executed; ROS2/DDS and physical latency N/A','source_before_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in backup.iterdir() if p.is_file()},'outcome_status':'offline only; hardware plans are not experimental results'}
 (out/'RUN_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 baseplans[str(number)]=str(out)
 print('Lab',number,'completed offline:',out)
Path(r'C:\Users\ittip\Documents\ChatGPT\lamp\lab67_paths.json').write_text(json.dumps(baseplans),encoding='utf-8')
