"""
Data structure definitions:

Targets:
    Original format for storing hosts, grouped by target. Used by the frontend graph and table.

    {
        target:
            (
                (ip_address1, ([port1, proto], [port2, proto], [port3, proto])),
                (ip_address2, ...)
            )
        target:
            ...
    }

Hosts:
    Newer format for storing hosts, hostname or IP address as key. Much easier to use everywhere else.

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
from redbot.settings import ISCORE_URL
from redbot.web.web import socketio, send_msg

URL = ISCORE_URL + '/api/v1/servicestatus'


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
            'name': 'Scan Interval (seconds)',
            'default': 60 * 10
        }
    }

    @classmethod
    def push_update(cls, data):
        if data.get('status') == 'RESULTS':
            hosts = {data['result']['target']: data['result']['hosts']}
            update_hosts(hosts)
            log("Completed nmap scan against " + data['result']['target'], "nmap", "success")
        socketio.emit('nmap progress', data, broadcast=True)

    @classmethod
    def run_scans(cls) -> None:
        storage.delete('hosts')
        g = group(nmap_scan.s(target) for target in targets).delay()
        g.get(on_message=cls.push_update, propagate=False)
        send_msg('Scan finished.')
        socketio.emit('scan finished', {}, broadcast=True)
        storage.set('last_scan', int(time()))


cls = NmapScan


def update_iscore_targets() -> None:
    r = requests.get(URL, headers={'Content-Type': 'application/json'}).json()
    hosts = {}
    for host in r:
        address = socket.gethostbyname(host['service_url'])  # IScorE URLs are not URLs
        if not hosts.get(address):
            hosts[address] = {'ports': [],
                              'target': "Team " + str(host['team_number'])
                              }
        if not hosts[address].get('hostname'):
            hosts[address]['hostname']: host['service_url']
        if not host['service_status'] == "down":
            hosts[address]['ports'].append(host['service_port'])
    update_hosts(hosts)


def get_hosts() -> Dict:
    return json.loads(storage.get('hosts') or "{}")


def get_targets() -> Dict:
    return json.loads(storage.get('targets') or "{}")


def update_hosts(hosts) -> None:
    current_hosts = get_hosts()
    current_targets = get_targets()
    for target in hosts:
        for host in hosts[target]:
            current_hosts[host[0]] = {'ports': [_[0] for _ in host[1]], 'target': target}
    storage.set('hosts', json.dumps(current_hosts))
    current_targets.update(hosts)
    storage.set('targets', json.dumps(current_targets))


def get_last_scan() -> int:
    return int(storage.get('last_scan') or 0)


@celery.task
def scheduled_scan():
    discovery_type = get_core_setting('discovery_type')
    if 'nmap' in discovery_type or 'both' in discovery_type:
        if int(time()) - get_last_scan() > NmapScan.get_setting('scan_interval'):
            print("scanning now")
            NmapScan.run_scans()
        else:
            print("no need to scan")
    if 'iscore' in discovery_type or 'both' in discovery_type:
        update_iscore_targets()


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
    h = [(host.address, host.get_open_ports()) for host in report.hosts if host.is_up()]
    self.update_state(state="RESULTS", meta={'hosts': h,
                                             'target': target['name']})
