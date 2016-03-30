import os

import argparser as args
from HTTPProxyServer import MITMProxyServer

if args.args.log and not os.path.exists(args.args.log):
    os.makedirs(args.args.log)

opts = args.args
try:
    server = MITMProxyServer(port_num=opts.port)
    server.run(num_workers=opts.numworker, timeout=opts.timeout, log=opts.log)
except KeyboardInterrupt:
    print("\nKeyboard interrupt received, exiting.")
    if server is not None:
        server.close()
