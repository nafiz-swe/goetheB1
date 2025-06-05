from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import threading
import time
import webbrowser
import pyautogui
import mysql.connector
import uuid
from flask import make_response

app = Flask(__name__)
app.secret_key = "f8a1d5b65cc9473d931b407ec8e8573b"

TRIGGER_TEXTS = ["Select Module", "Select module", "select module", "SELECT MODULES"]

watching = {"b1": False, "b2": False, "kolkata_b1": False}
trigger_audio = {"b1": False, "b2": False, "kolkata_b1": False}

TARGET_URLS = {
    "b1": "https://www.goethe.de/ins/bd/en/spr/prf/gzb1.cfm",
    "b2": "https://www.goethe.de/ins/bd/en/spr/prf/gzb2.cfm",
    "kolkata_b1": "https://www.goethe.de/ins/in/en/sta/kol/prf/gzb1.cfm"
}


ALARM_LIST = [
    ("1-Morning.mp3", "Morning"),
    ("2-MorningBird1.mp3", "Morning Bird-1"),
    ("3-MorningBird2.mp3", "Morning Bird-2"),
    ("7-Melody.mp3", "Melody"),
    ("4-La_ilaha_ilallah.mp3", "La ilaha illallah"),
    ("5-Subhanallah.mp3", "Subhanallah"),
    ("6-Fire.mp3", "Fire"),
    ("8-kgf.mp3", "KGF Theme")
]

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",         # আপনার DB username
        password="",         # আপনার DB password
        database="goethe_alarm_db"
    )

def get_device_id():
    device_id = request.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())  # নতুন random device_id
    return device_id

def click_screen_center():
    screenWidth, screenHeight = pyautogui.size()
    x, y = screenWidth // 2, screenHeight // 2
    for i in range(3):
        pyautogui.click(x, y)
        time.sleep(0.1)  # শুধু 0.1 সেকেন্ড বিরতি


def check_condition_and_open(level):
    global watching, trigger_audio
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--blink-settings=imagesEnabled=false")  # Images disabled for faster load
    driver = webdriver.Chrome(options=options)

    while watching[level]:
        try:
            driver.get(TARGET_URLS[level])
            time.sleep(1)
            body_text = driver.page_source

            if any(text in body_text for text in TRIGGER_TEXTS):
                webbrowser.open_new_tab(TARGET_URLS[level])
                webbrowser.open_new_tab("http://127.0.0.1:5000/alarm")
                trigger_audio[level] = True
                watching[level] = False
                click_screen_center()
                print(f"✅ {level.upper()} - Select Module Found!")
            else:
                print(f"❌ {level.upper()} - Not found.")
        except Exception as e:
            print("⚠️ Error:", e)
        time.sleep(1)

    driver.quit()




