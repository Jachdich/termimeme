import os, threading, random, json, ssl, sys
from socket import *
from struct import unpack, pack

PATH = "/var/www/html"

class getmeta:
    def __init__(self, ID):
        self.ID = ID
        
    def __enter__(self):
        print("getmeta for " + self.ID)
        with open(PATH + "/meme/" + self.ID + ".metadata", "r") as f:
            self.data = json.loads(f.read())
        return self.data

    def __exit__(self, type, value, traceback):
        print("getmeta cleaning up for " + self.ID)
        with open(PATH + "/meme/" + self.ID + ".metadata", "w") as f:
            f.write(json.dumps(self.data))



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

    def send_msg(self, data):
        length = pack('>Q', len(data))
        self.connection.sendall(length)
        self.connection.sendall(data)

    def gen_id(self):
        return str(random.randint(0, 100000))

    def authenticate_user(self, username, password):
        self.user = username
        return True

    def index_posts(self):
        x = []
        for f in os.listdir(PATH + "/meme/"):
            if f.endswith(".metadata"): continue
            with open(PATH + "/meme/" + f + ".metadata", "r") as fp:
                metadata = json.loads(fp.read())
            with open(PATH + "/meme/" + f, "r") as fp:
                data = fp.read()
            x.append({"data": data, **metadata})
        return x
            
        
    def handle_client(self):
        try:
            while True:
                command = self.recv_msg(send_ack=False)
                if command == b"quit":
                    self.connection.sendall(b'\00')
                    break
                elif command == b"login":
                    self.connection.sendall(b'\00')
                    username = self.recv_msg().decode("utf-8")
                    password = self.recv_msg().decode("utf-8")
                    if self.authenticate_user(username, password):
                        self.connection.sendall(b"\00")
                        continue
                    self.connection.sendall(b"\02")
                    continue
                    
                if self.user == None:
                    self.connection.sendall(b'\01') #need to log in
                    continue                    
                
                if command == b"upload":
                    title = self.recv_msg().decode("utf-8")
                    data = self.recv_msg()
                    ID = self.gen_id()
                    metadata = json.dumps({"title": title, "comments": [], "votes": 0, "op": self.user})
                    with open(PATH + "/meme/" + ID, "wb") as f:
                        f.write(data)
                    with open(PATH + "/meme/" + ID + ".metadata", "w") as f:
                        f.write(metadata)
                    self.connection.sendall(b'\00')

                elif command == b"upvote":
                    ID = self.recv_msg().decode("utf-8")
                    with getmeta(ID) as meta:
                        meta["votes"] += 1

                    self.connection.sendall(b'\00')
                    
                    
                elif command == b"comment":
                    self.connection.sendall(b'\00')
                    pass
                elif command == b"get":
                    sort = self.recv_msg()
                    x = self.index_posts()
                    self.connection.sendall(b'\00')
                    self.send_msg(json.dumps(x).encode("utf-8"))
                
        finally:
            self.connection.shutdown(SHUT_WR)
            self.connection.close()

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("127.0.0.1", 6969))
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

    except Exception as e:
        ss.close()
        s.close()
        raise e
    except KeyboardInterrupt:
        ss.close()
        s.close()
        sys.exit(1)
    finally:
        ss.close()
        s.close()
