from socket import *
from pathlib import Path

def recvAll(sock, numBytes):
    data = b''
    while (len(data) < numBytes):
        data += sock.recv(numBytes - len(data))
    return data

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
