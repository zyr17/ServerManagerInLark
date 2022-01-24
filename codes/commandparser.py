import json
import logging
from event import MessageReceiveEvent
from flask import jsonify


class Command:
    """
    Base class of commands.
    """
    def __init__(self, message_api_callback, message_api_callback_text_argname, 
                 check_user_is_admin, database):
        """
        args:
            message_api_callback: a callback function to reply in lark.
            message_api_callback_text_argname: argname of callback to be filled
                with generated texts.
            check_user_is_admin: check certain user_id is admin user. useful
                to perform previliged commands.
            database: a database instance to set/get informations.
        """
        self.db = database
        self.api_cb = message_api_callback
        self.api_cb_textkey = message_api_callback_text_argname
        self._user_admin_check = check_user_is_admin

    @staticmethod
    def command_name():
        """
        The command name to trigger
        """
        return ""

    @staticmethod
    def _is_p2p(req_data: MessageReceiveEvent):
        return req_data.event.message.chat_type == 'p2p'

    @staticmethod
    def _get_user_id(req_data: MessageReceiveEvent):
        return req_data.event.sender.sender_id.user_id

    def _private_chat_command_notify(self, 
                                     req_data: MessageReceiveEvent, 
                                     cb_kwargs: dict):
        """
        For commands that should only be used in private chat, 
        make notification.

        return: if not in private, return true; else return false
        """
        if not self._is_p2p(req_data):
            self._reply_text_msg(
                'Please private chat me with this command.',
                cn_kwargs
            )
            return True
        return False

    def _not_admin_notify(self, user_id:str, cb_kwargs: dict):
        """
        Check if is admin user. if not, make notification.

        return: if is not admin, return True, else False.
        """
        if not self._user_admin_check(user_id):
            self._reply_text_msg(
                'Sorry, only admins can use this command',
                cb_kwargs
            )
            return True
        return False

    def _reply_text_msg(self, text_msg: str, cb_kwargs: dict):
        """
        reply text message
        """
        cb_kwargs[self.api_cb_textkey] = json.dumps({"text":text_msg})
        self.api_cb(**cb_kwargs)

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        """
        get request information and run.
        args:
            cmd_data: text arguments that after the command. has splitted by 
                space
            req_data: event data
            cb_kwargs: keyword arguments to pass to message_api_callback
        """
        pass


class BindAccount(Command):
    """
    Bind user_id to account_name
    """
    @staticmethod
    def command_name():
        return "BindAccount"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        # if not self._is_p2p(req_data):
        #     return
        if len(cmd_data) != 1:
            self._reply_text_msg(
                'Command "BindAccount" should contain exactly one argument.', 
                cb_kwargs
            )
            return
        user_id = self._get_user_id(req_data)
        res, err_msg = self.db.user_id_to_account_name(user_id, cmd_data[0])
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Success! your user_id: {user_id}, binded account: {res}', 
                cb_kwargs
            )


class CheckAccount(Command):
    """
    Check binded account name 
    """
    @staticmethod
    def command_name():
        return "CheckAccount"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        user_id = self._get_user_id(req_data)
        res, err_msg = self.db.user_id_to_account_name(user_id)
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Success! your user_id: {user_id}, binded account: {res}', 
                cb_kwargs
            )


class GenerateNewPassword(Command):
    """
    generate new password for account
    """
    @staticmethod
    def command_name():
        return "GenerateNewPassword"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        user_id = self._get_user_id(req_data)
        res, err_msg = self.db.user_id_to_password(user_id)
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                'Generate new password success!\n-----\n'
                f'New Password: \n{res}\n-----\n'
                'Please note the password will expire in the next day, '
                'you should generate new password after then. '
                'To use servers more convenient, we highly recommend '
                'using SSH keys as main login method. See '
                'Command "AddNewPublicKey" in doc for details.',
                cb_kwargs
            )


class AddNewPublicKey(Command):
    """
    add new public key for account
    """
    @staticmethod
    def command_name():
        return "AddNewPublicKey"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        if len(cmd_data) == 0:
            self._reply_text_msg(
                'Command "AddNewPublicKey" should take public key as input', 
                cb_kwargs
            )
            return
        user_id = self._get_user_id(req_data)
        res, err_msg = self.db.user_id_to_pk(user_id, ' '.join(cmd_data))
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                'Add public key success!\n'
                'Current available public keys:'
                 + '\n-----\n'.join([''] + res + [''])
                 + 'Delete/modify is not supported now, please wait for newer '
                'version or contact admin.',
                cb_kwargs
            )


