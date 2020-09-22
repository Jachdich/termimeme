from socket import *
from struct import pack
import curses, ssl, sys

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
        # could handle a bad ack here, but we'll assume it's fine.

if __name__ == '__main__':
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
