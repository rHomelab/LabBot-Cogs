#### This tool checks whether the report contains a message link, aka: link for a message of possible rule breaking or something that the report is about. 
#### It takes the text input and loops through words until it finds the interesting. 

import re

Message = "This is the thing I want to report that https://discord.com/channels/184315303323238400/184315303323238400/339707834105331714"

def WordTester(MessageInText):
    ContainsLink = False
    for Word in MessageInText.split(" "):
        if re.match(r"https://discord.com/channels/[0-9]*/[0-9]*/[0-9]*",Word):
            ContainsLink = True
    return ContainsLink

  
####
#Uncomment this if you want to test it
####

#print(WordTester(Message))       
