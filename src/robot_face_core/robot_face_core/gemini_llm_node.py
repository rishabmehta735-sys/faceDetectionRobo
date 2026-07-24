"""
person_parser_local_llm.py

Uses a local LLM (via llama-cpp-python) to extract person fields (name, occupation,
email, phone) from arbitrary transcribed text. Returns a small dict with only
the keys found. Falls back to simple regex extraction if the LLM is unavailable
or fails.

How to use:
    from voice_turtle.person_parser_local_llm import extract_person_info, save_person_data

    info = extract_person_info("Hi, I'm Abhi and I work as a software engineer")
    if info:
        save_person_data(face_id, info)
"""

import os
import json
import tempfile
import re
from std_msgs.msg import String
import google.generativeai as genai
from typing import Dict, Any, Optional
import rclpy
from rclpy.node import Node

api_key = "AIzaSyB-ZXlg-0J2K69Hzf1ZjHmCx76DjMbw7BI"
DATA_PATH = os.path.expanduser("~/ros2_ws/data/people.json")

class GeminiLLMNode(Node):
    def __init__(self):
        
            super().__init__('gemini_llm_node')
            self.get_logger().info("Gemini node activated")
            self.api_key = api_key
            genai.configure(api_key=self.api_key)
            self.create_subscription(String, '/voice/asr',self.tts_callback, 10)
            # Gemini node worked on audio device if 7 (default one) where mic icon will appear
            # print("self.create_subscription:",self.create_subscription)
        

    def tts_callback(self, msg):
        try:
            print("!!!!! CALLBACK FIRED !!!!!")
            text = msg.data.strip()
            print("text from sub is :",text)
            self.extract_person_info(text)
        
            self.get_logger().info(f"Message {text}")
        except Exception as e:
            print(e)

        


# ---------- Configuration ----------


# -------------------------------


# ---------- LLM-based extraction ----------
    def extract_person_info(self,text: str):
        prompt = f"""
    You are a JSON extractor. From the following text, extract the person's name and occupation.
    Example:
    Input: "Hi, I'm Abhi and I work as a software engineer"
    Output: {{"name": "Abhi", "occupation": "software engineer"}}
    be dynmic like input is "I work at I work at Infosys as a software engineer"
    then workplace is "Infosys" and occupation is software engineer
    Think of yourself like a robot you will store these peices of information name and occupation are just example of those keywords
    Input: "{text}"
        """
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw = response.text.strip().strip("`")
        try:
            print("reaching",raw)
            return raw
            # return json.loads(raw)
        except Exception as e:
            self.get_logger().error(e)

            return {}


# ---------- JSON store helpers (same as earlier) ----------
    # def _load_json_store(path: str = DATA_PATH) -> Dict[str, Any]:
    #     if not os.path.exists(os.path.dirname(path)):
    #         os.makedirs(os.path.dirname(path), exist_ok=True)
    #     if not os.path.exists(path):
    #         with open(path, "w") as f:
    #             json.dump({}, f)
    #     with open(path, "r") as f:
    #         try:
    #             return json.load(f)
    #         except Exception:
    #             return {}


    # def _atomic_write(path: str, data: Dict[str, Any]):
    #     tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(path))
    #     json.dump(data, tmp, indent=2)
    #     tmp.flush()
    #     tmp.close()
    #     os.replace(tmp.name, path)


    # def save_person_data(face_id: str, data: Dict[str, str], path: str = DATA_PATH):
    #     store = _load_json_store(path)
    #     entry = store.get(face_id, {})
    #     entry.update(data)
    #     import datetime
    #     entry["last_seen"] = datetime.datetime.utcnow().isoformat() + "Z"
    #     store[face_id] = entry
    #     _atomic_write(path, store)


    # def get_person_data(face_id: str, path: str = DATA_PATH) -> Dict[str, Any]:
    #     store = _load_json_store(path)
    #     return store.get(face_id, {})


# Quick test when run directly
# if __name__ == "__main__":
#     tests = [
#         "Hi, I'm Amit Kumar and I work as a data scientist",
#         "Call me Rishab",
#         "Hii,my name is rohit ,I work at Infosys as a software engineer",
#         "My email is test@example.com and phone is +91 99999 99999",
#         "my email is testadderateexample.com and phone is plus 9191 double 9191"
#     ]
#     for t in tests:
#         print("IN:", t)
#         print("out:",extract_person_info(t))
#         # print("OUT:", extract_person_info(t))
#         print("----")

def main(args=None):
    rclpy.init(args=args)
    node = GeminiLLMNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
