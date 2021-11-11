import math
import torch
import torch.nn as nn
import torch.utils.model_zoo as model_zoo

# from compute_flops import *
from thop import profile
from torchvision import models
# from .channel_selection import channel_selection


__all__ = ['resnet50_official']

model_urls = {
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
}

def conv3x3(in_planes, out_planes, stride=1):
    "3x3 convolution with padding"
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)

class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, cfg, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(cfg[0], cfg[1], kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(cfg[1])
        self.conv2 = nn.Conv2d(cfg[1], cfg[2], kernel_size=3, stride=stride,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(cfg[2])
        self.conv3 = nn.Conv2d(cfg[2], planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, layers, cfg, num_classes=1000):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, cfg[0:9], 64, layers[0])
        self.layer2 = self._make_layer(block, cfg[9:21], 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, cfg[21:39], 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, cfg[39:48], 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(m.weight, mode='fan_out')
                # m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, cfg, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, cfg[:3], stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes, cfg[3*i:3*(i+1)]))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x

cfg_official = [[64, 64, 64], [256, 64, 64] * 2, [256, 128, 128], [512, 128, 128] * 3, 
                [512, 256, 256], [1024, 256, 256] * 5, [1024, 512, 512], [2048, 512, 512] * 2]
cfg_official = [item for sublist in cfg_official for item in sublist]
assert len(cfg_official) == 48, "Length of cfg_official is not right"


def resnet50_official(pretrained=False, **kwargs):
    """Constructs a ResNet-50 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 6, 3], cfg_official, **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet50']))
    return model

def resnet50(pretrained=False, cfg=None, **kwargs):
    """Constructs a ResNet-50 model.
# 
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    if cfg is None:
        cfg = cfg_official
    model = ResNet(Bottleneck, [3, 4, 6, 3], cfg, **kwargs)
    # if pretrained:
    #     model.load_state_dict(model_zoo.load_url(model_urls['resnet50']))
    return model

if __name__ == '__main__':
    # cfg1=[64, 64, 5, 256, 64, 37, 256, 64, 48, 256, 128, 33, 512, 512, 128, 11, 512, 128, 70, 512, 128, 23, 512, 256, 18, 1024, 256, 54, 1024, 256, 127, 1024, 256, 102, 1024, 256, 43, 1024, 256, 90, 1024, 512, 1, 2048, 512, 16, 2048, 512, 77]
    # model = ResNet(Bottleneck, [3, 4, 6, 3], cfg_official)

    checkpoint = torch.load('./pruned/pruned.pth')
    print(checkpoint['cfg'])
    model = resnet50(cfg=checkpoint['cfg'])
    # model.load_state_dict(checkpoint['state_dict'])
    # print(len(cfg1))
    # print(len(cfg_official))
    # print(cfg1)
    # print(cfg_official)
    # for i in range(len(cfg1)):
    #     print("1=", cfg1[i])
    #     print("2=", cfg_official[i])
    # n = 0
    # skip_layer = [4, 14, 27, 46,52]
    # print(skip_layer+1)
    # layer = 0
    # for m in model.modules():
    #     if isinstance(m, nn.Conv2d) :
    #         print(m.weight.data.size())
    #         if layer not in skip_layer:
    #             # print("layer = ", layer)            
    # #             n += 1
    #             print(m)
    #             print(m.weight.data.size())
    #         layer += 1
    # print("n=", n)
    # model = resnet50_official(pretrained=True)
    # model = models.resnet50()
    # print(model)
    # model.load_state_dict(model_zoo.load_url(model_urls['resnet50']))
    
    x = torch.randn(1, 3, 224, 224)
    flops, params = profile(model, inputs=(x,))
    print(' Total flops = %.2fB' % (flops / 1e9))
    print(' Total params = %.2fM' % (params / 1e6))
