# รายงาน Lab05 Hormone SO2 CPG และ Kinematic Walking

ชื่อ/รหัส อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม __________ | วันที่ทดลอง 09/11/2026

Lab05เป็นworking scaffoldเชื่อม hormone→SO(2)CPG→kinematic walking ไม่โหลดstudent codeโดยตรง ผู้ช่วยตรวจเทียบhormone_stepกับstudent_hormone.pyจากLab04ที่ย้ายไว้แล้ว ครบ600updatesรวมfaultและratesB2/B3ให้ผลh/r/raw/p/c/b/faultตรงกันทุกค่า ไม่แก้sourceของLab04หรือLab05

## วัตถุประสงค์และสถาปัตยกรรม

```text
Scheduled stimulus S → fixed/direct/hormone controller → R_used
    → bounded phi/stride → SO(2) CPG → tripod decoder → kinematic body
```
Main runner ไม่มี independent sensory feedback จาก terrain/body กลับเข้าcontroller contactในdecoderมาจากsign(o2)เอง ส่วนcontact demoเป็นการทดลองสังเคราะห์แยก ไม่ป้อนกลับไปสร้างฮอร์โมน

| ประเภท | ตัวอย่างและสถานะ |
|---|---|
| Source equation | SIF เป็น populationSDของ6SI และ release=CI/(1+exp(−SIF)), CI=1 ตาม paper Eqs.(1)–(2) |
| Proposed course equation | Euler H_new=clamp(H+dt(k_prod S−k_clear H−k_bind R),0,1); affine phi/stride; paired-product Pearson ของdemo |
| Expected vs measured proxy | expected sine1Hz เทียบ synthetic actual contact-proxy; ไม่ใช่force sensorหรือfeedbackฮาร์ดแวร์ |
| วัดไม่ได้ | Stability/Harmony/Displacement ตามpaperเป็นN/A; ไม่มีdynamics/sensorindices/normalizationที่ตรงนิยาม |


## Protocol และเวลา

dt=.05 s,duration30 s,warmup10 s,alpha1.10,lift.03 m,initial(.1,0); S0/1/0ที่0/10/20 s ทุกconditionใช้scheduleและwarmupร่วมกัน 601states/600intervals ไม่มีrandomnoise

| command/input s | state end s | H_start | H_end | R_used | phi rad | stride_half m |
|---|---|---|---|---|---|---|
| 10.000000 | 10.050000 | 0.000000 | 0.040000 | 0.000000 | 0.200000 | 0.055000 |
| 10.050000 | 10.100000 | 0.040000 | 0.078400 | 0.040000 | 0.208000 | 0.055400 |
| 20.000000 | 20.050000 | 0.999715 | 0.959727 | 0.999715 | 0.399943 | 0.064997 |

B1commandlatency0แต่statelatency.05 s ส่วนB2ใช้Hต้นช่วงจึงcommand10.05ใช้H=.04 บันทึกHปลายช่วง=.0784 ไม่ใช่physical latency

## ผลและข้อค้นพบ

| Condition | TV phi rad | maxΔphi rad/step | TV stride m | cmd latency s | cmd recovery s | on frequency Hz | on distance m |
|---|---|---|---|---|---|---|---|
| B0 | 0.000000 | 0.000000 | 0.000000 | N/A | N/A | 0.624877 | 0.778743 |
| B1 | 0.400000 | 0.200000 | 0.020000 | 0.000000 | 0.000000 | 1.268366 | 1.825152 |
| B2 | 0.399827 | 0.008000 | 0.019991 | 0.150000 | 2.850000 | 1.202760 | 1.706250 |
| B3 | 0.399534 | 0.008000 | 0.019977 | 0.150000 | 3.800000 | 1.225791 | 1.727498 |

B2ลด maxΔphi จากB1 .200000 เป็น .008000 rad/step (ลด96%) และ maxΔstride จาก.010000เป็น.000400 m/step แต่ command latencyเพิ่ม0→.15 s และrecovery0→2.85 s สนับสนุนhypothesisด้านความค่อยเป็นค่อยไป ไม่ใช่การรับรองความเร่ง/แรงหรือความปลอดภัยมอเตอร์ TVphiยังใกล้กัน .400000กับ.399827 rad จึงไม่สนับสนุนคำกล่าวว่าhormoneต้องลดTVอย่างมาก B3ไม่มีbindingแต่ยังมีH state/clearance จึงมีmemoryและrecovery3.80 s ช้ากว่าB2 .95 s

