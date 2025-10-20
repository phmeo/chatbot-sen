from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Facebook Messenger configuration
PAGE_ACCESS_TOKEN = "EAAR0px92PQ0BO5ZAXQQF78wvIXf5ZABVY7bUlv3lZA6mlVbvmcfTZBeJHdUnG8QWlhCtiK7ORCplPueCfPQbuVO5s5OpkbDa3uim0OC78KUdSLmUw8pF8K9ej0q67N2gTKblnVjgs91KgTs9uZAb1pehFTfNlGk6GZAsJV7ZAq5rJ4MFjcCTzZARJabTs8ryGsNo0pdstqPv"
PAGE_ID = "1254161043045645"
VERIFY_TOKEN = "f948b6f6e1a08a02c2789a1447f17493"

app = Flask(__name__)

def send_message(recipient_id, message_text):
    """Send message to Facebook Messenger."""
    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for Facebook Messenger."""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403
    return 'Bad Request', 400

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming messages from Facebook Messenger."""
    data = request.get_json()
    
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                
                if 'message' in messaging_event:
                    if 'text' in messaging_event['message']:
                        message_text = messaging_event['message']['text']
                        
                        # Forward the message to your existing chat endpoint
                        chat_response = requests.post(
                            'http://localhost:5000/chat',
                            json={'message': message_text}
                        )
                        
                        if chat_response.status_code == 200:
                            response_data = chat_response.json()
                            # Send the response back to Facebook Messenger
                            send_message(sender_id, response_data['response'])
                        else:
                            send_message(sender_id, "Xin lỗi, có lỗi xảy ra khi xử lý tin nhắn của bạn.")
    
    return 'OK', 200

if __name__ == '__main__':
    app.run(port=5001)