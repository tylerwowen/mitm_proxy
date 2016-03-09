import socket
import ssl


def build_ssl_conns(client_socket, path):
    server_ssl_sock = build_server_conn(path)
    cert = server_ssl_sock.getpeercert()
    client_ssl_sock = build_client_conn(client_socket, cert)

    return server_ssl_sock, client_ssl_sock


def build_server_conn(path):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    # context.load_verify_locations('/etc/ssl/certs/ca-bundle.crt')
    host, port = parse_connect_path(path)

    ssl_sock = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    ssl_sock.connect((host, port))
    return ssl_sock


def build_client_conn(sock, cert):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.load_cert_chain(certfile="mycertfile", keyfile="mykeyfile")
    return context.wrap_socket(sock, server_side=True)


def parse_connect_path(path):
    host = path[:path.find(':')]
    port = path[path.find(':')+1:]
    if len(port) < 1:
        port = 443
    else:
        port = int(port)
    return host, port
