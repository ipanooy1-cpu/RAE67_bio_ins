import profile from './kuka-profile.json';
import hardware from './kuka-hardware.json';
import {next,weights as matrix, type Mode} from './engine';

export const modes: Mode[] = ['Neutral','Happy','Sad','Confused'];
export const emotions = ['Happy','Sad','Confused'] as const;
const dt = 0.05;
const clamp = (x:number,lo:number,hi:number)=>Math.min(hi,Math.max(lo,x));
const hName = {Happy:'H_happy',Sad:'H_sad',Confused:'H_curious'};
export type Row = Record<string,number|string>;

function interpolate<T extends {time:number}>(frames:T[], time:number, value:(f:T)=>number){
  const i=frames.findIndex(f=>f.time>=time);
  if(i<0)return value(frames[frames.length-1]);
  if(i===0)return value(frames[0]);
  const a=frames[i-1], b=frames[i];
  return value(a)+(value(b)-value(a))*(time-a.time)/(b.time-a.time);
}

export class KukaSession {
  profile=structuredClone(profile);
  mode:Mode='Neutral';
  manual=false;
  h={Happy:0,Sad:0,Confused:0};
  osc={o1:.1,o2:0};
  q=[90,90,90,90];
  light={color:'#ffffff',brightness:.15};
  rows:Row[]=[];
  onset:Partial<Record<Mode,number>>={Neutral:0};
  private previous:Mode='Neutral';
  private headStart=90;
  constructor(){
    for(let i=0;i<this.profile.global.warmup_steps;i++)
      this.osc=next(this.osc,{alpha:this.profile.global.so2_alpha,phi:this.profile.modes.Neutral.phi,dt});
  }
  tick(){
    const p=this.profile, time=(this.rows.length+1)*dt;
    if(this.mode!==this.previous){
      this.onset[this.mode]=time;
      this.headStart=this.q[3];
      this.previous=this.mode;
    }
    const elapsed=time-(this.onset[this.mode]??0);
    const row:Row={time_s:time,dt,profile:'robot_cpg_gui',mode:this.mode,mode_time_s:elapsed,H_control:this.manual?'manual':'auto',alpha:p.global.so2_alpha};
    let sum=0;
    for(const e of emotions){
      const target=Number(this.mode===e), tau=p.hormones[e];
      if(!this.manual)this.h[e]=clamp(this.h[e]+dt*(target-this.h[e])/(target>this.h[e]?tau.tau_up:tau.tau_down),0,1);
      sum+=this.h[e];row[hName[e]]=this.h[e];row[e+'_target']=target;
      row[e+'_tau_up']=tau.tau_up;row[e+'_tau_down']=tau.tau_down;
    }
    const centers=[0,0,0,0],gains=[0,0,0,0],rgb=[0,0,0];
    let phi=0,brightness=0;
    for(const m of modes){
      const w=m==='Neutral'?Math.max(0,1-sum):this.h[m]/Math.max(1,sum);
      const cfg=p.modes[m], t=this.onset[m]===undefined?0:time-this.onset[m]!;
      row['weight_'+m]=w;row['phi_'+m]=cfg.phi;phi+=w*cfg.phi;
      for(let j=0;j<4;j++){
        let center=interpolate(cfg.poses,t,f=>f.angles[j]);
        if(j===3&&m==='Sad'&&this.mode==='Sad'&&t<cfg.poses[1].time)
          center=this.headStart+(cfg.poses[1].angles[j]-this.headStart)*t/cfg.poses[1].time;
        centers[j]+=w*center;gains[j]+=w*cfg.gains[j];row[m+'_gain_J'+(j+1)]=cfg.gains[j];
      }
      brightness+=w*interpolate(cfg.brightness,t,f=>f.value);
      rgb.forEach((_,j)=>rgb[j]+=w*parseInt(cfg.light_color.slice(1+j*2,3+j*2),16));
    }
    this.light={color:'#'+rgb.map(v=>Math.round(v).toString(16).padStart(2,'0')).join(''),brightness:brightness*.25};
    const params={alpha:p.global.so2_alpha,phi,dt};
    this.osc=next(this.osc,params);
    Object.assign(row,this.osc,matrix(params),{phi,brightness,led_level:this.light.brightness,rgb:this.light.color,max_slew_deg_s:p.global.max_slew_deg_s,face_detected:'',face_x:'',face_y:'',tracking_state:'',stage:'',input_source:'simulated mode'});
    const {o1,o2}=this.osc;
    const fade=p.modes[this.mode].head_fade;
    this.q=this.q.map((old,j)=>{
      const blend=Math.min(1,time/p.global.oscillation_blend_s)*(j===3&&fade?1-clamp((elapsed-fade.start)/(fade.end-fade.start),0,1):1);
      const raw=centers[j]+blend*gains[j]*[o1,o2,-o1,o2][j];
      const {min,max}=p.joint_limits[j],target=clamp(raw,min,max),step=p.global.max_slew_deg_s*dt;
      const q=clamp(old+clamp(target-old,-step,step),min,max), s=hardware.servos[j],k='J'+(j+1);
      const delta=Math.round(s.direction*(q-90)/hardware.nominal_degrees_per_count);
      Object.assign(row,{[k]:q,[k+'_center']:centers[j],[k+'_gain']:gains[j],[k+'_requested']:raw,[k+'_min']:min,[k+'_max']:max,[k+'_counts']:clamp(s.center+clamp(delta,-171,171),s.safe_min,s.safe_max),[k+'_feedback']:''});
      return q;
    });
    row.profile_json=JSON.stringify(p);
    this.rows.push(row);
  }
}
export function sessionCSV(rows:Row[]){
  if(!rows.length)return '';
  const keys=Object.keys(rows[0]);
  const escape=(x:unknown)=>'"'+String(x??'').replaceAll('"','""')+'"';
  return [keys.join(','),...rows.map(r=>keys.map(k=>escape(r[k])).join(','))].join('\r\n');
}
