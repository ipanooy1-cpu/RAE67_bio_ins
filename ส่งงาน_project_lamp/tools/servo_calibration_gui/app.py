from __future__ import annotations

import argparse
import csv
import itertools
import json
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .tcl_bootstrap import prepare_tcl_runtime

prepare_tcl_runtime()

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .bus import MockServoBus, ServoFeedback
from .controller import CalibrationController, ControllerError, MotionResult
from .feetech_bus import FeetechBus
from .models import RobotConfig, load_config


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "servo_config.json"
OUTPUT_DIR = APP_DIR / "output"
LOG_FIELDS = (
    "timestamp",
    "mode",
    "operation",
    "servo_id",
    "before",
    "target",
    "present",
    "speed",
    "status",
    "message",
)


@dataclass(frozen=True)
class UiProjection:
    can_connect: bool
    can_disconnect: bool
    can_read: bool
    can_enable_motion: bool
    can_move: bool
    can_torque_off: bool


@dataclass(frozen=True)
class JogObservation:
    servo_id: int
    sign: int
    displacement: int


def make_jog_observation(
    result: MotionResult, sign: int
) -> JogObservation | None:
    displacement = result.present - result.before
    if displacement == 0:
        return None
    return JogObservation(result.servo_id, sign, displacement)


def output_paths(mock_mode: bool) -> tuple[Path, Path]:
    prefix = "mock_" if mock_mode else ""
    return (
        OUTPUT_DIR / f"{prefix}servo_test_log.csv",
        OUTPUT_DIR / f"{prefix}calibration_results.json",
    )


def is_shutdown_completion(result_name: str) -> bool:
    return result_name == "safe close"


def project_ui_state(controller: Any | None, busy: bool) -> UiProjection:
    connected = bool(controller is not None and controller.connected)
    faulted = bool(connected and controller.faulted)
    motion_enabled = bool(connected and controller.motion_enabled)
    external_torque = bool(connected and controller.external_torque_detected)
    return UiProjection(
        can_connect=not connected and not busy,
        can_disconnect=connected and not busy,
        can_read=connected and not busy,
        can_enable_motion=(
            connected
            and not busy
            and not faulted
            and not motion_enabled
            and not external_torque
        ),
        can_move=connected and not busy and not faulted and motion_enabled,
        can_torque_off=connected,
    )


def build_log_row(
    operation: str,
    *,
    mode: str = "",
    servo_id: int | str = "",
    before: int | str = "",
    target: int | str = "",
    present: int | str = "",
    speed: int | str = "",
    status: str = "ok",
    message: str = "",
) -> dict[str, str | int]:
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": mode,
        "operation": operation,
        "servo_id": servo_id,
        "before": before,
        "target": target,
        "present": present,
        "speed": speed,
        "status": status,
        "message": message,
    }


def append_csv_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow({field_name: row.get(field_name, "") for field_name in LOG_FIELDS})


def try_append_csv_log(path: Path, row: dict[str, Any]) -> str | None:
    try:
        append_csv_log(path, row)
    except OSError as exc:
        return str(exc)
    return None


def merge_direction_results(
    path: Path,
    updates: dict[str, dict[str, str]],
    *,
    mode: str,
) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"directions": {}}
    directions = data.setdefault("directions", {})
    for servo_id, values in updates.items():
        directions.setdefault(str(servo_id), {}).update(values)
    data["mode"] = mode
    data["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe Feetech SCS15 calibration GUI")
    parser.add_argument("--mock", action="store_true", help="run without hardware")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="construct and close the GUI without entering mainloop",
    )
    return parser.parse_args(argv)


@dataclass(order=True)
class _WorkItem:
    priority: int
    sequence: int
    generation: int
    name: str = field(compare=False)
    action: Callable[[], Any] = field(compare=False)
    on_success: Callable[[Any], None] | None = field(compare=False, default=None)
    cancellable: bool = field(compare=False, default=False)


@dataclass(frozen=True)
class _WorkResult:
    name: str
    value: Any = None
    error: Exception | None = None
    on_success: Callable[[Any], None] | None = None


