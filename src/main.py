import os

import argparser as args
import HTTPProxy

if args.args.log and not os.path.exists(args.args.log):
    os.makedirs(args.args.log)

HTTPProxy.run(handler_class=HTTPProxy.MITMHTTPRequestHandler, port=args.args.port)
