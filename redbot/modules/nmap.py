from time import sleep
from typing import Dict

from libnmap.process import NmapProcess

from redbot.async import celery
from redbot.models import targets
from redbot.web.web import socketio, send_msg


@celery.task(bind=True)
def nmap_scan(self, target: Dict[str, str], options: str = 'sT -n') -> None:
    nm = NmapProcess(target['range'], options=options)
    nm.run_background()
    while nm.is_running():
        self.update_state(state="PROGRESS", meta={'progress': nm.progress,
                          'target': target['name']})
        sleep(2)


def push_update(body):
    socketio.emit('nmap progress', body, broadcast=True)


def run_scans() -> None:
    r = []
    for target in targets:
        r.append(nmap_scan.delay(target))
    for status in r:
        status.get(on_message=push_update, propagate=False)
    send_msg('Scan finished.')