class CommandCancelled(ControllerError):
    """A queued motion command invalidated by a later Torque Off request."""


class CommandWorker:
    def __init__(self) -> None:
        self.cancel_event = threading.Event()
        self.results: queue.Queue[_WorkResult] = queue.Queue()
        self._commands: queue.PriorityQueue[_WorkItem] = queue.PriorityQueue()
        self._sequence = itertools.count()
        self._generation = 0
        self._generation_lock = threading.Lock()
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(
        self,
        name: str,
        action: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        *,
        priority: int = 10,
        cancellable: bool = False,
    ) -> None:
        with self._generation_lock:
            generation = self._generation
        self._commands.put(
            _WorkItem(
                priority,
                next(self._sequence),
                generation,
                name,
                action,
                on_success,
                cancellable,
            )
        )

    def request_cancel(self) -> None:
        with self._generation_lock:
            self._generation += 1
        self.cancel_event.set()

    def allow_motion(self) -> None:
        self.cancel_event.clear()

    def stop(self) -> None:
        self._stopping.set()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                item = self._commands.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                with self._generation_lock:
                    stale = item.generation != self._generation
                if item.cancellable and stale:
                    raise CommandCancelled(f"{item.name} cancelled before execution")
                value = item.action()
            except Exception as exc:
                self.results.put(
                    _WorkResult(item.name, error=exc, on_success=item.on_success)
                )
            else:
                self.results.put(
                    _WorkResult(item.name, value=value, on_success=item.on_success)
                )
            finally:
                self._commands.task_done()


