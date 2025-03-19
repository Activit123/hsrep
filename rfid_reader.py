#!/home/Tp/HSproject/env/bin/python
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
import RPi.GPIO as GPIO
import sqlite3
from mfrc522 import SimpleMFRC522
import spidev
import threading
import time
import atexit

app = Flask(__name__)
app.secret_key = 'parola'
socketio = SocketIO(app)
spi = spidev.SpiDev()
spi.open(0, 0)  # Deschide SPI bus 0, CS0
spi.max_speed_hz = 1250000  # Setează frecvența SPI la 10 MHz
# Global variables for RFID and motor control
active_pin = None
current_rfid = None

# Setup GPIO once at startup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Define RFID-related LED pins
led_pins = [17, 27, 22]
for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Define motor control pins
FORWARD_PIN = 18   # Pin for forward movement
REVERSE_PIN = 23   # Pin for reverse movement
motor_pins = [FORWARD_PIN, REVERSE_PIN]
for pin in motor_pins:
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

# Motor control functions
def forward():
    GPIO.output(REVERSE_PIN, GPIO.LOW)
    GPIO.output(FORWARD_PIN, GPIO.HIGH)
    print("Motor running forward.")

def reverse():
    GPIO.output(FORWARD_PIN, GPIO.LOW)
    GPIO.output(REVERSE_PIN, GPIO.HIGH)
    print("Motor running in reverse.")

def stop_motor():
    GPIO.output(FORWARD_PIN, GPIO.LOW)
    GPIO.output(REVERSE_PIN, GPIO.LOW)
    print("Motor stopped.")

# SocketIO event handlers for motor control
@socketio.on('motor_forward')
def handle_motor_forward(data):
    forward()
    emit('motor_status', {'status': 'forward'})

@socketio.on('motor_reverse')
def handle_motor_reverse(data):
    reverse()
    emit('motor_status', {'status': 'reverse'})

@socketio.on('motor_stop')
def handle_motor_stop(data):
    stop_motor()
    emit('motor_status', {'status': 'stopped'})

# Background thread: continuously listens for RFID cards
def rfid_listener():
    global active_pin, current_rfid
    print("Starting RFID listener...")
    while True:
        try:
            print("RFID listener waiting for card...")
            # Read RFID (this is a blocking call)
            card_id, card_text = reader.read()
            scanned = str(card_id)
            current_rfid = scanned
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
                c.execute("INSERT INTO access_log (tag_id, gpio_pin) VALUES (?, ?)", (card_id, 0))
                conn.commit()
            # Emit the new active pin to all connected clients
            socketio.emit('rfid_update', {'active_pin': active_pin})
        except Exception as e:
            print("RFID listener error:", e)
        time.sleep(0.5)

# Start RFID listener in a background thread
listener_thread = threading.Thread(target=rfid_listener, daemon=True)
listener_thread.start()

atexit.register(GPIO.cleanup)

# Routes
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
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            print("Apropiați un tag RFID de cititor pentru autentificare...")
            card_id = current_rfid
            user = get_user_by_tag(card_id)
            GPIO.setmode(GPIO.BCM)
            for pin in led_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            if user:
                session['current_user'] = {'name': user[1], 'tag_id': user[2], 'gpio_pin': user[3]}
                flash('Autentificare reușită!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Tag RFID necunoscut. Încercați din nou.', 'danger')
        except Exception as e:
            flash("Eroare la autentificare: " + str(e), 'danger')
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
    # Măsurarea frecvenței SPI:
    configured_spi_frequency = spi.max_speed_hz  # Frecvența setată
    n_transfers = 100
    dummy_data = [0x00, 0x00, 0x00, 0x00]  # Se trimit 4 octeți (32 de biți)
    start_time = time.perf_counter()
    for _ in range(n_transfers):
        spi.xfer2(dummy_data)
    end_time = time.perf_counter()
    avg_transfer_time = (end_time - start_time) / n_transfers
    # Calculăm frecvența efectivă în Hz: 32 de biți / timpul mediu de transfer
    measured_spi_frequency = 32 / avg_transfer_time

    return render_template('dashboard.html',
                           access_log=access_log,
                           users=users,
                           pin_statuses=pin_statuses,
                           active_pin=active_pin,
                           current_user=current_user,
                           pin_positions=pin_positions,
                           configured_spi_frequency=configured_spi_frequency,
                           measured_spi_frequency=measured_spi_frequency)

@app.route('/users')
def users():
    users = get_users()
    return render_template('users.html', users=users)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=3080, allow_unsafe_werkzeug=True)
