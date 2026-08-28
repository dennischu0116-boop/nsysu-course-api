"""
用 nsysu-opendev/NSYSUCourseAPI 訓練好的 EfficientCapsNet 模型辨識驗證碼。
前處理流程照抄他們的 utils/parse_valid_code.py（灰階 -> 中值濾波 -> 平均切4份 ->
resize 28x28 -> /255），只是改成一次載入模型、重複用。
"""
import os
import numpy as np
import torch
from PIL import Image, ImageFilter

from capsnet_model import DEVICE, make_deploy_model

DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(DIR, "model", "EfficientCapsNetDeploy.pth")

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    model = make_deploy_model()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False))
    model.to(DEVICE)
    model.eval()
    _model = model
    return _model


def preload():
    """Force the model to load now, so worker threads don't race on the
    first solve() call."""
    _load_model()


def solve(image_path):
    """Return a 4-char digit string guess (digits 1-9)."""
    model = _load_model()

    image = Image.open(image_path).convert("L")
    image = image.filter(ImageFilter.MedianFilter(size=3))

    width = image.size[0]
    slice_width = width // 4
    slices = []
    for i in range(4):
        slice_img = image.crop((i * slice_width, 0, (i + 1) * slice_width, image.size[1]))
        slice_img = slice_img.resize((28, 28))
        slices.append(slice_img)

    slices = np.array([np.array(s) / 255.0 for s in slices])
    slices_tensor = torch.tensor(slices, dtype=torch.float32).unsqueeze(1)
    slices_tensor = slices_tensor.to(DEVICE)

    with torch.no_grad():
        _, predictions = model(slices_tensor)

    predicted_classes = torch.argmax(predictions, dim=1).cpu().numpy() + 1
    return "".join(map(str, predicted_classes))
