from werkzeug.security import generate_password_hash
import sqlite3

#Configurações do Admin

nome_completo = "Cuandoneque"
login_usuario = "admin"
palavra_passe = "0000"
tipo_conta = "admin"
hashed_pw = generate_password_hash (palavra_passe)


#Conexão com o SQLite

conn = sqlite3.connect('farmacia.db')
cursor = conn.cursor()

cursor.execute ("DELETE FROM usuarios WHERE usuario = ?", (login_usuario))

try:
     sql = "INSERT INTO usuarios(nome, usuario, senha, tipo) VALUES (?, ?, ?, ?)"
     cursor.execute (sql, (nome_completo, login_usuario, hashed_pw, tipo_conta))

     conn.commit()
     print ("Sucesso! Utilizador cadastrado como admin")

except Exception as e:
     print(f"Erro: {e}")
finally:
     conn.close
