import random

import requests
from bs4 import BeautifulSoup
from celery import group
from faker import Faker
from http_crawler import crawl

from redbot.core.async import celery
from redbot.core.utils import log, random_targets
from redbot.modules import Attack

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
    def run_attack(cls):
        attacks = [do_nikto, crawl_site]
        cls.log("Starting HTTP attack.")
        targets = (random_targets(int(port) for port in cls.get_setting('ports').replace(' ', '').split(',')))
        attacks = random.choices(attacks, random.randint(1, len(attacks)))
        g = group(random.choice(attacks).s(target) for target in targets)()
        g.get(on_message=cls.push_update, propagate=False)
        cls.log("Finished HTTP attack.", "success")


cls = HTTPAttacks


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


@celery.task(bind=True)
def crawl_site(self, target: str, submit_forms=True):
    results = crawl(target, follow_external_links=False)
    self.update_state(state="PROGRESS", meta={'target': target, 'status': 'Completed crawl'})
    if submit_forms:
        for r in results:
            if r.status_code == 200:
                fill_submit_forms.delay(r.text)
    self.update_state(state="DONE", meta={'target': target})


@celery.task(bind=True)
def do_nikto():
    pass
