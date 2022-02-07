FROM python:latest
RUN pip install --no-cache-dir fastapi[all] Flask==2.0.2 requests==2.24.0 python-dotenv pycryptodome redis Flask-APScheduler apscheduler -i https://mirrors.aliyun.com/pypi/simple/ \
    && echo "cd /app/; python server.py" > /run.sh
    # && echo "cd /app/; uvicorn api:app --reload --host 0.0.0.0 --port 29980" > /run.sh

VOLUME /app

EXPOSE 29980

CMD ["/bin/sh", "/run.sh"]
