from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, shutil, sqlite3
from datetime import datetime
# import smtplib  # Para e-mail futuro
# from email.mime.text import MIMEText

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="gestaofrota123")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY, placa TEXT UNIQUE, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS devolucoes (id INTEGER PRIMARY KEY, nome TEXT, placa TEXT, observacoes TEXT, status_final TEXT, imagem TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS prereservas (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, retirada TEXT, devolucao TEXT, motivo TEXT, status TEXT)")
conn.commit()

@app.get("/inicio", response_class=HTMLResponse)
def inicio(request: Request):
    gestor = request.session.get("gestor") == True
    return templates.TemplateResponse("home.html", {"request": request, "gestor": gestor})

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "erro": False})

@app.post("/login")
def login_post(request: Request, senha: str = Form(...)):
    if senha == "gestor123":
        request.session["gestor"] = True
        return RedirectResponse("/inicio", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "erro": True})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/inicio")

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
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "registros": registros,
        "status_count": status_count,
        "devolucao_count": devolucao_count
    })

@app.get("/formulario", response_class=HTMLResponse)
def formulario(request: Request):
    return templates.TemplateResponse("formulario.html", {"request": request})

@app.post("/formulario")
def reservar(nome: str = Form(...), email: str = Form(...), placa: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...)):
    cursor.execute("INSERT INTO registros (nome, email, placa, retirada, devolucao) VALUES (?, ?, ?, ?, ?)", (nome, email, placa, retirada, devolucao))
    cursor.execute("UPDATE veiculos SET status = 'em_uso' WHERE placa = ?", (placa,))
    conn.commit()
    # Aviso por e-mail futuro
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
    cursor.execute("SELECT id, retirada FROM prereservas WHERE status = 'pendente'")
    for pid, r in cursor.fetchall():
        if datetime.strptime(r, "%Y-%m-%d") >= datetime.now():
            cursor.execute("UPDATE prereservas SET status = 'atendido' WHERE id = ?", (pid,))
            conn.commit()
            break
    return RedirectResponse("/inicio", status_code=303)

@app.get("/admin/veiculos", response_class=HTMLResponse)
def cadastro(request: Request):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    return templates.TemplateResponse("cadastro_veiculo.html", {"request": request})

@app.post("/admin/veiculos")
def inserir_veiculo(placa: str = Form(...), status: str = Form(...)):
    cursor.execute("INSERT OR IGNORE INTO veiculos (placa, status) VALUES (?, ?)", (placa.upper(), status))
    conn.commit()
    return RedirectResponse("/admin/veiculos/listar", status_code=303)

@app.get("/admin/veiculos/listar", response_class=HTMLResponse)
def listar(request: Request):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT * FROM veiculos ORDER BY placa")
    veiculos = cursor.fetchall()
    return templates.TemplateResponse("listar_veiculos.html", {"request": request, "veiculos": veiculos})

@app.get("/prereserva", response_class=HTMLResponse)
def prereserva(request: Request, retirada: str = "", devolucao: str = ""):
    return templates.TemplateResponse("prereserva.html", {"request": request, "retirada": retirada, "devolucao": devolucao})

@app.post("/prereserva")
def enviar_pre(nome: str = Form(...), email: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...), motivo: str = Form(...)):
    cursor.execute("INSERT INTO prereservas (nome, email, retirada, devolucao, motivo, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                   (nome, email, retirada, devolucao, motivo))
    conn.commit()
    return RedirectResponse("/inicio", status_code=303)

@app.get("/admin/prereservas", response_class=HTMLResponse)
def ver_pre(request: Request):
    if request.session.get("gestor") != True:
        return RedirectResponse("/inicio")
    cursor.execute("SELECT * FROM prereservas ORDER BY retirada")
    reservas = cursor.fetchall()
    return templates.TemplateResponse("listar_prereservas.html", {"request": request, "prereservas": reservas})

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

@app.get("/backup")
def download_db():
    return FileResponse("frota.db", filename="frota-backup.db", media_type="application/octet-stream")