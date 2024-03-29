#!/usr/bin/env python3.8

import os
import logging
import requests
import json
from db import RedisConnect
from command import CommandParser
from api import MessageApiClient
from event import (
    MessageReceiveEvent, 
    UrlVerificationEvent, 
    AlertManagerEvent,
    EventManager
)
from flask import Flask, jsonify, request
from flask_apscheduler import APScheduler
from dotenv import load_dotenv, find_dotenv
from utils import (
    parse_alertmanager_value_string, 
    generate_alert_card,
    update_hosts
)
from ssh import lock_all_password

# load env parameters form file named .env
load_dotenv(find_dotenv())

app = Flask(__name__)

# load from env
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")
ALERT_GROUP_NUMBER = os.getenv("ALERT_GROUP_NUMBER")
# LOCK_PASSWORD_INTERVAL = os.getenv("LOCK_PASSWORD_INTERVAL")

# init service
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)
event_manager = EventManager()
database = RedisConnect()
command_parser = CommandParser(
    message_api_callback = message_api_client.reply_text_with_message_id,
    message_api_callback_text_argname = 'content',
    check_user_is_admin = message_api_client.check_user_is_admin,
    database = database
)

def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running werkzeug')
    shutdown_func()

# init scheduler
# scheduler = sched.scheduler(time.time, time.sleep)
scheduler = APScheduler()
scheduler.init_app(app)

@scheduler.task('cron', id = 'lock_all_password_scheduler', hour = 4)
def lock_all_password_scheduler():
    res = lock_all_password()
    if res is not None:
        logging.warning(f'error in lock_all_password: {res}')

@scheduler.task('interval', id = 'daily_shutdown_scheduler', days = 1)
def daily_shutdown_scheduler():
    # import requests
    # requests.get('http://localhost:29980/shutdown_the_server')
    os.system('pkill -2 python')

scheduler.start()


@event_manager.register("url_verification")
def request_url_verify_handler(req_data: UrlVerificationEvent):
    # url verification, just need return challenge
    if req_data.event.token != VERIFICATION_TOKEN:
        raise Exception("VERIFICATION_TOKEN is invalid")
    return jsonify({"challenge": req_data.event.challenge})


@event_manager.register("im.message.receive_v1")
def message_receive_event_handler(req_data: MessageReceiveEvent):
    message = req_data.event.message
    if message.message_type != "text":
        logging.warning("Other types of messages have not been processed yet")
        return jsonify()
        # get open_id and text_content
    message_id = message.message_id
    user_id = req_data.event.sender.sender_id.user_id
    msg_ptime = database.message_id_last_process_time(message_id)
    if msg_ptime == 0:
        # echo text message
        # message_api_client.send_text_with_open_id(open_id, text_content)
        # message_api_client.reply_text_with_message_id(message_id, text_content)
        # message_api_client.reply_user_id(message_id, user_id)
        logging.warning('is admin? '
                        f'{message_api_client.check_user_is_admin(user_id)}')
        command_parser.parse(req_data, {'message_id': message_id})
        # raise NotImplementedError
        pass
    else:
        logging.warning("message that has received bebore!")
    return jsonify()


@event_manager.register("alert_manager")
def alert_manager_event_handler(req_data: AlertManagerEvent):
    data = req_data.event
    logging.warning(f'alertmanager: {req_data.dict}')
    for alert in data.alerts:
        status = alert.status
        title = alert.labels.alertname
        try:
            rule_id = alert.labels.__alert_rule_uid__
        except:
            rule_id = None
        fingerprint = alert.fingerprint
        if '__value_string__' in dir(alert.annotations):
            detail = parse_alertmanager_value_string(alert.annotations.__value_string__)
        else:
            detail = []
        # detail = json.loads(alert.annotations.__value_string__)
        message = generate_alert_card(status, title, detail, rule_id, fingerprint)
        message_api_client.send(
            'chat_id', 
            ALERT_GROUP_NUMBER, 
            'interactive',
            message
        )
        # logging.warning(detail)
    return jsonify()


@app.errorhandler
def msg_error_handler(ex):
    logging.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@app.route("/", methods=["POST"])
def callback_event_handler():
    # init callback instance and handle
    event_handler, event = event_manager.get_handler_with_event(VERIFICATION_TOKEN, ENCRYPT_KEY)

    return event_handler(event)


@app.route("/shutdown_the_server", methods=["GET"])
def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running werkzeug')
    logging.error('try shutdown')
    shutdown_func()
    logging.error('shutdown over?')
    return jsonify("shutdown")

if __name__ == "__main__":
    # init()
    update_hosts()
    app.run(host="0.0.0.0", port=29980, debug=True)
