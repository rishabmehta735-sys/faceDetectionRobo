# Face Detection Robot

A ROS 2-based robot that detects faces, remembers people it has seen before, and interacts with users through voice — powered by an LLM "brain" for conversation and structured data extraction.

## Overview

The robot uses its onboard camera to detect and recognize faces. When it sees a new face, it remembers it; when it sees a face it already knows, it can recall who they are. A voice interface lets users talk to the robot naturally, with a Gemini-based LLM node acting as the reasoning core — deciding what to say and extracting structured information (like a person's name and occupation) from conversation.

## Note - In order to use it flawlessly you may need gemini subscription,as tokens may get expire soon and system will throw an error !! 

## Features

- **Real-time camera feed** using the system's built-in camera
- **Face recognition** — detects new faces and distinguishes them from previously seen ones
- **Persistent face memory** — remembers people across sessions
- **Voice interaction** — listens via microphone and responds via speech
- **LLM-powered reasoning** — Gemini acts as the robot's "brain," structuring conversation info (e.g. name, occupation) into JSON
- **Modular ROS 2 architecture** — five independent nodes communicating over topics


## Nodes

### 1. `camera_node`
Captures live footage using the system's built-in camera and publishes image frames for downstream processing.

### 2. `face_recognition_node`
Subscribes to `camera_node`. Detects faces in each frame, checks whether a detected face is new or already known, and stores new face data for future recognition.

### 3. `gemini_llm_node`
Acts as the robot's brain. Handles conversational responses and also functions as a JSON extractor — structuring free-form conversation (e.g. spoken introductions) into structured fields like name and occupation.

### 4. `talker_node`
Handles the robot's speech output, converting text responses into spoken audio.

### 5. `voice_interface_node`
Uses the system's microphone to capture audio and handles voice-to-text and text-to-voice interaction logic.

### 6. `brain_node`
Generates a response and keeps track of user conversation

## Requirements

- ROS 2 Jazzy
- Python 3.12
- System camera and microphone access
- Gemini API access (for `gemini_llm_node`)

> **Note:** Add your specific Python dependencies (e.g. `deepface`, speech recognition/TTS libraries, `google-generativeai` or equivalent) to `requirements.txt` and pin versions for stability.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/rishabmehta735-sys/faceDetectionRobo.git


# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build the ROS 2 workspace
colcon build --symlink-install
source install/setup.bash

```

> **Note:** If running nodes individually via `ros2 run`, ensure your virtualenv's `site-packages` is on `PYTHONPATH`, since `ros2 run` uses its own interpreter and won't see venv-installed packages by default.

## Roadmap / Ideas

- [ ] Persistent face database (currently in-memory / TBD storage backend)
- [ ] Multi-face tracking in a single frame
- [ ] Wake-word activation for voice interface
- [ ] Emotion/expression detection
- [ ] Dockerized deployment for reproducible environments

