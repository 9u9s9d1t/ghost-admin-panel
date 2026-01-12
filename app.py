from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Расширенная база данных
workers = {}
# Очередь команд: { "имя_сотрудника": { "команда": значение } }
commands_queue = {}

@app.route('/')
def index():
    return render_template('index.html', workers=workers)

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    name = data.get("name")
    
    # Обновляем данные о сотруднике
    workers[name] = {
        "key": data.get("key"),
        "total": data.get("total"),
        "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
        "mode": data.get("mode"),
        "speed": data.get("speed"),
        "last_seen": data.get("time", "Неизвестно")
    }
    
    # Проверяем, есть ли команды для этого сотрудника
    commands = commands_queue.get(name, {})
    # Очищаем очередь после выдачи (чтобы команда не выполнялась вечно)
    commands_queue[name] = {}
    
    return jsonify({"status": "ok", "commands": commands})

# Эндпоинт для отправки команд с сайта
@app.route('/api/send_command/<name>/<cmd>/<value>')
def send_command(name, cmd, value):
    if name not in commands_queue:
        commands_queue[name] = {}
    
    # Превращаем строковые значения в нужные типы
    if value.lower() == "true": val = True
    elif value.lower() == "false": val = False
    else: val = value
        
    commands_queue[name][cmd] = val
    return jsonify({"status": "command_sent", "to": name, cmd: val})

if __name__ == '__main__':
    app.run()
