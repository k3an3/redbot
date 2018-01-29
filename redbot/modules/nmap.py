import json
from time import sleep, time
from typing import Dict

from libnmap.parser import NmapParser, NmapParserException
from libnmap.process import NmapProcess

from redbot.async import celery, storage
from redbot.models import targets
from redbot.modules import get_setting
from redbot.utils import log
from redbot.web.web import socketio, send_msg

settings = {
    'scan_options': {
        'name': 'Scan Options',
        'default': '-sT -n -T5',
    },
    'ports': {
        'name': 'Target Ports',
        'default': ",".join((str(n) for n in (21, 22, 23, 80, 443)))
    }
}


def get_hosts() -> Dict:
    return json.loads(storage.get('hosts') or "{}")


def get_last_scan() -> int:
    return int(storage.get('last_scan') or 0)


@celery.task(bind=True)
def nmap_scan(self, target: Dict[str, str],
              options: str = get_setting('scan_options', settings)) -> None:
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


def push_update(data):
    if data.get('status') == 'RESULTS':
        hosts = {data['result']['target']: data['result']['hosts']}
        log("Completed nmap scan against " + data['result']['target'], "nmap", "success")
        storage.set('hosts', json.dumps(hosts))
    socketio.emit('nmap progress', data, broadcast=True)


def run_scans() -> None:
    storage.delete('hosts')
    # The way I wish it worked:
    # r = ResultSet([])
    r = []
    for target in targets:
        r.append(nmap_scan.delay(target))
    # But this blocks indefinitely even after tasks complete for some reason
    # r.get(on_message=push_update, propagate=False)
    for scan in r:
        scan.get(on_message=push_update, propagate=False)
    send_msg('Scan finished.')
    socketio.emit('scan finished', {}, broadcast=True)
    storage.set('last_scan', int(time()))
