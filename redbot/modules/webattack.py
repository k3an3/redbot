from typing import List, Tuple, Dict

import requests
from bs4 import BeautifulSoup
from celery.result import GroupResult
from faker import Faker
from http_crawler import crawl
from requests.utils import dict_from_cookiejar

from redbot.core.async import celery
from redbot.modules import Attack
from redbot.modules.discovery import get_hosts

settings = {
    'ports': {
        'default': [80],
    }
}


class HTTPAttacks(Attack):
    name = "http_attack"
    settings = {
        'ports': {
            'name': 'Target Ports',
            'default': '80',
            'description': "Comma-separated list of ports to target.",
        },
        'submit_forms': {
            'name': 'Auto-Submit Forms',
            'default': True,
            'description': "Whether the web crawler should fill out and submit forms with random data."
        },
        'enable_nikto': {
            'name': 'Enable Nikto',
            'default': False,
            'description': "Whether to enable the Nikto web application scanner. Nikto must be installed."
        }
    }

    @classmethod
    def push_update(cls, data):
        if data.get('status') == 'PROGRESS':
            cls.log(data['result']['status'] + " " + data['result']['target'])
        elif data.get('status') == 'DONE':
            cls.log('Finished HTTP attack on {}"'.format(data['result']['target']), "success")

    @classmethod
    def run_attack(cls) -> (GroupResult, List[str]):
        attacks = [crawl_site]
        if cls.get_setting('enable_nikto'):
            attacks.append(run_nikto)
        targets = cls.get_random_targets()
        cls.log("Starting HTTP attack on " + str(targets))
        g = cls.attack_all(attacks=attacks, targets=targets)
        return g, targets


cls = HTTPAttacks


def get_proper_url(host: str, port: int) -> str:
    hostname = get_hosts()[host].get('hostname', host)
    return 'http{}://{}:{}'.format('s' if port == 443 else '', hostname, port)


@celery.task
def fill_submit_forms(resp_text: str, resp_url: str, resp_cookies: Dict):
    soup = BeautifulSoup(resp_text, 'lxml')
    fake = Faker()
    for form in soup.find_all('form'):
        params = {}
        # Fields that may be requested repeatedly
        email = ""
        passwd = ""
        for inp in form.find_all('input'):
            if inp.get('name'):
                name = inp['name']
                cname = name.lower().replace('_', '').replace('-', '')
                if 'pass' in cname:
                    passwd = passwd or fake.password(int(inp.get('maxlength', 10)))
                    params[name] = passwd
                elif 'mail' in cname:
                    email = email or fake.email()
                    params[name] = email
                elif cname in ['username', 'user', 'login']:
                    params[name] = fake.user_name()
                elif cname in ['givenname', 'firstname', 'fname']:
                    params[name] = fake.first_name()
                elif cname in ['lname', 'lastname', 'surname']:
                    params[name] = fake.last_name()
                elif cname in ['name', 'fullname']:
                    params[name] = fake.name()
                elif cname in ['phone', 'cell']:
                    params[name] = fake.phone_number()
                elif inp.get('value'):
                    params[name] = inp['value']
                else:
                    params[name] = fake.sentence()
        url = resp_url.split('/')[0] + '/' + inp.get('action', '/'.join(resp_url.split('/')[1:]))
        if inp.get('method', '').lower() == 'get':
            requests.get(url, params=params, cookies=resp_cookies, headers={'User-Agent': fake.user_agent()},
                         verify=False)
        else:
            requests.post(url, data=params, cookies=resp_cookies, headers={'User-Agent': fake.user_agent()},
                          verify=False)


@celery.task
def crawl_site(host: str, port: int):
    results = crawl(get_proper_url(host, port), follow_external_links=False)
    if HTTPAttacks.get_setting('submit_forms') in [True, 'True']:
        for r in results:
            if r.status_code == 200:
                fill_submit_forms.delay(r.text, r.url, dict_from_cookiejar(r.cookies))
    cls.log("Finished crawling {}:{}".format(host, port))


@celery.task
def run_nikto(target: Tuple[str, int]):
    cls.log("Finished Nikto on {}:{}".format(*target))
    pass
