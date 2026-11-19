import { useEffect, useState } from 'react';
import { Robot } from './Robot';
import { defaultMounting, lightingAt, mountedAngles, parseMotion, sampleAt, type MotionData } from './playback';
import type { Mode } from './engine';

export function LampPlayback(){
  const [data,setData]=useState<MotionData|null>(null);
  const [error,setError]=useState('');
  const [mode,setMode]=useState<Mode>('Sad');
  const [time,setTime]=useState(0);
  const [playing,setPlaying]=useState(false);
  const [speed,setSpeed]=useState(1);
  const [axes,setAxes]=useState(true);
  const [manual,setManual]=useState(false);
  const [manualQ,setManualQ]=useState([90,90,90,90]);
  const [mounting,setMounting]=useState(()=>structuredClone(defaultMounting));
  useEffect(()=>{let active=true;fetch(`${import.meta.env.BASE_URL}lamp-motion.json`).then(r=>{if(!r.ok)throw Error('Run python scripts/export_lamp_motion.py first');return r.json();}).then(parseMotion).then(d=>{if(active)setData(d);}).catch(e=>{if(active)setError(String(e));});return()=>{active=false;};},[]);
  useEffect(()=>{if(!playing||!data||manual)return;let last=performance.now();const id=setInterval(()=>{const now=performance.now(),delta=(now-last)/1000*speed;last=now;setTime(t=>Math.min(data.duration,t+delta));},30);return()=>clearInterval(id);},[playing,data,manual,speed]);
  useEffect(()=>{if(data&&time>=data.duration)setPlaying(false);},[time,data]);
  if(!data)return <section className="panel panel-body">{error||'Loading Python motion samples…'}</section>;
  const sample=sampleAt(data.modes[mode].samples,time);
  const light=sample.light??lightingAt(data.modes[mode].preset.light,time);
  const commands=manual?manualQ:sample.q;
  const angles=mountedAngles(commands,mounting);
  const changeMode=(value:Mode)=>{setMode(value);setTime(0);setPlaying(false);};
  return <div className="python-playback"><div className="section-intro"><h2>Python → 4DOF lamp</h2><p>J1: vertical yaw · J2/J3/J4: parallel horizontal pitch · 0 → 1 → 5 → 10 seconds</p></div>
    <section className="panel playback-toolbar"><label>Expression <select aria-label="Playback expression" value={mode} onChange={e=>changeMode(e.target.value as Mode)}>{Object.keys(data.modes).map(m=><option key={m}>{m}</option>)}</select></label>
      <button className="primary" disabled={manual} onClick={()=>{if(time>=data.duration)setTime(0);setPlaying(!playing);}}>{playing?'Pause':'Play Python motion'}</button>
      <button onClick={()=>{setPlaying(false);setTime(0);}}>Reset time</button>
      <select aria-label="Playback speed" value={speed} onChange={e=>setSpeed(+e.target.value)}>{[.25,.5,1,2].map(v=><option key={v} value={v}>{v}×</option>)}</select>
      <label><input type="checkbox" checked={axes} onChange={e=>setAxes(e.target.checked)}/> Joint axes</label>
      <label><input type="checkbox" checked={manual} onChange={e=>{setManual(e.target.checked);setPlaying(false);setManualQ([...sample.q]);}}/> Manual joint check</label>
    </section>
    <div className="playback-layout"><section className="panel"><div className="panel-heading"><h2>{manual?'Manual joint check':`${mode} · ${time.toFixed(2)} s`}</h2><span>LOCAL Y / Z / Z / Z</span></div><Robot angles={angles} axes={axes} lengths={[120,150,80]} j4Axis="z" light={light}/>
      <div className="playback-timeline"><p className="light-status"><span style={{background:light.color,boxShadow:`0 0 12px ${light.color}`}}/> LED {mode} · {Math.round(light.brightness*100)}% brightness</p><label>Simulation time <strong>{time.toFixed(2)} s</strong><input aria-label="Playback time" type="range" min={0} max={data.duration} step={.01} value={time} disabled={manual} onChange={e=>{setPlaying(false);setTime(+e.target.value);}}/></label><div>{[0,1,5,10].filter(t=>t<=data.duration).map(t=><button key={t} onClick={()=>{setPlaying(false);setTime(t);}}>{t} s pose</button>)}</div></div>
      <div className="joint-strip">{commands.map((q,i)=><div key={i}><span>J{i+1} · {i===0?'Y':'Z'}</span><strong>{q.toFixed(1)}<em>°</em></strong><small>model {angles[i].toFixed(1)}°</small></div>)}</div>
    </section><aside className="panel panel-body"><h2>Mounting calibration</h2><p className="small muted">Illustrative geometry based on your reference image. Command 90° maps to each reference pose below. Set actual zero and direction after measuring your lamp.</p>
      {mounting.map((m,i)=><div className="mounting-joint" key={i}><h2>J{i+1} · {['Base yaw','Shoulder pitch','Elbow pitch','Head pitch'][i]}</h2>
        <label>Servo reference (°)<input aria-label={`J${i+1} servo reference`} type="number" min={0} max={180} value={m.reference} onChange={e=>setMounting(mounting.map((x,j)=>j===i?{...x,reference:+e.target.value}:x))}/></label>
        <label>Model reference (°)<input aria-label={`J${i+1} model reference`} type="number" min={-180} max={180} value={m.offset} onChange={e=>setMounting(mounting.map((x,j)=>j===i?{...x,offset:+e.target.value}:x))}/></label>
        <label><input type="checkbox" checked={m.direction===-1} onChange={e=>setMounting(mounting.map((x,j)=>j===i?{...x,direction:e.target.checked?-1:1}:x))}/> Reverse mounting direction</label>
        {manual&&<label>Command {manualQ[i].toFixed(1)}°<input aria-label={`Manual J${i+1}`} type="range" min={60} max={120} step={.1} value={manualQ[i]} onChange={e=>setManualQ(manualQ.map((q,j)=>j===i?+e.target.value:q))}/></label>}
      </div>)}<button onClick={()=>setMounting(structuredClone(defaultMounting))}>Reset mounting</button>
    </aside></div>
    <section className="panel panel-body playback-info"><div><h2>Data from Python</h2><p className="small muted">α {data.modes[mode].preset.alpha} · φ {(sample.phi??data.modes[mode].preset.phi).toFixed(3)} rad/update · dt {data.dt} s · warmup {data.warmup} steps<br/>o1 {sample.o1.toFixed(4)} · o2 {sample.o2.toFixed(4)}<br/>Playback interpolates exported command samples. No independent motion animation.</p></div><div><h2>Update your Python poses</h2><p className="small muted">Edit cpg_for_lamp.py, then run:</p><code>python scripts/export_lamp_motion.py</code><p className="small muted">Reload this page, or load an exported JSON file below.</p><input aria-label="Import Python motion JSON" type="file" accept=".json" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;try{const d=parseMotion(JSON.parse(await file.text()));setData(d);setTime(0);setPlaying(false);setError('');}catch(err){setError(String(err));}e.target.value='';}}/>{error&&<p role="alert">{error}</p>}</div></section>
    <p className="small muted">The joint hierarchy follows your specified mounting. Link sizes, mechanical offsets and servo directions remain illustrative until calibrated. This view does not model collisions, loads or servo dynamics.</p>
  </div>;
}
