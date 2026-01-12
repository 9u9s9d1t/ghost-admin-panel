from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Хранилище сотрудников и их команд
workers = {}
commands_queue = {}

@app.route('/')
def index():
    # Если воркеров нет, передаем пустой словарь
    return render_template('index.html', workers=workers)

@app.route('/api/update', methods=['POST'])
def update():
    try:
        data = request.json
        name = data.get("name")
        if not name:
            return jsonify({"status": "error"}), 400
        
        # Обновляем или создаем запись о сотруднике
        workers[name] = {
            "key": data.get("key", "—"),
            "total": data.get("total", 0),
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "mode": data.get("mode", "Type"),
            "speed": data.get("speed", 1.0),
            "last_seen": datetime.now().strftime("%H:%M:%S")
        }
        
        # Проверяем команды
        commands = commands_queue.get(name, {})
        if commands:
            commands_queue[name] = {} # Очищаем после выдачи
            
        return jsonify({"status": "ok", "commands": commands})
    except Exception as e:
        print(f"Ошибка в update: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/api/send_command/<name>/<cmd>/<value>')
def send_command(name, cmd, value):
    if name not in commands_queue:
        commands_queue[name] = {}
    
    # Преобразование типов
    if value.lower() == "true": val = True
    elif value.lower() == "false": val = False
    else: val = value
        
    commands_queue[name][cmd] = val
    return jsonify({"status": "command_sent", "to": name, "cmd": cmd, "value": val})

if __name__ == '__main__':
    app.run()
