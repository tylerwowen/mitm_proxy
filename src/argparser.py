import argparse

parser = argparse.ArgumentParser(prog='mitm', description='MITM HTTPS proxy for CS 176B')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
parser.add_argument('-p', '--port', type=int, required=True,
                    help='The port server will be listening on')
parser.add_argument('-n', '--numworker', metavar='NUM_OF_WORKER', type=int, default=10,
                    help='The number of workers in the thread pool used for handling concurrent HTTP requests.')
parser.add_argument('-t', '--timeout', type=int, default=-1,
                    help='The time (seconds) to wait before give up waiting for response from server. '
                         '(default: ?1, meaning infinite)')
parser.add_argument('-l', '--log',
                    help='Logs all the HTTP requests and their corresponding responses under the directory log.')

args = parser.parse_args()
