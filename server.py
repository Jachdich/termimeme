import os, threading, random, json, ssl, sys, mysql.connector, datetime
from socket import *
from struct import unpack, pack

PATH = "/var/www/html/meme/"

db = mysql.connector.connect(host="localhost", user="test", password="password", database="termimeme_metadata")
dbc = db.cursor()

class getmeta:
    def __init__(self, ID):
        self.ID = ID
        
    def __enter__(self):
        dbc.execute("select * from posts where id = {}".format(self.ID))
        results = list(dbc)
        if len(results) == 0: return None
        if len(results) > 1 : raise RuntimeError(">= 2 posts with the same ID")
        r = results[0]
        self.data = {"id": r[0], "date": r[1], "title": r[2], "votes": r[3], "op": r[4]}
        return self.data

    def __exit__(self, type, value, traceback):
        d = self.data #I'm lazy ok
        dbc.execute("update posts set date=%s, title=%s, votes=%s, op=%s where id=%s", (
            d["date"].strftime("%Y-%m-%d %H:%M:%S"),
            d["title"],
            d["votes"],
            d["op"],
            d["id"]
        ))
        db.commit()

def makemeta(d):
    dbc.execute("insert into posts values (%s, %s, %s, %s, %s);", (
            d["id"],
            d["date"].strftime("%Y-%m-%d %H:%M:%S"),
            d["title"],
            d["votes"],
            d["op"]
        ))
    db.commit()

class ServerProtocol:

    def __init__(self, connection):
        self.connection = connection
        self.user = None

    def recv_msg(self, send_ack=True):
        bs = self.connection.recv(8)
        (length,) = unpack('>Q', bs)
        data = b''
        while len(data) < length:
            to_read = length - len(data)
            data += self.connection.recv(
                4096 if to_read > 4096 else to_read)

        if send_ack:
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
        for f in os.listdir(PATH):
            if f.endswith(".metadata"): continue
            
            with getmeta(f) as meta:
                metadata = meta.copy()
            
            with open(PATH + f, "r") as fp:
                data = fp.read()
            
            x.append({"data": data, **metadata})
        return x
            
        
    def handle_client(self):
        try:
            while True:
                command = self.recv_msg(send_ack=False)
                print(command)
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
                    self.connection.sendall(b'\00')
                    title = self.recv_msg().decode("utf-8")
                    data = self.recv_msg()
                    ID = self.gen_id()
                    with open(PATH + ID, "wb") as f:
                        f.write(data)
                    
                    makemeta({"title": title, "date": datetime.datetime.now(), "votes": 0, "op": self.user, "id": ID})
                    self.connection.sendall(b'\00')

                elif command == b"upvote":
                    self.connection.sendall(b'\00')
                    ID = self.recv_msg().decode("utf-8")
                    with getmeta(ID) as meta:
                        meta["votes"] += 1                    
                    
                elif command == b"comment":
                    self.connection.sendall(b'\00')
                    ID = self.recv_msg()
                    body = self.recv_msg()
                    
                elif command == b"get":
                    self.connection.sendall(b'\00')
                    sort = self.recv_msg()
                    x = self.index_posts()
                    for n in x:
                        n["date"] = n["date"].strftime("%Y-%m-%d %H:%M:%S")
                    self.send_msg(json.dumps(x).encode("utf-8"))
                
        finally:
            self.connection.shutdown(SHUT_WR)
            self.connection.close()

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("127.0.0.1", 6968))
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
