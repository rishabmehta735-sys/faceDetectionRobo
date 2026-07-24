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

        self.get_logger().info("✅ Voice Interface Node started (Faster-Whisper + Edge-TTS)")

        # Timer to continuously listen (every ~10 s)
        self.create_timer(10.0, self.listen_and_publish)
        self.testAudio()

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

    def testAudio(self):
        try:
            fs = 48000
            duration = 5  

            devices = sd.query_devices()
            for i, d in enumerate(devices):
                 print(i, d['name'], "| in:", d['max_input_channels'], "| out:", d['max_output_channels'])
        except Exception as e:
            print(e)


    def listen_and_publish(self):
        try:
            duration = 10
            device_info = sd.query_devices(sd.default.device[0], 'input')
           
            native_rate = int(device_info['default_samplerate'])

            self.get_logger().info("🎙️ Listening… speak now.")
            audio = sd.rec(int(duration * native_rate),
                            samplerate=native_rate, channels=2, dtype='float32', device=7)
            sd.wait()

            volume = np.std(audio)
            
            if volume < 0.004:
                self.get_logger().info("🕳️ Silent or very low speech — skipping.")
                return

            self.get_logger().info("⏹️ Recording stopped. Processing…")

            wav_path = tempfile.mktemp(suffix=".wav")
            sf.write(wav_path, audio, native_rate)  # write at the TRUE rate it was recorded at

            segments, info = self.model.transcribe(wav_path, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip().lower()
            if text:
                self.get_logger().info(f"🗣️ Recognized: {text}")
                msg = String()
                msg.data = text
                self.asr_publisher.publish(msg)
                self.get_logger().info("Text sent")
        except Exception as e:
             self._logger("Error", e)


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
