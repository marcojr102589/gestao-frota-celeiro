from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, shutil, sqlite3
from datetime import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Conexão com banco SQLite
conn = sqlite3.connect("frota.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY, placa TEXT UNIQUE, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT, placa TEXT, retirada TEXT, devolucao TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS devolucoes (id INTEGER PRIMARY KEY, nome TEXT, placa TEXT, observacoes TEXT, status_final TEXT, imagem TEXT)")
conn.commit()

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    registros = cursor.fetchall()
    cursor.execute("SELECT * FROM devolucoes ORDER BY id DESC")
    devolucoes = cursor.fetchall()
    cursor.execute("SELECT * FROM veiculos ORDER BY placa")
    veiculos = cursor.fetchall()

    status_count = {"disponivel": 0, "em_uso": 0, "manutencao": 0}
    for v in veiculos:
        status_count[v[2]] += 1

    placa_count = {}
    for r in registros:
        placa_count[r[3]] = placa_count.get(r[3], 0) + 1

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "registros": registros,
        "devolucoes": devolucoes,
        "veiculos": veiculos,
        "status_count": status_count,
        "placa_count": placa_count
    })

@app.get("/formulario", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("formulario.html", {"request": request, "placas": [], "retirada": "", "devolucao": ""})

@app.get("/disponiveis", response_class=HTMLResponse)
def veiculos_disponiveis(request: Request, retirada: str = Query(...), devolucao: str = Query(...)):
    data_ret = datetime.strptime(retirada, "%Y-%m-%d")
    data_dev = datetime.strptime(devolucao, "%Y-%m-%d")
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'disponivel'")
    todas_placas = [r[0] for r in cursor.fetchall()]
    cursor.execute("""
        SELECT DISTINCT placa FROM registros
        WHERE 
            (date(retirada) <= date(?) AND date(devolucao) >= date(?)) OR
            (date(retirada) >= date(?) AND date(retirada) <= date(?)) OR
            (date(devolucao) >= date(?) AND date(devolucao) <= date(?))
    """, (data_dev, data_ret, data_ret, data_dev, data_ret, data_dev))
    placas_ocupadas = set([r[0] for r in cursor.fetchall()])
    placas_livres = [p for p in todas_placas if p not in placas_ocupadas]
    return templates.TemplateResponse("formulario.html", {
        "request": request,
        "placas": placas_livres,
        "retirada": retirada,
        "devolucao": devolucao
    })

@app.post("/formulario")
def agendar(nome: str = Form(...), email: str = Form(...), placa: str = Form(...), retirada: str = Form(...), devolucao: str = Form(...)):
    cursor.execute("INSERT INTO registros (nome, email, placa, retirada, devolucao) VALUES (?, ?, ?, ?, ?)", (nome, email, placa, retirada, devolucao))
    cursor.execute("UPDATE veiculos SET status = 'em_uso' WHERE placa = ?", (placa,))
    conn.commit()
    return RedirectResponse("/formulario?ok=1", status_code=303)

@app.get("/devolucao", response_class=HTMLResponse)
def devolucao_form(request: Request):
    cursor.execute("SELECT placa FROM veiculos WHERE status = 'em_uso'")
    placas = [r[0] for r in cursor.fetchall()]
    return templates.TemplateResponse("devolucao.html", {"request": request, "placas": placas})

@app.post("/devolucao")
def registrar_devolucao(nome: str = Form(...), placa: str = Form(...), observacoes: str = Form(...), status_final: str = Form(...), imagem: UploadFile = File(None)):
    filename = ""
    if imagem:
        ext = os.path.splitext(imagem.filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{placa}_{timestamp}{ext}"
        path = os.path.join("static/uploads", filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(imagem.file, buffer)
    cursor.execute("INSERT INTO devolucoes (nome, placa, observacoes, status_final, imagem) VALUES (?, ?, ?, ?, ?)",
                   (nome, placa, observacoes, status_final, filename))
    cursor.execute("UPDATE veiculos SET status = ? WHERE placa = ?", (status_final, placa))
    conn.commit()
    return RedirectResponse("/devolucao?ok=1", status_code=303)
@app.get("/admin/veiculos", response_class=HTMLResponse)
def form_veiculo(request: Request):
    return templates.TemplateResponse("cadastro_veiculo.html", {"request": request})

@app.post("/admin/veiculos")
def inserir_veiculo(placa: str = Form(...), status: str = Form(...)):
    cursor.execute("INSERT OR IGNORE INTO veiculos (placa, status) VALUES (?, ?)", (placa.upper(), status))
    conn.commit()
    return RedirectResponse("/admin/veiculos/listar", status_code=303)

@app.get("/admin/veiculos/listar", response_class=HTMLResponse)
def listar_veiculos(request: Request):
    cursor.execute("SELECT * FROM veiculos ORDER BY placa")
    veiculos = cursor.fetchall()
    return templates.TemplateResponse("listar_veiculos.html", {"request": request, "veiculos": veiculos})
