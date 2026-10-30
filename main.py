
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import uuid
import random
import json
import base64
import area_hints

app = Flask(__name__)
app.secret_key = "skibidi-toilet"

@app.route("/")
def index():
    return redirect("/start")

@app.route("/start")
def start():
    return render_template("start.html")

@app.route("/api/get_initial_data", methods=["POST"])
def get_initial_data():
    content = request.get_json(silent = True).get("content", "")
    with get_db() as db:
        user_id = content["user_id"]
        query = db.execute("SELECT * FROM registrations WHERE id = ?", (user_id,))
        user_data = dict(query.fetchone())

        user_path = json.loads(user_data["path"])
        station_index = user_path["path"][user_path["current"]]

    return jsonify({"success": True, "user_info": {
        "team_name": user_data["team_name"],
        "hint": area_hints.hints[station_index]
    }})

@app.route("/api/registration", methods=["POST"])
def registration():
    content = request.get_json(silent = True).get("content", "")
    print(content)

    try:
        with get_db() as db:
            unique_id = str(uuid.uuid4())
            new_path = [0, 1, 2, 3, 4, 5]
            random.shuffle(new_path)
            path = json.dumps({
                "path": new_path,
                "current": 0
            })

            data = (unique_id, content["team_name"], f"#{content["unit_floor"].zfill(2)}-{content["unit_number"].zfill(2)}", int(content["pax"]), path)
            print(data)

            db.execute("""
                INSERT INTO registrations (id, team_name, unit_number, pax, path) VALUES (?, ?, ?, ?, ?)
            """, data)
    except sqlite3.Error as e:
        print(f"SQLite error code: {e.sqlite_errorcode}")
        print(f"SQLite error name: {e.sqlite_errorname}")

        unique_constraints = ["team_name", "unit_number"]
        for i, v in enumerate(unique_constraints):
            if ("registrations." + v) in str(e):
                return jsonify({
                    "success": False,
                    "content": i
                })

    return jsonify({
        "success": True,
        "content": unique_id
    })

@app.route("/game")
def game():
    return render_template("game.html")

@app.route("/api/submit_scan", methods=["POST"])
def submit_scan():
    data = request.get_json(silent = True) or {}
    info = data.get("content", "")
    try:
        user_id = info["user_id"]
        scanned = json.loads(base64.b64decode(info["decodedtext"].encode("utf-8")))
        print(scanned)

        with get_db() as db:
            query = db.execute("SELECT * FROM registrations WHERE id = ?", (user_id,))
            user_data = dict(query.fetchone())

            user_path = json.loads(user_data["path"])

            if user_path["path"][user_path["current"]] == scanned["station"]:
                user_path["current"] += 1
                print(user_path)
                db.execute("UPDATE registrations SET path = ? WHERE id = ?", (json.dumps(user_path), user_id))
                return {
                    "success": True,
                    "content": {
                        "correct": True,
                        "message": "Correct!"
                    }
                }
            else:
                return {
                    "success": True,
                    "content": {
                        "correct": False,
                        "message": "Boo! Incorrect!"
                    }
                }
    except Exception:
        return jsonify({
            "success": False,
            "content": {
                "message": "Invalid QR code"
            }
        })

    return jsonify({"penis": "like"})

DATABASE = "registrations.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id TEXT PRIMARY KEY,
                team_name TEXT NOT NULL UNIQUE,
                unit_number TEXT NOT NULL UNIQUE,
                pax INTEGER NOT NULL
                    CHECK (pax BETWEEN 1 AND 6),
                path TEXT NOT NULL
            )
        """)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
