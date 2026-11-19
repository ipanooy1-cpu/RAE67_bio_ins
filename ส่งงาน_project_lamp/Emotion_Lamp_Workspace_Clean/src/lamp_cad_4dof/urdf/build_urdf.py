#!/usr/bin/env python3
"""Regenerate URDF after editing joint_pivots.json (ROS metres) or names."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

HERE=Path(__file__).resolve().parent
CONFIG=HERE/'joint_pivots.json'
OUT=HERE/'lamp_cad_4dof.urdf'
LINKS=['base_link','base2_link','arm1_link','arm3_link','head2_link']
MESHES=['base1_fixed','base2_yaw','arm1_shoulder','arm3_elbow','head2_pitch']
COLORS=['0.72 0.76 0.85 1','0.52 0.77 0.93 1','0.97 0.74 0.44 1','0.56 0.85 0.71 1','0.84 0.59 0.86 1']

def xyz(v):return ' '.join(f'{float(x):.6f}' for x in v)

def generate():
    d=json.loads(CONFIG.read_text())
    joints=d['joints']
    pivots=[[0.,0.,0.]]+[j['pivot_ros_m'] for j in joints]
    zero_xyz=d['cad_frame_to_ros']['xyz_m']
    world=ET.Element('robot',{'name':'lamp_cad_4dof'})
    for i,name in enumerate(LINKS):
        link=ET.SubElement(world,'link',{'name':name})
        visual=ET.SubElement(link,'visual')
        delta=[zero_xyz[k]-pivots[i][k] for k in range(3)]
        ET.SubElement(visual,'origin',{'xyz':xyz(delta),'rpy':'3.141592653589793 0 0'})
        geo=ET.SubElement(visual,'geometry')
        ET.SubElement(geo,'mesh',{'filename':f'package://lamp_cad_4dof/meshes/{MESHES[i]}.stl','scale':'0.001 0.001 0.001'})
        material=ET.SubElement(visual,'material',{'name':'cad_group_'+str(i)})
        ET.SubElement(material,'color',{'rgba':COLORS[i]})
    for idx,j in enumerate(joints):
        el=ET.SubElement(world,'joint',{'name':j['name'],'type':'revolute'})
        delta=[pivots[idx+1][k]-pivots[idx][k] for k in range(3)]
        ET.SubElement(el,'origin',{'xyz':xyz(delta),'rpy':'0 0 0'})
        ET.SubElement(el,'parent',{'link':LINKS[idx]})
        ET.SubElement(el,'child',{'link':LINKS[idx+1]})
        ET.SubElement(el,'axis',{'xyz':j['axis']})
        lo,hi=j['limits_rad']
        ET.SubElement(el,'limit',{'lower':str(lo),'upper':str(hi),'effort':'1.0','velocity':'1.0'})
    ET.indent(world,'  ')
    OUT.write_text('<?xml version="1.0"?>\n'+ET.tostring(world,encoding='unicode')+'\n')
    print(f'Generated: {OUT}')
    print('Joint names:', ', '.join(j['name'] for j in joints))

if __name__=='__main__':generate()
