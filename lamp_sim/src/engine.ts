export type State = { o1: number; o2: number };
export type Params = { alpha: number; phi: number; dt: number };
export type Mode = 'Neutral' | 'Happy' | 'Sad' | 'Confused';
export type Joint = { name: string; center: number; amplitude: number; min: number; max: number; enabled: boolean; source: 'o1' | 'o2'; invert: boolean };
export type Sample = State & Params & { step: number; time_s: number; emotion_mode: Mode; q1_deg: number; q2_deg: number; q3_deg: number; q4_deg: number; w11: number; w12: number; w21: number; w22: number };
export const defaults: Params = { alpha: 1.1, phi: .2, dt: .05 };
export const initial: State = { o1: .1, o2: 0 };
export const presets: Record<Mode, { phi: number; scale: number; head: number }> = { Neutral: {phi:.2,scale:1,head:0}, Happy:{phi:.35,scale:6,head:-15}, Sad:{phi:.12,scale:2,head:25}, Confused:{phi:.25,scale:4,head:0} };
export const defaultJoints: Joint[] = ['Base yaw','Shoulder pitch','Elbow pitch','Head pitch'].map((name,i)=>({name,center:[0,-25,65,-25][i],amplitude:1,min:[-90,-70,-20,-80][i],max:[90,70,120,80][i],enabled:true,source:i%2?'o2':'o1',invert:i===2}));
export function weights(p: Params) { const c=p.alpha*Math.cos(p.phi),s=p.alpha*Math.sin(p.phi); return {w11:c,w12:s,w21:-s,w22:c}; }
export function next(s: State,p: Params): State { const w=weights(p); return {o1:Math.tanh(w.w11*s.o1+w.w12*s.o2),o2:Math.tanh(w.w21*s.o1+w.w22*s.o2)}; }
export function decode(s: State,joints: Joint[],scale=1,head=0) { return joints.map((j,i)=>{ const target=j.center+(i===3?head:0)+(j.enabled?j.amplitude*scale*s[j.source]*(j.invert?-1:1):0); return {angle:Math.max(j.min,Math.min(j.max,target)),limited:target<j.min||target>j.max}; }); }
export function record(s:State,p:Params,joints:Joint[],step:number,mode:Mode,angles?:number[]):Sample { const q=angles??decode(s,joints,presets[mode].scale,presets[mode].head).map(j=>j.angle); return {...s,...p,...weights(p),step,time_s:step*p.dt,emotion_mode:mode,q1_deg:q[0],q2_deg:q[1],q3_deg:q[2],q4_deg:q[3]}; }
export function experiment(p:Params,joints=defaultJoints,steps=1000,warmup=200,mode:Mode='Neutral') { let s={...initial}; for(let i=0;i<warmup;i++)s=next(s,p); const rows:Sample[]=[]; for(let i=0;i<steps;i++){s=next(s,p);rows.push(record(s,p,joints,i+1,mode));}return rows; }
function peaks(a:number[]) { const out:number[]=[]; for(let i=1;i<a.length-1;i++)if(a[i]>a[i-1]&&a[i]>=a[i+1]){ const d=a[i-1]-2*a[i]+a[i+1];out.push(i+(d===0?0:.5*(a[i-1]-a[i+1])/d)); }return out; }
export function metrics(rows:Sample[]) {
 const a=rows.map(r=>r.o1),b=rows.map(r=>r.o2),p=peaks(a),q=peaks(b);const amp=(v:number[])=>v.length?(Math.max(...v)-Math.min(...v))/2:0;
 const period=p.length>=3?(p.at(-1)!-p[0])/(p.length-1):null;
 const intervals=p.slice(1).map((v,i)=>v-p[i]); const stable=period!==null&&intervals.every(v=>Math.abs(v-period)/period<.1)&&rows.every(r=>r.dt===rows[0].dt&&r.alpha===rows[0].alpha&&r.phi===rows[0].phi);
 const seconds=stable?period!*rows[0].dt:null;
 const lags=stable?p.map(x=>q.reduce((best,y)=>Math.abs(y-x)<Math.abs(best-x)?y:best,Infinity)-x).filter(Number.isFinite).map(d=>((d/period!*360+540)%360)-180):[];
 return {period:stable?period:null,seconds,frequency:seconds?1/seconds:null,amplitude1:amp(a),amplitude2:amp(b),peakToPeak:amp(a)*2,phase:lags.length?lags.reduce((s,x)=>s+x,0)/lags.length:null,duration:rows.length?rows.at(-1)!.time_s-rows[0].time_s+rows[0].dt:0,reason:stable?'':'Need ≥3 stable peaks after warmup, with unchanged parameters.'};
}
export const csvColumns: (keyof Sample)[]=['step','time_s','emotion_mode','alpha','phi','o1','o2','w11','w12','w21','w22','q1_deg','q2_deg','q3_deg','q4_deg'];
export function csv(rows:Sample[]) { return [csvColumns.join(','),...rows.map(r=>csvColumns.map(k=>r[k]).join(','))].join('\n'); }
export function download(name:string,text:string,type='text/plain'){const u=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
