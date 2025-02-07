# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

WORKDIR /app

RUN apt-get update && apt-get -y install cron curl

COPY metrics_app/requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY metrics_app .

COPY metrics_app/api_call.sh /etc/cron.d/api_call

RUN chmod 0644 /etc/cron.d/api_call
# Add cron job to call API every 5 minutes
RUN echo "*/5 * * * * /app/api_call.sh" > /etc/cron.d/api_call

RUN crontab /etc/cron.d/api_call
# Create log file for cron
RUN touch /var/log/cron.log

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0", "--port=8085"]