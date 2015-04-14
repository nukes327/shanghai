# NOTES
###############################################################################
import socket
import json
import time

class Bot:

    def __init__(self, config="config.txt"):
        try:
            f = open(config)
        except:
            print("Error, config not found")
            self.serv = input("Server: ")
            self.port = int(input("Port: "))
            self.nick = input("Nick: ")
            self.key = input("Oauth key: ")
            f = open(config, "w+")
            f.write(self.serv + "\n")
            f.write(str(self.port) + "\n")
            f.write(self.nick + "\n")
            f.write(self.key + "\n")
            f.close()
        else:
            self.serv = f.readline().rstrip('\n')
            self.port = int(f.readline().rstrip('\n'))
            self.nick = f.readline().rstrip('\n')
            self.key  = f.readline().rstrip('\n')
            f.close()
        self.users = {}
        self.optcoms = {}
        self.syscoms = {"quit" : self.quit,
                        "part" : self.part,
                        "join" : self.join,
                        "echo" : self.say,
                        "command" : self.addcommand}
        self.params = {"chan" : "",
                       "msg"  : "",
                       "user" : "",
                       "color" : "",
                       "mod" : False}
        self.loadlist()

    def send(self, cmd):
        """Send encoded message to irc socket"""
        self.irc.send(str.encode("%s\r\n" % cmd))

    def connect(self):
        """Connect to twitch irc server"""
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((self.serv, self.port))
        self.send("PASS %s" % (self.key))
        self.send("NICK %s" % (self.nick))
        self.send("CAP REQ :twitch.tv/tags")

    def join(self, channel=None):
        """Join and load commands for given channel"""
        if channel is None:
            channel = "#%s" % self.params["user"]
        self.send("JOIN %s" % (channel))
        print("Connected to channel %s" % (channel))
        print("Loading command list for %s" % (channel))
        try:
            f = open(channel)
        except:
            f = open(channel, "w+")
            print("File not found, "
                  "creating a new command list for %s" % (channel))
        try:
            self.optcoms[channel] = json.load(f)
        except:
            print("No command list found, initializing")
            self.optcoms[channel] = {}
        else:
            print("Command list loaded, ready to go")
        f.close()


    def say(self, msg=None, channel=None):
        """Send message to channel"""
        if msg is None:
            msg = self.params["msg"]
        if channel is None:
            channel = self.params["chan"]
        self.send("PRIVMSG %s :%s" % (channel, msg))

    def part(self, channel=None):
        """Leave channel and save specific commands"""
        if channel is None:
            channel = self.params["chan"]
        self.send("PART %s" % (channel))
        print("Writing command list for %s to file..." % (channel))
        f = open(channel, "w")
        json.dump(self.optcoms[channel], f)
        f.close()

    def quit(self):
        """Save all open command sets, quit server, and exit program"""
        for chan in self.optcoms:
            self.part(chan)

        print("Writing userlist to file...")
        f = open("userlist.txt", "w")
        json.dump(self.users, f)
        f.close()
        self.send("QUIT")

        exit()

    def loadlist(self):
        """Loads global user list"""
        print("Loading user list")
        try:
            f = open("userlist.txt")
        except:
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
        if data is None:
            data = self.params["msg"]
        if channel is None:
            channel = self.params["chan"]
        data = data.split(" ",maxsplit=1)
        self.optcoms[channel][data[0]] = data[1]

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
        data = data.rstrip("\r\n")
        data = data.split(" :", maxsplit=2)
        data[0] = data[0].split(";")
        data[1] = data[1].split(" ")
        self.params["msg"] = data[2]
        self.params["user"] = data[1][0].split("!")[0]
        self.params["chan"] = data[1][2]
        self.params["color"] = data[0][0].split("=")[1]

        msgtime = time.localtime()
        print("[%02i:%02i:%02i] %s: %s" % (msgtime[3], msgtime[4], msgtime[5],
                                           self.params["user"], self.params["msg"]))

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
    shanghai.listen()
