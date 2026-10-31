import ipaddress
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bridge'))
from bridge import Controller, FakeSDK, discovery_networks, discovery_reply, discovery_source_allowed


class APDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.subnets = {'wlan0': '192.168.5.0/24', 'ap0': '192.168.234.0/24'}
        self.add_interface('wlan0')
        self.add_interface('ap0')
        patcher = patch('bridge.interface_network', side_effect=lambda name: ipaddress.IPv4Network(self.subnets[name]))
        self.network_reader = patcher.start()
        self.addCleanup(patcher.stop)

    def add_interface(self, name, flags='0x1003', wifi=True):
        path = self.root / name
        path.mkdir(exist_ok=True)
        if wifi:
            (path / 'wireless').mkdir(exist_ok=True)
        (path / 'flags').write_text(flags)

    def allowed(self, address):
        return discovery_source_allowed('wlan0', address, self.root)

    def test_station_and_ap_clients_allowed_other_networks_rejected(self):
        self.assertTrue(self.allowed('192.168.5.21'))
        self.assertTrue(self.allowed('192.168.234.25'))
        self.assertFalse(self.allowed('192.168.235.25'))
        self.assertFalse(self.allowed('10.0.0.25'))

    def test_ap_only_works_when_station_has_no_ipv4(self):
        def read(name):
            if name == 'wlan0':
                raise OSError('No IPv4 address')
            return ipaddress.IPv4Network(self.subnets[name])
        self.network_reader.side_effect = read
        self.assertTrue(self.allowed('192.168.234.25'))
        self.assertFalse(self.allowed('192.168.5.21'))

    def test_inactive_or_missing_ap_is_not_admitted(self):
        (self.root / 'ap0' / 'flags').write_text('0x1002')
        self.assertFalse(self.allowed('192.168.234.25'))
        self.assertTrue(self.allowed('192.168.5.21'))
        (self.root / 'ap0' / 'flags').unlink()
        self.assertFalse(self.allowed('192.168.234.25'))

    def test_dhcp_subnet_change_is_read_for_next_query(self):
        self.assertTrue(self.allowed('192.168.234.25'))
        self.subnets['ap0'] = '10.44.8.0/23'
        self.assertFalse(self.allowed('192.168.234.25'))
        self.assertTrue(self.allowed('10.44.9.25'))
        self.assertFalse(self.allowed('10.44.10.25'))

    def test_ethernet_vpn_and_unconfigured_subnets_are_excluded(self):
        self.add_interface('eth0', wifi=False)
        self.add_interface('tun0', wifi=False)
        self.subnets.update({'eth0': '10.1.0.0/24', 'tun0': '10.2.0.0/24'})
        self.assertFalse(self.allowed('10.1.0.25'))
        self.assertFalse(self.allowed('10.2.0.25'))
        self.subnets['ap0'] = '0.0.0.0/0'
        self.assertFalse(self.allowed('10.2.0.25'))
        self.subnets['ap0'] = '0.0.0.0/24'
        self.assertEqual(discovery_networks('wlan0', self.root), [ipaddress.IPv4Network('192.168.5.0/24')])

    def test_both_subnets_keep_same_mac_and_do_not_take_control(self):
        sdk = FakeSDK()
        controller = Controller(sdk, {'mac': '02:12:34:56:78:90'})
        controller.ready = True
        query = json.dumps({'type': 'd1-discover-v1', 'request': 'a' * 32}).encode()
        replies = []
        for address in ('192.168.5.21', '192.168.234.25'):
            self.assertTrue(self.allowed(address))
            replies.append(discovery_reply(controller, query))
        self.assertEqual(replies[0], replies[1])
        self.assertEqual(replies[0]['mac'], '02:12:34:56:78:90')
        self.assertIsNone(controller.lease)
        self.assertEqual(sdk.moves, [])


if __name__ == '__main__':
    unittest.main()
