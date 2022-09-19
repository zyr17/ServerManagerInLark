#!/usr/bin/env python3

import os 
import sys

def copy_shell(server, username, userid):
    script = open('setuser.sh').read()
    script = script.replace('USER', username)
    script = script.replace('ID', userid)
    open('/tmp/setuser.sh', 'w').write(script)
    os.system(f'scp /tmp/setuser.sh {server}:/tmp/setuser.sh')
    os.system(f'ssh {server} "bash /tmp/setuser.sh"')


if __name__ == '__main__':
    server_path = sys.argv[1]
    servers = open(server_path).read().strip().split('\n')
    username = sys.argv[2]
    userid = sys.argv[3]
    userid = userid[:7] + userid[8:]
    for server in servers:
        print(f'server {server}')
        copy_shell(server, username, userid)
