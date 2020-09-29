from socket import *
from struct import pack
import curses, ssl, sys

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

    def sendBytes(self, data):

        # use struct to make sure we have a consistent endianness on the length
        length = pack('>Q', len(data))

        # sendall to make sure it blocks if there's back-pressure on the socket
        self.socket.sendall(length)
        self.socket.sendall(data)

        ack = self.socket.recv(1)
        if ack != b"\00":
            print("Error: got non-zero ack byte " + ack.hex())

def makeData(data):
    out = []
    pos = 0
    #print(bytes(data[:20], "utf-8"))
    cfg = 0
    cbg = 0
    pair = 0
    maxpair = 0
    pairs = {}
    while pos < len(data):
        if ord(data[pos]) == 27:
            pos += 2
            if data[pos] == "0": pos += 2; continue
            if data[pos] == "4": fg = False; bg = True
            else: fg = True; bg = False
            pos += 5 #skip ;5;
            num = ""
            while data[pos] != "m":
                num += data[pos]
                pos += 1
            num = int(num)
            #print(num)
            pos += 1
            if fg:
                cfg = num
            if bg:
                cbg = num

            if not (cfg, cbg) in pairs:
                maxpair += 1
                pair = maxpair
                pairs[(cfg, cbg)] = pair
                curses.init_pair(pair, cfg, cbg)
            else:
                pair = pairs[(cfg, cbg)]

            
        else:
            #log("'" + data[pos] + "'")
            #if data[pos] == " ":
                #log("reee")
            #    out.append((ccol, "█"))
            #else:
            out.append((pair, data[pos]))
            pos += 1
    return out

class MemeWin:
    def __init__(self, imgdata, metadata):
        self.data = makeData(imgdata)
        self.metadata = metadata
        self.width = 0
        while self.data[self.width][1] != "\n": self.width += 1
        self.width += 2
        self.height = len(imgdata.split("\n")) + 4
        self.s = curses.newwin(self.height, self.width, 3, 3)
        self.y = 3

    def move(self, y):
        self.s.mvwin(y, 3)
        self.y = y

    def draw(self):
        self.s.erase()
        self.s.addstr(0, 0, "┌" + "─" * (self.width - 2) + "┐")
        for i in range(1, self.height - 2):
            self.s.addstr(i, 0, "│" + " " * (self.width - 2) + "│")
        self.s.addstr(self.height - 2, 0, "└" + "─" * (self.width - 2) + "┘")

        self.s.addstr(1, 2, self.metadata["title"])

        votestr = "↑↓" + str(self.metadata["votes"])
        self.s.addstr(1, self.width - 2 - len(votestr), votestr)

        self.s.addstr(self.height - 3, 2, str(len(self.metadata["comments"])) + " Comments")
        y = 2
        x = 1
        for char in self.data:
            if char[1] == "\n":
                y += 1
                x = 1
            else:
                #curses.init_pair(1, char[0], char[1])
                #log(char[0], y, x)
                self.s.addstr(y, x, char[1], curses.color_pair(char[0]))
                x += 1
                
        self.s.refresh() 

class Application:
    def __init__(self):
        self.wins = []
        with open("file.txt", "r") as f:
            data = f.read()
        #print(makeData(data))
    
    def mainLoop(self):
        curses.wrapper(self.main)
        pass
    def getInput(self):
        ch = self.s.getch()
        self.s.addstr(str(ch))
        if ch == 27: #esc
            return False
        elif ch == 259: #up
            for win in self.wins:
                win.move(win.y - 1)
        elif ch == 258: #down
            for win in self.wins:
                win.move(win.y + 1)
        return True
        
    def drawScreen(self):
        #self.s.erase()
        for win in self.wins:
            win.draw()
        self.s.refresh()

    def main(self, stdscr):
        self.s = stdscr
        running = True
        curses.use_default_colors()
            
        with open("file.txt", "r") as f:
            data = f.read()
        self.wins.append(MemeWin(data, {"title": "An interesting title", "votes": 4, "comments": []}))
        while running:
            running = self.getInput()
            self.drawScreen()

if __name__ == '__main__':
    a = Application()
    a.mainLoop()
    """
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.keypad(True)
    
    while True:
        getInput(stdscr)
        drawScreen(stdscr)


    curses.echo()
    curses.keypad(False)
    curses.echo()
    curses.endwin()
    """
    
    """
    cp = ClientProtocol()

    with open('file.txt', 'rb') as fp:
        data = fp.read()

    cp.connect('127.0.0.1', 6967)
    success = cp.authenticate("Jachdich", "password")
    if success:
        print("Logged in!")
    else:
        print("Invalid username or password!")
        cp.sendBytes(b"quit")
        sys.exit(1)
        
    cp.sendBytes("upload".encode("utf-8"))
    cp.sendBytes("An interesting title".encode("utf-8"))
    cp.sendBytes(data)
    cp.sendBytes("quit".encode("utf-8"))
    cp.close()
    """
