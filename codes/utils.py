#!/usr/bin/env python3.8


import base64
import logging
import secrets
import json
import logging


class Obj(dict):
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
                setattr(self, a, [Obj(x) if isinstance(x, dict) else x for x in b])
            else:
                setattr(self, a, Obj(b) if isinstance(b, dict) else b)


def dict_2_obj(d: dict):
    return Obj(d)


def is_valid_account_name(account_name):
    valid = open('ENV/available_accounts').read().strip().split('\n')
    return account_name in valid


def is_valid_pk(pk):
    """
    check if a public key is valid
    """
    pk = pk.split(' ')
    if len(pk) < 2:
        return False
    try:
        data = base64.b64decode(pk[1])
        recover = base64.b64encode(data).decode()
        if recover != pk[1]:  # decode & encode result differ
            return False
        for i in range(3):
            j = (data[0] << 24) + (data[1] << 16) + (data[2] << 8) + data[3]
            data = data[4:]
            if len(data) < j:
                return False
            part = data[:j]
            data = data[j:]
            if i == 0:
                # content should same as pk[0]
                if pk[0] != part.decode():
                    return False
        if len(data):
            return False
    except Exception as e:
        raise e
        return False
    return True


def duplicate_pk(current, pk):
    if current is None:
        return False
    current = current.split(':')
    for c in current:
        def r(x):
            return ' '.join(x.split(' ')[:2])
        if r(c) == r(pk):
            return True
    return False


def generate_password(length = 12):
    """
    generate a password with specified length.
    """
    LOWER = 'abcdefghjkmnopqrstuvwxyz'
    UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    NUMBER = '234567892345678923456789'
    OTHER = '@%_+-=@%_+-=@%_+-=@%_+-='
    CHARS = [LOWER, UPPER, NUMBER, OTHER]
    secret_generator=secrets.SystemRandom()
    assert length >= 4, 'generated password length is at least 4'
    passwd = ''
    for i in CHARS:
        passwd += i[secret_generator.randint(1, len(i)) - 1]
    CHARS = ''.join(CHARS)
    while len(passwd) < length:
        passwd += CHARS[secret_generator.randint(1, len(CHARS)) - 1]
    return passwd


def parse_alertmanager_value_string(vs):
    """
    parse value string, return a list with important info dict.
    """
    use_key = ['hostname', 'mountpoint', 'index']
    vs = vs.strip()
    if vs[0] != '[':
        # unknown format, skip
        return [{'raw': vs}]
    vs = vs.split('[')[1:]
    res = []
    for onevs in vs:
        raw_onevs = '[' + onevs
        onevs = [x.strip() for x in onevs.split("'")]
        if 'metric' not in onevs[0] or onevs[1][0] != '{' or onevs[1][-1] != '}':
            # unknown format, skip
            res.append({'raw': raw_onevs})
            continue
        try:
            onevs = onevs[1][1:-1].split(', ')
            onevs = [x.split('=') for x in onevs]
            ores = {}
            for k, v in onevs:
                if k in use_key:
                    ores[k] = v[1:-1]
            res.append(ores)
        except Exception as e:
            # json parse error
            raise e
            res.append({'raw': "'".join(onevs)})
    return res


def generate_alert_card(status, title, detail, rule_id, fingerprint):
    template = '{ "config": { "wide_screen_mode": true }, "elements": [ { "tag": "div", "text": { "content": "DETAIL", "tag": "plain_text" } } ], "header": { "template": "COLOR", "title": { "content": "STATUS: TITLE", "tag": "plain_text" } } }'
    template = json.loads(template)
    kwargs = {}
    if status == 'firing':
        template['header']['template'] = 'red' 
    elif status == 'resolved':
        template['header']['template'] = 'green' 
    else:
        template['header']['template'] = 'blue'
    template['header']['title']['content'] = f'{status.upper()}: {title}'
    template['elements'][0]['text']['content'] = (
        '\n'.join([str(x) for x in detail])
        + '\n' + '-' * 10
        + f'\nalert rule id: {rule_id}'
        + f'\nfingerprint: {fingerprint}'
    )
    return json.dumps(template)


def list_all_servers():
    """
    list all server nickname and IP.
    """
    server_nickname = open('ENV/available_servers').read().strip().split('\n')
    hosts = []
    try:
        hosts += open('/etc/hosts').read().strip().split('\n')
    except:
        pass
    try:
        hosts += open('/etc/host_hosts').read().strip().split('\n')
    except:
        pass
    res = []
    for nickname in server_nickname:
        for host in hosts:
            if nickname in host:
                res.append(host.split())
                break
    logging.warning(f'servers: {res}')
    return res


def update_hosts():
    """
    update /etc/host_hosts into /etc/hosts
    """
    hosts = []
    try:
        hosts += open('/etc/hosts').read().strip().split('\n')
    except:
        pass
    try:
        hosts += open('/etc/host_hosts').read().strip().split('\n')
    except:
        pass

    hosts = list(set(hosts))
    hosts.sort()
    hosts_str = '\n'.join(hosts)
    logging.warning(f"Host updated: \n{hosts_str}")
    open('/etc/hosts', 'w').write('\n'.join(hosts))
