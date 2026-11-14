# โครงงานโคมไฟปฏิสัมพันธ์ด้วย AHM และ SO2 CPG
อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม: ยังไม่ระบุ | วันที่รัน 09/11/2026
สถานะ proposal ยังไม่ได้ทดลอง AHM–CPG,ROSหรือหุ่นยนต์จริง ผลoffline22sอยู่worksheet.mdคนละการทดลอง
## คำถามและแรงบันดาลใจ
การเพิ่มฮอร์โมน engagement ที่สะสมตามสิ่งเร้า ก่อนปรับ gain ของ SO(2) CPG ลดการเปลี่ยนคำสั่งฉับพลันและทำให้การฟื้นตัวหลังปิดสิ่งเร้าช้ากว่า direct stimulus หรือไม่ ในโคมไฟปฏิสัมพันธ์ 600 s?
C1 hormone จะลด peak command rate และเพิ่ม recovery time เทียบ C0 direct ภายใต้ fixture เดียวกัน; ไม่รับรอง both latency ดีขึ้น และไม่ใช้ state label เป็นหลักฐานอารมณ์จริง
การสะสมและสลายสัญญาณฮอร์โมนที่ทำให้ผลคงอยู่หลัง stimulus; ใช้สมการต้นทางในเอกสาร Week04 ของรายวิชา Hc(t)=beta Hc(t-1)+Hg(t)-Hr(t), Hg=alpha_h f(S), Hr=sum(gamma_i Receptor_i). SO(2) recurrent oscillator ตาม Lab03/course notation ของ Dr. Poramate; การเชื่อมและตัวเลขด้านล่างเป็น proposed course model ไม่ใช่ physiology calibration
## สมการและการเชื่อมระบบ
หนึ่ง hormone engagement H: R_old=clamp(H_old,0,1); P=.8*S; C=.6*H_old; B=.2*R_old; H_raw=H_old+dt_h*(P-C-B); H_new=clamp(H_raw,0,1); R_new=H_new, dt_h=.05s,H0=0. ทุก rate ใช้ OLD state แล้ว update ครั้งเดียว. beta ไม่เท่ากับ clear โดยตรง; โมเดลนี้เป็น Euler course adaptation
[a1_next,a2_next]^T=alpha*[[cos(phi),sin(phi)],[-sin(phi),cos(phi)]]*[o1,o2]^T; o1_next=tanh(a1_next),o2_next=tanh(a2_next); คำนวณพร้อมกันจาก OLD o. alpha=1.10,phi=.20 rad/update,o1(0)=.10,o2(0)=0,dt_cpg=.02s; tanh และค่าพารามิเตอร์เป็น course choices ไม่ใช่ continuous-time frequency calibration
Sensor validation/debounce→S=max(button,touch,approach_binary); AHM→R; C0 ใช้ R=S, C1 ใช้ R=H. ทั้งคู่ G=.02+.06*R rad และ q_target=q_neutral+G*[o1,o2,-o1], ผ่าน limits/slew/watchdog ก่อน driver. FSM แสดง emotion/RGB เดิม โดย near/fault override CPG; เมื่อไม่ปลอดภัยหยุด oscillator path. คง phi=.20 และalpha=1.10 เพื่อเปลี่ยนเพียงการมี hormone memory
## Architecture
sensor→validation/debounce→interaction/FSM→AHM→CPG→safetyarbiter→servo/RGBdriver; safetyFSMoverrideAHMCPG. Hostเก็บH,o,FSM;MCUacquisition/driverwatchdog. ใช้AHMCPGเป็นinternalmodulesก่อนเพื่อคง7topics; ROSและMCU/Agentยังต้องสร้าง/ทดสอบ
## ที่มาพารามิเตอร์
Lab04ให้prod=.8,clear=.6,bind=.2,H∈[0,1]; Lab03ให้SO(2)notationและcoursealpha1.1,phi.2,o0=[.1,0]. GroupเสนอG=.02+.06Rradและmulti-ratedt_h=.05/dt_cpg=.02s.ค่าเหล่านี้ไม่ใช่ผลสอบเทียบชีววิทยาหรือmechanicalhardware


---

