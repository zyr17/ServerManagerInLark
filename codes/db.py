import redis
import time
import logging
import base64
import secrets


def is_valid_pk(pk):
    """
    check if a public key is valid
    """
    pk = pk.split(' ')
    if len(pk) < 2:
        return False
    try:
        data = base64.b64decode(pk[1])
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


def generate_password(length = 12):
    """
    generate a password with specified length.
    """
    LOWER = 'abcdefghijklmnopqrstuvwxyz'
    UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    NUMBER = '0123456789'
    OTHER = '!@#$%^&*()+-=~[]{}<>'
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


class RedisConnect:
    """
    connect to Redis server in `redis' docker.
    except specified, all functions is used to get/set value with a key.
    """
    def __init__(self):
        self.conn = redis.StrictRedis(host = 'redis', decode_responses=True)
        self.an_prefix = 'account_name_'

    def _message_id_to_value(self, message_id, value = None):
        """
        get or set message_id. if value is not set, return value.
        else, replace value. not recommended to directly use, 
        use self.message_id_last_process_time instead.

        return: if get or successfully set, return (value, None)
            if got error, return (error, Error message)
        """
        if value is None:
            res = self.conn.get(message_id)
            if res is None:
                return None, 'empty message value'
            return res, None
        self.conn.set(message_id, value)
        return value, None

    def message_id_last_process_time(self, message_id):
        """
        input message id, will get its last process time (UNIX timestamp).
        if it is the first time to process, will return 0.
        the process time of message_id will be updated to now.

        return: 0 for first process, otherwise last process time.
        """
        last_res, _ = self._message_id_to_value(message_id)
        self._message_id_to_value(message_id, time.time())
        return 0 if last_res is None else last_res

    def user_id_to_account_name(self, user_id, account_name = None, 
                                strict = True):
        """
        get or set account name by user id. if account_name is not set, 
        return account name. else, replace account name.
        strict: if True, account name can only be replaced when it is None.

        return: if get or successfully set, return (account_name, None).
            if got error, return (None, Error message).
        """
        if account_name is None:
            res = self.conn.get(user_id)
            if res is None:
                return None, 'empty account name'
            return res, None
        else:
            current = self.conn.get(user_id)
            if strict and current is not None:
                return (
                    None, 
                    f'try to bind account_name({account_name}) of '
                    f'user_id({user_id}) but already binded to ({current})!'
                )
            self.conn.set(user_id, account_name)
            return account_name, None

    def _account_pk_key(self, account_name):
        return self.an_prefix + account_name + '_pk'

    def _account_passwd_key(self, account_name):
        return self.an_prefix + account_name + '_passwd'

    def user_id_to_pk(self, user_id, pk = None, append = True):
        """
        alias of account_name_to_pk, except use user id as input, will
        find account name and call self.account_name_to_pk

        return: if user id has corresponding account name, return the results
            of self.account_name_to_pk; otherwise, return (None, Error message)
        """
        account_name = self.conn.get(user_id)
        if account_name is None:
            return None, 'user id has no corresponding account name'
        return self.account_name_to_pk(account_name, pk, append)
            
    def account_name_to_pk(self, account_name, pk = None, append = True):
        """
        get or set public key of an account. will check pk basic format.
        after set, trigger self.update_account_pk.

        when set, defaule is append, and use `:' to split. 
        if not append, will replace the value.

        return: if get or successfully set, return ([pk1, pk2, ...], None)
            if got error, return (None, Error message)
        """
        key = self._account_pk_key(account_name)
        current = self.conn.get(key)
        if pk is None:
            if current is None:
                return None, 'empty public key'
            return current.split(':'), None
        if ':' in pk:
            return None, "public key should not contain `:'"
        if not is_valid_pk(pk):
            return None, 'public key is not valid'
        if current is None:
            current = ''
        if len(current) != 0:
            pk = current + ':' + pk
        self.conn.set(key, pk)
        self.update_account_pk(account_name)
        return pk.split(':'), None

    def update_account_pk(self, account_name):
        """
        update public keys of account
        """
        key = self._account_pk_key(account_name)
        # TODO 
        logging.warning(f'try to update public keys of {account_name}')

    def user_id_to_password(self, user_id, password = None):
        """
        alias of account_name_to_password, except use user id as input, will
        find account name and call self.account_name_to_password

        return: if user id has corresponding account name, return the results
            of self.account_name_to_pk; otherwise, return (None, Error message)
        """
        account_name = self.conn.get(user_id)
        if account_name is None:
            return None, 'user id has no corresponding account name'
        return self.account_name_to_password(account_name, password)
            
    def account_name_to_password(self, account_name, password = None):
        """
        get or set password of an account. 
        after set, trigger self.update_account_passwd.

        return: if get or successfully set, return (password, None)
            if got error, return (None, Error message)
        """
        key = self._account_passwd_key(account_name)
        if password is not None:
            return None, 'unable to set password, can only get random password'
        new_passwd = generate_password()
        # self.conn.set(key, new_passwd)  # currently no need to save in db
        self._update_account_passwd(account_name, new_passwd)
        return new_passwd, None

    def _update_account_passwd(self, account_name, passwd):
        """
        update password of an account.
        """
        # TODO
        logging.warning(f'try to update password of {account_name}')
    
    def clear_user_data(self, user_id):
        """
        clear user data based on user_id. if it is linked to a account name,
        all data about this account will be removed too.

        return: list of removed keys in db.
        """
        rmkeys = [user_id]
        account_name, _ = self.user_id_to_account_name(user_id)
        if account_name is not None:
            rmkeys.append(self._account_pk_key(account_name))
            rmkeys.append(self._account_passwd_key(account_name))
        else:
            rmkeys = []
        if len(rmkeys):
            self.conn.delete(*rmkeys)
        return rmkeys, None

    def get_all_keys(self):
        """
        get all keys
        """
        res = self.conn.keys()
        return res, None

    def get_set_db(self, key, value = None):
        """
        get and set kv in db directly
        """
        if value is None:
            res = self.conn.get(key)
            if res is None:
                return None, 'Key {key} not exist'
            return res, None
        if value is None:
            self.conn.delete(key)
            return 'None', None
        else:
            self.conn.set(key, value)
            return value, None

    def clear_message_id(self):
        """
        clear message_id in db
        """
        keys = self.conn.keys('om_*')
        if len(keys):
            self.conn.delete(*keys)
        return keys, None
