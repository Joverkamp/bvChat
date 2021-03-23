# [NameServer] Client
from socket import *
from sys import argv
from pathlib import Path

def recvAll(sock, numBytes):
    data = b''
    while (len(data) < numBytes):
        data += sock.recv(numBytes - len(data))
    return data

# Set server/port from command line
progname = argv[0]
if len(argv) != 3:
    print("Usage: python3 {} <IPaddress> <port>".format(progname))
    exit(1)
serverIP = argv[1]
serverPort = int(argv[2])

# Establish connection
clientSock = socket(AF_INET, SOCK_STREAM)
clientSock.connect( (serverIP, serverPort) )


clientSock.close()
