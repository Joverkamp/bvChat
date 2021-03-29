# [NameServer] Client
from socket import *
from sys import argv
from pathlib import Path
import threading
import os

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

def handleServer(serverSock, listeningPort):
    # what port will we receive messages on
    msg = "{}\n".format(listeningPort)
    serverSock.send(msg.encode())

    # verifying login
    tryingLogin = True
    loginReport = '0'
    try:
        #serverSock, serverAddr = connInfo
        while (tryingLogin == True):
            username = input("Enter username: ") + "\n"
            password = input("Enter your password: ") + "\n"
            serverSock.send(username.encode())
            serverSock.send(password.encode())
            loginReport = getLine(serverSock).rstrip()
            if(loginReport == "badpass"):
                print("Wrong Password, try again.")
            elif(loginReport == "blocked"):
                print("Too many incorrect entries, user blocked.")
            elif(loginReport == "alrlogd"):
                print("That Username is already in use.")
            elif(loginReport == "badinpt"):
                print("Entered input is invalid.")
            elif (loginReport == 'success'):
                print("Welcome to bvChat.")
                tryingLogin = False

        # sending messages to server
        connected = True 
        while connected == True:
            msg = input()
            if inputCheck(msg):
                msg = msg+"\n"
                serverSock.send(msg.encode())
                if msg.rstrip() == "/exit":
                    connected = False
    except Exception:
        pass
    serverSock.close()
    os._exit(0)

def receiveMessage(connInfo):
    clientConn, clientInfo = connInfo
    msg = getLine(clientConn).rstrip()
    print(msg)
    clientConn.close()

def listen(listener):
    #Create a listening socket to receive requests from peers
    listener.listen(4)
    running = True
    while running:
        threading.Thread(target=receiveMessage, args=(listener.accept(),),daemon=True).start()


if __name__ == "__main__":
    # Set server/port from command line
    progname = argv[0]
    if len(argv) != 3:
        print("Usage: python3 {} <IPaddress> <port>".format(progname))
        exit(1)
    serverIP = argv[1]
    serverPort = int(argv[2])

    # Establish connection
    serverSock = socket(AF_INET, SOCK_STREAM)
    serverSock.connect( (serverIP, serverPort) )

    listener = socket(AF_INET, SOCK_STREAM)
    listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    listener.bind(('', 0))
    listeningPort = listener.getsockname()[1]
    # This thread will be for sending messaged with the server
    serverThread = threading.Thread(target=handleServer, args=(serverSock,listeningPort,),daemon=False).start()

    # This thread will be for receiving messages from the server
    listenThread = threading.Thread(target=listen, args=(listener,), daemon=False).start()

#    serverThread.join()
#    listenThread.join()

