# Use NVIDIA CUDA base image with Ubuntu 20.04
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    git \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA for Python 3.9
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update

# Install Python 3.9 and pip
RUN apt-get install -y python3.9 python3.9-dev python3.9-distutils && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.9 get-pip.py && \
    rm get-pip.py

# Set Python 3.9 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# Set working directory
WORKDIR /workspace

# Copy requirements file
COPY ../requirements.txt .

# Install PyTorch with CUDA 11.8 support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
RUN pip3 install -r requirements.txt

# Set default command
CMD ["/bin/bash"]
