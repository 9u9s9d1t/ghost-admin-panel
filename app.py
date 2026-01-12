import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Расширенное хранилище
workers = {}
commands_queue = {}
global_settings = {"common_text": ""}

@app.route('/')
def index():
    # Сортировка будет на стороне клиента (в браузере), так удобнее
    return render_template('index.html', workers=workers, global_text=global_settings["common_text"])

@app.route('/api/update', methods=['POST'])
def update():
    try:
        data = request.json
        name = data.get("name")
        if not name: return jsonify({"status": "error"}), 400
        
        # Расчет сообщений в минуту (CPM)
        now = datetime.now()
        total_sent = data.get("total", 0)
        
        if name in workers:
            start_time = workers[name].get('start_session', now)
            diff = (now - start_time).total_seconds() / 60
            cpm = round(total_sent / diff, 1) if diff > 0.1 else 0
        else:
            workers[name] = {'start_session': now}
            cpm = 0

        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": cpm,
            "last_seen": now.strftime("%H:%M:%S")
        })
        
        cmds = commands_queue.get(name, {})
        # Добавляем глобальный текст в команды, если он есть
        if global_settings["common_text"]:
            cmds["new_text"] = global_settings["common_text"]
            
        if cmds: commands_queue[name] = {}
            
        return jsonify({"status": "ok", "commands": cmds})
    except:
        return jsonify({"status": "error"}), 500

@app.route('/api/admin_action', methods=['POST'])
def admin_action():
    data = request.json
    action = data.get("action")
    target = data.get("target") # "all" или имя воркера
    
    if action == "set_text":
        text = data.get("text")
        if target == "all":
            global_settings["common_text"] = text
        else:
            if target not in commands_queue: commands_queue[target] = {}
            commands_queue[target]["new_text"] = text
            
    elif action == "reset":
        if target == "all":
            for w in workers: 
                if w not in commands_queue: commands_queue[w] = {}
                commands_queue[w]["reset_stats"] = True
        else:
            if target not in commands_queue: commands_queue[target] = {}
            commands_queue[target]["reset_stats"] = True
            
    return jsonify({"status": "success"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
