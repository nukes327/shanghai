# NOTES
# (1) Link scanning regex doesn't pick up links without http(s)
#     prepended, I'm not sure I care to fix that
#---------
# TODO
# (1) Fix the config crashing if it receives invalid JSON
# (2) Figure out better server authentication method
# (3) Check for chat moderator status to limit system commands
# (4) Make parse case-insensitive
# (5) Clean up error checking so it checks for specific errors
# (7) LOGGING EVERYTHING
#---------
# Recent Changes:
#   Moved link scanning to its own file so I can add more
#     specialized scanning without clogging up this file
################################################################################

import socket
import json
import time
import re
import codecs
import ssl
import os
from linkscanning import *

class ShanghaiError(Exception):
    """Base Error Class"""
    pass

class ClearanceError(ShanghaiError):
    """Somebody tried to run something above their clearance"""
    def __init__(self, *args, user=None, func=None):
        self.user = user
        self.func = func
    def __str__(self):
        return repr(self.user + " - " + self.func)

class Bot:

    def __init__(self, config="config.txt"):
        self.config = {}
        try:
            f = open(config)
        except FileNotFoundError:
            #File wasn't found, initialize all values
            print("Error, config not found")
            self.config["server"] = input("Server: ")
            self.config["port"] = int(input("Port: "))
            self.config["nick"] = input("Nick: ")
            self.config["pass"] = input("Server pass: ")
            self.config["ssl"] = bool(input("SSL? True or False: ")) # TODO (2)
            self.config["prefix"] = input("Command prefix: ")
            self.config["owner"] = input("Bot owner nick: ")

            #Create file with given name, dump JSON to file
            with open(config, "w+") as f:
                json.dump(self.config, f, indent=4)
        else:
            # TODO (1)
            self.config = json.load(f)
            f.close()
        self.users = {}

        #Loaded later with any channel-specific commands
        self.optcoms = {}

        #Used to call methods from irc messages
        self.syscoms = {"quit" : self.quit,
                        "part" : self.part,
                        "join" : self.join,
                        "echo" : self.say,
                        "addcommand" : self.addcommand,
                        "delcommand" : self.delcommand,
                        "commands" : self.commandlist,
                        "help" : self.commandhelp,
                        "grep" : self.greplogs}

        #Put the channel message regex here
        self.msplit = re.compile(r"""
         :                       #Start of standard IRC message
         (?P<user>[^!]*)         #Get the user's nick
         !\S*?\s*?               #Lose extra, and trailing whitespace
         PRIVMSG                 #We only want to match a PRIVMSG
         \s*?                    #Lose whitespace again
         (?P<chan>\S*)           #Grab the channel the message was to
         \s*?                    #Lose more whitespace
         :(?P<msg>[^\r\n]*)      #Message is whatever is left
        """, re.VERBOSE | re.IGNORECASE)  #Ignore the case just in case

        #Regex to scan a message for links
        self.links = re.compile(r"\bhttps?://[^. ]+\.[^. \t\n\r\f\v][^ \n\r]+")

        #A match object used for regex comparison to decide what to do with data
        self.match = None

        #Message used as default for some method calls
        self.message = ""
        
        self.loadlist()
        
        self.scanner = LinkScanner()

    def send(self, cmd):
        """Send encoded message to irc socket"""
        #Encode to bytes on send
        self.irc.send(str.encode("{}\r\n".format(cmd)))

    def connect(self):
        """Connect to given irc server"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.config["server"], self.config["port"]))
        if self.config["ssl"]:
            self.irc = ssl.wrap_socket(s)
        else:
            self.irc = s
        if self.config["pass"]:
            self.send("PASS {}".format(self.config["pass"]))
        self.send("NICK {}".format(self.config["nick"]))
        self.send("USER {0} {0} {0} :{0}".format(self.config["nick"]))

    def join(self, force=False, channel=None):
        """Join and load commands for given channel"""
        if channel is None:
            channel = self.message

        self.send("JOIN {}".format(channel))
        print("Connected to channel {}".format(channel))
        print("Loading command list for {}".format(channel))

        #Open command file or create a blank file if missing
        try:
            f = open(channel)
        except FileNotFoundError:
            f = open(channel, "w+")
            print("File not found, "
                  "creating a new command list for {}".format(channel))

        #Loads the JSON for the channel-specific commands 
        try:
            self.optcoms[channel] = json.load(f)
        except:
            print("No command list found, initializing")
            self.optcoms[channel] = {}
        else:
            print("Command list loaded, ready to go")
        f.close()

    def ircprint(self, msg=None, user=None):
        """Print message readably to terminal with timestamp"""
        if msg is None:
            msg = self.match.group('msg')
        if user is None:
            user = self.match.group('user')
        msgtime = time.localtime()
        print("[{0[3]:02d}:{0[4]:02d}:{0[5]:02d}] {1}: {2}".format(msgtime,
                                                                   user,
                                                                   msg))

    def greplogs(self, pattern=None, channel=None):
        if pattern is None:
            pattern = self.message
        if channel is None:
            channel = self.match.group('chan')
        pass
        # pseudocode:
        # result = []
        # for filename in os get log files:
        #     # Make sure to read the oldest logs first,
        #     with open(filename) as f:
        #         for line in re.findall(re.compile(pattern, re.MULTILINE),
        #                                file.read())
        #             result.append(line)
        # send( result[-5:] )   <-- want to return the 5 most recent matches

    def say(self, msg=None, channel=None):
        """Send message to channel"""
        if msg is None:
            msg = self.message
        if channel is None:
            channel = self.match.group('chan')
        self.send("PRIVMSG {} :{}".format(channel, msg))
        self.ircprint(msg, "shanghai_doll")

    def part(self, force=False, channel=None):
        """Leave channel and save specific commands"""
        if not force and self.match.group('user') is not self.config["owner"]:
                raise ClearanceError("Unauthorized user",
                                     self.match.group('user'))
        if channel is None:
            channel = self.match.group('chan')
        self.send("PART {}".format(channel))

        #Saves the channel's commands to the channel's file
        print("Writing command list for {} to file...".format(channel))
        f = open(channel, "w")
        json.dump(self.optcoms[channel], f, indent=4)
        f.close()

        #Remove the channel from the channel list
        self.optcoms.pop(channel)

    def quit(self, force=False):
        """Save all open command sets, quit server, and exit program"""
        #You can't iterate over the dict itself because part pops the values
        #And you can't iterate the dict's keys because that returns another damned dict
        if force or (self.match.group('user') == self.config["owner"]):
            for chan in list(self.optcoms.keys()):
                self.part(chan)

            print("Writing userlist to file...")
            f = open("userlist.txt", "w")
            json.dump(self.users, f, indent=4)
            f.close()
            self.send("QUIT")

            exit()
        else:
            self.say("Nope", self.match.group('chan'))


    def loadlist(self):
        """Load global user list"""
        print("Loading user list")
        
        #Opens the global userlist, or creates a new one if not found
        try:
            f = open("userlist.txt")
        except FileNotFoundError:
            f = open("userlist.txt", "w+")
            print("File not found, creating a new userlist.txt")
            
        #Loads the userlist from the file
        try:
            self.users = json.load(f)
        except:
            print("No userlist found in file, initializing")
        else:
            print("Userlist loaded and ready to go")
        f.close()

    def addcommand(self, data=None, channel=None):
        """Add or change command in optcoms for channel"""
        if data is None:
            data = self.message
        if channel is None:
            channel = self.match.group('chan')
            
        #Get the command to add
        data = data.split(" ",maxsplit=1)

        #Add the command to the channel command list
        if data[0] not in self.syscoms:
            try:
                self.optcoms[channel][data[0]] = data[1]
            except:
                print("Improper syntax, no command added")
        else:
            print("Command exists as a system command, ignored")

    def delcommand(self, data=None, channel=None):
        """Delete a command from optcoms for channel"""
        if data is None:
            data = self.message
        if channel is None:
            channel = self.match.group('chan')

        #Get the command to remove
        data = data.split(" ")[0]

        #Remove the command from the channel command list
        try:
            self.optcoms[channel].pop(data)
        except KeyError:
            print("Command not present")
        except IndexError:
            print("Somebody fucked the input")
    
    def commandlist(self, channel=None):
        """Prints a command list to the channel"""
        if channel is None:
            channel = self.match.group('chan')
        buf = "Current system commands are: "
        buf += ', '.join(str(command) for command in self.syscoms.keys())
        self.say(buf, channel)
        buf = "Current commands for this channel are: "
        if len(list(self.optcoms[channel].keys())):
            buf += ', '.join(str(command) for command in
                             self.optcoms[channel].keys())
            self.say(buf, channel)

    def commandhelp(self, data=None, channel=None):
        """Sends docstring for requested command"""
        if data is None:
            data = self.message
        if channel is None:
            channel = self.match.group('chan')

        #Make sure only checking for one command
        data = data.split(" ")[0]

        try:
            self.say(self.syscoms[data].__doc__, channel)
        except KeyError:
            self.say(self.commandhelp.__doc__, channel)

    

    def listen(self):
        """Respond to PING, call parse if channel message"""

        #Decode data on receive to work with strings
        data = bytes.decode(self.irc.recv(4096))

        #Respond to server PINGs to stay connected
        if data.startswith("PING"):
            self.send("PONG " + data.split(" ")[1])

        #If there's a PRIVMSG parse the data
        self.match = self.msplit.search(data)
        if self.match:
            self.parse()
        else:
            pass

    def parse(self, data=None):
        """Parse data for commands"""
        # TODO (3)
        # TODO (4)
        #Cut down on line length
        user = self.match.group('user')
        chan = self.match.group('chan')
        msg = self.match.group('msg')

        self.ircprint()

        # NOTES (1)
        if self.links.search(msg) and (user != self.config["nick"]):
            try:
                message = self.scanner.scan(self.links.search(msg).group())
            except RequestError as inst:
                print(type(inst))
                print(inst.args)
                print(inst) # TODO (7)
            except Exception as inst:
                print(type(inst))
                print(inst.args)
                print(inst) #TODO (7)
            else:
                for ln in message:
                    print(ln)
                    self.say(ln, chan)

        #Add the user to the userlist if they're not present already
        if user not in self.users:
            self.users[user] = {}
            print("User {} added to userlist".format(user))

        #Only check for commands if the message starts with an !
        if msg.startswith(self.config["prefix"]):
            
            #Snag the actual command to compare
            command = msg.split(" ",maxsplit=1)[0].lstrip(self.config["prefix"])

            #Attempt to set command args (msg), or give it a blank string
            try:
                self.message = msg.split(" ",maxsplit=1)[1]
            except:
                self.message = ""

            #Compare to system commands first, and then channel commands after
            if command in self.syscoms:
                self.syscoms[command]()
            elif command in self.optcoms[chan]:
                self.say(self.optcoms[chan][command], chan)

if __name__ == '__main__':
    shanghai = Bot("config.txt")
    shanghai.connect()
    shanghai.join(channel="##shanghaidoll")
    while True:
        try:
            shanghai.listen()
        except KeyboardInterrupt:
            shanghai.quit(True)
