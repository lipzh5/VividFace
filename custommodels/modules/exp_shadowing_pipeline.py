# -*- coding:utf-8 -*-
# @Desc: predict control values based on robot's observation
import cv2
import os
import torch
import time
from PIL import Image
import os.path as osp
import numpy as np
from rich.progress import track
# from liveportrait_configs.argument_config import ArgumentConfig
from custommodels.modules.liveportrait_configs.inference_config import InferenceConfig
from custommodels.modules.liveportrait_configs.crop_config import CropConfig
from custommodels.modules.liveportrait_utils.cropper import Cropper
from custommodels.modules.exp_shadowing_wrapper import ExpShadowingWrapper
from custommodels.modules.liveportrait_utils.camera import get_rotation_matrix
from custommodels.modules.liveportrait_utils.io import load_image_rgb, resize_to_limit, load_image_sequences, load_images_from_bytes
from custommodels.modules.liveportrait_utils.rprint import rlog as log
from custommodels.modules.liveportrait_utils.helper import serialize_images, dct2device,  calc_motion_multiplier, basename
from custommodels.modules.liveportrait_utils.video import images2video
# from utils import serialize_images
from io import BytesIO
import imageio.v2 as iio
# from insightface.app import FaceAnalysis
# app = FaceAnalysis(providers=['CPUExecutionProvider', 'CUDAExecutionProvider'])  # 'CUDAExecutionProvider'
# app.prepare(ctx_id=0, det_size=(640, 640))

OUTPUT_FPS = 12
REF_UPDATE_MAX = 100  # update the reference driving motion at most 10 times for one person



