FROM python:buster
RUN apt update
RUN apt -y install make wget curl python3-openssl git openjdk-11-jre
RUN groupadd -r redbot && useradd  -r -m -g redbot redbot
RUN mkdir -p /usr/local/share/Red-DiscordBot
RUN chown -R redbot:redbot /usr/local/share/Red-DiscordBot/
USER redbot
COPY requirements.txt /tmp/requirements.txt
ENV PATH="/home/redbot/.local:/home/redbot/.local/bin:${PATH}"
RUN python -m pip install -U --user -r /tmp/requirements.txt
RUN mkdir -p /home/redbot/.local/share
