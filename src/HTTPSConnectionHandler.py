import pprint
import socket
import ssl
import subprocess

CERT_ROOT = '../certificates/'
CA_KEY = 'MITM_CA.key'
CA_KEY_DIR = CERT_ROOT + CA_KEY
CA_CERT = 'MITM_CA.crt'
CA_CERT_DIR = CERT_ROOT + CA_CERT
GEN_KEY = 'cert_gen.key'
GEN_KEY_DIR = CERT_ROOT + GEN_KEY
SAN_TEMP = '''[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
prompt = no

[v3_req]
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

[v3_req]
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
    server_ssl_sock = build_server_conn(path)
    client_socket.sendall(('HTTP/1.1 %d %s\r\n\r\n' % (200, 'OK')).encode('latin-1', 'strict'))

    cert_dict = server_ssl_sock.getpeercert()
    crt_dir = generate_fake_cert(cert_dict)
    client_ssl_sock = build_client_conn(client_socket, crt_dir)

    return server_ssl_sock, client_ssl_sock


def build_server_conn(path):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_OPTIONAL
    # context.load_verify_locations('/etc/ssl/certs/ca-bundle.crt')
    context.set_default_verify_paths()
    host, port = parse_connect_path(path)

    ssl_sock = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    ssl_sock.connect((host, port))
    return ssl_sock


def build_client_conn(sock, crt_dir):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.load_cert_chain(certfile=crt_dir, keyfile=GEN_KEY_DIR)
    client_ssl_sock = context.wrap_socket(sock, server_side=True)
    return client_ssl_sock


def parse_connect_path(path):
    host = path[:path.find(':')]
    port = path[path.find(':')+1:]
    if len(port) < 1:
        port = 443
    else:
        port = int(port)
    return host, port


def generate_fake_cert(cert_dict):
    csr_dir, common_name = generate_csr(cert_dict)
    crt_dir = CERT_ROOT + common_name + '.crt'
    subprocess.call('openssl x509 -req -days 365 -CAcreateserial' +
                    ' -CAkey ' + CA_KEY_DIR +
                    ' -CA ' + CA_CERT_DIR +
                    ' -in ' + csr_dir +
                    ' -out ' + crt_dir, shell=True)
    return crt_dir


def generate_csr(cert_dict):
    common_name, config_dir = generate_config(cert_dict)
    csr_dir = CERT_ROOT + common_name + '.csr'
    subprocess.call('openssl req -new' +
                    ' -config ' + config_dir +
                    ' -key ' + GEN_KEY_DIR +
                    ' -out ' + csr_dir, shell=True)
    return csr_dir, common_name


def generate_config(cert_dict):
    common_name = ''
    for tuple in cert_dict['subject']:
        if tuple[0][0] == 'commonName':
            common_name = tuple[0][1]

    f = open(CERT_ROOT+common_name+'.cfg', 'w')
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
    return common_name, f.name


def save_cert(cert_raw, name):
    f = open(CERT_ROOT+name, 'w')
    pem = ssl.DER_cert_to_PEM_cert(cert_raw)
    f.write(pem)
    f.close()
    return CERT_ROOT+name


def deal_with_client(connstream):
    data = connstream.recv(1024)
    # empty data means the client is finished with us
    while data:
        data = connstream.recv(1024)
        pprint.pprint(data)
    # finished with client

if __name__ == "__main__":
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
    ssl_sock = build_server_conn('google.com:443')
    cert_raw = ssl_sock.getpeercert(True)
    save_cert(cert_raw, 'google_orig.crt')

