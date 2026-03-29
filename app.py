from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from database import register_user, login_user, save_score, get_top_scores, init_db
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    username = session.get('username', None)
    if not username:
        return redirect(url_for('index'))
    scores = get_top_scores(10)
    return render_template('game.html', username=username, scores=scores)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    success, msg = login_user(username, password)
    if success:
        session['username'] = username
    return jsonify({"success": success, "message": msg})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    success, msg = register_user(username, password)
    if success:
        session['username'] = username
    return jsonify({"success": success, "message": msg})

@app.route('/api/save_score', methods=['POST'])
def api_save_score():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    data = request.get_json()
    score = data.get('score', 0)
    save_score(username, int(score))
    return jsonify({"success": True})

@app.route('/api/scores', methods=['GET'])
def api_scores():
    scores = get_top_scores(10)
    scores_list = [{"rank": i+1, "username": s[0], "score": s[1]} for i, s in enumerate(scores)]
    return jsonify(scores_list)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
