# NOTES
# (1) Link scanning regex doesn't pick up links without http(s)
#     prepended, I'm not sure I care to fix that
# ---------
# TODO
# (1) https://docs.python.org/3.5/library/asyncio.html ASYNCIO
# (3) Check for chat moderator status to limit system commands
# (4) Make parse case-insensitive
# (5) Clean up error checking so it checks for specific errors
# (7) LOGGING EVERYTHING
# (8) Time ==> Datetime
# (9) Python 3.6 string format changes
# ---------
# Recent Changes:
#   Added some comments for python 3.6 format strings
###############################################################################


import configparser
import getpass
import json
import logging
import re
import socket
import ssl
import time
import fuckit

# from linkscanning import *
from linkscanning import LinkScanner


class ShanghaiError(Exception):
    """Base Error Class"""
    pass


class ClearanceError(ShanghaiError):
    """Somebody tried to run something above their clearance"""
    def __init__(self, *, user: str, func: str):
        self.user = user
        self.func = func

    def __str__(self):
        return repr(self.user + " - " + self.func)


class Bot:

    Channel = str
    Command = str
    Filename = str
    Flag = bool
    Message = str
    Regex = str
    Time = time.struct_time
    User = str

    def __init__(self,
                 config: Filename = "shanghai.ini",
                 chancoms: Filename = "commands.ini"):
        self.config = configparser.ConfigParser()
        try:
            with open(config) as f: self.config.read_file(f)
        except FileNotFoundError:
            default = self.config["DEFAULT"]
            default["owner"] = input("Default bot owner: ")
            default["nick"] = input("Default bot nick: ")
            default["password"] = getpass.getpass("Default server password: ")
            default["prefix"] = input("Default command prefix: ")
            default["server"] = input("IRC server: ")
            default["port"] = input("Server port: ")
            default["ssl"] = input("SSL? Yes or No: ")
            with open(config, 'w') as conffile:
                self.config.write(conffile)
        self.users = {}

        # Loaded later with any channel-specific commands
        self.chancoms = configparser.ConfigParser()
        try:
            with open(chancoms) as f:
                self.chancoms.read_file(f)
        except FileNotFoundError:
            print("Channel commands file not found, will initialize as needed")

        # Save the channel command filename for later use
        self.chanfile = chancoms

        # Used to call methods from irc messages
        self.syscoms = {"quit":       self.quit,
                        "part":       self.part,
                        "join":       self.join,
                        "echo":       self.echo,
                        "addcommand": self.addcommand,
                        "delcommand": self.delcommand,
                        "commands":   self.commandlist,
                        "help":       self.commandhelp,
                        "grep":       self.greplogs}

        # Put the channel message regex here
        self.msplit = re.compile(r"""
         :                       # Start of standard IRC message
         (?P<user>[^!]*)         # Get the user's nick
         !\S*?\s*?               # Lose extra, and trailing whitespace
         PRIVMSG                 # We only want to match a PRIVMSG
         \s*?                    # Lose whitespace again
         (?P<chan>\S*)           # Grab the channel the message was to
         \s*?                    # Lose more whitespace
         :(?P<msg>[^\r\n]*)      # Message is whatever is left
        """, re.VERBOSE | re.IGNORECASE)  # Ignore the case just in case

        # Regex to scan a message for links
        self.links = re.compile(r"\bhttps?://[^. ]+\.[^. \t\n\r\f\v][^ \n\r]+")

        # A match object used for regex comparison to decide what to do with data
        self.match = None

        # Message used as default for some method calls
        self.message = ""

        self.irc = None

        self.loadlist()

        self.logger = logging.getLogger('shanghai')
        self.scanner = LinkScanner(self.logger)

