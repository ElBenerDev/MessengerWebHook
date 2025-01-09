from flask import Flask, request, jsonify
from assistant_logic import handle_assistant_response
from google_calendar_utils import create_event, list_events, delete_event

app = Flask(__name__)

# Ruta para manejar los mensajes del usuario
@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('user_id')

    if not user_message or not user_id:
        return jsonify({"error": "Mensaje o ID de usuario no proporcionados"}), 400

    assistant_message, error = handle_assistant_response(user_message, user_id)
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"message": assistant_message}), 200

# Ruta para crear un evento en Google Calendar
@app.route('/create-event', methods=['POST'])
def create_google_event():
    data = request.json
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    summary = data.get('summary')
    description = data.get('description')
    attendees = data.get('attendees')
    reminders = data.get('reminders')

    if not start_time or not end_time or not summary:
        return jsonify({"error": "Faltan parámetros para crear el evento"}), 400

    try:
        event = create_event(start_time, end_time, summary, description, attendees, reminders)
        return jsonify({"event": event}), 200
    except Exception as e:
        return jsonify({"error": f"Error al crear el evento: {e}"}), 500

# Ruta para listar eventos
@app.route('/list-events', methods=['GET'])
def list_google_events():
    try:
        events = list_events()
        return jsonify({"events": events}), 200
    except Exception as e:
        return jsonify({"error": f"Error al listar eventos: {e}"}), 500

# Ruta para eliminar un evento
@app.route('/delete-event', methods=['POST'])
def delete_google_event():
    data = request.json
    event_summary = data.get('event_summary')
    if not event_summary:
        return jsonify({"error": "Falta el resumen del evento"}), 400

    try:
        result = delete_event(event_summary)
        return jsonify({"message": result}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar el evento: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
