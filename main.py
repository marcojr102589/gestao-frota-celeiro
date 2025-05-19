
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
conn.commit()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/reserva", response_class=HTMLResponse)
def reserva(request: Request):
    return templates.TemplateResponse("reserva.html", {"request": request})

@app.get("/devolucao", response_class=HTMLResponse)
def devolucao(request: Request):
    return templates.TemplateResponse("devolucao.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
