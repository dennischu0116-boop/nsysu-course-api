"""
EfficientCapsNet 架構定義（僅推論所需的部分）。

來源：https://github.com/nsysu-opendev/NSYSUCourseAPI (MIT License)
      utils/model.py，該檔案本身標註是從
      https://github.com/akhdanfadh/efficient-capsnet-pytorch 改寫而來。
只保留推論用得到的類別（拿掉訓練用的 ReconstructionNet / MarginLoss / make_model），
配合下載回來的 model/EfficientCapsNetDeploy.pth 權重檔使用。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def squash(x, eps=10e-21):
    n = torch.norm(x, dim=-1, keepdim=True)
    return (1 - 1 / (torch.exp(n) + eps)) * (x / (n + eps))


def length(x) -> torch.Tensor:
    return torch.sqrt(torch.sum(x**2, dim=-1) + 1e-8)


class PrimaryCapsLayer(nn.Module):
    def __init__(self, in_channels, kernel_size, num_capsules, dim_capsules, stride=1):
        super().__init__()
        self.depthwise_conv = nn.Conv2d(
            in_channels=in_channels,
            out_channels=in_channels,
            kernel_size=kernel_size,
            stride=stride,
            groups=in_channels,
            padding="valid",
        )
        self.num_capsules = num_capsules
        self.dim_capsules = dim_capsules

    def forward(self, input):
        output = self.depthwise_conv(input)
        output = output.view(output.size(0), self.num_capsules, self.dim_capsules)
        return squash(output)


class RoutingLayer(nn.Module):
    def __init__(self, num_capsules, dim_capsules):
        super().__init__()
        self.W = nn.Parameter(torch.Tensor(num_capsules, 16, 8, dim_capsules))
        self.b = nn.Parameter(torch.zeros(num_capsules, 16, 1))
        self.num_capsules = num_capsules
        self.dim_capsules = dim_capsules
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.kaiming_normal_(self.W)
        nn.init.zeros_(self.b)

    def forward(self, input):
        u = torch.einsum("...ji,kjiz->...kjz", input, self.W)
        c = torch.einsum("...ij,...kj->...i", u, u)[..., None]
        c = c / torch.sqrt(
            torch.Tensor([self.dim_capsules]).type(torch.FloatTensor).to(DEVICE)
        )
        c = torch.softmax(c, axis=1)
        c = c + self.b
        s = torch.sum(torch.mul(u, c), dim=-2)
        return squash(s)


class EfficientCapsNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=5, padding="valid")
        self.batch_norm1 = nn.BatchNorm2d(num_features=32)
        self.conv2 = nn.Conv2d(32, 64, 3, padding="valid")
        self.batch_norm2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 64, 3, padding="valid")
        self.batch_norm3 = nn.BatchNorm2d(64)
        self.conv4 = nn.Conv2d(64, 128, 3, stride=2, padding="valid")
        self.batch_norm4 = nn.BatchNorm2d(128)

        self.primary_caps = PrimaryCapsLayer(
            in_channels=128, kernel_size=9, num_capsules=16, dim_capsules=8
        )
        self.digit_caps = RoutingLayer(num_capsules=10, dim_capsules=16)
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.kaiming_normal_(self.conv1.weight)
        nn.init.kaiming_normal_(self.conv2.weight)
        nn.init.kaiming_normal_(self.conv3.weight)
        nn.init.kaiming_normal_(self.conv4.weight)

    def forward(self, x):
        x = torch.relu(self.batch_norm1(self.conv1(x)))
        x = torch.relu(self.batch_norm2(self.conv2(x)))
        x = torch.relu(self.batch_norm3(self.conv3(x)))
        x = torch.relu(self.batch_norm4(self.conv4(x)))
        x = self.primary_caps(x)
        x = self.digit_caps(x)
        probs = length(x)
        return x, probs


def make_deploy_model() -> torch.nn.Module:
    model = EfficientCapsNet()
    model.eval()
    return model
