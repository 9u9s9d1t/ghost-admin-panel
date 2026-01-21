# ... (предыдущий код)

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
        
        if total_sent == 0 and workers[name].get('total', 0) > 0:
            workers[name]['start_session'] = now
        
        workers[name].update({
            "total": total_sent,
            "status": "РАБОТАЕТ" if data.get("status") else "ПАУЗА",
            "cpm": round(total_sent / ((now - workers[name]['start_session']).total_seconds() / 60), 1) if (now - workers[name]['start_session']).total_seconds() > 5 else 0,
            "mode": data.get("mode", "Type"),
            "speed": data.get("speed", 1.0),
            "phrases": data.get("phrases_content", ""),
            "last_seen": now.strftime("%H:%M:%S"),
            "last_seen_dt": now # Для проверки онлайна
        })

        # Расчет рейтинга для ответа клиенту
        all_workers = sorted(workers.items(), key=lambda x: x[1].get('total', 0), reverse=True)
        rank = 0
        diff = 0
        is_leader = False
        
        for i, (w_name, w_info) in enumerate(all_workers):
            if w_name == name:
                rank = i + 1
                is_leader = (i == 0)
                if not is_leader:
                    diff = all_workers[0][1].get('total', 0) - total_sent
                break

        res_data = {
            "status": "ok",
            "commands": commands_queue.pop(name, {}),
            "rating": {"rank": rank, "diff": diff, "is_leader": is_leader}
        }
        return jsonify(res_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin_action', methods=['POST'])
@requires_auth
def admin_action():
    data = request.json
    action = data.get("action")
    target = data.get("target") # Имя или 'all'

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
