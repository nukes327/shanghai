# NOTES
# (1) While this WILL connect to non-twitch IRC servers currently, don't do it
#  -- As is it'll pitch a fit if the received data isn't formatted correctly
#
# (2) Very important information, but this is subject to change:
#  -- Sending CAP REQ :twitch.tv/tags to the twitch IRC server toggles
#  -- IRCv3 tags being sent from the server. The format is as follows:
#  -- @color=#0000FF;emotes=;subscriber=0;turbo=0;user_type=mod(...)
#  -- (...) :nukes327!nukes327@nukes327.tmi.twitch.tv PRIVMSG #nukes327 :Msg
#
#  -- color is the user's nickname color in twitch webirc
#  -- emotes contains the emote ID, and the location of the emote within the msg
#  --   this is empty if there are no emotes in the message
#  -- subscriber is 0 unless the user is subscribed to the channel
#  -- turbo is 0 unless the user is paying for Twitch turbo
#  -- user_type can be staff, admin, global_mod, or mod
#  --   users are blank and broadcaster is blank or mod if they modded themself
#---------
# TODO
# (1) Fix the config crashing if it receives invalid JSON
# (2) Comment the shit out of the code
# (3) Check for chat moderator status to limit system commands
# (4) Make parse case-insensitive
# (5) Clean up error checking rather than having except on anything
# (6) Ask user in the future if they want to generate a new oauth key
###############################################################################
import socket
import json
import time

class Bot:

    def __init__(self, config="config.txt"):
        try:
            f = open(config)
        except FileNotFoundError:
            #File wasn't found, initialize all values
            print("Error, config not found")
            self.config["server"] = input("Server: ")
            self.config["port"] = int(input("Port: "))
            self.config["nick"] = input("Nick: ")
            self.config["key"] = input("Twitch oauth key: ") # TODO (6)

            #Create file with given name, dump JSON to file
            f = open(config, "w+")
            json.dump(self.config, f, indent=4)
            f.close()
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
                        "np" : self.nowplaying,
                        "songinfo" : self.songinfo,
                        "sessioninfo" : self.sessioninfo}

        #Contains all data on any message received to pass between methods
        self.params = {"chan" : "",
                       "msg"  : "",
                       "user" : "",
                       "color" : "",
                       "mod" : False}

        self.loadlist()

    def send(self, cmd):
        """Send encoded message to irc socket"""
        self.irc.send(str.encode("{}\r\n".format(cmd)))

    def connect(self):
        """Connect to twitch irc server"""
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((self.config["server"], self.config["port"]))
        self.send("PASS {}".format(self.config["key"]))
        self.send("NICK {}".format(self.config["nick"]))
        self.send("CAP REQ :twitch.tv/tags") # NOTES (2)

    def join(self, channel=None):
        """Join and load commands for given channel"""
        if channel is None:
            channel = "#{}".format(self.params["user"])
        self.send("JOIN {}".format(channel))
        print("Connected to channel {}".format(channel))
        print("Loading command list for {}".format(channel))
        try:
            f = open(channel)
        except FileNotFoundError:
            f = open(channel, "w+")
            print("File not found, "
                  "creating a new command list for {}".format(channel))
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
            msg = self.params["msg"]
        if user is None:
            user = self.params["user"]
        msgtime = time.localtime()
        print("[{0[3]:02d}:{0[4]:02d}:{0[5]:02d}] {1}: {2}".format(msgtime, user, msg))

    def say(self, msg=None, channel=None):
        """Send message to channel"""
        if msg is None:
            msg = self.params["msg"]
        if channel is None:
            channel = self.params["chan"]
        self.send("PRIVMSG {} :{}".format(channel, msg))
        self.ircprint(msg, "shanghai_doll")

    def part(self, channel=None):
        """Leave channel and save specific commands"""
        if channel is None:
            channel = self.params["chan"]
        self.send("PART {}".format(channel))
        print("Writing command list for {} to file...".format(channel))
        f = open(channel, "w")
        json.dump(self.optcoms[channel], f, indent=4)
        f.close()

    def quit(self):
        """Save all open command sets, quit server, and exit program"""
        for chan in self.optcoms:
            self.part(chan)

        print("Writing userlist to file...")
        f = open("userlist.txt", "w")
        json.dump(self.users, f, indent=4)
        f.close()
        self.send("QUIT")

        exit()

    def loadlist(self):
        """Load global user list"""
        print("Loading user list")
        try:
            f = open("userlist.txt")
        except FileNotFoundError:
            f = open("userlist.txt", "w+")
            print("File not found, creating a new userlist.txt")
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
            data = self.params["msg"]
        if channel is None:
            channel = self.params["chan"]
        data = data.split(" ",maxsplit=1)
        try:
            self.optcoms[channel][data[0]] = data[1]
        except:
            print("Improper syntax, no command added")

    def delcommand(self, data=None, channel=None):
        """Delete a command from optcoms for channel"""
        if data is None:
            data = self.params["msg"]
        if channel is None:
            channel = self.params["chan"]
        data = data.split(" ")[0]
        try:
            self.optcoms[channel].pop(data)
        except KeyError:
            print("Command not present")
        except IndexError:
            print("Somebody fucked the input")
    
    def commandlist(self, channel=None):
        """Pastebin a command list for channel"""
        pass

    def nowplaying(self):
        """Send now playing info for osu"""
        pass

    def songinfo(self):
        """Send song info for osu"""
        pass

    def sessioninfo(self):
        """Send current stream session info"""
        pass

    def listen(self):
        """Respond to PING, call parse if channel message"""
        data = bytes.decode(self.irc.recv(4096))
        if data.startswith("PING"):
            self.send("PONG " + data.split(" ")[1])
        if ("PRIVMSG ") in data and not data.startswith(":jtv"):
            self.parse(data)
        else:
            pass

    def parse(self, data):
        """Parse data for commands"""
        # TODO (5)
        data = data.rstrip("\r\n")
        data = data.split(" :", maxsplit=2)
        data[0] = data[0].split(";")
        data[1] = data[1].split(" ")
        self.params["msg"] = data[2]
        self.params["user"] = data[1][0].split("!")[0]
        self.params["chan"] = data[1][2]
        self.params["color"] = data[0][0].split("=")[1]
        # TODO (3)

        self.ircprint()
        #msgtime = time.localtime()
        #print("[{0[3]:02d}:{0[4]:02d}:{0[5]:02d}] {1}: {2}".format(msgtime,
        #                                                           self.params["user"],
        #                                                           self.params["msg"]))

        if self.params["user"] not in self.users:
            self.users[self.params["user"]] = {}
            print("User %s added to userlist" % (self.params["user"]))
        if self.params["msg"].startswith("!"):
            command = self.params["msg"].split(" ",maxsplit=1)[0].lstrip("!")
            try:
                self.params["msg"] = self.params["msg"].split(" ",maxsplit=1)[1]
            except:
                self.params["msg"] = ""
            if command in self.syscoms:
                self.syscoms[command]()
            elif command in self.optcoms[self.params["chan"]]:
                self.say(self.optcoms[self.params["chan"]][command], self.params["chan"])

shanghai = Bot()
shanghai.connect()
shanghai.join("#nukes327")
while True:
    try:
        shanghai.listen()
    except KeyboardInterrupt:
        shanghai.quit()
