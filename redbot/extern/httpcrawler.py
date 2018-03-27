#!/usr/bin/env python
"""
https://github.com/inglesp/http-crawler

Copyright (c) 2016 Peter Inglesby

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import cgi
from urllib.parse import urldefrag, urljoin, urlparse

import lxml.html
import requests
import tinycss2

__version__ = '0.2.0'


def crawl(base_url, follow_external_links=True, ignore_fragments=True, verify_ssl=True):
    base_netloc = urlparse(base_url).netloc

    seen = set([base_url])
    todo = [base_url]

    session = requests.Session()
    session.verify = verify_ssl

    while todo:
        url = todo.pop()

        try:
            rsp = session.get(url)
        except requests.exceptions.InvalidSchema:
            # TODO: Check if the scheme is a valid one, or otherwise
            # communicate the error to the user.
            continue

        yield rsp

        if urlparse(url).netloc != base_netloc:
            continue

        content_type, _ = cgi.parse_header(rsp.headers['content-type'])

        if content_type == 'text/html':
            urls = extract_urls_from_html(rsp.text)
        elif content_type == 'text/css':
            urls = extract_urls_from_css(rsp.text)
        else:
            # see https://bitbucket.org/ned/coveragepy/issues/497/
            continue  # pragma: no cover

        for url1 in urls:
            abs_url = urljoin(url, url1)

            if ignore_fragments:
                abs_url = urldefrag(abs_url)[0]

            if not follow_external_links:
                if urlparse(abs_url).netloc != base_netloc:
                    continue

            if abs_url not in seen:
                seen.add(abs_url)
                todo.append(abs_url)


def extract_urls_from_html(html):
    dom = lxml.html.fromstring(html)
    return dom.xpath('//@href|//@src')


def extract_urls_from_css(css):
    urls = []
    rules = tinycss2.parse_stylesheet(css)
    for rule in rules:
        if rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
            for token in rule.prelude:
                if token.type in ['string', 'url']:
                    urls.append(token.value)
        elif hasattr(rule, 'content'):
            for token in rule.content:
                if token.type == 'url':
                    urls.append(token.value)

    return urls
