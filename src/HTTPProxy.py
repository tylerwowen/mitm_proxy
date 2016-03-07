import http.client
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlunsplit, urlsplit

connTimeout = 9999


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass


def run(server_class=ThreadedHTTPServer, handler_class=BaseHTTPRequestHandler, port=8080, timeout=9999):
    global connTimeout
    connTimeout = timeout
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        httpd.server_close()
        sys.exit(0)


class MITMHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    establishedConns = {}
    establishedConnsLock = threading.Lock()

    def do_GET(self):
        """Serve a GET request."""
        req = self
        parsedURL = urlsplit(req.path)

        scheme = parsedURL.scheme
        host = parsedURL.netloc
        url = urlunsplit(('', '', parsedURL.path, parsedURL.query, ''))

        contentLength = req.headers['Content-Length']
        reqBody = req.rfile.read(int(contentLength)) if contentLength else None

        target = (scheme, host)
        self.establishedConnsLock.acquire()
        if target not in self.establishedConns:
            conn, connLock = self.buildConn(target)
        else:
            conn, connLock = self.establishedConns[target]
        self.establishedConnsLock.release()

        try:
            tries = 1
            connLock.acquire()
            print(host, url)
            while tries <= 5:
                try:
                    conn.request(self.command, url, reqBody, req.headers)
                except http.client.ImproperConnectionState:
                    conn.connect()
                    tries += 1
                    continue
                try:
                    res = conn.getresponse()
                    self.respondToRequest(res)
                except http.client.HTTPException:
                    if tries == 5:
                        req.send_error(404)
                    print('tries'+str(tries))
                    tries += 1
                    continue
                break
        finally:
            connLock.release()

    def respondToRequest(self, res):
        req = self
        req.send_response_only(res.status)
        for header in res.getheaders():
            req.send_header(header[0], header[1])
        req.end_headers()
        if self.command is not 'HEAD':
            req.wfile.write(res.read())
            req.wfile.flush()

    do_HAED = do_GET
    do_POST = do_GET

    def buildConn(self, target):
        global connTimeout
        conn = http.client.HTTPConnection(target[1], timeout=connTimeout)
        connLock = threading.Lock()
        self.establishedConns[target] = (conn, connLock)
        return conn, connLock

