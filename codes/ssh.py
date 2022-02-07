import os
import logging
from subprocess import PIPE, Popen
from dotenv import load_dotenv, find_dotenv
from multiprocessing.dummy import Pool as DummyPool
from multiprocessing import Pool


load_dotenv(find_dotenv())


available_servers = open('ENV/available_servers').read().strip().split('\n')


def exec_cmd(cmd):
    logging.warning(f'running command: {cmd}')
    p = Popen(cmd, shell = True, stdout = PIPE, stderr = PIPE)
    p.wait()
    stdout, stderr = p.communicate()
    return p.returncode, stdout.decode('utf8'), stderr.decode('utf8')


def change_password(server, user, password):
    cmd = f""" ssh {server} "echo '{user}:{password}' | chpasswd" """
    return exec_cmd(cmd)


def change_password_w(args):
    return change_password(*args)


def lock_password(server):
    users = open('ENV/available_accounts').read().strip().split('\n')
    cmd = f"""ssh {server} " """
    for user in users:
        cmd += f""" passwd -l {user}; """
    cmd += f""" " """
    return exec_cmd(cmd)


def get_auth_keys(server, user):
    cmd = (
        f""" ssh {server} " """
        f""" if [[ ! -e /home/{user}/.ssh ]]; then """
        f"""   mkdir /home/{user}/.ssh; """
        f"""   chown {user}:{user} /home/{user}/.ssh; """
        f""" fi; """
        f""" if [[ ! -e /home/{user}/.ssh/authorized_keys ]]; then """
        f"""   touch /home/{user}/.ssh/authorized_keys; """
        f"""   chmod 600 /home/{user}/.ssh/authorized_keys; """
        f"""   chown {user}:{user} /home/{user}/.ssh/authorized_keys; """
        f""" fi; """
        f""" cat /home/{user}/.ssh/authorized_keys;" """
    )
    return exec_cmd(cmd)


def set_auth_keys(server, user, auth_keys):
    cmd = (
        f""" ssh {server} "echo {auth_keys} | tr ':' '\\n' """
        f""" > /home/{user}/.ssh/authorized_keys;" """
    )
    return exec_cmd(cmd)


def change_all_password(user, password, pool = 5):
    """
    change all password in servers, pool parallel number with multiprocessing.

    return: if all success, none. else, a dict: 
        {error_server_name: { stdout: xxx, stderr: yyy } }
    """
    pool = Pool(pool)
    args = []
    for i in available_servers:
        args.append([i, user, password])
    errors = {}
    for server, [retcode, res_out, res_err] \
            in zip(available_servers, pool.imap(change_password_w, args)):
        # logging.warning(str((retcode, res_out, res_err)))
        if retcode != 0:
            errors[server] = {'stdout': res_out, 'stderr': res_err}
    pool.close()
    pool.join()
    if len(errors):
        return errors


def lock_all_password(pool = 5):
    """
    lock all password in servers, pool parallel number with multiprocessing.
    expected to run daily.

    return: if all success, none. else, a dict: 
        {error_server_name: { stdout: xxx, stderr: yyy } }
    """
    pool = Pool(pool)
    errors = {}
    for server, [retcode, res_out, res_err] \
            in zip(available_servers, pool.imap(lock_password, 
                                                available_servers)):
        # logging.warning(str((retcode, res_out, res_err)))
        if retcode != 0:
            errors[server] = {'stdout': res_out, 'stderr': res_err}
    pool.close()
    pool.join()
    if len(errors):
        return errors


def change_auth_keys(server, user, auth_keys):
    """
    update authorize keys. ath_keys is list of keys.
    will get current auth_keys, remove keys with auth_tag, and add new 
    auth_keys with auth_tag.

    return: if success, none. else, a dict: { stdout: xxx, stderr: yyy }
    """
    auth_tag = os.getenv('AUTH_KEY_TAG')
    retcode, out, err = get_auth_keys(server, user)
    if retcode != 0:
        return {'stdout': out, 'stderr': err}
    current_keys = [x for x in out.strip().split('\n') if auth_tag not in x]
    for key in auth_keys:
        current_keys.append(f'{key} {auth_tag}')
    retcode, out, err = set_auth_keys(server, user, ':'.join(current_keys))
    if retcode != 0:
        return {'stdout': out, 'stderr': err}
    return 0, None, None


def change_auth_keys_w(args):
    return change_auth_keys(*args)

def change_all_auth_keys(user, auth_keys, pool = 5):
    pool = Pool(pool)
    args = []
    for i in available_servers:
        args.append([i, user, auth_keys])
    errors = {}
    for server, [retcode, res_out, res_err] \
            in zip(available_servers, pool.imap(change_auth_keys_w, args)):
        if retcode != 0:
            errors[server] = {'stdout': res_out, 'stderr': res_err}
    pool.close()
    pool.join()
    if len(errors):
        return errors


def get_nvidia_smi(server):
    """
    remote nvidia-smi. if success, return [response, None], 
    else [None, error_dict]
    """
    if server not in available_servers:
        return None, { 'stdout': None, 'stderr': 'unrecognized server name' }
    retcode, out, err = exec_cmd(f'ssh {server} "nvidia-smi"')
    if retcode != 0:
        return None, {'stdout': out, 'stderr': err}
    return out, None


def get_my_monitor(server, all = False):
    """
    Like nvidia-smi, but scp my-monitor to target server and run. all means 
    show full length command.
    """
    if server not in available_servers:
        return None, { 'stdout': None, 'stderr': 'unrecognized server name' }
    retcode, out, err = exec_cmd(
        f'scp {os.path.dirname(os.path.abspath(__file__))}/my-monitor '
        f'{server}:/tmp/my-monitor'
    )
    if retcode != 0:
        return None, {'stdout': out, 'stderr': err}
    all = '-a' if all else ''
    retcode, out, err = exec_cmd(f'ssh {server} "/tmp/my-monitor -1 {all}"')
    if retcode != 0:
        return None, {'stdout': out, 'stderr': err}
    return out, None
