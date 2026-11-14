# ใบงาน Lab04 ฉบับกรอกผลจริง

ชื่อ/รหัส: อิทธิพล แป้นอ้อย / 6752500053 | กลุ่ม: __________ | วันที่รันจริง: 29/10/2026 | code commit: c5b68bf

## A ก่อนรัน

Prediction ในส่วนนี้มาจากร่างที่ผู้เรียนส่งไว้ในแชตก่อนผู้ช่วยรันชุด completed_20261109 ไม่ได้อ้างว่าเป็น prediction ที่คิดขึ้นใหม่หลังเห็นผล

```text
S → P ─────────────────────┐
H_old → C ────────────────(−) → H_new = clamp(H_old + dt(P−C−B))
H_old → R_old → B ────────(−)                ↓
                                          R_new → bounded phi/stride
H_new ถูกเก็บเป็น H_old ของรอบถัดไป
```

S เพิ่ม P; H_old เพิ่ม clearance C; receptor จาก H_old เพิ่ม binding B; ผลสุทธิเปลี่ยน H แล้ว receptor อ่านสถานะใหม่ก่อน mapping จึงมีความจำเชิงเวลา

|Comparison|Prediction ก่อนรัน|เหตุผลจากสมการ|ผลจริงหลังรัน|
|---|---|---|---|
|C2 vs C1|เพิ่มเร็วและอาจชนเพดาน|prod .8→1.2 เพิ่ม P|latency .10 vs .15 s; rise1.05 vs2.70 s; peak1 vs .999715; clamp .29 vs0|
|C3 vs C1|สะสมมากและลดช้า|clear .6→.25 ลด C|AUC11.389145 vs9.999644; recovery5.10 vs2.85 s|
|C4 vs C1|สะสมมากและลดช้า|bind .2→0 ทำให้ B=0|AUC10.754720 vs9.999644; recovery3.80 vs2.85 s|
|C0 vs C1|ตอบตรง ไม่มีความจำ|R=S ไม่มี H|latency .05 vs.15 s; recovery .05 vs2.85 s; C0 H=N/A|

C2/C3 peak เท่ากันที่1เนื่องจาก upper bound ต้องดู AUC/recovery/clamp fraction ร่วมด้วย C1 peak .999715 ยังไม่ถูก upper-clamp

## B โค้ดและคำนวณมือ

อ้างอิง README/worksheet ของ Lab04 รายวิชา RAE67 Bio-Inspired Robotics ซึ่งอธิบายสมการต้นทาง Hc(t)=βHc(t−1)+Hg(t)−Hr(t), Hg(t)=αf(S(t)), Hr(t)=ΣγᵢReceptorᵢ(t) และอ้าง Homchanthanakul et al. (2019), DOI 10.1109/IROS40897.2019.8968580 แบบจำลองที่รันเป็น proposed course model แบบ Euler ไม่ใช่การทำซ้ำผลของบทความ และไม่แทน β ด้วย k_clear โดยตรง

receptor(.2,.1,.5)=(.2−.1)/(.5−.1)=.25; function ตรวจ finite และ h_max>h_min แล้วจำกัดผล0–1

C1: prod=.8, clear=.6, bind=.2, dt=.05, S=1 ใช้สถานะเก่าสำหรับทุกอัตรา

|input_time_s|time_s|P|C|B|H_raw|H|R|phi rad|stride m|
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|10.00|10.05|.8|0|0|.04|.04|.04|.208|.0554|
|10.05|10.10|.8|.024|.008|.0784|.0784|.0784|.21568|.055784|

รอบ1: H=0+.05(.8−0−0)=.04; รอบ2: H=.04+.05(.8−.024−.008)=.0784 ตรวจตรงกับ CSV แล้ว input_time_s เป็นต้นช่วงอ่านinput ส่วน time_s เป็นสถานะหลังupdate ต่างกัน dt=.05 s ไม่ใช่การวัดเวลาตอบสนองมอเตอร์จริง

Checker ผ่าน13/13 เก็บ output ใน checker.txt; ไม่เปลี่ยนโค้ด student_hormone.py ในการรันครั้งนี้

## C Controlled comparison

