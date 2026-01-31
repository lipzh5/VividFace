# -*- coding:utf-8 -*-
# @Desc: None
import time
import os
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ["TORCH_DISTRIBUTED_DEBUG"] = "DETAIL"
from conf import *
from const import *

from flask import Flask, Response, request
import zmq
from zmq.asyncio import Context

import threading

import asyncio
from subrouter import SubPub, on_exp_shadowing_task

app = Flask(__name__)
frame_data = None

@app.route('/')
def index():
	return "<h1>Hello! The Flask server is running.</h1>"


@app.route('/stream', methods=['POST'])
def stream():
	global frame_data
	frame_data = request.data
	# print(f'frame data: {type(frame_data)}')
	return "OK"


WRITE_FILE_INTERVAL = 605   # WRITE EVERY 10 min

ctx = Context.instance()
pub_sock = ctx.socket(zmq.PUB)
pub_sock.bind("tcp://*:6666")  # Publishes to clients


time_stamps = []

def write_ts_to_file():
	global time_stamps
	now = time.time()

	with open(f'timestamps_stage_{now}.txt', 'w') as f:
		for frm_arrive, frm_prepare, cv_arrive, rtt_end in time_stamps:
			f.write(f'{frm_arrive}, {frm_prepare}, {cv_arrive}, {rtt_end} \n')
	print('write files done!!!')


async def pub_cvs():
	global frame_data
	start_time = time.time()
	# try:
	while True:
		now = time.time()
		resp_code, cv_list, metadata = await on_exp_shadowing_task(frame_data, metadata=(str(now),))
		frame_data = None
		# self.time_stamps.append(metadata)
		if resp_code == ResponseCode.Success:
			# print(f'send ctrl values: {time.time()}')
			encoded = [val.encode(ENCODING) for val in cv_list]   # time send
			# print(f'metadata: {metadata}')
			# print(f'len cv list: {cv_list}')
			await pub_sock.send_multipart(encoded)
			time_stamps.append(metadata + (str(time.time()),))
			# print(f'timestamps: {time_stamps[-1]}')

		# Penny NOTE: if using liveportrait original cropping algorithm (slow), then need to sleep a little bit
		# to avoid the Assertion failed: !_more (src/fq.cpp:80) Aborted (core dumped)
		await asyncio.sleep(0.001) # 

		if time.time() - start_time > WRITE_FILE_INTERVAL:
			write_ts_to_file()
			start_time = time.time()

	# except Exception as e:
	# 	print(str(e))



def run():
	sub_pub = SubPub()
	asyncio.run(sub_pub.sub_vcap_pub_cvs())


def start_asyncio_loop():
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	loop.run_until_complete(pub_cvs())



if __name__ == "__main__":
	threading.Thread(target=start_asyncio_loop, daemon=True).start()
	app.run(host='0.0.0.0', port=5000)
	# run()
	