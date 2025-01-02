from flask import Flask, request, jsonify
from assistant_logic import handle_assistant_response
from google_calendar_utils import create_event, delete_event

app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    response, error = handle_assistant_response(user_message, user_id)
    if error:
        return jsonify({'response': error}), 500

    return jsonify({'response': response})

@app.route('/webhook', methods=['GET'])
def webhook_verification():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == '12345':
        return challenge
    else:
        return "Error, invalid token", 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
