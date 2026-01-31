
# -*- coding:utf-8 -*-
# @Desc: pose regression network -- from image (and possibly language instruction) to control values


from transformers import AutoFeatureExtractor, AutoModelForImageClassification
import torch
from torchvision import models
import torch.nn as nn


class X2Control(nn.Module):
	"""mapping from image to control values (corresponds to facial expression)"""
	def __init__(self, cfg):
		super().__init__()
		self.encoder_opt = cfg.model.encoder_opt
		if self.encoder_opt == 'vgg':
			self.feature_extractor = models.vgg16(pretrained=True).features
			self.pos_pred_head = nn.Sequential(
				nn.Linear(25088, 256), nn.ReLU(), 
				nn.Linear(256, 256), nn.ReLU(),
				nn.Linear(256, cfg.model.pos_action_size))
		elif self.encoder_opt == 'transformer':
			model_name = "google/vit-base-patch16-224-in21k"  # Pretrained ViT
			model = AutoModelForImageClassification.from_pretrained(model_name, num_labels=10)
			# print(f'model : {model}')
			self.feature_extractor = nn.Sequential(*list(model.children())[:-1])
			self.pos_pred_head = nn.Sequential(
				nn.Linear(151296, 256), nn.ReLU(), 
				nn.Linear(256, 256), nn.ReLU(),
				nn.Linear(256, cfg.model.pos_action_size))
		elif self.encoder_opt == 'efficient':
			self.feature_extractor = models.efficientnet_b0(pretrained=True).features
			self.pool = nn.AdaptiveAvgPool2d(1)
			self.pos_pred_head = nn.Sequential(
				nn.Linear(1280, 256), nn.ReLU(), 
				nn.Linear(256, 256), nn.ReLU(),
				nn.Linear(256, cfg.model.pos_action_size))

		else:
			# self.angle_pred_head = nn.Sequential(nn.Linear(2048, 256), nn.ReLU(), nn.Linear(256, cfg.model.angle_action_size))
			weights = models.ResNet18_Weights.DEFAULT if cfg.model.use_resnet_pretrain else None
			model = models.resnet18(weights=weights) # 44.629 MB, 
			self.feature_extractor = nn.Sequential(*list(model.children())[:-1])  # cls=1000
			self.pos_pred_head = nn.Sequential(
				nn.Linear(512, 256), nn.ReLU(), 
				nn.Linear(256, 256), nn.ReLU(),
				nn.Linear(256, cfg.model.pos_action_size),
				# nn.Sigmoid(),
				)
	
	def forward(self, x):  
		'''for resnet18'''
		output = self.feature_extractor(x) # output now has the features corresponding to input x
		# print(output.shape)   # torch.Size([bs, 2048, 1, 1]) for resnet 50, torch.Size([4, 512, 1, 1]) for resnet18
		if self.encoder_opt == 'vgg':
			output = torch.flatten(output, 1)
			# raise ValueError(f'output shape: {output.shape}')
			pos_pred_vals = self.pos_pred_head(output)
		elif self.encoder_opt == 'transformer':
			# print(f'output {output.last_hidden_state.shape} \n *****')
			features = output.last_hidden_state
			# print(f'features shape 111: {features.shape}')
			features = features.view(features.size(0), -1)
			# print(f'feature shape: {features.shape}')
			pos_pred_vals = self.pos_pred_head(features)
		elif self.encoder_opt == 'efficient':
			features = self.pool(output)
			features = features.view(features.size(0), -1)
			pos_pred_vals = self.pos_pred_head(features)
        
		else:
			output = output.squeeze(-1).squeeze(-1)
			pos_pred_vals = self.pos_pred_head(output)
		return pos_pred_vals


