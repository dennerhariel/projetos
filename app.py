from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import mysql.connector
from datetime import datetime, timedelta
import io
import csv
import random
import string
from flask_mail import Mail, Message
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'stockparts631@gmail.com'  # Seu endereço de email
app.config['MAIL_PASSWORD'] = 'eiitlxzgrcnzqcyq'  # Sua senha de app (não a senha normal do email)
app.config['MAIL_DEFAULT_SENDER'] = 'stockparts631@gmail.com'

mail = Mail(app)

def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        database='CST',
        user='root',
        password='root'
    )
    return conn

def format_date(value, format="%d/%m/%Y"):
    return value.strftime(format)

app.jinja_env.filters['date_format'] = format_date

def generate_random_password(length=8):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

def send_email(to_email, new_password):
    html_content = f"""\
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Recuperação de Senha</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background-color: #e66022;
                color: #ffffff;
                padding: 10px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                padding: 20px;
            }}
            .footer {{
                background-color: #e66022;
                color: #ffffff;
                padding: 10px;
                border-radius: 0 0 10px 10px;
                text-align: center;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin: 20px 0;
                background-color: #e66022;
                color: #ffffff;
                text-decoration: none;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://i.imgur.com/x3cZ0FS.png" alt="Logo"style="width: 113px; height: 80px;">
                <h1>Recuperação de Senha</h1>
            </div>
            <div class="content">
                <p>Olá,</p>
                <p>Você solicitou a recuperação de sua senha. Sua nova senha é:</p>
                <p><strong>{new_password}</strong></p>
                <p>Recomendamos que você altere esta senha assim 
                que fizer login.</p>
                <a href="{url_for('login', _external=True)}" class="button">Login</a>
            </div>
            <div class="footer">
                <p>&copy; 2024 StockParts. Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    msg = Message('Recuperação de Senha', recipients=[to_email])
    msg.html = html_content
    try:
        mail.send(msg)
    except Exception as e:
        print(f'Erro ao enviar e-mail: {e}')
        raise e

@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        conn.close()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']
            return redirect(url_for('home'))
        else:
            msg = 'Nome de usuário/senha incorretos!'
    return render_template('login.html', msg=msg)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Conta já existe!'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            conn.commit()
            msg = 'Conta criada com sucesso!'
        conn.close()

    return render_template('registro.html', msg=msg)

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
        account = cursor.fetchone()
        conn.close()

        if account:
            new_password = generate_random_password()

            try:
                # Envia o e-mail com a nova senha
                send_email(email, new_password)

                # Atualiza a senha no banco de dados
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE accounts SET password = %s WHERE email = %s', (new_password, email))
                conn.commit()
                conn.close()

                msg = 'Nova senha enviada para o e-mail.'
            except Exception as e:
                msg = f'Erro ao enviar e-mail. Tente novamente mais tarde. Detalhes: {e}'
        else:
            msg = 'E-mail não encontrado!'

    return render_template('recuperar_senha.html', msg=msg)

@app.route('/home')
def home():
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM estoque WHERE quantidade < 10 ORDER BY quantidade DESC LIMIT 5')
        pecas_baixa_quantidade = cursor.fetchall()
        
        cursor.execute('SELECT * FROM manutencao WHERE status = "Pendente"')
        manutencoes_pendentes = cursor.fetchall()

        cursor.execute('SELECT * FROM manutencao WHERE status = "Em andamento"')
        manutencoes_andamento = cursor.fetchall()
        
        conn.close()
        return render_template('home.html', username=session['username'], pecas=pecas_baixa_quantidade, manutencoes_pendentes=manutencoes_pendentes, manutencoes_andamento=manutencoes_andamento)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/controle_estoque')
def controle_estoque():
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM estoque')
        itens = cursor.fetchall()
        conn.close()
        return render_template('controle_estoque.html', itens=itens)
    return redirect(url_for('login'))

@app.route('/adicionar_item', methods=['POST'])
def adicionar_item():
    if 'loggedin' in session:
        nome = request.form['nome']
        quantidade = int(request.form['quantidade'])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM estoque WHERE nome = %s', (nome,))
        item = cursor.fetchone()

        if item:
            nova_quantidade = item['quantidade'] + quantidade
            cursor.execute('UPDATE estoque SET quantidade = %s WHERE id = %s', (nova_quantidade, item['id']))
        else:
            cursor.execute('INSERT INTO estoque (nome, quantidade) VALUES (%s, %s)', (nome, quantidade))

        conn.commit()
        conn.close()
        return redirect(url_for('controle_estoque'))
    return redirect(url_for('login'))

@app.route('/importar_xml', methods=['POST'])
def importar_xml():
    if 'loggedin' in session:
        file = request.files['file']
        if file:
            tree = ET.parse(file)
            root = tree.getroot()

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            for item in root.findall('peca'):
                nome = item.find('nome').text
                quantidade = int(item.find('quantidade').text)

                cursor.execute('SELECT * FROM estoque WHERE nome = %s', (nome,))
                db_item = cursor.fetchone()

                if db_item:
                    nova_quantidade = db_item['quantidade'] + quantidade
                    cursor.execute('UPDATE estoque SET quantidade = %s WHERE id = %s', (nova_quantidade, db_item['id']))
                else:
                    cursor.execute('INSERT INTO estoque (nome, quantidade) VALUES (%s, %s)', (nome, quantidade))

            conn.commit()
            conn.close()

        flash('Arquivo XML importado com sucesso!')
        return redirect(url_for('controle_estoque'))
    return redirect(url_for('login'))

@app.route('/registro_manutencao')
def registro_manutencao():
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM manutencao')
        manutencoes = cursor.fetchall()
        conn.close()
        return render_template('registro_manutencao.html', manutencoes=manutencoes)
    return redirect(url_for('login'))

@app.route('/adicionar_manutencao', methods=['POST'])
def adicionar_manutencao():
    if 'loggedin' in session:
        data = request.form['data']
        descricao = request.form['descricao']
        pecas = request.form['pecas']
        responsavel = request.form['responsavel']
        status = "Em andamento"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO manutencao (data, descricao, pecas, responsavel, status) VALUES (%s, %s, %s, %s, %s)', (data, descricao, pecas, responsavel, status))
        conn.commit()
        cursor.execute('UPDATE manutencao SET created_at = NOW() WHERE id = LAST_INSERT_ID()')
        conn.commit()
        conn.close()
        return redirect(url_for('registro_manutencao'))
    return redirect(url_for('login'))

@app.route('/saida_pecas', methods=['POST'])
def saida_pecas():
    if 'loggedin' in session:
        nome = request.form['nome']
        quantidade = int(request.form['quantidade'])
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, quantidade FROM estoque WHERE nome = %s', (nome,))
        item = cursor.fetchone()
        if item:
            id = item['id']
            current_quantity = item['quantidade']
            if current_quantity >= quantidade:
                nova_quantidade = current_quantity - quantidade
                cursor.execute('UPDATE estoque SET quantidade = %s WHERE id = %s', (nova_quantidade, id))
                conn.commit()
                cursor.execute('UPDATE estoque SET created_at = NOW() WHERE id = %s', (id,))
                conn.commit()
                conn.close()
                return '', 204
            else:
                conn.close()
                return 'Quantidade insuficiente no estoque!', 400
        else:
            conn.close()
            return 'Item não encontrado!', 404
    return redirect(url_for('login'))

@app.route('/concluir_manutencao/<int:id>', methods=['POST'])
def concluir_manutencao(id):
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE manutencao SET status = %s WHERE id = %s', ('Concluído', id))
        conn.commit()
        conn.close()
        return redirect(url_for('registro_manutencao'))
    return redirect(url_for('login'))

@app.route('/editar_manutencao/<int:id>', methods=['GET', 'POST'])
def editar_manutencao(id):
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM manutencao WHERE id = %s', (id,))
        manutencao = cursor.fetchone()
        conn.close()
        if request.method == 'POST' and 'data' in request.form and 'descricao' in request.form and 'pecas' in request.form and 'responsavel' in request.form:
            data = request.form['data']
            descricao = request.form['descricao']
            pecas = request.form['pecas']
            responsavel = request.form['responsavel']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE manutencao SET data = %s, descricao = %s, pecas = %s, responsavel = %s WHERE id = %s', (data, descricao, pecas, responsavel, id))
            conn.commit()
            conn.close()
            return redirect(url_for('registro_manutencao'))
        return render_template('editar_manutencao.html', manutencao=manutencao)
    return redirect(url_for('login'))

@app.route('/excluir_manutencao/<int:id>', methods=['POST'])
def excluir_manutencao(id):
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM manutencao WHERE id = %s', (id,))
        conn.commit()
        conn.close()
        return '', 204
    return redirect(url_for('login'))

@app.route('/relatorios')
def relatorios():
    if 'loggedin' in session:
        return render_template('relatorios.html')
    return redirect(url_for('login'))

@app.route('/gerar_relatorio', methods=['POST'])
def gerar_relatorio():
    if 'loggedin' in session:
        tipo = request.form['tipo']
        data_inicio = request.form['data_inicio']
        data_fim = request.form['data_fim']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if tipo == 'estoque':
            query = """
                SELECT * FROM estoque
                WHERE created_at BETWEEN %s AND %s
            """
        elif tipo == 'manutencao':
            query = """
                SELECT * FROM manutencao
                WHERE created_at BETWEEN %s AND %s
            """
        cursor.execute(query, (data_inicio, data_fim))
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        if tipo == 'estoque':
            writer.writerow(['ID', 'Nome', 'Quantidade', 'Data Entrada'])
        elif tipo == 'manutencao':
            writer.writerow(['ID', 'Data', 'Descrição', 'Peças', 'Responsável', 'Status'])
        for row in rows:
            writer.writerow(row.values())

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{tipo}_relatorio.csv'
        )
    return redirect(url_for('login'))

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'loggedin' in session:
        email_msg = ''
        password_msg = ''
        if request.method == 'POST':
            if 'email' in request.form:
                new_email = request.form['email']
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE accounts SET email = %s WHERE id = %s', (new_email, session['id']))
                conn.commit()
                conn.close()
                session['email'] = new_email
                email_msg = 'Email atualizado com sucesso!'
                flash(email_msg, 'email')
            elif 'current_password' in request.form and 'new_password' in request.form:
                current_password = request.form['current_password']
                new_password = request.form['new_password']
                confirm_password = request.form['confirm_password']
                if new_password != confirm_password:
                    password_msg = 'As senhas não coincidem!'
                    flash(password_msg, 'password')
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM accounts WHERE id = %s AND password = %s', (session['id'], current_password))
                    account = cursor.fetchone()
                    if account:
                        cursor.execute('UPDATE accounts SET password = %s WHERE id = %s', (new_password, session['id']))
                        conn.commit()
                        password_msg = 'Senha atualizada com sucesso!'
                        flash(password_msg, 'password')
                    else:
                        password_msg = 'Senha atual incorreta!'
                        flash(password_msg, 'password')
                    conn.close()

        return render_template('perfil.html', account=session)
    return redirect(url_for('login'))

@app.route('/suporte', methods=['GET', 'POST'])
def suporte():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']

        msg = Message(f'Suporte: {title}', 
                      sender='stockparts631suport@gmail.com', 
                      recipients=['stockparts631suport@gmail.com'])
        msg.body = description

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            with app.open_resource(file_path) as fp:
                msg.attach(filename, file.content_type, fp.read())

        mail.send(msg)
        flash('Solicitação de suporte enviada com sucesso!', 'suporte')
        return redirect(url_for('suporte'))

    return render_template('suporte.html')
if __name__ == '__main__':
    app.run(debug=True)
