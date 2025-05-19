from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY,
    placa TEXT UNIQUE,
    status TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    email TEXT,
    placa TEXT,
    retirada TEXT,
    devolucao TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS prereservas (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    email TEXT,
    retirada TEXT,
    devolucao TEXT,
    origem TEXT,
    valor TEXT
)
""")
conn.commit()

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/reserva")
def reserva(request: Request):
    return templates.TemplateResponse("reserva.html", {"request": request})

@app.get("/devolucao")
def devolucao(request: Request):
    return templates.TemplateResponse("devolucao.html", {"request": request})

@app.get("/prereserva")
def prereserva(request: Request):
    return templates.TemplateResponse("prereserva.html", {"request": request})

@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/admin/prereservas")
def listar_prereservas(request: Request):
    cursor.execute("SELECT * FROM prereservas")
    dados = cursor.fetchall()
    return templates.TemplateResponse("listar_prereservas.html", {"request": request, "dados": dados})

@app.get("/admin/prereservas/editar/{id}")
def editar_prereserva(id: int, request: Request):
    cursor.execute("SELECT * FROM prereservas WHERE id = ?", (id,))
    item = cursor.fetchone()
    return templates.TemplateResponse("editar_prereserva.html", {"request": request, "item": item})

@app.get("/admin/cadastro")
def cadastro_veiculo(request: Request):
    return templates.TemplateResponse("cadastro_veiculo.html", {"request": request})