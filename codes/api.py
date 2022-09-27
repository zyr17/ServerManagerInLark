#! /usr/bin/env python3.8
import os
import logging
import requests

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

# const
TENANT_ACCESS_TOKEN_URI = "/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URI = "/open-apis/im/v1/messages"
USER_URI = '/open-apis/contact/v3/users'


class MessageApiClient(object):
    def __init__(self, app_id, app_secret, lark_host):
        self._app_id = app_id
        self._app_secret = app_secret
        self._lark_host = lark_host
        self._tenant_access_token = ""
        self._admin_cache = {}

    @staticmethod
    def _c_msg(text):
        assert '"' not in text, f'text({text}) contains " is not supported now'
        return f'{{"text":"{text}"}}'

    @property
    def tenant_access_token(self):
        return self._tenant_access_token

    def send_text_with_open_id(self, open_id, content):
        self.send("open_id", open_id, "text", content)

    def reply_text_with_message_id(self, message_id, content):
        self.reply(message_id, "text", content)

    def reply_user_id(self, message_id, user_id):
        self.reply(message_id, "text", self._c_msg(f"ID: {user_id}"))

    def reply(self, message_id, msg_type, content):
        # reply message
        self._authorize_tenant_access_token()
        url = f"{self._lark_host}{MESSAGE_URI}/{message_id}/reply"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        req_body = {
            "content": content,
            "msg_type": msg_type,
        }
        resp = requests.post(url=url, headers=headers, json=req_body)
        MessageApiClient._check_error_response(resp)

    def send(self, receive_id_type, receive_id, msg_type, content):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}?receive_id_type={}".format(
            self._lark_host, MESSAGE_URI, receive_id_type
        )
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        req_body = {
            "receive_id": receive_id,
            "content": content,
            "msg_type": msg_type,
        }
        resp = requests.post(url=url, headers=headers, json=req_body)
        MessageApiClient._check_error_response(resp)

    def _authorize_tenant_access_token(self):
        # get tenant_access_token and set, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal
        url = "{}{}".format(self._lark_host, TENANT_ACCESS_TOKEN_URI)
        req_body = {"app_id": self._app_id, "app_secret": self._app_secret}
        response = requests.post(url, req_body)
        MessageApiClient._check_error_response(response)
        self._tenant_access_token = response.json().get("tenant_access_token")
        logging.warning(f't_access_token {self._tenant_access_token}')

    def check_user_is_admin(self, user_id):
        if user_id not in self._admin_cache:
            logging.warning('unknown user, check whether is admin')
            self._admin_cache[user_id] = self._get_user_is_admin(user_id)
        return self._admin_cache[user_id]

    def _get_user_is_admin(self, user_id):
        self._authorize_tenant_access_token()
        url = f'{self._lark_host}{USER_URI}/{user_id}?user_id_type=user_id'
        headers = {
            "Authorization": "Bearer " + self.tenant_access_token,
        }
        response = requests.get(url, headers = headers)
        MessageApiClient._check_error_response(response)
        is_admin = response.json()['data']['user']['is_tenant_manager']
        return is_admin

    @staticmethod
    def _check_error_response(resp):
        # check if the response contains error information
        if resp.status_code != 200:
            resp.raise_for_status()
        response_dict = resp.json()
        code = response_dict.get("code", -1)
        if code != 0:
            logging.error(response_dict)
            raise LarkException(code=code, msg=response_dict.get("msg"))


class LarkException(Exception):
    def __init__(self, code=0, msg=None):
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "{}:{}".format(self.code, self.msg)

    __repr__ = __str__
