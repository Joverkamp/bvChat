from socket import *
import threading
import hashlib
import sys
import time
import os.path
from os import path


# Get users/passwords from file
userPassList = {}
userPassListLock = threading.Lock()
if path.exists("users.txt"):
    with open("users.txt", "r") as f:
        lines = f.readlines()
    for line in lines:
        line = line.rstrip()
        userPass = line.split(":")
        userPassList[userPass[0]] = userPass[1]

# This dict holds users who are currentky logged in
usersLoggedIn = {}
usersLoogedInLock = threading.Lock()

# Set the message of the day
if path.exists("motd.txt"):
    with open("motd.txt", "r") as f:
        motd = f.read()+"\n"
else:
    motd = "There is no message of the day. :(\n"
       
# Set up linstener that will recieve connections to client users
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
        print("User {} already exists.".format(username))
        userPassListLock.release()
        return True
    else:
        userPassList[username] = password
        print("User {} added.".format(username))
        userPassListLock.release()
        return False


def login(username, clientAddr): 
    usersLoggedInLock.acquire()
    usersLoggedIn[username] = "{}:{}".format(clientAddr[0],clientAddr[1])
    usersLoggedInLock.release()


def logout(username):
    usersLoggedInLock.acquire()
    del usersLoggedIn[username]
    usersLoggedInLock.release()


def isLoggedIn(username):
    usersLoggedInLock.acquire()
    if username in usersLoggedIn:
        usersLoggedInLock.release()
        return True
    else:
        usersLoggedInLock.release()
        return False


def correctIsPassword(username, password):
    userPassListLock.acquire()
    if userPassList[username] == password:
        print("Password is correct.")
        userPassListLock.release()
        return True
    else:
        print("Password is incorrect.")
        userPassListLock.release()
        return False


def motd(clientConn):
    clientConn.send(motd.encode())


def broadcast(msg):
    pass

def handleClient(connInfo):
    # Connection has been established
    clientConn, clientAddr = connInfo
    clientIP = clientAddr[0]
    clientPort = clientAddr[1]
    print("Recieved connection from {}:{}".format(clientIP, clientPort))
    
    # Get username
    incoming = getLine(clientConn)
    username = incoming.rstrip()
    
    # Get password
    incoming = getLine(clientConn)
    password = incoming.rstrip()
   
    # Check if this is a new user/are they already logged in/is password correct
    if userExists(username,password):
        if isLoggedIn(username):
            # TODO what do we do if user is already logged in?
            # Close connection? Have them try again?
            pass
        else:
            if correctIsPassword(username, password):
            # TODO set up so that passwords cant be brute forced
            # Temp block users who fail 3 times in 30 seconds
            pass
    # User has passed the login
    login(username, clientAddr)
    # Notify other users of a login
    msg = "{} connected.\n".format(username)
    broadcast(msg) # TODO implement this function
    # Send user the motd
    motd(clientConn)


running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    except KeyboardInterrupt:
        print('\n[Shutting down]')
        running = False
