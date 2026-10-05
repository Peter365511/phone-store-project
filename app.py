from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kenya_phone_store_secret_key'

def get_db_connection():
    # Cleaned and versioned connection layer to bypass old disk cache issues
    conn = sqlite3.connect('store_v4.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        
    # Full list of 17 devices seeding smoothly with identifiers mapped to the visual grid layers
    default_phones = [
        # --- PREMIUM ULTRA LAYERS ---
        ("Samsung Galaxy S25 Ultra", 165000, "12GB RAM, 512GB Storage. Flagship performance device.", "samsung_ultra"),
        ("Samsung Galaxy S24 Ultra", 135000, "12GB RAM, 256GB Storage. Solid Titanium Frame with Galaxy AI.", "samsung_ultra"),
        ("Samsung Galaxy S23 Ultra", 110000, "8GB RAM, 256GB Storage. 100x Zoom Space Engine & S-Pen.", "samsung_ultra"),
        
        # --- MID TIER SAMSUNG A SERIES ---
        ("Samsung Galaxy A55 5G", 54000, "8GB RAM, 128GB Storage. Protective Metal Frame setup.", "samsung_a"),
        ("Samsung Galaxy A35 5G", 42000, "6GB RAM, 128GB Storage. Super AMOLED Display panel.", "samsung_a"),
        ("Samsung Galaxy A15", 23000, "4GB RAM, 128GB Storage. Smooth 90Hz Display core.", "samsung_a"),

        # --- TECNO PERFORMANCE PLATERS ---
        ("Tecno Camon 30 Pro 5G", 48000, "12GB RAM, 512GB Storage. Flagship Dimensity Processing Unit.", "tecno"),
        ("Tecno Camon 20 Premier", 39500, "8GB RAM, 512GB Storage. Premium Leather Design Layout.", "tecno"),
        ("Tecno Spark 20 Pro+", 29000, "8GB RAM, 256GB Storage. Curved Ergonomic Display setup.", "tecno"),
        ("Tecno Spark 20 Go", 14500, "4GB RAM, 64GB Storage. Dual Speakers with Dynamic UI.", "tecno"),

        # --- ITEL VALUE SERIES ---
        ("itel S25 Pro", 18500, "8GB RAM, 256GB Storage. Slim Profile Body and AMOLED Screen.", "itel"),
        ("itel S23 Plus", 21000, "8GB RAM, 256GB Storage. Immersive 3D Curved Panels.", "itel"),
        ("itel P55 5G", 16000, "6GB RAM, 128GB Storage. Affordable 5G Module.", "itel"),
        ("itel A70", 12800, "4GB RAM, 128GB Storage. Built for reliable everyday performance.", "itel"),
        ("itel A05s", 9500, "2GB RAM, 32GB Storage. Essential tier for mobile browsing.", "itel"),
        
        # --- ALTERNATIVE HISTORICAL DATA ---
        ("iPhone 15 Pro Max", 165000, "256GB Storage. Premium High-speed Processing blocks.", "iphone"),
        ("Xiaomi Redmi Note 13 Pro", 38500, "8GB RAM, 256GB Storage. 5000mAh long battery module.", "xiaomi")
    ]
    cursor.executemany("INSERT INTO phones (name, price, description, image) VALUES (?, ?, ?, ?)", default_phones)
    conn.commit()
    conn.close()

def generate_invoice_file(username, item_name, amount, phone_number, order_id):
    if not os.path.exists('invoices'):
        os.makedirs('invoices')
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"invoices/invoice_ORD{order_id}.txt"
    invoice_content = f"""
==================================================
              KENYA PHONE HUB STORE
            OFFICIAL PAYMENT INVOICE
==================================================
Invoice ID     : ORD-{order_id:05d}
Date & Time    : {current_time}
Customer Name  : {username}
Payment Channel: Safaricom M-Pesa Express
==================================================
ITEM DETAILS:
Product Name   : {item_name}
Total Paid     : KSh {amount:,.2f}
M-Pesa Number  : {phone_number}
Transaction Status: SUCCESSFUL / PAID
==================================================
         Thank you for shopping with us!
==================================================
"""
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(invoice_content.strip())

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
        finally:
            conn.close()
    return render_template('register.html')

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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (username, item_name, amount, phone_number, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user'], phone['name'], phone['price'], phone_number, 'Paid via M-Pesa STK Push', timestamp))
        new_order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        generate_invoice_file(session['user'], phone['name'], phone['price'], phone_number, new_order_id)
        flash(f"Payment confirmed for {phone['name']}!", "success")
        return redirect(url_for('orders'))
    return render_template('pay.html', phone=phone)

@app.route('/orders')
def orders():
    if 'user' not in session:
        flash("Please log in to view your orders!", "danger")
        return redirect(url_for('login'))
    conn = get_db_connection()
    user_orders = conn.execute('SELECT * FROM orders WHERE username = ? ORDER BY id DESC', (session['user'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=user_orders)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if session.get('user') != 'admin':
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        if 'add_phone' in request.form:
            name = request.form.get('name')
            price = int(request.form.get('price'))
            description = request.form.get('description')
            image = request.form.get('image')
            conn.execute('INSERT INTO phones (name, price, description, image) VALUES (?, ?, ?, ?)', 
                         (name, price, description, image))
            conn.commit()
            flash(f"Successfully added {name}!", "success")
        elif 'delete_id' in request.form:
            delete_id = request.form.get('delete_id')
            conn.execute('DELETE FROM phones WHERE id = ?', (delete_id,))
            conn.commit()
            flash("Listing removed.", "info")
        return redirect(url_for('admin_panel'))
        
    all_phones = conn.execute('SELECT * FROM phones ORDER BY id DESC').fetchall()
    all_orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', phones=all_phones, orders=all_orders)

if __name__ == '__main__':
    # Binds production host environment patterns cleanly for Render cloud stacks
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
