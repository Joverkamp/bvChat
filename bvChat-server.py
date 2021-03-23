from socket import *
from pathlib import Path

def getFullMsg(conn, msgLength):
    msg = b''
    while len(msg) < msgLength:
        retVal = conn.recv(msgLength - len(msg))
        msg += retVal
        if len(retVal) == 0:
            break   
    return msg

def getLine(conn):
    msg = b''
    while True:
        ch = conn.recv(1)
        msg += ch
        if ch == b'\n' or len(ch) == 0:
            break
    return msg.decode()

port = 27120

listener = socket(AF_INET, SOCK_STREAM)
listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener.bind( ('', port) )
listener.listen(4)
print("Server is now listening for connections on port", port)

try:
  while True:
    (conn, clientAddr) = listener.accept()
    print("Client Connected")
    
    # Retreive files available for sending
    folder = Path("./repository")
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)

    print("Client Connection Closed")
    conn.close()


except KeyboardInterrupt:
  print("Killing server...")
