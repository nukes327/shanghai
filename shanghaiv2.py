import socket

class Bot:
    def __init__(self):
        f = open("config.txt")
        self.serv = str.encode(f.readline().rstrip('\n'))
        self.port = int(f.readline().rstrip('\n'))
        self.nick = str.encode(f.readline().rstrip('\n'))
        self.key  = str.encode(f.readline().rstrip('\n'))
        self.users = {}
        f.close()

    def connect(self):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((self.serv, self.port))
        self.irc.send(b"PASS " + self.key + b"\r\n")
        self.irc.send(b"NICK " + self.nick + b"\r\n")
        self.irc.send(b"CAP REQ :twitch.tv/tags\r\n")

    def join(self, channel):
        self.irc.send(b"JOIN " + channel + b"\r\n")
        self.say(b"Connected to channel", channel)

    def say(self, msg, channel):
        self.irc.send(b"PRIVMSG " + channel + b" :" + msg + b"\r\n")

    def quit(self):
        self.irc.send(b"QUIT\r\n")
        exit()

    def loadlist(self, userlist):
        pass

    def listen(self):
        data = self.irc.recv(4096)
        if data.startswith(b"PING"):
            self.irc.send(b"PONG " + data.split(b" ")[1])
        if (b"PRIVMSG ") in data and not data.startswith(b":jtv"):
            self.parse(data)
        else:
            pass

    def parse(self, data):
        data = data.split(b" :", maxsplit=2)
        print (data)
        data[0] = data[0].split(b";")
        data[1] = data[1].split(b" ")
        msg = data[2]
        user = data[1][0].split(b"!")[0]
        channel = data[1][2]
        color = data[0][0].split(b"=")[1]
        if msg.startswith(b"!"):
            msg = msg.lstrip(b"!")
            if msg.startswith(b"quit"):
                self.quit()
            if msg.startswith(b"echo"):
                self.say(msg.split(b" ",maxsplit=1)[1], channel)
        elif msg.lower().startswith(b"shanghai"):
            msg = msg.lower().split(b"shanghai ",maxsplit=1)
            if msg[1].startswith(b"purge"):
                self.say(b".timeout " + user + b" 1", channel)


shanghai = Bot()
shanghai.connect()
shanghai.join(b"#nukes327")
while True:
    shanghai.listen()
