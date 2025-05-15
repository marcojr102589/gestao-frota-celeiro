
# main.py (revisado completo)

from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import sqlite3

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="secret")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Banco de dados
conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()
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
    locado TEXT DEFAULT 'Não',
    valor TEXT DEFAULT ''
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY,
    placa TEXT,
    status TEXT
)
""")
conn.commit()

def enviar_email(destinatario, assunto, corpo):
    print(f"\n--- Email ---\nPara: {destinatario}\nAssunto: {assunto}\n{corpo}\n")

def conflito_data(placa, retirada, devolucao):
    cursor.execute("SELECT * FROM reservas WHERE placa = ?", (placa,))
    reservas = cursor.fetchall()
    for r in reservas:
        if not (devolucao < r[4] or retirada > r[5]):
            return True
    return False

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/formulario", response_class=HTMLResponse)
def formulario(request: Request):
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'Disponivel'")
    placas = [v[0] for v in cursor.fetchall()]
    return templates.TemplateResponse("formulario.html", {"request": request, "placas": placas})

@app.post("/reserva")
def reserva(nome: str = Form(...), email: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...), placa: str = Form(...)):
    if placa == "Nenhum disponível":
        cursor.execute("INSERT INTO prereservas (nome, email, retirada, devolucao) VALUES (?, ?, ?, ?)", (nome, email, retirada, devolucao))
        conn.commit()
        enviar_email("gestor@empresa.com", "Nova pré-reserva", f"{nome} solicitou um veículo de {retirada} a {devolucao}.")
        return RedirectResponse("/formulario?status=prereserva", status_code=303)

    if conflito_data(placa, retirada, devolucao):
        return RedirectResponse("/formulario?status=conflito", status_code=303)

    cursor.execute("INSERT INTO reservas (nome, email, placa, retirada, devolucao) VALUES (?, ?, ?, ?, ?)", (nome, email, placa, retirada, devolucao))
    conn.commit()
    enviar_email(email, "Reserva confirmada", f"Olá {nome}, sua reserva para o veículo {placa} foi confirmada.\nPeríodo: {retirada} a {devolucao}.")
    return RedirectResponse("/formulario?status=ok", status_code=303)

@app.get("/admin/prereservas", response_class=HTMLResponse)
def listar_prereservas(request: Request):
    cursor.execute("SELECT * FROM prereservas")
    lista = cursor.fetchall()
    return templates.TemplateResponse("listar_prereservas.html", {"request": request, "lista": lista})

@app.get("/admin/prereservas/editar/{id}", response_class=HTMLResponse)
def editar_prereserva(request: Request, id: int):
    cursor.execute("SELECT * FROM prereservas WHERE id = ?", (id,))
    dados = cursor.fetchone()
    return templates.TemplateResponse("editar_prereserva.html", {"request": request, "dados": dados})

@app.post("/admin/prereservas/editar/{id}")
def salvar_edicao_prereserva(id: int, locado: str = Form(...), valor: str = Form(...)):
    cursor.execute("UPDATE prereservas SET locado = ?, valor = ? WHERE id = ?", (locado, valor, id))
    conn.commit()
    return RedirectResponse("/admin/prereservas", status_code=303)
