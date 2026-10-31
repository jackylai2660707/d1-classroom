import pathlib
import sys
import threading
import unittest
import http.client
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bridge'))
from bridge import Controller, FakeSDK, Refused, make_server


class HeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.sdk = FakeSDK()
        self.sdk.mode = 1  # These tests exercise stopping an already-standing robot.
        self.controller = Controller(self.sdk, {'mac': '02:12:34:56:78:90'}, lambda: self.now)
        self.lease = self.controller.handle('/connect', {'expected_mac': '02:12:34:56:78:90'})['lease']

    def test_heartbeats_continue_while_native_posture_call_is_blocked(self):
        entered, release = threading.Event(), threading.Event()

        def slow_stand():
            entered.set()
            if not release.wait(3):
                raise RuntimeError('Test SDK action was not released')

        self.sdk.standUp = slow_stand
        self.controller.handle('/begin', {'lease': self.lease})
        with ThreadPoolExecutor(2) as pool:
            action = pool.submit(self.controller.handle, '/command', {'lease': self.lease, 'action': 'stand'})
            try:
                self.assertTrue(entered.wait(1))
                # Total action time exceeds the lease lifetime, but each heartbeat is on time.
                for _ in range(5):
                    self.now += .4
                    response = pool.submit(self.controller.handle, '/heartbeat', {'lease': self.lease}).result(timeout=.5)
                    self.assertEqual(response['battery'], 80)
                    self.assertEqual(self.controller.lease, self.lease)
            finally:
                release.set()
                action.result(timeout=1)
        self.controller.tick()
        self.assertEqual(self.controller.lease, self.lease)

    def test_heartbeat_does_not_call_native_sdk(self):
        def unexpected():
            raise AssertionError('Heartbeat must not call the SDK')
        self.sdk.getBatteryPower = unexpected
        self.sdk.checkConnect = unexpected
        self.now += .4
        self.assertEqual(self.controller.handle('/heartbeat', {'lease': self.lease})['battery'], 80)

    def test_late_or_wrong_heartbeat_cannot_revive_control(self):
        self.now += .4
        with self.assertRaises(Refused):
            self.controller.handle('/heartbeat', {'lease': 'wrong'})
        self.assertEqual(self.controller.beat, 10)
        self.now += .9
        with self.assertRaises(Refused):
            self.controller.handle('/heartbeat', {'lease': self.lease})
        self.assertEqual(self.controller.beat, 10)
        self.controller.tick()
        self.assertIsNone(self.controller.lease)
        self.assertEqual(self.sdk.moves[-1], (0, 0, 0))

    def test_low_battery_monitor_still_stops_job_and_updates_cache(self):
        self.controller.handle('/begin', {'lease': self.lease})
        self.sdk.power = 29
        self.controller.refresh()
        self.assertEqual(self.controller.job_end, 0)
        self.assertEqual(self.sdk.moves[-1], (0, 0, 0))
        self.assertEqual(self.controller.handle('/heartbeat', {'lease': self.lease})['battery'], 29)

    def test_connection_failure_monitor_still_stops_job(self):
        self.controller.handle('/begin', {'lease': self.lease})
        self.sdk.checkConnect = lambda: False
        self.controller.refresh()
        self.assertFalse(self.controller.ready)
        self.assertEqual(self.controller.job_end, 0)
        self.assertEqual(self.sdk.moves[-1], (0, 0, 0))

    def test_http_heartbeats_reuse_one_tcp_connection(self):
        server = make_server(self.controller, ('127.0.0.1', 0))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = http.client.HTTPConnection(*server.server_address, timeout=2)
        try:
            ports = []
            for _ in range(5):
                client.request('POST', '/heartbeat', json.dumps({'lease': self.lease}), {'Content-Type': 'application/json'})
                ports.append(client.sock.getsockname()[1])
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.version, 11)
                self.assertEqual(json.loads(response.read())['battery'], 80)
                self.assertIsNotNone(client.sock)
            self.assertEqual(len(set(ports)), 1)
            # Malformed/unread bodies must close rather than poison that connection.
            client.request('POST', '/heartbeat', b'garbage', {'Content-Length': 'bad'})
            response = client.getresponse()
            self.assertEqual(response.status, 400)
            self.assertEqual(response.getheader('Connection'), 'close')
            response.read()
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
