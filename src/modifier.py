import gzip
import json
import re
from html.parser import HTMLParser

IMAGE_DIR = '../resources/whisper.gz'


def request_spoof(request):
    if 'api.tumblr.com' in request.host:
        if b'/v2/search/' in request.payload:
            tumblr_spoof(request)
        if b'/v2/mobile/search' in request.payload:
            tumblr_spoof_button_pressed(request)


def response_spoof(request, response):
    if 'www.buzzfeed.com' in request.host:
        buzzfeed_spoof(request, response)
    if 'cdn-client.wimages.net' in request.host:
        whisper_spoof(response)
    if b'/api/v2/getBroadcasts' in request.payload:
        periscope_spoof(response)


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


def tumblr_spoof(request):
    req_str = str(request.payload, 'iso-8859-1')
    req_str = re.sub(r'/v2/search/.*\?', '/v2/search/panda?', req_str)
    request.payload = bytes(req_str, 'iso-8859-1')


def tumblr_spoof_button_pressed(request):
    req_str = str(request.payload, 'iso-8859-1')
    req_str = re.sub(r'&query=.*&', '&query=panda&', req_str)
    request.payload = bytes(req_str, 'iso-8859-1')


def periscope_spoof(response):
    json_str = response.body.decode("utf-8", "strict")
    modified = re.sub(r'"n_watching":[0-9]*,', '"n_watching":1,', json_str)
    response.replace_body(bytes(modified, 'utf-8'))

