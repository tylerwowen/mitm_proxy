import http.client
import sys
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

    def do_GET(self):
        """Serve a GET request."""
        req = self
        parsedURL = urlsplit(req.path)

        scheme = parsedURL.scheme
        host = parsedURL.netloc
        url = urlunsplit(('', '', parsedURL.path, parsedURL.query, ''))
        print(host, url)

        contentLength = req.headers['Content-Length']
        reqBody = req.rfile.read(contentLength) if contentLength else None

        target = (scheme, host)
        if target not in self.establishedConns:
            conn = self.buildConn(target)
        else:
            conn = self.establishedConns[target]

        try:
            conn.request(self.command, url, reqBody, req.headers)
        except http.client.CannotSendRequest:
            conn = self.rebuildConn(target)
            conn.request(self.command, url, reqBody, req.headers)

        res = conn.getresponse()
        self.respondToRequest(res, self.readFrom(res))

    def respondToRequest(self, res, resBody):
        req = self
        req.send_response_only(res.status)
        for header in res.getheaders():
            req.send_header(header[0], header[1])
        req.end_headers()
        if self.command is not 'HEAD':
            req.wfile.write(resBody)
            req.wfile.flush()

    def readFrom(self, res):
        if res.fp is None:
            return b""

        if res.length is None:
            s = res.fp.read()
        else:
            try:
                s = res._safe_read(res.length)
            except http.IncompleteRead:
                res._close_conn()
                raise
            res.length = 0
        res._close_conn()        # we read everything
        return s

    do_HAED = do_GET

    def do_POST(self):
        req = self
        contentLength = req.getheader('Content-Length')
        req_body = req.rfile.read(contentLength) if contentLength else None

    def buildConn(self, target):
        global connTimeout
        conn = http.client.HTTPConnection(target[1], timeout=connTimeout)
        self.establishedConns[target] = conn
        return conn

    def rebuildConn(self, target):
        global connTimeout
        conn = http.client.HTTPConnection(target[1], timeout=connTimeout)
        self.establishedConns[target] = conn
        return conn