class ClearUserData(Command):
    """
    add new public key for account
    """
    @staticmethod
    def command_name():
        return "ClearUserData"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        if len(cmd_data) != 1:
            self._reply_text_msg(
                'Command "ClearUserData" should take one user_id as input', 
                cb_kwargs
            )
            return
        user_id = self._get_user_id(req_data)
        if self._not_admin_notify(user_id, cb_kwargs):
            return
        res, err_msg = self.db.clear_user_data(cmd_data[0])
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Clear data of user_id({cmd_data[0]}) success!\n '
                f'removed {len(res)} keys: {" ".join(res)}',
                cb_kwargs
            )


class GetAllKeys(Command):
    """
    get all keys in db
    """
    @staticmethod
    def command_name():
        return "GetAllKeys"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        user_id = self._get_user_id(req_data)
        if self._not_admin_notify(user_id, cb_kwargs):
            return
        res, err_msg = self.db.get_all_keys()
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Get all keys success!\n'
                f'{len(res)} keys: {" ".join(res)}',
                cb_kwargs
            )


class GetKeyValue(Command):
    """
    get certain key value when key is specified
    """
    @staticmethod
    def command_name():
        return "GetKeyValue"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        if len(cmd_data) != 1:
            self._reply_text_msg(
                'Command "GetKeyValue" should take one key as input', 
                cb_kwargs
            )
            return
        user_id = self._get_user_id(req_data)
        if self._not_admin_notify(user_id, cb_kwargs):
            return
        res, err_msg = self.db.get_set_db(cmd_data[0])
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'{cmd_data[0]}: {res}',
                cb_kwargs
            )


class SetKeyValue(Command):
    """
    set certain key value when key and value is specified
    """
    @staticmethod
    def command_name():
        return "SetKeyValue"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        if len(cmd_data) != 2:
            self._reply_text_msg(
                'Command "SetKeyValue" should take key and value as input', 
                cb_kwargs
            )
            return
        user_id = self._get_user_id(req_data)
        if self._not_admin_notify(user_id, cb_kwargs):
            return
        res, err_msg = self.db.get_set_db(*cmd_data)
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Set success! {cmd_data[0]}: {res}',
                cb_kwargs
            )


class ClearMessageID(Command):
    """
    get all keys in db
    """
    @staticmethod
    def command_name():
        return "ClearMessageID"

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        if self._private_chat_command_notify(req_data, cb_kwargs):
            return
        user_id = self._get_user_id(req_data)
        if self._not_admin_notify(user_id, cb_kwargs):
            return
        res, err_msg = self.db.clear_message_id()
        if res is None:
            self._reply_text_msg(f'Error occured: {err_msg}', cb_kwargs)
        else:
            self._reply_text_msg(
                f'Clear message_id success! {len(res)} keys: {" ".join(res)}',
                cb_kwargs
            )


class CommandParser(Command):
    """
    A special command that parse the text, get real command and call 
    corresponding command class. use self.parse to parse commands.
    """
    def __init__(self, *argv, **kwargs):
        """
        after initialize, save all Command instance in self.commands.
        """
        super().__init__(*argv, **kwargs)
        # all command classes. for new command, add class here.
        self._cmd_classes = [
            BindAccount, 
            CheckAccount,
            GenerateNewPassword,
            AddNewPublicKey,
            ClearUserData,
            GetAllKeys,
            GetKeyValue,
            SetKeyValue,
            ClearMessageID,
        ]
        # save all commands. key is command name, value is commad func.
        self.commands = {}
        for i in self._cmd_classes:
            self.commands[i.command_name().lower()] = i(*argv, **kwargs)

    def run(self, 
            cmd_data: str, 
            req_data: MessageReceiveEvent, 
            cb_kwargs: dict):
        """
        parse a command. the first word separated by space is considered as 
        command, and will use corresponding function to process.
        """
        assert cmd_data is None or len(cmd_data) == 0, \
            'in CommandParser, cmd_data should remain "" or None'
        message = req_data.event.message
        if message.message_type != "text":
            logging.warning("can only process plain text, "
                            f"but got {message.message_type}.")
            return
        text_content = json.loads(message.content)['text'].strip()
        logging.warning(text_content)
        # chat_type = message.chat_type  # p2p or group
        # user_id = req_data.event.sender.sender_id.user_id
        text_content = text_content.split(' ')
        command = text_content[0].lower()
        data = text_content[1:]
        if command in self.commands.keys():
            self.commands[command].run(data, req_data, cb_kwargs)
        else:
            logging.warning(f"not a command: {command}")

    def parse(self, req_data: MessageReceiveEvent, cb_kwargs: dict):
        """
        parse a command. will call self.run to do real parse.
        """
        self.run('', req_data, cb_kwargs)
