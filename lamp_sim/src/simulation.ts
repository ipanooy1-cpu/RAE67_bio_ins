import { defaults, initial, next, record, defaultJoints, decode, presets, type Params, type Joint, type Mode, type Sample } from './engine';
export class Simulation {
 params:Params={...defaults}; joints:Joint[]=structuredClone(defaultJoints); mode:Mode='Neutral'; state={...initial}; step=0; time=0; rows:Sample[]=[]; angles=defaultJoints.map(j=>j.center); scale=1; head=0; accumulator=0;
 updateMotion(dt:number){const preset=presets[this.mode];const f=1-Math.exp(-dt/.4);this.scale+=(preset.scale-this.scale)*f;this.head+=(preset.head-this.head)*f;const targets=decode(this.state,this.joints,this.scale,this.head);this.angles=targets.map((t,i)=>{const delta=Math.max(-60*dt,Math.min(60*dt,t.angle-this.angles[i]));return Math.max(this.joints[i].min,Math.min(this.joints[i].max,this.angles[i]+delta));});}
 tick(){this.state=next(this.state,this.params);this.step++;this.time+=this.params.dt;this.updateMotion(this.params.dt);const row=record(this.state,this.params,this.joints,this.step,this.mode,this.angles);row.time_s=this.time;this.rows.push(row);if(this.rows.length>10000)this.rows.shift();}
 advance(elapsed:number,speed:number){this.accumulator+=elapsed*speed;while(this.accumulator+1e-12>=this.params.dt){this.tick();this.accumulator=Math.max(0,this.accumulator-this.params.dt);}}
 reset(){this.state={...initial};this.step=0;this.time=0;this.rows=[];this.accumulator=0;this.scale=presets[this.mode].scale;this.head=presets[this.mode].head;this.angles=decode(this.state,this.joints,this.scale,this.head).map(x=>x.angle);}
}
