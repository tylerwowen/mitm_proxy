import socket
import threading
from urllib.parse import urlsplit, urlunsplit


class MITMProxyServer:

    def __init__(self, port_num=8080):
        self.port = port_num
        try:
            # create an INET, STREAMing socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', self.port))
        except socket.error:
            if self.socket:
                self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', 0))
        self.socket.listen(15)
        print('listening at port ', self.socket.getsockname()[1])

    def run(self):
        while True:
            (client_socket, address) = self.socket.accept()
            ct = Worker(client_socket)
            ct.run()

    def close(self):
        self.socket.close()


class Worker(threading.Thread):

    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.client_socket = sock
        self.body_start = b''
        self.body_len = 0
        self.method = 'GET'
        self.remote_port = 80
        self.chunked = False

    def run(self):
        request_header = self.receive_request_header()
        if not request_header:
            return
        self.parse_request(request_header)
        request_body = self.receive_request_body()
        request = request_header + request_body

        if self.method == 'CONNECT':
            return
        self.body_len = 0
        self.chunked = False

        if self.send_request(request):
            response_header = self.receive_response_header()
            self.parse_response_header(response_header)
            response_body = self.receive_response_body()
            response = response_header + response_body
            self.send_response(response)

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
                print(self.body_len)

        parsedURL = urlsplit(path)

        scheme = parsedURL.scheme
        self.remote_host = parsedURL.netloc
        if parsedURL.port:
            self.remote_port = parsedURL.port

    def receive_request_body(self):
        if self.chunked:
            return receive_body_chunked(self.client_socket, self.body_start)
        return receive_body(self.client_socket, self.body_start, self.body_len)

    def send_request(self, data):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.remote_host, self.remote_port))
            self.server_socket.sendall(data)
        except socket.error:
            if self.server_socket:
                self.server_socket.close()
            self.client_socket.close()
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
                print(self.body_len)
            if 'Transfer-Encoding' in header and 'chunked' in header:
                self.chunked = True

    def receive_response_body(self):
        if self.chunked:
            return receive_body_chunked(self.server_socket, self.body_start)
        return receive_body(self.server_socket, self.body_start, self.body_len)

    def send_response(self, data):
        self.client_socket.sendall(data)
        self.client_socket.close()

    def send_error(self):
        self.client_socket.send()


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
            print('chunk----', chunk)
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
        if server:
            server.close()
