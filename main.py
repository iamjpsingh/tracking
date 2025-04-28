from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from user_agents import parse
import sqlite3
from datetime import datetime
import os
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Database file name
DB_NAME = "tracking.db"

# Initialize the database with extended columns
def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)  # Remove old DB if exists
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            current_page TEXT,
            user_agent TEXT,
            timestamp TEXT,
            browser TEXT,
            os TEXT,
            device TEXT,
            country TEXT,
            city TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.get("/track.gif")
async def track(request: Request, current_page: str = "unknown"):
    ip = request.client.host
    ua_string = request.headers.get('user-agent', 'unknown')
    user_agent_parsed = parse(ua_string)
    
    # Parse browser, OS and device
    browser = f"{user_agent_parsed.browser.family} {user_agent_parsed.browser.version_string}"
    os_info = f"{user_agent_parsed.os.family} {user_agent_parsed.os.version_string}"
    device = "Mobile" if user_agent_parsed.is_mobile else "Tablet" if user_agent_parsed.is_tablet else "PC"
    
    # Get GeoIP data using ipapi.co
    try:
        geo = requests.get(f"https://ipapi.co/{ip}/json/").json()
        country = geo.get("country_name", "Unknown")
        city = geo.get("city", "Unknown")
    except Exception as e:
        country = "Unknown"
        city = "Unknown"
    
    timestamp = datetime.utcnow().isoformat()

    # Insert the tracked info into the database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tracking_logs (ip_address, current_page, user_agent, timestamp, browser, os, device, country, city)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ip, current_page, ua_string, timestamp, browser, os_info, device, country, city))
    conn.commit()
    conn.close()

    # Return a transparent 1x1 GIF
    transparent_gif = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF!'
        b'\xF9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
        b'\x00\x00\x02\x02D\x01\x00;'
    )
    return Response(content=transparent_gif, media_type="image/gif")

@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring(request: Request):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ip_address, current_page, user_agent, timestamp, browser, os, device, country, city 
        FROM tracking_logs ORDER BY id DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse("monitor.html", {"request": request, "rows": rows})
