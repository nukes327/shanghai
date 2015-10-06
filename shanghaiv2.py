# NOTES
# (1) Very important information, but this is subject to change:
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
# (2) Regex works barely. Still catches too much bad data, looking in to fixes
# (3) Check for chat moderator status to limit system commands
# (4) Make parse case-insensitive
# (5) Clean up error checking so it checks for specific errors
# (6) Ask user in the future if they want to generate a new oauth key
# (7) Fix link scan. Needs moar error checking
#---------
# Recent Changes:
#   The regex I'm using now means that it won't fuck up if it receives
#   a PRIVMSG that it doesn't like the format of
#   This means the bot can now connect to any server it gets the info for
################################################################################

import socket
import json
import time
import re
import codecs
import ssl
try:
    from requests import requests
except ImportError:
    try:
        import requests
    except ImportError:
        print("Failed to import requests")
        exit()

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
            self.config["pass"] = input("Server pass: ") # TODO (6)
            self.config["ssl"] = bool(input("SSL? True or False: "))

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
                        "sessioninfo" : self.sessioninfo,
                        "help" : self.commandhelp}

        #Put the channel message regex here
        # TODO (2)
        self.msplit = re.compile(r"""
         (?P<tags>               #Put all the twitch IRCv3 tags in to a group
         @color=
         (?P<color>[^;]*);       #Set Color group to color value
         display-name=
         (?P<display>[^;]*);     #Set Display group to display name
         emotes=
         (?P<emotes>[^;]*);      #Set Emotes group to emotes value
         subscriber=
         (?P<sub>[^;]*);         #Set Sub group to subscriber value
         turbo=
         (?P<turbo>[^;]*);       #Set Turbo group to turbo value
         user-type=
         (?P<wtftwitch>[^;]*);   #Set WTFTwitch group to SECOND USER VALUE
         user_type=
         (?P<type>\S*?)          #Set Type group to user_type value
         )?                      #Make Twitch IRCv3 tags optional
         \s*?                    #Lose any extra whitespace
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

        #Regex to find title in page text
        self.pagetitle = re.compile(r"\<title\b[^>]*\>\s*(?P<title>[\s\S]*?)\</title\>", re.MULTILINE)

        #A match object used for regex comparison to decide what to do with data
        self.match = None

        #Message used as default for some method calls
        self.message = ""
        
        self.loadlist()

    def send(self, cmd):
        """Send encoded message to irc socket"""
        #Encode to bytes on send
        self.irc.send(str.encode("{}\r\n".format(cmd)))

    def connect(self):
        """Connect to twitch irc server"""
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
        self.send("CAP REQ :twitch.tv/tags") # NOTES (1)

    def join(self, channel=None):
        """Join and load commands for given channel"""

        #If a user sends !join, join their channel
        if channel is None:
            channel = self.message
            #channel = "#{}".format(self.match.group('user'))


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

    def say(self, msg=None, channel=None):
        """Send message to channel"""
        if msg is None:
            msg = self.message
        if channel is None:
            channel = self.match.group('chan')
        self.send("PRIVMSG {} :{}".format(channel, msg))
        self.ircprint(msg, "shanghai_doll")

    def part(self, channel=None):
        """Leave channel and save specific commands"""
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

    def quit(self):
        """Save all open command sets, quit server, and exit program"""
        #You can't iterate over the dict itself because part pops the values
        #And you can't iterate the dict's keys because that returns another damned dict
        if (self.match.group('user') == 'nukes327'):
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
        for command in self.syscoms.keys():
            buf += command + ", "
        self.say(buf, channel)
        buf = "Current commands for this channel are: "
        for command in self.optcoms[channel].keys():
            buf += command + ", "
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
            self.say("Command not present", channel)

    def nowplaying(self):
        """Send now playing info for osu"""
        #try:
        #    f = codecs.open("C:\\Program Files (x86)\\OBS\\nowplaying.txt", encoding="utf-8")
        #except FileNotFoundError:
        #    print("File not found.")
        #except:
        #    print("Something went wrong")
        #else:
        #    self.say(f.readline(), self.match.group('chan'))
        pass

    def songinfo(self):
        """Send song info for osu"""
        pass

    def sessioninfo(self):
        """Send current stream session info"""
        pass

    def sizeconvert(self, size=0):
        size_name = ("B", "KB", "MB", "GB")
        i = 0
        while size >= 1024:
            size >>= 10
            i += 1
        try:
            return str(size) + size_name[i]
        except IndexError:
            return "What the fuck are you linking a file so big for"
        

    def linkscan(self, link):
        """Handle a link"""
        try:
            r = requests.get(link, timeout=1, stream=True,
                             headers={"Accept-Encoding": "deflate"})
        except requests.exceptions.SSLError:
            r = requests.get(link, timeout=1, stream=True,
                             headers={"Accept-Encoding": "deflate"},
                             verify=False)
        except requests.exceptions.HTTPError:
            print("Invalid HTTP response")
        except requests.exceptions.ReadTimeout:
            self.say("Request timed out, working on a fix", self.match.group('chan'))
            return
        except requests.exceptions.ConnectionError:
            print("Connection error")
        if r:
            if "html" in r.headers["content-type"]:
                msg = "[title] "
                try:
                    msg += self.pagetitle.search(r.text).group('title')
                except AttributeError:
                    self.say("No page title found", self.match.group('chan'))
                else:
                    self.say(msg, self.match.group('chan'))
            else:
                msg = "[{}] - ".format(r.headers["content-type"])
                try:
                    msg += self.sizeconvert(int(r.headers["content-length"]))
                except KeyError:
                    print("No content-length present")
                
                self.say(msg, self.match.group('chan'))
            r.close()

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
        # TODO (4)
        # TODO (3)
        #Cut down on line length
        user = self.match.group('user')
        chan = self.match.group('chan')
        msg = self.match.group('msg')

        self.ircprint()

        # TODO (7)
        if self.links.search(msg) and (user != "shanghai_doll"):
            print(self.links.search(msg).group())
            self.linkscan(self.links.search(msg).group())

        #Add the user to the userlist if they're not present already
        if user not in self.users:
            self.users[user] = {}
            print("User {} added to userlist".format(user))

        #Only check for commands if the message starts with an !
        if msg.startswith("!"):
            
            #Snag the actual command to compare
            command = msg.split(" ",maxsplit=1)[0].lstrip("!")

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
