from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'kenya_phone_store_secret_key'

def get_db_connection():
    # Utilizing your original database filename structure clears existing runtime cache conflicts
    db_path = os.path.join(base_dir, 'store.db')
    conn = sqlite3.connect(db_path)
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
            image TEXT NOT NULL,
            search_name TEXT NOT NULL,
            search_desc TEXT NOT NULL,
            brand_tag TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES ('admin', '1234')")
        
    default_phones = [
        ("Samsung Galaxy S25 Ultra", 165000, "12GB RAM, 512GB Storage. Flagship performance device.", "vector_css", "samsung galaxy s25 ultra", "12gb ram 512gb storage flagship performance device", "samsung"),
        ("Samsung Galaxy S24 Ultra", 135000, "12GB RAM, 256GB Storage. Solid Titanium Frame with Galaxy AI.", "vector_css", "samsung galaxy s24 ultra", "12gb ram 256gb storage solid titanium frame with galaxy ai", "samsung"),
        ("Samsung Galaxy S23 Ultra", 110000, "8GB RAM, 256GB Storage. 100x Zoom Space Engine & S-Pen.", "vector_css", "samsung galaxy s23 ultra", "8gb ram 256gb storage 100x zoom space engine s-pen", "samsung"),
        ("Samsung Galaxy A55 5G", 54000, "8GB RAM, 128GB Storage. Protective Metal Frame setup.", "vector_css", "samsung galaxy a55 5g", "8gb ram 128gb storage protective metal frame setup", "samsung"),
        ("Samsung Galaxy A35 5G", 42000, "6GB RAM, 128GB Storage. Super AMOLED Display panel.", "vector_css", "samsung galaxy a35 5g", "6gb ram 128gb storage super amoled display panel", "samsung"),
        ("Samsung Galaxy A15", 23000, "4GB RAM, 128GB Storage. Smooth 90Hz Display core.", "vector_css", "samsung galaxy a15", "4gb ram 128gb storage smooth 90hz display core", "samsung"),
        ("Tecno Camon 30 Pro 5G", 48000, "12GB RAM, 512GB Storage. Flagship Dimensity Processing Unit.", "vector_css", "tecno camon 30 pro 5g", "12gb ram 512gb storage flagship dimensity processing unit", "tecno"),
        ("Tecno Camon 20 Premier", 39500, "8GB RAM, 512GB Storage. Premium Leather Design Layout.", "vector_css", "tecno camon 20 premier", "8gb ram 512gb storage premium leather design layout", "tecno"),
        ("Tecno Spark 20 Pro+", 29000, "8GB RAM, 256GB Storage. Curved Ergonomic Display setup.", "vector_css", "tecno spark 20 pro+", "8gb ram 256gb storage curved ergonomic display setup", "tecno"),
        ("Tecno Spark 20 Go", 14500, "4GB RAM, 64GB Storage. Dual Speakers with Dynamic UI.", "vector_css", "tecno spark 20 go", "4gb ram 64gb storage dual speakers with dynamic ui", "tecno"),
        ("itel S25 Pro", 18500, "8GB RAM, 256GB Storage. Slim Profile Body and AMOLED Screen.", "vector_css", "itel s25 pro", "8gb ram 256gb storage slim profile body and amoled screen", "itel"),
        ("itel S23 Plus", 21000, "8GB RAM, 256GB Storage. Immersive 3D Curved Panels.", "vector_css", "itel s23 plus", "8gb ram 256gb storage immersive 3d curved panels", "itel"),
        ("itel P55 5G", 16000, "6GB RAM, 128GB Storage. Affordable 5G Module.", "vector_css", "itel p55 5g", "6gb ram 128gb storage affordable 5g module", "itel"),
        ("itel A70", 12800, "4GB RAM, 128GB Storage. Built for reliable everyday performance.", "vector_css", "itel a70", "4gb ram 128gb storage built for reliable everyday performance", "itel"),
        ("itel A05s", 9500, "2GB RAM, 32GB Storage. Essential tier for mobile browsing.", "vector_css", "itel a05s", "2gb ram 32gb storage essential tier for mobile browsing", "itel"),
        ("iPhone 15 Pro Max", 165000, "256GB Storage. Premium High-speed Processing blocks.", "vector_css", "iphone 15 pro max", "256gb storage premium high-speed processing blocks", "premium"),
        ("Xiaomi Redmi Note 13 Pro", 38500, "8GB RAM, 256GB Storage. 5000mAh long battery module.", "vector_css", "xiaomi redmi note 13 pro", "8gb ram 256gb storage 5000mah long battery module", "premium")
    ]
    cursor.executemany("INSERT INTO phones (name, price, description, image, search_name, search_desc, brand_tag) VALUES (?, ?, ?, ?, ?, ?, ?)", default_phones)
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
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    phone_id = request.args.get('id', type=int)
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
        ''', (session['user'], phone['name'], phone['price'], phone_number, 'Pending Verification', timestamp))
        conn.commit()
        conn.close()
        return redirect(url_for('orders'))
    return render_template('pay.html', phone=phone)

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
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        if 'add_phone' in request.form:
            name = request.form.get('name')
            price = int(request.form.get('price'))
            description = request.form.get('description')
            image = request.form.get('image')
            s_name = name.lower()
            s_desc = description.lower()
            b_tag = "samsung" if "samsung" in s_name else "tecno" if "tecno" in s_name else "itel" if "itel" in s_name else "premium"
            
            conn.execute('INSERT INTO phones (name, price, description, image, search_name, search_desc, brand_tag) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                         (name, price, description, image, s_name, s_desc, b_tag))
            conn.commit()
        elif 'delete_id' in request.form:
            delete_id = request.form.get('delete_id')
            conn.execute('DELETE FROM phones WHERE id = ?', (delete_id,))
            conn.commit()
        return redirect(url_for('admin_panel'))
        
    all_phones = conn.execute('SELECT * FROM phones ORDER BY id DESC').fetchall()
    all_orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', phones=all_phones, orders=all_orders)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
