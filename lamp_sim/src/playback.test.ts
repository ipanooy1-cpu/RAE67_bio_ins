import { describe, it, expect } from 'vitest';
import { Matrix4, Vector3 } from 'three';
import { defaultMounting, lightingAt, mountedAngles, parseMotion, sampleAt } from './playback';
import { jointRotation } from './geometry';
import exported from '../public/lamp-motion.json';

describe('Python playback and mounting',()=>{
  it('loads hormone-modulated poses while preserving the timed Sad head endpoint',()=>{
    const data=parseMotion(exported);
    for(const mode of Object.values(data.modes)){
      expect(mode.samples).toHaveLength(201);
      for(const sample of mode.samples)expect(sample.q.every(q=>q>=60&&q<=120)).toBe(true);
    }
    const happy=sampleAt(data.modes.Happy.samples,1);
    expect(happy.centers[1]).toBeGreaterThan(90);
    expect(happy.centers[1]).toBeLessThan(95);
    expect(happy.phi).toBeGreaterThan(.2);
    expect(happy.phi).toBeLessThan(.35);
    expect(sampleAt(data.modes.Happy.samples,0).centers).toEqual([90,90,90,90]);
    expect(sampleAt(data.modes.Sad.samples,5).centers[3]).toBe(85);
    expect(sampleAt(data.modes.Sad.samples,10).q[3]).toBe(60);
  });
  it('maps servo reference and mounting direction without changing raw commands',()=>{
    const q=[90,100,95,105];const copy=[...q];
    expect(mountedAngles(q,defaultMounting)).toEqual([0,-35,60,-40]);
    expect(q).toEqual(copy);
  });
  it('interpolates exported commands and clamps playback endpoints',()=>{
    const rows=parseMotion(exported).modes.Happy.samples;
    const middle=sampleAt(rows,.025);
    middle.q.forEach((v,i)=>expect(v).toBeCloseTo((rows[0].q[i]+rows[1].q[i])/2,10));
    expect(sampleAt(rows,-1)).toBe(rows[0]);expect(sampleAt(rows,99)).toBe(rows.at(-1));
  });
  it('rejects nonfinite commands and nonmonotonic sample times',()=>{
    const a=structuredClone(exported);a.modes.Sad.samples[1].q[0]=NaN;expect(()=>parseMotion(a)).toThrow();
    const b=structuredClone(exported);b.modes.Happy.samples[1].t=0;expect(()=>parseMotion(b)).toThrow();
  });
  it('keeps J2-J4 pitch axes parallel under parent yaw and pitch',()=>{
    const parent=new Matrix4().makeRotationY(.7);
    const z=new Vector3(0,0,1).transformDirection(parent);
    expect(z.distanceTo(new Vector3(0,0,1))).toBeGreaterThan(.1);
    parent.multiply(new Matrix4().makeRotationZ(-.6));
    expect(new Vector3(0,0,1).transformDirection(parent).distanceTo(z)).toBeLessThan(1e-12);
    parent.multiply(new Matrix4().makeRotationZ(.9));
    expect(new Vector3(0,0,1).transformDirection(parent).distanceTo(z)).toBeLessThan(1e-12);
    expect(jointRotation(30,'z')).toEqual([0,0,Math.PI/6]);
  });
  it('rotating the shoulder moves downstream joints but leaves its pivot fixed',()=>{
    const before=new Vector3(0,1.2,0);
    const after=before.clone().applyMatrix4(new Matrix4().makeRotationZ(Math.PI/2));
    expect(after.x).toBeCloseTo(-1.2);expect(after.y).toBeCloseTo(0);
    expect(new Vector3().applyMatrix4(new Matrix4().makeRotationZ(.5)).length()).toBe(0);
  });
});

describe('Expression lighting timeline',()=>{
  it('uses the requested colors and brightness at each keyframe',()=>{
    const data=parseMotion(exported);
    const expected={Neutral:['#ffffff',[.6,.6,.6,.6]],Happy:['#ffd43b',[.6,.8,1,1]],Sad:['#377dff',[.6,.45,.25,.1]],Confused:['#b05cff',[.6,.75,.45,.65]]} as const;
    for(const name of Object.keys(expected) as (keyof typeof expected)[]){
      const timeline=data.modes[name].preset.light;
      [0,1,5,10].forEach((t,i)=>{const light=lightingAt(timeline,t);expect(light.color).toBe(expected[name][0]);expect(light.brightness).toBeCloseTo(expected[name][1][i],12);});
    }
  });
  it('interpolates between times and holds the final brightness',()=>{
    const timeline=parseMotion(exported).modes.Sad.preset.light;
    expect(lightingAt(timeline,3).brightness).toBeCloseTo(.35);
    expect(lightingAt(timeline,100).brightness).toBe(.1);
    expect(lightingAt(timeline,-1).brightness).toBe(.6);
  });
  it('rejects invalid brightness levels from imported files',()=>{
    const d=structuredClone(exported);d.modes.Sad.preset.light.brightness[0][1]=2;
    expect(()=>parseMotion(d)).toThrow('Invalid light timeline');
  });
  it('plays hormone light samples and interpolates their brightness',()=>{
    const rows=parseMotion(exported).modes.Sad.samples;
    expect(rows[0].light).toEqual({color:'#ffffff',brightness:.6});
    expect(rows.at(-1)!.light!.brightness).toBeGreaterThan(.1);
    expect(rows.at(-1)!.light!.brightness).toBeLessThan(.11);
    const middle=sampleAt(rows,.025).light!;
    expect(middle.brightness).toBeCloseTo((rows[0].light!.brightness+rows[1].light!.brightness)/2,12);
  });
  it('rejects invalid per-sample light or phase values',()=>{
    const a=structuredClone(exported);a.modes.Sad.samples[1].light.brightness=Infinity;
    expect(()=>parseMotion(a)).toThrow('Invalid sample light');
    const b=structuredClone(exported);b.modes.Happy.samples[1].phi=NaN;
    expect(()=>parseMotion(b)).toThrow('Invalid sample phi');
  });
});