@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin/eurozoom', methods=['GET', 'POST'])
def admin_create_user():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        subscription = request.form['subscription']  # নতুন subscription ইনপুট নিচ্ছি
        plan_days = int(request.form['plan_days'])
        amount = float(request.form['amount'])
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        devices = request.form['devices']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (full_name, email, phone, subscription, plan_days, amount, start_date, end_date, devices)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (full_name, email, phone, subscription, plan_days, amount, start_date, end_date, devices))
            conn.commit()
            msg = "User added successfully!"
        except mysql.connector.Error as err:
            msg = f"Error: {err}"
        finally:
            cursor.close()
            conn.close()
        return render_template('admin/eurozoom.html', message=msg)
    
    return render_template('admin/eurozoom.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form['identifier']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM users
            WHERE (email = %s OR phone = %s) AND is_active = TRUE
        """, (identifier, identifier))
        user = cursor.fetchone()

        if user:
            device_id = get_device_id()

            cursor.execute("SELECT COUNT(*) AS device_count FROM user_devices WHERE email = %s", (user['email'],))
            device_info = cursor.fetchone()
            current_device_count = device_info['device_count']

            allowed_devices = int(user.get('devices', 1))

            cursor.execute("SELECT * FROM user_devices WHERE email = %s AND device_id = %s", (user['email'], device_id))
            existing = cursor.fetchone()

            if not existing and current_device_count >= allowed_devices:
                cursor.close()
                conn.close()
                return render_template('login.html', error="🚫 Maximum device limit reached.")

            if not existing:
                cursor.execute("INSERT INTO user_devices (email, device_id) VALUES (%s, %s)", (user['email'], device_id))
                conn.commit()

            cursor.close()
            conn.close()

            session['email'] = user['email']
            resp = make_response(redirect(url_for('dashboard')))
            resp.set_cookie("device_id", device_id, max_age=30*24*60*60)
            return resp

        else:
            return render_template('login.html', error="Invalid your data or subscription expired.")

    return render_template('login.html')




@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (session['email'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        alarms=ALARM_LIST,
        session_alarm=session.get('alarm_file'),
        user=user
    )

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home'))



@app.route('/set-alarm', methods=['POST'])
def set_alarm():
    selected_alarm = request.form.get('alarm_choice')
    if selected_alarm:
        session['alarm_file'] = selected_alarm
    return redirect(url_for('dashboard'))



@app.route('/start-watch/<level>') 
def start_watch(level): 
    normalized_level = level.replace("-", "_")  # হাইফেনকে আন্ডারস্কোরে বদলে দিলাম
    
    if normalized_level in watching and not watching[normalized_level]: 
        watching[normalized_level] = True 
        trigger_audio[normalized_level] = False 
        threading.Thread(target=check_condition_and_open, args=(normalized_level,)).start()

        return f"""
        <html>
            <head>
                <style>
                    body {{
                        background-color: #f0f8ff;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        font-family: Arial, sans-serif;
                    }}
                    .message-box {{
                        background-color: #ffffff;
                        padding: 30px;
                        max-width: 600px;
                        border: 2px solid #4CAF50;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                    }}
                    .message-box h2 {{
                        color: #4CAF50;
                    }}
                    .monitoring-page {{ 
                        font-weight: bold;
                        text-align: center;
                        margin-bottom: 5px;
                    }}
                    .back-button {{
                        margin-top: 20px;
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #4CAF50;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                    }}
                    .back-button:hover {{
                        background-color: #45a049;
                    }}
                </style>
            </head>
            <body>
                <div class="message-box">
                    <h2>Monitoring {normalized_level.upper()} level for 'Select Module'</h2>
                    <p class="monitoring-page">Don't worry! Page changes won’t interrupt your monitoring.</p>
                    <p style="text-align: justify; margin-top: 0;">
                        When 'Select Module' appears, your alarm will sound and the registration page will open within 5 seconds. If your internet is slow, it may take up to 12 seconds for the alarm and page to load.
                    </p> 
                    <a href="/dashboard" class="back-button">← Back to Dashboard</a>
                </div>
            </body>
        </html>
        """
    else:
        return """
        <html>
            <head>
                <style>
                    body {
                        background-color: #fff0f0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        font-family: Arial, sans-serif;
                    }
                    .message-box {
                        background-color: #ffffff;
                        padding: 30px;
                        border: 2px solid #ff4c4c;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                    }
                    .back-button {
                        margin-top: 20px;
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #ff4c4c;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                    }
                    .back-button:hover {
                        background-color: #e63939;
                    }
                </style>
            </head>
            <body>
                <div class="message-box">
                    <h2>Invalid request or already being monitored. Please wait.</h2>
                    <a href="/dashboard" class="back-button">← Back to Dashboard</a>
                </div>
            </body>
        </html>
        """


@app.route('/alarm')
def alarm():
    alarm_file = session.get('alarm_file', '1-Morning.mp3')
    return render_template('alarm.html', alarm_file=alarm_file)

@app.route('/check-audio/<level>')
def check_audio(level):
    if level in trigger_audio:
        return jsonify({"play": trigger_audio[level]})
    return jsonify({"play": False})

if __name__ == '__main__':
    app.run(debug=False)
