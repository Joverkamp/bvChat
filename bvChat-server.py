from socket import *
import threading
import hashlib
import sys
import time
import os.path
from os import path


# Get users/passwords from file
userPassList = {}
if path.exists("users.txt"):
    with open("users.txt", "r") as f:
        lines = f.readlines()
    for line in lines:
        line = line.rstrip()
        userPass = line.split(":")
        userPassList[userPass[0]] = userPass[1]
userPassListLock = threading.Lock()


port = 27120
listener = socket(AF_INET, SOCK_STREAM)
listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener.bind(('', port))
listener.listen(32) # Support up to 32 simultaneous connections

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


def userExists(username, password):
    userPassListLock.acquire()
    if username in userPassList:
        print("User exists!")
    else:
        userPassList[username] = password
        print("User {} added!".format(username))
    userPassListLock.release()



def handleClient(connInfo):
    clientConn, clientAddr = connInfo
    clientIP = clientAddr[0]
    clientPort = clientAddr[1]
    print("Recieved connection from {}:{}".format(clientIP, clientPort))
    
    incoming = getLine(clientConn)
    username = incoming.rstrip()
    incoming = getLine(clientConn)
    password = incoming.rstrip()
   
    userExists(username,password)

running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    except KeyboardInterrupt:
        print('\n[Shutting down]')
        running = False
