"""
Data structure definitions:

Hosts:
    Format for storing hosts, hostname or IP address as key.

    { \
        'hostname1': { \
                        'ports': { \
                            portnum: { \
                                'banner': '', \
                            } \
                        } \
                        'target': target, \
                        'notes': '', \
                    }, \
        'hostname2': { \
                        ... \
                    }, \
        ... \
    }


"""
import json
import socket
from json import JSONDecodeError
from time import sleep, time
from typing import Dict

import requests
from celery import group
from libnmap.parser import NmapParser, NmapParserException
from libnmap.process import NmapProcess
from requests.exceptions import MissingSchema, HTTPError

from redbot.core.async import celery
from redbot.core.models import targets, storage
from redbot.core.utils import log
from redbot.modules import Attack
from redbot.settings import TEAM_DOMAIN_SUFFIX
from redbot.web.web import socketio, send_msg


class Discovery(Attack):
    name = "discovery"
    exempt = True
    test = False

    settings = {
        'scan_options': {
            'name': 'Scan Options',
            'default': '-n -T5 -sV',
            'description': 'Accepts any nmap command-line flags.'
        },
        'ports': {
            'name': 'Target Ports',
            'default': "",
            'description': 'Comma-separated ports or port ranges to scan. Default is 1000 most common.'
        },
        'scan_interval': {
            'name': 'Scan Interval',
            'default': 60 * 10,
            'description': 'How often (in seconds) to perform nmap scans.'
        },
        'iscore_url': {
            'name': 'IScorE URL',
            'default': '',
            'description': 'URL to the IScorE system to be used for API queries.'
        },
        'iscore_api': {
            'name': 'IScorE API Token (optional)',
            'default': '',
            'description': 'An API token obtained from IScorE. May increase functionality and performance',
        },
        'update_frequency': {
            'name': 'IScorE Check Frequency',
            'default': 5 * 60,
            'description': 'How often (in seconds) to poll the IScorE servicecheck API.'
        },
        'discovery_type': {
            'name': 'Host Discovery Method',
            'default': 'nmap',
            'description': 'Method for discovering targets. Can be "nmap", "iscore", or "both". IScorE requires a '
                           'valid configuration. '
        },
    }

    @classmethod
    def push_update(cls, data):
        if data.get('status') == 'RESULTS':
            log("Completed nmap scan against " + data['result']['target'], "nmap", "success")
        socketio.emit('nmap progress', data, broadcast=True)

    @classmethod
    def run_scans(cls, ondemand: bool = False) -> None:
        clear_targets()
        g = group(nmap_scan.s(target) for target in targets).apply_async(queue='discovery')
        if ondemand:
            g.get(on_message=cls.push_update, propagate=False)
            send_msg('Scan finished.')
            socketio.emit('scan finished', {}, broadcast=True)


cls = Discovery


def get_url() -> str:
    """
    Format the provided IScorE URL for the API.
    :return: Full URL to IScorE's API.
    """
    return Discovery.get_setting('iscore_url') + '/api/v1/'


def clear_targets() -> None:
    """
    Erase the hosts currently in Redis and clear scan times.
    """
    storage.delete('hosts')
    storage.set('last_nmap_scan', 0)
    storage.set('last_iscore_update', 0)
    storage.set('scan_in_progress', 0)


@celery.task
def dns_lookup(hostname: str) -> Dict[str, str]:
    """
    Slow, fallback method for resolving a hostname to IP address using real DNS queries.
    :param hostname: The hostname to look up.
    :return: The resolved IP address as a dictionary.
    """
    try:
        return {hostname: socket.gethostbyname(hostname)}  # IScorE URLs are not URLs. This call is also IPv4 only.
    except socket.gaierror:
        return {hostname: hostname}


