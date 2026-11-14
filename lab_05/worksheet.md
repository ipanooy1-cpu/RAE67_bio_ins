# ใบงาน Lab 05 Prediction timing evidence

ชื่อ/รหัส อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม __________ | วันที่ทดลอง 09/11/2026

Lab05เป็นworking scaffoldเชื่อม hormone→SO(2)CPG→kinematic walking ไม่โหลดstudent codeโดยตรง ผู้ช่วยตรวจเทียบhormone_stepกับstudent_hormone.pyจากLab04ที่ย้ายไว้แล้ว ครบ600updatesรวมfaultและratesB2/B3ให้ผลh/r/raw/p/c/b/faultตรงกันทุกค่า ไม่แก้sourceของLab04หรือLab05

## 1 ก่อนรัน hypothesis และ architecture

ดูPREDICTIONS_BEFORE_RUN.md บันทึกโดยผู้ช่วยก่อนรัน ไม่ใช่การอ้างว่าเป็นpredictionที่ผู้เรียนเขียนเอง H1:B2 max-stepต่ำกว่าB1แต่latency/recoveryสูงกว่า; H2:B3ยังมีmemoryและฟื้นช้ากว่าB2; H3:phi-onlyเปลี่ยนจังหวะ ส่วนstride-onlyคงfrequencyแต่เปลี่ยนระยะในmodel

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


## 2 Comparison และ timing

| command/input s | state end s | H_start | H_end | R_used | phi rad | stride_half m |
|---|---|---|---|---|---|---|
| 10.000000 | 10.050000 | 0.000000 | 0.040000 | 0.000000 | 0.200000 | 0.055000 |
| 10.050000 | 10.100000 | 0.040000 | 0.078400 | 0.040000 | 0.208000 | 0.055400 |
| 20.000000 | 20.050000 | 0.999715 | 0.959727 | 0.999715 | 0.399943 | 0.064997 |

B1command10.00ใช้S=1ทันทีจึงlatency0 s ส่วนstateหลังupdateเริ่ม10.05จึงstate latency.05 s เป็นnumerical scheduling ไม่ใช่hardware latency B2ใช้Rจากstateต้นช่วง จึงcommand10.00ยังbaselineและcommand10.05จึงphi=.208

config.jsonทุกcondition warmup10 s/200steps phi=.20 alpha1.10 จาก(.10,0) ได้initialo1=−.026965330782974153,o2=−.5608626776309884เหมือนกัน resetH/R/body origin/footanchors/log หลังwarmupแต่คงoscillatorไว้

## 3 ผลเปรียบเทียบ

| Condition | TV phi rad | maxΔphi rad/step | TV stride m | cmd latency s | cmd recovery s | on frequency Hz | on distance m |
|---|---|---|---|---|---|---|---|
| B0 | 0.000000 | 0.000000 | 0.000000 | N/A | N/A | 0.624877 | 0.778743 |
| B1 | 0.400000 | 0.200000 | 0.020000 | 0.000000 | 0.000000 | 1.268366 | 1.825152 |
| B2 | 0.399827 | 0.008000 | 0.019991 | 0.150000 | 2.850000 | 1.202760 | 1.706250 |
| B3 | 0.399534 | 0.008000 | 0.019977 | 0.150000 | 3.800000 | 1.225791 | 1.727498 |

B2ลด maxΔphi จากB1 .200000 เป็น .008000 rad/step (ลด96%) และ maxΔstride จาก.010000เป็น.000400 m/step แต่ command latencyเพิ่ม0→.15 s และrecovery0→2.85 s สนับสนุนhypothesisด้านความค่อยเป็นค่อยไป ไม่ใช่การรับรองความเร่ง/แรงหรือความปลอดภัยมอเตอร์ TVphiยังใกล้กัน .400000กับ.399827 rad จึงไม่สนับสนุนคำกล่าวว่าhormoneต้องลดTVอย่างมาก B3ไม่มีbindingแต่ยังมีH state/clearance จึงมีmemoryและrecovery3.80 s ช้ากว่าB2 .95 s

Boundsเหมือนกันไม่ได้ทำให้amplitudeเท่ากัน B0 peakR_used=0, B1=1, B2=.999715, B3=1; phi peakตามลำดับ .20/.40/.399943/.40 rad และไม่มีcommandclampทั้ง4condition จำนวนsupportlegs=3มาจากdecoder ไม่พิสูจน์stability/ไม่ล้ม TVไม่ใช่Harmony และdistanceที่วัดไม่ใช่paperDisplacement การแบ่งpre/on/offสำคัญเพราะมีtransient: B2frequencypre=.624878,on=1.202760,off=.698234 Hz ไม่ควรแทนด้วยค่าเฉลี่ย30sและเรียกทุกช่วงsteady state ไม่มีforce/mass/friction/CoM/energyหรือterrainfeedback

## 4 One-factor และ fault

ก่อนรันประกาศว่าจะทำทั้งphi-onlyและstride-onlyโดยคงdt/alpha/warmup/schedule/decoderเหมือนเดิม metricหลักคือonfrequency/ondistance/max-step ตรวจCSVแล้วphi-onlyทุกintervalstride=.055 และstride-onlyทุกintervalphi=.20

