import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Хранилище данных
workers = {}
commands_queue = {}
global_settings = {"common_text": ""}

@app.route('/')
def index():
    return render_template('index.html', workers=workers)

@app.route('/api/update', methods=['POST'])
def update():
    try:
        data = request.json
        name = data.get("name")
        if not name:
            return jsonify({"status": "error"}), 400
        
        now = datetime.now()
        total_sent = data.get("total", 0)
        
        # Расчет CPM
        if name in workers:
            start_time = workers[name].get('start_session', now)
            if isinstance(start_time, str):
                try:
                    start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                except:
                    start_time = now
            diff_minutes = (now - start_time).total_seconds() / 60
            cpm = round(total_sent / diff_minutes, 1) if diff_minutes > 0.1 else 0
        else:
            workers[name] = {'start_session': now}
            cpm = 0

        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": cpm,
            "mode": data.get("mode", "Type"),
            "phrases": data.get("phrases_content", ""),
            "last_seen": now.strftime("%H:%M:%S"),
            "start_session": workers[name]['start_session']
        })
        
        cmds = commands_queue.get(name, {})
        if global_settings["common_text"]:
            cmds["new_text"] = global_settings["common_text"]
            
        if name in commands_queue:
            commands_queue[name] = {}
            
        return jsonify({"status": "ok", "commands": cmds})
    except Exception as e:
        print(f"Update error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/api/admin_action', methods=['POST'])
def admin_action():
    try:
        data = request.json
        action = data.get("action")
        target = data.get("target")
        
        if action == "set_text":
            text = data.get("text")
            if target == "all":
                global_settings["common_text"] = text
                for w in workers:
                    if w not in commands_queue: commands_queue[w] = {}
                    commands_queue[w]["new_text"] = text
            else:
                if target not in commands_queue: commands_queue[target] = {}
                commands_queue[target]["new_text"] = text
                
        elif action == "reset":
            if target == "all":
                for w in workers:
                    if w not in commands_queue: commands_queue[w] = {}
                    commands_queue[w]["reset_stats"] = True
                    workers[w]['start_session'] = datetime.now()
            else:
                if target not in commands_queue: commands_queue[target] = {}
                commands_queue[target]["reset_stats"] = True
                if target in workers:
                    workers[target]['start_session'] = datetime.now()
                    
        elif action == "force_status":
            value = data.get("value")
            if target not in commands_queue: commands_queue[target] = {}
            commands_queue[target]["force_ready"] = value

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Action error: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
