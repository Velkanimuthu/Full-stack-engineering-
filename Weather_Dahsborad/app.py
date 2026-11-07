from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "4eb9305bd2eaa7868fdd12ff34654974"
BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
# ---------- Database ----------
DATABASE = "users.db"

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        db.commit()

# ---------- Routes ----------
@app.route("/")
def home():
    return redirect(url_for("login"))

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").lower()
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            session["user_email"] = email
            session["user_name"] = user[1]
            return redirect(url_for("welcome"))
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")

# Create Account page
@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email").lower()
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("create_account.html", error="Email already registered!")

    return render_template("create_account.html")

# Welcome page
def get_weather_suggestion(condition):
    if condition == "Sunny":
        return {
            "quote": "☀️ Bright days bring brighter thoughts!",
            "advice": "Stay hydrated and wear sunscreen when going outside."
        }
    elif condition == "Clouds":
        return {
            "quote": "☁ Every cloud has a silver lining.",
            "advice": "Good day for a walk, but keep an umbrella handy."
        }
    elif condition == "Rain":
        return {
            "quote": "🌧 Let the rain wash away your worries.",
            "advice": "Carry an umbrella and avoid street food today."
        }
    elif condition == "Stormy":
        return {
            "quote": "⛈ Storms make trees take deeper roots.",
            "advice": "Stay indoors if possible and avoid travel."
        }
    else:
        return {
            "quote": "🌍 Weather changes, but positivity stays.",
            "advice": "Take care of your health and stay safe."
        }


def get_weather(city):
    params = {
        "q": city,
        "appid":app.secret_key ,
        "units": "metric"
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if "list" not in data:
        return []

    forecast_list = data["list"]

    today = datetime.now()
    weather_data = []

    # Loop through 0, +1, +2, +3, +4 days
    for i in range(5):
        target_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")

        # Find forecasts for that day
        daily_forecasts = [f for f in forecast_list if f["dt_txt"].startswith(target_date)]

        if daily_forecasts:
            # Take the midday forecast (around 12:00)
            midday = next((f for f in daily_forecasts if "12:00:00" in f["dt_txt"]), daily_forecasts[0])

            weather_data.append({
                "date": target_date,
                "temp": round(midday["main"]["temp"], 1),
                "rain": midday.get("rain", {}).get("3h", 0),
                "weather": midday["weather"][0]["main"]
            })
        else:
            weather_data.append({
                "date": target_date,
                "temp": None,
                "rain": None,
                "weather": "No Data"
            })

    return weather_data

@app.route("/welcome", methods=["GET", "POST"])
def welcome():
    if "user_email" not in session:
        return redirect(url_for("login"))

    city = None
    weather_data = []
    suggestion = {
        "quote": "",
        "advice": ""
    }

    if request.method == "POST":
        city = request.form.get("city")
        weather_data = get_weather(city)

        if weather_data:
            today_condition = weather_data[0]["weather"]
            suggestion = get_weather_suggestion(today_condition)

    return render_template("welcome.html", 
                           name=session["user_name"], 
                           city=city, 
                           weather_data=weather_data,
                           suggestion=suggestion)


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
