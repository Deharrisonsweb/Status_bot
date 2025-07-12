from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import threading
import random
import logging
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# FastAPI setup
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Emoji list
EMOJIS = ["😄", "😍", "🤩", "😎", "😂"]

# WhatsApp bot function
def run_whatsapp_bot(token: str, chat_id: str):
    try:
        logging.info("Launching WhatsApp Status Bot")

        options = Options()
        options.add_argument("--user-data-dir=./profile")  # persist session
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless=new")  # optional: run headless

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")

        logging.info("Waiting for WhatsApp to load...")
        time.sleep(15)  # Allow time for manual QR scan or session restore

        while True:
            try:
                status_containers = driver.find_elements("xpath", '//div[@aria-label="View once"]')
                if not status_containers:
                    logging.info("No new statuses. Checking again in 60 seconds...")
                    time.sleep(60)
                    driver.refresh()
                    continue

                for i, status in enumerate(status_containers):
                    try:
                        status.click()
                        time.sleep(4)  # wait for status to load

                        emoji = random.choice(EMOJIS)
                        input_box = driver.find_element("xpath", '//div[@title="Type a message"]')
                        input_box.send_keys(emoji)
                        input_box.send_keys("\ue007")  # Enter key

                        requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={
                            "chat_id": chat_id,
                            "text": f"✅ Status {i+1} viewed and reacted with {emoji}"
                        })

                        time.sleep(3)
                        driver.find_element("xpath", '//span[@data-icon="x"]').click()
                        time.sleep(1)

                    except Exception as e:
                        logging.warning(f"Error viewing status: {e}")
                        continue
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                break
    except Exception as e:
        logging.error(f"Critical bot error: {e}")
    finally:
        driver.quit()

# Routes
@app.get("/", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/start")
async def start_bot(request: Request, token: str = Form(...), chat_id: str = Form(...)):
    thread = threading.Thread(target=run_whatsapp_bot, args=(token, chat_id))
    thread.start()
    return templates.TemplateResponse("login.html", {"request": request, "message": "Bot is running in background..."})