# Interface และการทดลองโครงงาน
| Topic | Type | Units | Publisher→subscriber |
|---|---|---|---|
| /lamp/input/button | std_msgs/Bool | bool | input_source→interaction |
| /lamp/input/touch | std_msgs/Bool | bool | input_source→interaction |
| /lamp/input/distance | std_msgs/Float32 | m | input_source→interaction |
| /lamp/interaction | std_msgs/String | event | interaction→collector/logger |
| /lamp/emotion | std_msgs/String | state | interaction→collector/logger |
| /lamp/servo_command | std_msgs/Float32MultiArray | rad [tilt,extend,nod] | interaction→collector/driver |
| /lamp/rgb_command | std_msgs/ColorRGBA | r,g,b,a in [0,1] | interaction→collector/LED driver |
QoSทุกtopicRELIABLE,KEEP_LASTdepth10,VOLATILE; servoหน่วยradและRGB/255,a=1.คงmeaningทั้งsimulation/robot. Headerไม่มีบนwireจึงต้องsidecaridentity/clock
## Conditions และ controls
C0directใช้R=S; C1hormoneใช้R=H เปลี่ยนเพียงmemory stage. คงalpha,phi,Gmapping,sourcefixture,FSM,RGB,safety,dtและtransport. resetH=0,o=[.1,0],FSMnormalและneutralทุกtrial; 2ssetupก่อนเริ่มclock. near/faultoverrideเสมอ
Simulation2conditions×3pairedseeds41/42/43×600s และreal2conditions×3pairedsessions×600s รวม12trial/120minเฉพาะเวลารัน. ลำดับpairsC0–C1,C1–C0,C0–C1เป็นpartialcounterbalanceเพราะจำนวนคี่;ไม่อ้างว่ากำจัดorderbiasหมด. RealP01สมัครใจoperatorคนเดียวซ้ำ3session ไม่ใช่3independentparticipants
## Scenario 600 s และ denominator
0–150sท่ากลางและbutton60–70s;150–300s touch180–190s;300–450s approach300–310s,near400–420sและclear420s;450–600sbutton540–550sแล้วพัก. Expectedก่อนรัน5IDs:p_button_060,p_touch_180,p_approach_300,p_clear_420,p_button_540 เก็บfault/conflictเพิ่มทั้งหมดแม้ไม่มีexpressionใหม่; ไม่แก้subsetหลังเห็นผล. ก่อนprimaryต้องวางstateให้expressionเปลี่ยน ถ้าไม่สำเร็จเก็บno-state-change/missตามจริง
## Metrics
M1 peakcommandrate=max|Δq|/dt rad/sทุกแกน พร้อมจำนวนsamplesชนslewcap; C1คาดลดแต่capอาจทำให้เท่ากัน. M2 recoveryจากSoffถึงR≤.1ต่อเนื่อง.5s;ไม่ฟื้นในoffwindowให้right-censored. M3bothlatency=max(motion,RGB)−source; deadline1s,observation22s/event. Physicalใช้encoder/photodiode,simulationใช้appliedcommandแยกกัน. Missingnull/abortพร้อมreason เก็บplanned3trial/condition/platformในdenominator


---

# การวัด ความปลอดภัย และแผนดำเนินงาน
## Clock และไฟล์หลักฐาน
Wire7topics unchanged noHeader; use sidecar with trial_id/source_id/acquisition sequence at instrumented source. MCU source trigger and photodiode/encoder share acquisition clock when possible; otherwise two-way sync estimateoffset/drift with timestamps before/aftertrial, state residual+resolution uncertainty and reject cross-host subtraction when mapping unavailable. ROS bag/collector alone measures delivery or applied command not physical onset; source_latency null when identity ambiguous
Logtrial_id,condition,seed/participantID,source_id,acquisition/receive/decision/queue/apply/physicalonset,H/R/o/q,codeSHA,config,calibrationID. เก็บROSbagและsidecarCSV+manifestSHA256ทุกtrial รวมfailed/aborted;ห้ามใช้collectorreceiptแทนphysicalonset. Fitclockmappingก่อน/หลังtrialและรายงานuncertaintyจากresolution+mappingresidual;ถ้ายังวัดไม่ได้ให้N/A
## Robot และ calibration
ยังไม่ได้รัน: Ubuntu24.04/Jazzy host + tested MCU/Agent firmware (not supplied). Sensors button/touch/range and encoder+photodiode measurement. Confirm actual board,pins,power,neutral,sign,gear ratio and mechanical limits with instructor. Map abstract tilt/extend/nod to calibrated J2/J3/J4 only after linkage fit; J1 fixed neutral until a revised contract. Execute 2conditions x3trials x600s with one consenting operator/participant per pair and rests; report as repeated case study, not population inference
ก่อนจริงต้องให้ผู้สอนตรวจ wiring/limitsและกำหนดwatchdog deadlineจากcalibration; operatorเข้าถึงE-stopตัดenableได้ตลอด. near/fault/reconnect require validated neutral recovery; comm watchdog never hold stale moving trajectory. Stop trial immediately on unintended motion,collision risk,overcurrent/overtemperature or lowbattery using manufacturer thresholds verified for actual device; recordreasonandtimestamp then reset onlyafterinspection
## ความเสี่ยงและการควบคุม
Slewcapอาจบังผลhormoneจึงรายงานcapfractionร่วม; order/participantfatigueอาจbiasจึงreset,restและpartialcounterbalance; derivative/physicalnoiseใช้sampling/filterเดียวกันทั้งconditionsและเก็บraw. ไม่ถือcolor/stateชื่อemotionว่าเป็นหลักฐานความรู้สึกจริง. การทดลองมนุษย์ต้องให้ผู้สอนตรวจแผนและขอconsentก่อน ไม่มีผู้เข้าร่วมหรือข้อมูลจริงตอนนี้
## Timeline และผู้รับผิดชอบ
Proposed after09Nov2026: D1 instructor reviews proposal/equations; D2 implementAHMCPG+unit/fixture checks; D3 calibrateandteststop/clock; D4 simulation6x600s; D5 real6x600safterreadinessgate; D6 analyzealltrialsandreport. Totalplannedtrialtime120min plussetup/reset/rest; exactcalendar dates require team availability
อิทธิพลรับผิดชอบcode/analysis/report;ผู้ควบคุมhardwareและผู้ตรวจsafetyต้องยืนยันกับทีมก่อนD3. วันที่ปฏิทินรอยืนยันavailability ไม่รายงานแผนเป็นผลสำเร็จแล้ว
## เกณฑ์ส่งและที่มา
proposal.jsonมีparameter/provenance/metricmissingrulesครบ; check_proposal.pyตรวจเพียงcompletenessต้องให้ผู้สอนทบทวนvalidity. อ้างอิงLab03SO(2),Lab04AHM,Lab06course_model.py,Lab07README.mdและinterface_contract.json. Numericaltransportและmappingทั้งหมดเป็นproposedcoursemodel. Offline22s6runsที่ทำแล้วไม่แทน12trial600sและไม่แทนAHMCPGimplementation
