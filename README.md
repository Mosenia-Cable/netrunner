# netrunner
This is an overly simplified client-server socket stack intended to replace the deprecated MQTT command feed for 4broadcast. The goal of the stack is to deliver function commands and supplied arguments to listening clients for manipulation of other IoT softwares.

The server script listens to paths defined in outboxes.conf for new files. These files must be in JSON format.

The receiver script connects to the server and listens for inbound packets. The received packet is checked for valid JSON, and if the dict contains a key for "function" it is considered a valid packet. The provided string for "function" is then checked in the internal FUNCTIONS dict, where that string will be mapped to a callable function by an external Python program. If a callable function is found, it is started in a threading.Thread.


Again, this is some serious boilerplate code. This is in active development.