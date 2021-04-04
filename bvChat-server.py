from socket import *
import threading
import hashlib
import sys
import time
import os
from queue import Queue
import json

# load in user data
# this data includes
#     -- username
#     -- password
#     -- loggedin (either "none" or an ip:port)
#     -- mail (list of offline messages)
userInfo = {}
userInfoLock = threading.Lock()
if os.path.exists("users.json") and os.stat("users.json").st_size != 0:
    with open("users.json", "r") as f:
        userInfo = json.load(f)

# dict of ip:usernames and a list of their last three failed
# login attempts
# used for blocking brute force attempts
ipUserFailStamps = {}
ipUserFailStampsLock = threading.Lock()

# list for temporarily blocked ip/usernames
ipUserBlocked = [] 
ipUserBlockedLock = threading.Lock()

# Set the message of the day from text file
if os.path.exists("motd.txt"):
    with open("motd.txt", "r") as f:
        todaysMsg = f.read()
else:
    todaysMsg = "There is no message of the day. :("
       
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


# sends a newline terminated string to a given ip port list/tuple
def sendMessage(msg, ipPort):
    ip = ipPort[0]
    port = int(ipPort[1])
    msg = msg+"\n"
    sendMsgSock = socket(AF_INET, SOCK_STREAM)
    sendMsgSock.connect( (ip, port) )
    sendMsgSock.send(msg.encode())
    sendMsgSock.close()

# Returns false is a string is empty. Can also add any other prohibited
# string behaiors here
def inputCheck(toCheck):
    toCheck = toCheck.replace(" ","")
    if toCheck == "" or len(toCheck) == 0:
        return False
    return True

# Given a username and password, adds user to dictionary and initializes
# other data 
def createUser(username, password):
    userInfoLock.acquire()
    userInfo[username] = {}
    userInfo[username]["password"] = password
    userInfo[username]["loggedin"] = "none"
    userInfo[username]["mail"] = []
    userInfoLock.release()

# Checks if user exists in the global dictionary
def userExists(username):
    userInfoLock.acquire()
    if username in userInfo:
        userInfoLock.release()
        return True
    else:
        userInfoLock.release()
        return False

# Adds login data to user dict and broadcasts to users of a login
def login(username, clientAddr): 
    userInfoLock.acquire()
    userInfo[username]["loggedin"] = clientAddr
    userInfoLock.release()
    
    msg = "[{} connected]\n".format(username)
    broadcast(msg)
    
    print("{} logged in".format(username))

# Removes login data from user dict and broadcasts to users of a logout
def logout(username):
    if userExists(username):    
        userInfoLock.acquire()
        userInfo[username]["loggedin"] = "none"
        userInfoLock.release()

        msg = "[{} disconnected]\n".format(username)
        broadcast(msg)

        print("{} logged out".format(username))


# Remove all current logins on server termination and startup to avoid 
# misleading login status
def logoutAll():
    userInfoLock.acquire()
    for user in userInfo:
        userInfo[user]["loggedin"] = "none"
    userInfoLock.release()


# Checks if user is logged in
def isLoggedIn(username):
    if userExists(username):
        userInfoLock.acquire()
        if userInfo[username]["loggedin"] != "none":
            userInfoLock.release()
            return True
    userInfoLock.release()
    return False


# Checks if password matches username
def correctPassword(username, password):
    userInfoLock.acquire()
    if userInfo[username]["password"] == password:
        userInfoLock.release()
        return True
    else:
        userInfoLock.release()
        return False

# Get current time
def getTimeStamp():
    timeStamp = time.time()
    return timeStamp


# Checks the difference between most recent 3rd and most recent timestamps
# if the dii is <= 30, block the user
def checkTimeDiff(timeStamps, ipUsername):
    diff = timeStamps[2] - timeStamps[0]
    if diff <= 30.0:
        tempBlockUser(ipUsername)


