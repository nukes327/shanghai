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
        self.commands = {}
        self.loadlist()

    def send(self, cmd):
        """Send encoded message to irc socket"""
        self.irc.send(str.encode(cmd + "\r\n"))

    def connect(self):
        """Connect to twitch irc server"""
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((self.serv, self.port))
        self.send("PASS %s" % (self.key))
        self.send("NICK %s" % (self.nick))
        self.send("CAP REQ :twitch.tv/tags")

    def join(self, channel):
        """Join and load commands for given channel"""
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
            self.commands[channel] = json.load(f)
        except:
            print("No command list found, initializing")
            self.commands[channel] = {}
        else:
            print("Command list loaded, ready to go")
        f.close()


    def say(self, msg, channel):
        """Send message to channel"""
        self.send("PRIVMSG %s : %s" % (channel, msg))

    def part(self, channel):
        """Leave channel and save specific commands"""
        self.send("PART %s" % (channel))
        print("Writing command list for %s to file..." % (channel))
        f = open(channel, "w")
        json.dump(self.commands[channel], f)
        f.close()

    def quit(self):
        """Save all open command sets, quit server, and exit program"""
        for chan in self.commands:
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

    def addcommand(self, data, channel):
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
        data = data.rstrip("\r\n")
        data = data.split(" :", maxsplit=2)
        data[0] = data[0].split(";")
        data[1] = data[1].split(" ")
        msg = data[2]
        user = data[1][0].split("!")[0]
        channel = data[1][2]
        color = data[0][0].split("=")[1]

        msgtime = time.localtime()
        print("[%02i:%02i:%02i] %s: %s" % (msgtime[3], msgtime[4], msgtime[5], user, msg))

        if user not in self.users:
            self.users[user] = {}
            print("User %s added to userlist" % (user))
        if msg.startswith("!"):
            msg = msg.lstrip("!")
            if msg.startswith("add"):
                self.addcommand(msg.split(" ",maxsplit=1[1]), channel)
            if msg.startswith("part"):
                self.part(channel)
            if msg.startswith("echo"):
                self.say(msg.split(" ",maxsplit=1)[1], channel)
            if msg.startswith("quit"):
                self.quit()

shanghai = Bot()
shanghai.connect()
shanghai.join("#nukes327")
while True:
    shanghai.listen()
