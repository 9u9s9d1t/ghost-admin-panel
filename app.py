from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# База данных в оперативной памяти (после перезагрузки сервера очистится)
# Для бесплатного тарифа этого хватит.
workers = {}

@app.route('/')
def index():
    # Главная страница с таблицей
    return render_template('index.html', workers=workers)

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    name = data.get("name")
    
    # Сохраняем данные от сотрудника
    workers[name] = {
        "key": data.get("key"),
        "total": data.get("total"),
        "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
        "mode": data.get("mode"),
        "speed": data.get("speed"),
        "last_seen": datetime.now().strftime("%H:%M:%S")
    }
    
    # Тут можно прописать логику команд (например, если в словаре есть флаг стопа)
    return jsonify({"status": "ok"})

@app.route('/api/reset/<name>')
def reset_worker(name):
    if name in workers:
        workers[name]['total'] = 0
    return "OK"

if __name__ == '__main__':
    app.run(debug=True)