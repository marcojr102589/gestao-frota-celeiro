from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, shutil, sqlite3
from datetime import datetime

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="gestaofrota123")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()

# Atualiza tabela com colunas adicionais se necessário
cursor.execute("CREATE TABLE IF NOT EXISTS prereservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, retirada TEXT, devolucao TEXT, motivo TEXT, status TEXT)")
try:
    cursor.execute("ALTER TABLE prereservas ADD COLUMN locado TEXT")
except: pass
try:
    cursor.execute("ALTER TABLE prereservas ADD COLUMN valor TEXT")
except: pass

cursor.execute("CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY, placa TEXT UNIQUE, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS devolucoes (id INTEGER PRIMARY KEY, nome TEXT, placa TEXT, observacoes TEXT, status_final TEXT, imagem TEXT)")
conn.commit()

@app.get("/admin/prereservas", response_class=HTMLResponse)
def ver_pre(request: Request):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT * FROM prereservas ORDER BY retirada")
    reservas = cursor.fetchall()
    return templates.TemplateResponse("listar_prereservas.html", {"request": request, "prereservas": reservas})

@app.post("/admin/prereservas/atualizar")
def atualizar_pre(id: int = Form(...), locado: str = Form(...), valor: str = Form(...)):
    cursor.execute("UPDATE prereservas SET locado = ?, valor = ? WHERE id = ?", (locado, valor, id))
    conn.commit()
    return RedirectResponse("/admin/prereservas", status_code=303)

@app.get("/prereserva", response_class=HTMLResponse)
def prereserva(request: Request, retirada: str = "", devolucao: str = ""):
    return templates.TemplateResponse("prereserva.html", {"request": request, "retirada": retirada, "devolucao": devolucao})

@app.post("/prereserva")
def enviar_pre(nome: str = Form(...), email: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...), motivo: str = Form(...)):
    cursor.execute("INSERT INTO prereservas (nome, email, retirada, devolucao, motivo, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                   (nome, email, retirada, devolucao, motivo))
    conn.commit()
    return RedirectResponse("/inicio", status_code=303)