from socket import *
from struct import pack, unpack
import curses, ssl, sys, time, json
from blessed import Terminal

from read_image import makeData

term = Terminal()

def log(*args):
    args = " ".join([str(x) for x in args])
    with open("log.txt", "a") as f:
        f.write(args + "\n")

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
            print("Error: got non-zero ack byte " + ack.hex())

class MemeWin:
    def __init__(self, imgdata, metadata):
        self.data = makeData(imgdata)
        self.metadata = metadata
        self.width = 0
        while self.data[self.width][2] != "\n": self.width += 1
        self.width += 2
        self.height = len(imgdata.split("\n")) + 4
        #self.s = curses.newwin(self.height, self.width, 3, 3)
        self.y = 0
        self.x = 0

    def move(self, y):
        #self.s.mvwin(y, 3)
        self.y = y

    def draw(self):
        if self.y < 0: return
        if self.y > term.height - self.height: return
        top = "┌" + "─" * (self.width - 2) + "┐" + "\n"
        sides = ""
        for i in range(1, self.height - 2):
            sides += "│" + " " * (self.width - 2) + "│" + "\n"
                
        bottom = "└" + "─" * (self.width - 2) + "┘" + "\n"

        with term.location(x=self.x, y=self.y):
            print(top + sides + bottom)

        with term.location(x=self.x + 2, y=self.y + 1):
            print(self.metadata["title"])

        votestr = "↑↓" + str(self.metadata["votes"])
        with term.location(x=self.x + self.width - 2 - len(votestr), y=self.y + 1):
            print(votestr)

        with term.location(x=self.x + 2, y=self.height - 3 + self.y):
            print(str(len(self.metadata["comments"])) + " Comments")

        img = ""
        for char in self.data:
            fg = char[0]
            bg = char[1]
            img += term.on_color_rgb(bg[0], bg[1], bg[2]) + term.color_rgb(fg[0], fg[1], fg[2]) + char[2]
        with term.location(x=self.x + 1, y = self.y + 2):
            print(img)
                
                
class Application:
    def __init__(self, cp):
        self.wins = []
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
                win.y += 1
        elif ch.name == u"KEY_DOWN":
            for win in self.wins:
                win.y -= 1
        return True
        
    def drawScreen(self):
        print(term.clear())
        for win in self.wins:
            win.draw()

    def main(self):
        #with open("test24bit.txt", "r") as f:
        #    data = f.read()
        #self.wins.append(MemeWin(data, {"title": "An interesting title", "votes": 4, "comments": []}))

        cp.sendBytes("get".encode("utf-8"))
        cp.sendBytes("top".encode("utf-8"))
        data = json.loads(cp.recvBytes().decode("utf-8"))[0] 
        self.wins.append(MemeWin(data["data"], data))

        running = True
        while running:
            running = self.getInput()
            self.drawScreen()

if __name__ == '__main__':
    cp = ClientProtocol()
    cp.connect('127.0.0.1', 6967)
    success = cp.authenticate("Jachdich", "password")
    if success:
        print("Logged in!")
    else:
        print("Invalid username or password!")
        cp.sendBytes(b"quit")
        sys.exit(1)

    a = Application(cp)
    a.mainLoop()
    
    #with open('test24bit.txt', 'rb') as fp:
    #    data = fp.read()        
    #cp.sendBytes("upload".encode("utf-8"))
    #cp.sendBytes("An interesting title".encode("utf-8"))
    #cp.sendBytes(data)
    #cp.sendBytes("quit".encode("utf-8"))
    cp.close()