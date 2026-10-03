from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kenya_phone_store_secret_key'

def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
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
        
    cursor.execute("SELECT COUNT(*) FROM phones")
    if cursor.fetchone()[0] == 0:
        default_phones = [
            ("Samsung Galaxy S24 Ultra", 145000, "256GB Storage, 12GB RAM, 200MP Camera. Ultimate performance.", "https://unsplash.com"),
            ("iPhone 15 Pro Max", 165000, "Titanium design, A17 Pro chip, 256GB. Premium smartphones.", "https://unsplash.com"),
            ("Xiaomi Redmi Note 13 Pro", 38500, "8GB RAM, 256GB Storage, 5000mAh battery. Incredible value.", "https://unsplash.com")
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

# ================= NEW ADMIN MANAGEMENT CONTROL PATHS =================

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    # Security checkpoint: Restrict page to user session 'admin'
    if session.get('user') != 'admin':
        flash("Unauthorized Access! Admin session verification failed.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Check if user is adding a phone
        if 'add_phone' in request.form:
            name = request.form.get('name')
            price = int(request.form.get('price'))
            description = request.form.get('description')
            image = request.form.get('image')
            
            conn.execute('INSERT INTO phones (name, price, description, image) VALUES (?, ?, ?, ?)', 
                         (name, price, description, image))
            conn.commit()
            flash(f"Successfully added {name} to store inventory!", "success")
            
        # Check if user is deleting a phone
        elif 'delete_id' in request.form:
            delete_id = request.form.get('delete_id')
            conn.execute('DELETE FROM phones WHERE id = ?', (delete_id,))
            conn.commit()
            flash("Product listing removed completely.", "info")
            
        return redirect(url_for('admin_panel'))
        
    all_phones = conn.execute('SELECT * FROM phones ORDER BY id DESC').fetchall()
    all_orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('admin.html', products=all_phones, orders=all_orders)

if __name__ == '__main__':
    app.run(debug=True)

