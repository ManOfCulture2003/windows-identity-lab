import copy
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness', ROOT / 'tools/check_readiness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.config = module.read_json(ROOT / 'config/lab.json')
        self.host = dict(captured_at=datetime.now(timezone.utc).isoformat(), os_caption='Windows 11 Home',
                         ram_available_gib=12, disk_free_gib=170, drive_type=3,
                         virtualbox_version='7.0.18r162988', hypervisor_present=True)

    def test_exact_resource_boundary_is_not_deployment_proof(self):
        result = module.assess(self.config, self.host)
        self.assertEqual(result['resource_gate'], 'pass')
        self.assertFalse(result['deployment_verified'])
        self.assertTrue(result['remaining_gates'])

    def test_both_resource_shortages_reported(self):
        self.host.update(ram_available_gib=8.9, disk_free_gib=127)
        self.assertEqual(len(module.assess(self.config, self.host)['blockers']), 2)

    def test_negative_nonfinite_bool_and_string_measurements_rejected(self):
        for value in [-1, float('nan'), float('inf'), True, '170', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.assess(self.config, dict(self.host, disk_free_gib=value))

    def test_stale_future_and_naive_timestamp(self):
        for hours in [-1, 1]:
            self.host['captured_at'] = (datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()
            self.assertEqual(module.assess(self.config, self.host)['resource_gate'], 'blocked')
        self.host['captured_at'] = '2026-11-09T15:00:00'
        with self.assertRaises(ValueError): module.assess(self.config, self.host)

    def test_unknown_missing_and_duplicate_fields(self):
        for change in [dict(self.config, password='no'), {k:v for k,v in self.config.items() if k!='vms'}]:
            with self.assertRaises(ValueError): module.validate_config(change)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'bad.json'; p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError): module.read_json(p)
            p.write_text(' ' * 65537)
            with self.assertRaises(ValueError): module.read_json(p)

    def test_unsafe_network_and_foreign_domain_rejected(self):
        for key,value in [('network_mode','bridged'),('domain','personal.example'),('subnet','192.168.1.0/24')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.validate_config(dict(self.config, **{key:value}))

    def test_duplicate_or_invalid_guest_rejected(self):
        for key,value in [('name','RH-LAB-DC01'),('address','10.77.0.10'),('address','10.77.0.255'),('address','8.8.8.8'),('disk_gib',63),('ram_gib',True),('role',[]),('cpus',2.0)]:
            config=copy.deepcopy(self.config);config['vms'][1][key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): module.validate_config(config)

    def test_removable_drive_and_missing_virtualbox_block(self):
        result=module.assess(self.config,dict(self.host,drive_type=2,virtualbox_version=''))
        self.assertEqual(len(result['blockers']),2)

    def test_resource_reserves_cannot_be_bypassed(self):
        for key in ['host_reserve_gib','media_allowance_gib','memory_headroom_gib']:
            with self.assertRaises(ValueError): module.validate_config(dict(self.config,**{key:0}))


if __name__ == '__main__': unittest.main()
