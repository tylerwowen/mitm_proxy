from http.server import BaseHTTPRequestHandler, HTTPServer

import urllib.request
import sys
import http.client
import shutil
from urllib.parse import urlparse


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler, port=8080):
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
    establishedConns = []

    def do_GET(self):
        """Serve a GET request."""
        req = self
        parsedURL = urlparse(req.path)
        host = parsedURL.netloc
        path = parsedURL.path
        print(host, path)
        # contentLength = req.getheader('Content-Length')
        # req_body = req.rfile.read(contentLength) if contentLength else None
        conn = http.client.HTTPConnection(host)
        conn.request('GET', path, headers=req.headers)
        res = conn.getresponse()
        print(res.read())
        # resContentLength = res.getheader('Content-Length')
        req.send_response(res.status)
        for header in res.getheaders():
            req.send_header(header[0], header[1])
        req.end_headers()
        req.wfile.write(res.read())
        conn.close()

        # print(self.path)
        # print(self.headers)
        # request = urllib.request.Request(url=req.path, headers=req.headers)
        # request.method = 'GET'
        # print(request.header_items())
        # with urllib.request.urlopen(request) as f:
        #     req.send_response(f.getcode())
        #     for header in f.info()._headers:
        #         req.send_header(header[0], header[1])
        #     req.end_headers()
        #     req.wfile.write(f.read())
        #     f.close()

