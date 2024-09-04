from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import bcrypt
import requests
import googlemaps

app = Flask(__name__)
app.secret_key = '7cb20e6b5b657663843f4cd025c71f364686f447ed235709'

# Initialize Google Maps client
gmaps = googlemaps.Client(key='AIzaSyDybq2mxujekZVivmr03Y5-GGHXesn4TLI')

# Initialize Gemini API key and URL
gemini_api_key = 'AIzaSyDeqaZ-9kxMy8WeWOnQbgLy2EIkGOAkCPg'
gemini_api_url = 'https://api.gemini.com/v1/'

# Database setup
DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def check_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Initialize the database
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      name TEXT NOT NULL, 
                      email TEXT UNIQUE NOT NULL, 
                      password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

@app.route('/')
def landing_page():
    return render_template('landing_page/index.html')

@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot/index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if user and check_password(password, user[3]):
                return jsonify({'redirect': url_for('chatbot_page')})
            else:
                return jsonify({'message': 'Incorrect email or password.', 'field': 'email'})
        else:
            email = request.form.get('email')
            password = request.form.get('password')

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if user and check_password(password, user[3]):
                return redirect('/chatbot')
            else:
                flash("Incorrect email or password.")
                return redirect(url_for('login_page'))

    return render_template('login/index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))

        hashed_password = hash_password(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login_page'))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            conn.close()
            return redirect(url_for('register'))

    return render_template('register/index.html')

@app.route('/route', methods=['GET'])
def get_route():
    start = request.args.get('start')
    end = request.args.get('end')

    directions_result = gmaps.directions(start, end)
    return jsonify(directions_result)

@app.route('/chatbot_query', methods=['POST'])
def chatbot_query():
    if request.is_json:
        data = request.get_json()
        user_message = data.get('query', '').lower()
        route = data.get('route', {})

        response = process_chatbot_message(user_message, route)
        return jsonify({"response": response})
    else:
        return jsonify({"error": "Invalid input, please send a JSON payload"}), 400

def process_chatbot_message(message, route):
    if 'route' in message:
        if 'distance' in message:
            return f"The distance of the route is {route.get('distance', 'unknown')} meters."
        elif 'duration' in message:
            return f"The estimated duration of the route is {route.get('duration', 'unknown')} seconds."
        elif 'steps' in message or 'directions' in message:
            steps = "\n".join(route.get('steps', ['No steps available']))
            return f"Here are the directions:\n{steps}"
        else:
            return "Please ask about the distance, duration, or steps of the route."
    
    # Fallback to Gemini API if the query is not related to route details
    return query_gemini_api(message)

def query_gemini_api(question):
    headers = {
        'Authorization': f'Bearer {gemini_api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'query': question
    }

    response = requests.post(gemini_api_url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json().get('result', 'Sorry, I could not find any information on that.')
    else:
        result = 'Sorry, there was an issue with the API request.'

    return result

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
