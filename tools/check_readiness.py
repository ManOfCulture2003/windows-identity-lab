"""Read-only lab resource gate. No VM creation, installation or host changes."""
import argparse
import ipaddress
import json
import math
from pathlib import Path
import re


def object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate field: {key}")
        result[key] = value
    return result


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Input exceeds 64 KiB")
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=object_without_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite number')))


def exact_keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError('Missing or unknown fields')


def number(value, minimum, maximum, integer=False):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('Invalid numeric resource value')
    if integer and type(value) is not int:
        raise ValueError('Expected an integer resource value')


def validate_config(config):
    exact_keys(config, 'domain network_name subnet network_mode host_reserve_gib media_allowance_gib memory_headroom_gib vms')
    if config['domain'] != 'ad.northstar.test' or config['network_name'] != 'rh-identity-lab' or config['network_mode'] != 'internal':
        raise ValueError('Only the isolated fictional lab is supported')
    network = ipaddress.ip_network(config['subnet'], strict=True)
    if network != ipaddress.ip_network('10.77.0.0/24'):
        raise ValueError('Unexpected lab subnet')
    for key, minimum in [('host_reserve_gib', 40), ('media_allowance_gib', 16), ('memory_headroom_gib', 4)]:
        number(config[key], minimum, 1024, integer=True)
    if not isinstance(config['vms'], list) or len(config['vms']) != 2:
        raise ValueError('Project 1 needs exactly two guests')
    names, addresses, roles = set(), set(), set()
    expected = {'dc': 'RH-LAB-DC01', 'client': 'RH-LAB-CL01'}
    for vm in config['vms']:
        exact_keys(vm, 'name role address ram_gib disk_gib cpus')
        if not isinstance(vm['role'], str) or vm['role'] not in expected or vm['name'] != expected[vm['role']]:
            raise ValueError('Unexpected guest identity')
        address = ipaddress.ip_address(vm['address'])
        if address not in network or address in (network.network_address, network.broadcast_address):
            raise ValueError('Invalid guest address')
        if vm['name'] in names or address in addresses or vm['role'] in roles:
            raise ValueError('Duplicate guest identity or address')
        names.add(vm['name']); addresses.add(address); roles.add(vm['role'])
        number(vm['ram_gib'], 4, 16, integer=True)
        number(vm['disk_gib'], 64 if vm['role'] == 'client' else 50, 256, integer=True)
        number(vm['cpus'], 2, 8, integer=True)
    return config


def assess(config, host, scope='project1'):
    validate_config(config)
    if scope not in ('project1', 'server-install'):
        raise ValueError('Unknown resource-check scope')
    exact_keys(host, 'captured_at os_caption ram_available_gib disk_free_gib drive_type virtualbox_version hypervisor_present')
    for key in ('ram_available_gib', 'disk_free_gib'):
        number(host[key], 0, 1000000)
    if type(host['drive_type']) is not int or type(host['hypervisor_present']) is not bool:
        raise ValueError('Invalid host capability types')
    for key in ('captured_at', 'os_caption', 'virtualbox_version'):
        if not isinstance(host[key], str) or len(host[key]) > 256:
            raise ValueError('Invalid host metadata')
    from datetime import datetime, timezone
    captured = datetime.fromisoformat(host['captured_at'].replace('Z', '+00:00'))
    if captured.tzinfo is None:
        raise ValueError('Inventory timestamp must include a timezone')
    age = (datetime.now(timezone.utc) - captured).total_seconds()
    guests = config['vms'] if scope == 'project1' else [v for v in config['vms'] if v['role'] == 'dc']
    disk = sum(v['disk_gib'] for v in guests) + config['host_reserve_gib'] + config['media_allowance_gib']
    ram = sum(v['ram_gib'] for v in guests) + config['memory_headroom_gib']
    blockers = []
    if age < -60 or age > 900:
        blockers.append('Inventory is stale or future-dated; collect it again')
    if host['drive_type'] != 3:
        blockers.append('Use an approved fixed storage volume; removable storage is not selected automatically')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:r\d+)?', host['virtualbox_version']):
        blockers.append('VirtualBox was not detected with a recognized version')
    if 'Windows' not in host['os_caption']:
        blockers.append('This collector and plan target a Windows host')
    if host['disk_free_gib'] < disk:
        blockers.append(f'Disk budget short by {disk-host["disk_free_gib"]:.2f} GiB')
    if host['ram_available_gib'] < ram:
        blockers.append(f'Available RAM short by {ram-host["ram_available_gib"]:.2f} GiB')
    return {'scope': scope, 'resource_gate': 'blocked' if blockers else 'pass', 'required_disk_gib': disk,
            'required_available_ram_gib': ram, 'blockers': blockers,
            'deployment_verified': False,
            'remaining_gates': ['Guest license/media verification and user acceptance',
                                'VirtualBox release/support review and actual guest boot',
                                'Network isolation and backup destination verification']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'config/lab.json')
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--scope', choices=['project1', 'server-install'], default='project1',
                        help='Budget both guests (default), or only the initial Server installation')
    args = parser.parse_args()
    try:
        result = assess(read_json(args.config), read_json(args.inventory), args.scope)
    except (ValueError, TypeError, OSError, RecursionError, OverflowError) as exc:
        print(json.dumps({'resource_gate': 'invalid_input', 'error': str(exc), 'deployment_verified': False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['resource_gate'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
