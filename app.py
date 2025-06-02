from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, send

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DOWNLOAD_DIR = 'downloads'
PUBLIC_ROOM = 'public'
os.makedirs(os.path.join(DOWNLOAD_DIR, PUBLIC_ROOM), exist_ok=True)

def get_room_path(room_name):
    return os.path.join(DOWNLOAD_DIR, room_name)


@app.route('/')
def index():
    files = os.listdir(get_room_path(PUBLIC_ROOM))
    return render_template('index.html', files=files, rooms=sorted(set(os.listdir(os.path.join(DOWNLOAD_DIR)))))


@app.route('/order', methods=['POST'])
def order_public():
    file = request.files.get('file')
    if not file:
        return jsonify({'message': 'No file detected'}), 400

    try:
        filename = secure_filename(file.filename)
        file.save(os.path.join(get_room_path(PUBLIC_ROOM), filename))
        socketio.emit('upload_complete', {'files': sorted(set(os.listdir(os.path.join(DOWNLOAD_DIR,'public'))))})
        return 'ok',200
    except Exception as e:
        app.logger.error(f"Error saving public file: {e}")
        return jsonify({'message': str(e)}), 500


@app.route('/order/<room_name>', methods=['POST'])
def order_room(room_name):
    file = request.files.get('file')
    if not file:
        return redirect(url_for('room', room_name=room_name))

    try:
        room_path = get_room_path(room_name)
        os.makedirs(room_path, exist_ok=True)
        filename = secure_filename(file.filename)
        file.save(os.path.join(room_path, filename))
        socketio.emit('upload_room_complete', {'files': sorted(set(os.listdir(os.path.join(DOWNLOAD_DIR,room_name))))})
        return 'ok',200
    except Exception as e:
        app.logger.error(f"Error saving file to room {room_name}: {e}")
        return jsonify({'message': str(e)}), 500


@app.route('/room/<room_name>')
def room(room_name):
    room_path = get_room_path(room_name)
    files = os.listdir(room_path) if os.path.exists(room_path) else []
    return render_template('room.html', files=files, room_name=room_name)


@app.route('/create-room', methods=['POST'])
def create_room():
    room_name = request.form.get('room_name')
    if room_name:
        os.makedirs(get_room_path(room_name), exist_ok=True)
        socketio.emit('room_added', {'rooms': sorted(set(os.listdir(get_room_path(room_name))))})
    return jsonify({'message':'ok'})


@app.route('/download/<room_name>')
def download(room_name):
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'message': 'No filename specified'}), 400

    file_path = os.path.join(get_room_path(room_name), filename)
    if not os.path.exists(file_path):
        return jsonify({'message': 'File not found'}), 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Error sending file {filename} from {room_name}: {e}")
        return jsonify({'message': 'An error occurred', 'error': str(e)}), 500


if __name__ == '__main__':
    socketio.run(app,debug=True, host='0.0.0.0')
