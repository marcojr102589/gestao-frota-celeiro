# Implementações: Notificações, Conflitos e Edição de Reservas

## ✅ 1. Notificação por e-mail ao gestor (pré-reserva pendente)
- Usar `smtplib` e `email.message` para disparo
- Enviar e-mail para `gestor@empresa.com` sempre que uma nova prereserva for criada

## ✅ 2. Notificação por e-mail ao usuário após reserva
- Após inserção em `registros`, enviar e-mail para `email` informado
- Assunto: Reserva Confirmada
- Conteúdo: Dados da reserva (placa, datas)

---

## ✅ 3. Validação de conflitos de datas
- Antes de registrar nova reserva:
  - Verificar se o veículo está disponível nesse período
  - Buscar no `registros` se há interseção com `retirada` e `devolucao`
- Bloquear a duplicidade com mensagem clara na tela

---

## ✅ 4. Permitir editar uma reserva
- Criar rota GET `/admin/reservas/editar/{id}` com formulário de edição
- Criar rota POST `/admin/reservas/atualizar`
- Campos editáveis:
  - nome, email, placa, retirada, devolucao

---

## 🧩 Dependências externas
- Enviar e-mail: requer configuração SMTP (exemplo com Gmail):
```python
import smtplib
from email.message import EmailMessage

def enviar_email(destinatario, assunto, conteudo):
    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = 'sistemafrota@seudominio.com'
    msg['To'] = destinatario
    msg.set_content(conteudo)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('usuario@gmail.com', 'senha-app')
        smtp.send_message(msg)
```

---

## 📌 Sugestão
- Criar `.env` com credenciais de envio
- Usar `python-dotenv` para carregar variáveis