from time import sleep
from typing import Dict

import datetime
from libnmap.parser import NmapParser, NmapParserException
from libnmap.process import NmapProcess

from redbot.async import celery
from redbot.models import targets
from redbot.web.web import socketio, send_msg

last_scan = None


@celery.task(bind=True)
def nmap_scan(self, target: Dict[str, str], options: str = 'sT -n -T5') -> None:
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
    hosts = [(host.address, host.get_open_ports()) for host in report.hosts if host.is_up()]
    self.update_state(state="RESULTS", meta={'hosts': hosts,
                                             'target': target['name']})


def push_update(body):
    socketio.emit('nmap progress', body, broadcast=True)


def run_scans() -> None:
    r = []
    for target in targets:
        r.append(nmap_scan.delay(target))
    for status in r:
        status.get(on_message=push_update, propagate=False)
    send_msg('Scan finished.')
    global last_scan
    last_scan = datetime.datetime.now()
