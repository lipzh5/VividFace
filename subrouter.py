# -*- coding:utf-8 -*-
# @Desc: None
import sys
# print(f'sys.path: {sys.path}')
import asyncio
# import io
from io import BytesIO
import os

import zmq
import zmq.asyncio
from zmq.asyncio import Context
from utils.framebuffer import frame_buffer
from custommodels.exp_shadowing import exp_shadow

# from LanguageModels.ChatModels import generate_ans, llama_to_cpu (penny note: use gpt-4o for answer polish instead)
# from LanguageModels.RAG.main import RAGInfo  # for mq stuff training
from conf import *
from const import *
import time
import base64
from PIL import Image
import os.path as osp
import logging
log = logging.getLogger(__name__)
# rag_info = RAGInfo(use_public_embedding=True, top_k=3)

# conda activate amecabackend
# torchrun --nproc_per_node 1 AmecaSubRouter.py

# note: video capture needs configure video_capture node as follows
'''
{
  "data_address": "tcp://0.0.0.0:5001",
  "mjpeg_address": "tcp://0.0.0.0:5000",
  "sensor_name": "Left Eye Camera",
  "video_device": "/dev/eyeball_camera_left",
  "video_height": 720,
  "video_width": 1280
}
'''

# ip = '10.6.36.39'   # dynamic ip of the robot
# # face_detect_addr = f'tcp://{ip}:6666'   # face detection result from Ameca
# vsub_addr = f'tcp://{ip}:5000'  # From Ameca, 5000: mjpeg
# vtask_deal_addr = f'tcp://{ip}:2017' #'tcp://10.126.110.67:2006'
# # vsub_mjpeg_addr = f'tcp://{ip}:5000'  # mjpeg From Ameca
WRITE_FILE_INTERVAL = 605   # WRITE EVERY 10 min


ctx = Context.instance()


async def on_exp_shadowing_task(frame, metadata):  # metadata = (ts_sent: str, ts_arrive: str)
	# frame = frame_buffer.consume_one_frame()
	# frame = frame_buffer.buffer_content[-1]
	if not frame:
		return ResponseCode.Fail, None, metadata + (str(time.time()), )
	try:
		cv_list, metadata = await exp_shadow.on_exp_shadowing(frame, metadata)
		if cv_list is None:
			return ResponseCode.KeepSilent, None, metadata
		return ResponseCode.Success, cv_list, metadata # [0.005, 0.3335, ...]
	except Exception as e:
		print(str(e))
		print(f'=====================')
		import traceback
		traceback.print_stack()
		return ResponseCode.Fail, None, metadata
	


