# -*- coding:utf-8 -*-
# @Desc: perform facial expression shadowing for Ameca
import os
import os.path as osp
import tyro
import subprocess
import time
import sys
from pathlib import Path
CUR_DIR = Path(__file__).resolve().parent
sys.path.append(osp.join(CUR_DIR, '../'))
from custommodels.modules.liveportrait_configs.argument_config import ArgumentConfig
from custommodels.modules.liveportrait_configs.inference_config import InferenceConfig
from custommodels.modules.liveportrait_configs.crop_config import CropConfig
from custommodels.modules.exp_shadowing_pipeline import ExpShadowPipeline


from utils.datautils import clamp_ctrl_values, concat_frames, images2video


def partial_fields(target_class, kwargs):
	return target_class(**{k: v for k, v in kwargs.items() if hasattr(target_class, k)})

debug_cvs = [[0.54288,0.51821,0.49966,0.53313,1.07417,1.14752,0.86507,0.77793,0.01949,0.04524,-2.50785,0.73429,-6.1531,0.97179,0.46319,0.48876,0.45395,0.42976,0.36852,0.54123,0.56361,0.49633,0.49497,0.3783,0.49209,0.50636,0.51976,-0.88375,0.0694,0.05347],
[0.53646,0.50397,0.50846,0.52722,1.05202,1.09831,0.75169,0.65395,0.03168,-0.06057,-3.03183,0.79451,-6.47336,0.96346,0.44274,0.49266,0.45562,0.41635,0.38101,0.52043,0.54841,0.48679,0.48448,0.38484,0.5031,0.5158,0.53229,-1.01342,0.07298,0.01779],
[0.51167,0.42284,0.5312,0.58715,1.06249,1.10894,0.88275,0.61487,-0.04062,0.01402,-4.85258,2.11757,-6.25772,0.96936,0.45296,0.4992,0.47061,0.41329,0.4047,0.53013,0.54684,0.49627,0.49262,0.39583,0.53874,0.53763,0.56662,-1.11135,0.05841,0.05518],
[0.54139,0.4501,0.58946,0.62264,0.86685,0.92457,0.90235,0.62354,-0.17154,0.00936,-5.77016,2.32005,-7.87279,0.95799,0.46654,0.51409,0.48238,0.39718,0.42436,0.52123,0.53761,0.49124,0.48906,0.40921,0.56623,0.54783,0.58378,-1.00422,0.13049,0.07513],
[0.56546,0.44246,0.59383,0.62433,0.84229,0.93198,0.90284,0.67932,-0.02581,0.13676,-6.30352,2.68802,-8.15394,0.94153,0.45831,0.52495,0.48391,0.39544,0.42057,0.52587,0.53239,0.49604,0.49117,0.40666,0.56617,0.53907,0.57339,-0.80489,0.12572,0.08218],
]

class ExpressionShadow:
	def __init__(self):
		super().__init__()
		tyro.extras.set_accent_color("bright_cyan")
		args = tyro.cli(ArgumentConfig)
		args.output_dir = '/home/penny/pycharmprojects/assets/animations2'
		inference_cfg = partial_fields(InferenceConfig, args.__dict__)
		crop_cfg = partial_fields(CropConfig, args.__dict__)
		inference_cfg.checkpoint_G = '/home/penny/pycharmprojects/humanoidexpgen/checkpoints/train_spade/4_net_G.pth'

		self.exp_shadowing_pipeline = ExpShadowPipeline(inference_cfg, crop_cfg)
		self.dummy_cvs = [[str(v) for v in vals] for vals in debug_cvs]
		self.cur_idx = 0
		self.debug_fb_len = len(self.exp_shadowing_pipeline.frame_buffer)
		self.cropped_drivings = []
		self.animated_frames = []
		# self.ctrl_values = []
		# self.exp_shadowing_pipeline.set_dring_ref_motion(self.exp_shadowing_pipeline.frame_buffer[4])
   
   
 
	async def on_exp_shadowing(self, frame:bytes, metadata: tuple):  # (frm_sent_ts, frm_arrive_ts)
	# def on_exp_shadowing(self, frame:bytes):
		# ================↓↓↓debug↓↓↓==================
		# if self.exp_shadowing_pipeline.driving_ref_motion is None:  
		#     frame = self.exp_shadowing_pipeline.frame_buffer[4]
		# else:
		# frame = self.exp_shadowing_pipeline.frame_buffer[self.cur_idx%self.debug_fb_len]
		# self.cur_idx += 1
		# ================↑↑↑debug↑↑↑==================
		# print(f'execution time: {time.time()}')
		# ctrl_values, cropped_driving, parsed_out = self.exp_shadowing_pipeline.execute(frame)
		ctrl_values, ts_prepare = self.exp_shadowing_pipeline.execute(frame)
		if ctrl_values is None:
			return None, metadata + (str(ts_prepare), str(time.time()))
		ctrl_values = clamp_ctrl_values(ctrl_values.tolist())

		line_str = ','.join([str(round(t, 5)) for t in ctrl_values])
		line_str = '[' + line_str + '],'
		# print(line_str)
		# len_cropped_driving = len(self.cropped_drivings)
		# if len_cropped_driving <= 240:
		# 	self.cropped_drivings.append(cropped_driving)
		# 	self.animated_frames.append(parsed_out)
		# if len_cropped_driving == 240:
		# 	# images2video(self.cropped_drivings, 'cropped_driving.mp4')
		# 	# images2video(self.animated_frames, 'animated_frames.mp4')
		# 	concat_frames(self.cropped_drivings, self.animated_frames)
			
		# print(f'***************\n len animated frames: {len(self.cropped_drivings)}, {len(self.animated_frames)} \n *************')
		new_meta = metadata + (str(ts_prepare), str(time.time()))
		return [str(v) for v in ctrl_values], new_meta
		# idx = int(time.time())%5
		# return self.dummy_cvs[idx]   # Penny DEBUG
		# ctrl_values = await self.cv_inference_pipeline.execute(frame)
		# return ctrl_values


exp_shadow = ExpressionShadow()

if __name__ == "__main__":
	frame = exp_shadow.exp_shadowing_pipeline.frame_buffer[0]
	cvs = exp_shadow.on_exp_shadowing(frame)
	print(f'cvs: {cvs}')
