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
from std_msgs.msg import String
import google.generativeai as genai
import json
import rclpy
from rclpy.node import Node
from robot_face_core.database.database_connection import cursor,connection
from datetime import datetime, timezone
from typing import Literal
from std_msgs.msg import String

api_key = "AIzaSyB-ZXlg-0J2K69Hzf1ZjHmCx76DjMbw7BI"
DATA_PATH = os.path.expanduser("~/ros2_ws/data/people.json")

class BrainNode(Node):
    def __init__(self):
        
            super().__init__('brain_node')
            self.get_logger().info("Brain node activated")
           
            self.api_key = api_key
            genai.configure(api_key=self.api_key)
            #Subscribing to the topic where user says something 
            self.create_subscription(String, '/voice/asr',self.tts_callback, 10)
            self.create_subscription(String,"/faceId",self.getFaceId,4)

            self.publisher =  self.create_publisher(String,"/robot_text",1)
            self.currentFaceId = None
            
            # self.currentFaceId = "9edf112b-5b96-4a24-a164-98081251847f"
            self.robotText = None
            self.isConversationEnded = False
            self.currentUserSummary = None
            # self.buildContextSummary()

            

            # self.geminiModel("Hi,my name is abc")
            # Brain node worked on audio device if 7 (default one) where mic icon will appear
            
    
    def getFaceId(self,msg):
         
         print("Id is ",msg.data)
         self.currentFaceId = msg.data
         self.currentUserSummary = self.getSummary()


    def getSummary(self):
        try:
          
            summary = cursor.execute(f"SELECT summary from ChatSummary where faceId='{self.currentFaceId}' ORDER BY createdDateTimeUtc ASC ")
            summary = summary.fetchone()
            if summary:
                return summary
            return None
               
        except Exception as e:
            self.get_logger().error(str(e))




    def insertOrUpdateSummary(self, summary):
        try:
            cursor.execute(
                "SELECT * FROM ChatSummary WHERE FaceId = ?",
                (self.currentFaceId,)
            )
            row = cursor.fetchone()
            print("ROW IS ",row)

            if row:
                cursor.execute(
                    "UPDATE ChatSummary SET summary = ?, updatedDateTimeUtc = ? WHERE FaceId = ?",
                    (summary, datetime.now(timezone.utc).isoformat(), self.currentFaceId)
                )
            else:
                cursor.execute(
                    "INSERT INTO ChatSummary(faceId, summary) VALUES (?, ?);",
                    (self.currentFaceId, summary)
                )

            connection.commit()
            self.get_logger().info("Summary created/updated in db")

        except Exception as e:
            print("Error in Summary", e)
            self.get_logger().error(str(e))
            connection.rollback()
        

    def tts_callback(self, msg):
        try:
            print("!!!!! CALLBACK FIRED !!!!!")
            userText = msg.data.strip()
            print("text from sub is :",userText)
            self.insertText(userText,"user")
            # self.extract_person_info(userText)
        
            # self.get_logger().info(f"Message {userText}")
        except Exception as e:
            self.get_logger().error(str(e))

    def insertText(self,text,userOrRobot :Literal["user","robot"]):
        try:
            if self.currentFaceId:
                cursor.execute("INSERT INTO UserInteraction(faceId,type,text) VALUES (?,?,?);",(self.currentFaceId,userOrRobot,text))
                connection.commit()
                if userOrRobot == "user":
                    self.geminiModel(text,self.currentUserSummary)
                self.get_logger().info("Text inserted in DB")
            else: raise Exception("faceId does not exist !!")

        except Exception as e:
            self.get_logger().error(str(e))
            connection.rollback()
              
         
    def buildContextSummary(self):
        conversationList = []
        try:
            for row in cursor.execute(f"SELECT type,text FROM UserInteraction where faceId = '{self.currentFaceId}' ORDER BY createdDateTimeUtc ASC"):
                conversationList.append(row)

            prompt=f"""I am providing you a chat summary of robot(whose name is chitti) and user in ascending order in the form of a list.
            Provide a summary of the chat.Keep it short and simple. {conversationList}"""

        
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            summary = response.text
            
            print("Summary is ",summary)
            self.insertOrUpdateSummary(summary)

        except Exception as e:
            self.get_logger().error(str(e))
                        
                   
                          
        


    def geminiModel(self,text: str,context:str = None):
            prompt = f"""
            You are Chitti, a friendly social interaction robot talking to a person out loud.

            You are given:
            - text: what the user just said
            - context: a summary of your previous conversations with them (if empty, treat this as your first ever interaction)

            Your job: reply to the user's text in a natural, conversational way, as if speaking out loud.

            STRICT OUTPUT RULES (this is critical — your response goes straight to a text-to-speech engine):
            - Do NOT use any markdown formatting: no asterisks (*), no bold, no italics, no bullet points, no numbered lists, no headers.
            - Do NOT use special symbols like *, #, _, -, or emojis.
            - Write only plain, natural spoken sentences — nothing that would sound odd if read aloud word-for-word.
            - Keep the reply short: strictly between 15 and 17 words.
            - Do not repeat the user's text back to them verbatim.
            - Sound warm, human, and conversational — like a companion, not an assistant reading a report.

                context: "{context if context else 'This is the first conversation.'}"
                text: "{text}"

            CONVERSATION-END DETECTION:
            Judge whether the user is wrapping up the conversation, based on intent and tone, not exact wording.
            Set conversationEnded to True if the user's text signals any of these, in any phrasing:
            - A farewell or sign-off (bye, goodbye, see you, take care, catch you later, gotta go, talk soon, etc.)
            - Gratitude that signals closure (thanks, appreciate it, thank you for the chat, etc.)
            - A clear intent to leave or end the interaction (I'm heading out, I should go, that's all for now, we'll continue later, etc.)
            - A short closing acknowledgment after a natural resolution point (okay cool, alright then, sounds good, said with a tone of wrapping up rather than continuing the topic)

            Set conversationEnded to False if the user is still asking something, sharing something, continuing the topic, or their intent to end is unclear.

            When uncertain, lean on the overall tone and context of the exchange rather than requiring an exact keyword match.

            format : your_reply conversationEnded:True or False   (strictly follow this format, always write True or False with a capital first letter)

            Reply now, following all the rules above.
            """
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                text = response.text.strip().strip("`")
                
                # text = "Hi my name is Chitti,how may I assist you ?"
                print("ROBOT'S REPLY IS ",text)
                reply = text.split("conversationEnded")[0]
               
                self.isConversationEnded = text.split("conversationEnded:")[1] == "True"
                print("Conversation Ended",self.isConversationEnded)

                temp = String(data=reply)
                self.publisher.publish(temp)
               
                if self.isConversationEnded:
                    self.buildContextSummary()
                self.insertText(reply,"robot")
                
            except Exception as e:
                self.get_logger().error(str(e))
                temp = String(data="Sorry an error occurred in my system")
                self.publisher.publish(temp)



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
            self.get_logger().error(str(e))

            return {}




def main(args=None):
    rclpy.init(args=args)
    node = BrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
