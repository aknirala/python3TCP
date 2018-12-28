#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import socket
import selectors
import types
import time
import random
sel = selectors.DefaultSelector()

msgStart = "crrrazy_msg_START"
msgEnd = "crrrazy_msg_END"
verbose = False


# In[ ]:


def start_connections(host, port):
    server_addr = (host, port)
    print("\n\nstarting connection to", server_addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(server_addr)    #connect_ex() is used instead of connect() since connect() would immediately raise a BlockingIOError exception. connect_ex() initially returns an error indicator, errno.EINPROGRESS, instead of raising an exception while the connection is in progress.
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    data = types.SimpleNamespace(
        #connid=connid,  #In case multiple connections are made from same machine
        #                  we can assign an ID to them.
        #Other fields, if other protocols like fixed message lengths etc needs to be
        #used then more variables could be added here to keep track of those.
        inb="", #Not a binary stream as it will be easier to handle str
    )
    sel.register(sock, events, data=data)


# In[ ]:


tempTaskID = None
def sendRecv(sel, tS = {}, recv = True, disconnect = False):
    '''
    This function is written in such a way that one can send a message to server 
    and server will send a return message and the function will return that. 
    
    Since the function may wait endlessly if server does not return it, after some
    delay, we are assuming that server didn't listened, so we are resending the message.
    This is not an ideal solution, as server might get the message again and falsely 
    assume that task has been done. This can be fixed by providing unique key to each job,
    and IMHO must be done in actual code.

    sel: contains the connection to server.
    tS: dictionary to send. By default it is empty, which in our case we consider as 
        blank message.
    recv: a flag to indicate, if we are expecting a return message from server.
          In our case, this will always be True.
    disconnect: When True, this function will close the connection.
    '''
    global msgStart
    global msgEnd
    global tempTaskID
    global verbose
    waitAttempts = 0
    while True:
        events = sel.select(timeout=1)
        if events:
            toProcess = True        #To ensure that there is only one connection
            #                         If everything goes correctly we don't need this.
            #                         and ideally code involving this shouldnot run.
            #                         Thus all code involving this could be removed,
            for key, mask in events: #Idealy we should have just one value in events.
                sock = key.fileobj
                data = key.data
                if not toProcess:
                    print('Repeated!!!!! ', key.index, ' closing it.')
                    print('THIS SHOULD NOT HAVE BEEN EXECUTED. But what can we say...')
                    sel.unregister(sock)
                    sock.close()
                    print('Disconnected extra socket.')
                    continue
                toProcess = False
                if disconnect:  #This time function hsa been called to disconnect the connection.
                    #           Please note, in case we would have been managing multiple 
                    #           connections, this would have been added to data when calling
                    #           SimpleNamespace while registering, so that we know which socket
                    #           to close.
                    sel.unregister(sock)
                    sock.close()
                    print('Disconnected')
                    return {}
                msg = msgStart + str(tS) + msgEnd
                toSend = str.encode(msg) 
                if waitAttempts <= 0:  #It'll not send again till waitAttempts becomes less
                    #                   This is added in case, server does not recieve the message
                    #                   for the first time. So after waiting for few times
                    #                   ,in our case 10 seconds, as done by sleep in each iteration
                    #                   we'll resend the message.
                    #                   In practice, this could even happen when message from server
                    #                  is lost, thus a better mechanism to detect that should be there
                    while len(toSend) > 0:
                        if mask & selectors.EVENT_WRITE:
                            sent = sock.send(toSend)
                            if verbose:
                                print('sent: ',sent, 'From: ',sock.getsockname(),' Cont: ',toSend[:sent])
                            toSend = toSend[sent:]
                        else:
                            print('Not ready to write!!. THIS SHOULD NOT HAVE HAPPENED, but what do I know..')
                            time.sleep(0.0001)
                    waitAttempts = 10  #Try again after these many iterations of outer while
                else:
                    waitAttempts -= 1
                if not recv:           #Return not expected.
                    return {}
                if verbose:
                    print('wtoR...', end=' ')#For illustration we are SoPing 
                #                        wtoR: waiting to READ.
                msg = ''
                if mask & selectors.EVENT_READ:
                    recv_data = sock.recv(1024)  # Should be ready to read
                    if recv_data:
                        data.inb += recv_data.decode()
                    #print('Now we got:::: ',data.outb,' len: ',len(data.outb), 'and find: ',data.outb.find(msgEnd))
                else:
                    if verbose:
                        print('NotR..', end=' ')#For illustration we are SoPing 
                    #                        NotR: Not ready to READ. (Waiting for server to send message)
                    time.sleep(1)  #By giving delay here we will wait for 10 seconds for 
                    #              server to reply.
                eI = data.inb.find(msgEnd)
                if eI >= 0:
                    sI = data.inb.find(msgStart)
                    if sI < 0 or sI > eI: #Ideally throw an exception here.
                        sI = 0
                    else:
                        sI += len(msgStart)
                    msg = data.inb[sI:eI]
                    if len(msg) <= 0:
                        print('ERROR, this definitely looks like a protocol failure. Terminating connection, by returning -1')
                        #We are expecting that server must alway reply an integer eithre
                        #representing taskID or -1 to terminate.
                        return -1
                    data.inb = data.inb[eI + len(msgEnd):] #Simply removing the part
                    #        of the message we have processed. In this case, if everything
                    #        is as planned, this should always set data.inb to empty string.
                    try:
                        return int(msg)
                    except:
                        print('Integer not returned. Val return is:',msg,'. Protocol break.')
                        return -1
                else:
                    if verbose:
                        print('No end on: ',  data.inb, end='')
        else:
            print('No events!!! THIS SHOULD NOT HAPPEN...')
        if not sel.get_map():
            print('It\'s likely that no socket is opened OR server is not there.')
            break
    return {}


# In[ ]:


host, port = "<<ENTER YOUR SERVER IP>>", 65432#sys.argv[1:4]
start_connections(host, int(port))


# In[ ]:


d = sendRecv(sel)
while True:
    if d <0:
        if d == -2:
            print('d is: ',d)
            time.sleep(0.5)
            d = sendRecv(sel)
            continue
        sendRecv(sel, disconnect=True)
        print('Disconnected as server said target achieved',d)
        break
    tS = {}
    tS[d] = random.randint(1,2) #Random number between 1 and 2
    print('Sending: ',tS)
    d = sendRecv(sel, tS)


# In[ ]:


#sendRecv(sel, disconnect=True)


# In[ ]:




