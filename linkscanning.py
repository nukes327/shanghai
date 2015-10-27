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
                raise RequestError(link, inst)
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
        except requests.exceptions.SSLError:
            raise RequestError(link, "SSL Error")
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
        while size >= 1024:
            size /= 1024
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
        
