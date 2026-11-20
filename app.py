from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
import sqlite3, os, random, threading, time

BASE = Path(__file__).resolve().parent
DB = BASE / "smart_led.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-demo-secret")
lock = threading.RLock()
state = {
    "connected": False, "mode": "disconnected", "device": "ESP32_LED",
    "led_on": False, "brightness": 0, "started_at": None,
    "last_seen": None, "port": "", "last_error": ""
}
serial_conn = None

def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, display_name TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings(
            user_id INTEGER PRIMARY KEY, notifications INTEGER DEFAULT 1,
            theme TEXT DEFAULT 'dark', device_name TEXT DEFAULT 'ESP32_LED')""")
        con.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            command TEXT NOT NULL, brightness INTEGER NOT NULL, status TEXT NOT NULL,
            mode TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            led_on INTEGER NOT NULL, brightness INTEGER NOT NULL,
            voltage REAL, current_ma REAL, power_mw REAL, temperature REAL,
            mode TEXT NOT NULL)""")
        if not con.execute("SELECT id FROM users WHERE username='admin'").fetchone():
            cur = con.execute("INSERT INTO users(username,password,display_name) VALUES(?,?,?)",
                ("admin", generate_password_hash("admin123"), "Project Admin"))
            con.execute("INSERT INTO settings(user_id) VALUES(?)", (cur.lastrowid,))

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user_id" not in session: return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper

def log_event(command, brightness, status="Success"):
    with db() as con:
        con.execute("INSERT INTO events(timestamp,command,brightness,status,mode) VALUES(?,?,?,?,?)",
                    (datetime.now().isoformat(timespec="seconds"), command, int(brightness), status, state["mode"]))