class ExpShadowPipeline:
	def __init__(self, inference_cfg: InferenceConfig, crop_cfg: CropConfig):
		self.wrapper = ExpShadowingWrapper(inference_cfg=inference_cfg)
		self.cropper = Cropper(crop_cfg=crop_cfg)
		self.init_source(inference_cfg)
		self.driving_ref_motion = None   # motion info of the first driving frame
		self.driving_ref_kps = None    # transformed keypoints of the first driving frame
		self.motion_multiplier = None
		# debug only
		self.frame_buffer = serialize_images(image_folder='/home/penny/pycharmprojects/AmecaBackend/Assets/debug_imgs_penny')
		self.frame_buffer = self.frame_buffer[:200]
		self.ref_driving_image = None
		self.ref_updated_cnt = 0
		self.force_correct_driving_ref = False


	def init_source(self, inf_cfg: InferenceConfig):
		'''source features are fixed in our application'''
		img_rgb = load_image_rgb(inf_cfg.source)
		img_rgb = resize_to_limit(img_rgb, inf_cfg.source_max_dim, inf_cfg.source_division)
		log(f"Load source image from {inf_cfg.source}")
		# source_lmk = self.cropper.calc_lmk_from_cropped_image(img_rgb)
		img_crop_256x256 = cv2.resize(img_rgb, (256, 256))  # force to resize to 256x256
		img_source = self.wrapper.prepare_source(img_crop_256x256)
		self.source_info = {"feat_3d": self.wrapper.extract_feature_3d(img_source)}
		self.source_info.update(self.extract_motion(img_source))
		
	
	def extract_motion(self, image):
		kp_info = self.wrapper.get_kp_info(image)
		transformed_kps = self.wrapper.transform_keypoint(kp_info)
		rot_matrix = get_rotation_matrix(kp_info['pitch'], kp_info['yaw'], kp_info['roll'])
		# print(f'roll pitch yaw and delta: {kp_info["roll"]}, {kp_info["pitch"]}, {kp_info["yaw"]}')
		# print(f'exp: {kp_info["exp"]}, t: {kp_info["t"]}, {kp_info["scale"]}')
		return {
			"scale": kp_info["scale"], "exp": kp_info["exp"], "t": kp_info["t"],
			"kps": kp_info["kp"], "transformed_kps": transformed_kps, "rot_matrix": rot_matrix}
		# return {"kp_info": kp_info, "transformed_kps": transformed_kps, "rot_matrix": rot_matrix}

	def get_driving_motion_from_frame(self, frame: bytes) -> dict:
		cropped_driving = self.cropper.crop_driving_image(frame) # ndarray: HxWx3 (256, 256)
		if cropped_driving is None:
			return None
		driving_rgb_crop = self.wrapper.prepare_img_rgb(cropped_driving)  # (256, 256, 3)[0, 255], ndarray
		return self.extract_motion(driving_rgb_crop)
	
	def execute(self, frame: bytes) -> torch.Tensor:
		'''excute frame by frame'''
		# driving_ref_updated = False
		this_is_ref_frame = False
		# need_update_driving_ref = False   # wheter to update driving reference frame
		if len(frame) == 0:
			return None, time.time()
		ts = time.time()
		# =======↓↓↓crop using original algorithm↓↓↓===========
		nparr = np.frombuffer(frame, np.uint8)
		image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
		# # strategy 1:
		# # if self.ref_driving_image is None:
		# # 	self.ref_driving_image = image
		# # driving_rgb_lst = [self.ref_driving_image, image]
		# # strategy 2:
		driving_rgb_lst = [image]
		frame_crop_lst = self.cropper.crop_driving_video(driving_rgb_lst)['frame_crop_lst']
		# print(f'crop driving time: {time.time() - ts}')
		# ts = time.time()
		if not frame_crop_lst:
			return None, time.time()
		cropped_driving = frame_crop_lst[-1]
		cropped_driving = cv2.resize(cropped_driving, (256, 256))
		# =======↑↑↑crop using original algorithm↑↑↑===========

		# =======↓↓↓more efficient crop xxx Penny NOTE it is actually slower↓↓↓===========
		# cropped_driving = self.cropper.crop_driving_image(frame) # ndarray: HxWx3 (256, 256)
		# =======↑↑↑more efficient crop↑↑↑===========	
		# print(f'cropping time: {time.time() - ts}')
		if cropped_driving is None:
			return None, time.time()
		# cv2.imwrite('debug_driving.png', cropped_driving)
		# cv2.imwrite(f'debug_driving_{time.time()}.png', cropped_driving)

		driving_rgb_crop = self.wrapper.prepare_img_rgb(cropped_driving)  # (256, 256, 3)[0, 255], ndarray
		ts_prepare = time.time()
		driving_motion = self.extract_motion(driving_rgb_crop)
		if driving_motion is None:
			return None, ts_prepare
		if self.driving_ref_motion is None:  # or self.force_correct_driving_ref
			self.driving_ref_motion = driving_motion
		
		# ======↓↓↓update ref motion↓↓↓======= 
		# if self.ref_updated_cnt < REF_UPDATE_MAX and torch.abs(self.driving_ref_motion['kps'] - self.driving_ref_motion['transformed_kps']).sum() > torch.abs(driving_motion['kps'] - driving_motion['transformed_kps']).sum():
		# 	self.driving_ref_motion = driving_motion
		# 	# driving_ref_updated = True
		# 	self.force_correct_driving_ref = True
		# 	self.ref_updated_cnt += 1
		# else:
		# 	self.force_correct_driving_ref = False
		# 	print(f'driving ref updated!!!')
		# ======↑↑↑update ref motion↑↑↑======= 
		
		# print(f'extract driving motion cost: {time.time() - ts}')
		# ts = time.time()

		rot_matrix_new = (driving_motion["rot_matrix"] @ self.driving_ref_motion["rot_matrix"].permute(0, 2, 1)) @ self.source_info["rot_matrix"]
		delta_new = self.source_info["exp"] + driving_motion["exp"] - self.driving_ref_motion["exp"]
		scale_new = self.source_info["scale"] * (driving_motion['scale'] / self.driving_ref_motion['scale'])
		t_new = self.source_info['t'] + (driving_motion['t'] - self.driving_ref_motion['t'])
		t_new[..., 2].fill_(0)  # zero tz
		driving_kps_new = scale_new * (self.source_info['kps'] @ rot_matrix_new + delta_new) + t_new
		if self.driving_ref_kps is None or self.force_correct_driving_ref:
			self.driving_ref_kps = driving_kps_new
		
		if self.motion_multiplier is None:
			self.motion_multiplier = calc_motion_multiplier(self.source_info['transformed_kps'], self.driving_ref_kps)

		driving_kps_diff = (driving_kps_new - self.driving_ref_kps) * self.motion_multiplier
		driving_kps_new = self.source_info['transformed_kps'] + driving_kps_diff
		# NOTE: ablation-stitching or not
		driving_kps_new = self.wrapper.stitching(self.source_info['transformed_kps'], driving_kps_new)
		out = self.wrapper.warp_decode(self.source_info['feat_3d'], self.source_info['transformed_kps'], driving_kps_new)
		# print(f'warp decode cost: {time.time() - ts}')
		# print(f'out: {out["out"].shape}')
		ctrl_values = self.wrapper.get_control_values(out['out'])[0]
		
		return ctrl_values, ts_prepare
		# print(f'ctrl values: {ctrl_values}')
		
		# img = Image.fromarray(parsed_out)
		# # img.save('debug_out.png')
		# img.save(f'debug_out_{time.time()}.png')
		# return None
		
		parsed_out = self.wrapper.parse_output(out['out'])[0]
	
		debug = Image.fromarray(parsed_out)
		debug.save('debug_out.png')
		# debug.save(f'debug_out_{time.time()}.png')
		# raise ValueError('penny stops here!!!')
		return ctrl_values, cropped_driving, parsed_out
		
	