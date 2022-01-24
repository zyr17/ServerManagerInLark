#!/usr/bin/env python3.8


import base64
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
    NUMBER = '23456789'
    OTHER = '~!@#$%^&*_+-='
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


