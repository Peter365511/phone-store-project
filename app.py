from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kenya_phone_store_secret_key'

def get_db_connection():
    # Bumping to version 40 completely drops old database states to prevent data errors
    conn = sqlite3.connect('store_v40.db')
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
    # Sending exact parameters labeled as 'products'
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
        ''', (session['user'], phone['name'], phone['price'], phone_number, 'Pending API M-Pesa Verification', timestamp))
        conn.commit()
        conn.close()
        
        flash(f"M-Pesa STK push request pushed out to {phone_number} successfully!", "success")
        return redirect(url_for('orders'))
    return render_template('pay.html', phone=phone)

@app.route('/simulate/mpesa-success/<int:order_id>')
def simulate_mpesa_success(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    order = cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order:
        cursor.execute("UPDATE orders SET status = 'Paid via M-Pesa (Verified Confirmation)' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        flash(f"Safaricom Mock Callback simulated successfully for Order #ORD-{order_id:05d}!", "success")
        return redirect(url_for('orders'))
    conn.close()
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    if 'user' not in session:
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
