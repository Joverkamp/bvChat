from socket import *
import threading
import hashlib
import sys
import time
import os
from queue import Queue
import json

# load in user data that is saved upon server termination
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

# Set the message of the day
if os.path.exists("motd.txt"):
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

def inputCheck(toCheck):
    toCheck = toCheck.replace(" ","")
    if toCheck == "" or len(toCheck) == 0:
        return False
    return True


def createUser(username, password):
    userInfoLock.acquire()
    userInfo[username] = {}
    userInfo[username]["password"] = password
    userInfo[username]["loggedin"] = "none"
    userInfo[username]["mail"] = []
    userInfoLock.release()

def userExists(username):
    userInfoLock.acquire()
    if username in userInfo:
        userInfoLock.release()
        return True
    else:
        userInfoLock.release()
        return False


def login(username, clientAddr): 
    userInfoLock.acquire()
    userInfo[username]["loggedin"] = clientAddr
    userInfoLock.release()
    
    msg = "* {} connected.\n".format(username)
    broadcast(msg)
    
    print("{} logged in".format(username))


def logout(username):
    if userExists(username):    
        userInfoLock.acquire()
        userInfo[username]["loggedin"] = "none"
        userInfoLock.release()

        msg = "* {} disconnected.\n".format(username)
        broadcast(msg)

        print("{} logged out".format(username))


def logoutAll():
    userInfoLock.acquire()
    for user in userInfo:
        userInfo[user]["loggedin"] = "none"
    userInfoLock.release()

def isLoggedIn(username):
    userInfoLock.acquire()
    if userInfo[username]["loggedin"] != "none":
        userInfoLock.release()
        return True
    else:
        userInfoLock.release()
        return False


def correctPassword(username, password):
    userInfoLock.acquire()
    if userInfo[username]["password"] == password:
        userInfoLock.release()
        return True
    else:
        userInfoLock.release()
        return False


def getTimeStamp():
    timeStamp = time.time()
    return timeStamp


def checkTimeDiff(timeStamps, ipUsername):
    diff = timeStamps[2] - timeStamps[0]
    if diff <= 30.0:
        tempBlockUser(ipUsername)


def tempBlockUser(ipUsername):
    ipUserBlockedLock.acquire()
    ipUserBlocked.append(ipUsername)
    ipUserBlockedLock.release()
    print("{} blocked".format(ipUsername))


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

        

def motd(clientConn):
    #clientConn.send(motd.encode())
    pass

def broadcast(msg):
    for user in userInfo:
        userInfoLock.acquire()
        if userInfo[user]["loggedin"] != "none":
            ipPort = userInfo[user]["loggedin"].split(":")
            userInfoLock.release()
            ip = ipPort[0]
            port = int(ipPort[1])
            sendMsgSock = socket(AF_INET, SOCK_STREAM)
            sendMsgSock.connect( (ip, port) )
            sendMsgSock.send(msg.encode())
            sendMsgSock.close()
        else:
            userInfoLock.release()
        

def tell(toTell, msg, username):
    if isLoggedIn(toTell): 
        ipPort = userInfo[toTell]["loggedin"].split(":")
        ip = ipPort[0]
        port = int(ipPort[1])

        msg = "(DM){}: {}\n".format(username, msg)
        sendMsgSock = socket(AF_INET, SOCK_STREAM)
        sendMsgSock.connect( (ip, port) )
        sendMsgSock.send(msg.encode())
        sendMsgSock.close()
    else:
        userInfo[toTell]["mail"].append(msg)

def help_():
    return


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
                msg = "0\n"
                clientConn.send(msg.encode())
                continue

            elif userExists(username):
                # can't login if you are blocked
                # if blocking time has passed you will be unblocked here
                if isBlocked(clientIP, username):
                    msg = "0\n"
                    clientConn.send(msg.encode())
                    continue
                elif isLoggedIn(username):
                    print("already logged")
                    msg = "0\n"
                    clientConn.send(msg.encode())
                    continue
                else:
                    if not correctPassword(username, password):
                        print("bad attempt")
                        msg = "0\n"
                        clientConn.send(msg.encode())
                        badPasswordAttempt(clientIP, username)
                        continue
            else:
                createUser(username, password)
            # verification success 
            # login user
            # send confirmation code to client and begin listening for messages
            msg = "1\n"
            clientConn.send(msg.encode())
            login(username,clientAddrListen)
            verifyingUser = False
        # while user is connected receive messages and commands
        participating = True
        while participating:
            incoming = getLine(clientConn).rstrip()
            if incoming.startswith("/"):
                command = incoming.split()[0][1:]
                if command == "exit":
                    participating = False
                elif command == "tell":
                    try:
                        restOfMsg = incoming[6:]
                        toTell = restOfMsg.split()[0]
                        msg = restOfMsg[len(toTell)+1:]
                        tell(toTell, msg, username)
                    except:
                        help_(clientConn)
                    
            else:
                msg = "{}: {}\n".format(username, incoming)
                broadcast(msg)

    # handle diconnects         
    except Exception:
       print("Exception occurred, closing connection")
    clientConn.close()
    logout(username)
            
# Listen for users to join the server
running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    # When server closes save data and log everyone out
    except KeyboardInterrupt:
        logoutAll()
        saveUserInfo()
        print('\n[Shutting down]')
        running = False