def save_reading(v):
    with db() as con:
        con.execute("""INSERT INTO readings(timestamp,led_on,brightness,voltage,current_ma,power_mw,temperature,mode)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (datetime.now().isoformat(timespec="seconds"), int(v["led_on"]), int(v["brightness"]),
                     v.get("voltage"), v.get("current_ma"), v.get("power_mw"), v.get("temperature"), state["mode"]))
        con.execute("DELETE FROM readings WHERE id NOT IN (SELECT id FROM readings ORDER BY id DESC LIMIT 5000)")

def get_settings():
    with db() as con:
        return con.execute("SELECT * FROM settings WHERE user_id=?", (session["user_id"],)).fetchone()

def send_serial(command, brightness):
    global serial_conn
    if not serial_conn or not serial_conn.is_open:
        raise RuntimeError("Bluetooth serial port is not open. Pair the ESP32 and select its outgoing COM port.")
    if command == "DIM":
        payload = f"DIM,{brightness}\n"
    else:
        payload = command + "\n"
    serial_conn.write(payload.encode("utf-8"))
    serial_conn.flush()

def simulated_reading():
    # Clearly labelled demonstration telemetry; these are generated, not physical sensor measurements.
    on = state["led_on"]
    b = state["brightness"] if on else 0
    voltage = round(5.0 + random.uniform(-0.04, 0.04), 2)
    current = round((b / 100) * 18.0 + random.uniform(-0.35, 0.35), 2) if on else 0.0
    power = round(voltage * current, 2)
    temp = round(27.0 + (current * 0.42) + random.uniform(-0.3, 0.3), 1)
    return {"led_on": on, "brightness": b, "voltage": voltage if on else 0.0,
            "current_ma": current, "power_mw": power, "temperature": temp}

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        with db() as con: user=con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"]=user["id"]; session["display_name"]=user["display_name"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password. Please try again.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        events=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 8").fetchall()
        total=con.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
        settings=get_settings()
    return render_template("dashboard.html", rows=events, total=total, settings=settings, now=datetime.now())

@app.route("/analysis")
@login_required
def analysis():
    return render_template("analysis.html")

@app.route("/calculator", methods=["GET","POST"])
@login_required
def calculator():
    result=None
    if request.method=="POST":
        start=request.form.get("start_date")
        brightness=max(1,min(100,int(request.form.get("brightness",100))))
        nominal=25000
        estimated=int(nominal * (100/brightness))
        used=0
        try: used=max(0,(datetime.now()-datetime.strptime(start,"%Y-%m-%d")).days*8)
        except Exception: pass
        remaining=max(0,estimated-used)
        result={"estimated":estimated,"used":used,"remaining":remaining,"years":round(remaining/(8*365),1)}
    with db() as con: history=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 10").fetchall()
    return render_template("calculator.html", result=result, today=datetime.now().strftime("%Y-%m-%d"), read_history=history)

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    with db() as con:
        if request.method=="POST":
            con.execute("UPDATE settings SET notifications=?,theme=?,device_name=? WHERE user_id=?",
                (1 if request.form.get("notifications") else 0, request.form.get("theme","dark"),
                 request.form.get("device_name","ESP32_LED").strip() or "ESP32_LED", session["user_id"]))
            flash("Settings saved.", "success")
        data=con.execute("SELECT * FROM settings WHERE user_id=?", (session["user_id"],)).fetchone()
    return render_template("settings.html", settings=data)

@app.route("/about")
@login_required
def about():
    return render_template("about.html")

@app.route("/api/connect", methods=["POST"])
@login_required
def connect():
    global serial_conn
    data=request.get_json(silent=True) or {}
    mode=data.get("mode","demo")
    with lock:
        if mode == "demo":
            state.update(connected=True, mode="demo", device=data.get("device","ESP32_LED"),
                         last_seen=datetime.now().isoformat(timespec="seconds"), last_error="", port="")
            log_event("CONNECT", state["brightness"], "Demo connected")
            return jsonify(ok=True, message="Demo Bluetooth link connected. Telemetry is simulated.", status=state)
        if mode == "serial":
            port=(data.get("port") or "").strip()
            if not port: return jsonify(ok=False, message="Enter the paired ESP32 Bluetooth COM port (for example COM5)."), 400
            try:
                import serial
                if serial_conn and serial_conn.is_open: serial_conn.close()
                serial_conn=serial.Serial(port, 115200, timeout=1, write_timeout=1)
                time.sleep(1.5)
                state.update(connected=True, mode="serial", port=port, device="ESP32_LED",
                             last_seen=datetime.now().isoformat(timespec="seconds"), last_error="")
                log_event("CONNECT", state["brightness"], "Serial Bluetooth connected")
                return jsonify(ok=True, message=f"Connected to ESP32 through {port}.", status=state)
            except Exception as e:
                state.update(connected=False, mode="disconnected", last_error=str(e))
                return jsonify(ok=False, message=f"Could not open {port}: {e}"), 400
        return jsonify(ok=False, message="Unknown connection mode."), 400

@app.route("/api/disconnect", methods=["POST"])
@login_required
def disconnect():
    global serial_conn
    with lock:
        try:
            if serial_conn and serial_conn.is_open: serial_conn.close()
        except Exception: pass
        serial_conn=None
        state.update(connected=False, mode="disconnected", last_seen=None, port="")
        log_event("DISCONNECT", state["brightness"], "Disconnected")
    return jsonify(ok=True, message="Device disconnected.")

@app.route("/api/control", methods=["POST"])
@login_required
def control():
    data=request.get_json(silent=True) or {}
    command=str(data.get("command","")).upper()
    if command not in ["ON","OFF","DIM"]: return jsonify(ok=False,message="Unsupported command."),400
    try: brightness=max(0,min(100,int(data.get("brightness",100))))
    except Exception: return jsonify(ok=False,message="Brightness must be a number."),400
    with lock:
        if not state["connected"]: return jsonify(ok=False,message="Connect the demo device or ESP32 first."),409
        try:
            if state["mode"]=="serial": send_serial(command,brightness)
            if command=="OFF":
                state["led_on"]=False; state["brightness"]=0; state["started_at"]=None
            else:
                state["led_on"]=True; state["brightness"]=brightness if command=="DIM" else max(1,brightness)
                if not state["started_at"]: state["started_at"]=time.time()
            state["last_seen"]=datetime.now().isoformat(timespec="seconds")
            log_event(command,state["brightness"],"Success")
            return jsonify(ok=True,message=f"{command} command sent ({state['mode']} mode).",status=state)
        except Exception as e:
            log_event(command,brightness,f"Failed: {e}")
            return jsonify(ok=False,message=str(e)),500

@app.route("/api/live")
@login_required
def live():
    with lock:
        if state["connected"] and state["mode"]=="demo":
            v=simulated_reading()
            save_reading(v)
            state["last_seen"]=datetime.now().isoformat(timespec="seconds")
        elif state["connected"] and state["mode"]=="serial":
            # Firmware returns: STATUS,<led 0|1>,<brightness 0..100>
            try:
                serial_conn.reset_input_buffer()
                serial_conn.write(b"STATUS\n")
                line=serial_conn.readline().decode("utf-8",errors="replace").strip()
                parts=line.split(",")
                if len(parts)>=3 and parts[0]=="STATUS":
                    state["led_on"]=bool(int(parts[1])); state["brightness"]=max(0,min(100,int(parts[2])))
                    v={"led_on":state["led_on"],"brightness":state["brightness"],"voltage":None,
                       "current_ma":None,"power_mw":None,"temperature":None}
                    save_reading(v); state["last_seen"]=datetime.now().isoformat(timespec="seconds")
                else:
                    v={"led_on":state["led_on"],"brightness":state["brightness"],"voltage":None,
                       "current_ma":None,"power_mw":None,"temperature":None}
            except Exception as e:
                state["last_error"]=str(e); state["connected"]=False
                v={"led_on":False,"brightness":0,"voltage":None,"current_ma":None,"power_mw":None,"temperature":None}
        else:
            v={"led_on":False,"brightness":0,"voltage":None,"current_ma":None,"power_mw":None,"temperature":None}
        with db() as con:
            events=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 6").fetchall()
            count=con.execute("SELECT COUNT(*) n FROM readings").fetchone()["n"]
            on_seconds=0
            if state["started_at"] and state["led_on"]: on_seconds=int(time.time()-state["started_at"])
        return jsonify(status=state.copy(),reading=v,events=[dict(x) for x in events],
                       reading_count=count,operating_seconds=on_seconds,
                       server_time=datetime.now().isoformat(timespec="seconds"))

@app.route("/api/analysis")
@login_required
def api_analysis():
    # Keep the stream alive while the Analysis page is open, even if Dashboard is not.
    with lock:
        if state["connected"] and state["mode"] == "demo":
            save_reading(simulated_reading())
            state["last_seen"] = datetime.now().isoformat(timespec="seconds")
    with db() as con:
        events=[dict(x) for x in con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 500").fetchall()]
        readings=[dict(x) for x in con.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 120").fetchall()]
        total=con.execute("SELECT COUNT(*) n FROM readings").fetchone()["n"]
    counts={k:sum(1 for e in events if e["command"]==k) for k in ["ON","OFF","DIM"]}
    vals=[r["brightness"] for r in readings]
    labels=[r["timestamp"][11:19] for r in readings[::-1]]
    brightness=[r["brightness"] for r in readings[::-1]]
    power=[r["power_mw"] for r in readings[::-1] if r["power_mw"] is not None]
    return jsonify(counts=counts,total_events=len(events),total_readings=total,
                   average_brightness=round(sum(vals)/len(vals),1) if vals else 0,
                   labels=labels,brightness=brightness,readings=readings[:20],
                   power=power,mode=state["mode"],connected=state["connected"])

if __name__=="__main__":
    init_db()
    app.run(host="127.0.0.1",port=5000,debug=False,threaded=True)
