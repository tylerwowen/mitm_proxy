import concurrent.futures
import os
import shutil
import socket
from urllib.parse import urlsplit

import HTTPSConnectionHandler as HTTPS


class MITMProxyServer:

    def __init__(self, port_num=8080):
        self.port = port_num

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind(('', self.port))
        except OSError:
            self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', 0))
        self.socket.listen(20)
        print('listening at port ', self.socket.getsockname()[1])

    def run(self, num_workers=10, timeout=9999, log=None):
        if log is not None:
            if os.path.exists(log):
                shutil.rmtree(log)
            os.mkdir(log)

        index = 0
        self.executor = concurrent.futures.ThreadPoolExecutor(num_workers)
        while True:
            (client_socket, address) = self.socket.accept()
            ct = Worker(client_socket, timeout, index, log)
            self.executor.submit(ct.run)
            index += 1

    def close(self):
        if self.executor is not None:
            self.executor.shutdown(False)
        self.socket.close()


class Worker:

    def __init__(self, sock, timeout, index, log):
        self.client_socket = sock
        self.timeout = timeout
        self.index = index
        self.log = log
        self.server_socket = None

    def run(self):
        request = response = None
        try:
            request = handle_request(self.client_socket)

            response = self.get_response(request)

            self.send_response(response.payload)
        except ClientDisconnected:
            pass
        except TimeoutError:
            self.send_error(504, 'Gateway Timeout')
        finally:
            self.log_traffic(request, response)
            self.cleanup()

    def https_proxy(self):
        handler = HTTPS.HTTPSConnectionHandler()
        self.server_socket, cert = handler.connect_to_remote_server(self.remote_host, self.remote_port)
        context = handler.get_context(cert)
        self.client_socket = context.wrap_socket(self.client_socket, server_side=True)
        # try:
        #
        # finally:
        #     self.client_socket.shutdown(socket.SHUT_RDWR)
        #     self.client_socket.close()

    def get_response(self, request):
        try:
            self.create_server_conn(request)
        except socket.error:
            self.send_error(502, 'Bad Gateway')
            raise HostNotReachable
        self.send_request(request.payload)
        return receive_response(self.server_socket)

    def create_server_conn(self, request):
        if request.scheme == 'http':
            self.server_socket = socket.create_connection((request.host, request.port), self.timeout)
        else:
            self.server_socket = request.server_sock

    def send_request(self, data):
        self.server_socket.sendall(data)

    def send_response(self, data):
        self.client_socket.sendall(data)

    def send_error(self, code, msg):
        self.client_socket.sendall(('HTTP/1.1 %d %s\r\n\r\n' % (code, msg)).encode('latin-1', 'strict'))

    def cleanup(self):
        if self.client_socket is not None:
            self.client_socket.close()
        if self.server_socket is not None:
            self.server_socket.close()

    def log_traffic(self, request, response):
        if self.log is not None:
            filename = str(self.index) + '_' + self.client_socket.getpeername()[0] + '_' + request.host
            f = open(os.path.join(self.log, filename), 'wb')
            request = request.payload if request is not None else b''
            response = response.payload if response is not None else b''
            f.write(request + b'\n' + response)
            f.close()


def handle_request(sock):
    # HTTP or HTTPS
    requestline = readline(sock)
    method, path = parse_request_line(requestline)

    if method is 'CONNECT':
        return None
    else:
        return receive_request(sock, requestline)


def readline(sock):
    chars = []
    while True:
        char = sock.recv(1)
        if not char:
            raise ClientDisconnected
        chars.append(char)
        if char == b'\n':
            break
        if char == b'\r':
            n_char = sock.recv(1)
            chars.append(n_char)
            if n_char == b'\n':
                break
    return b''.join(chars)


def parse_request_line(requestline):
    words = str(requestline, 'iso-8859-1').split()
    if len(words) == 3:
        method, path, version = words
    elif len(words) == 2:
        method, path = words
    else:
        raise InvalidRequest('Cannot parse request line')
    return method.upper(), path


