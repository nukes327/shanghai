"""
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Failed to import BeautifulSoup, are you sure it's installed?")
    raise
try:
    from requests import requests
except ImportError:
    try:
        import requests
    except ImportError:
        print("Failed to import requests")
        raise

class LinkScanner:

    def __init__(self):
        self.message = []
        self.request = None

    def scan(self, link):
        try:
            self.message.append(self.linkscan(link))
        except:
            raise
        if ".pixiv." in link:
            try:
                self.message.append(self.pixiv(link))
            except:
                raise
        message = self.message
        self.message = []
        return message

    def linkscan(self, link):
        ""Handle a link""
        message = ""
        try: #Get the link
            self.request = requests.get(link, timeout=1, stream=True, 
                             headers={"Accept-Encoding": "deflate"}) 
        except requests.exceptions.SSLError: #SSL Failed, try again without
            self.request = requests.get(link, timeout=1, stream=True,
                             headers={"Accept-Encoding": "deflate"}, 
                             verify=False)
        except requests.exceptions.HTTPError:
            message = "Invalid HTTP response"
            raise
        except requests.exceptions.ReadTimeout:
            message = "Request timed out, working on a fix"
            raise
        except requests.exceptions.ConnectionError:
            message = "Connection error, is this a real site?"
            raise
        if self.request:
            if "html" in self.request.headers["content-type"]:
                message = "[title] "
                try:
                    message += BeautifulSoup(self.request.text,
                                             'html.parser').title.string.strip()
                    message = message.replace('\n', '')
                except AttributeError:
                    message = "No page title found"
            else:
                message = "[{}] - ".format(self.request.headers["content-type"])
                try:
                    message += self.sizeconvert(
                        int(self.request.headers["content-length"]))
                except KeyError:
                    message += "?B"
                except IndexError:
                    message += "What the fuck are you linking a file so big for"
            self.request.close()
        return message

    def sizeconvert(self, size=0):
        ""Convert a Byte size to something readable""
        size_name = ("B", "KB", "MB", "GB")
        i = 0
        while size >= 1024:
            size >>= 10
            i += 1
        try:
            return str(size) + size_name[i]
        except IndexError:
            raise #Raise IndexError if the file is too big

    def pixiv(self, link):
        tags = BeautifulSoup(self.request.text, 'html.parser') \
               .find(class_="tags-container")
        message = "[tags] "
        if tags:
            message += ', '.join(tag.string for tag
                                in tags.find_all(class_="text"))
            return message
        return "Tags not found, probably NSFW, working on a fix"
"""

"""
This script is dedicated to the memory of ZaSu Pitts and Clu Gulager.
It slices and dices the user's toes using special peripherals.
"""
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Failed to import BS4, make sure it's installed")
try:
    from requests import requests
except ImportError:
    try:
        import requests
    except ImportError:
        raise ImportError("Failed to import requests")
import re



class LinkScanError(Exception):
    """Base Error Class"""
    pass
    
class TitleError(LinkScanError):
    """Error in fetching title"""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)
                
class RequestError(LinkScanError):
    """Error in GET request"""
    def __init__(self, link, msg):
        self.link = link
        self.msg = msg
    def __str__(self):
        return " - ".join([repr(self.msg), repr(self.link)])


        
class LinkScanner:
    
    def __init__(self):
        self.message = []
        self.request = None
        self.sites = {"\.pixiv\." : self.pixiv}
        
    def scan(self, link):
        try:
            self.getrequest(link)
        except:
            raise
        if self.request:
            try:
                self.request.raise_for_status()
            except Exception as inst:
                self.message.append(inst)
            if "html" in self.request.headers["content-type"]:
                self.message.append(self.fetchtitle())
                if ".pixiv" in link:
                    self.message.append(self.pixiv())
            else:
                self.message.append(self.fetchsize())
        message = self.message
        self.message = []
        return message
        
    def getrequest(self, link):
        """Send GET request to given link"""
        try:
            self.request = requests.get(link, timeout=1, stream=True,
                                        headers={"Accept-Encoding": "deflate"})
        except requests.exceptions.SSLError:                                       #Probably should remove this, was only for warsh's shit :^)
            self.request = requests.get(link, timeout=1, stream=True,
                                        headers={"Accept-Encoding": "deflate"},
                                        verify=False)
        except requests.exceptions.HTTPError as inst:
            raise RequestError(link, inst)
        except requests.exceptions.ReadTimeout:
            raise RequestError(link, "Request timed out")
        except requests.exceptions.ConnectionError:
            raise RequestError(link, "Connection error, is this a real site?")

    def fetchtitle(self):
        """Get a title from html"""
        message = "[title] "
        try:
            message += BeautifulSoup(self.request.text,'html.parser').title.string.strip()
            message = message.replace('\n', '')
        except AttributeError:
            raise TitleError("No page title found")
        return message
    
    def fetchsize(self):
        """Get size of linked content"""
        message = "[{}] - ".format(self.request.headers["content-type"])
        try:
            message += self.sizeconvert(
                int(self.request.headers["content-length"]))
        except KeyError:
            message += "?B"
        except IndexError:
            message += "What the fuck are you linking a file so big for"
        return message
        

    # I removed the old size convert that truncated the decimal
    
    def sizeconvert(self, size=0):
        """Convert's a Byte size to something more readable"""
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size >= 1000:
            size /= 1000
            i+=1
        try:
            return str(round(size, 2)) + size_name[i]
        except IndexError:
            raise
        
    def pixiv(self):
        """Get tags off a pixiv link"""
        tags = BeautifulSoup(self.request.text, 'html.parser') \
               .find(class_="tags-container")
        message = "[tags] "
        if tags:
            message += ', '.join(tag.string for tag
                                in tags.find_all(class_="text"))
            return message
        return "Tags not found, probably NSFW, working on a fix"
        