class SubPub:
	def __init__(self):
		super().__init__()
		self.sub_sock = ctx.socket(zmq.SUB)
		self.sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
		# self.sub_sock.setsockopt(zmq.CONFLATE, 1)
		self.sub_sock.connect(VSUB_ADDR)

		self.pub_sock = ctx.socket(zmq.PUB)
		self.pub_sock.bind("tcp://*:6666")  # Publishes to clients
		self.time_stamps = []  # (frm_sent_ts, frm_arrive_ts, cv_inferred_ts)
		# self.ts_frames = []  # time stamps for frame receiving
		# self.ts_cvs = []     # tiem stamps for control value receiving
		self.time_start = time.time()
	
	def write_ts_to_files(self):
		now = time.time()

		with open(f'timestamps_{now}.txt', 'w') as f:
			for ts_send, ts_arrive, ts_cv in self.time_stamps:
				f.write(f'{ts_send}, {ts_arrive}, {ts_cv} \n')
		# ts_cvs = [str(ts) for ts in self.ts_cvs]
		# with open(f'ts_cvs_{now}.txt', 'w') as f:
		# 	for s in ts_cvs:
		# 		f.write(f'{s}\n')
		print(f'write files done!!!')
			

	async def debug_save_frame(self, frame_data: bytes):
		img = Image.open(BytesIO(frame_data))
		# img = Image.frombytes('RGB', IMG_SIZE, frame_data)
		img_dir = 'Assets/debug_imgs'
		if not osp.exists(img_dir):
			os.makedirs(img_dir)
		img.save(osp.join(img_dir, f'{time.time()}.png' ))

	async def sub_vcap_pub_cvs(self):
		# start_time = 1733097054.5939214 + 60 * 5
		# end_time = 1733097054.5939214 + 60 * 5 + 10
		try:
			while True:
				# metadata, frame = await self.sub_sock.recv_multipart()
				resp = await self.sub_sock.recv_multipart()
				# print(f'type resp: {type(resp)}, {len(resp)}')
				ts_sent, frame = resp
				ts_sent = ts_sent.decode()
				# print(f'type received frame: {type(frame)}, {len(frame)}, {time.time()}')
				# await self.debug_save_frame(frame)
				# frame_buffer.append_content(frame)  # TODO time.time() , img = Image.open(BytesIO(data))
				# print(f'subrouter recvd at: {time.time()}') ~30FPS
				# self.ts_frames.append((ts_sent, time.time()))  # send, arrive
				# print(f'ts send: {ts.decode()}, ts arrive: {time.time()}')
				resp_code, cv_list, metadata = await on_exp_shadowing_task(frame, metadata=(ts_sent, str(time.time())))
				self.time_stamps.append(metadata)
				if resp_code == ResponseCode.Success:
					# print(f'send ctrl values: {time.time()}')
					encoded = [str(time.time()).encode(ENCODING)]   # time send
					encoded.extend([val.encode(ENCODING) for val in cv_list])
					
					await self.pub_sock.send_multipart(encoded)

	
				
				# Penny NOTE: if using liveportrait original cropping algorithm (slow), then need to sleep a little bit
				# to avoid the Assertion failed: !_more (src/fq.cpp:80) Aborted (core dumped)
				await asyncio.sleep(0.005) # 

				if time.time() - self.time_start > WRITE_FILE_INTERVAL:
					self.write_ts_to_files()
					self.time_start = time.time()


		except Exception as e:
			print(str(e))

	async def pub_cvs(self, frame_data):
		# start_time = 1733097054.5939214 + 60 * 5
		# end_time = 1733097054.5939214 + 60 * 5 + 10
		try:
			while True:
				now = time.time()
				resp_code, cv_list, metadata = await on_exp_shadowing_task(frame_data, metadata=(str(now), str(now)))
				frame_data = None
				self.time_stamps.append(metadata)
				if resp_code == ResponseCode.Success:
					# print(f'send ctrl values: {time.time()}')
					encoded = [str(time.time()).encode(ENCODING)]   # time send
					encoded.extend([val.encode(ENCODING) for val in cv_list])
					
					await self.pub_sock.send_multipart(encoded)

				# Penny NOTE: if using liveportrait original cropping algorithm (slow), then need to sleep a little bit
				# to avoid the Assertion failed: !_more (src/fq.cpp:80) Aborted (core dumped)
				await asyncio.sleep(0.005) # 

				if time.time() - self.time_start > WRITE_FILE_INTERVAL:
					self.write_ts_to_files()
					self.time_start = time.time()


		except Exception as e:
			print(str(e))


# async def run_sub_router():
# 	sub_router = SubPub()
# 	loop = asyncio.get_event_loop()
# 	# await asyncio.gather(task)
# 	task1 = loop.create_task(sub_router.sub_vcap_data())
# 	task2 = loop.create_task(sub_router.route_visual_task())
# 	await asyncio.gather(task1, task2)

if __name__ == "__main__":
	os.environ['TOKENIZERS_PARALLELISM']='false'
	sub_pub = SubPub()
	asyncio.run(sub_pub.sub_vcap_pub_cvs())  # iphone camera to the right