class ServoCalibrationApp:
    def __init__(self, root: tk.Tk, config: RobotConfig, *, mock_mode: bool) -> None:
        self.root = root
        self.config = config
        self.mock_mode = mock_mode
        self.controller: CalibrationController | None = None
        self.worker = CommandWorker()
        self.pending_count = 0
        self.last_jog_sign = 1
        self.last_jog_observation: JogObservation | None = None
        self.closing = False
        self.closed = False
        self.mode = "mock" if mock_mode else "real"
        self.log_path, self.direction_path = output_paths(mock_mode)

        self.port_var = tk.StringVar(value=config.port)
        self.baud_var = tk.StringVar(value=str(config.baud))
        self.servo_var = tk.StringVar(value=self._servo_choice(0))
        self.step_var = tk.IntVar(value=config.default_step)
        self.speed_var = tk.IntVar(value=config.default_speed)
        self.status_var = tk.StringVar(value="ยังไม่เชื่อมต่อ / Disconnected")
        self.last_jog_var = tk.StringVar(value="ยังไม่ได้กด + หรือ -")

        self._build_ui()
        self._refresh_ui_state()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._poll_worker)

    def _build_ui(self) -> None:
        self.root.title("Emotion Robotic Lamp — SCS15 Safe Test")
        self.root.geometry("1050x760")
        self.root.minsize(920, 680)
        try:
            ttk.Style(self.root).theme_use("clam")
        except tk.TclError:
            pass

        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(3, weight=1)

        connection = ttk.LabelFrame(container, text="1) Connection", padding=8)
        connection.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(connection, text="Port").grid(row=0, column=0, padx=4)
        self.port_entry = ttk.Entry(connection, textvariable=self.port_var, width=12)
        self.port_entry.grid(row=0, column=1, padx=4)
        ttk.Label(connection, text="Baud").grid(row=0, column=2, padx=4)
        self.baud_entry = ttk.Entry(connection, textvariable=self.baud_var, width=12)
        self.baud_entry.grid(row=0, column=3, padx=4)
        self.connect_button = ttk.Button(connection, text="Connect", command=self._connect)
        self.connect_button.grid(row=0, column=4, padx=4)
        self.disconnect_button = ttk.Button(
            connection, text="Disconnect", command=self._disconnect
        )
        self.disconnect_button.grid(row=0, column=5, padx=4)
        mode_text = "MOCK — ไม่ขยับหุ่น" if self.mock_mode else "REAL HARDWARE"
        ttk.Label(connection, text=mode_text).grid(row=0, column=6, padx=12)
        ttk.Label(connection, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=7, sticky="w", padx=4, pady=(6, 0)
        )

        safety = ttk.LabelFrame(container, text="2) Safety / Motion", padding=8)
        safety.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self.enable_button = ttk.Button(
            safety, text="ENABLE MOTION", command=self._enable_motion
        )
        self.enable_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.read_button = ttk.Button(safety, text="READ ALL", command=self._read_all)
        self.read_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.torque_button = tk.Button(
            safety,
            text="TORQUE OFF ALL",
            command=self._torque_off,
            bg="#b71c1c",
            fg="white",
            activebackground="#7f0000",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.torque_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Label(
            safety,
            text="ปิด Feetech FD ก่อน Connect • รองรับแขนไว้ก่อน Torque Off",
            foreground="#9a5b00",
            wraplength=430,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        pose = ttk.LabelFrame(container, text="3) Pose (Speed ต่ำ)", padding=8)
        pose.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
        self.home_button = ttk.Button(pose, text="GO HOME", command=lambda: self._move_pose("home"))
        self.home_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.center_button = ttk.Button(
            pose, text="GO CENTER", command=lambda: self._move_pose("center")
        )
        self.center_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(
            pose,
            text="คำเตือน: Home ID3=0 (ชนขอบ min), ID2=946 (ห่าง max 77)",
            foreground="#9a5b00",
            wraplength=430,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        jog = ttk.LabelFrame(container, text="4) เลือก Servo แล้วกด - / +", padding=8)
        jog.grid(row=2, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self.servo_combo = ttk.Combobox(
            jog,
            textvariable=self.servo_var,
            values=[self._servo_choice(servo_id) for servo_id in self.config.servos],
            state="readonly",
            width=18,
        )
        self.servo_combo.grid(row=0, column=0, columnspan=2, padx=4, pady=4, sticky="ew")
        self.servo_combo.bind("<<ComboboxSelected>>", self._on_servo_selected)
        ttk.Label(jog, text="Step").grid(row=1, column=0, padx=4, pady=4, sticky="e")
        self.step_combo = ttk.Combobox(
            jog,
            textvariable=self.step_var,
            values=self.config.allowed_steps,
            state="readonly",
            width=8,
        )
        self.step_combo.grid(row=1, column=1, padx=4, pady=4, sticky="w")
        ttk.Label(jog, text="Speed").grid(row=2, column=0, padx=4, pady=4, sticky="e")
        self.speed_combo = ttk.Combobox(
            jog,
            textvariable=self.speed_var,
            values=self.config.allowed_speeds,
            state="readonly",
            width=8,
        )
        self.speed_combo.grid(row=2, column=1, padx=4, pady=4, sticky="w")
        self.minus_button = ttk.Button(jog, text="−", command=lambda: self._jog(-1))
        self.minus_button.grid(row=3, column=0, padx=5, pady=8, sticky="ew")
        self.plus_button = ttk.Button(jog, text="+", command=lambda: self._jog(+1))
        self.plus_button.grid(row=3, column=1, padx=5, pady=8, sticky="ew")

        direction = ttk.LabelFrame(container, text="5) ทิศที่เห็นหลัง Jog", padding=8)
        direction.grid(row=2, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
        ttk.Label(direction, textvariable=self.last_jog_var).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=4, pady=4
        )
        self.direction_button_a = ttk.Button(direction, command=lambda: self._record_direction(0))
        self.direction_button_a.grid(row=1, column=0, padx=5, pady=8, sticky="ew")
        self.direction_button_b = ttk.Button(direction, command=lambda: self._record_direction(1))
        self.direction_button_b.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        self._update_direction_buttons()

        feedback = ttk.LabelFrame(container, text="6) Feedback", padding=6)
        feedback.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        feedback.rowconfigure(0, weight=1)
        feedback.columnconfigure(0, weight=1)
        columns = ("id", "joint", "position", "speed", "moving", "torque", "range")
        self.tree = ttk.Treeview(feedback, columns=columns, show="headings", height=6)
        labels = {
            "id": "ID",
            "joint": "Joint",
            "position": "Position",
            "speed": "Speed",
            "moving": "Moving",
            "torque": "Torque",
            "range": "Safe Range",
        }
        for column in columns:
            self.tree.heading(column, text=labels[column])
            self.tree.column(column, width=90 if column != "range" else 130, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        for servo_id, servo in self.config.servos.items():
            self.tree.insert(
                "",
                "end",
                iid=str(servo_id),
                values=(servo_id, servo.name, "-", "-", "-", "-", f"{servo.safe_min}..{servo.safe_max}"),
            )

        log_frame = ttk.LabelFrame(container, text="7) Log", padding=6)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=7, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        self.motion_widgets = [
            self.home_button,
            self.center_button,
            self.minus_button,
            self.plus_button,
        ]
        self.direction_widgets = [self.direction_button_a, self.direction_button_b]

    def _servo_choice(self, servo_id: int) -> str:
        return f"{servo_id} - {self.config.servos[servo_id].name}"

    def _selected_id(self) -> int:
        return int(self.servo_var.get().split("-", 1)[0].strip())

    def _set_ttk_enabled(self, widget: ttk.Widget, enabled: bool) -> None:
        widget.state(["!disabled"] if enabled else ["disabled"])

    def _refresh_ui_state(self) -> None:
        state = project_ui_state(self.controller, self.pending_count > 0)
        self._set_ttk_enabled(self.connect_button, state.can_connect)
        self._set_ttk_enabled(self.disconnect_button, state.can_disconnect)
        self._set_ttk_enabled(self.read_button, state.can_read)
        self._set_ttk_enabled(self.enable_button, state.can_enable_motion)
        for widget in self.motion_widgets:
            self._set_ttk_enabled(widget, state.can_move)
        can_record_direction = state.can_move and self.last_jog_observation is not None
        for widget in self.direction_widgets:
            self._set_ttk_enabled(widget, can_record_direction)
        self.torque_button.configure(state="normal" if state.can_torque_off else "disabled")

    def _submit(
        self,
        name: str,
        action: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        *,
        priority: int = 10,
        emergency: bool = False,
        cancellable: bool = False,
    ) -> None:
        if emergency:
            self.worker.request_cancel()
        self.pending_count += 1
        self.worker.submit(
            name,
            action,
            on_success,
            priority=priority,
            cancellable=cancellable,
        )
        self.status_var.set(f"กำลังทำงาน: {name}")
        self._refresh_ui_state()

    def _poll_worker(self) -> None:
        try:
            while True:
                result = self.worker.results.get_nowait()
                self.pending_count = max(0, self.pending_count - 1)
                try:
                    if result.error is not None:
                        self._handle_error(result.name, result.error)
                    elif result.on_success is not None and not self.closing:
                        result.on_success(result.value)
                except Exception as callback_error:
                    self._display_log_line(
                        f"UI callback error ({result.name}): {callback_error}"
                    )
                    self.status_var.set(f"UI ERROR: {callback_error}")
                finally:
                    self.worker.results.task_done()

                if self.closing and is_shutdown_completion(result.name):
                    if result.error is not None:
                        messagebox.showwarning(
                            "Torque Off อาจไม่สำเร็จ",
                            f"{result.error}\nโปรดตัดไฟ hardware อย่างปลอดภัย",
                        )
                    self._finish_close()
                    return
        except queue.Empty:
            pass
        finally:
            if not self.closed:
                self._refresh_ui_state()
                self.root.after(50, self._poll_worker)

    def _connect(self) -> None:
        try:
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("Baud ไม่ถูกต้อง", "Baud ต้องเป็นตัวเลข")
            return
        if self.mock_mode:
            positions = {servo_id: servo.home for servo_id, servo in self.config.servos.items()}
            bus = MockServoBus(positions)
        else:
            bus = FeetechBus(self.port_var.get().strip(), baud)
        self.controller = CalibrationController(
            self.config,
            bus,
            cancel_requested=self.worker.cancel_event.is_set,
        )

        def connected(readings: dict[int, ServoFeedback]) -> None:
            self._update_readings(readings)
            if self.controller and self.controller.external_torque_detected:
                self.status_var.set("Connected แต่พบ Torque เปิดอยู่ — กด TORQUE OFF ALL ก่อน")
            else:
                self.status_var.set("Connected — ยังไม่ขยับ จนกด ENABLE MOTION")
            self._write_log(build_log_row("connect", status="ok"))

        self._submit("connect", self.controller.connect, connected)

    def _disconnect(self) -> None:
        if self.controller is None:
            return

        def disconnected(_value: Any) -> None:
            self.status_var.set("Disconnected")
            self._write_log(build_log_row("disconnect"))
            self.controller = None

        self._submit("disconnect", self.controller.disconnect, disconnected)

    def _enable_motion(self) -> None:
        if self.controller is None:
            return
        self.worker.allow_motion()

        def enabled(_value: Any) -> None:
            self.status_var.set("Motion Enabled — ใช้ Step/Speed ต่ำ")
            self._write_log(build_log_row("enable_motion"))

        self._submit(
            "enable motion",
            self.controller.enable_motion,
            enabled,
            cancellable=True,
        )

    def _read_all(self) -> None:
        if self.controller is None:
            return

        def read(readings: dict[int, ServoFeedback]) -> None:
            self._update_readings(readings)
            self.status_var.set("อ่าน Feedback แล้ว")
            self._write_log(build_log_row("read_all"))

        self._submit("read all", self.controller.read_all, read)

    def _jog(self, sign: int) -> None:
        if self.controller is None:
            return
        servo_id = self._selected_id()
        step = int(self.step_var.get())
        speed = int(self.speed_var.get())
        self.last_jog_sign = sign
        self.last_jog_observation = None
        self.last_jog_var.set(f"กำลัง Jog ID{servo_id} {'+' if sign > 0 else '-'}")

        def action():
            result = self.controller.jog(servo_id, sign, step=step, speed=speed)
            return result, self.controller.read_all()

        def moved(payload) -> None:
            result, readings = payload
            self._update_readings(readings)
            self.last_jog_observation = make_jog_observation(result, sign)
            clipped = " (clamped)" if result.clipped else ""
            if self.last_jog_observation is None:
                self.status_var.set(f"ID{servo_id}: ไม่ได้ขยับ จึงยังบันทึกทิศไม่ได้")
                self.last_jog_var.set("Jog ล่าสุดไม่มีการเคลื่อนที่")
            else:
                self.status_var.set(
                    f"ID{servo_id}: {result.before} → {result.present}{clipped}"
                )
                self.last_jog_var.set(
                    f"Jog ล่าสุด ID{servo_id} {'+' if sign > 0 else '-'} — เลือกทิศที่เห็น"
                )
            self._log_motion(f"jog{'+' if sign > 0 else '-'}", result, speed)

        self._submit(
            f"jog {'+' if sign > 0 else '-'} ID{servo_id}",
            action,
            moved,
            cancellable=True,
        )

    def _move_pose(self, pose: str) -> None:
        if self.controller is None:
            return
        title = "HOME" if pose == "home" else "CENTER"
        speed = 50
        if not messagebox.askyesno(
            f"ยืนยัน GO {title}",
            f"หุ่นจะขยับทั้ง 4 แกนด้วย Speed {speed}\n"
            "ตรวจว่าไม่มีสิ่งกีดขวางแล้วหรือยัง?",
        ):
            return

        def action():
            results = self.controller.move_pose(pose, speed=speed)
            return results, self.controller.read_all()

        def moved(payload) -> None:
            results, readings = payload
            self._update_readings(readings)
            self.status_var.set(f"GO {title} สำเร็จ")
            for result in results.values():
                self._log_motion(pose, result, speed)

        self._submit(f"go {pose}", action, moved, cancellable=True)

    def _torque_off(self) -> None:
        if self.controller is None:
            return

        def off(_value: Any) -> None:
            self.status_var.set("TORQUE OFF — รองรับแขน/หัวไว้")
            self._write_log(build_log_row("torque_off_all"))

        self._submit(
            "TORQUE OFF ALL",
            self.controller.torque_off_all,
            off,
            priority=0,
            emergency=True,
        )

    def _record_direction(self, label_index: int) -> None:
        observation = self.last_jog_observation
        if (
            self.controller is None
            or not self.controller.motion_enabled
            or observation is None
        ):
            return
        servo_id = observation.servo_id
        label = self.config.servos[servo_id].direction_labels[label_index]
        try:
            updates = self.controller.record_direction(
                servo_id, observation.sign, label
            )
            merge_direction_results(self.direction_path, updates, mode=self.mode)
        except Exception as exc:
            self._handle_error("record direction", exc)
            return
        sign_label = "+" if observation.sign > 0 else "-"
        self.status_var.set(f"บันทึก ID{servo_id}: กด {sign_label} แล้ว {label}")
        self._write_log(
            build_log_row(
                "record_direction",
                servo_id=servo_id,
                message=f"{sign_label} => {label}",
            )
        )
        self.last_jog_observation = None
        self.last_jog_var.set("บันทึกทิศแล้ว — Jog ใหม่เพื่อบันทึกครั้งต่อไป")

    def _update_direction_buttons(self) -> None:
        servo_id = self._selected_id()
        labels = self.config.servos[servo_id].direction_labels
        self.direction_button_a.configure(text=labels[0])
        self.direction_button_b.configure(text=labels[1])

    def _on_servo_selected(self, _event=None) -> None:
        self.last_jog_observation = None
        self.last_jog_var.set("เปลี่ยน ID แล้ว — กรุณา Jog ใหม่")
        self._update_direction_buttons()
        self._refresh_ui_state()

    def _update_readings(self, readings: dict[int, ServoFeedback]) -> None:
        for servo_id, reading in readings.items():
            servo = self.config.servos[servo_id]
            self.tree.item(
                str(servo_id),
                values=(
                    servo_id,
                    servo.name,
                    reading.position,
                    reading.speed,
                    int(reading.moving),
                    "ON" if reading.torque_enabled else "OFF",
                    f"{servo.safe_min}..{servo.safe_max}",
                ),
            )

    def _log_motion(self, operation: str, result: MotionResult, speed: int) -> None:
        self._write_log(
            build_log_row(
                operation,
                servo_id=result.servo_id,
                before=result.before,
                target=result.target,
                present=result.present,
                speed=speed,
                message="clamped" if result.clipped else "",
            )
        )

    def _write_log(self, row: dict[str, Any]) -> None:
        row = dict(row)
        row["mode"] = self.mode
        log_error = try_append_csv_log(self.log_path, row)
        text = (
            f"{row['timestamp']} | {row['operation']} | ID={row['servo_id']} "
            f"target={row['target']} present={row['present']} "
            f"{row['status']} {row['message']}\n"
        )
        self._display_log_line(text.rstrip("\n"))
        if log_error:
            self._display_log_line(f"LOG FILE ERROR: {log_error}")

    def _display_log_line(self, text: str) -> None:
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _handle_error(self, operation: str, error: Exception) -> None:
        message = str(error)
        self.status_var.set(f"ERROR: {message}")
        self._write_log(
            build_log_row(operation, status="error", message=message)
        )
        if "cancelled" not in message.lower() and not self.closing:
            messagebox.showerror("Servo Error", message)

    def _on_close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self.status_var.set("กำลัง Torque Off และปิดพอร์ต...")
        self._refresh_ui_state()
        if self.controller is None:
            self._finish_close()
            return

        controller = self.controller

        def safe_close():
            controller.disconnect()

        self._submit(
            "safe close",
            safe_close,
            priority=0,
            emergency=True,
        )

    def _finish_close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.worker.stop()
        self.root.destroy()

    def shutdown_for_smoke_test(self) -> None:
        self.closing = True
        self.worker.stop()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(CONFIG_PATH)
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    app = ServoCalibrationApp(root, config, mock_mode=args.mock)
    if args.smoke_test:
        root.update_idletasks()
        app.shutdown_for_smoke_test()
        root.destroy()
        print("GUI smoke test passed")
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
