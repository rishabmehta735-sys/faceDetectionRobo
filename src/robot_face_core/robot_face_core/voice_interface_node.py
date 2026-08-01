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
from faster_whisper import WhisperModel # encoder-decoder model


class VoiceInterfaceNode(Node):
    def __init__(self):
        super().__init__('voice_interface_node')

        # ROS topics
        self.isAudioListeningEnabled = False
        self.create_subscription(String, '/robot_text', self.tts_callback, 1) #listens for the text message that robot should speak
        self.asr_publisher = self.create_publisher(String, '/voice/asr', 10) #After the robot listens and converts speech → text, it sends (publishes) that recognized text here so other nodes can use it
        
        # Load Faster-Whisper model (choose size: tiny, base, small, medium, large)
        self.model = WhisperModel("base", device="cpu")  # use "cuda" if GPU available

        self.get_logger().info("✅ Voice Interface Node started (Faster-Whisper + Edge-TTS)")

        # Timer to continuously listen (every ~10 s)
        # self.listen_and_publish()
        self.create_timer(3, self.listen_and_publish)
        self.create_subscription(String,"/faceId",self.startVoiceInput,4)
        

    def startVoiceInput(self,msg):
        if msg.data:
             self.isAudioListeningEnabled = True
        else: self.isAudioListeningEnabled = False
     
        

    # ---------- TEXT → SPEECH ----------
    def tts_callback(self, msg):
        self.get_logger().info("REACHED TTS CALLBACK")
       
        
        text = msg.data.strip()
        print("text from sub is :",text)
        if not text:
            return
        self.get_logger().info(f"TTS speaking: {text}")
        self.isAudioListeningEnabled = False
        asyncio.run(self.speak(text))

    async def speak(self, text):
        # Use Edge TTS (AriaNeural = natural female voice)
        communicate = edge_tts.Communicate(text, voice="en-IN-NeerjaExpressiveNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            await communicate.save(fp.name)
            os.system(f"ffplay -nodisp -autoexit {fp.name}")
            self.isAudioListeningEnabled = True

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

    def find_input_device(self, preferred_name='default', fallback_name='CX8070'):
        """
        Returns (device_index, device_info) for a working input device.
        Tries `preferred_name` first (validating it currently reports input channels),
        falls back to `fallback_name` (real hardware) if preferred fails.
        """
        devices = sd.query_devices()

        def try_match(name_substr):
            for i, d in enumerate(devices):
                if name_substr.lower() in d['name'].lower() and d['max_input_channels'] > 0:
                    return i, d
            return None, None

        # 1. Try preferred (e.g. 'default')
        idx, info = try_match(preferred_name)
        if idx is not None:
            try:
                # sanity check: make sure PortAudio will actually open it right now
                sd.check_input_settings(device=idx, channels=min(2, info['max_input_channels']))
                return idx, info
            except Exception as e:
                self.get_logger().warn(f"Preferred device '{preferred_name}' (idx {idx}) failed check: {e}")

        # 2. Fall back to real hardware
        idx, info = try_match(fallback_name)
        if idx is not None:
            try:
                sd.check_input_settings(device=idx, channels=min(2, info['max_input_channels']))
                return idx, info
            except Exception as e:
                self.get_logger().warn(f"Fallback device '{fallback_name}' (idx {idx}) failed check: {e}")

        raise RuntimeError("No working input device found (checked 'default' and 'CX8070')")

  



    def listen_and_publish(self):
        try:
          
            if not self.isAudioListeningEnabled:
                return
            device_index, device_info = self.find_input_device(
                preferred_name='default', fallback_name='CX8070'
            )
            self.get_logger().info(f"🎙️ Using input device {device_index}: {device_info['name']}")

            native_rate = int(device_info['default_samplerate'])
            channels = min(2, device_info['max_input_channels'])

            
            # Tunable parameters
            silence_threshold = 0.06      # same threshold you used before
            silence_duration = 1.5         # seconds of silence to stop
            min_speech_duration = 0.3      # ignore blips shorter than this
            max_record_duration = 15.0     # hard cap safety net
            blocksize = 2048               # samples per callback chunk

            chunk_duration = blocksize / native_rate

            # Mutable state shared with the callback
            state = {
                'buffer': [],
                'speech_started': False,
                'silence_chunks': 0,
                'speech_chunks': 0,
                'total_chunks': 0,
            }

            silence_chunk_limit = int(silence_duration / chunk_duration)
            max_chunk_limit = int(max_record_duration / chunk_duration)

            def callback(indata, frames, time_info, status):
                if status:
                    self.get_logger().warn(str(status))

                chunk = indata.copy()
                volume = np.std(chunk)

                state['buffer'].append(chunk)
                state['total_chunks'] += 1
                print("volume",volume)

                if volume >= silence_threshold:
                    state['speech_started'] = True
                    state['speech_chunks'] += 1
                    state['silence_chunks'] = 0
                elif state['speech_started']:
                    state['silence_chunks'] += 1

                # Stop conditions
                if state['speech_started'] and state['silence_chunks'] >= silence_chunk_limit:
                    raise sd.CallbackStop
                if state['total_chunks'] >= max_chunk_limit:
                    raise sd.CallbackStop

            self.get_logger().info("🎙️ Listening… speak now.")

            with sd.InputStream(
                samplerate=native_rate,
                channels=channels,
                dtype='float32',
                device=device_index,
                blocksize=blocksize,
                callback=callback,
            ) as stream:
                while stream.active:
                    sd.sleep(50)  # poll every 50ms until callback raises CallbackStop

            if not state['buffer']:
                self.get_logger().info("🕳️ No audio captured — skipping.")
                return

            audio = np.concatenate(state['buffer'], axis=0)

            speech_time = state['speech_chunks'] * chunk_duration
            if not state['speech_started'] or speech_time < min_speech_duration:
                self.get_logger().info("🕳️ Silent or very brief speech — skipping.")
                return

            self.get_logger().info("⏹️ Recording stopped. Processing…")

            wav_path = tempfile.mktemp(suffix=".wav")
            sf.write(wav_path, audio, native_rate)

            segments, info = self.model.transcribe(wav_path, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip().lower()
            if text:
                self.get_logger().info(f"🗣️ Recognized: {text}")
                msg = String()
                msg.data = text
                self.asr_publisher.publish(msg)
                self.get_logger().info("Text sent")
                self.isAudioListeningEnabled = False

        except Exception as e:
            self.get_logger().error(f"listen_and_publish failed: {e}")


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
