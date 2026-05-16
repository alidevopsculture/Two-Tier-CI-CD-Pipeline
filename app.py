import os
import time
import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# Configure MySQL from environment variables (defaults to 'mysql' to match service name)
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'default_user')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'default_password')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'default_db')

# Initialize MySQL
mysql = MySQL(app)

def init_db():
    with app.app_context():
        # Loop up to 15 times to give MySQL time to fully initialize files
        for attempt in range(15):
            try:
                print(f"Connecting to database at {app.config['MYSQL_HOST']}... (Attempt {attempt + 1}/15)")
                cur = mysql.connection.cursor()
                cur.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message TEXT
                );
                ''')
                mysql.connection.commit()  
                cur.close()
                print("Database table checked/created successfully!")
                return # Connection successful, exit the retry loop
            except (MySQLdb.OperationalError, MySQLdb.InterfaceError) as e:
                print(f"Database not ready yet. Retrying in 5 seconds... Error: {e}")
                time.sleep(5)
        
        # If all retries fail
        raise Exception("Could not connect to the database after multiple attempts.")

@app.route('/')
def hello():
    cur = mysql.connection.cursor()
    cur.execute('SELECT message FROM messages')
    messages = cur.fetchall()
    cur.close()
    return render_template('index.html', messages=messages)

@app.route('/submit', methods=['POST'])
def submit():
    new_message = request.form.get('new_message')
    cur = mysql.connection.cursor()
    cur.execute('INSERT INTO messages (message) VALUES (%s)', [new_message])
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': new_message})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')