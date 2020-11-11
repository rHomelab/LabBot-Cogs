FROM python:3.8-buster

ENV PATH="/home/redbot/.local:/home/redbot/.local/bin:${PATH}"

RUN apt-get update && \
   apt-get --no-install-reccomends -y install make wget curl python3-openssl git openjdk-11-jre && \
   apt-get clean && \
   groupadd -r redbot && useradd  -r -m -g redbot redbot && \
   mkdir -p /usr/local/share/Red-DiscordBot && \
   chown -R redbot:redbot /usr/local/share/Red-DiscordBot/ && \
   mkdir -p /home/redbot/.local/share

USER redbot

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --no-cache -U --user -r /tmp/requirements.txt
