import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery

logging.basicConfig(level=logging.INFO)

# НАСТРОЙКИ
BOT_TOKEN = "8629870935:AAHA7umAHSD86CxFQ1mJ7lcyTwuv_EzTSSs"
BOT_USERNAME = "PLAKATMOEX_BOT"
SITE_SECRET = "supersecretkey"
SITE_URL = "http://127.0.0.1:5000/api/activate-sub"

PRICE_STARS = 150
SUBSCRIPTION_DAYS = 30

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Админы, которые получают сообщения от пользователей
ADMIN_IDS = [1019310612, 1661066590]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("pay_"):
        user_id = args[1].replace("pay_", "")
        await message.answer(
            f"Счёт на оплату подписки (30 дней, 299 ₽).\n"
            f"Ваш ID: {user_id}\n\n"
            "Нажмите кнопку ниже для оплаты через Telegram Stars."
        )
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="ПЛАКАТ — Подписка",
            description="Доступ к анализу акций на 30 дней",
            payload=f"sub_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Подписка на 30 дней", amount=PRICE_STARS)]
        )
    else:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="💳 Оплатить подписку")],
                [types.KeyboardButton(text="📞 Связаться с нами")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "👋 Добро пожаловать! Я бот для оплаты подписки на ПЛАКАТ.\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )

@dp.message(Command("pay"))
async def cmd_pay(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите ID пользователя: /pay 123")
        return
    user_id = args[1]
    await message.answer(f"Выставляю счёт для ID {user_id}...")
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="ПЛАКАТ — Подписка",
        description="Доступ к анализу акций на 30 дней",
        payload=f"sub_{user_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка на 30 дней", amount=PRICE_STARS)]
    )

@dp.message(F.text == "💳 Оплатить подписку")
async def btn_pay(message: types.Message):
    await message.answer(
        "Чтобы оплатить подписку, перейдите по ссылке с сайта (кнопка «Оплатить через Telegram» в разделе «Подписка»).\n\n"
        "Или напишите /pay <ваш ID пользователя> (ID можно найти в профиле на сайте)."
    )

@dp.message(F.text == "📞 Связаться с нами")
async def btn_contact(message: types.Message):
    await message.answer(
        "📞 Контакты ПЛАКАТ:\n\n"
        "По вопросам подписки и оплаты: @PLAKATMOEX_BOT\n"
        "Техподдержка и предложения: напишите сюда же, мы ответим в течение 24 часов.\n\n"
        "Или просто напишите своё сообщение прямо сейчас — мы его увидим."
    )

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@dp.message(F.successful_payment)
async def on_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    user_id = payload.replace("sub_", "")
    try:
        resp = requests.post(
            SITE_URL,
            json={"user_id": int(user_id), "secret": SITE_SECRET},
            timeout=10
        )
        data = resp.json()
        if data.get("success"):
            await message.answer(
                f"✅ Подписка активирована!\n"
                f"Действует до: {data.get('message', '').replace('Подписка активирована до ', '')}\n"
                f"Вернитесь на сайт и войдите в аккаунт."
            )
        else:
            await message.answer(f"❌ Ошибка активации: {data.get('message', 'Неизвестная ошибка')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка связи с сайтом: {str(e)}")

@dp.message(F.text, ~F.text.startswith("/"))
async def forward_to_admins(message: types.Message):
    if message.text in ["💳 Оплатить подписку", "📞 Связаться с нами"]:
        return

    user_info = f"Сообщение от @{message.from_user.username or 'без username'} (ID: {message.from_user.id}):"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"{user_info}\n\n{message.text}")
        except:
            pass
    await message.answer("✅ Ваше сообщение отправлено. Мы ответим в ближайшее время.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())