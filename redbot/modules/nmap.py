import json
from time import sleep, time
from typing import Dict

from libnmap.parser import NmapParser, NmapParserException
from libnmap.process import NmapProcess

from redbot.core.async import celery, storage
from redbot.core.models import targets
from redbot.modules import Attack
from redbot.core.utils import log
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
        # The way I wish it worked:
        # r = ResultSet([])
        r = []
        for target in targets:
            r.append(nmap_scan.delay(target))
        # But this blocks indefinitely even after tasks complete for some reason
        # r.get(on_message=push_update, propagate=False)
        for scan in r:
            scan.get(on_message=cls.push_update, propagate=False)
        send_msg('Scan finished.')
        socketio.emit('scan finished', {}, broadcast=True)
        storage.set('last_scan', int(time()))

cls = NmapScan


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
    if int(time()) - get_last_scan() > NmapScan.get_setting('scan_interval'):
        NmapScan.run_scans()


@celery.task(bind=True)
def nmap_scan(self, target: Dict[str, str],
              options: str = NmapScan.get_setting('scan_options')) -> None:
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
