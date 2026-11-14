"""Lab04: complete the two TODOs. Use only the Python standard library."""
import math

def receptor(h, h_min=0.0, h_max=1.0):
    if not all(math.isfinite(x) for x in (h, h_min, h_max)):
        raise ValueError("ค่าทั้งหมดต้องเป็นจำนวน finite")

    if h_max <= h_min:
        raise ValueError("h_max ต้องมากกว่า h_min")

    # คำนวณค่าตอบสนอง
    r = (h - h_min) / (h_max - h_min)
    
    return max(0.0, min(1.0, r))


def step(h, stimulus, dt, prod, clear, bind):
    # ข้อมูลผิดปกติ: รีเซ็ตและแจ้ง fault
    if not math.isfinite(stimulus) or not 0.0 <= stimulus <= 1.0:
        return {
            "h": 0.0, "r": 0.0, "raw": 0.0,
            "p": 0.0, "c": 0.0, "b": 0.0,
            "fault": 1,
        }

    # อ่าน receptor จากฮอร์โมนเดิม
    r_old = receptor(h)

    # อัตราการสร้าง การสลาย และ binding
    p = prod * stimulus
    c = clear * h
    b = bind * r_old

    # อัปเดตฮอร์โมน แล้วจำกัดให้อยู่ในช่วง 0–1
    raw = h + dt * (p - c - b)
    h_new = max(0.0, min(1.0, raw))

    return {
        "h": h_new,
        "r": receptor(h_new),
        "raw": raw,
        "p": p,
        "c": c,
        "b": b,
        "fault": 0,
    }
