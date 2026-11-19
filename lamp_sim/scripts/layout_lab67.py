from pathlib import Path
import json, math, re
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
from PIL import Image,ImageDraw,ImageFont
paths=json.loads(Path('lab67_paths.json').read_text())
font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',25)
small=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',20)
def arrow(d,a,b,label=''):
    d.line([a,b],fill='#555555',width=3);ang=math.atan2(b[1]-a[1],b[0]-a[0])
    pts=[b, (b[0]-14*math.cos(ang-.4),b[1]-14*math.sin(ang-.4)),(b[0]-14*math.cos(ang+.4),b[1]-14*math.sin(ang+.4))];d.polygon(pts,fill='#555555')
    if label:d.text(((a[0]+b[0])/2-40,(a[1]+b[1])/2-24),label,font=small,fill='black')
def box(d,xy,text):
    d.rounded_rectangle(xy,radius=12,fill='#eaf0f5',outline='#47627a',width=2)
    d.multiline_text((xy[0]+15,xy[1]+15),text,font=font,fill='black',spacing=8)
for n in [6,7]:
    b=Path(paths[str(n)]);im=Image.new('RGB',(1300,440),'white');dr=ImageDraw.Draw(im)
    if n==6:
        box(dr,(40,150,240,220),'normal');box(dr,(400,30,620,100),'interested');box(dr,(850,30,1050,100),'happy');box(dr,(400,270,620,340),'sleepy');box(dr,(850,270,1050,340),'afraid')
        arrow(dr,(240,165),(400,70),'button/approach');arrow(dr,(620,65),(850,65),'touch');arrow(dr,(480,100),(220,180),'timeout 2s');arrow(dr,(240,205),(400,300),'idle 6s');arrow(dr,(620,300),(850,300),'near');arrow(dr,(850,335),(240,220),'clear / fault')
        dr.text((40,380),'All states: fault/clear -> normal; near -> afraid. Afraid holds positive events.',font=small,fill='black')
        dr.text((40,410),'Other states: touch -> happy; button/approach -> interested. Full 5 x 8 table is authoritative.',font=small,fill='black')
        name='fsm.png';idx=27
    else:
        box(dr,(20,50,260,150),'MCU / simulation\nbutton touch range');box(dr,(400,50,790,150),'Host interaction / FSM\nAHM -> SO(2) CPG (planned)');box(dr,(960,50,1280,150),'Safety arbiter / driver\nservo + RGB output')
        arrow(dr,(260,95),(400,95));arrow(dr,(790,95),(960,95))
        dr.text((280,165),'3 input topics',font=small,fill='black');dr.text((820,165),'4 output topics',font=small,fill='black')
        box(dr,(400,260,790,345),'Collector / logger\nsource ID + clock correlation');arrow(dr,(1140,150),(790,300),'encoder / photodiode');arrow(dr,(580,150),(580,260))
        dr.text((20,390),'Real extension: MCU client <-> serial <-> micro-ROS Agent <-> ROS 2 host',font=small,fill='black')
        dr.text((20,420),'All 7 topics: RELIABLE, KEEP_LAST depth 10, VOLATILE. Hardware and ROS not executed.',font=small,fill='black')
        name='architecture.png';idx=10
    im.save(b/name)
    root=b.parent.parent;src=root/f'Week0{n}_Student_Worksheet_TH.docx';d=Document(src)
    p=d.paragraphs[idx];p.text='';p.add_run().add_picture(str(b/name),width=Inches(6.2))
    for p in list(d.paragraphs):
        if not p.text.strip() and not p._p.xpath('.//w:drawing') and p._p.xpath('.//w:br[@w:type="page"]'):
            p._p.getparent().remove(p._p)
    for p in d.paragraphs:
        if p.style.name.startswith('Heading 1'):
            p.paragraph_format.page_break_before=not p.text.startswith('1 ')
        p.paragraph_format.space_after=Pt(4)
    stage=Path('qa_lab67/final')/f'lab0{n}';stage.mkdir(parents=True,exist_ok=True)
    d.save(stage/src.name)
    md=root/'worksheet.md';s=md.read_text(encoding='utf-8');s+='\n\n![Diagram](results/completed_20261109/'+name+')\n';md.write_text(s,encoding='utf-8')
print('Final layout staged in qa_lab67/final; original names preserved.')
