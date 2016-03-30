
## Run
Please cd to `src` and run `python3 mproxy.py -p port`

## Certificates
The root certificate is `certificates/MITM_CA.crt`. The key used to generate fake certificates is `certificates/cer_gen.key`.

## Two versions


### Complete version

cd to `src` and run `python3 mproxy.py -p port`

This is the latest version I implemented. It uses pyopenssl to get SNI.


### Stable version

cd to `src2` and run `python3 mproxy.py -p port`.

This version works well (actually stabler) except it sets SNI to the hostname getting from `CONNECT` command, instead of getting from client hello.

This version does not have log file path issues. Most differences between the two version are in `HTTPSConnectionHandler.py`, where I adapted pyopenssl (`import OpenSSL`). The problem of this version is that if the actual SNI is different from the host name after `CONNECT`, the client won't be able to connect to the server it requests. According to my test, this case is rare. On the other hand, this version starts SSL handshake when certificates are ready, the chance of timeout is low. That's why I think this is stabler.


## Spoof
All four hacks work. These functionalities are implemented in `src/modifier.py`. It has two functions `request_spoof(request)` for modifying requests and `response_spoof(request, response)` for responses.

### BuzzFeed
If the response is from `www.buzzfeed.com`, modify it.
```python
if 'www.buzzfeed.com' in request.host:
      buzzfeed_spoof(request, response)
```

Depending on the response form, either change the HTML or JSON.

```python
def buzzfeed_spoof(request, response):
    if b'text/html' in response.header:
        buzzfeed_html(response)
    elif b'index.mobile' in request.payload\
            or b'life.mobile' in request.payload\
            or b'lol.mobile' in request.payload:
        buzzfeed_json(response)
```

### Whisper
Whisper loads its images from  `cdn-client.wimages.net`. So hijack all responses from the host, and replace their contents with the one in `resources/whisper.gz`.

```python
if 'cdn-client.wimages.net' in request.host:
      whisper_spoof(response)

def whisper_spoof(response):
    with open(IMAGE_DIR, 'rb') as image:
        data = image.read()
        body = bytes(format(len(data), 'x'), 'ascii') + b'\r\n' + data + b'\r\n0\r\n\r\n'
        response.replace_body(body)
```

### Tumblr
Tumblr queries two servers for search results. One is queried when you type (`/v2/search/`), the other is queried when you hit enter (`/v2/mobile/search`). To do this hack, the request need to be modified.

```python
if 'api.tumblr.com' in request.host:
    if b'/v2/search/' in request.payload:
        tumblr_spoof(request)
    if b'/v2/mobile/search' in request.payload:
        tumblr_spoof_button_pressed(request)

def tumblr_spoof(request):
    req_str = str(request.payload, 'iso-8859-1')
    req_str = re.sub(r'/v2/search/.*\?', '/v2/search/panda?', req_str)
    request.payload = bytes(req_str, 'iso-8859-1')

def tumblr_spoof_button_pressed(request):
    req_str = str(request.payload, 'iso-8859-1')
    req_str = re.sub(r'&query=.*&', '&query=panda&', req_str)
    request.payload = bytes(req_str, 'iso-8859-1')
```

### Periscope
This is also a response modification. By inspecting the packages, I found that the number of watchers are in the responses to endpoint `/api/v2/getBroadcasts`. The responses are in JSON format, so the modification is simply done by replacing string with a regular expression. Note that it takes longer for the app to show the modified numbers of watchers, and occasionally the app crashes. I could't figure out why.

```python
if b'/api/v2/getBroadcasts' in request.payload:
    periscope_spoof(response)

def periscope_spoof(response):
    json_str = response.body.decode("utf-8", "strict")
    modified = re.sub(r'"n_watching":[0-9]*,', '"n_watching":1,', json_str)
    response.replace_body(bytes(modified, 'utf-8'))
```
