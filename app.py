import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Хранилище данных в оперативной памяти сервера
workers = {}
commands_queue = {}
global_settings = {"common_text": ""}

@app.route('/')
def index():
    # Передаем данные на страницу
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
        
        # Расчет CPM (Сообщений в минуту)
        if name in workers:
            start_time = workers[name].get('start_session', now)
            # Если это строка (после перезапуска сервера), переводим в объект времени
            if isinstance(start_time, str):
                start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                
            diff_minutes = (now - start_time).total_seconds() / 60
            cpm = round(total_sent / diff_minutes, 1) if diff_minutes > 0.1 else 0
        else:
            # Новый воркер
            workers[name] = {'start_session': now}
            cpm = 0

        # Обновляем данные сотрудника
        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": cpm,
            "mode": data.get("mode", "Type"),
            "phrases": data.get("phrases_content", ""), # Содержимое файла phrases.txt
            "last_seen": now.strftime("%H:%M:%S"),
            "start_session": workers[name]['start_session'] # Сохраняем время начала
        })
        
        # Проверяем наличие команд для этого воркера
        cmds = commands_queue.get(name, {})
