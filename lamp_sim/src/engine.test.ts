import { describe,it,expect } from 'vitest';
import { weights,next,defaults,initial,experiment,decode,defaultJoints,metrics,csv,csvColumns } from './engine';
import { Simulation } from './simulation';
describe('SO(2) mathematics',()=>{
 it('forms the scaled rotation matrix',()=>{const w=weights({...defaults,alpha:1.3,phi:.4});expect(w.w11).toBeCloseTo(1.3*Math.cos(.4),12);expect(w.w12).toBeCloseTo(1.3*Math.sin(.4),12);expect(w.w21).toBe(-w.w12);expect(w.w22).toBe(w.w11);expect(w.w11*w.w22-w.w12*w.w21).toBeCloseTo(1.69,12);});
 it('updates both neurons from the same old state',()=>{const s={o1:.7,o2:-.2},p={...defaults,alpha:1.3,phi:.4};const n=next(s,p);expect(n.o1).toBeCloseTo(Math.tanh(1.3*Math.cos(.4)*.7+1.3*Math.sin(.4)*-.2),12);expect(n.o2).toBeCloseTo(Math.tanh(-1.3*Math.sin(.4)*.7+1.3*Math.cos(.4)*-.2),12);expect(s).toEqual({o1:.7,o2:-.2});});
 it('reproduces runs and responds to gain and phase',()=>{const a=experiment(defaults),b=experiment({...defaults,phi:.4}),c=experiment({...defaults,alpha:1.3});expect(a).toEqual(experiment(defaults));expect(metrics(b).frequency!).toBeGreaterThan(metrics(a).frequency!*1.8);expect(metrics(c).amplitude1).toBeGreaterThan(metrics(a).amplitude1);});
 it('remains bounded',()=>{expect(experiment({...defaults,alpha:1.5,phi:.45}).every(r=>Math.abs(r.o1)<=1&&Math.abs(r.o2)<=1)).toBe(true);});
});
describe('motion and scheduler',()=>{
 it('decodes source, direction, disabled joints and clamps limits',()=>{const j=structuredClone(defaultJoints);j[0].amplitude=20;j[0].max=5;j[1].enabled=false;const q=decode({o1:.8,o2:.5},j);expect(q[0]).toEqual({angle:5,limited:true});expect(q[1].angle).toBe(j[1].center);expect(q[2].angle).toBeCloseTo(j[2].center-.8);});
 it('keeps speed separate from fixed step and resets deterministically',()=>{const a=new Simulation(),b=new Simulation();a.advance(1,2);b.advance(2,1);expect(a.rows).toEqual(b.rows);a.reset();expect(a.state).toEqual(initial);expect(a.step).toBe(0);});
 it('rate limits expression transitions',()=>{const s=new Simulation();s.mode='Happy';s.tick();expect(Math.abs(s.angles[3]-defaultJoints[3].center)).toBeLessThanOrEqual(3);});
});
describe('analysis and export',()=>{
 it('recovers period frequency amplitude and phase from known signals',()=>{const rows=experiment(defaults).map((r,i)=>({...r,o1:Math.sin(2*Math.PI*i/40),o2:Math.sin(2*Math.PI*(i-10)/40)}));const m=metrics(rows);expect(m.period).toBeCloseTo(40,4);expect(m.seconds).toBeCloseTo(2,4);expect(m.frequency).toBeCloseTo(.5,4);expect(m.phase).toBeCloseTo(90,4);expect(m.amplitude1).toBeCloseTo(1);});
 it('reports inadequate or changing signals as unavailable',()=>{expect(metrics(experiment(defaults).slice(0,10)).period).toBeNull();const rows=experiment(defaults);rows[500].phi=.3;expect(metrics(rows).frequency).toBeNull();});
 it('exports actual samples with complete columns',()=>{const rows=experiment(defaults).slice(0,2),lines=csv(rows).split('\n');expect(lines).toHaveLength(3);expect(lines[0]).toBe(csvColumns.join(','));expect(lines[1].split(',')).toHaveLength(15);expect(+lines[1].split(',')[5]).toBe(rows[0].o1);});
});