def receive_request(sock, requestline):
    header, body_start = receive_header(sock)
    request = parse_request_header(requestline, header)
    receive_body(sock, body_start, request)
    return request


def receive_response(sock):
    header, body_start = receive_header(sock)
    response = parse_response_header(header)
    receive_body(sock, body_start, response)
    return response


def receive_header(sock):
    end = b'\r\n\r\n'
    chunks = []
    body_start = b''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ClientDisconnected
        if end in chunk:
            chunks.append(chunk[:chunk.find(end) + 4])
            body_start = chunk[chunk.find(end) + 4:]
            break
        chunks.append(chunk)
        if len(chunks) > 1:
            # check if end_of_data was split
            last_pair = chunks[-2] + chunks[-1]
            if end in last_pair:
                chunks[-2] = last_pair[:last_pair.find(end) + 4]
                body_start = last_pair[last_pair.find(end) + 4:]
                chunks.pop()
                break
    print('headers', chunks)
    return b''.join(chunks), body_start


def parse_request_header(requestline, header):
    body_len = parse_body_length(header)
    method, path = parse_request_line(requestline)

    parsed_URL = urlsplit(path)
    host = parsed_URL.netloc
    port = parsed_URL.port
    scheme = parsed_URL.scheme.lower()
    complete_header = requestline + header
    return Request(complete_header, host, port, body_len, scheme)


def parse_response_header(header):
    body_len = parse_body_length(header)
    return Response(header, body_len)


def parse_body_length(header):
    header_tuple = str(header, 'iso-8859-1').split('\r\n')
    for header in header_tuple:
        if 'Content-Length' in header:
            return int(header.split(':')[1])
        if 'Transfer-Encoding' in header and 'chunked' in header:
            return -1
    return 0


def parse_connect_path(path):
    host = path[:path.find(':')]
    port = int(path[path.find(':')+1:])
    return host, port


def receive_body(sock, body_start, reqres):
    if reqres.chunked:
        complete_body = receive_body_chunked(sock, body_start)
    else:
        complete_body = receive_body_length(sock, body_start, reqres.body_length)
    reqres.add_body(complete_body)


def receive_body_length(sock, body_start, body_length):
    chunks = [body_start]
    received = len(body_start)
    while received < body_length:
        chunk = sock.recv(4096)
        if not chunk:
            raise ClientDisconnected
        chunks.append(chunk)
        received += len(chunk)
    return b''.join(chunks)


def receive_body_chunked(sock, body_start):
    end = b'0\r\n\r\n'
    if end in body_start:
        return body_start
    chunks = [body_start]
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ClientDisconnected
        chunks.append(chunk)
        if end in chunk:
            break
        if len(chunks) > 1:
            # check if end_of_data was split
            last_pair = chunks[-2] + chunks[-1]
            if end in last_pair:
                chunks[-2] = last_pair[:last_pair.find(end) + 5]
                chunks.pop()
                break
    return b''.join(chunks)


class Request:

    def __init__(self, header, host, port, body_length, scheme):
        self.host = host
        self.port = port if port is not None else 80
        self.body_length = body_length
        self.chunked = True if body_length == -1 else False
        self.payload = header
        self.scheme = scheme
        self.server_sock = None

    def add_body(self, body):
        self.payload += body


class Response:

    def __init__(self, header, body_length):
        self.body_length = body_length
        self.chunked = True if body_length == -1 else False
        self.payload = header

    def add_body(self, body):
        self.payload += body


class Error(Exception):
    """  Base error class """
    pass


class InvalidRequest(Error):

    def __init__(self, message):
        self.message = message


class ClientDisconnected(Error):
    pass


class HostNotReachable(Error):
    pass

if __name__ == "__main__":
    try:
        server = MITMProxyServer()
        server.run()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        if server is not None:
            server.close()
