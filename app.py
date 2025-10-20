# app.py
import os
import sqlite3
import json
import calendar
from datetime import date, datetime, timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for, g

app = Flask(__name__)
app.secret_key = "supersecretkey"
DATABASE = "iron.db"

IRON_DATA = {
    "Almonds": 3.7,
    "Beef": 2.7,
    "Beef Liver": 6.2,
    "Buckwheat": 6.7,
    "Chicken": 1.3,
    "Dark Chocolate": 11.9,
    "Kidney Beans": 5.1,
    "Lentils": 3.3,
    "Oats": 4.3,
    "Pumpkin Seeds": 8.8,
    "Quinoa": 4.6,
    "Soybeans": 15.7,
    "Spinach": 2.7,
    "Tofu": 5.4,
    "White Beans": 3.7,
    "Apple": 0.1
}

USER_ID = 1

# === DB ===
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                record_date TEXT,
                total_iron REAL,
                percentage REAL,
                items_json TEXT
            )
        ''')
        db.commit()

# === HTML TEMPLATE ===
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Iron Tracker</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f9f9f9;
            padding: 20px;
            color: #333;
            display: flex;
            justify-content: center;
        }

        .container {
            width: 100%;
            max-width: 800px;
        }

        h1 {
            font-size: 28px;
            margin-bottom: 10px;
            text-align: center;
        }

        .date-indicator {
            font-size: 16px;
            color: #666;
            text-align: center;
            margin-bottom: 20px;
        }

        form {
            background: #fff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            width: 100%;
            box-sizing: border-box;
        }

        label, p {
            font-weight: 500;
            margin-bottom: 8px;
            display: block;
        }

        input[type="number"], select {
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            font-size: 16px;
            margin-bottom: 10px;
        }

        input[readonly] {
            background: #f1f1f1;
            border: 1px solid #e0e0e0;
            width: 90px;
            text-align: center;
        }

        #products > .product-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .remove-button {
            background: none;
            border: none;
            color: #888;
            font-size: 14px;
            cursor: pointer;
            padding: 4px 8px;
            transition: color 0.2s;
        }

        .remove-button:hover {
            color: #ff3b30;
        }

        button, input[type="submit"] {
            background-color: #007aff;
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }

        button:hover, input[type="submit"]:hover {
            background-color: #005ecb;
        }

        .calendar-link {
            display: inline-block;
            margin-top: 25px;
            background-color: #e5e5ea;
            color: #333;
            padding: 10px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            text-align: center;
        }

        .calendar-link:hover {
            background-color: #d1d1d6;
        }

        .result-ok {
            color: green;
            font-weight: bold;
            text-align: center;
        }

        .result-over {
            color: red;
            font-weight: bold;
            text-align: center;
        }

        .calendar-container {
            text-align: center;
        }

        /* 📱 Адаптация под мобильные устройства */
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }

            h1 {
                font-size: 22px;
            }

            form {
                padding: 15px;
            }

            #products > .product-row {
                flex-direction: column;
                align-items: stretch;
            }

            select, input[type="number"], input[readonly] {
                width: 100%;
            }

            button, input[type="submit"], .calendar-link {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Iron Tracker</h1>
        <div class="date-indicator">📅 {{ day_text[5:] }}</div>

        <form method="post">
            <label><strong>Please specify your maximum daily iron intake (mg):</strong></label>
            <input type="number" step="0.1" name="norm" value="{{ norm }}" required>

            <p><strong>Enter the products you consumed{{ day_text }}:</strong></p>
            <div id="products">
                {% for i in range(product_count) %}
                <div class="product-row" data-index="{{ i }}">
                    <select name="product_{{ i }}">
                        {% for name in iron_data %}
                            <option value="{{ name }}" {% if selections[i]['product'] == name %}selected{% endif %}>{{ name }}</option>
                        {% endfor %}
                    </select>
                    <input type="number" name="grams_{{ i }}" placeholder="Grams" value="{{ selections[i]['grams'] }}" required>
                    <input type="text" readonly value="{{ selections[i]['iron'] }} mg">
                    <button type="button" class="remove-button" onclick="removeProduct(this)">🗑 Delete</button>
                </div>
                {% endfor %}
            </div>

            <button type="button" onclick="addProduct()">➕ Add more</button>
            <br><br>
            <input type="submit" value="💾 Save">
        </form>

        {% if total is not none %}
            <h3 class="{{ 'result-over' if total > norm else 'result-ok' }}">
                Total: {{ "%.2f"|format(total) }} mg of iron
            </h3>
            <h4 class="{{ 'result-over' if total > norm else 'result-ok' }}">
                {{ status }}
            </h4>
        {% endif %}

        <div class="calendar-container">
            <a href="/calendar" class="calendar-link">📆 Back to Calendar</a>
        </div>
    </div>

    <script>
        let count = {{ product_count }};
        const ironData = {{ iron_data_json | safe }};

        function addProduct() {
            const div = document.createElement("div");
            div.className = "product-row";
            div.setAttribute("data-index", count);
            div.innerHTML = `
                <select name="product_${count}">
                    ${Object.entries(ironData).map(([k]) => `<option value="${k}">${k}</option>`).join("")}
                </select>
                <input type="number" name="grams_${count}" placeholder="Grams" required>
                <input type="text" readonly value=" mg">
                <button type="button" class="remove-button" onclick="removeProduct(this)">🗑 Delete</button>
            `;
            document.getElementById("products").appendChild(div);
            count++;
        }

        function removeProduct(button) {
            const row = button.closest(".product-row");
            row.remove();
            updateIndexes();
        }

        function updateIndexes() {
            const rows = document.querySelectorAll("#products .product-row");
            rows.forEach((row, idx) => {
                row.setAttribute("data-index", idx);
                const selects = row.getElementsByTagName("select");
                const inputs = row.getElementsByTagName("input");

                if (selects.length > 0) selects[0].setAttribute("name", `product_${idx}`);
                if (inputs.length > 0) inputs[0].setAttribute("name", `grams_${idx}`);
            });
            count = rows.length;
        }
    </script>
</body>
</html>
'''

