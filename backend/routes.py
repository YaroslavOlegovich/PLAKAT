# backend/routes.py
from flask import request, render_template_string, redirect, url_for, jsonify, send_file
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from models import db, Security, Candle, User, Subscription, PromoCode, News
from engine import generate_idea, create_plot
import pandas as pd
import csv
import io
import base64
import os
import tempfile

def has_active_subscription():
    if not current_user.is_authenticated:
        return False
    sub = Subscription.query.filter_by(
        user_id=current_user.id, is_active=True
    ).filter(Subscription.end_date >= date.today()).first()
    return sub is not None

def check_blocked():
    if current_user.is_authenticated and current_user.is_blocked:
        logout_user()
        return True
    return False

def register_routes(app):

    @app.before_request
    def before_request():
        if check_blocked():
            return redirect(url_for('login'))

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('analyze'))
        from frontend.templates import render_base
        return render_base("""
            <h2>📈 Анализ акций Мосбиржи</h2>
            <p style="font-size:18px;">Сервис технического анализа с торговыми идеями, тейк-профитом и стоп-лоссом.</p>
            <p>Для доступа ко всем функциям <a href="/register" style="color:#cc0000;">зарегистрируйтесь</a> и приобретите подписку или активируйте промокод.</p>
        """)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        from frontend.templates import render_base
        error = ""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            if not email or not password:
                error = "Заполните все поля"
            elif User.query.filter_by(email=email).first():
                error = "Пользователь уже существует"
            else:
                user = User(email=email, password_hash=generate_password_hash(password))
                import random, string
                user.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for('subscribe'))
        content = f"""
            <h2>🔐 Регистрация</h2>
            <form method="post">
                <input type="email" name="email" placeholder="Email" required><br><br>
                <input type="password" name="password" placeholder="Пароль" required><br><br>
                <button type="submit" class="btn">Зарегистрироваться</button>
            </form>
            <p style="color:red;">{error}</p>
            <p>Уже есть аккаунт? <a href="/login" style="color:#cc0000;">Войти</a></p>
        """
        return render_base(content, "Регистрация")

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        from frontend.templates import render_base
        error = ""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                error = "Неверный email или пароль"
            elif user.is_blocked:
                error = "Аккаунт заблокирован"
            else:
                login_user(user)
                return redirect(url_for('analyze'))
        content = f"""
            <h2>🔐 Вход</h2>
            <form method="post">
                <input type="email" name="email" placeholder="Email" required><br><br>
                <input type="password" name="password" placeholder="Пароль" required><br><br>
                <button type="submit" class="btn">Войти</button>
            </form>
            <p style="color:red;">{error}</p>
            <p>Нет аккаунта? <a href="/register" style="color:#cc0000;">Зарегистрироваться</a></p>
        """
        return render_base(content, "Вход")

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        from frontend.templates import render_base
        if request.method == 'POST':
            interval = request.form.get('interval', 'D')
            current_user.analysis_interval = interval
            db.session.commit()

        active_sub = Subscription.query.filter_by(
            user_id=current_user.id, is_active=True
        ).filter(Subscription.end_date >= date.today()).first()

        if active_sub:
            remaining = (active_sub.end_date - date.today()).days
            sub_info = f"""
                <div class="result-block" style="margin-top:0;">
                    <p style="font-size:18px;"><b>✅ Подписка активна</b></p>
                    <p>Осталось дней: <b>{remaining}</b> (до {active_sub.end_date.strftime('%d.%m.%Y')})</p>
                </div>
            """
        else:
            sub_info = """
                <div class="error" style="margin-top:0;">
                    <p>❌ У вас нет активной подписки.</p>
                    <p><a href="/subscribe" style="color:#cc0000;">Оформить подписку</a></p>
                </div>
            """

        selected_d = 'selected' if current_user.analysis_interval == 'D' else ''
        selected_h = 'selected' if current_user.analysis_interval == 'H' else ''
        if not current_user.referral_code:
            import random, string
            current_user.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            db.session.commit()

        content = f"""
            <h2>Профиль</h2>
            
            <p><strong>Email:</strong> {current_user.email}</p>
            <p><strong>User ID:</strong> {current_user.id}</p>
            <p><strong>Реферальный код:</strong> <code>{current_user.referral_code}</code></p>
            <p style="color:var(--text-muted); font-size:13px;">Отправьте этот код другу — он получит 7 дней доступа, а вы +12 дней к подписке.</p>
            
            {sub_info}
            
            <div style="margin-top:30px; padding:20px; background:var(--card-bg); border:1px solid var(--border); border-radius:12px;">
                <h3 style="margin-bottom:12px;">⚙️ Настройки анализа</h3>
                <form method="post">
                    <label style="font-size:14px;">Тип сигналов:</label>
                    <select name="interval" id="intervalSelect" onchange="this.form.submit()" style="padding:8px 12px; border-radius:6px; margin-left:8px; font-size:14px;">
                        <option value="D" {selected_d}>📅 Дневные (долгосрочные)</option>
                        <option value="H" {selected_h}>⏰ Часовые (краткосрочные)</option>
                    </select>
                </form>
                <div id="intervalHint" style="display:none; margin-top:12px; padding:14px 18px; background:var(--card-bg); border:1px solid #f39c12; border-left:4px solid #f39c12; border-radius:8px; font-size:14px; color:var(--text);">
                    ⚠️ <b>Для краткосрочных сигналов необходимо загружать часовые свечи.</b><br>
                    Используйте кнопку <b>«Анализировать»</b> — данные подтянутся автоматически с часовым интервалом.
                </div>
                <script>
                function showIntervalHint(val) {{
                    var hint = document.getElementById('intervalHint');
                    if (hint) hint.style.display = val === 'H' ? 'block' : 'none';
                }}
                document.addEventListener('DOMContentLoaded', function() {{
                    var select = document.getElementById('intervalSelect');
                    if (select) showIntervalHint(select.value);
                }});
                </script>
            </div>
            
            <div style="margin-top:20px; padding:20px; background:var(--card-bg); border:1px solid var(--border); border-radius:12px;">
                <h3 style="margin-bottom:12px;">🎨 Оформление</h3>
                <button onclick="toggleTheme()" id="themeBtn" class="btn-outline" style="padding:10px 20px; font-size:14px;">🌙 Тёмная тема</button>
            </div>
            
            <div style="margin-top:20px;">
                <a href="/subscribe" class="btn">💳 Управление подпиской</a>
                <a href="/logout" class="btn" style="background:#000; margin-left:10px;">🚪 Выйти</a>
            </div>
        """
        return render_base(content, "Профиль")

    @app.route('/subscribe')
    @login_required
    def subscribe():
        from frontend.templates import render_base
        content = f"""
            <h2>💳 Подписка</h2>
            <p>Ваш ID: <b>{current_user.id}</b></p>
            <p>Стоимость подписки: <b>299 ₽/мес</b> (оплата через Telegram Stars)</p>
            <p><a href="https://t.me/PLAKATMOEX_BOT?start=pay_{current_user.id}" class="btn" target="_blank">Оплатить через Telegram</a></p>
            <p style="margin-top:20px; font-size:16px;">⚠️ <b>Важно!</b> После перехода в бота нажмите <b>START</b>.</p>
            <p style="margin-top:20px;"><a href="/activate-promo" style="color:#cc0000; font-size:18px;">🎟️ У меня есть промокод</a></p>
            <p style="margin-top:20px;">После оплаты бот активирует подписку автоматически.</p>
        """
        return render_base(content, "Подписка")

    @app.route('/activate-promo', methods=['GET', 'POST'])
    @login_required
    def activate_promo():
        from frontend.templates import render_base
        msg = ""
        if request.method == 'POST':
            code = request.form.get('code', '').strip().upper()
            
            promo = PromoCode.query.filter_by(code=code, is_used=False).first()
            if promo:
                days = 3 if code == 'PLAK3' else 36500
                today = date.today()
                end_date = today + timedelta(days=days)
                Subscription.query.filter_by(user_id=current_user.id, is_active=True).update({"is_active": False})
                sub = Subscription(user_id=current_user.id, start_date=today, end_date=end_date, is_active=True)
                db.session.add(sub)
                promo.is_used = True
                db.session.commit()
                msg = f'<div style="color:green; font-weight:bold;">✅ Подписка активирована на {days} дн. Действует до {end_date}</div>'
            else:
                referrer = User.query.filter_by(referral_code=code).first()
                if referrer and referrer.id != current_user.id and not current_user.referred_by:
                    days = 7
                    today = date.today()
                    end_date = today + timedelta(days=days)
                    Subscription.query.filter_by(user_id=current_user.id, is_active=True).update({"is_active": False})
                    new_sub = Subscription(user_id=current_user.id, start_date=today, end_date=end_date, is_active=True)
                    db.session.add(new_sub)
                    current_user.referred_by = referrer.id
                    
                    ref_sub = Subscription.query.filter_by(user_id=referrer.id, is_active=True).order_by(Subscription.end_date.desc()).first()
                    if ref_sub and ref_sub.end_date >= date.today():
                        ref_sub.end_date = ref_sub.end_date + timedelta(days=12)
                    else:
                        ref_sub = Subscription(user_id=referrer.id, start_date=date.today(), end_date=date.today() + timedelta(days=12), is_active=True)
                        db.session.add(ref_sub)
                    
                    db.session.commit()
                    msg = f'<div style="color:green; font-weight:bold;">✅ Реферальный код активирован! Вы получили {days} дн., реферер +12 дн.</div>'
                elif referrer and referrer.id == current_user.id:
                    msg = '<div class="error">Нельзя использовать свой реферальный код</div>'
                elif current_user.referred_by:
                    msg = '<div class="error">Вы уже использовали реферальный код</div>'
                else:
                    msg = '<div class="error">Промокод не найден или уже использован</div>'
        
        content = f"""
            <h2>🎟️ Активация промокода</h2>
            <form method="post">
                <label style="font-size:18px;">Введите промокод:</label><br><br>
                <input type="text" name="code" placeholder="Введите промокод или реферальный код" required>
                <button type="submit" class="btn">Активировать</button>
            </form>
            <p style="margin-top:20px;">{msg}</p>
            <p><a href="/subscribe" style="color:#cc0000;">← На страницу подписки</a></p>
        """
        return render_base(content, "Промокод")

    @app.route('/analyze', methods=['GET', 'POST'])
    @login_required
    def analyze():
        from frontend.templates import render_base
        from engine.moex_api import get_moex_candles
        if not has_active_subscription():
            return redirect(url_for('subscribe'))

        error_block = result_block = ""
        
        # GET запрос — показываем пустую форму
        if request.method == 'GET':
            content = f"""
                <h2>Анализ акции</h2>
                <form method="post">
                    <label style="font-size:18px;">Введите тикер (SBER, GAZP, LKOH...):</label><br><br>
                    <input type="text" name="ticker" placeholder="Например: SBER" required style="width:250px;">
                    <button type="submit" class="btn" style="margin-left:10px;">Анализировать</button>
                </form>
                <div style="margin-top:20px;">
                    <a href="/history" class="btn-outline" style="display: inline-block; padding:10px 20px; text-decoration:none;">История сигналов</a>
                </div>
            """
            return render_base(content)
        
        # POST запрос — анализируем
        ticker = request.form.get('ticker', '').strip().upper()
        if not ticker:
            error_block = '<div class="error">Введите тикер</div>'
            content = f"""
                <h2>Анализ акции</h2>
                <form method="post">
                    <label style="font-size:18px;">Введите тикер (SBER, GAZP, LKOH...):</label><br><br>
                    <input type="text" name="ticker" placeholder="Например: SBER" required style="width:250px;">
                    <button type="submit" class="btn" style="margin-left:10px;">Анализировать</button>
                </form>
                {error_block}
                <div style="margin-top:20px;">
                    <a href="/history" class="btn-outline" style="display: inline-block; padding:10px 20px; text-decoration:none;">История сигналов</a>
                </div>
            """
            return render_base(content)
        
        interval = getattr(current_user, 'analysis_interval', 'D')
        df = get_data_from_db(ticker, interval)
        
        # Если данных нет в БД — автоматически загружаем с MOEX
        if df is None:
            moex_interval = 'day' if interval == 'D' else 'hour'
            df = get_moex_candles(ticker, interval=moex_interval, days=180)
            
            if df is not None and not df.empty:
                # Сохраняем в базу
                from models import Security, Candle
                with app.app_context():
                    security = Security.query.filter_by(ticker=ticker).first()
                    if not security:
                        security = Security(ticker=ticker, name=ticker)
                        db.session.add(security)
                        db.session.commit()
                    
                    for _, row in df.iterrows():
                        date_val = row['date'].to_pydatetime()
                        exists = Candle.query.filter_by(security_id=security.id, date=date_val).first()
                        if not exists:
                            candle = Candle(
                                security_id=security.id,
                                date=date_val,
                                open=float(row['open']),
                                high=float(row['high']),
                                low=float(row['low']),
                                close=float(row['close']),
                                volume=int(float(row['volume'])) if pd.notna(row['volume']) else 0
                            )
                            db.session.add(candle)
                    db.session.commit()
        
        # Повторно проверяем наличие данных после загрузки
        df = get_data_from_db(ticker, interval)
        
        if df is None:
            error_block = f'<div class="error">❌ Не удалось загрузить данные для {ticker}. Проверьте тикер или попробуйте позже.</div>'
            content = f"""
                <h2>Анализ акции</h2>
                <form method="post">
                    <label style="font-size:18px;">Введите тикер (SBER, GAZP, LKOH...):</label><br><br>
                    <input type="text" name="ticker" placeholder="Например: SBER" required style="width:250px;">
                    <button type="submit" class="btn" style="margin-left:10px;">Анализировать</button>
                </form>
                {error_block}
                <div style="margin-top:20px;">
                    <a href="/history" class="btn-outline" style="display: inline-block; padding:10px 20px; text-decoration:none;">История сигналов</a>
                </div>
            """
            return render_base(content)
        
        # Анализируем
        result = generate_idea(df, ticker, interval)
        
        # Сохраняем в историю сигналов
        from models import SignalHistory
        signal = SignalHistory(
            user_id=current_user.id,
            ticker=result['ticker'],
            direction=result['direction'],
            price=result['last_price'],
            take_profit=result.get('take_profit'),
            stop_loss=result.get('stop_loss'),
            rationale=result.get('rationale')
        )
        db.session.add(signal)
        db.session.commit()
        
        result['theme'] = request.cookies.get('theme', 'light')
        plot_img = create_plot(df, result)
        
        tp_block = ""
        if result['take_profit']:
            tp_block = f"""
                <p><span class="green">▲ Тейк-профит:</span> {result['take_profit']} ₽</p>
                <p><span class="red">▼ Стоп-лосс:</span> {result['stop_loss']} ₽</p>
            """
        
        result_block = f"""
            <div class="result-block">
                <h2>Результат для {result['ticker']}</h2>
                <p><b>Цена закрытия:</b> {result['last_price']} ₽</p>
                <p><b>RSI:</b> {result['rsi']} | <b>Stochastic K/D:</b> {result['stoch_k']}/{result['stoch_d']}</p>
                <p><b>MACD:</b> {result['macd']} / Сигнал {result['macd_signal']}</p>
                <p><b>Bollinger:</b> {result['bb_lower']} — {result['bb_upper']}</p>
                <p><b>CCI:</b> {result['cci']} | <b>ADX:</b> {result['adx']}</p>
                <p><b>Объём:</b> {result['volume_ratio']}x | <b>ATR:</b> {result['atr']} ₽</p>
                <p><b>EMA:</b> {result['ema20']} ₽ | <b>SAR:</b> {result['sar']} ({result['sar_trend']})</p>
                <p><b>Pivot:</b> {result['pivot']} (R1: {result['r1']}, S1: {result['s1']})</p>
                <p><b>Ichimoku:</b> Tenkan={result['tenkan']}, Kijun={result['kijun']}</p>
                <h3>Торговая идея: {result['direction']}</h3>
                <p>{result['rationale']}</p>
                {tp_block}
                <h3 style="text-align:center; margin:20px 0 10px; font-size:22px; color:{'#2e7d32' if result['direction'] == 'ПОКУПКА' else '#c62828' if result['direction'] == 'ПРОДАЖА' else '#888'};">
                    {result['direction']}
                </h3>
                <div id="chart-container">
                    <div class="skeleton" id="chart-skeleton"></div>
                    <img src="{plot_img}" class="plot-image" alt="График" id="main-chart" style="display:none;">
                </div>
                <script>
                (function() {{
                    var img = document.getElementById('main-chart');
                    if (img) {{
                        img.onload = function() {{
                            var skel = document.getElementById('chart-skeleton');
                            if (skel) skel.style.display = 'none';
                            img.style.display = 'block';
                        }};
                        if (img.complete) img.onload();
                    }}
                }})();
                </script>
                <div style="margin-top:20px; text-align:center;">
                    <a href="/download-pdf/{ticker}" target="_blank" style="display:inline-block; background:#d32f2f; color:#fff; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:600;">📄 Скачать PDF</a>
                </div>
                <p><i>Дисклеймер: Это не инвестиционная рекомендация.</i></p>
            </div>
        """
        
        content = f"""
            <h2Анализ акции</h2>
            <form method="post">
                <label style="font-size:18px;">Введите тикер (SBER, GAZP, LKOH...):</label><br><br>
                <input type="text" name="ticker" placeholder="Например: SBER" required style="width:250px;">
                <button type="submit" class="btn" style="margin-left:10px;">Анализировать</button>
            </form>
            {result_block}
            <div style="margin-top:20px;">
                <a href="/history" class="btn-outline" style="display: inline-block; padding:10px 20px; text-decoration:none;">История сигналов</a>
            </div>
        """
        return render_base(content)

    @app.route('/portfolios')
    @login_required
    def portfolios():
        from frontend.templates import render_base
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        content = """
            <h2>Готовые портфели</h2>
            
            <div class="portfolio-item">
                <h3>💵 Портфель на 5 000 ₽</h3>
                <p style="color:var(--text-muted); margin-bottom:12px;">Стартовый бюджет с фокусом на дивиденды и облигации.</p>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">50% (2 500 ₽)</td><td style="padding:10px;">Фонд облигаций «Первая — Государственные облигации» (ОФЗ, пай ~14 ₽, дох. ~28%)NonNull</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">30% (1 500 ₽)</td><td style="padding:10px;">Дивидендные акции: МТС (MTSS) или Россети Ленэнерго (префы LSNGP)</td></tr>
                    <tr><td style="padding:10px; font-weight:600;">20% (1 000 ₽)</td><td style="padding:10px;">ETF на индекс Мосбиржи для диверсификации (Сбер, Лукойл)</td></tr>
                </table>
            </div>
            
            <div class="portfolio-item">
                <h3>💵 Портфель на 10 000 ₽</h3>
                <p style="color:var(--text-muted); margin-bottom:12px;">Баланс дивидендов и роста с надёжными эмитентами.</p>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">40% (4 000 ₽)</td><td style="padding:10px;">ОФЗ или корп. облигации: ГТЛК, Альфа-банк (дох. 21-24%)</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">40% (4 000 ₽)</td><td style="padding:10px;">Дивидендные акции: Лукойл (LKOH), Северсталь (CHMF), Фосагро (PHOR)</td></tr>
                    <tr><td style="padding:10px; font-weight:600;">20% (2 000 ₽)</td><td style="padding:10px;">Растущие акции: Яндекс (YDEX)</td></tr>
                </table>
            </div>
            
            <div class="portfolio-item">
                <h3>💵 Портфель на 20 000 ₽</h3>
                <p style="color:var(--text-muted); margin-bottom:12px;">Дивидендный фокус с элементами роста для стабильного дохода.</p>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">30% (6 000 ₽)</td><td style="padding:10px;">Фонд облигаций «Т-Капитал — Российские облигации» (дох. ~27%)</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">50% (10 000 ₽)</td><td style="padding:10px;">Дивиденды: МТС (MTSS), Россети Ленэнерго (LSNGP), Лукойл (LKOH)</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">20% (4 000 ₽)</td><td style="padding:10px;">Голубые фишки: Сбербанк (SBER), ВТБ (VTBR)</td></tr>
                </table>
                <div class="instruction" style="margin-top:16px; padding:14px; font-size:14px;">
                    <table style="width:100%; border-collapse:collapse;">
                        <tr style="background:var(--card-bg);"><th style="padding:8px; text-align:left;">Актив</th><th style="padding:8px; text-align:left;">Доля</th><th style="padding:8px; text-align:left;">Ожидаемая доходность</th></tr>
                        <tr><td style="padding:8px;">Облигации (фонды)</td><td style="padding:8px;">30%</td><td style="padding:8px;">25-28%</td></tr>
                        <tr><td style="padding:8px;">Дивиденды (МТС, Лукойл)</td><td style="padding:8px;">50%</td><td style="padding:8px;">10-11%</td></tr>
                        <tr><td style="padding:8px;">Сбербанк/ВТБ</td><td style="padding:8px;">20%</td><td style="padding:8px;">Рост индекса до 3400 пкт</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="portfolio-item">
                <h3>💵 Портфель на 50 000 ₽</h3>
                <p style="color:var(--text-muted); margin-bottom:12px;">Полноценный диверсифицированный портфель с акциями, облигациями и ростом.</p>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">30% (15 000 ₽)</td><td style="padding:10px;">Облигации: ОФЗ (26230, 26233) + корп. (Гидромаш, РЕСО)</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">40% (20 000 ₽)</td><td style="padding:10px;">Дивиденды: Лукойл, МТС, Фосагро, Северсталь, Россети Ленэнерго</td></tr>
                    <tr style="border-bottom:1px solid var(--border);"><td style="padding:10px; font-weight:600;">20% (10 000 ₽)</td><td style="padding:10px;">Рост: Яндекс, Ozon, Т-Технологии</td></tr>
                    <tr><td style="padding:10px; font-weight:600;">10% (5 000 ₽)</td><td style="padding:10px;">Голубые фишки: Газпром, НОВАТЭК, Транснефть</td></tr>
                </table>
                <div class="instruction" style="margin-top:16px; padding:14px; font-size:14px;">
                    <table style="width:100%; border-collapse:collapse;">
                        <tr style="background:var(--card-bg);"><th style="padding:8px; text-align:left;">Актив</th><th style="padding:8px; text-align:left;">Пример распределения</th><th style="padding:8px; text-align:left;">Доходность/риск</th></tr>
                        <tr><td style="padding:8px;">Облигации</td><td style="padding:8px;">15 тыс. ₽ (ОФЗ + корп.)</td><td style="padding:8px;">Низкий, 20-25%</td></tr>
                        <tr><td style="padding:8px;">Дивиденды</td><td style="padding:8px;">20 тыс. ₽ (Лукойл и др.)</td><td style="padding:8px;">Средний, 10-12%</td></tr>
                        <tr><td style="padding:8px;">Рост (Яндекс)</td><td style="padding:8px;">10 тыс. ₽</td><td style="padding:8px;">Высокий</td></tr>
                        <tr><td style="padding:8px;">Фишки</td><td style="padding:8px;">5 тыс. ₽</td><td style="padding:8px;">Средний</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="instruction" style="margin-top:30px;">
                <h3 class="collapsible-header" onclick="this.classList.toggle('active'); this.nextElementSibling.classList.toggle('open');" style="color:#d32f2f;">
                    💰 Не подходит под ваш бюджет? Портфели для крупных капиталов
                </h3>
                <div class="collapsible-body">
                    <div class="portfolio-item" style="margin-top:16px;"><h3>💎 100 000 ₽</h3><p style="font-size:13px;">ОФЗ 40% + корп. облигации 25% + золото 15% + фишки 15% + рост 5%</p></div>
                    <div class="portfolio-item"><h3>💎 500 000 ₽</h3><p style="font-size:13px;">ОФЗ 35% + корп. облигации 25% + золото 15% + недвижимость 10% + фишки 10% + рост 5%</p></div>
                    <div class="portfolio-item"><h3>💎 1 000 000 ₽</h3><p style="font-size:13px;">ОФЗ 45% + корп. облигации 25% + золото 15% + фишки 10% + венчур 5%</p></div>
                    <div class="portfolio-item"><h3>💎 10 000 000 ₽</h3><p style="font-size:13px;">ОФЗ 50% + корп. облигации 25% + золото 15% + фишки 7% + ПИФы 3%</p></div>
                </div>
            </div>
            
            <p style="margin-top:20px; color:var(--text-muted); font-size:13px;">
                <i>Все портфели носят информационный характер и не являются инвестиционной рекомендацией.</i>
            </p>
        """
        return render_base(content, "Готовые портфели")

    @app.route('/lectures')
    @login_required
    def lectures():
        from frontend.templates import render_base
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        
        # Данные лекций с видео
        lectures_data = [
            {
                'id': 1,
                'title': 'Введение в площадку ПЛАКАТ',
                'description': 'Обзор сервиса, как пользоваться, что такое технический анализ.',
                'video_url': 'https://rutube.ru/video/76eddd1cbdd72ad63c2c43839cd3cd87/',
            },
            {
                'id': 2,
                'title': 'Работаем с площадкой ПЛАКАТ',
                'description': 'Создаем первые сигналы. Обзор интерфейса и функций.',
                'video_url': 'https://rutube.ru/video/d219c878b80487d6fdbd964d60c23dcd/',
            },
            {
                'id': 3,
                'title': 'Введение в акции и облигации',
                'description': 'Что такое акции и облигации, как на них зарабатывать, основные отличия.',
                'video_url': 'https://rutube.ru/video/227f979e33ec213c28e8b2d2a9e8c280/',
            },
            {
                'id': 4,
                'title': 'Введение в простой и сложный процент',
                'description': 'Как работает сложный процент, почему важно начинать инвестировать рано.',
                'video_url': 'https://rutube.ru/video/74c411c9e4b9389aafc19df76e6f66a7/',
            },
            {
                'id': 5,
                'title': '13 технических индикаторов ПЛАКАТ',
                'description': 'Какие индикаторы мы используем для анализа: RSI, MACD, SMA, Bollinger, Stochastic, CCI, ADX, ATR, EMA, SAR, OBV, Pivot, Ichimoku.',
                'video_url': 'https://rutube.ru/video/f4840a2f205eab126e8f4df718a6a4f7/',
            },
        ]
        
        # Генерируем HTML
        lectures_html = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(350px, 1fr)); gap:24px;">'
        
        for lec in lectures_data:
            # Получаем ID видео из URL Rutube
            video_id = ''
            if 'rutube.ru/video/' in lec['video_url']:
                video_id = lec['video_url'].split('/video/')[-1].split('/')[0].split('?')[0]
            
            embed_url = f'https://rutube.ru/embed/{video_id}/?autoplay=1' if video_id else ''
            
            # Используем загруженное превью
            thumbnail = f'/static/lectures/prev{lec["id"]}.jpg'
            
            lectures_html += f"""
                <div class="lecture-card" style="background:var(--card-bg); border:1px solid var(--border); border-radius:16px; overflow:hidden; transition:transform 0.2s, box-shadow 0.2s; cursor:pointer;" 
                     onclick="openVideoModal('{embed_url}', '{lec['title']}')">
                    <div style="position:relative;">
                        <img src="{thumbnail}" alt="{lec['title']}" style="width:100%; height:200px; object-fit:cover; background:#1a1a1a;" onerror="this.src='/static/logo.png'">
                        <span style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); background:rgba(0,0,0,0.7); border-radius:50%; width:50px; height:50px; display:flex; align-items:center; justify-content:center;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
                        </span>
                    </div>
                    <div style="padding:20px;">
                        <h3 style="margin:0 0 8px 0; font-size:18px;">{lec['title']}</h3>
                        <p style="color:var(--text-muted); font-size:14px; margin:0; line-height:1.5;">{lec['description']}</p>
                    </div>
                </div>
            """
        
        lectures_html += '</div>'
        
        # Модальное окно для видео
        modal_html = """
        <div id="videoModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:10000; justify-content:center; align-items:center;">
            <div style="position:relative; width:90%; max-width:1000px; background:var(--card-bg); border-radius:20px; overflow:hidden;">
                <div style="padding:20px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                    <h3 id="modalTitle" style="margin:0;">Видеоурок</h3>
                    <button onclick="closeVideoModal()" style="background:#d32f2f; color:white; border:none; border-radius:50%; width:36px; height:36px; font-size:20px; cursor:pointer; transition:0.2s;">&times;</button>
                </div>
                <div style="padding:20px;">
                    <div id="videoContainer" style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius:12px;">
                        <iframe id="videoIframe" style="position:absolute; top:0; left:0; width:100%; height:100%;" frameborder="0" allowfullscreen allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .lecture-card:hover {
                transform: translateY(-6px);
                box-shadow: 0 12px 24px rgba(0,0,0,0.15);
            }
        </style>
        
        <script>
        function openVideoModal(videoUrl, title) {
            if (!videoUrl) {
                alert('Видео временно недоступно');
                return;
            }
            document.getElementById('modalTitle').innerText = title;
            document.getElementById('videoIframe').src = videoUrl;
            document.getElementById('videoModal').style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
        
        function closeVideoModal() {
            document.getElementById('videoModal').style.display = 'none';
            document.getElementById('videoIframe').src = '';
            document.body.style.overflow = 'auto';
        }
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeVideoModal();
            }
        });
        
        document.getElementById('videoModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeVideoModal();
            }
        });
        </script>
        """
        
        content = f"""
            <h2>Лекторий ПЛАКАТ</h2>
            <p style="color:var(--text-muted); margin-bottom:30px; font-size:16px;">Видеоуроки по техническому анализу и работе с платформой</p>
            
            {lectures_html}
            
            {modal_html}
        """
        return render_base(content, "Лекторий")

    @app.route('/team')
    def team():
        from frontend.templates import render_base
        content = """
            <h2>О проекте</h2>
            
            <div style="display:flex; gap:40px; flex-wrap:wrap; margin-top:20px;">
                <div style="flex:1; min-width:300px;">
                    <div class="portfolio-item" style="display:flex; align-items:flex-start; gap:16px;">
                        <img src="/static/yaroslav.jpg" alt="Ярослав" style="width:100px; height:100px; border-radius:50%; object-fit:cover; border:3px solid #d32f2f; flex-shrink:0;">
                        <div>
                            <h3>Ярослав Славутский</h3>
                            <p style="color:#888; margin-bottom:4px;">Бизнес-аналитик / Project Manager</p>
                            <p style="font-size:13px;">АНО «Школа 21», DevFest.ru. С 14 лет в инвестициях. Разогнал депозит с 50 000 ₽ до 470 000 ₽.</p>
                        </div>
                    </div>
                    <div class="portfolio-item" style="display:flex; align-items:flex-start; gap:16px; margin-top:12px;">
                        <img src="/static/nikita.jpg" alt="Никита" style="width:100px; height:100px; border-radius:50%; object-fit:cover; border:3px solid #d32f2f; flex-shrink:0;">
                        <div>
                            <h3>Никита Стоян</h3>
                            <p style="color:#888; margin-bottom:4px;">Дизайнер / Видеомонтажёр / SMM</p>
                            <p style="font-size:13px;">6 лет в дизайне и монтаже. Ведёт соцсети «ПЛАКАТ». С 15 лет в акциях и крипте.</p>
                        </div>
                    </div>
                </div>
                
                <div style="flex:2; min-width:300px;">
                    <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #d32f2f; border-radius:12px; padding:24px; margin-bottom:16px;">
                        <h3 style="color:#d32f2f;">Для чего создан ПЛАКАТ</h3>
                        <p style="line-height:1.7;">Мы хотим, чтобы каждый частный инвестор мог принимать решения на основе данных, а не эмоций. ПЛАКАТ — это 13 индикаторов, которые за 2 секунды дают готовую торговую идею с уровнями входа и выхода.</p>
                    </div>
                    
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center;">
                            <p style="font-size:28px; font-weight:800; color:#d32f2f; margin:0;">2 сек</p>
                            <p style="font-size:13px; color:var(--text-muted); margin:4px 0 0;">скорость анализа</p>
                        </div>
                        <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center;">
                            <p style="font-size:28px; font-weight:800; color:#d32f2f; margin:0;">13</p>
                            <p style="font-size:13px; color:var(--text-muted); margin:4px 0 0;">индикаторов</p>
                        </div>
                        <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center;">
                            <p style="font-size:28px; font-weight:800; color:#d32f2f; margin:0;">299 ₽</p>
                            <p style="font-size:13px; color:var(--text-muted); margin:4px 0 0;">в месяц</p>
                        </div>
                        <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center;">
                            <p style="font-size:28px; font-weight:800; color:#d32f2f; margin:0;">73%</p>
                            <p style="font-size:13px; color:var(--text-muted); margin:4px 0 0;">точность TP</p>
                        </div>
                    </div>
                    
                    <p style="margin-top:16px; font-size:14px; color:var(--text-muted); line-height:1.6;">
                        <b>ПЛАКАТ</b> — это не инвестиционная рекомендация. Это математика, которая помогает вам принимать решения. Мы не управляем вашими деньгами, мы даём вам данные.
                    </p>
                </div>
            </div>
            
            <h2 style="margin-top:40px;">С ПЛАКАТ вы</h2>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:16px;">
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Получать готовые торговые идеи за 2 секунды</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Тратить часы на ручной анализ графиков</p>
                </div>
                
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Использовать 13 индикаторов одновременно</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Гадать на кофейной гуще</p>
                </div>
                
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Знать точные уровни входа и выхода в рублях</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Терять деньги без стоп-лосса</p>
                </div>
                
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Платить 299 ₽/мес вместо 3000+</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Переплачивать за сложные терминалы</p>
                </div>
                
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Скачивать PDF-отчёт после каждого анализа</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Держать всё в голове</p>
                </div>
                
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #2e7d32; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#2e7d32; font-weight:700; font-size:16px; margin-bottom:6px;">✅ Быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Инвестировать с уверенностью на основе данных</p>
                </div>
                <div style="background:var(--card-bg); border:1px solid var(--border); border-left:6px solid #c62828; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <p style="color:#c62828; font-weight:700; font-size:16px; margin-bottom:6px;">❌ Не быть</p>
                    <p style="color:var(--text); margin:0; line-height:1.5;">Поддаваться эмоциям и панике</p>
                </div>
            </div>
            <p style="margin-top:30px; text-align:center; font-size:18px; font-weight:600; color:#d32f2f;">ПЛАКАТ — ваш инструмент для уверенных решений на бирже.</p>
        """
        return render_base(content, "О проекте")

    @app.route('/news')
    def news():
        from frontend.templates import render_base
        all_news = News.query.order_by(News.created_at.desc()).all()
        news_html = ""
        for n in all_news:
            news_html += f"""
                <div class="result-block" style="margin-bottom:16px;">
                    <h3>{n.title}</h3>
                    <p style="color:var(--text-muted); font-size:13px;">{n.created_at.strftime('%d.%m.%Y %H:%M')}</p>
                    <p>{n.content}</p>
                </div>
            """
        if not news_html:
            news_html = "<p>Новостей пока нет.</p>"
        return render_base(f"<h2>Новости</h2>{news_html}", "Новости")

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        from frontend.templates import BASE_CSS, UPLOAD_HTML
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        
        msg = ""
        if request.method == 'POST':
            file = request.files.get('file')
            if not file:
                msg = '<div class="error">Файл не выбран</div>'
            else:
                try:
                    content = file.read().decode('utf-8')
                    sample = content[:1024]
                    dialect = csv.Sniffer().sniff(sample)
                    has_header = csv.Sniffer().has_header(sample)
                    if not has_header:
                        msg = '<div class="error">Файл должен содержать заголовок</div>'
                        return UPLOAD_HTML.replace('{style}', BASE_CSS).replace('{msg}', msg)
                    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
                    fieldnames = reader.fieldnames
                    finam_fields = {'<TICKER>', '<PER>', '<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<VOL>'}
                    if finam_fields.issubset(set(fieldnames)):
                        df = pd.read_csv(io.StringIO(content), usecols=finam_fields, dtype=str)
                        df['datetime'] = pd.to_datetime(df['<DATE>'] + df['<TIME>'], format='%Y%m%d%H%M%S')
                        ticker = df['<TICKER>'].iloc[0].strip().upper()
                        with app.app_context():
                            security = Security.query.filter_by(ticker=ticker).first()
                            if not security:
                                security = Security(ticker=ticker, name=ticker)
                                db.session.add(security)
                            count = 0
                            for _, row in df.iterrows():
                                date_val = pd.to_datetime(row['datetime'])
                                exists = Candle.query.filter_by(security_id=security.id, date=date_val).first()
                                if not exists:
                                    try: vol = int(float(row['<VOL>']))
                                    except: vol = 0
                                    candle = Candle(security_id=security.id, date=date_val, open=float(row['<OPEN>']),
                                                    high=float(row['<HIGH>']), low=float(row['<LOW>']),
                                                    close=float(row['<CLOSE>']), volume=vol)
                                    db.session.add(candle)
                                    count += 1
                            db.session.commit()
                        msg = f'<div style="color:green;">Загружено {count} свечей для {ticker}</div>'
                    else:
                        reader = csv.DictReader(io.StringIO(content))
                        count = 0
                        for row in reader:
                            ticker = row['ticker'].upper().strip()
                            date_val = pd.to_datetime(row['date']).date()
                            security = Security.query.filter_by(ticker=ticker).first()
                            if not security:
                                security = Security(ticker=ticker, name=ticker)
                                db.session.add(security)
                            exists = Candle.query.filter_by(security_id=security.id, date=date_val).first()
                            if not exists:
                                candle = Candle(security_id=security.id, date=date_val, open=float(row['open']),
                                                high=float(row['high']), low=float(row['low']),
                                                close=float(row['close']), volume=int(float(row['volume'])))
                                db.session.add(candle)
                                count += 1
                        db.session.commit()
                        msg = f'<div style="color:green;">Загружено {count} свечей</div>'
                except Exception as e:
                    db.session.rollback()
                    msg = f'<div class="error">Ошибка: {str(e)}</div>'
        return UPLOAD_HTML.replace('{style}', BASE_CSS).replace('{msg}', msg)

    @app.route('/clear-data/<ticker>')
    @login_required
    def clear_ticker_data(ticker):
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        security = Security.query.filter_by(ticker=ticker.upper()).first()
        if security:
            Candle.query.filter_by(security_id=security.id).delete()
            db.session.commit()
        return redirect(url_for('upload'))

    @app.route('/clear-data', methods=['POST'])
    @login_required
    def clear_all_data():
        from frontend.templates import BASE_CSS, UPLOAD_HTML
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        try:
            Candle.query.delete()
            db.session.commit()
            msg = '<div style="color:#2e7d32; font-weight:bold;">✅ Все данные успешно удалены</div>'
        except Exception as e:
            db.session.rollback()
            msg = f'<div class="error">Ошибка: {str(e)}</div>'
        return render_template_string(UPLOAD_HTML.replace('{style}', BASE_CSS).replace('{msg}', msg))

    @app.route('/api/activate-sub', methods=['POST'])
    def activate_sub():
        if not request.is_json:
            return jsonify({"success": False, "message": "Только JSON"}), 400
        data = request.get_json()
        user_id = data.get('user_id')
        secret = data.get('secret')
        if secret != app.config['SECRET_KEY']:
            return jsonify({"success": False, "message": "Неверный secret"}), 403
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 404
        today = date.today()
        end_date = today + timedelta(days=30)
        Subscription.query.filter_by(user_id=user.id, is_active=True).update({"is_active": False})
        sub = Subscription(user_id=user.id, start_date=today, end_date=end_date, is_active=True)
        db.session.add(sub)
        db.session.commit()
        return jsonify({"success": True, "message": f"Подписка активирована до {end_date}"})

    @app.route('/api/add-news', methods=['POST'])
    def add_news():
        if not request.is_json:
            return jsonify({"success": False}), 400
        data = request.get_json()
        secret = data.get('secret')
        if secret != app.config['SECRET_KEY']:
            return jsonify({"success": False}), 403
        title = data.get('title', 'Новость')
        content = data.get('content', '')
        news_entry = News(title=title, content=content)
        db.session.add(news_entry)
        db.session.commit()
        return jsonify({"success": True})

    @app.route('/api/block-user', methods=['POST'])
    def api_block_user():
        if not request.is_json:
            return jsonify({"success": False}), 400
        data = request.get_json()
        secret = data.get('secret')
        if secret != app.config['SECRET_KEY']:
            return jsonify({"success": False}), 403
        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 404
        user.is_blocked = True
        db.session.commit()
        return jsonify({"success": True, "message": f"Пользователь {user.email} заблокирован"})

    @app.route('/oferta')
    def oferta():
        with open('legal/oferta.html', 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/privacy')
    def privacy():
        with open('legal/privacy.html', 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/data-processing')
    def data_processing():
        with open('legal/data-processing.html', 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/about')
    def about():
        with open('legal/about.html', 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/faq')
    def faq():
        with open('legal/faq.html', 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/dividends')
    @login_required
    def dividends():
        from frontend.templates import render_base
        from engine.dividends import get_dividend_calendar
        
        tickers = ['SBER', 'GAZP', 'LKOH', 'GMKN', 'NVTK', 'ROSN', 'VTBR', 'CHMF', 'AFLT', 'MGNT', 'PLZL', 'TATN', 'SNGS', 'ALRS', 'MTSS']
        calendar = get_dividend_calendar(tickers)
        
        if not calendar:
            return render_base("<h2>📅 Календарь дивидендов</h2><p>Данные временно недоступны. Попробуйте позже.</p>", "Дивиденды")
        
        rows = ""
        for d in calendar[:30]:
            rows += f"""
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:10px;">{d['ticker']}</td>
                    <td style="padding:10px;">{d['date']}</td>
                    <td style="padding:10px;">{d['value']} {d['currency']}</td>
                </tr>
            """
        
        content = f"""
            <h2>📅 Календарь дивидендов</h2>
            <p style="color:var(--text-muted); margin-bottom:20px;">Даты закрытия реестра и размер выплат по акциям Мосбиржи.</p>
            <table style="width:100%; border-collapse:collapse;">
                <tr style="background:var(--card-bg); font-weight:600;">
                    <td style="padding:10px;">Тикер</td>
                    <td style="padding:10px;">Дата реестра</td>
                    <td style="padding:10px;">Размер</td>
                </tr>
                {rows}
            </table>
            <p style="margin-top:20px; color:var(--text-muted); font-size:13px;">Данные с MOEX ISS API. Обновляются автоматически.</p>
        """
        return render_base(content, "Дивиденды")

    @app.route('/api/dividends-widget')
    def dividends_widget():
        from engine.dividends import get_dividend_calendar
        tickers = ['SBER', 'GAZP', 'LKOH', 'GMKN', 'NVTK', 'ROSN', 'VTBR', 'CHMF', 'AFLT', 'MGNT', 'PLZL', 'TATN', 'SNGS', 'ALRS', 'MTSS']
        calendar = get_dividend_calendar(tickers)
        return jsonify(calendar[:15])

    @app.route('/api/recent-signals')
    @login_required
    def recent_signals():
        from models import SignalHistory
        signals = SignalHistory.query.filter_by(user_id=current_user.id).order_by(SignalHistory.created_at.desc()).limit(5).all()
        
        result = []
        for s in signals:
            result.append({
                'ticker': s.ticker,
                'direction': s.direction,
                'price': s.price,
                'take_profit': s.take_profit,
                'stop_loss': s.stop_loss,
                'created_at': s.created_at.strftime('%d.%m.%Y %H:%M')
            })
        return jsonify(result)

    @app.route('/history')
    @login_required
    def history():
        from frontend.templates import render_base
        from models import SignalHistory
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        
        signals = SignalHistory.query.filter_by(user_id=current_user.id).order_by(SignalHistory.created_at.desc()).all()
        
        rows = ""
        for s in signals:
            direction_color = '#2e7d32' if s.direction == 'ПОКУПКА' else '#c62828' if s.direction == 'ПРОДАЖА' else '#888'
            rows += f"""
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:10px;"><b>{s.ticker}</b></td>
                    <td style="padding:10px; color:{direction_color};">{s.direction}</td>
                    <td style="padding:10px;">{s.price} ₽</td>
                    <td style="padding:10px;">{s.take_profit if s.take_profit else '—'}</td>
                    <td style="padding:10px;">{s.stop_loss if s.stop_loss else '—'}</td>
                    <td style="padding:10px; font-size:12px;">{s.created_at.strftime('%d.%m.%Y %H:%M')}</td>
                </tr>
            """
        
        if not rows:
            rows = '<tr><td colspan="6" style="padding:40px; text-align:center;">📭 Пока нет сигналов. Проведите анализ акции. NSFNonmenth'
        
        content = f"""
            <h2>История сигналов</h2>
            <p style="color:var(--text-muted); margin-bottom:20px;">Все ваши торговые идеи в одном месте.</p>
            
            <div style="overflow-x: auto;">
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:var(--card-bg); border-bottom:2px solid #d32f2f;">
                            <th style="padding:12px; text-align:left;">Тикер</th>
                            <th style="padding:12px; text-align:left;">Сигнал</th>
                            <th style="padding:12px; text-align:left;">Цена</th>
                            <th style="padding:12px; text-align:left;">TP</th>
                            <th style="padding:12px; text-align:left;">SL</th>
                            <th style="padding:12px; text-align:left;">Время</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
            
            <p style="margin-top:20px; color:var(--text-muted); font-size:13px;">
                <i>Сохраняются последние 100 сигналов. Не является инвестиционной рекомендацией.</i>
            </p>
        """
        return render_base(content, "История сигналов")
    
    @app.route('/download-pdf/<ticker>')
    @login_required
    def download_pdf(ticker):
        if not has_active_subscription():
            return redirect(url_for('subscribe'))
        interval = getattr(current_user, 'analysis_interval', 'D')
        df = get_data_from_db(ticker, interval)
        if df is None:
            return "Нет данных для PDF", 404
        result = generate_idea(df, ticker, interval)
        plot_img = create_plot(df, result)
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
        pdf.set_font("DejaVu", "B", 22)
        pdf.set_text_color(211, 47, 47)
        pdf.cell(0, 15, f"ПЛАКАТ — {ticker}", ln=True, align="C")
        pdf.set_font("DejaVu", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "Читай плакат — получай торговую идею", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("DejaVu", "B", 14)
        pdf.set_text_color(33, 33, 33)
        pdf.cell(0, 10, f"Торговая идея: {result['direction']}", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 8, f"Цена закрытия: {result['last_price']} ₽", ln=True)
        pdf.cell(0, 8, f"RSI(14): {result['rsi']}   |   Stochastic K/D: {result['stoch_k']}/{result['stoch_d']}", ln=True)
        pdf.cell(0, 8, f"MACD: {result['macd']} / Сигнал {result['macd_signal']}", ln=True)
        pdf.cell(0, 8, f"Bollinger: {result['bb_lower']} — {result['bb_upper']}", ln=True)
        pdf.cell(0, 8, f"CCI(20): {result['cci']}   |   ADX(14): {result['adx']}", ln=True)
        pdf.cell(0, 8, f"Объём (отн. среднего): {result['volume_ratio']}x", ln=True)
        pdf.cell(0, 8, f"ATR(14): {result['atr']} ₽", ln=True)
        pdf.ln(10)
        if result['take_profit']:
            pdf.set_fill_color(232, 245, 233)
            pdf.set_text_color(46, 125, 50)
            pdf.cell(0, 8, f"Take Profit: {result['take_profit']} ₽", ln=True, fill=True)
        if result['stop_loss']:
            pdf.set_fill_color(255, 235, 238)
            pdf.set_text_color(198, 40, 40)
            pdf.cell(0, 8, f"Stop Loss: {result['stop_loss']} ₽", ln=True, fill=True)
        pdf.ln(10)
        img_data = base64.b64decode(plot_img.split(',')[1])
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name
        pdf.image(tmp_path, x=15, w=180)
        os.unlink(tmp_path)
        pdf.ln(10)
        pdf.set_font("DejaVu", "I", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.multi_cell(0, 5, "Дисклеймер: Это не инвестиционная рекомендация. Данный отчёт сгенерирован автоматически сервисом ПЛАКАТ. Все торговые решения пользователь принимает самостоятельно на свой страх и риск.")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf.output(tmp.name)
            tmp_path = tmp.name
        with open(tmp_path, 'rb') as f:
            pdf_content = f.read()
        os.unlink(tmp_path)
        return send_file(io.BytesIO(pdf_content), mimetype='application/pdf', as_attachment=True, download_name=f'PLAKAT_{ticker}.pdf')


def get_data_from_db(ticker, interval='D'):
    security = Security.query.filter_by(ticker=ticker.upper()).first()
    if not security:
        return None
    candles = Candle.query.filter_by(security_id=security.id).order_by(Candle.date.asc()).all()
    if len(candles) < 30:
        return None
    data = [{'date': c.date, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'volume': c.volume} for c in candles]
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index)
    has_time = any(d.time() != pd.Timestamp('00:00:00').time() for d in df.index)
    if interval == 'D' and has_time:
        df = df.resample('D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    if len(df) < 10:
        return None
    return df[['open', 'high', 'low', 'close', 'volume']]