| Condition | peak_H | AUC_H (H·s) | latency (s) | rise (s) | recovery (s) | upper clamp fraction | phi TV (rad) |
|---|---|---|---|---|---|---|---|
| C0 | N/A | N/A | 0.050000 | 0.000000 | 0.050000 | N/A | 0.400000 |
| C1 | 0.999715 | 9.999644 | 0.150000 | 2.700000 | 2.850000 | 0.000000 | 0.399829 |
| C2 | 1.000000 | 10.672410 | 0.100000 | 1.050000 | 2.850000 | 0.290000 | 0.399943 |
| C3 | 1.000000 | 11.389145 | 0.150000 | 1.450000 | 5.100000 | 0.273333 | 0.397890 |
| C4 | 1.000000 | 10.754720 | 0.150000 | 1.700000 | 3.800000 | 0.258333 | 0.399548 |

AUC ใช้ left rectangle ΣH(t_k)dt 600 intervals ไม่รวม endpoint เพิ่มอีก dt; upper clamp fraction มี denominator600 updates; riseวัด10→90%ของ peak_R ใน on-window[10,20]; recoveryวัดหลัง20 sจนR≤10%ของ peakก่อนปิด

C3 ฟื้นช้ากว่า C1=5.10−2.85=2.25 s; C2/C3 peak=1เท่ากัน แต่ AUC ต่าง .716735 H·s, recovery ต่าง2.25 s และ clamp fractionต่าง .016667 แยกระบบได้ C0ไม่มีสถานะH จึงใช้ N/A ไม่แทน0 TVต่ำไม่ยืนยัน gait เพราะLabนี้ไม่รันCPG/body และค่าปลายtrialมีผลต่อTV

## D Extreme tests และ handoff

|Profile C1|หลักฐานจาก CSV/metrics|ผล|
|---|---|---|
|zero|ทุก601states H=R=0; phi=.20 stride=.055; fault0|ผ่าน|
|one|S=1ครบ600updates; peak_H=.999999999977; upper clamp0; AUC28.750000 H·s|ผ่าน เข้าใกล้1แต่ไม่ได้เกิดupper clamp|
|spike|S=1เพียงinterval input10.00; state10.05 H=.04 และค่อยลด; peak_H=.04|ผ่าน|
|fault|NaN1sample input15.00; state15.05 fault1 H/R/raw/P/C/B=0 phi=.20 stride=.055; state15.10 fault0 H=.04|ผ่าน|

Timing latency/rise/recovery ของทั้ง4 extreme profiles เป็น N/A ตามนิยาม Lab เพราะไม่ใช่ step protocol ไม่ใช้ศูนย์แทน N/A สำหรับ fault input เก็บ nan ใน CSV เป็นสิ่งเร้าที่จงใจฉีด แต่ controller output ไม่เป็นNaN

ใช้ contract เดิมจริงจาก lab_03/results/week4_bridge/handoff_contract.json โดยระบุ --contract แล้ว C1 CSV ตรงกับการใช้ contract ของLab04ทุกแถว

|R|phi rad|stride_half m|
|---:|---:|---:|
|0|.20|.055|
|1|.40|.065|

คง alpha=1.10, dt=.05, lift=.03; bounds phi[.10,.45], stride[.040,.070] ซอฟต์แวร์clampนี้ไม่ใช่ขอบเขตมุม/ความเร็ว/แรงบิดเซอร์โว ไม่ทดแทนwatchdog/E-stop Lab04ยังไม่ทดสอบgait, energy, terrain, stability, physical latencyหรือhardware safety

## E สรุปสามย่อหน้า

