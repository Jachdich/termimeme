import os, threading, random, json, ssl
from socket import *
from struct import unpack

PATH = "/var/www/html"

class ServerProtocol:

    def __init__(self, connection):
        self.connection = connection
        self.user = None

    def recv_msg(self, send_ack=True):
        bs = self.connection.recv(8)
        (length,) = unpack('>Q', bs)
        data = b''
        while len(data) < length:
            # doing it in batches is generally better than trying
            # to do it all in one go, so I believe.
            to_read = length - len(data)
            data += self.connection.recv(
                4096 if to_read > 4096 else to_read)

        if send_ack:
            # send our 0 ack
            assert len(b'\00') == 1
            self.connection.sendall(b'\00')
        return data

    def gen_id(self):
        return str(random.randint(0, 100000))

    def authenticate_user(self, username, password):
        self.user = username
        return True
        
    def handle_client(self):
        try:
            while True:
                command = self.recv_msg(send_ack=False)
                if command == b"quit":
                    self.connection.sendall(b'\00')
                    break
                elif command == b"login":
                    self.connection.sendall(b'\00')
                    username = self.recv_msg()
                    password = self.recv_msg()
                    if self.authenticate_user(username, password):
                        self.connection.sendall(b"\00")
                        continue
                    self.connection.sendall(b"\02")
                    continue
                    
                if self.user == None:
                    self.connection.sendall(b'\01') #need to log in
                    continue
                self.connection.sendall(b'\00')
                    
                
                if command == b"upload":
                    title = self.recv_msg().decode("utf-8")
                    data = self.recv_msg()
                    ID = self.gen_id()
                    metadata = json.dumps({"title": title, "comments": [], "votes": 0, "op": self.user})
                    with open(PATH + "/meme/" + ID, "wb") as f:
                        f.write(data)
                    with open(PATH + "/meme/" + ID + ".metadata", "w") as f:
                        f.write(metadata)

                elif command == b"upvote":
                    pass
                elif command == b"comment":
                    pass
                
        finally:
            self.connection.shutdown(SHUT_WR)
            self.connection.close()

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("127.0.0.1", 6967))
    s.listen(100)
    ss = context.wrap_socket(s, server_side=True)
    clients = []
    try:
        while True:
            connection, addr = ss.accept()
            sp = ServerProtocol(connection)
            sp_thread = threading.Thread(target=sp.handle_client)
            sp_thread.start()
            clients.append((sp, sp_thread))
    finally:
        ss.close()
        s.close()