# === ROUTES ===

@app.route("/edit/<day>", methods=["GET", "POST"])
def edit_day(day):
    return handle_day(day)

def handle_day(day):
    db = get_db()
    norm = session.get("norm", 15.0)
    selections = []
    total = None
    status = None
    record_date = day

    cur = db.execute("SELECT * FROM records WHERE user_id = ? AND record_date = ?", (USER_ID, record_date))
    record = cur.fetchone()

    if request.method == "POST":
        norm = float(request.form["norm"])
        session["norm"] = norm

        selections = []
        total = 0
        i = 0
        while True:
            p_key = f"product_{i}"
            g_key = f"grams_{i}"
            if p_key in request.form and g_key in request.form:
                name = request.form[p_key]
                grams = float(request.form[g_key])
                iron = round((IRON_DATA.get(name, 0) / 100) * grams, 2)
                selections.append({"product": name, "grams": round(grams, 2), "iron": iron})
                total += iron
                i += 1
            else:
                break

        total = round(total, 2)
        perc = round((total / norm) * 100, 2)
        db.execute("DELETE FROM records WHERE user_id = ? AND record_date = ?", (USER_ID, record_date))
        db.execute("INSERT INTO records (user_id, record_date, total_iron, percentage, items_json) VALUES (?, ?, ?, ?, ?)",
                   (USER_ID, record_date, total, perc, json.dumps(selections, ensure_ascii=False)))
        db.commit()
        status = f"This is {perc}% of your daily limit."
        return redirect(url_for("dashboard", saved=1))
        
    else:
        if record:
            selections = json.loads(record["items_json"])
            total = round(record["total_iron"], 2)
            perc = round(record["percentage"], 2)
            status = f"This is {perc}% of your daily limit."
        else:
            selections = [{"product": "", "grams": "", "iron": ""}]

    return render_template_string(HTML_TEMPLATE,
                                  iron_data=sorted(IRON_DATA.keys()),
                                  iron_data_json=json.dumps(IRON_DATA, ensure_ascii=False),
                                  product_count=len(selections),
                                  selections=selections,
                                  total=total,
                                  status=status,
                                  norm=norm,
                                  day_text=f" for {record_date}")

