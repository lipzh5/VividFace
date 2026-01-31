# VividFace 🤖 
This repository is the official implementation of the facial expression shadowing system in paper 

_**VividFace: Real-Time and Realistic Facial Expression Shadowing for Humanoid Robots**_ 
![Alt text](docs/static/images/systemoverview8.png)

Customized iOS App source code is available at [VideoStreamer](appsrc/VideoStreamer).


## Real-World Examples of Realistic Imitation
![Alt text](docs/static/images/realworld_examples7.png)

## 🚀 Getting Started 
🔧 **Clone the Code and Set Up the Environment**

```bash
git clone git@github.com:pi3-141592653/VividFace.git
cd VividFace

# create env using conda
conda create -n vividface python=3.9
conda activate vividface
# for cuda 12.1
conda install pytorch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 pytorch-cuda=12.1 -c pytorch -c nvidia
```

 📦 **Install Python Dependencies**

```setup
pip install -r requirements.txt
```

## 📥 Pre-trained Models
You can download pre-trained models here:


[🔗Base Models](https://drive.google.com/drive/folders/10b7FyJ-IdRhi0I1Op_avqjRkNx8ItcKZ?usp=sharing) fine-tuned on <strong>X2C</strong> for 30 epochs.

 [🔗Mapping Network](https://drive.google.com/file/d/1KcRy9d5qTl349tSS-DyCapk4E597YiEu/view?usp=sharingg) trained on <strong>X2C</strong>  for 100 epochs, using ResNet18 as the feature extractor.

## 🚀 Run
```bash
python main.py
```

 ## 🤝 Contributing
We are actively updating and improving this repository. If you find any bugs or have suggestions, welcome to raise issues or submit pull requests (PR) 💖.
If you find <strong>VividFace</strong> or <strong>X2CNet++</strong> useful for your research, welcome to 🌟 this rep.
