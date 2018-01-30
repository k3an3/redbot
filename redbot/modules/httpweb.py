import requests
from bs4 import BeautifulSoup
from faker import Faker
from http_crawler import crawl

from redbot.async import celery
from redbot.utils import log, random_targets

settings = {
    'ports': {
        'default': [80],
    }
}


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


def push_update(data):
    if data.get('status') == 'PROGRESS':
        log(data['result']['status'] + " " + data['result']['target'], "http")
    elif data.get('status') == 'DONE':
        log('Finished HTTP attack on {}"'.format(data['result']['target']), "http", "success")


def run_attack():
    log("Starting HTTP attack.", "http")
    r = []
    for target in random_targets():
        r.append(crawl_site.delay(target))
    for status in r:
        status.get(on_message=push_update, propagate=False)
    log("Finished HTTP attack.", "http", "success")
