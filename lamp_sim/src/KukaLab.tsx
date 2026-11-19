import {useEffect,useState} from 'react';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,Legend} from 'recharts';
import {KukaSession,modes,emotions,sessionCSV} from './kuka';
import {download,type Mode} from './engine';
import {Robot} from './Robot';
import {defaultMounting,mountedAngles} from './playback';

function Num({name,value,min,max,change}:{name:string;value:number;min:number;max:number;change:(n:number)=>void}){
  return <label style={{display:'inline-grid',gap:3,margin:'4px 8px 4px 0'}}>{name}<input type="number" step="any" min={min} max={max} value={value} onChange={e=>{const v=e.target.valueAsNumber;if(Number.isFinite(v)&&v>=min&&v<=max)change(v)}}/></label>
}
export function KukaLab(){
  const [sim,setSim]=useState(()=>new KukaSession()),[running,run]=useState(false),[,draw]=useState(0);
  const refresh=()=>draw(n=>n+1);
  useEffect(()=>{
    if(!running)return;
    const id=setInterval(()=>{sim.tick();refresh()},50);
    return ()=>clearInterval(id);
  },[running,sim]);
  const mode=sim.mode,p=sim.profile,m=p.modes[mode],last=sim.rows.at(-1);
  const charts=[['ฮอร์โมน H','H_happy','H_sad','H_curious'],['สัญญาณ CPG','o1','o2'],['มุมคำสั่ง (°)','J1','J2','J3','J4']];
  return <><section className="session-bar"><strong>น้องคูก้า · {Number(last?.time_s??0).toFixed(2)} s</strong><div className="transport">
    <button className="primary" onClick={()=>run(!running)}>{running?'พัก':'เริ่ม / เล่นต่อ'}</button>
    <button onClick={()=>{run(false);setSim(new KukaSession())}}>เริ่มรอบใหม่</button>
    <button onClick={()=>download('kuka-session.csv','\uFEFF'+sessionCSV(sim.rows),'text/csv;charset=utf-8')} disabled={!last}>Export CSV ({sim.rows.length})</button>
  </div></section>
  <div className="playback-layout"><section className="panel"><Robot angles={mountedAngles(sim.q,defaultMounting)} axes={false} lengths={[120,150,80]} j4Axis="z" light={sim.light}/>
  <div className="joint-strip">{sim.q.map((q,i)=><div key={i}>J{i+1}<strong>{q.toFixed(1)}°</strong></div>)}</div></section>
  <section className="panel panel-body"><h2>อารมณ์และฮอร์โมน</h2><label>โหมดโคม <select value={mode} onChange={e=>{sim.mode=e.target.value as Mode;refresh()}}>{modes.map(v=><option key={v}>{v}</option>)}</select></label>
  <p><label><input type="checkbox" checked={sim.manual} onChange={e=>{sim.manual=e.target.checked;refresh()}}/> ปรับ H เอง</label></p>
  {emotions.map(e=><label className="field" key={e}>H {e} · {sim.h[e].toFixed(3)}<input aria-label={'H '+e} type="range" min="0" max="1" step=".01" disabled={!sim.manual} value={sim.h[e]} onChange={ev=>{sim.h[e]=+ev.target.value;refresh()}}/></label>)}
  <p>φ ที่ใช้จริง {last?Number(last.phi).toFixed(3):'—'} rad/update</p>
  <p className="small muted">จำลองการเลือกโหมด ภาพ 3D ใช้จุดติดตั้งโดยประมาณ</p></section></div>
  <section className="panel panel-body"><details><summary>ปรับโปรไฟล์ · {mode}</summary>
  <Num name="α ทุกโหมด" value={p.global.so2_alpha} min={0} max={3} change={v=>{p.global.so2_alpha=v;refresh()}}/>
  <Num name="φ rad/update" value={m.phi} min={0} max={3.14} change={v=>{m.phi=v;refresh()}}/>
  {m.gains.map((v,i)=><Num key={i} name={'gain J'+(i+1)} value={v} min={0} max={60} change={n=>{m.gains[i]=n;refresh()}}/>)}
  {mode!=='Neutral'&&(['tau_up','tau_down'] as const).map(k=><Num key={k} name={k+' (s)'} value={p.hormones[mode][k]} min={.05} max={60} change={n=>{p.hormones[mode][k]=n;refresh()}}/>)}
  {m.poses.map(f=><div key={f.time}><b>{f.time} s　</b>{f.angles.map((v,i)=><Num key={i} name={'J'+(i+1)+' °'} value={v} min={60} max={120} change={n=>{f.angles[i]=n;refresh()}}/>)}</div>)}
  <label>สีไฟ <input type="color" value={m.light_color} onChange={e=>{m.light_color=e.target.value;refresh()}}/></label>
  {m.brightness.map(f=><Num key={f.time} name={'แสง '+f.time+' s'} value={f.value} min={0} max={1} change={n=>{f.value=n;refresh()}}/>)}
  <button onClick={()=>{sim.profile=new KukaSession().profile;refresh()}}>คืนค่าโปรไฟล์หุ่น</button></details></section>
  {charts.map(([name,...keys])=><section className="panel panel-body" key={name}><h2>{name}</h2><ResponsiveContainer width="100%" height={190}><LineChart data={sim.rows.slice(-400)}><XAxis dataKey="time_s" type="number" domain={['dataMin','dataMax']} tickFormatter={v=>Number(v).toFixed(1)} unit=" s"/><YAxis/><Tooltip/><Legend/>{keys.map((k,i)=><Line key={k} dataKey={k} stroke={['#55e0df','#f4a65b','#9c95f5','#d8e66c'][i]} dot={false} isAnimationActive={false}/>)}</LineChart></ResponsiveContainer></section>)}</>
}
