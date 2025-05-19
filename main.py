
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Banco de dados local
conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()

# Criação de tabelas, se não existirem
cursor.execute("""
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL,
    status TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    placa TEXT NOT NULL,
    retirada TEXT NOT NULL,
    devolucao TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS prereservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    retirada TEXT NOT NULL,
    devolucao TEXT NOT NULL
)
""")
conn.commit()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/reserva", response_class=HTMLResponse)
def form_reserva(request: Request):
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'Disponivel'")
    placas = [row[0] for row in cursor.fetchall()]
    return templates.TemplateResponse("reserva.html", {"request": request, "placas": placas})

@app.post("/reserva")
def reserva(request: Request, nome: str = Form(...), email: str = Form(...),
            placa: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...)):
    if placa == "Nenhum disponível":
        cursor.execute("INSERT INTO prereservas (nome, email, retirada, devolucao) VALUES (?, ?, ?, ?)",
                       (nome, email, retirada, devolucao))
    else:
        cursor.execute("INSERT INTO reservas (nome, email, placa, retirada, devolucao) VALUES (?, ?, ?, ?, ?)",
                       (nome, email, placa, retirada, devolucao))
        cursor.execute("UPDATE veiculos SET status = 'Reservado' WHERE placa = ?", (placa,))
    conn.commit()
    return RedirectResponse(url="/", status_code=303)