# add ip:username combo to a blocked list
def tempBlockUser(ipUsername):
    ipUserBlockedLock.acquire()
    ipUserBlocked.append(ipUsername)
    ipUserBlockedLock.release()
    print("{} blocked".format(ipUsername))


# Check if a ip and username combo is blocked. Also if user is blocked and 
# 2 minuted have passed, unblock ip username
def isBlocked(ip, username):
    ipUsername = "{}:{}".format(ip,username)
    ipUserBlockedLock.acquire()
    ipUserFailStampsLock.acquire()
    if ipUsername in ipUserBlocked:
        if getTimeStamp() - ipUserFailStamps[ipUsername][2] > 120.0:
            ipUserBlocked.remove(ipUsername)
            ipUserBlockedLock.release()
            ipUserFailStampsLock.release()
            return False
        ipUserBlockedLock.release()
        ipUserFailStampsLock.release()
        return True
    ipUserBlockedLock.release()
    ipUserFailStampsLock.release()
    return False


# Called on a bad password attempt. Adds timestamp of failure to a dict of
# ip:username combos. If 3 stamps are already recored boot out the oldest
def badPasswordAttempt(ip, username):
    ipUsername = "{}:{}".format(ip,username)
    ipUserFailStampsLock.acquire()
    if ipUsername in ipUserFailStamps:
        if len(ipUserFailStamps[ipUsername]) < 3:
            ipUserFailStamps[ipUsername].append(getTimeStamp())
            if len(ipUserFailStamps[ipUsername]) == 3:
                checkTimeDiff(ipUserFailStamps[ipUsername], ipUsername)
        else:
            checkTimeDiff(ipUserFailStamps[ipUsername], ipUsername)
            ipUserFailStamps[ipUsername].pop(0)
            ipUserFailStamps[ipUsername].append(getTimeStamp())
    else:
        ipUserFailStamps[ipUsername] = []
        ipUserFailStamps[ipUsername].append(getTimeStamp())
    ipUserFailStampsLock.release()


# Send mail received offline and send to user on login
def getMail(username): 
    userInfoLock.acquire()
    ipPort =  userInfo[username]["loggedin"].split(":")
    mail = userInfo[username]["mail"]
    userInfo[username]["mail"] = []

    if len(mail) > 0:
        for msg in mail:
            sendMessage(msg, ipPort)
    userInfoLock.release()


# Send msg to all currently logged in users
def broadcast(msg):
    userInfoLock.acquire()
    for user in userInfo:
        if userInfo[user]["loggedin"] != "none":
            ipPort = userInfo[user]["loggedin"].split(":")
            sendMessage(msg, ipPort)
    userInfoLock.release()
        

# Send message to an existing user, if they are offline, add ,sg to their mail
def tell(toTell, msg, username):
    if isLoggedIn(toTell):
        userInfoLock.acquire()
        ipPort = userInfo[toTell]["loggedin"].split(":")
        userInfoLock.release()

        msg = "(DM){}: {}\n".format(username, msg)
        sendMessage(msg, ipPort) 
    else:
        if userExists(toTell):
            userInfoLock.acquire()
            userInfo[toTell]["mail"].append("(MAIL){}: {}".format(username,msg))
            userInfoLock.release()


# broadcast emote msg
def me(username, msg):
    msg = "*{} {}".format(username, msg)
    broadcast(msg)

# Send every user who is currently loggeg in to ipPort
def who(ipPort):
    ipPort = ipPort.split(":")

    userInfoLock.acquire()
    for user in userInfo:
        if userInfo[user]["loggedin"] != "none":
            msg = "{}\n".format(user)
            sendMessage(msg, ipPort)
    userInfoLock.release()


# Sends moty to ipPort
def motd(ipPort):
    ipPort = ipPort.split(":")
    msg = "(MOTD){}\n".format(todaysMsg)
    sendMessage(msg, ipPort)


