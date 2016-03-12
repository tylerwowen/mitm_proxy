import gzip
import json
import re
from html.parser import HTMLParser

IMAGE_DIR = '../resources/whisper.gz'


def spoof(request, response):
    if 'www.buzzfeed.com' in request.host:
        buzzfeed_spoof(request, response)
    if 'cdn-client.wimages.net' in request.host:
        whisper_spoof(response)


def buzzfeed_spoof(request, response):
    if b'text/html' in response.header:
        buzzfeed_html(response)
    elif b'index.mobile' in request.payload\
            or b'life.mobile' in request.payload\
            or b'lol.mobile' in request.payload:
        buzzfeed_json(response)


def buzzfeed_html(response):
    html = gzip.decompress(response.body).decode("utf-8", "strict")
    html_md = re.sub(r'<h1 class="title".?>.*</h1>', '<h1 class="title" >CS176B is Great!</h1>', html)
    response.replace_body(gzip.compress(bytes(html_md, 'utf-8')))


def buzzfeed_json(response):
    json_str = str(gzip.decompress(response.body), 'ascii')
    decoded = json.loads(json_str)
    section = decoded['section']
    for i in range(0, len(section)):
        section[i]['name'] = 'CS176B is Great!'
        section[i]['header']['name'] = 'CS176B is Great!'
    modified = json.dumps(decoded)
    response.replace_body(gzip.compress(bytes(modified, 'ascii')))


def whisper_spoof(response):
    with open(IMAGE_DIR, 'rb') as image:
        data = image.read()
        body = bytes(format(len(data), 'x'), 'ascii') + b'\r\n' + data + b'\r\n0\r\n\r\n'
        response.replace_body(body)


class BuzzFeedHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.title_found = False
        self.title = ''

    def handle_starttag(self, tag, attrs):
        if tag != 'h1':
            return
        for name, value in attrs:
            if name == 'class' and value == 'title':
                self.title_found = True

    def handle_endtag(self, tag):
        self.title_found = False

    def handle_data(self, data):
        if self.title_found:
            self.title = data
            return
