import os
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import shutil, sqlite3
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="gestaofrota123")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()

# Tabelas
cursor.execute("CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY, placa TEXT UNIQUE, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS devolucoes (id INTEGER PRIMARY KEY, nome TEXT, placa TEXT, observacoes TEXT, status_final TEXT, imagem TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS prereservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, retirada TEXT, devolucao TEXT, motivo TEXT, status TEXT)")
try:
    cursor.execute("ALTER TABLE prereservas ADD COLUMN locado TEXT")
except: pass
try:
    cursor.execute("ALTER TABLE prereservas ADD COLUMN valor TEXT")
except: pass
conn.commit()

# Utilitário de e-mail
def enviar_email(destinatario, assunto, conteudo):
    try:
        msg = EmailMessage()
        msg['Subject'] = assunto
        msg['From'] = os.getenv("SMTP_USER")
        msg['To'] = destinatario
        msg.set_content(conteudo)

        with smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            smtp.send_message(msg)
    except Exception as e:
        print("Erro ao enviar e-mail:", e)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    registros = cursor.fetchall()
    cursor.execute("SELECT status, COUNT(*) FROM veiculos GROUP BY status")
    status_count = {s: c for s, c in cursor.fetchall()}
    cursor.execute("SELECT status_final, COUNT(*) FROM devolucoes GROUP BY status_final")
    devolucao_count = {s: c for s, c in cursor.fetchall()}
    cursor.execute("SELECT * FROM prereservas WHERE status = 'pendente'")
    prereservas = cursor.fetchall()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "registros": registros,
        "status_count": status_count,
        "devolucao_count": devolucao_count,
        "prereservas": prereservas
    })

@app.get("/inicio", response_class=HTMLResponse)
def inicio(request: Request):
    gestor = request.session.get("gestor") == True
    return templates.TemplateResponse("home.html", {"request": request, "gestor": gestor})

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "erro": False})

@app.post("/login")
def login_post(request: Request, senha: str = Form(...)):
    if senha == "gestor123":
        request.session["gestor"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "erro": True})

@app.get("/formulario", response_class=HTMLResponse)
def formulario(request: Request):
    return templates.TemplateResponse("formulario.html", {"request": request})

@app.post("/formulario")
def reservar(nome: str = Form(...), email: str = Form(...), placa: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...)):
    # Verificar conflitos
    cursor.execute("SELECT retirada, devolucao FROM registros WHERE placa = ?", (placa,))
    conflitos = [
        (r, d) for r, d in cursor.fetchall()
        if datetime.strptime(r, "%Y-%m-%d") <= datetime.strptime(devolucao, "%Y-%m-%d") and
           datetime.strptime(d, "%Y-%m-%d") >= datetime.strptime(retirada, "%Y-%m-%d")
    ]
    if conflitos:
        return HTMLResponse("<h3>❌ Conflito: já existe uma reserva nesse período para essa placa.</h3>", status_code=400)

    cursor.execute("INSERT INTO registros (nome, email, placa, retirada, devolucao) VALUES (?, ?, ?, ?, ?)", (nome, email, placa, retirada, devolucao))
    cursor.execute("UPDATE veiculos SET status = 'em_uso' WHERE placa = ?", (placa,))
    conn.commit()

    # Enviar e-mail para usuário
    conteudo = f"Olá {nome}, sua reserva para o veículo {placa} foi confirmada."
Período: {retirada} a {devolucao}."
    enviar_email(email, "Reserva Confirmada", conteudo)
    return RedirectResponse("/inicio", status_code=303)

@app.get("/devolucao", response_class=HTMLResponse)
def devolucao(request: Request):
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'em_uso'")
    placas = [p[0] for p in cursor.fetchall()]
    return templates.TemplateResponse("devolucao.html", {"request": request, "placas": placas})

