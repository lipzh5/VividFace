from flask import Flask, Response, request
import time
import zmq
import json
from conf import VPUB_PORT

app = Flask(__name__)
frame_data = None

import threading
import asyncio

# ZMQ setup
# context = zmq.Context()
from zmq.asyncio import Context
context = Context.instance()
publisher = context.socket(zmq.PUB)
publisher.bind(f"tcp://*:{VPUB_PORT}")  # Publishes to clients


@app.route('/')
def index():
    return "<h1>Hello! The Flask server is running.</h1>"


@app.route('/stream', methods=['POST'])
def stream():
    global frame_data
    frame_data = request.data
    # print(f'frame data: {type(frame_data)}')
    return "OK"


async def zmq_broadcast():
    global frame_data
    while True:
        if frame_data:
            # Prepare metadata
            metadata = {
                'timestamp': time.time(),
                'length': len(frame_data)
            }

            # Send as multipart: [metadata, raw_frame]
            await publisher.send_multipart([
                # json.dumps(metadata).encode('utf-8'),
                str(time.time()).encode('utf-8'),
                frame_data,
            ])

            frame_data = None  # Reset buffer
        await asyncio.sleep(0.005)  # Avoid CPU hogging

def start_asyncio_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(zmq_broadcast())
    

if __name__ == "__main__":
    threading.Thread(target=start_asyncio_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000) # lsof -i :5000