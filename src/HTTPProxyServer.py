import concurrent.futures
import os
import socket
from urllib.parse import urlsplit, urlunsplit

import shutil


class MITMProxyServer:

    def __init__(self, port_num=8080, num_workers=10, timeout=9999, log=None):
        self.port = port_num
        self.num_workers = num_workers
        self.timeout = timeout
        self.log = log
        try:
            # create an INET, STREAMing socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', self.port))
        except socket.error as e:
            print(e)
            if self.socket:
                self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', 0))
        self.socket.listen(20)
        print('listening at port ', self.socket.getsockname()[1])
        print(num_workers, 'workers')

    def run(self):
        index = 0
        if self.log:
            if os.path.exists(self.log):
                shutil.rmtree(self.log)
            os.mkdir(self.log)
        self.executor = concurrent.futures.ThreadPoolExecutor(self.num_workers)
        while True:
            (client_socket, address) = self.socket.accept()
            ct = Worker(client_socket, self.timeout, index, self.log)
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
        self.body_start = b''
        self.body_len = 0
        self.method = 'GET'
        self.remote_port = 80
        self.chunked = False

    def run(self):
        request_header = self.receive_request_header()
        if not request_header:
            self.cleanup()
            return
        self.parse_request(request_header)
        request_body = self.receive_request_body()
        request = request_header + request_body

        if self.method == 'CONNECT':
            self.cleanup()
            return
        self.body_len = 0
        self.chunked = False

        response = None
        if self.send_request(request):
            try:
                response_header = self.receive_response_header()
                self.parse_response_header(response_header)
                response_body = self.receive_response_body()
                print('received body for ', self.remote_host)
                response = response_header + response_body
                self.send_response(response)
            except TimeoutError:
                self.send_error(504, 'Gateway Timeout')
        self.log_traffic(request, response)
        self.cleanup()

    def receive_request_header(self):
        headers, self.body_start = receive_header(self.client_socket)
        return headers

    def parse_request(self, request_header):
        raw_headers = str(request_header, 'iso-8859-1').split('\r\n')
        requestline = raw_headers[0]
        words = requestline.split()
        if len(words) == 3:
            self.method, path, version = words
        elif len(words) == 2:
            self.method, path = words
        else:
            return False

        for header in raw_headers:
            if 'Content-Length' in header:
                self.body_len = int(header.split(':')[1])

        parsedURL = urlsplit(path)
        self.remote_host = parsedURL.netloc

        if parsedURL.port:
            self.remote_port = parsedURL.port

    def receive_request_body(self):
        if self.chunked:
            return receive_body_chunked(self.client_socket, self.body_start)
        return receive_body(self.client_socket, self.body_start, self.body_len)

    def send_request(self, data):
        try:
            self.server_socket = socket.create_connection((self.remote_host, self.remote_port), self.timeout)
        except socket.error:
            self.send_error(502, 'Bad Gateway')
            return False
        try:
            self.server_socket.sendall(data)
        except socket.error:
            return False
        return True

    def receive_response_header(self):
        headers, self.body_start = receive_header(self.server_socket)
        return headers

    def parse_response_header(self, response_header):
        raw_headers = str(response_header, 'iso-8859-1').split('\r\n')
        for header in raw_headers:
            if 'Content-Length' in header:
                self.body_len = int(header.split(':')[1])
            if 'Transfer-Encoding' in header and 'chunked' in header:
                self.chunked = True

    def receive_response_body(self):
        if self.chunked:
            return receive_body_chunked(self.server_socket, self.body_start)
        return receive_body(self.server_socket, self.body_start, self.body_len)

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
            filename = str(self.index) + '_' + self.client_socket.getpeername()[0] + '_' + self.remote_host
            f = open(os.path.join(self.log, filename), 'wb')
            request = request if request is not None else b''
            response = response if response is not None else b''
            f.write(request + b'\n' + response)
            f.close()



def receive_header(sock):
    end = b'\r\n\r\n'
    chunks = []
    body_start = b''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            print('break')
            sock.close()
            break
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


def receive_body(sock, body_start, body_len):
    chunks = [body_start]
    received = len(body_start)
    while received < body_len:
        chunk = sock.recv(4096)
        if not chunk:
            print('break')
            sock.close()
            break
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
            print('break')
            sock.close()
            break
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


if __name__ == "__main__":
    try:
        server = MITMProxyServer()
        server.run()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        if server is not None:
            server.close()
