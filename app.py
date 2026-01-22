import os, io, json
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

USER_LOGIN = "Admin"
USER_PASSWORD = "GhostType9991"

workers, commands_queue, screenshots = {}, {}, {}

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == USER_LOGIN and auth.password == USER_PASSWORD):
            return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index(): return render_template('index.html')

@app.route('/api/get_workers')
@requires_auth
def get_workers_api(): return jsonify(workers)

@app.route('/api/get_screenshot/<name>')
@requires_auth
def get_screenshot(name):
    if name in screenshots: return jsonify({"image": screenshots[name]})
    return jsonify({"error": "not found"}), 404

@app.route('/api/upload_shot', methods=['POST'])
def upload_shot():
    data = request.json
    if data.get("name") and data.get("image"):
        screenshots[data["name"]] = data["image"]; return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    name = data.get("name")
    if not name: return jsonify({"status": "error"}), 400
    
    # КИЕВСКОЕ ВРЕМЯ (UTC+2)
    now = datetime.utcnow() + timedelta(hours=2)
    
    if name not in workers: workers[name] = {'start_session': now}
    
    workers[name].update({
        "total": data.get("total", 0),
        "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
        "cpm": round(data.get("total", 0) / ((now - workers[name]['start_session']).total_seconds() / 60), 1) if (now - workers[name]['start_session']).total_seconds() > 5 else 0,
        "mode": data.get("mode", "Type"),
        "speed": data.get("speed", 1.0),
        "phrases": data.get("phrases_content", ""),
        "last_seen": now.strftime("%H:%M:%S")
    })
    
    all_w = sorted(workers.items(), key=lambda x: x[1].get('total', 0), reverse=True)
    rank = next((i for i, v in enumerate(all_w) if v[0] == name), 0) + 1
    return jsonify({"status": "ok", "commands": commands_queue.pop(name, {}), "rating": {"rank": rank, "diff": 0, "is_leader": rank == 1}})

@app.route('/api/admin_action', methods=['POST'])
@requires_auth
def admin_action():
    data = request.json
    action, target = data.get("action"), data.get("target")
    targets = list(workers.keys()) if target == 'all' else [target]
    for t in targets:
        if t not in commands_queue: commands_queue[t] = {}
        if action == 'delete':
            for d in [workers, screenshots, commands_queue]: 
                if t in d: del d[t]
        elif action == 'set_config':
            c = data.get('config', {})
            if 'speed' in c: commands_queue[t]['new_speed'] = c['speed']
            if 'mode' in c: commands_queue[t]['new_mode'] = c['mode']
            if 'total' in c: commands_queue[t]['new_total'] = c['total']
            if 'name' in c and c['name'] != t:
                commands_queue[t]['new_name'] = c['name']
                workers[c['name']] = workers.pop(t) # Мгновенный перенос в БД
        elif action == 'shot': commands_queue[t]['make_screenshot'] = True
        elif action == 'set_text': commands_queue[t]['new_text'] = data.get('text')
        elif action == 'reset': commands_queue[t]['reset_stats'] = True
        elif action == 'toggle_status': commands_queue[t]['set_status'] = not (workers.get(t,{}).get('status')=="РАБОТАЕТ")
    return jsonify({"status": "ok"})

if __name__ == '__main__': app.run(debug=True)
