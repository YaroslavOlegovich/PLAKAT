import logging
from flask import Flask
from flask_login import LoginManager
from models import db, Security, User
from backend.routes import register_routes
import csv
import os
from dotenv import load_dotenv
import sys
import traceback

# Перехватчик ошибок для логирования на Render
sys.excepthook = lambda type, value, tb: sys.stderr.write(''.join(traceback.format_exception(type, value, tb)))

load_dotenv()  # Загружаем переменные из .env

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moex.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Войдите, чтобы получить доступ."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

logging.basicConfig(level=logging.INFO)

# Регистрируем все маршруты
register_routes(app)
print("Регистрирую маршруты...")  # ← добавь эту строку

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Security.query.count() == 0:
            try:
                with open('securities.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        db.session.add(Security(ticker=row['ticker'], name=row['name']))
                db.session.commit()
                print("Справочник тикеров загружен")
            except FileNotFoundError:
                print("securities.csv не найден")
    print("Сервер запущен: http://127.0.0.1:5000")
    app.run(debug=True)
