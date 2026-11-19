"""Export exact Python CPG/decoder samples for browser 3D playback.
Run from any directory: python scripts/export_lamp_motion.py
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lamp_cpg', ROOT / 'cpg_for_lamp.py')
lamp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lamp)


def build_export():
    modes = {}
    for name, preset in lamp.PRESETS.items():
        samples = lamp.simulate(name)
        modes[name] = {'preset': preset, 'samples': samples}
    return {'version': 1, 'source': 'cpg_for_lamp.py', 'dt': lamp.DT,
            'duration': lamp.DURATION, 'warmup': lamp.WARMUP_STEPS,
            'limits': lamp.JOINT_LIMITS, 'modes': modes}


if __name__ == '__main__':
    output = ROOT / 'public' / 'lamp-motion.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(build_export(), indent=2, allow_nan=False), encoding='utf-8')
    print(f'Exported all Python modes to {output}')
