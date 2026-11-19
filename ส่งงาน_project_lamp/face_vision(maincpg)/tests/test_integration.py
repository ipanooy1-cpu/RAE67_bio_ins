import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from face_vision.lamp_controller import ExpressionGate, LampController, EXPRESSION_MAP
from face_vision.live_lamp import replay


def observation(seq, label='happy', detected=True, strength=.8, stream='test'):
    return {'schema': 1, 'stream_id': stream, 'seq': seq,
            'detected': detected, 'emotion': label, 'strength': strength}


def feed(controller, start, end, label):
    result = []
    for i in range(round(start * 20), round(end * 20) + 1):
        t = round(i / 20, 8)
        controller.observe(observation(i, label), t)
        result.append(controller.step(t))
    return result


class IntegrationTests(unittest.TestCase):
    def test_user_requested_mapping(self):
        self.assertEqual(EXPRESSION_MAP['angry'], 'Confused')
        self.assertEqual(EXPRESSION_MAP['surprised'], 'Confused')
        self.assertEqual(EXPRESSION_MAP['sad'], 'Sad')

    def test_waits_for_consistent_frames(self):
        g = ExpressionGate()
        g.push(observation(0), 0)
        g.push(observation(1), .1)
        self.assertEqual(g.current(.2), 'Neutral')
        g.push(observation(2), .3)
        self.assertEqual(g.current(.3), 'Happy')
        g.push(observation(3, 'sad'), .35)
        g.push(observation(4, 'happy'), .4)
        self.assertEqual(g.current(.4), 'Happy')

    def test_one_frame_is_not_enough(self):
        g = ExpressionGate()
        g.push(observation(0), 0)
        self.assertEqual(g.current(.4), 'Neutral')

    def test_stale_and_duplicate_cannot_keep_emotion_alive(self):
        g = ExpressionGate()
        for i, t in enumerate([0, .15, .3]):
            g.push(observation(i), t)
        self.assertFalse(g.push(observation(2), .7))
        self.assertEqual(g.current(.81), 'Neutral')
        self.assertEqual(g.reason, 'input_timeout')

    def test_bad_input_goes_neutral(self):
        for changes in [{'strength': float('nan')}, {'strength': 2}, {'detected': 'false'},
                        {'emotion': 'invalid'}, {'emotion': ['happy']}, {'detected': False}]:
            g = ExpressionGate(stable_s=0, min_samples=1)
            g.push(observation(0), 0)
            self.assertEqual(g.mode, 'Happy')
            bad = observation(1)
            bad.update(changes)
            g.push(bad, .1)
            self.assertEqual(g.current(.1), 'Neutral')

    def test_source_restart_requires_new_stability(self):
        g = ExpressionGate()
        for i, t in enumerate([0, .15, .3]):
            g.push(observation(i), t)
        g.push(observation(0, stream='restarted'), .35)
        self.assertEqual(g.mode, 'Neutral')

    def test_hormone_memory_across_changes(self):
        c = LampController()
        feed(c, 0, 2, 'happy')
        initial = c.hormones['Happy']
        feed(c, 2.05, 3, 'sad')
        self.assertGreater(c.hormones['Happy'], 0)
        self.assertLess(c.hormones['Happy'], initial)
        self.assertGreater(c.hormones['Sad'], 0)
        self.assertEqual(c.mode, 'Sad')

    def test_repeated_sad_frames_do_not_reset_ten_second_clock(self):
        c = LampController()
        samples = feed(c, 0, 11, 'sad')
        self.assertAlmostEqual(c.q[3], 60.0, places=7)
        self.assertLess(c.onset['Sad'], 1.0)
        # The live head starts at 90 and must not first rise to the offline 100.
        self.assertLess(max(s['centers_deg'][3] for s in samples), 91.0)

    def test_scheduler_overrun_holds_last_command(self):
        c = LampController()
        feed(c, 0, 1, 'happy')
        before = c.q.copy()
        s = c.step(4)
        self.assertTrue(s['scheduler_fault'])
        self.assertEqual(s['q_deg'], before)
        self.assertEqual(c.gate.mode, 'Neutral')

    def test_replay_outputs_finite_and_slew_limited(self):
        samples = replay(Path('examples/observations.jsonl'))
        self.assertEqual({s['mode'] for s in samples}, {'Neutral', 'Happy', 'Sad', 'Confused'})
        self.assertTrue(any(s['input_status'] == 'no_face' for s in samples))
        self.assertTrue(any(s['input_status'] == 'input_timeout' for s in samples))
        for s in samples:
            json.dumps(s, allow_nan=False)
            self.assertTrue(all(60 <= q <= 120 for q in s['q_deg']))
            self.assertTrue(all(0 <= h <= 1 for h in s['hormones'].values()))
        for a, b in zip(samples, samples[1:]):
            self.assertTrue(all(abs(x-y) <= 1.0000001 for x, y in zip(a['q_deg'], b['q_deg'])))

    def test_classifier_unknown_on_missing_or_invalid_blendshapes(self):
        # Execute just pure expression functions, without camera/ROS imports.
        source = ast.parse(Path('face_vision/vision_core.py').read_text(encoding='utf-8'))
        functions = [n for n in source.body if isinstance(n, ast.FunctionDef)
                     and n.name in ('clamp', 'classify_expression')]
        env = {'math': math}
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<classifier>', 'exec'), env)
        classify = env['classify_expression']
        self.assertEqual(classify([]), ('unknown', 0.0))
        self.assertEqual(classify([SimpleNamespace(category_name='mouthSmileLeft', score=math.nan)]), ('unknown', 0.0))
        happy = [SimpleNamespace(category_name=k, score=.8) for k in ('mouthSmileLeft', 'mouthSmileRight')]
        self.assertEqual(classify(happy), ('happy', .8))


if __name__ == '__main__':
    unittest.main()