กลไกฮอร์โมนใช้ S กระตุ้น P=k_prod S ขณะที่ C=k_clear H_old และ B=k_bind R_old เป็นอัตรากำจัดที่คำนวณจากสถานะเก่าชุดเดียวกัน ก่อนอัปเดต H_new=clamp(H_old+dt(P−C−B),0,1) และอ่าน receptor ใหม่ R=H ภายใต้ bounds 0–1 จึงเก็บประวัติของสิ่งเร้าและค่อย ๆ กลับสู่ปกติ ต่างจาก C0 ซึ่ง R=S โดยตรง จากนั้น bounded mapping ส่ง phi=clamp(.20+.20R,.10,.45) rad และ stride=clamp(.055+.010R,.040,.070) m โดยไม่สั่งมอเตอร์ตรง อ้างอิง README/worksheet ของ Lab04 รายวิชา RAE67 Bio-Inspired Robotics ซึ่งอธิบายสมการต้นทาง Hc(t)=βHc(t−1)+Hg(t)−Hr(t), Hg(t)=αf(S(t)), Hr(t)=ΣγᵢReceptorᵢ(t) และอ้าง Homchanthanakul et al. (2019), DOI 10.1109/IROS40897.2019.8968580 แบบจำลองที่รันเป็น proposed course model แบบ Euler ไม่ใช่การทำซ้ำผลของบทความ และไม่แทน β ด้วย k_clear โดยตรง

ข้อมูลสนับสนุน prediction ที่บันทึกไว้ก่อนการรันชุดนี้: C2 เพิ่ม production ทำให้ latency ลดจาก C1 .15 เป็น .10 s และ rise ลดจาก 2.70 เป็น 1.05 s; C3 ลด clearance ทำให้ recovery เพิ่มจาก 2.85 เป็น 5.10 s (ช้ากว่า 2.25 s); C4 ตัด binding ทำให้ recovery เป็น 3.80 s (ช้ากว่า C1 .95 s) C2/C3 มี peak_H=1 เท่ากันเพราะ saturation แต่ AUC ต่างกัน 10.672410 กับ 11.389145 H·s และ upper-clamp fraction ต่างกัน .290000 กับ .273333 จึงต้องใช้หลาย metric ส่วน C0 ไม่มี H ทำให้ peak_H/AUC/clamp fraction เป็น N/A ไม่ใช่ศูนย์ ค่า latency/recovery .05 s ของ C0 เป็นผลของ post-update sampling ไม่ใช่ความหน่วงทางกายภาพ

ขอบเขตหลักฐานจำกัดที่ hormone subsystem แบบ deterministic; TV ต่ำกว่าไม่ได้พิสูจน์ gait ที่ดีขึ้น โดย phi TV ของ C3=.397890 rad ต่ำกว่า C1=.399829 rad เล็กน้อยส่วนหนึ่งเพราะ H ของ C3 ยังเหลือมากกว่าที่ปลาย trial ไม่ใช่หลักฐานว่าหุ่นยนต์เดินดีกว่า ผล zero คง H=0; spike มี S=1 หนึ่ง interval ที่ 10.00 s ให้ H=.04 ที่ 10.05 s; fault NaN ที่ input15.00 ทำให้ H=R=0 และ phi=.20/stride=.055 ที่ state15.05 ก่อนสะสมใหม่ H=.04 ที่15.10 s ขอบเขตซอฟต์แวร์และ fallback นี้ไม่ใช่ actuator limits, watchdog หรือ E-stop การทดลอง Lab05 ควรเชื่อม hormone–CPG เปรียบเทียบ fixed/direct/hormone/binding-ablation ใช้ schedule และ warmup เดียวกัน และแยก phi-only/stride-only เพื่อศึกษาสาเหตุ ก่อนขยายสู่ contact feedback และการทดลองฮาร์ดแวร์ที่สอบเทียบแล้ว

## Checklist และไฟล์หลักฐาน

- [x] โค้ด student_hormone.py และ source snapshot
- [x] comparison CSV 5ไฟล์ ใน comparison/
- [x] extreme CSV 4ไฟล์ ใน zero/one/spike/fault
- [x] config.json ทุกrun และ manifest.json พร้อมSHA256/commit
- [x] กราฟSVGและ report.html ทุกrun
- [x] metrics.json/metrics.csv ทุกrun
- [x] รายงาน REPORT_TH.md และ REPORT_TH.html
- [x] คำสั่งรันซ้ำ README_REPRODUCE.md
- [ ] ผู้เรียนเติมกลุ่ม ตรวจความถูกต้องของชื่อ/วันที่ และอ่านอธิบายผลด้วยตนเองก่อนส่ง
