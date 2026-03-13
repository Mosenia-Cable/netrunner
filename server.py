import socketio
import json
import logging, coloredlogs
import os
from watchfiles import awatch

log = logging.getLogger("netrunner server")
log.setLevel(logging.DEBUG)
coloredlogs.install(level="DEBUG", logger=log)

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')  # For cross-origin
app = socketio.ASGIApp(sio)

def clear_outbox_cache():
    with open("outboxes.conf", "r") as conf_f:
        config = json.load(conf_f)
        monitored_paths = config.get("monitored", [])
    for path in monitored_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                if len(os.listdir(path)) > 0:
                    for file in os.listdir(path):
                        fpath = os.path.join(path, file)
                        os.remove(fpath)
                    log.debug(f"Cleared old packets from '{path}'")
    
    
@sio.event
async def connect(sid, environ, auth):
    log.info(f"Client connected: {sid}")
    
@sio.event
async def disconnect(sid):
    log.info(f"Client disconnected: {sid}")

@sio.event
async def message(sid, data):
    log.info(f"Received message from {sid}: {data}")

async def send_packet(packet:dict):
    socketmessage = f'{packet}'
    #log.debug(socketmessage)
    await sio.emit(data=str(socketmessage),event='inbound_packet')
    log.info(f"Sent socket packet: {socketmessage}")

@sio.start_background_task
async def outbox_watcher():

    with open("outboxes.conf", "r") as conf_f:
        config = json.load(conf_f)
        monitored_paths = config.get("monitored", [])

    async for changes in awatch(*monitored_paths):
        for change, path in changes:
            if change.name == "added": # process new only
                log.debug(f"Detected new file: {path}")
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    log.debug(f"Loaded message: {data}")
                    # send to clients
                    await send_packet(data)
                    os.remove(path)
                except Exception as e:
                    log.error(f"Error processing {path}: {e}")


if __name__ == "__main__":
    clear_outbox_cache()
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=4000, reload=False, access_log=True)