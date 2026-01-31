# -*- coding:utf-8 -*-
# @Desc: None
ENABLE_EXP_SHADOWING = True

# =====IP address=========
IP_ROBOT = '10.6.38.25'   # dynamic ip of the robot
IP_LOCAL_SERVER = '10.6.32.239'  
# # face_detect_addr = f'tcp://{ip}:6666'   # face detection result from Ameca
# VSUB_ADDR = f'tcp://{IP_ROBOT}:5000'  # From Ameca, 5000: mjpeg
VPUB_PORT = 5556
VSUB_ADDR = f'tcp://{IP_LOCAL_SERVER}:{VPUB_PORT}'  # subscribe video data from my own local server (flask)

CVPUB_ADDR = f'tcp://*:6666'  # publish the inferenced ctrl values to the robot
TASK_DEALER_ADDR = f'tcp://{IP_ROBOT}:2016' #'tcp://10.126.110.67:2006'
# # vsub_mjpeg_addr = f'tcp://{ip}:5000'  # mjpeg From Ameca
# =========================

DEBUG = False  # whether in debug mode or not
FRAME_BUFF_MAX_LEN = 640

DIAG_BUFF_MAX_LEN = 8  # 20
TARGET_SIZE = 160
PRETRAINED_PATH = 'princeton-nlp/sup-simcse-roberta-large'

MAX_FACES = 100
MAX_FRAMES = 100

# face recognition
# try matching face using the newest {face_reg_try_cnt} frames
FACE_REC_TRY_CNT = 10 * 3



class HieraConf:
	hiera_temp_stride = 4
	n_infer_clips = 4        # number of clips for inference
	n_frames_per_clip = 16   # TODO 16 , no sampling with stride 4 first
	n_frames_per_video = 64  # 16 * 4
	input_size = (16, 224, 224)
	input_interp_mode = 'trilinear'


GPT_MODEL_NAME = 'gpt-3.5-turbo-instruct'

# action generation
BASE_PROMPT = """
cadidate_poses = [
  'EXP_neutral', 'eyelids_close', 'eyelids_open', 'eyelids_squeeze', 'eyelids_top_down', 'eyelids_wide',
  'HB3_Face_Neutral', 'Lip Corner Smile', 'Mouth Anger', 'Mouth Disgust', 'Mouth Fear', 'Mouth Happy',
  'Mouth Huh', 'Mouth Joy', 'Mouth Open', 'Mouth Sad', 'Mouth Smile', 'Mouth Sneer', 'Mouth Surprise',
  'Mouth Worried','AU4 Jaw Speaking', 'Mouth Neutral', 'AU1 Nose Neutral', 'AU1 Nose Wrinkler'
]
# when the user is reading book
robot.apply_poses(['Mouth Smile', 'eyelids_open']).

# when the user is whistling
robot.apply_poses(['Mouth Surprise', 'eyelids_open']).

# when the user is waiting in line
robot.apply_poses(['Mouth Huh', 'eyelids_close']).
"""

class ChatMode:
	QA = 0     # default mode
	VLE = 1    # vision language to facial expression in human-robot conversation




