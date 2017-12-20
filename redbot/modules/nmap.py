from time import sleep

from libnmap.process import NmapProcess

from redbot.async import celery


@celery.task(bind=True)
def nmap_scan(self, target: str, options: str = 'sT -n'):
    nm = NmapProcess(target, options=options)
    nm.run_background()
    while nm.is_running():
        self.update_state(state="PROGRESS", meta=nm.progress)
        sleep(2)