@app.route("/calendar")
def calendar_view():
    db = get_db()
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    _, days_in_month = calendar.monthrange(year, month)
    first_day = date(year, month, 1)
    start_day = first_day - timedelta(days=first_day.weekday())
    end_day = date(year, month, days_in_month)

    cur = db.execute(
        "SELECT record_date, percentage FROM records WHERE user_id = ? AND record_date BETWEEN ? AND ?",
        (USER_ID, start_day.isoformat(), (end_day + timedelta(days=6 - end_day.weekday())).isoformat())
    )
    data = {row["record_date"]: row["percentage"] for row in cur.fetchall()}

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Calendar — {year}-{month:02}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f9f9f9;
                color: #333;
                padding: 40px;
                display: flex;
                justify-content: center;
            }}
            .calendar-container {{
                background: #fff;
                border-radius: 14px;
                box-shadow: 0 4px 14px rgba(0,0,0,0.08);
                padding: 30px;
                max-width: 850px;
                width: 100%;
            }}
            h1 {{
                font-size: 26px;
                text-align: center;
                margin-bottom: 25px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: center;
                border-radius: 10px;
                overflow: hidden;
                table-layout: fixed; /* фиксированные размеры колонок */
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: 600;
                padding: 12px 0;
                font-size: 15px;
            }}
            td {{
                width: 14.28%;
                height: 80px;
                border: 1px solid #eee;
                font-size: 16px;
                vertical-align: middle;
                position: relative;
            }}
            td a {{
                text-decoration: none;
                color: #333;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                width: 100%;
                transition: background-color 0.2s;
            }}
            td a:hover {{
                background-color: #eaf4ff;
            }}
            .green-day {{ background-color: #d4edda; }}
            .red-day {{ background-color: #f8d7da; }}
            .gray-day {{ background-color: #f1f1f1; color: #aaa; }}
            .empty-day {{ background-color: #fff; }}

            .nav-controls {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin: 25px 0;
            }}
            .nav-btn {{
                background-color: #e5e5ea;
                color: #333;
                padding: 10px 16px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            .nav-btn:hover {{ background-color: #d1d1d6; }}

            .home-btn {{
                display: block;
                width: fit-content;
                margin: 0 auto;
                background-color: #007aff;
                color: white;
                padding: 10px 16px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            .home-btn:hover {{ background-color: #005ecb; }}
        </style>
    </head>
    <body>
        <div class="calendar-container">
            <h1>📅 Calendar — {year}-{month:02}</h1>
            <table>
                <tr>
                    <th>Mon</th><th>Tue</th><th>Wed</th>
                    <th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th>
                </tr>
    """

    current = start_day
    while True:
        html += "<tr>"
        for _ in range(7):
            day_str = current.isoformat()
            percentage = data.get(day_str)

            if percentage is None and current.month != month:
                class_name = "gray-day"
                cell = f"<td class='{class_name}'>{current.day}</td>"
            elif percentage is None:
                class_name = "empty-day"
                cell = f"<td class='{class_name}'><a href='/edit/{day_str}'>{current.day}</a></td>"
            elif percentage > 100:
                class_name = "red-day"
                cell = f"<td class='{class_name}'><a href='/edit/{day_str}'>{current.day}</a></td>"
            else:
                class_name = "green-day"
                cell = f"<td class='{class_name}'><a href='/edit/{day_str}'>{current.day}</a></td>"

            html += cell
            current += timedelta(days=1)
        html += "</tr>"
        if current.month > month and current.weekday() == 0:
            break

    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year - 1 if month == 1 else year
    next_year = year + 1 if month == 12 else year

    html += f"""
            </table>
            <div class="nav-controls">
                <a href="/calendar?year={prev_year}&month={prev_month}" class="nav-btn">⬅ Previous</a>
                <a href="/calendar?year={next_year}&month={next_month}" class="nav-btn">Next ➡</a>
            </div>
            <a href="/" class="home-btn">🏠 Back to Dashboard</a>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/")
def dashboard():
    db = get_db()
    today = date.today()
    today_str = today.isoformat()

    saved = request.args.get("saved")

    # Гарантируем свежие данные из SQLite
    db.commit()

    # === Сегодня ===
    cur_today = db.execute(
        "SELECT total_iron, percentage FROM records WHERE user_id = ? AND record_date = ?",
        (USER_ID, today_str)
    )
    today_data = cur_today.fetchone()

    perc = round(today_data["percentage"], 1) if today_data else 0
    total = round(today_data["total_iron"], 2) if today_data else 0

    today_status = (
        f"{total} mg — {perc}% of your daily limit."
        if today_data else "No data yet for today."
    )

    # === Последние 5 дней ===
    recent_days = []
    for offset in range(1, 6):
        day = today - timedelta(days=offset)
        day_str = day.isoformat()
        cur = db.execute(
            "SELECT total_iron, percentage FROM records WHERE user_id = ? AND record_date = ?",
            (USER_ID, day_str)
        )
        row = cur.fetchone()

        if row:
            total_day = round(row["total_iron"], 2)
            perc_day = round(row["percentage"], 1)
            status_icon = "🟩" if perc_day <= 100 else "🟥"
        else:
            total_day, perc_day, status_icon = "—", "—", "⬜"

        recent_days.append({
            "date": day.strftime("%d %b"),
            "total": total_day,
            "perc": perc_day,
            "icon": status_icon,
            "link": f"/edit/{day_str}"
        })

    # === Уведомление об успешном сохранении ===
    alert_html = ""
    if saved:
        alert_html = "<div class='alert-success'>✅ Saved successfully!</div>"

    # === HTML ===
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Iron Tracker — Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
        <meta http-equiv="Pragma" content="no-cache" />
        <meta http-equiv="Expires" content="0" />
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f9f9f9;
                padding: 30px;
                color: #333;
                max-width: 800px;
                margin: auto;
            }}
            h1 {{
                font-size: 30px;
                margin-bottom: 25px;
            }}
            .card {{
                background: #fff;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                margin-bottom: 25px;
            }}
            .btn {{
                display: inline-block;
                background-color: #007aff;
                color: white;
                padding: 10px 18px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            .btn:hover {{ background-color: #005ecb; }}
            .calendar-btn {{
                background-color: #e5e5ea;
                color: #333;
                margin-top: 10px;
            }}
            .calendar-btn:hover {{ background-color: #d1d1d6; }}
            .today-status {{
                color: #666;
                margin-top: 8px;
                font-size: 16px;
            }}
            /* === Прогресс-бар === */
            .progress-container {{
                width: 100%;
                height: 16px;
                background-color: #eee;
                border-radius: 8px;
                overflow: hidden;
                margin-top: 10px;
            }}
            .progress-bar {{
                height: 100%;
                transition: width 0.5s ease-in-out;
                border-radius: 8px;
            }}
            .progress-label {{
                margin-top: 6px;
                font-size: 15px;
                color: #555;
            }}
            /* === Таблица последних дней === */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                text-align: left;
                padding: 10px;
                border-bottom: 1px solid #eee;
                font-size: 16px;
            }}
            th {{
                color: #666;
                font-weight: 600;
                border-bottom: 2px solid #ccc;
            }}
            td a {{
                text-decoration: none;
                color: #333;
                font-weight: 500;
            }}
            td a:hover {{ text-decoration: underline; }}
            /* === Уведомление === */
            .alert-success {{
                background-color: #d4edda;
                color: #155724;
                padding: 12px 18px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-size: 16px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                animation: fadeOut 3s forwards;
            }}
            @keyframes fadeOut {{
                0% {{ opacity: 1; }}
                80% {{ opacity: 1; }}
                100% {{ opacity: 0; display: none; }}
            }}
        </style>
    </head>
    <body>
        {alert_html}
        <h1>Iron Tracker</h1>

        <div class="card">
            <h2>📅 Today: {today_str}</h2>
            <p class="today-status">{today_status}</p>

            {f"""
            <div class='progress-container'>
                <div class='progress-bar' 
                     style='width:{min(perc, 100)}%; 
                            background-color:{"#28a745" if perc < 80 else ("#ffcc00" if perc <= 100 else "#ff3b30")};'>
                </div>
            </div>
            <p class='progress-label'>
                {perc}% of your daily limit{' <span style="color:#ff3b30;">(Exceeded!)</span>' if perc > 100 else ''}
            </p>
            """ if today_data else ""}

            <a href="/edit/{today_str}" class="btn">➕ Add or Edit Today</a>
        </div>

        <div class="card">
            <h2>🕓 Recent Days</h2>
            <table>
                <tr><th>Date</th><th>Iron (mg)</th><th>% of norm</th><th>Status</th></tr>
                {''.join(f'<tr><td><a href="{d["link"]}">{d["date"]}</a></td><td>{d["total"]}</td><td>{d["perc"]}</td><td style="font-size:20px;">{d["icon"]}</td></tr>' for d in recent_days)}
            </table>
        </div>

        <div class="card">
            <h2>📆 Full History</h2>
            <a href="/calendar" class="btn calendar-btn">Open Calendar</a>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
