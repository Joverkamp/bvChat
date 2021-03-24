from socket import *
import threading
import hashlib
import sys
import time
import os.path
from os import path
from queue import Queue

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
usersLoggedInLock = threading.Lock()
    
# Dict for ips and last three invalid attempt timestamps
ipBadAttempts = {}
ipBadAttemptsLock = threading.Lock()

tempBlockedUsers = {}
tempBlockedUsersLock = threading.Lock()

# Set the message of the day
if path.exists("motd.txt"):
    with open("motd.txt", "r") as f:
        motd = f.read()
else:
    motd = "There is no message of the day. :("
       
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


def getTimeStamp():
    timeStamp = time.time()
    print(timeStamp)
    return timeStamp

def checkTimeDiff(timeStamps, ipUsername):
    diff = timeStamps[2] - timeStamps[0]
    if diff <= 30.0:
        tempBlockUser(ipUsername)

def tempBlockUser(ipUsername):
    print("User has been blocked")
    tempBlockedUsers[ipUsername] = "asldfjna"

def userIsBlocked(ip, username):
    ipUsername = "{}:{}".format(ip,username)
    if ipUsername in tempBlockedUsers:
        return True
    return False

def badPasswordAttempt(ip, username):
    ipUsername = "{}:{}".format(ip,username)
    if ipUsername in ipBadAttempts:
        if len(ipBadAttempts[ipUsername]) < 3:
            ipBadAttempts[ipUsername].append(getTimeStamp())
            if len(ipBadAttempts[ipUsername]) == 3:
                checkTimeDiff(ipBadAttempts[ipUsername], ipUsername)
        else:
            checkTimeDiff(ipBadAttempts[ipUsername], ipUsername)
            ipBadAttempts[ipUsername].pop(0)
            ipBadAttempts[ipUsername].append(getTimeStamp())
    else:
        ipBadAttempts[ipUsername] = []
        ipBadAttempts[ipUsername].append(getTimeStamp())


        

def motd(clientConn):
    #clientConn.send(motd.encode())
    pass

def broadcast(msg):
    pass

def handleClient(connInfo):
    # Connection has been established
    clientConn, clientAddr = connInfo
    clientIP = clientAddr[0]
    clientPort = clientAddr[1]
    print("Recieved connection from {}:{}".format(clientIP, clientPort))
    verifyUser = False
    while verifyUser == False:
        # Get username
        incoming = getLine(clientConn)
        username = incoming.rstrip()
        
        # Get password
        incoming = getLine(clientConn)
        password = incoming.rstrip()
       
        # Check if this is a new user/are they already logged in/is password correcti
        if userExists(username,password):
            if userIsBlocked(clientIP, username):
                msg = "0\n"
                clientConn.send(msg.encode())
                continue

            elif isLoggedIn(username):
                print("User already logged in.")
                msg = "0\n"
                clientConn.send(msg.encode())
                continue
            else:
                if not correctIsPassword(username, password):
                    print("bad password attempt")
                    msg = "0\n"
                    clientConn.send(msg.encode())
                    badPasswordAttempt(clientIP, username)
                    continue
        msg = "1\n"
        clientConn.send(msg.encode())
        verifyUser = True
    # User has passed the login
    login(username, clientAddr)
    print("login success")
    # Notify other users of a login
    #msg = "{} connected.\n".format(username)
    #broadcast(msg) # TODO implement this function
    # Send user the motd
    #motd(clientConn)
    clientConn.close()
    logout(username)

running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    except KeyboardInterrupt:
        print('\n[Shutting down]')
        running = False
