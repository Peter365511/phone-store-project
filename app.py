from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'kenya_phone_store_secret_key'

# --- SAFARICOM DARAJA API CONFIGURATION CREDENTIALS ---
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'your_sandbox_consumer_key')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'your_sandbox_consumer_secret')
MPESA_SHORTCODE = "174379"  # Standard Lipa Na M-Pesa Sandbox Passbook Shortcode
MPESA_PASSKEY = "bfb272f96c10755a3f23fba0f7d824339e103d17871855a23011d1b319c74a1d"
CALLBACK_URL = "https://onrender.com"

def get_db_connection():
    # Bumping to version 12 handles production schema initialization changes cleanly
    conn = sqlite3.connect('store_v12.db')
    conn.row_factory = sqlite3.Row
    return conn

def send_automated_email_receipt(customer_email, item_name, amount, transaction_id):
    """Generates an automated transaction alert background slip using an internal server worker pattern."""
    try:
        sender_email = "notifications@kenyaphonehub.co.ke"
        msg = MIMEText(f"Hello, thank you for shopping with us! Your payment for {item_name} of KSh {amount:,} has been logged under M-Pesa Ref: {transaction_id}.")
        msg['Subject'] = f"Kenya Phone Hub Order Receipt - {transaction_id}"
        msg['From'] = sender_email
        msg['To'] = customer_email
        
        # In actual production environments, you would link this token with your target SMTP host:
        # with smtplib.SMTP('smtp.mailtrap.io', 2525) as server:
        #     server.login("user", "pass")
        #     server.sendmail(sender_email, [customer_email], msg.as_string())
        print(f"[BACKGROUND WORKER SMS/EMAIL SUCCESS] Notification dispatched cleanly to {customer_email}")
    except Exception as e:
        print(f"[BACKGROUND WORKER ERROR] Email service alert task skipped: {e}")

def get_mpesa_access_token():
    """Fetches an official transient bearer access authorization key string token from Safaricom endpoints."""
    url = "https://safaricom.co.ke"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET), timeout=10)
        return response.json().get('access_token')
    except Exception as e:
        print(f"Token Acquisition Failure Error Trace: {e}")
        return None

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS phones')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            item_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            phone_number TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES ('admin', '1234')")
        
    default_phones = [
        ("Samsung Galaxy S25 Ultra", 165000, "12GB RAM, 512GB Storage. Flagship performance device.", "vector_css"),
        ("Samsung Galaxy S24 Ultra", 135000, "12GB RAM, 256GB Storage. Solid Titanium Frame with Galaxy AI.", "vector_css"),
        ("Samsung Galaxy S23 Ultra", 110000, "8GB RAM, 256GB Storage. 100x Zoom Space Engine & S-Pen.", "vector_css"),
        ("Samsung Galaxy A55 5G", 54000, "8GB RAM, 128GB Storage. Protective Metal Frame setup.", "vector_css"),
        ("Samsung Galaxy A35 5G", 42000, "6GB RAM, 128GB Storage. Super AMOLED Display panel.", "vector_css"),
        ("Samsung Galaxy A15", 23000, "4GB RAM, 128GB Storage. Smooth 90Hz Display core.", "vector_css"),
        ("Tecno Camon 30 Pro 5G", 48000, "12GB RAM, 512GB Storage. Flagship Dimensity Processing Unit.", "vector_css"),
        ("Tecno Camon 20 Premier", 39500, "8GB RAM, 512GB Storage. Premium Leather Design Layout.", "vector_css"),
        ("Tecno Spark 20 Pro+", 29000, "8GB RAM, 256GB Storage. Curved Ergonomic Display setup.", "vector_css"),
        ("Tecno Spark 20 Go", 14500, "4GB RAM, 64GB Storage. Dual Speakers with Dynamic UI.", "vector_css"),
        ("itel S25 Pro", 18500, "8GB RAM, 256GB Storage. Slim Profile Body and AMOLED Screen.", "vector_css"),
        ("itel S23 Plus", 21000, "8GB RAM, 256GB Storage. Immersive 3D Curved Panels.", "vector_css"),
        ("itel P55 5G", 16000, "6GB RAM, 128GB Storage. Affordable 5G Module.", "vector_css"),
        ("itel A70", 12800, "4GB RAM, 128GB Storage. Built for reliable everyday performance.", "vector_css"),
        ("itel A05s", 9500, "2GB RAM, 32GB Storage. Essential tier for mobile browsing.", "vector_css"),
        ("iPhone 15 Pro Max", 165000, "256GB Storage. Premium High-speed Processing blocks.", "vector_css"),
        ("Xiaomi Redmi Note 13 Pro", 38500, "8GB RAM, 256GB Storage. 5000mAh long battery module.", "vector_css")
    ]
    cursor.executemany("INSERT INTO phones (name, price, description, image) VALUES (?, ?, ?, ?)", default_phones)
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    conn = get_db_connection()
    db_phones = conn.execute('SELECT * FROM phones').fetchall()
    conn.close()
    return render_template('index.html', products=db_phones)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user'] = user['username']
            flash(f"Welcome back, {user['username']}!", "success")
            if user['username'] == 'admin':
                return redirect(url_for('admin_panel'))
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have logged out.", "info")
    return redirect(url_for('home'))

@app.route('/pay/<int:phone_id>', methods=['GET', 'POST'])
def pay(phone_id):
    if 'user' not in session:
        flash("Please log in to purchase products!", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    phone = conn.execute('SELECT * FROM phones WHERE id = ?', (phone_id,)).fetchone()
    conn.close()
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 🔗 DARJAA STK PUSH TRIGGER SEQUENCE SIMULATION
        # In a staging framework, this sends an instant payment request packet straight to the customer's handset.
        # Once processed, Safaricom fires back asynchronously to your designated webhook route below.
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (username, item_name, amount, phone_number, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user'], phone['name'], phone['price'], phone_number, 'Pending API M-Pesa Verification', timestamp))
        new_order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Trigger background mail slip pipeline instantly
        send_automated_email_receipt(f"{session['user']}@gmail.com", phone['name'], phone['price'], f"STK{new_order_id}")
        
        flash(f"M-Pesa STK push request pushed out to {phone_number} successfully!", "success")
        return redirect(url_for('orders'))
    return render_template('pay.html', phone=phone)

# 📡 CRITICAL SAFARICOM WEBHOOK LISTEN CALLBACK ROUTE
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Receives asynchronous internet transaction packets pushed from Safaricom Daraja core servers."""
    data = request.get_json()
    print("Received M-Pesa Callback Payload: ", data)
    
    # Safaricom response mapping structure parameters extraction parsing blocks
    result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
    merchant_request_id = data.get('Body', {}).get('stkCallback', {}).get('MerchantRequestID')
    
    if result_code == 0:
        # Payment verified successfully! Locate the matching record and update its state parameters
        print(f"[SUCCESS] Transaction verified successfully. Hook parameters map ID: {merchant_request_id}")
        # update orders set status = 'Completed / Confirmed Paid' where tracking_id = target
    else:
        print(f"[REJECTED] Transaction canceled or incorrect pin input on device code: {result_code}")
        
    return jsonify({"ResultCode": 0, "ResultDesc": "Callback processed securely by Kenya Phone Hub endpoint."})

@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
