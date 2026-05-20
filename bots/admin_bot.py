import asyncio
import logging
import requests
import io
import sys
import os

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import docx2txt

from flask import current_app

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8616357665:AAEQjhkmXeoddU1I4OL4RGkrD39QZjoSxmk"
SITE_SECRET = "supersecretkey"
SITE_URL = "http://127.0.0.1:5000"
ALLOWED_USERS = [1019310612, 1661066590]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_allowed(user_id):
    return user_id in ALLOWED_USERS

# Функция для получения контекста приложения
def get_app():
    from app import app
    return app

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return
    await message.answer(
        "🔐 Админ-бот ПЛАКАТ\n\n"
        "📰 **Управление новостями:**\n"
        "/list_news — список новостей\n"
        "/del_news <id> — удалить новость\n"
        "/clear_news — удалить ВСЕ новости\n\n"
        "📊 **Статистика:**\n"
        "/stats — статистика пользователей\n\n"
        "👤 **Пользователи:**\n"
        "/block <id> — заблокировать\n"
        "/unblock <id> — разблокировать\n\n"
        "🎟️ **Промокоды:**\n"
        "/promo <код> — создать промокод\n\n"
        "📄 **Другое:**\n"
        "Отправьте .docx — опубликовать новость",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_allowed(message.from_user.id):
        return
    try:
        from app import app
        from models import User, Subscription
        with app.app_context():
            users = User.query.count()
            subs = Subscription.query.filter_by(is_active=True).count()
        await message.answer(f"📊 Пользователей: {users}\nАктивных подписок: {subs}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(Command("block"))
async def cmd_block(message: Message):
    if not is_allowed(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /block <user_id>")
        return
    user_id = args[1]
    resp = requests.post(f"{SITE_URL}/api/block-user", json={"user_id": int(user_id), "secret": SITE_SECRET})
    await message.answer(f"Результат: {resp.json().get('message', 'OK')}")

@dp.message(Command("unblock"))
async def cmd_unblock(message: Message):
    if not is_allowed(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unblock <user_id>")
        return
    user_id = args[1]
    from app import app
    from models import User
    with app.app_context():
        user = User.query.get(int(user_id))
        if user:
            user.is_blocked = False
            db.session.commit()
            await message.answer(f"Пользователь {user.email} разблокирован")
        else:
            await message.answer("Пользователь не найден")

@dp.message(Command("promo"))
async def cmd_promo(message: Message):
    if not is_allowed(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /promo <код>")
        return
    code = args[1].upper()
    from app import app
    from models import PromoCode
    with app.app_context():
        exists = PromoCode.query.filter_by(code=code).first()
        if exists:
            await message.answer("Такой промокод уже существует")
        else:
            db.session.add(PromoCode(code=code))
            db.session.commit()
            await message.answer(f"Промокод {code} создан")

@dp.message(Command("list_news"))
async def cmd_list_news(message: Message):
    if not is_allowed(message.from_user.id):
        return
    try:
        from app import app
        from models import News
        with app.app_context():
            all_news = News.query.order_by(News.created_at.desc()).all()
            if not all_news:
                await message.answer("📭 Новостей нет")
                return
            
            news_list = "📰 **Список новостей:**\n\n"
            for n in all_news[:15]:
                news_list += f"**ID:** `{n.id}`\n"
                news_list += f"**Заголовок:** {n.title[:50]}\n"
                news_list += f"**Дата:** {n.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                news_list += "——————————\n"
            
            await message.answer(news_list, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("del_news"))
async def cmd_del_news(message: Message):
    if not is_allowed(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: `/del_news <id>`\n\nЧтобы узнать ID новости, отправьте `/list_news`", parse_mode="Markdown")
        return
    
    try:
        news_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    
    try:
        from app import app
        from models import News, db
        with app.app_context():
            news = News.query.get(news_id)
            if not news:
                await message.answer(f"❌ Новость с ID `{news_id}` не найдена", parse_mode="Markdown")
                return
            
            title = news.title
            db.session.delete(news)
            db.session.commit()
            
            await message.answer(f"✅ Новость **{title}** удалена", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("clear_news"))
async def cmd_clear_news(message: Message):
    if not is_allowed(message.from_user.id):
        return
    await message.answer("⚠️ Вы уверены? Отправьте `/clear_news_confirm` для подтверждения")

@dp.message(Command("clear_news_confirm"))
async def cmd_clear_news_confirm(message: Message):
    if not is_allowed(message.from_user.id):
        return
    
    try:
        from app import app
        from models import News, db
        with app.app_context():
            count = News.query.count()
            News.query.delete()
            db.session.commit()
            
            await message.answer(f"✅ Удалено {count} новостей")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.document)
async def handle_doc(message: Message):
    if not is_allowed(message.from_user.id):
        return
    doc = message.document
    if not doc.file_name.endswith('.docx'):
        await message.answer("Только .docx")
        return
    await message.answer("Обрабатываю...")
    try:
        file = await bot.get_file(doc.file_id)
        downloaded = await bot.download_file(file.file_path)
        text = docx2txt.process(io.BytesIO(downloaded.read()))
        lines = text.strip().split('\n')
        title = lines[0].strip() if lines else "Новость"
        content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
        resp = requests.post(f"{SITE_URL}/api/add-news", json={"title": title, "content": content, "secret": SITE_SECRET}, timeout=10)
        if resp.status_code == 200:
            await message.answer(f"✅ Новость: «{title}»")
        else:
            await message.answer(f"❌ Ошибка: {resp.status_code}")
    except Exception as e:
        await message.answer(f"❌ {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())