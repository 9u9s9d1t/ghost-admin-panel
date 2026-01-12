import os
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
USER_LOGIN = "Admin"
USER_PASSWORD = "GhostType9991"

# Хранилище
workers = {}
commands_queue = {}
global_settings = {"common_text": ""}

def check_auth(username, password):
    return username == USER_LOGIN and password == USER_PASSWORD

def authenticate():
    return Response('Доступ ограничен.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/api/get_workers')
@requires_auth
def get_workers_api():
    return jsonify(workers)

@app.route('/api/update', methods=['POST'])
def update():
    try:
        data = request.json
        name = data.get("name")
        if not name: return jsonify({"status": "error"}), 400
        
        now = datetime.now()
        total_sent = data.get("total", 0)
        
        if name not in workers:
            workers[name] = {'start_session': now}
        
        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": round(total_sent / ((now - workers[name]['start_session']).total_seconds() / 60), 1) if (now - workers[name]['start_session']).total_seconds() > 10 else 0,
            "mode": data.get("mode", "Type"),
            "speed": data.get("speed", 1.0),
            "phrases": data.get("phrases_content", ""),
            "last_seen": now.strftime("%H:%M:%S")
        })
        
        cmds = commands_queue.get(name, {})
        if global_settings["common_text"]: cmds["new_text"] = global_settings["common_text"]
        
        # Очищаем очередь после отправки команд софту
        commands_queue[name] = {}
        
        return jsonify({"status": "ok", "commands": cmds})
    except: return jsonify({"status": "error"}), 500

@app.route('/api/admin_action', methods=['POST'])
@requires_auth
def admin_action():
    try:
        data = request.json
        action = data.get("action")
        target = data.get("target")
        
        if target != "all" and target not in commands_queue:
            commands_queue[target] = {}

        if action == "set_text":
            text = data.get("text")
            if target == "all":
                global_settings["common_text"] = text
                for w in workers:
                    if w not in commands_queue: commands_queue[w] = {}
                    commands_queue[w]["new_text"] = text
            else:
                commands_queue[target]["new_text"] = text
                
        elif action == "reset":
            if target == "all":
                for w in workers:
                    if w not in commands_queue: commands_queue[w] = {}
                    commands_queue[w]["reset_stats"] = True
                    workers[w]['start_session'] = datetime.now()
            else:
                commands_queue[target]["reset_stats"] = True
                if target in workers: workers[target]['start_session'] = datetime.now()

        elif action == "toggle_status":
            if target in workers:
                current_is_ready = workers[target].get("status") == "РАБОТАЕТ"
                commands_queue[target]["set_status"] = not current_is_ready

        elif action == "update_config":
            commands_queue[target].update({
                "new_speed": data.get("speed"),
                "new_total": data.get("total"),
                "new_mode": data.get("mode")
            })

        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
