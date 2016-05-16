import os
import socket
import ssl
import subprocess

from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM, load_privatekey, load_certificate
from OpenSSL.SSL import Context, SSLv23_METHOD, Connection

CA_ROOT = '../certificates/'
CERT_ROOT = '../temp_certs/'
CA_KEY = 'MITM_CA.key'
CA_KEY_DIR = CA_ROOT + CA_KEY
CA_CERT = 'MITM_CA.crt'
CA_CERT_DIR = CA_ROOT + CA_CERT
GEN_KEY = 'cert_gen.key'
GEN_KEY_DIR = CA_ROOT + GEN_KEY
SRL_DIR = CERT_ROOT + 'MITM_CA.srl'

SAN_TEMP = '''[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
prompt = no

[ v3_req ]
basicConstraints=CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment

[req_distinguished_name]
C = US
ST = CA
L = Goleta
O = Tyler
OU = MyDivision
'''

SAN_TEMP_ALT = '''[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
prompt = no

[ v3_req ]
basicConstraints=CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[req_distinguished_name]
C = US
ST = CA
L = Goleta
O = Tyler
OU = MyDivision
'''


def build_ssl_conns(client_socket, path):
    host, port = parse_connect_path(path)
    mitm = ManInTheMiddle(client_socket, host, port)
    mitm.start_hacking()

    return mitm.server_ssl_sock, mitm.client_ssl_sock


class ManInTheMiddle:

    def __init__(self, client_socket, host, port):
        self.client_socket = client_socket
        self.host = host
        self.port = port
        self.sni = None
        self.client_ssl_sock = None
        self.server_ssl_sock = None

    def start_hacking(self):
        self.client_socket.sendall(('HTTP/1.1 {0:d} {1!s}\r\n\r\n'.format(200, 'OK')).encode('latin-1', 'strict'))
        self.accept_client_conn()

    def accept_client_conn(self):
        context = Context(SSLv23_METHOD)
        context.set_tlsext_servername_callback(self.prepare_handshake)

        self.client_ssl_sock = Connection(context, self.client_socket)
        self.client_ssl_sock.set_accept_state()
        self.client_ssl_sock.do_handshake()

    def prepare_handshake(self, connection):
        raw_sni = connection.get_servername()
        if raw_sni is not None:
            self.sni = str(raw_sni, 'ascii')

        self.build_server_conn()
        cert_dict = self.server_ssl_sock.getpeercert()
        crt_dir = generate_fake_cert(cert_dict)
        try:
            key, cert = load(crt_dir)
        except crypto.Error:
            raise CertificateRaceCondition
        new_context = Context(SSLv23_METHOD)
        new_context.use_privatekey(key)
        new_context.use_certificate(cert)
        connection.set_context(new_context)

    def build_server_conn(self):
        server_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        server_context.verify_mode = ssl.CERT_OPTIONAL
        # context.load_verify_locations('/etc/ssl/certs/ca-bundle.crt')
        server_context.set_default_verify_paths()
        ssl_sock = server_context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=self.sni)
        try:
            ssl_sock.connect((self.host, self.port))
        except socket.gaierror:
            print(self.host, self.port)
            raise ServerConnectionError
        self.server_ssl_sock = ssl_sock


def load(crt_dir):
    crt = open(crt_dir)
    key = open(GEN_KEY_DIR)
    result = (
        load_privatekey(FILETYPE_PEM, key.read()),
        load_certificate(FILETYPE_PEM, crt.read()))
    crt.close()
    key.close()
    return result


def parse_connect_path(path):
    host = path[:path.find(':')]
    port = path[path.find(':')+1:]
    if len(port) < 1:
        port = 443
    else:
        port = int(port)
    return host, port


def generate_fake_cert(cert_dict):
    crt_dir = CERT_ROOT + cert_dict['serialNumber'] + '.crt'
    if os.path.isfile(crt_dir):
        return crt_dir
    csr_dir, config_dir = generate_csr(cert_dict)
    subprocess.call('openssl x509 -req -days 365 -extensions v3_req' +
                    ' -CAserial ' + SRL_DIR +
                    ' -CAkey ' + CA_KEY_DIR +
                    ' -CA ' + CA_CERT_DIR +
                    ' -in ' + csr_dir +
                    ' -extfile ' + config_dir +
                    ' -out ' + crt_dir, shell=True, stderr=subprocess.DEVNULL)
    return crt_dir


def generate_csr(cert_dict):
    config_dir = generate_config(cert_dict)
    csr_dir = CERT_ROOT + cert_dict['serialNumber'] + '.csr'
    subprocess.call('openssl req -new' +
                    ' -config ' + config_dir +
                    ' -key ' + GEN_KEY_DIR +
                    ' -out ' + csr_dir, shell=True, stderr=subprocess.DEVNULL)
    return csr_dir, config_dir


def generate_config(cert_dict):
    common_name = ''
    for pairs in cert_dict['subject']:
        if pairs[0][0] == 'commonName':
            common_name = pairs[0][1]

    f = open(CERT_ROOT+cert_dict['serialNumber']+'.cfg', 'w')
    alt_names = cert_dict['subjectAltName']
    if len(alt_names) > 0:
        f.write(SAN_TEMP_ALT)
        f.write('CN = ' + common_name + '\n')
        f.write('[alt_names]' + '\n')
        for i in range(0, len(alt_names)):
            f.write(alt_names[i][0] + '.' + str(i) + ' = ' + alt_names[i][1] + '\n')
    else:
        f.write(SAN_TEMP)
        f.write('CN = ' + common_name + '\n')
    f.close()
    return f.name


def save_cert(cert_raw, name):
    f = open(CERT_ROOT+name, 'w')
    pem = ssl.DER_cert_to_PEM_cert(cert_raw)
    f.write(pem)
    f.close()
    return CERT_ROOT+name


class CertificateRaceCondition(Exception):
    pass


class ServerConnectionError(Exception):
    pass

# if __name__ == "__main__":
    # path = 'www.google.com:443'
    # server_ssl_sock = build_server_conn(path)
    # pprint.pprint(server_ssl_sock.getpeercert())
    # server_ssl_sock.send(b'GET www.google.com/ HTTP/1.1\r\n\r\n')
    # res = server_ssl_sock.recv()
    # pprint.pprint(res)
    # context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    # context.load_cert_chain(certfile='../tyler_mitm.crt', keyfile='../tyler_mitm.key')
    #
    # bindsocket = socket.socket()
    # bindsocket.bind(('', 8001))
    # bindsocket.listen(5)
    #
    # while True:
    #     newsocket, fromaddr = bindsocket.accept()
    #     connstream = context.wrap_socket(newsocket, server_side=True)
    #     try:
    #         deal_with_client(connstream)
    #     finally:
    #         # connstream.shutdown(socket.SHUT_RD)
    #         connstream.close()
    # build_ssl_conns(socket.socket(), 'google.com:443')


