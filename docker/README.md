# RedBot Docker Image Setup

This folder contains the Dockerfile which can be used to build a docker image of RedBot.

## Building the image
To build this image, run `docker build -t IMAGENAME:VER .` within this directory. This will set up a Python image based upon Debian Buster, with the latest Python 3.x build.

## Setting up RedBot for the first time
Once this image has been built, it needs some setup to be able to run redbot successfully.
Whilst in this folder, run the following commands:
```
mkdir -p ${PWD}/share
mkdir -p ${PWD}/Red-DiscordBot
```
Then, start the image in order to set up the bot for the first time.
```
docker run -it -v ${PWD}/share:/home/redbot/.local/share -v ${PWD}/Red-DiscordBot:/usr/local/share/Red-DiscordBot IMAGENAME:VER /bin/bash
```

Once in the container, run `redbot-setup` and set up RedBot as you would normally. Once this is complete, run `redbot $Bot_Name` and add your token and prefix.
Once the bot has initialised, press Ctrl + C to exit the bot, then Ctrl + D to exit the container.

Finally, to start the bot, please run 
```
docker run -it --detach -v ${PWD}/share:/home/redbot/.local/share -v ${PWD}/Red-DiscordBot:/usr/local/share/Red-DiscordBot IMAGENAME:VER /bin/bash -c "redbot $Bot_Name"
```
