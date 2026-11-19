import { writeFileSync } from 'node:fs';
import { defaults, experiment, metrics, csv, initial, defaultJoints } from '../src/engine';
const configs=[{name:'A0-baseline',alpha:1.1,phi:.2},{name:'A1-fast',alpha:1.1,phi:.4},{name:'A2-high-gain',alpha:1.3,phi:.2}];
const summary=configs.map(c=>{const params={...defaults,alpha:c.alpha,phi:c.phi};const rows=experiment(params);writeFileSync(`examples/${c.name}.csv`,csv(rows));return {name:c.name,configuration:{params,initial,warmup:200,steps:1000,joints:defaultJoints,mode:'Neutral',motion:'direct steady-state decoder'},metrics:metrics(rows)};});
writeFileSync('examples/summary.json',JSON.stringify(summary,null,2));
console.log(summary.map(s=>({name:s.name,...s.metrics})));
