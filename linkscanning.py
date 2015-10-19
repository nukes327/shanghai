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
        """Handle a link"""
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
        """Convert a Byte size to something readable"""
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