# Core functionality

    def send(self,
             cmd: Message):
        """Send encoded message to irc socket"""
        # Encode to bytes on send
        # self.irc.send(str.encode("{}\r\n".format(cmd)))
        self.irc.send(str.encode(f"{cmd}\r\n"))

    def connect(self):
        """Connect to given irc server"""
        default = self.config["DEFAULT"]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((default['server'], int(default['port'])))
        s.settimeout(0.5)
        if default.getboolean('ssl'):
            context = ssl.create_default_context()
            self.irc = context.wrap_socket(s, server_hostname=default['server'])
        else:
            self.irc = s
        if default["password"]:
            # self.send("PASS {}".format(default['password']))
            self.send(f"PASS {default['password']}")
        # self.send("NICK {}".format(default['nick']))
        self.send(f"NICK {default['nick']}")
        self.send("USER {0} {0} {0} :{0}".format(default['nick']))

    def join(self,
             force: Flag = False,
             channel: Channel = None):
        """Join and load commands for given channel.
        Example syntax: ,join <channel>
        """
        if channel is None:
            channel = self.message

        # self.send("JOIN {}".format(channel))
        self.send(f"JOIN {channel}")
        # print("Connected to channel {}".format(channel))
        print(f"Connected to channel {channel}")

        # Verify a section exists for the channel, and create it if not
        # print("Verifying command list for {}".format(channel))
        print(f"Verifying command list for {channel}")
        try:
            self.chancoms.add_section(channel)
        except configparser.DuplicateSectionError:
            print("Channel entry exists...")
        else:
            print("Created new entry for channel...")
        finally:
            # print("Ready to go for {}".format(channel))
            print(f"Ready to go for {channel}")

    def say(self,
            msg: Message = None,
            channel: Channel = None):
        """Send message to channel"""
        if msg is None:
            msg = self.message
        if channel is None:
            channel = self.match.group('chan')
        # self.send("PRIVMSG {} :{}".format(channel, msg))
        self.send(f"PRIVMSG {channel} :{msg}")
        self.ircprint(msg, "shanghai_doll", channel)

    def part(self,
             force: Flag = False,
             channel: Channel = None):
        """Leave the current channel.
        Example syntax: ,part
        """
        if not force and self.match.group('user') != self.config["DEFAULT"]["owner"]:
            raise ClearanceError(user=self.match.group('user'),
                                 func='part')
        if channel is None:
            channel = self.match.group('chan')
        # self.send("PART {}".format(channel))
        self.send(f"PART {channel}")

    def quit(self,
             force: Flag = False):
        """Write channel commands file, quit server, and exit program.
        Example syntax: ,quit
        """
        if force or (self.match.group('user') == self.config["DEFAULT"]["owner"]):
            print("Writing userlist to file...")
            f = open("userlist.txt", "w")
            json.dump(self.users, f, indent=4)
            f.close()
            self.send("QUIT")
            self.irc.shutdown(socket.SHUT_RDWR)
            self.irc.close()
            with open(self.chanfile, 'w') as chanfile:
                self.chancoms.write(chanfile)

            exit()
        else:
            self.say("Nope", self.match.group('chan'))

    def loadlist(self):
        """Load global user list"""
        print("Loading user list")

        # Opens the global userlist, or creates a new one if not found
        try:
            f = open("userlist.txt")
        except FileNotFoundError:
            f = open("userlist.txt", "w+")
            print("File not found, creating a new userlist.txt")

        # Loads the userlist from the file
        try:
            self.users = json.load(f)
        except:
            print("No userlist found in file, initializing")
        else:
            print("Userlist loaded and ready to go")
        f.close()

    def listen(self):
        """Respond to PING, call parse if channel message"""

        # Decode data on receive to work with strings
        try:
            data = self.irc.recv(4096)
        except socket.timeout:
            return
        if not data:
            self.reconnect()
        else:
            data = bytes.decode(data, encoding="utf-8")

        # Respond to server PINGs to stay connected
        if data.startswith("PING"):
            pong = data.split(' ')[1]
            # self.send("PONG {}".format(pong))
            self.send(f"PONG {pong}")

        # If there's a PRIVMSG parse the data
        self.match = self.msplit.search(data)
        if self.match:
            self.parse()
        else:
            pass

    def reconnect(self):
        """Reconnect to server on connection loss"""
        print("Connection lost, trying to reconnect now")
        self.irc.shutdown(socket.SHUT_RDWR)
        self.irc.close()
        self.connect()

    def parse(self):
        """Parse data for commands"""
        # TODO (3)
        # TODO (4)
        # Cut down on line length
        user = self.match.group('user')
        chan = self.match.group('chan')
        msg = self.match.group('msg')

        self.ircprint()

        # NOTES (1)
        if self.links.search(msg) and (user != self.config["DEFAULT"]["nick"]):
            try:
                message = self.scanner.scan(self.links.search(msg).group())
            except RequestError as inst:
                print(type(inst))
                print(inst.args)
                print(inst)  # TODO (7)
            except Exception as inst:
                print(type(inst))
                print(inst.args)
                print(inst)  # TODO (7)
            else:
                for line in message:
                    print(line)
                    self.say(line, chan)

        # Add the user to the userlist if they're not present already
        if user not in self.users:
            self.users[user] = {}
            # print("User {} added to userlist".format(user))
            print(f"User {user} added to userlist")

        # Only check for commands if the message starts with an !
        if msg.startswith(self.config["DEFAULT"]["prefix"]):

            # Snag the actual command to compare
            command = msg.split(" ", maxsplit=1)[0]
            command = command.lstrip(self.config["DEFAULT"]["prefix"])

            # Attempt to set command args (msg), or give it a blank string
            try:
                self.message = msg.split(" ", maxsplit=1)[1]
            except:
                self.message = ""

            # Compare to system commands first, and then channel commands after
            if command in self.syscoms:
                self.syscoms[command]()
            elif command in self.chancoms[chan]:
                self.say(self.chancoms[chan][command], chan)