@app.post("/devolucao")
def registrar_devolucao(nome: str = Form(...), placa: str = Form(...), observacoes: str = Form(...), status_final: str = Form(...), imagem: UploadFile = File(None)):
    img_path = ""
    if imagem:
        os.makedirs("static/uploads", exist_ok=True)
        img_path = f"static/uploads/{imagem.filename}"
        with open(img_path, "wb") as f:
            shutil.copyfileobj(imagem.file, f)
    cursor.execute("INSERT INTO devolucoes (nome, placa, observacoes, status_final, imagem) VALUES (?, ?, ?, ?, ?)",
                   (nome, placa, observacoes, status_final, img_path))
    cursor.execute("UPDATE veiculos SET status = ? WHERE placa = ?", (status_final, placa))
    conn.commit()

    # atende pré-reservas automaticamente
    cursor.execute("SELECT id, retirada FROM prereservas WHERE status = 'pendente'")
    for pid, r in cursor.fetchall():
        if datetime.strptime(r, "%Y-%m-%d") >= datetime.now():
            cursor.execute("UPDATE prereservas SET status = 'atendido' WHERE id = ?", (pid,))
            conn.commit()
            break

    return RedirectResponse("/inicio", status_code=303)

@app.get("/admin/reservas/editar/{id}", response_class=HTMLResponse)
def editar_reserva(request: Request, id: int):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT nome, email, placa, retirada, devolucao FROM registros WHERE id = ?", (id,))
    dados = cursor.fetchone()
    return templates.TemplateResponse("editar_reserva.html", {
        "request": request,
        "id": id,
        "nome": dados[0],
        "email": dados[1],
        "placa": dados[2],
        "retirada": dados[3],
        "devolucao": dados[4]
    })

@app.post("/admin/reservas/atualizar")
def atualizar_reserva(id: int = Form(...), nome: str = Form(...), email: str = Form(...), placa: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...)):
    cursor.execute("UPDATE registros SET nome = ?, email = ?, placa = ?, retirada = ?, devolucao = ? WHERE id = ?",
                   (nome, email, placa, retirada, devolucao, id))
    conn.commit()
    return RedirectResponse("/", status_code=303)

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

@app.get("/admin/prereservas/editar/{id}", response_class=HTMLResponse)
def editar_pre(request: Request, id: int):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT locado, valor FROM prereservas WHERE id = ?", (id,))
    locado, valor = cursor.fetchone() or ("Não", "")
    return templates.TemplateResponse("editar_prereserva.html", {
        "request": request,
        "id": id,
        "locado": locado,
        "valor": valor
    })

@app.get("/prereserva", response_class=HTMLResponse)
def prereserva(request: Request, retirada: str = "", devolucao: str = ""):
    return templates.TemplateResponse("prereserva.html", {"request": request, "retirada": retirada, "devolucao": devolucao})

@app.post("/prereserva")
def enviar_pre(nome: str = Form(...), email: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...), motivo: str = Form(...)):
    cursor.execute("INSERT INTO prereservas (nome, email, retirada, devolucao, motivo, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                   (nome, email, retirada, devolucao, motivo))
    conn.commit()
    # notifica gestor
    conteudo = f"Nova pré-reserva pendente: {nome} solicitou de {retirada} a {devolucao}."
    enviar_email(os.getenv("DESTINATARIO_GESTOR"), "Nova Pré-Reserva", conteudo)
    return RedirectResponse("/inicio", status_code=303)

@app.get("/backup")
def download_db():
    return FileResponse("frota.db", filename="frota-backup.db", media_type="application/octet-stream")

@app.get("/disponiveis")
def listar_disponiveis(retirada: str, devolucao: str):
    data_ini = datetime.strptime(retirada, "%Y-%m-%d")
    data_fim = datetime.strptime(devolucao, "%Y-%m-%d")
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'disponivel'")
    todas = [p[0] for p in cursor.fetchall()]
    cursor.execute("SELECT placa, retirada, devolucao FROM registros")
    registros = cursor.fetchall()
    indisponiveis = set()
    for placa, r_ini, r_fim in registros:
        r_ini = datetime.strptime(r_ini, "%Y-%m-%d")
        r_fim = datetime.strptime(r_fim, "%Y-%m-%d")
        if (r_ini <= data_fim and r_fim >= data_ini):
            indisponiveis.add(placa)
    disponiveis = [p for p in todas if p not in indisponiveis]
    return {"disponiveis": disponiveis}