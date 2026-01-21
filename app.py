import os
import io
import csv
from flask import Flask, render_template, request, jsonify, Response, make_response
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# --- НАСТРОЙКИ ДОСТУПА ---
USER_LOGIN = "Admin"
USER_PASSWORD = "GhostType9991"

# --- ХРАНИЛИЩЕ ДАННЫХ (В ПАМЯТИ) ---
workers = {}
commands_queue = {}
screenshots = {}

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
    # Помечаем, у кого есть готовый скриншот
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
    cw.writerow(['Имя сотрудника', 'Количество сообщений', 'Последняя активность'])
    sorted_names = sorted(workers.keys())
    for name in sorted_names:
        w = workers[name]
        cw.writerow([name, w.get('total', 0), w.get('last_seen', '')])
    
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
        
        # Если сбросили стату
        if total_sent == 0 and workers[name].get('total', 0) > 0:
            workers[name]['start_session'] = now
        
        # Обновляем данные сотрудника
        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": round(total_sent / ((now - workers[name]['start_session']).total_seconds() / 60), 1) if (now - workers[name]['start_session']).total_seconds() > 5 else 0,
            "mode": data.get("mode", "Type"),
            "speed": data.get("speed", 1.0),
            "phrases": data.get("phrases_content", ""),
            "last_seen": now.strftime("%H:%M:%S")
        })

        # Считаем рейтинг для софта
        all_workers_sorted = sorted(workers.items(), key=lambda x: x[1].get('total', 0), reverse=True)
        rank = 0
        diff = 0
        is_leader = False
        
        for i, (w_name, w_info) in enumerate(all_workers_sorted):
            if w_name == name:
                rank = i + 1
                is_leader = (i == 0)
                if not is_leader:
                    diff = all_workers_sorted[0][1].get('total', 0) - total_sent
                break

        return jsonify({
            "status": "ok",
            "commands": commands_queue.pop(name, {}),
            "rating": {"rank": rank, "diff": diff, "is_leader": is_leader}
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin_action', methods=['POST'])
@requires_auth
def admin_action():
    data = request.json
    action = data.get("action")
    target = data.get("target") 

    targets = list(workers.keys()) if target == 'all' else [target]

    for t in targets:
        if action == 'delete':
            if t in workers: del workers[t]
            if t in screenshots: del screenshots[t]
            if t in commands_queue: del commands_queue[t]
            continue

        if t not in commands_queue: commands_queue[t] = {}
        
        if action == 'shot': commands_queue[t]['make_screenshot'] = True
        elif action == 'set_text': commands_queue[t]['new_text'] = data.get('text')
        elif action == 'update_config':
            commands_queue[t].update({
                "new_mode": data.get("mode"),
                "new_speed": data.get("speed"),
                "new_total": data.get("total")
            })
        elif action == 'toggle_status':
            current = workers.get(t, {}).get('status') == "РАБОТАЕТ"
            commands_queue[t]['set_status'] = not current
        elif action == 'reset':
            commands_queue[t]['reset_stats'] = True
            if t in workers: workers[t]['start_session'] = datetime.now()

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)
