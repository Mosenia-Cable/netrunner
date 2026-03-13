import socketio
import asyncio
import logging
import threading
import ast

log = logging.getLogger(__name__)

SERVER_ADDRESS = "http://192.168.1.41:4000"
FUNCTIONS = {} # an external program will add functions into this dictionary

sio = socketio.AsyncClient(reconnection=True,reconnection_attempts=0,reconnection_delay=1)

@sio.event
async def connect():
    log.debug("Connected!")
    await sio.send("Hello from client!")

@sio.event
async def disconnect():
    log.debug(f"Disconnected! Waiting to reconnect...")

@sio.event
async def message(data):
    log.debug("Message received:", data)

@sio.event
async def inbound_packet(data):
    try:
        log.debug(data)
        packet = ast.literal_eval(data)
        if isinstance(packet, dict):
            # validate the packet to make sure it's actually a 4pkt packet and not garbage
            function = packet.get("function", None)
            args = packet.get("args", [])
            if not function:
                log.warning(f"Received invalid packet.")
            else:
                log.debug(f"Received valid packet. {function}, args={args}")
                target_function = FUNCTIONS.get(function, None)
                if target_function:
                    if callable(target_function):
                        # this gonna be threaded cus uh god knows what people will do with this
                        t = threading.Thread(target=target_function, args=args)
                        t.start()
                    else:
                        log.warning(f"{function} was defined in FUNCTIONS dict but was not callable!")
                else:
                    log.warning(f"No function defined for {function}.")
        else:
            log.warning(f"Data was not formatted as dict?")
    except:
        log.error(f"Unhandled exception while receiving packet.", exc_info=True)

async def main():
    await sio.connect(SERVER_ADDRESS)
    await sio.wait()

if __name__ == "__main__":
    import coloredlogs
    coloredlogs.install(level="DEBUG")
    asyncio.run(main())