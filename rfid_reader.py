#!/home/Tp/HSproject/env/bin/python
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
import RPi.GPIO as GPIO
import sqlite3
from mfrc522 import SimpleMFRC522
import threading
import time
import atexit

app = Flask(__name__)
app.secret_key = 'parola'
socketio = SocketIO(app)

# Global variable for the active GPIO pin
active_pin = None
current_rfid = None
# Setup GPIO once at startup
GPIO.cleanup()
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
led_pins = [17, 27, 22]
for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Initialize RFID reader globally
reader = SimpleMFRC522()

# Configure database connection
conn = sqlite3.connect('rfid_system.db', check_same_thread=False)
c = conn.cursor()

def get_users():
    c.execute("SELECT * FROM users")
    return c.fetchall()

def get_access_log():
    c.execute("SELECT * FROM access_log ORDER BY timestamp DESC")
    return c.fetchall()

def get_user_by_tag(tag_id):
    c.execute("SELECT * FROM users WHERE tag_id = ?", (tag_id,))
    return c.fetchone()

# Background thread: continuously listens for RFID cards
def rfid_listener():
    global active_pin
    global current_rfid
    while True:
        try:
            print("RFID listener waiting for card...")
            card_id, card_text = reader.read()  # Blocking call
            scanned = str(card_id)
            current_rfid = scanned
            print(current_rfid)
            print("Scanned RFID:", scanned, card_text)
            # Process scanned RFID:
            if scanned == "289690225624":
                if active_pin != 17:
                    if active_pin:
                        GPIO.output(active_pin, GPIO.LOW)
                    active_pin = 17
                    GPIO.output(17, GPIO.HIGH)
                    c.execute("INSERT INTO access_log (tag_id, gpio_pin) VALUES (?, ?)", (card_id, 17))
                    conn.commit()
                    print("Activated GPIO 17 for RFID 1")
            elif scanned == "839647038315":
                if active_pin != 27:
                    if active_pin:
                        GPIO.output(active_pin, GPIO.LOW)
                    active_pin = 27
                    GPIO.output(27, GPIO.HIGH)
                    c.execute("INSERT INTO access_log (tag_id, gpio_pin) VALUES (?, ?)", (card_id, 27))
                    conn.commit()
                    print("Activated GPIO 27 for RFID 2")
            else:
                print("Unrecognized RFID:", scanned)
            # Emit the new active pin to all connected clients
            socketio.emit('rfid_update', {'active_pin': active_pin})
        except Exception as e:
            print("RFID listener error:", e)
        time.sleep(0.5)

# Start RFID listener in a background thread
listener_thread = threading.Thread(target=rfid_listener, daemon=True)
listener_thread.start()

atexit.register(GPIO.cleanup)

# Routes (registration, login, etc.) remain unchanged.
@app.route('/logout')
def logout():
    session.clear()
    flash('Ați fost deconectat cu succes!', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        try:
            print("Apropiați un tag RFID de cititor pentru înregistrare...")
            card_id = current_rfid
            print(f"ID tag: {card_id}")
            if get_user_by_tag(card_id):
                flash('Acest tag RFID este deja înregistrat. Încercați cu un alt tag.', 'danger')
                return redirect(url_for('register'))
            c.execute("SELECT gpio_pin FROM users")
            used_pins = [row[0] for row in c.fetchall()]
            available_pins = [pin for pin in led_pins if pin not in used_pins]
            if available_pins:
                gpio_pin = available_pins[0]
                c.execute("INSERT INTO users (name, tag_id, gpio_pin) VALUES (?, ?, ?)", (name, card_id, gpio_pin))
                conn.commit()
                flash('Înregistrare reușită!', 'success')
                return redirect(url_for('login'))
            else:
                flash('Nu mai sunt pini GPIO disponibili.', 'danger')
        except Exception as e:
            flash("Eroare: " + str(e), 'danger')
        # Do not call GPIO.cleanup() here
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            print("Apropiați un tag RFID de cititor pentru autentificare...")
           # card_id, card_text = reader.read()
         #   print("Scanned:", card_id, card_text)
            card_id = current_rfid
            user = get_user_by_tag(card_id)
            GPIO.setmode(GPIO.BCM)
            for pin in led_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            if user:
                session['current_user'] = {'name': user[1], 'tag_id': user[2], 'gpio_pin': user[3]}
                # Let the background thread manage the active pin
                flash('Autentificare reușită!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Tag RFID necunoscut. Încercați din nou.', 'danger')
        except Exception as e:
            flash("Eroare la autentificare: " + str(e), 'danger')
        # Do not call GPIO.cleanup() here
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    current_user = session.get('current_user')
    access_log = get_access_log()
    users = get_users()
    print("Dashboard entered. Active pin:", active_pin)
    # Build pin_statuses for all 40 pins
    pin_statuses = {}
    GPIO.setmode(GPIO.BCM)
    for pin in range(1, 41):
        if pin in led_pins:
            pin_statuses[pin] = "Activat" if (active_pin == pin and GPIO.input(pin) == GPIO.HIGH) else "Dezactivat"
        else:
            pin_statuses[pin] = "Dezactivat"
    # Mapping for physical layout (two columns: odd on left, even on right)
    pin_positions = {}
    left_start = 10
    right_start = 10
    gap = 65
    for i, pin in enumerate(range(1, 41, 2)):
        pin_positions[pin] = {'top': left_start + i * gap, 'left': 50}
    for i, pin in enumerate(range(2, 41, 2)):
        pin_positions[pin] = {'top': right_start + i * gap, 'left': 150}
    return render_template('dashboard.html',
                           access_log=access_log,
                           users=users,
                           pin_statuses=pin_statuses,
                           active_pin=active_pin,
                           current_user=current_user,
                           pin_positions=pin_positions)

@app.route('/users')
def users():
    users = get_users()
    return render_template('users.html', users=users)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=3070)
