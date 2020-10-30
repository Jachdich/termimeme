from socket import *
from struct import pack, unpack
import curses, ssl, sys, time, json
from blessed import Terminal
from math import *

from read_image import makeData

term = Terminal()

with open("log.txt", "w") as f: pass

def log(*args):
    args = " ".join([str(x) for x in args])
    with open("log.txt", "a") as f:
        f.write(args + "\n")
    
rtn = lambda x, n: round(x, -int(floor(log10(x))) + (n - 1))

class ClientProtocol:

    def __init__(self):
        self.socket = None

    def connect(self, server_ip, server_port):
        self.unssocket = socket(AF_INET, SOCK_STREAM)
        self.unssocket.connect((server_ip, server_port))
        self.context = ssl.create_default_context(cafile="cert.pem")
        self.context.check_hostname = False
        #ssl.create_default_context(cafile="cert.pem")
        self.socket = self.context.wrap_socket(self.unssocket, server_hostname=server_ip)

    def close(self):
        self.sendBytes("quit".encode("utf-8"))
        self.socket.shutdown(SHUT_WR)
        self.socket.close()
        self.socket = None

    def authenticate(self, username, password):
        self.sendBytes(b"login")
        self.sendBytes(username.encode("utf-8"))
        self.sendBytes(password.encode("utf-8"))
        success = self.socket.recv(1)
        if success == b"\00":
            return True
        return False

    def recvBytes(self):
        bs = self.socket.recv(8)
        (length,) = unpack('>Q', bs)
        data = b''
        while len(data) < length:
            # doing it in batches is generally better than trying
            # to do it all in one go, so I believe.
            to_read = length - len(data)
            data += self.socket.recv(
                4096 if to_read > 4096 else to_read)

        return data

    def sendBytes(self, data):
        # use struct to make sure we have a consistent endianness on the length
        length = pack('>Q', len(data))

        # sendall to make sure it blocks if there's back-pressure on the socket
        self.socket.sendall(length)
        self.socket.sendall(data)

        ack = self.socket.recv(1)
        if ack != b"\00":
            print("Error: got non-zero ack byte '" + ack.hex() + "'")

class MemeWin:
    def __init__(self, imgdata, metadata):
        self.data = makeData(imgdata)
        self.metadata = metadata
        self.width = 0
        while self.data[self.width][2] != "\n": self.width += 1
        self.width += 2
        if len(metadata["title"]) + 8 > self.width: self.width = len(metadata["title"]) + 8
        self.height = len(imgdata.split("\n")) + 4
        #self.s = curses.newwin(self.height, self.width, 3, 3)
        self.y = 0
        self.x = 0
        self.update_data()

    def update_data(self,start=0):
        top = "┌" + "─" * (self.width - 2) + "┐" + "\n"
        bottom = "└" + "─" * (self.width - 2) + "┘" + "\n"
        votestr = "↑↓" + str(self.metadata["votes"])
        comments = str(start) + " Comments"
        date = self.metadata["date"] + " "
        
        commentstr = "│ " + comments + " " * (self.width - 3 - len(comments) - len(date)) + date + "│\n"

        img = top + "│ " + self.metadata["title"] +\
               " " * (self.width - len(self.metadata["title"]) - 4 - len(votestr)) +\
               votestr + " │\n│" + term.reset
               
        for char in self.data:
            fg = char[0]
            bg = char[1]
            if char[2] == "\n":
                img += term.normal + "│\n│"
                continue
            img += term.on_color_rgb(bg[0], bg[1], bg[2]) + term.color_rgb(fg[0], fg[1], fg[2]) + char[2]
        if img.endswith("\n│"): img = img[:-2]
        
        img += "\n" + commentstr + bottom
        self.img = img.split("\n")

    def move(self, y):
        #self.s.mvwin(y, 3)
        self.y = y

    def draw(self, select=False):
        if self.y > term.height + self.height: return
        if self.y < 0 - self.height: return
        a = time.time()
        
        start_y = self.y
        start = 0
        if self.y < 0: start_y = 0; start = -self.y
        
        end = len(self.img)
        if self.y + self.height > term.height: end = - ((self.y + self.height) - term.height)
        trunk_img = "\n".join(self.img[start:end])
        #
        """
        for y, line in enumerate(self.img):
            if (y + self.y) < 10 or (y + self.y) > term.height:
                pass
            else:
                trunk_img += line + "\n"
        """
        
        b = time.time()
        if select:
            col = term.color_rgb(255, 255, 0)
        else:
            col = ""
        print(col + term.move_xy(self.x, start_y) + trunk_img)
        c = time.time()
        #log("Processing/printing {}".format((b-a)/(c-b)))
                
class Application:
    def __init__(self, cp):
        self.wins = []
        self.selected_idx = 0
        self.cp = cp
        with open("file.txt", "r") as f:
            data = f.read()
        #print(makeData(data))
    
    def mainLoop(self):
        #curses.wrapper(self.main)
        with term.cbreak():
            with term.fullscreen():
                with term.hidden_cursor():
                    self.main()

    def getInput(self):
        ch = term.inkey()
        if ch.name == u"KEY_ESCAPE":
            return False
        elif ch.name == u"KEY_UP": 
            for win in self.wins:
                win.y += 4
            self.updateSelected()
        elif ch.name == u"KEY_DOWN":
            for win in self.wins:
                win.y -= 4
            self.updateSelected()
            
        elif repr(ch) == "'a'":
            self.cp.sendBytes("upvote".encode("utf-8"))
            self.cp.sendBytes(str(self.wins[self.selected_idx].metadata["id"]).encode("utf-8"))
            
            pass
        return True

    def updateSelected(self):
        for i, win in enumerate(self.wins):
            if win.y > 0 and win.y < term.height:
                log(i)
                self.selected_idx = i
                break
    
    def drawScreen(self):
        print(term.clear())
        for i, win in enumerate(self.wins):
            win.draw(select=i==self.selected_idx)

    def main(self):
        #with open("test24bit.txt", "r") as f:
        #    data = f.read()
        #self.wins.append(MemeWin(data, {"title": "An interesting title", "votes": 4, "comments": []}))

        self.cp.sendBytes("get".encode("utf-8"))
        self.cp.sendBytes("top".encode("utf-8"))
        data = json.loads(self.cp.recvBytes().decode("utf-8"))
        y = 0
        for n in data:
            self.wins.append(MemeWin(n["data"], n,))
            self.wins[-1].y = y
            y += self.wins[-1].height


        running = True
        while running:
            running = self.getInput()
            self.drawScreen()
        self.cp.close()

if __name__ == '__main__':
    cp = ClientProtocol()
    cp.connect('127.0.0.1', 6968)
    success = cp.authenticate("Jachdich", "password")
    if success:
        print("Logged in!")
    else:
        print("Invalid username or password!")
        cp.close()
        sys.exit(1)

    a = Application(cp)
    a.mainLoop()
    """
    for ree in range(9):
        with open('mem' + str(ree) + '.txt', 'rb') as fp:
            data = fp.read()
        cp.sendBytes("upload".encode("utf-8"))
        cp.sendBytes("An interesting title: mem{}".format(ree).encode("utf-8"))
        cp.sendBytes(data)
    cp.close()"""