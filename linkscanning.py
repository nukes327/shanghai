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
        self.message = ""

    def linkscan(self, link):
        """Handle a link"""
        try:
            r = requests.get(link, timeout=1, stream=True,
                             headers={"Accept-Encoding": "deflate"}) #Get the link
        except requests.exceptions.SSLError:
            r = requests.get(link, timeout=1, stream=True,
                             headers={"Accept-Encoding": "deflate"}, #SSL Failed, try again without
                             verify=False)
        except requests.exceptions.HTTPError:
            self.message = "Invalid HTTP response"
            raise
        except requests.exceptions.ReadTimeout:
            self.message = "Request timed out, working on a fix"
            raise
        except requests.exceptions.ConnectionError:
            self.message = "Connection error, is this a real site?"
            raise
        if r:
            if "html" in r.headers["content-type"]:
                self.message = "[title] "
                try:
                    self.message += BeautifulSoup(r.text, 'html.parser').title.string.strip()
                except AttributeError:
                    self.message = "No page title found"
            else:
                self.message = "[{}] - ".format(r.headers["content-type"])
                try:
                    self.message += self.sizeconvert(int(r.headers["content-length"]))
                except KeyError:
                    self.message += "?B"
                except IndexError:
                    self.message += "What the fuck are you linking a file so big for"
            r.close()
        return self.message

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
