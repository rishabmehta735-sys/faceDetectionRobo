#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import asyncio
import edge_tts
import tempfile
import os
import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel


class VoiceInterfaceNode(Node):
    def __init__(self):
        super().__init__('voice_interface_node')

        # ROS topics
        self.create_subscription(String, '/voice/tts', self.tts_callback, 10) #listens for the text message that robot should speak
        self.asr_publisher = self.create_publisher(String, '/voice/asr', 10) #After the robot listens and converts speech → text, it sends (publishes) that recognized text here so other nodes can use it

        # Load Faster-Whisper model (choose size: tiny, base, small, medium, large)
        self.model = WhisperModel("base", device="cpu")  # use "cuda" if GPU available
        self.samplerate = 16000 # Audio recording rate to 16 kHz

        self.get_logger().info("✅ Voice Interface Node started (Faster-Whisper + Edge-TTS)")

        # Timer to continuously listen (every ~10 s)
        self.create_timer(10.0, self.listen_and_publish)

    # ---------- TEXT → SPEECH ----------
    def tts_callback(self, msg):
        text = msg.data.strip()
        print("text from sub is :",text)
        if not text:
            return
        self.get_logger().info(f"TTS speaking: {text}")
        asyncio.run(self.speak(text))

    async def speak(self, text):
        # Use Edge TTS (AriaNeural = natural female voice)
        print("reaching speak function")
        communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            await communicate.save(fp.name)
            os.system(f"ffplay -nodisp -autoexit {fp.name}")

    # ---------- SPEECH → TEXT ----------
    def listen_and_publish(self):
        duration = 10  # seconds to record
        self.get_logger().info("🎙️ Listening… speak now.")
        audio = sd.rec(int(duration * self.samplerate),
                       samplerate=self.samplerate, channels=1, dtype='float32')
        sd.wait()
        # Here In this function we are recording the speech for 10 seconds 
        # after that when it is being processed it is not listening
        print("audio value is ",round(np.max(np.abs(audio)), 2))
        volume = np.std(audio)
        print("volume is ",volume)
        rms = np.sqrt(np.mean(audio**2))
        if volume < 0.004: 
             self.get_logger().info("🕳️ Silent or very low speech — skipping.")
             return
      
        self.get_logger().info("⏹️ Recording stopped. Processing…")

        # Save temporary WAV file
        wav_path = tempfile.mktemp(suffix=".wav")
        sf.write(wav_path, audio, self.samplerate)

        # Transcribe using Faster-Whisper
        segments, info = self.model.transcribe(wav_path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip().lower()
        if text:
            self.get_logger().info(f"🗣️ Recognized: {text}")
            msg = String()
            msg.data = text
            self.asr_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = VoiceInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
