import os
import io
import csv
from flask import Flask, render_template, request, jsonify, Response, make_response
from datetime import datetime
from functools import wraps

app = Flask(__name__)

USER_LOGIN = "Admin"
USER_PASSWORD = "GhostType9991"

workers = {}
commands_queue = {}
screenshots = {}
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
    # Добавляем инфо о наличии скриншота
    for name in workers:
        workers[name]['has_shot'] = name in screenshots
    return jsonify(workers)

@app.route('/api/get_screenshot/<name>')
@requires_auth
def get_screenshot(name):
    if name in screenshots:
        return jsonify({"image": screenshots[name]})
    return jsonify({"error": "not found"}), 404

@app.route('/api/upload_shot', methods=['POST'])
def upload_shot():
    data = request.json
    name = data.get("name")
    image = data.get("image")
    if name and image:
        screenshots[name] = image
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/api/download_report')
@requires_auth
def download_report():
    si = io.StringIO()
    si.write('\ufeff')
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['Имя сотрудника', 'Количество сообщений'])
    sorted_names = sorted(workers.keys())
    for name in sorted_names:
        cw.writerow([name, workers[name].get('total', 0)])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=report_{datetime.now().strftime('%d_%m_%Y')}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output

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
        
        all_workers = []
        for w_name, w_info in workers.items():
            all_workers.append({"name": w_name, "total": w_info.get("total", 0)})
        
        all_workers.sort(key=lambda x: x['total'], reverse=True)
        
        rank = 0
        diff_to_leader = 0
        for i, w in enumerate(all_workers):
            if w['name'] == name:
                rank = i + 1
                if i > 0:
                    diff_to_leader = all_workers[0]['total'] - w['total']
                break
        
        rating_info = {
            "rank": rank,
            "total_workers": len(all_workers),
            "diff": diff_to_leader,
            "is_leader": (rank == 1 and len(all_workers) > 1)
        }

        cmds = commands_queue.get(name, {})
        if global_settings["common_text"]: cmds["new_text"] = global_settings["common_text"]
        commands_queue[name] = {}
        
        return jsonify({
            "status": "ok", 
            "commands": cmds, 
            "rating": rating_info
        })
    except: return jsonify({"status": "error"}), 500

@app.route('/api/admin_action', methods=['POST'])
@requires_auth
def admin_action():
    try:
        data = request.json
        action, target = data.get("action"), data.get("target")
        if target != "all" and target not in commands_queue: commands_queue[target] = {}
        
        if action == "shot":
            commands_queue[target]["make_screenshot"] = True
        elif action == "set_text":
            if target == "all":
                global_settings["common_text"] = data.get("text")
                for w in workers: 
                    if w not in commands_queue: commands_queue[w] = {}
                    commands_queue[w]["new_text"] = data.get("text")
            else: commands_queue[target]["new_text"] = data.get("text")
        elif action == "reset":
            targets = workers.keys() if target == "all" else [target]
            for t in targets:
                if t not in commands_queue: commands_queue[t] = {}
                commands_queue[t]["reset_stats"] = True
                if t in workers: workers[t]['start_session'] = datetime.now()
        elif action == "toggle_status":
            if target in workers:
                commands_queue[target]["set_status"] = not (workers[target]["status"] == "РАБОТАЕТ")
        elif action == "update_config":
            commands_queue[target].update({
                "new_speed": data.get("speed"),
                "new_total": data.get("total"),
                "new_mode": data.get("mode")
            })
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
