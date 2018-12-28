# python3TCP
A simple code to demonstrate communication over TCP in python3

### Consider this toy problem:
Say we have 1000 different type of tasks. Each tasks needs to be executed at least 10 times. Since execution of one task takes a huge amount of time (say parsing a sentence, which can take 100s of milliseconds), we would like to parallelize it. We’ll simulate the tasks as:
Each task is represented by it’s ID: 0 to 999.
To keep track of count of each tasks we’ll use a hashmap, with key as taskID and value as number of times the tasks has been executed.

### Communication between client and server will be done as:
- Server will listen to a port.
- Clients will connect to the server.
- For first run they will send an empty hashmap.
- To which server will pass a key.
- Client will do 1 or 2 units of job and will return that as a hashmap. So if say taskID 11 is passed, and client choose to do 2 units of job it will return {11:2}.
- Server will then increment units of job done (in the above case 2) to respective taskID (which is 11), and will send a new taskID.
- If taskID is sent as negative client will disconnect. This will happen when all the tasks has been completed.
- -2 is reserved for waiting. This may happen at the end, when server may choose to send the task again to available clients (as previous clients didn’t returned for whatsoever reason)

### Some more details:
- Clients will wait for few seconds to simulate the time taken to finish the task.
- One can create as many clients as one wants (I hope, tested with 6 clients), and can disconnect them at any time. If server will not be get a response for a task for long time, it will assign that task to some other client.
- At client side: It is possible that a single client have multiple connections to server. In that case events list returned will have more than one event. In our case if everything goes well, they will have single events, as we are making only single connection.
- At client side: However, if say for some reasons we terminate the code but socket is not closed, and then we re-run it then events will have multiple events. (in that case we’ll keep the first and close the rest)
- At server side ideally, after a threshold we should close the connection, else server can wait endlessly for a client which has not closed the socket.
- Since a lot of things can go wrong while communicating, and also we are reading in buffers of 1024, it is likely that we won’t get the entire message once. Thus at application layer (which is our code), we’ll be adding a start and end values. It is entirely possible that our message is broken down to single bytes. However TCP ensure that order in which data will arrive will be correct.
- If your client and server are running on multiple machine, ensure that you have opened the port (in this case it is 65432)

### We have code as:
- myServer.py: Only one instance of the code will run on a single machine.
- myClient.py: Many instances of code will run on many machine (a single machine can also run multiple instances), which can run different operating systems as well.
