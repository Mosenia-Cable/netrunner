import asyncio
import socketio
import json
import logging, coloredlogs
import os
from watchfiles import awatch
import time

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
async def heartbeats():
    try:
        with open("misc.conf", "r") as misc_f:
            config = json.load(misc_f)
            misc_f.close()
        heartbeat_settings = config.get("ts_heartbeats", {})
        enabled = heartbeat_settings.get("enabled", False)
        frequency_seconds = heartbeat_settings.get("frequency", 60)
        if enabled:
            log.debug(f"Timestamp heartbeats are enabled, beginning background task to write heartbeats every {frequency_seconds} seconds.")
            i = 0
            while True:
                i += 1
                packet = {
                    "function": "HEARTBEAT",
                    "args": [time.time()] # write the time here for as little cycle latency as possible
                }
                await send_packet(packet=packet)
                log.debug(f"Sent HEARTBEAT packet. (Packet no. {i})")
                await asyncio.sleep(frequency_seconds) # asyncio needed to not hold main thread
    except:
        log.error(f"Failed to check miscellaneous configuration.")
        

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