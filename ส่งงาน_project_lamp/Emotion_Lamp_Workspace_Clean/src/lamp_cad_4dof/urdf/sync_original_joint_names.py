#!/usr/bin/env python3
"""Optional: use original lamp_description joint names if exactly 4 revolutes are found."""
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
p=Path('/workspace/src/lamp_description/urdf/lamp.urdf.xacro')
if not p.exists():
    sys.exit(f'Original xacro not found: {p}')
res=subprocess.run(['xacro',str(p)], capture_output=True,text=True)
if res.returncode:
    sys.exit('xacro could not parse original description: '+res.stderr[-1200:])
root=ET.fromstring(res.stdout)
joints=[j for j in root.findall('joint') if j.get('type') in ('revolute','continuous')]
if len(joints)!=4:
    sys.exit(f'Expected exactly 4 movable joints; found {len(joints)}. No changes made.')
# Walk the kinematic chain, starting with joint whose parent is not child of any movable joint.
children={j.find('child').get('link') for j in joints}
roots=[j for j in joints if j.find('parent').get('link') not in children]
if len(roots)!=1:
    sys.exit('Ambiguous original chain order; no changes made.')
ordered=[roots[0]]
for i in range(3):
    cur=ordered[-1].find('child').get('link')
    nexts=[j for j in joints if j.find('parent').get('link')==cur]
    if len(nexts)!=1:
        sys.exit('Original joints are not a 4-joint serial chain; no changes made.')
    ordered+=nexts
names=[j.get('name') for j in ordered]
c=Path(__file__).with_name('joint_pivots.json')
d=json.loads(c.read_text())
for j,name in zip(d['joints'],names):j['name']=name
c.write_text(json.dumps(d,ensure_ascii=False,indent=2))
subprocess.run([sys.executable,str(Path(__file__).with_name('build_urdf.py'))],check=True)
print('Synchronized joint names:',names)
