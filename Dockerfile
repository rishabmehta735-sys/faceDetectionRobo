FROM osrf/ros:jazzy-desktop

# System deps
RUN apt-get update && apt-get install -y \
    python3-pip \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy your pinned requirements
COPY requirements.txt /requirements.txt
RUN pip install --break-system-packages --ignore-installed -r /requirements.txt

WORKDIR /workspace/robot_face_ws    