# แผนการทดลองก่อนรัน

จัดทำโดยผู้ช่วยตามคำขอให้ทำLab05ต่อ ไม่ใช่การบันทึกความคิดเดิมของผู้เรียน และเขียนก่อนรันผลชุดนี้

H1: B2 hormone จะมี max-step ของ phi/stride ต่ำกว่า B1 direct แต่ command latency/recovery มากกว่า ไม่คาดว่า TV ต้องลดมากเพราะช่วงการเปลี่ยนแปลงรวมใกล้กัน
H2: B3ตัดเฉพาะbinding term จึงยังมีH state/clearanceและmemory คาดว่าฟื้นช้ากว่าB2และอาจชนเพดานมากขึ้น
H3 phi-only: คงstride=.055 m คาดว่าเปลี่ยนจังหวะfrequency; stride-only: คงphi=.20 rad คาดว่าfrequencyใกล้B0แต่distanceเปลี่ยนในkinematic model ไม่อ้างแรง/พลังงาน
Contact: matched SI1/SIF0; gain-offset SI1แต่MAE>0; all-inverted SI−1แต่SIF0; constant SI=N/A; NaNหนึ่งsampleจะกระทบหลายwindows ไม่แทนN/Aด้วย0

Protocol: dt=.05 s, duration30 s, commonCPGwarmup10 s phi=.20 alpha1.10, initial(.1,0), S0/1/0ที่0/10/20 s ทุกconditionใช้scheduleเดียวกัน ไม่มีrandom independent repetitions