# Extra functionality

    def ircprint(self,
                 msg: Message = None,
                 user: User = None,
                 chan: Channel = None,
                 msgtime: Time = None):
        """Print message readably to terminal with timestamp and channel"""
        # TODO: Fix unicode encode error
        if msg is None:
            msg = self.match.group('msg')
        if user is None:
            user = self.match.group('user')
        if chan is None:
            chan = self.match.group('chan')
        if msgtime is None:
            msgtime = time.localtime()
        with fuckit:
            print("[{3}/{0[3]:02d}:{0[4]:02d}:{0[5]:02d}] {1}: {2}".format(msgtime,
                                                                           user,
                                                                           msg,
                                                                           chan))

    def echo(self,
             message: Message = None,
             channel: Channel = None):
        """Echos a message to the channel.
        Example syntax: ,echo <message>
        """
        if message is None:
            message = self.message
        if channel is None:
            channel = self.match.group('chan')
        self.say(message, channel)

    def greplogs(self,
                 pattern: Regex = None,
                 channel: Channel = None):
        """Checks logs for specified pattern (NONFUNCTIONAL)"""
        if pattern is None:
            pattern = self.message
        if channel is None:
            channel = self.match.group('chan')
        # pseudocode:
        # result = []
        # for filename in os get log files:
        #     # Make sure to read the oldest logs first,
        #     with open(filename) as f:
        #         for line in re.findall(re.compile(pattern, re.MULTILINE),
        #                                file.read())
        #             result.append(line)
        # send( result[-5:] )   <-- want to return the 5 most recent matches

    def addcommand(self,
                   command: Command = None,
                   channel: Channel = None):
        """Add or change channel-specific command.
        Example syntax: ,addcommand <command>
        """
        if command is None:
            command = self.message
        if channel is None:
            channel = self.match.group('chan')

        # Get the command to add
        data = command.split(" ", maxsplit=1)

        # Add the command to the channel command list
        if data[0] not in self.syscoms:
            try:
                self.chancoms[channel][data[0]] = data[1]
            except:
                print("Improper syntax, no command added")
        else:
            print("Command exists as a system command, ignored")

    def delcommand(self,
                   command: Command = None,
                   channel: Channel = None):
        """Delete a channel-specific command.
        Example syntax: ,delcommand <command>
        """
        if command is None:
            command = self.message
        if channel is None:
            channel = self.match.group('chan')

        # Get the command to remove
        data = command.split(" ")[0]

        # Remove the command from the channel command list
        try:
            if self.chancoms.remove_option(channel, data):
                print("Command removed")
            else:
                print("Command not present")
        except configparser.NoSectionError:
            print("Dude wut, this should never be raised")

    def commandlist(self,
                    channel: Channel = None):
        """Prints a command list to the channel.
        Example syntax: ,commands
        """
        if channel is None:
            channel = self.match.group('chan')
        buf = "Current system commands are: "
        buf += ', '.join(str(command) for command in self.syscoms.keys())
        self.say(buf, channel)
        buf = "Current commands for this channel are: "
        if self.chancoms.options(channel):
            buf += ', '.join(str(command) for command in
                             self.chancoms.options(channel))
            self.say(buf, channel)

    def commandhelp(self,
                    command: Command = None,
                    channel: Channel = None):
        """Provides usage help for a command.
        Example syntax: ,help <command>
        """
        if command is None:
            command = self.message
        if channel is None:
            channel = self.match.group('chan')

        # Make sure only checking for one command
        data = command.split(" ")[0]

        try:
            self.say(self.syscoms[data].__doc__, channel)
        except KeyError:
            self.commandlist(channel)

if __name__ == '__main__':
    shanghai = Bot()
    shanghai.connect()
    while True:
        try:
            shanghai.listen()
        except KeyboardInterrupt:
            shanghai.quit(True)
