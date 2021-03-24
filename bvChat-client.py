# [NameServer] Client
from socket import *
from sys import argv
from pathlib import Path


tryingLogin = True

loginReport = '0'

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

#send username and password
while (tryingLogin == True):
    username = input("Enter username: ") + "\n"
    password = input("Enter your password: ") + "\n"
    clientSock.send(username.encode())
    clientSock.send(password.encode())
    loginReport = getLine(clientSock)
    print(loginReport)
    if(loginReport == '0\n'):
        print(loginReport + "FAILURE")
    elif (loginReport == '1\n'):
        tryingLogin = False


clientSock.close()