| Mapping | Condition | on frequency Hz | on distance m | total distance m |
|---|---|---|---|---|
| comparison | B1 | 1.268366 | 1.825152 | 3.377516 |
| comparison | B2 | 1.202760 | 1.706250 | 3.382580 |
| phi_only | B1 | 1.268366 | 1.549111 | 3.099299 |
| phi_only | B2 | 1.202760 | 1.467193 | 3.117323 |
| stride_only | B1 | 0.624877 | 0.914717 | 2.468477 |
| stride_only | B2 | 0.624877 | 0.901666 | 2.473523 |

Boundsเหมือนกันไม่ได้ทำให้amplitudeเท่ากัน B0 peakR_used=0, B1=1, B2=.999715, B3=1; phi peakตามลำดับ .20/.40/.399943/.40 rad และไม่มีcommandclampทั้ง4condition จำนวนsupportlegs=3มาจากdecoder ไม่พิสูจน์stability/ไม่ล้ม TVไม่ใช่Harmony และdistanceที่วัดไม่ใช่paperDisplacement การแบ่งpre/on/offสำคัญเพราะมีtransient: B2frequencypre=.624878,on=1.202760,off=.698234 Hz ไม่ควรแทนด้วยค่าเฉลี่ย30sและเรียกทุกช่วงsteady state ไม่มีforce/mass/friction/CoM/energyหรือterrainfeedback

## Fault และcontact

ในfaultprofile ทุกconditionfallbackก่อนCPG updateที่command15.00 s: fault1,R_used0,phi=.20 rad,stride=.055 m สำหรับB2 H_used=0,state15.05 H=0 และstate15.10 H=.04หลังinputกลับปกติ ไม่freezeตัวกรอง เป็นsoftwarefallback ไม่ใช่actuatorlimits/watchdog/E-stop

| Case | Mean SI LF | Mean SI RF | Mean SIF | MAE | valid SIF rows /600 |
|---|---|---|---|---|---|
| matched | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 551/600 |
| gain-offset | 1.000000 | 1.000000 | 0.000000 | 0.162844 | 551/600 |
| mixed-delay | 1.000000 | 0.000009 | 0.499995 | 0.226007 | 551/600 |
| all-inverted | -1.000000 | -1.000000 | 0.000000 | 0.631375 | 551/600 |
| constant | N/A | N/A | N/A | 0.000000 | 0/600 |
| fault | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 501/600 |

gain-offset: SI≈1แม้MAE=.162844 เพราะPearsonไม่ไวต่อpositive scaleและoffset; all-inverted: SI≈−1ทุกขาแต่populationSD≈0และrelease=.5เหมือนmatched เป็นcommon-mode blind spot; mixed-delay: LF/RM/LH≈1 ส่วนRF/LM/RH≈0และSIF≈.499995; constant: variance0จึงSI/SIF/release=N/A ไม่ใช่0 แม้MAE=0; faultที่15.00กระทบ50rollingwindowsช่วง15.00–17.45 s ไม่นับstartup49rows รวมunavailable99rows และกลับvalid17.50 s ทั้งนี้Pearsonเป็นproposed course definitionที่ประกาศชัด ไม่ใช่การอ้างว่าimplement Eq.(3)ของpaperตรงตามพิมพ์ และยังไม่ต่อCg/HR/MI_H

## ข้อสรุปและทำซ้ำ

หลักฐานรองรับการลดmax-stepของคำสั่ง แต่ไม่ยืนยันstability/energy/hardware safety รายละเอียดคำตอบครบทุกข้ออยู่WORKSHEET_COMPLETED_TH.md; Pythonversion/commands/hashอยู่RUN_MANIFEST.json; คำสั่งทำซ้ำREADME_REPRODUCE.md; แผนก่อนรันPREDICTIONS_BEFORE_RUN.md; หลักฐานตรวจVERIFICATION.txt

อ้างอิง README/worksheet/SOURCES ของLab05 และNgamkajornwiwat et al.(2020) DOI10.1109/ACCESS.2020.2992794 ตามขอบเขตproposed course model
