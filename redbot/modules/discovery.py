"""
Data structure definitions:

Hosts:
    Format for storing hosts, hostname or IP address as key.

    {
        hostname: {
                        'ports': [port1, port2, port3, ...],
                        'target': target,
                    },
        hostname: {
                        ...
                    },
        ...
    }


"""
import json
import socket
from time import sleep, time
from typing import Dict

import requests
from celery import group
from libnmap.parser import NmapParser, NmapParserException
from libnmap.process import NmapProcess

from redbot.core.async import celery
from redbot.core.models import targets, storage
from redbot.core.utils import log, get_core_setting
from redbot.modules import Attack
from redbot.settings import TEAM_DOMAIN_SUFFIX
from redbot.web.web import socketio, send_msg


class NmapScan(Attack):
    name = "nmap"
    exempt = True

    settings = {
        'scan_options': {
            'name': 'Scan Options',
            'default': '-sT -n -T5',
            'description': 'Accepts any nmap command-line flags'
        },
        'ports': {
            'name': 'Target Ports',
            'default': ",".join((str(n) for n in (21, 22, 23, 80, 443))),
            'description': 'Comma-separated TCP ports to scan'
        },
        'scan_interval': {
            'name': 'Scan Interval',
            'default': 60 * 10,
            'description': 'How often (in seconds) to perform nmap scans.'
        }
    }

    @classmethod
    def push_update(cls, data):
        if data.get('status') == 'RESULTS':
            hosts = {host[0]: {'ports': host[1], 'target': data['result']['target']} for host in data['result']['hosts']}
            update_hosts(hosts)
            log("Completed nmap scan against " + data['result']['target'], "nmap", "success")
        socketio.emit('nmap progress', data, broadcast=True)

    @classmethod
    def run_scans(cls) -> None:
        clear_targets()
        g = group(nmap_scan.s(target) for target in targets).delay()
        g.get(on_message=cls.push_update, propagate=False)
        send_msg('Scan finished.')
        socketio.emit('scan finished', {}, broadcast=True)


cls = NmapScan


def get_url() -> str:
    return get_core_setting('iscore_url') + '/api/v1/'


def clear_targets() -> None:
    storage.delete('hosts')
    storage.delete('targets')
    storage.set('last_scan', 0)


@celery.task
def dns_lookup(hostname: str) -> str:
    try:
        return {hostname: socket.gethostbyname(hostname)}  # IScorE URLs are not URLs. This call is also IPv4 only.
    except socket.gaierror:
        return {hostname: hostname}


def update_iscore_targets() -> None:
    r = requests.get(get_url() + 'servicestatus', headers={'Content-Type': 'application/json'}).json()
    hosts = {}
    records = {}
    if get_core_setting('iscore_api'):
        r2 = requests.get(get_url() + 'dns', headers={
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + get_core_setting('iscore_api').strip()
        }).json()
        for rec in r2:
            records['{}.team{}.{}'.format(rec['name'], rec['team_number'], TEAM_DOMAIN_SUFFIX)] = rec['value']
    else:
        lookups = group(dns_lookup.s(host['service_url'] for host in r))
        [records.update(l) for l in lookups.get()]
    for host in r:
        hostn = records.get(host['service_url'], host['service_url'])
        if not hosts.get(hostn):
            hosts[hostn] = {'ports': [],
                            'target': "Team " + str(host['team_number'])
                            }
        if not hosts[hostn].get('hostname'):
            hosts[hostn]['hostname'] = host['service_url']
        if not host['service_status'] == "down":
            hosts[hostn]['ports'].append(host['service_port'])
    update_hosts(hosts)
    send_msg('IScorE update finished.')
    socketio.emit('scan finished', {}, broadcast=True)


def get_hosts() -> Dict:
    return json.loads(storage.get('hosts') or "{}")


def update_hosts(hosts) -> None:
    current_hosts = get_hosts()
    for host in hosts:
        if host in current_hosts:
            current_hosts[host]['ports'] += host['ports']
        else:
            current_hosts[host] = hosts[host]
    storage.set('hosts', json.dumps(current_hosts))


def get_last_scan() -> int:
    return int(storage.get('last_scan') or 0)


def scheduled_scan(force: bool = False):
    discovery_type = get_core_setting('discovery_type')
    if 'nmap' in discovery_type or 'both' in discovery_type:
        if force or int(time()) - get_last_scan() > NmapScan.get_setting('scan_interval'):
            print("scanning now")
            NmapScan.run_scans()
        else:
            print("no need to scan")
    if 'iscore' in discovery_type or 'both' in discovery_type:
        update_iscore_targets()
    storage.set('last_scan', int(time()))


@celery.task(bind=True)
def nmap_scan(self, target: Dict[str, str]) -> None:
    options = NmapScan.get_setting('scan_options') + " " + NmapScan.get_setting('ports')
    nm = NmapProcess(target['range'], options=options)
    nm.run_background()
    while nm.is_running():
        self.update_state(state="PROGRESS", meta={'progress': nm.progress,
                                                  'target': target['name']})
        sleep(2)
    try:
        report = NmapParser.parse(nm.stdout)
    except NmapParserException as e:
        print(e)
    h = [(host.address, [p[0] for p in host.get_open_ports()]) for host in report.hosts if host.is_up()]
    self.update_state(state="RESULTS", meta={'hosts': h,
                                             'target': target['name']})
