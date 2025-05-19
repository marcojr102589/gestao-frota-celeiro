from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicializa o banco
if not os.path.exists("frota.db"):
    conn = sqlite3.connect("frota.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY, placa TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS prereservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, retirada TEXT, devolucao TEXT)")
    conn.commit()
    conn.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/reserva", response_class=HTMLResponse)
async def reserva(request: Request):
    return templates.TemplateResponse("reserva.html", {"request": request})

@app.get("/devolucao", response_class=HTMLResponse)
async def devolucao(request: Request):
    return templates.TemplateResponse("devolucao.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})