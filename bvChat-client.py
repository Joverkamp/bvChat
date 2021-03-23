# [NameServer] Client
from socket import *
from sys import argv
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