| Mapping | Condition | on frequency Hz | on distance m | total distance m |
|---|---|---|---|---|
| comparison | B1 | 1.268366 | 1.825152 | 3.377516 |
| comparison | B2 | 1.202760 | 1.706250 | 3.382580 |
| phi_only | B1 | 1.268366 | 1.549111 | 3.099299 |
| phi_only | B2 | 1.202760 | 1.467193 | 3.117323 |
| stride_only | B1 | 0.624877 | 0.914717 | 2.468477 |
| stride_only | B2 | 0.624877 | 0.901666 | 2.473523 |

stride-only B1/B2 onfrequency=.624877 HzเหมือนB0 แต่ondistance=.914717/.901666 mสูงกว่าB0 .778743 m ส่วนphi-only onfrequencyของB1/B2เท่ากับbothที่1.268366/1.202760 Hz แต่ondistanceน้อยกว่าboth เพราะไม่มีการเพิ่มstride ข้อสรุปเชิงสาเหตุจำกัดในแบบจำลองนี้ไม่อ้างterrainหรือphysicalperformance

ในfaultprofile ทุกconditionfallbackก่อนCPG updateที่command15.00 s: fault1,R_used0,phi=.20 rad,stride=.055 m สำหรับB2 H_used=0,state15.05 H=0 และstate15.10 H=.04หลังinputกลับปกติ ไม่freezeตัวกรอง เป็นsoftwarefallback ไม่ใช่actuatorlimits/watchdog/E-stop

Extremeเพิ่มเติม: zero B2H=0ตลอด; oneHอยู่ในboundsตลอด; spikeS=1เพียงinterval10.00 s; non-step timingmetricsเป็นN/Aตามนิยาม ไม่แทนด้วย0

## 5 Contact mini-lab

| Case | Mean SI LF | Mean SI RF | Mean SIF | MAE | valid SIF rows /600 |
|---|---|---|---|---|---|
| matched | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 551/600 |
| gain-offset | 1.000000 | 1.000000 | 0.000000 | 0.162844 | 551/600 |
| mixed-delay | 1.000000 | 0.000009 | 0.499995 | 0.226007 | 551/600 |
| all-inverted | -1.000000 | -1.000000 | 0.000000 | 0.631375 | 551/600 |
| constant | N/A | N/A | N/A | 0.000000 | 0/600 |
| fault | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 501/600 |

gain-offset: SI≈1แม้MAE=.162844 เพราะPearsonไม่ไวต่อpositive scaleและoffset; all-inverted: SI≈−1ทุกขาแต่populationSD≈0และrelease=.5เหมือนmatched เป็นcommon-mode blind spot; mixed-delay: LF/RM/LH≈1 ส่วนRF/LM/RH≈0และSIF≈.499995; constant: variance0จึงSI/SIF/release=N/A ไม่ใช่0 แม้MAE=0; faultที่15.00กระทบ50rollingwindowsช่วง15.00–17.45 s ไม่นับstartup49rows รวมunavailable99rows และกลับvalid17.50 s ทั้งนี้Pearsonเป็นproposed course definitionที่ประกาศชัด ไม่ใช่การอ้างว่าimplement Eq.(3)ของpaperตรงตามพิมพ์ และยังไม่ต่อCg/HR/MI_H

## 6 สรุปส่งงานและ exit ticket

Claimที่ข้อมูลรองรับ: ภายใต้step scheduleนี้ hormone B2ลดmax-stepของคำสั่งphi96%จาก.20เป็น.008rad/step แลกcommandlatency.15sและrecovery2.85s อ้างcomparison/metrics.json

Claimที่ยังรองรับไม่ได้: หุ่นยนต์เดินไม่ล้มหรือใช้พลังงานน้อยลง ต้องเพิ่มbodydynamics/IMU/CoM/forces/motorcurrentและhardware trialsก่อน ไม่มีpaperStability/Harmony/Displacementที่วัดได้ในชุดนี้

ใช้PythonversionและsourcehashตามRUN_MANIFEST.json ผลซ้ำdeterministicไม่ใช่independenttrials และไม่ได้สร้างlearningจากประสบการณ์ ทุกค่าตัวเลขในตารางปัด6ตำแหน่ง เก็บค่าดิบเต็มในCSV/JSON

Checklist: comparison+onefactor+fault raw/config/manifestครบ; contactmetrics/CSVครบ6cases; ตารางtimingและmetricsครบ; staticกราฟ2รูปในfigures; interactive reportทุกrun; snapshotsและคำสั่งรันซ้ำครบ ผู้เรียนยังต้องเติมกลุ่ม อ่านอธิบายผล และตรวจชื่อก่อนส่ง

อ้างอิง: README.md, worksheet.md และSOURCES.mdของLab05; Ngamkajornwiwat et al.(2020), DOI10.1109/ACCESS.2020.2992794ตามที่SOURCESอธิบาย ใช้แนวคิดและsource-equationที่ระบุ ไม่อ้างreproductionของpaper