# Save user info dict as json for easy readback
def saveUserInfo():
    with open("users.json", "w") as f:
        userInfoLock.acquire()
        json.dump(userInfo, f, indent=2)
        userInfoLock.release()


def handleClient(connInfo):
    # Connection has been established
    # Set all clietn info
    clientConn, clientAddr = connInfo
    clientIP = clientAddr[0]
    clientPort = clientAddr[1]
    print("Recieved connection from {}:{}".format(clientIP, clientPort))
    try:
        incoming = getLine(clientConn)
        clientListenPort = incoming.rstrip()
        clientAddrListen = "{}:{}".format(clientIP,clientListenPort)
        # client needs to login an account
        #     -- username must not already be logged in
        #     -- password must match
        #     -- if unique username is given new account is created
        #     -- cannot have empty input
        #     -- send appropriate error codes for client and loop upom failure
        # TODO add these error codes on client side
        # ERROR CODES
        #     -- "badpass" wrong password
        #     -- "blocked" user:ip is temporarily blocked
        #     -- "alrlogd" someone is already logged in under that username
        #     -- "badinpt" you typed invalid input
        #     -- "success" you successfully logged in

        verifyingUser = True
        while verifyingUser:
            # Get username
            incoming = getLine(clientConn)
            username = incoming.rstrip()
             
            # Get password
            incoming = getLine(clientConn)
            password = incoming.rstrip()
          
            # Check if input is valid
            if inputCheck(username) == False or inputCheck(password) == False:
                msg = "badinpt\n"
                clientConn.send(msg.encode())
                continue

            elif userExists(username):
                # can't login if you are blocked
                # if blocking time has passed you will be unblocked here
                if isBlocked(clientIP, username):
                    msg = "blocked\n"
                    clientConn.send(msg.encode())
                    badPasswordAttempt(clientIP, username)
                    continue
                elif isLoggedIn(username):
                    msg = "alrlogd\n"
                    clientConn.send(msg.encode())
                    continue
                else:
                    if not correctPassword(username, password):
                        msg = "badpass\n"
                        clientConn.send(msg.encode())
                        badPasswordAttempt(clientIP, username)
                        continue
            else:
                createUser(username, password)
            # verification success 
            # login user
            # send confirmation code to client and begin listening for messages
            msg = "success\n"
            clientConn.send(msg.encode())
            login(username,clientAddrListen)
            motd(clientAddrListen)
            getMail(username)
           # sendMessage(motd, username)
            verifyingUser = False
        # while user is connected receive messages and commands
        participating = True
        while participating:
            incoming = getLine(clientConn).rstrip()
            if inputCheck(incoming) == True:
                if incoming.startswith("/"):
                    command = incoming.split()[0][1:]
                    if command == "exit":
                        participating = False
                    elif command == "tell":
                        try:
                            restOfMsg = incoming[6:]
                            toTell = restOfMsg.split()[0]
                            msg = restOfMsg[len(toTell)+1:]
                            if inputCheck(msg) == True:
                                tell(toTell, msg, username)
                        except:
                            pass
                    elif command == "me":
                        try:
                            msg = incoming[4:]
                            if inputCheck(msg) == True:
                                me(username, msg)
                        except:
                            pass
                    elif command == "who":
                        who(clientAddrListen)
                    elif command == "motd":
                        motd(clientAddrListen)
                    else:
                        msg = "{}: {}\n".format(username, incoming)
                        broadcast(msg)

         
                        
                else:
                    msg = "{}: {}\n".format(username, incoming)
                    broadcast(msg)

     #handle diconnects         
    except Exception:
        print("Exception occurred, closing connection with {}:{}".format(clientIP, clientPort))
    logout(username)
    clientConn.close()
            
# Listen for users to join the server
running = True
print("Listening for connections on port {}".format(port))
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    # When server closes save data and log everyone out
    except KeyboardInterrupt:
        logoutAll()
        saveUserInfo()
        print('\n[Shutting down]')
        running = False
