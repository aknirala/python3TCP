#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import socket    #For TCP communication.
import types     #For types.SimpleNamespace
import selectors #For selectors.DefaultSelector()

import time
import random


# In[ ]:


totalTasks = 30
repAllTasks = 10
d = {}
for i in range(totalTasks):
    d[i] = 0
msgStart = "crrrazy_msg_START"
msgEnd = "crrrazy_msg_END" #Hoping that this will not be in the message.
verbose = False
#Instead of having start and end tokens, a better way is to have headers which will 
#have size of the message.


# In[ ]:


sel = selectors.DefaultSelector()


# In[ ]:


def accept_wrapper(sock):
    '''
    This function will accept the new clients, and will register them.
    '''
    conn, addr = sock.accept()
    print("\n\n accepted connection from", addr)
    conn.setblocking(False)   #If we want multiple clients we need to do this.
    #Below we are assigning three things to each clinet connection, if we want more details
    #like, when was the last time clinet communicated we need to pass one more argument here
    # and later, ensure that it gets updated.
    data = types.SimpleNamespace(addr=addr, inb="", outb=b"")
    #Above notice that inb is not binary. This is becasue our code will be simpler
    #if we'll keep it string (as a single message will be recieved over multiple
    #iterations). But we need to convert it from binary stream before appending it there.
    #In server we have made a loop and are senidng data till all is send, so outb can
    #be removed, as it is never used.
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


# In[ ]:


host, port = "<<<ENTER YOUR MACHINE IP>>>", 65432#sys.argv[1], int(sys.argv[2]) #TODO: Chnage to your machine IP
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)


# In[ ]:


underProcess = {}
for i in range(totalTasks):
    underProcess[i] = 0
ctr = 0
lastRetCtr = 0
def getNextTask(tD):
    '''
    tD is a dictionary which has, key values of taskID and units which has been completed.
    This function will update the d, accordingly and will then return the next taskID to be done
    if tD is None, we are just checking what is the next value to be returned, so no actual 
    changes are made to any variable.
    '''
    global d
    global underProcess
    global repAllTasks
    global ctr
    global lastRetCtr
    #print('Got tD as: ',tD)
    #Updating the task dictionary d, and also removing that from underProcess
    if tD is not None:
        for k in tD:
            underProcess[k] -= 1
            d[k] += tD[k]
            lastRetCtr += 1
            ctr = lastRetCtr
    for k in d:
        if d[k] + underProcess[k] < repAllTasks:
            if tD is not None:
                underProcess[k] += 1
            return k
    for k in underProcess:
        if underProcess[k] > 0:
            #print('k:',k,'underProcess[k]: ',underProcess[k], ' ctr: ',ctr, 'lastRetCtr: ',lastRetCtr)
            if tD is not None:
                ctr += 1
            if ctr - lastRetCtr > 10: #This is just a simple mechanism to resend stuff
                #               when some unprocess task has not been done.
                #               If till 10 iterations no client returns then it will 
                #               resend the task (not an ideal mechanism)
                if ctr - lastRetCtr > 15:
                    ctr = lastRetCtr
                print('Returning: ',k)
                return k
            else:
                if tD is not None:
                    time.sleep(1)
                return -2
    return -1
        


# In[ ]:


tmpGlobalMsg = ""  #These two are defined global coz I don't know how to work with
tmpGlobalTD = None #exec with local variables. :-( Let me know how to get rid of them
ctr = 0
def service_connection(key, mask):
    #print('In service_connection')
    global d        
    global msgStart
    global msgEnd
    global tmpGlobalMsg
    global tmpGlobalTD
    global ctr
    global verbose
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ: 
        recv_data = sock.recv(1024)  
        if recv_data:
            data.inb += recv_data.decode()
            eI = data.inb.find(msgEnd)  #Is the end str found? If so we have recievd entire message
            if eI >= 0:
                sI = data.inb.find(msgStart)
                if sI < 0 or sI > eI: #Ideally throw an exception here.
                    sI = 0
                else:
                    sI += len(msgStart)
                msg = data.inb[sI:eI]
                data.inb = data.inb[eI + len(msgEnd):]
                tmpGlobalTD = None
                msg = 'tmpGlobalTD = '+msg
                exec(msg,  locals(), globals())
                #Below, we update, how much unit of task has been done by client
                nJob = getNextTask(tmpGlobalTD)
                print('From : ',sock.getpeername(), 'nJob is: ', nJob)
                toSend = msgStart + str(nJob) + msgEnd
                toSend = str.encode(toSend)  #We need to encode it befre sending
                while len(toSend) > 0:
                    if mask & selectors.EVENT_WRITE:
                        sent = sock.send(toSend)
                        toSend = toSend[sent:]
                        if verbose:
                            print('Sent: ',sent)
                    else:   #Not needed could be removed.
                        print('Not ready to send!!!! THIS SHOULD NOT HAPPEN (But who knows!!)')
                        time.sleep(0.0001)
        else:  #This will be true when client will close connection. We can even set
            print("\n\n closing connection to", data.addr)    # a timer here.
            sel.unregister(sock)
            sock.close()
    else:
        if verbose:
            time.sleep(0.2) #So that output is not flooded
            print('Not read ready !!!!', end=" ") #Thre are clients which have registerd
        #                            But no one has sent anything for the server to read.


# In[ ]:


while True:
    events = sel.select(timeout=None)
    if verbose:
        sleepT = 1 - len(events)*0.1
        if sleepT <= 0:
            sleepT = 0.01
        time.sleep(sleepT)
        print('NUmber of clinets is: ',len(events))
    for key, mask in events:
        if key.data is None:
            accept_wrapper(key.fileobj)
        else:
            service_connection(key, mask)
    nT = getNextTask(None)
    if nT < 0:
        if nT == -2:
            print('Status: ',underProcess)
            time.sleep(1)
            continue
        print('All done.underProcess ', underProcess)
        for key, mask in events:
            data = key.data
            sock = key.fileobj
            print("\n\n closing connection to", data.addr)    # a timer here.
            sel.unregister(sock)
            sock.close()
        break

