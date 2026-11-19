import type { Mode } from './engine';
export type MotionSample = { t: number; o1: number; o2: number; q: number[]; centers: number[]; phi?:number; light?:LampLight };
export type LampLight = {color:string; brightness:number};
export type LightTimeline = {color:string; brightness:[number,number][]};
export type MotionData = { version: number; source: string; dt: number; duration: number; warmup: number; limits: number[][]; modes: Record<Mode, { preset: {light?:LightTimeline;alpha:number;phi:number;poses:[number,number[]][]}; samples: MotionSample[] }> };
export type Mounting = { reference: number; offset: number; direction: number };
// Servo command 90 degrees corresponds to the assembled reference pose.
// These offsets are illustrative mounting values, not hardware calibration.
export const defaultMounting: Mounting[] = [
  {reference:90,offset:0,direction:1},
  {reference:90,offset:-25,direction:-1},
  {reference:90,offset:65,direction:-1},
  {reference:90,offset:-25,direction:-1},
];
export function mountedAngles(q:number[],mounting:Mounting[]) {
  return q.map((v,i)=>mounting[i].offset+mounting[i].direction*(v-mounting[i].reference));
}
export function sampleAt(samples:MotionSample[],t:number):MotionSample {
  if(t<=samples[0].t)return samples[0];
  if(t>=samples[samples.length-1].t)return samples[samples.length-1];
  let lo=0,hi=samples.length-1;
  while(hi-lo>1){const mid=(lo+hi)>>1;if(samples[mid].t<=t)lo=mid;else hi=mid;}
  const a=samples[lo],b=samples[hi],f=(t-a.t)/(b.t-a.t);
  const mix=(x:number,y:number)=>x+(y-x)*f;
  const result:MotionSample={t,o1:mix(a.o1,b.o1),o2:mix(a.o2,b.o2),q:a.q.map((v,i)=>mix(v,b.q[i])),centers:a.centers.map((v,i)=>mix(v,b.centers[i]))};
  if(a.phi!==undefined&&b.phi!==undefined)result.phi=mix(a.phi,b.phi);
  if(a.light&&b.light){
    const channels=[1,3,5].map(i=>Math.round(mix(parseInt(a.light!.color.slice(i,i+2),16),parseInt(b.light!.color.slice(i,i+2),16))));
    result.light={color:'#'+channels.map(v=>v.toString(16).padStart(2,'0')).join(''),brightness:mix(a.light.brightness,b.light.brightness)};
  }
  return result;
}
export function parseMotion(value:unknown):MotionData {
  const d=value as MotionData;
  if(!d||d.version!==1||!Number.isFinite(d.duration)||d.duration<=0||!Number.isFinite(d.dt)||d.dt<=0)throw Error('Invalid motion file header');
  for(const name of ['Neutral','Happy','Sad','Confused'] as Mode[]){
    const mode=d.modes?.[name],s=mode?.samples;
    if(!mode?.preset||!s||s.length<2||s.length>100000||s[0].t!==0||Math.abs(s[s.length-1].t-d.duration)>1e-6)throw Error(`Invalid samples for ${name}`);
    const light=mode.preset.light;
    if(light&&(!/^#[0-9a-fA-F]{6}$/.test(light.color)||!Array.isArray(light.brightness)||light.brightness.length<1||light.brightness.some((f,i)=>!Array.isArray(f)||f.length!==2||!f.every(Number.isFinite)||f[0]<0||f[1]<0||f[1]>1||(i>0&&f[0]<=light.brightness[i-1][0]))))throw Error('Invalid light timeline');
    if(!Number.isFinite(mode.preset.alpha)||!Number.isFinite(mode.preset.phi))throw Error('Invalid preset');
    s.forEach((r,i)=>{if(!Number.isFinite(r.t)||(i>0&&r.t<=s[i-1].t)||!Number.isFinite(r.o1)||!Number.isFinite(r.o2)||![r.q,r.centers].every(a=>Array.isArray(a)&&a.length===4&&a.every(Number.isFinite)))throw Error(`Invalid sample in ${name}`);});
    s.forEach(r=>{
      if(r.phi!==undefined&&!Number.isFinite(r.phi))throw Error('Invalid sample phi');
      if(r.light&&(!/^#[0-9a-fA-F]{6}$/.test(r.light.color)||!Number.isFinite(r.light.brightness)||r.light.brightness<0||r.light.brightness>1))throw Error('Invalid sample light');
    });
  }
  return d;
}

/** Linear brightness interpolation uses simulation time, including pause/scrub. */
export function lightingAt(timeline:LightTimeline|undefined,t:number):LampLight {
  if(!timeline)return {color:'#ffffff',brightness:.6};
  const frames=timeline.brightness;
  if(t<=frames[0][0])return {color:timeline.color,brightness:frames[0][1]};
  for(let i=1;i<frames.length;i++){
    const [end,b]=frames[i], [start,a]=frames[i-1];
    if(t<=end)return {color:timeline.color,brightness:a+(b-a)*(t-start)/(end-start)};
  }
  return {color:timeline.color,brightness:frames[frames.length-1][1]};
}
