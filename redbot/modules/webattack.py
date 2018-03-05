import random
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup
from celery import group
from celery.result import GroupResult
from faker import Faker
from http_crawler import crawl

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
        cls.log("Starting HTTP attack.")
        targets = cls.get_random_targets()
        g = cls.attack_all(targets)
        return g, targets


cls = HTTPAttacks


def get_proper_url(target: Tuple[str, int]) -> str:
    hostname = get_hosts()[target[0]].get('hostname', target[0])
    return 'http{}://{}:{}'.format('s' if target[1] == 443 else '', hostname, target[1])


@celery.task
def fill_submit_forms(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
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
        url = resp.url.split('/')[0] + '/' + inp.get('action', '/'.join(resp.url.split('/')[1:]))
        if inp.get('method', '').lower() == 'get':
            requests.get(url, params=params, cookies=resp.cookies, headers={'User-Agent': fake.user_agent()})
        else:
            requests.post(url, data=params, cookies=resp.cookies, headers={'User-Agent': fake.user_agent()})


@celery.task
def crawl_site(target: Tuple[str, int], submit_forms=True):
    results = crawl(get_proper_url(target), follow_external_links=False)
    if submit_forms:
        for r in results:
            if r.status_code == 200:
                fill_submit_forms.delay(r.text)
    cls.log("Finished crawling {}:{}".format(*target))


@celery.task
def run_nikto(target: Tuple[str, int]):
    cls.log("Finished Nikto on {}:{}".format(*target))
    pass
