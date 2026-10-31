import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bridge'))
from bridge import Controller, FakeSDK, Refused
from highlevel import SENSORS


class HighLevelTests(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.sdk = FakeSDK()
        self.c = Controller(self.sdk, {'mac': '02:12:34:56:78:90'}, lambda: self.now)
        self.lease = self.c.handle('/connect', {'expected_mac': '02:12:34:56:78:90'})['lease']

    def begin(self, **flags):
        self.c.handle('/begin', {'lease': self.lease, **flags})

    def cmd(self, action, **args):
        return self.c.handle('/command', {'lease': self.lease, 'action': action, 'args': args})

    def advance(self, seconds):
        self.now += seconds
        self.c.beat = self.now  # Simulate timely heartbeats without a physical robot.
        self.c.tick()

    def test_greeting_requires_standing_and_waits_before_next_motion(self):
        self.begin()
        with self.assertRaises(Refused): self.cmd('greet')
        self.cmd('stand')
        self.assertGreaterEqual(self.cmd('greet')['duration_ms'], 4000)
        with self.assertRaises(Refused): self.cmd('lie')
        self.advance(4.2)
        self.cmd('lie')
        self.assertIn(('shakeHand',), self.sdk.calls)

    def test_high_risk_requires_per_job_permission_and_backflip_extra_permission(self):
        self.begin()
        self.cmd('stand')
        for action in ('jump', 'front_jump', 'backflip', 'two_leg_stand'):
            with self.assertRaisesRegex(Refused, '高風險'): self.cmd(action)
        self.c.handle('/stop', {'lease': self.lease})
        self.begin(allow_high_risk=True)
        with self.assertRaisesRegex(Refused, '後空翻'): self.cmd('backflip')
        self.c.handle('/stop', {'lease': self.lease})
        self.begin(allow_high_risk=True, allow_backflip=True)
        self.cmd('backflip')
        self.assertIn(('backflip',), self.sdk.calls)
        stop = self.c.handle('/stop', {'lease': self.lease})
        self.assertEqual(stop['stop'], 'not_confirmed')
        self.assertFalse(self.c.allow_high_risk)
        self.assertFalse(self.c.allow_backflip)
        with self.assertRaises(Refused): self.begin(allow_high_risk=True)

    def test_two_leg_exits_on_deadline_and_on_heartbeat_loss(self):
        for heartbeat_loss in (False, True):
            self.setUp()
            self.begin(allow_high_risk=True)
            self.cmd('stand')
            self.cmd('two_leg_stand', seconds=1)
            if heartbeat_loss:
                self.now += 1.3
                self.c.tick()
                self.assertIsNone(self.c.lease)
            else:
                self.advance(1.1)
            self.assertIn(('cancelTwoLegStand',), self.sdk.calls)
            self.assertIsNone(self.c.extra_kind)

    def test_attitude_stops_its_own_velocity_and_requires_standing_again(self):
        self.begin()
        self.cmd('stand')
        self.cmd('attitude', pitch=.05, seconds=.5)
        self.advance(.6)
        self.assertIn(('attitudeControl', 0, 0, 0, 0), self.sdk.calls)
        with self.assertRaises(Refused): self.cmd('forward', seconds=.5)
        self.cmd('stand')
        self.cmd('side_left', seconds=.5, speed=.1)
        self.assertEqual(self.sdk.moves[-1], (0, .1, 0))

    def test_parameter_limits_and_unknown_sensors_refused_without_motion(self):
        self.begin(allow_high_risk=True)
        self.cmd('stand')
        for action, args in [('move', {'vx': .2, 'vy': .2}), ('move', {'vy': .05}),
                             ('side_left', {'speed': .09}), ('side_right', {'seconds': True}),
                             ('attitude', {'height': .03}), ('attitude', {'pitch': float('nan')}),
                             ('two_leg_stand', {'seconds': 3}), ('telemetry', {'name': 'sendMotorCmd'})]:
            before = (list(self.sdk.moves), list(self.sdk.calls))
            with self.assertRaises(Refused): self.cmd(action, **args)
            self.assertEqual(before, (self.sdk.moves, self.sdk.calls))

    def test_all_sensor_groups_and_nonfinite_data_validation(self):
        self.begin()
        for name in SENSORS:
            value = self.cmd('telemetry', name=name)['value']
            if name.startswith('joints_'):
                self.assertEqual(set(value), {'abad', 'hip', 'knee'})
                self.assertTrue(all(len(v) == 4 for v in value.values()))
            elif name == 'mode': self.assertEqual(value, 0)
            else: self.assertEqual(len(value), 4 if name == 'quaternion' else 3)
        self.c.sensor_cache.clear()
        self.sdk.getRPY = lambda: [float('nan'), 0, 0]
        with self.assertRaisesRegex(Refused, '無效'): self.cmd('telemetry', name='rpy')

    def test_native_rejection_does_not_claim_posture_or_action_success(self):
        self.begin()
        self.sdk.standUp = lambda: 0x3011
        with self.assertRaisesRegex(Refused, '0x3011'): self.cmd('stand')
        self.assertEqual(self.c.posture, 'unknown')
        self.assertEqual(self.c.motion_end, 0)

    def test_stationary_mode_does_not_send_invalid_move_to_stop(self):
        self.begin()
        self.cmd('lie')
        self.c.handle('/end', {'lease': self.lease})
        self.assertEqual(self.sdk.moves, [])

    def test_two_leg_requires_exit_method_before_entry(self):
        self.begin(allow_high_risk=True)
        self.cmd('stand')
        self.sdk.cancelTwoLegStand = None
        with self.assertRaisesRegex(Refused, '退出雙腿'): self.cmd('two_leg_stand')
        self.assertFalse(any(call[0] == 'twoLegStand' for call in self.sdk.calls))

    def test_unknown_mode_still_attempts_zero_velocity(self):
        self.sdk.getCurrentCtrlmode = lambda: False  # Not the integer damping-mode code.
        self.c.stop()
        self.assertEqual(self.sdk.moves[-1], (0, 0, 0))

    def test_special_not_started_when_remaining_program_budget_too_short(self):
        self.begin(allow_high_risk=True, allow_backflip=True)
        self.cmd('stand')
        self.now += 58
        self.c.beat = self.now
        with self.assertRaisesRegex(Refused, '剩餘時間'): self.cmd('backflip')
        self.assertNotIn(('backflip',), self.sdk.calls)


if __name__ == '__main__':
    unittest.main()
