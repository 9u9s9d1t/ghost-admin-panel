from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Хранилище данных
workers = {}
commands_queue = {}

@app.route('/')
def index():
    # Гарантируем передачу словаря, чтобы HTML не выдал ошибку
    return render_template('index.html', workers=workers)

@app.route('/api/update', methods=['POST'])
def update():
    try:
        data = request.json
        name = data.get("name")
        if not name:
            return jsonify({"status": "error"}), 400
        
        workers[name] = {
            "key": data.get("key", "—"),
            "total": data.get("total", 0),
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "mode": data.get("mode", "Type"),
            "speed": data.get("speed", 1.0),
            "last_seen": datetime.now().strftime("%H:%M:%S")
        }
        
        commands = commands_queue.get(name, {})
        if commands:
            commands_queue[name] = {} # Очищаем после отправки
            
        return jsonify({"status": "ok", "commands": commands})
    except:
        return jsonify({"status": "error"}), 500

@app.route('/api/send_command/<name>/<cmd>/<value>')
def send_command(name, cmd, value):
    if name not in commands_queue:
        commands_queue[name] = {}
    
    val = True if value.lower() == "true" else False if value.lower() == "false" else value
    commands_queue[name][cmd] = val
    return jsonify({"status": "command_sent"})

if __name__ == '__main__':
    app.run()