def update_iscore_targets() -> None:
    """
    Performs service discovery via IScorE's API. A list of all service scans are fetched, and the hostnames provided
    for these services are resolved to IP address so they can be stored in the hosts database. Services that are
    marked up are added to the hosts database, or the database information is updated if the entry already exists.
    Requires a privileged IScorE API key in order to quickly resolve hosts, else it may be very slow/network
    intensive while many DNS queries are performed.
    """
    storage.set('last_iscore_update', int(time()))
    # Fetch service statuses from API
    try:
        r = requests.get(get_url() + 'servicestatus', headers={'Content-Type': 'application/json'})
        r.raise_for_status()
        r = r.json()
    except MissingSchema:
        send_msg('IScorE update failed. Check that a valid IScorE URL was provided.', 'danger')
        return
    except HTTPError as e:
        send_msg('Error when contacting IScorE: ' + str(e), 'danger')
        return
    except JSONDecodeError:
        send_msg("IScorE didn't return valid JSON.", 'danger')
        return
    hosts = {}
    records = {}
    # Resolve service hostnames to IP addresses, as they will be stored
    if Discovery.get_setting('iscore_api'):
        try:
            r2 = requests.get(get_url() + 'dns', headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token ' + Discovery.get_setting('iscore_api').strip()
            })
            r2.raise_for_status()
            r2 = r2.json()
        except HTTPError as e:
            send_msg('Error with IScorE API: ' + str(e), 'danger')
            return
        except JSONDecodeError:
            send_msg("IScorE API didn't return valid JSON.", 'danger')
            return
        for rec in r2:
            records['{}.team{}.{}'.format(rec['name'], rec['team_number'], TEAM_DOMAIN_SUFFIX)] = rec['value']
    else:
        # Low performance fallback method to obtain IP addresses using DNS
        lookups = group(dns_lookup.s(host['service_url'] for host in r))
        [records.update(l) for l in lookups.get()]
    for host in r:
        hostn = records.get(host['service_url'], host['service_url'])
        if not host['service_status'] == 'down':
            ports = hosts.get(hostn, {}).get('ports', {})
            hosts[hostn] = {'ports': ports,
                            'target': "Team " + str(host['team_number']),
                            'notes': [],
                            }
            if not hosts[hostn].get('hostname'):
                hosts[hostn]['hostname'] = host['service_url']
            hosts[hostn]['ports'][str(host['service_port'])] = {'port': host['service_port'],
                                                                'banner': "IScorE Service: " + host['service_name']}
    update_hosts(hosts)
    send_msg('IScorE update finished.')
    socketio.emit('scan finished', {}, broadcast=True)


def get_hosts() -> Dict:
    """
    Shortcut to retrieve hosts from storage.
    :return: Dictionary of discovery hosts.
    """
    return json.loads(storage.get('hosts') or "{}")


def update_hosts(hosts) -> None:
    """
    Parse and add/merge discovered hosts into the hosts database.
    :param hosts: Dictionary of new/updated hosts to insert.
    """
    current_hosts = get_hosts()
    for host in hosts:
        if host in current_hosts:
            current_host = current_hosts[host]
            host = hosts[host]
            for p in host['ports']:
                p = str(p)
                if p in current_host['ports']:
                    if not host['ports'][p]['banner'] in current_host['ports'][p]['banner']:
                        current_host['ports'][p]['banner'] += ", " + host['ports'][p]['banner']
            if not current_host.get('notes'):
                current_host['notes'] = []
            current_host['notes'].append(host.get('notes'))
            current_host['hostname'] = host.get('hostname')
        else:
            current_hosts[host] = hosts[host]
    storage.set('hosts', json.dumps(current_hosts))


def get_last_scan() -> int:
    """
    Shortcut to return the last scan time.
    :return: UNIX timestamp of last scan.
    """
    return int(storage.get('last_nmap_scan') or 0)


def get_last_update() -> int:
    """
    Shortcut to return the last IScorE update time.
    :return: UNIX timestamp of last update.
    """
    return int(storage.get('last_iscore_update') or 0)


def scan_in_progress() -> int:
    """
    Return how many scans are in progress.
    :return: Integer count of currrent running scans.
    """
    return int(storage.get('scan_in_progress') or 0)


@celery.task(soft_time_limit=1200)
def do_discovery(force: bool = False) -> None:
    """
    Periodic task to determine whether scanning is necessary, and which scans to launch.
    :param force: Whether the scan should be run now regardless of whether it is scheduled or not.
    """
    discovery_type = Discovery.get_setting('discovery_type')
    if 'nmap' in discovery_type or 'both' in discovery_type:
        if force or int(time()) - get_last_scan() > int(Discovery.get_setting('scan_interval')) \
                and not scan_in_progress():
            print("scanning now")
            if not force:
                Discovery.log("Scheduled discovery scan started.")
            Discovery.run_scans(ondemand=force)
        elif scan_in_progress():
            print("already scanning")
        else:
            print("no need to scan")
    if 'iscore' in discovery_type or 'both' in discovery_type:
        if force or int(time()) - get_last_update() > Discovery.get_setting('update_frequency'):
            if not force:
                Discovery.log("Scheduled IScorE update started.")
            update_iscore_targets()


@celery.task(bind=True, soft_time_limit=600)
def nmap_scan(self, target: Dict[str, str]) -> None:
    """
    Nmap scan task. Handles one Nmap process to scan the provided host(s) or range(s).
    Updates the host database when finished; may push status updates if invoked from web context.
    :param target: Target hosts or ranges in a format suitable for Nmap.
    """
    storage.incr('scan_in_progress')
    options = Discovery.get_setting('scan_options')
    ports = Discovery.get_setting('ports')
    if ports:
        options += ' -p' + ports
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
    h = [(host.address, {str(p[0]): host.get_service(*p).get_dict() for p in host.get_open_ports()})
         for host in report.hosts if host.is_up()]
    hosts = {host[0]: {'ports': host[1], 'target': target['name']} for host in h}
    update_hosts(hosts)
    storage.set('last_nmap_scan', int(time()))
    if scan_in_progress() > 0:
        storage.decr('scan_in_progress')
    self.update_state(state="RESULTS", meta={'hosts': h,
                                             'target': target['name']})
