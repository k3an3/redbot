import requests
from bs4 import BeautifulSoup
from faker import Faker
from http_crawler import crawl

from redbot.async import celery

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


@celery.task
def crawl_site(target: str, submit_forms=True):
    results = crawl(target, follow_external_links=False)
    if submit_forms:
        for r in results:
            if r.status_code == 200:
                fill_submit_forms.delay(r.text)


if __name__ == '__main__':
    r = requests.get('http://localhost:8000/signup/')
    fill_submit_forms(r)
