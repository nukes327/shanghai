import socket
import json

class Bot:
    def __init__(self):
        f = open("config.txt")
        self.serv = f.readline().rstrip('\n')
        self.port = int(f.readline().rstrip('\n'))
        self.nick = f.readline().rstrip('\n')
        self.key  = f.readline().rstrip('\n')
        self.users = {}
        self.chanlist = []
        f.close()
    def send(self, cmd):
        self.irc.send(str.encode(cmd + "\r\n"))

    def connect(self):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((self.serv, self.port))
        self.send("PASS " + self.key)
        self.send("NICK " + self.nick)
        self.send("CAP REQ :twitch.tv/tags")

    def join(self, channel):
        self.send("JOIN " + channel)
        print("Connected to channel " + channel)
        self.loadlist(channel)

    def say(self, msg, channel):
        self.send("PRIVMSG " + channel + " :" + msg)

    def part(self, channel):
        self.send("PART " + channel)
        print("Writing userlist to file...")
        f = open(channel, "w")
        json.dump(self.users, f)
        f.close()
        self.send("QUIT")
        exit()

    def loadlist(self, channel):
        print("Loading user list for " + channel)
        try:
            f = open(channel, "r")
        except:
            f = open(channel, "a+")
            f.seek(0)
            print("File not found, creating...")
        try:
            self.users = json.load(f)
        except:
            print("No user list found, initializing...")
        else:
            print("User list loaded, ready to go")
        f.close()

    def listen(self):
        data = bytes.decode(self.irc.recv(4096))
        if data.startswith("PING"):
            self.send("PONG " + data.split(" ")[1])
        if ("PRIVMSG ") in data and not data.startswith(":jtv"):
            self.parse(data)
        else:
            pass

    def parse(self, data):
        data = data.split(" :", maxsplit=2)
        print (data)
        data[0] = data[0].split(";")
        data[1] = data[1].split(" ")
        msg = data[2]
        user = data[1][0].split("!")[0]
        channel = data[1][2]
        color = data[0][0].split("=")[1]
        if user not in self.users:
            self.users[user] = {}
            print("User " + user + " added to userlist")
        if msg.startswith("!"):
            msg = msg.lstrip("!")
            if msg.startswith("part"):
                self.part(channel)
            if msg.startswith("echo"):
                self.say(msg.split(" ",maxsplit=1)[1], channel)
        elif msg.lower().startswith("shanghai"):
            msg = msg.lower().split("shanghai ",maxsplit=1)
            if msg[1].startswith("purge"):
                self.say(".timeout " + user + " 1", channel)


shanghai = Bot()
shanghai.connect()
shanghai.join("#nukes327")
while True:
    shanghai.listen()
