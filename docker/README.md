# Docker 环境配置说明

## 前置要求

1. **Windows环境**
   - 安装 Docker Desktop for Windows
   - 启用 WSL2 后端（Windows功能中开启"适用于Linux的Windows子系统"和"虚拟机平台"）

2. **GPU支持**
   - 安装 NVIDIA Container Toolkit
   - 确保显卡驱动版本兼容（RTX 3060 需要驱动版本 >= 511.x）

## 构建命令

```bash
# 进入docker目录
cd E:\rumor_detection\docker

# 构建镜像
docker-compose build

# 后台运行容器
docker-compose up -d

# 进入容器交互
docker exec -it rumor-detection-env /bin/bash
```

## 验证 GPU 是否可用

在容器内运行：

```python
import torch
print(torch.cuda.is_available())  # 应输出 True
print(torch.cuda.get_device_name(0))  # 应输出 NVIDIA GeForce RTX 3060
```

## 注意事项

- 确保 BIOS 中已启用 CPU 虚拟化
- Docker Desktop 设置中需勾选 "Use the WSL 2 based engine"
- 首次构建需要下载 CUDA 基础镜像，时间可能较长

## 文件结构

```
docker/
├── Dockerfile           # 镜像构建文件
├── docker-compose.yml   # 容器编排配置
└── README.md           # 本说明文件
```
