# frontend/templates.py
from flask_login import current_user

BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Russo+One&family=Inter:wght@400;500;600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
        --bg: #fafafa; --card-bg: #ffffff; --text: #1a1a1a;
        --text-secondary: #555; --text-muted: #888;
        --border: #f0f0f0; --input-border: #e0e0e0;
        --header-bg: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
        --footer-bg: #ffffff;
    }
    body.dark {
        --bg: #0c0c0c; --card-bg: #1a1a1a; --text: #e0e0e0;
        --text-secondary: #aaa; --text-muted: #777;
        --border: #2a2a2a; --input-border: #3a3a3a;
        --header-bg: linear-gradient(135deg, #1a1a1a 0%, #0c0c0c 100%);
        --footer-bg: #0c0c0c;
    }
    body {
        background: var(--bg); font-family: 'Inter', sans-serif;
        display: flex; flex-direction: column; min-height: 100vh;
        color: var(--text); line-height: 1.6;
        cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><circle cx='10' cy='10' r='8' fill='none' stroke='%23d32f2f' stroke-width='2'/></svg>") 10 10, auto;
    }
    a, button, input, .btn, .collapsible-header {
        cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><circle cx='10' cy='10' r='8' fill='%23d32f2f' stroke='%23d32f2f' stroke-width='2'/></svg>") 10 10, pointer;
    }
    .header { background: var(--header-bg); padding: 14px 40px; text-align: center; border-bottom: 1px solid #c62828; }
    .header h1 { font-family: 'Russo One', sans-serif; font-size: 42px; letter-spacing: 6px; color: #fff; text-transform: uppercase; margin: 0; }
    .header p { font-size: 14px; color: rgba(255,255,255,0.9); margin-top: 4px; font-weight: 500; }
    .logo { max-height: 70px; margin-bottom: 8px; }
    .nav { background: var(--card-bg); display: flex; justify-content: center; flex-wrap: wrap; border-bottom: 1px solid var(--border); padding: 0 20px; }
    .nav a { font-family: 'Inter', sans-serif; font-weight: 500; color: var(--text-secondary); text-decoration: none; padding: 16px 24px; font-size: 15px; border-bottom: 2px solid transparent; transition: all 0.2s; }
    .nav a:hover { color: #fff; background: #d32f2f; border-bottom-color: #d32f2f; border-radius: 4px 4px 0 0; }
    .content { flex: 1; max-width: 1200px; width: 100%; margin: 40px auto; padding: 40px; background: var(--card-bg); border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
    .footer { background: var(--footer-bg); border-top: 3px solid #d32f2f; text-align: center; padding: 24px 40px; font-size: 13px; color: var(--text-muted); }
    .footer a { color: #d32f2f; text-decoration: none; }
    h2 { font-weight: 700; color: var(--text); font-size: 30px; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 3px solid #d32f2f; display: inline-block; }
    h3 { font-weight: 600; font-size: 18px; color: var(--text); margin-bottom: 8px; }
    .btn { background: #d32f2f; color: #fff; border: 2px solid #d32f2f; padding: 12px 28px; font-weight: 600; font-size: 15px; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; transition: all 0.2s; }
    .btn:hover { background: #b71c1c; border-color: #b71c1c; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(211,47,47,0.3); }
    .btn-loading { pointer-events: none; opacity: 0.7; position: relative; }
    .btn-loading:after { content: ""; display: inline-block; width: 16px; height: 16px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; margin-left: 8px; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .btn-outline { background: transparent; border: 1px solid #d32f2f; color: #d32f2f; }
    .btn-outline:hover { background: #d32f2f; color: #fff; }
    input[type="text"], input[type="email"], input[type="password"] { background: var(--card-bg); border: 1px solid var(--input-border); border-radius: 8px; padding: 12px 16px; font-size: 15px; width: 100%; max-width: 360px; color: var(--text); transition: border-color 0.2s; }
    input:focus { outline: none; border-color: #d32f2f; box-shadow: 0 0 0 3px rgba(211,47,47,0.1); }
    .result-block { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin-top: 24px; animation: fadeInUp 0.5s ease both; }
    .green { color: #2e7d32; font-weight: 600; background: #e8f5e9; padding: 4px 12px; border-radius: 6px; }
    .red { color: #c62828; font-weight: 600; background: #ffebee; padding: 4px 12px; border-radius: 6px; }
    .error { color: #d32f2f; background: #fef0f0; border: 1px solid #ffcdd2; border-radius: 8px; padding: 16px; margin: 16px 0; }
    .portfolio-item, .lecture-item { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin: 12px 0; animation: fadeInUp 0.4s ease both; }
    .portfolio-item:nth-child(1) { animation-delay: 0.05s; }
    .portfolio-item:nth-child(2) { animation-delay: 0.1s; }
    .portfolio-item:nth-child(3) { animation-delay: 0.15s; }
    .portfolio-item:nth-child(4) { animation-delay: 0.2s; }
    .instruction { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-top: 30px; font-size: 15px; animation: fadeInUp 0.5s ease 0.1s both; }
    .instruction h3 { color: #d32f2f; margin-bottom: 12px; }
    .collapsible-header { cursor: pointer; user-select: none; display: flex; justify-content: space-between; align-items: center; }
    .collapsible-header:after { content: "\\25BC"; font-size: 18px; color: #d32f2f; font-weight: bold; margin-left: 12px; transition: transform 0.3s; }
    .collapsible-header.active:after { transform: rotate(180deg); }
    .collapsible-body { max-height: 0; overflow: hidden; transition: max-height 0.3s; }
    .collapsible-body.open { max-height: 2000px; }
    .plot-image { display: block; margin: 24px auto 0; max-width: 100%; border-radius: 8px; border: 1px solid var(--border); animation: fadeInUp 0.5s ease 0.3s both; }
    .skeleton { background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 12px; min-height: 300px; margin: 24px 0; }
    body.dark .skeleton { background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%); background-size: 200% 100%; }
    @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    .ai-comment { background: var(--card-bg); border: 1px solid var(--border); border-left: 4px solid #f39c12; border-radius: 12px; padding: 16px; margin-top: 16px; animation: fadeInUp 0.5s ease 0.5s both; }
    .ai-comment-label { color: #f39c12; font-size: 13px; margin-bottom: 4px; font-weight: 600; }
    /* Туториал */
    .tutorial-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; justify-content: center; align-items: center; }
    .tutorial-card { background: var(--card-bg); border: 3px solid #d32f2f; border-radius: 16px; padding: 30px; max-width: 400px; text-align: center; color: var(--text); box-shadow: 0 10px 40px rgba(0,0,0,0.3); animation: fadeInUp 0.4s ease; }
    .tutorial-card h3 { color: #d32f2f; font-size: 22px; margin-bottom: 12px; }
    .tutorial-card p { font-size: 15px; line-height: 1.6; margin-bottom: 20px; color: var(--text-muted); }
    .tutorial-step { display: flex; justify-content: center; gap: 8px; margin-top: 16px; }
    .tutorial-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--border); }
    .tutorial-dot.active { background: #d32f2f; }
    
    /* Адаптация под телефоны и планшеты */
    @media (max-width: 768px) {
        .header { padding: 12px 20px; }
        .header h1 { font-size: 28px; letter-spacing: 3px; }
        .logo { max-height: 45px; }
        .nav a { padding: 10px 14px; font-size: 13px; }
        .content { margin: 16px 12px; padding: 20px; }
        h2 { font-size: 22px; margin-bottom: 16px; }
        .btn, .btn-outline { padding: 8px 18px; font-size: 13px; }
        .result-block { padding: 16px; margin-top: 16px; }
        .portfolio-item, .lecture-item { padding: 14px 16px; }
        .instruction { padding: 16px; margin-top: 20px; font-size: 14px; }
        input[type="text"], input[type="email"], input[type="password"] { max-width: 100%; padding: 10px 14px; }
        .footer { padding: 16px 20px; font-size: 11px; }
        .footer p { margin: 4px 0; }
        .collapsible-header:after { font-size: 14px; }
    }
    
    @media (max-width: 480px) {
        .header h1 { font-size: 22px; letter-spacing: 2px; }
        .nav a { padding: 8px 10px; font-size: 11px; }
        .content { margin: 10px 8px; padding: 14px; }
        h2 { font-size: 18px; }
        h3 { font-size: 15px; }
        .btn, .btn-outline { padding: 6px 14px; font-size: 12px; }
        .result-block { padding: 12px; }
        .result-block p { font-size: 13px; }
        .green, .red { font-size: 11px; padding: 2px 8px; }
        .portfolio-item, .lecture-item { padding: 10px 12px; }
        .instruction { padding: 12px; font-size: 13px; }
        .tutorial-card { padding: 20px; max-width: 90%; }
        .tutorial-card h3 { font-size: 18px; }
        .tutorial-card p { font-size: 13px; }
    }
</style>
"""

BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<script>
function toggleTheme() {
    document.body.classList.toggle('dark');
    var isDark = document.body.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.cookie = 'theme=' + (isDark ? 'dark' : 'light') + '; path=/; max-age=31536000';
    var btn = document.getElementById('themeBtn');
    if (btn) btn.innerHTML = isDark ? '☀️ Светлая тема' : '🌙 Тёмная тема';
}
document.addEventListener('DOMContentLoaded', function() {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark') document.body.classList.add('dark');
    else if (!saved) localStorage.setItem('theme', 'light');
    document.cookie = 'theme=' + (document.body.classList.contains('dark') ? 'dark' : 'light') + '; path=/; max-age=31536000';
    var btn = document.getElementById('themeBtn');
    if (btn) btn.innerHTML = document.body.classList.contains('dark') ? '☀️ Светлая тема' : '🌙 Тёмная тема';
});
document.addEventListener('submit', function(e) {
    var form = e.target.closest('form');
    if (form && form.action.endsWith('/analyze')) {
        var btn = form.querySelector('button[type="submit"]');
        if (btn) { btn.classList.add('btn-loading'); btn.textContent = 'Анализируем...'; }
    }
});
</script>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <link rel="icon" type="image/png" href="/static/logo.png">
    <meta name="description" content="ПЛАКАТ — сервис технического анализа акций Московской биржи. 13 индикаторов, торговые идеи, тейк-профит и стоп-лосс за 2 секунды.">
    <title>ПЛАКАТ | Теханализ Мосбиржи</title>
    {style}
</head>
<body>
   <div class="header">
    <img src="/static/logo.png" alt="ПЛАКАТ" class="logo">
    <p>Читай плакат — получай торговую идею</p>
</div>
    <div class="nav">
        <a href="/">📈 Анализ</a>
        <a href="/portfolios">💼 Портфели</a>
        <a href="/lectures">📚 Лекторий</a>
        <a href="/team">🚀 О проекте</a>
        <a href="/news">📰 Новости</a>
        {auth_link}
    </div>
    <div id="tutorialOverlay" class="tutorial-overlay" style="display:none;">
        <div class="tutorial-card" id="tutorialCard">
            <h3 id="tutorialTitle">Добро пожаловать в ПЛАКАТ!</h3>
            <p id="tutorialText">Загрузите CSV-файл с котировками и получайте торговые идеи за 2 секунды.</p>
            <button class="btn" id="tutorialNext">Далее</button>
            <div class="tutorial-step" id="tutorialDots">
                <span class="tutorial-dot active"></span>
                <span class="tutorial-dot"></span>
                <span class="tutorial-dot"></span>
            </div>
        </div>
    </div>
    <div class="content">{content}</div>
    <div class="footer">
        <p><strong>ПЛАКАТ</strong> — сервис анализа акций Московской биржи.</p>
        <p>📧 plakat_invest@mail.ru | 📱 +7 (962) 050 40 40</p>
        <p>
        <a href="/about">📖 О продукте</a> |
        <a href="/oferta">📜 Публичная оферта</a> |
        <a href="/privacy">🔒 Конфиденциальность</a> |
        <a href="/data-processing">📋 Обработка данных</a> |
        <a href="/faq">❓ ЧАВО</a>
        </p>
        <p style="margin-top:8px;">Дисклеймер: не является инвестиционной рекомендацией.</p>
    </div>
    <audio id="ding-sound" src="/static/ding.wav" preload="auto"></audio>
</body>
</html>
"""

UPLOAD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Загрузка котировок</title>
    {style}
</head>
<script>
function toggleTheme() { document.body.classList.toggle('dark'); localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light'); }
document.addEventListener('DOMContentLoaded', function() {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark') document.body.classList.add('dark');
    document.cookie = 'theme=' + (document.body.classList.contains('dark') ? 'dark' : 'light') + '; path=/; max-age=31536000';
});
</script>
<body>
    <div class="header">
        <h1>Загрузка данных</h1>
        <button onclick="toggleTheme()" id="themeBtn" class="btn-outline" style="position: absolute; right: 20px; top: 20px;">🌙 Тёмная тема</button>
    </div>
    <div class="nav">
    <a href="/analyze">← Назад к анализу</a>
    <a href="/history">История</a>
    </div>
    </div>
    <div class="content">
        <h2>📤 Загрузить CSV с котировками</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".csv" required style="margin-bottom:12px;">
            <button type="submit" class="btn">Загрузить</button>
        </form>
        <p style="margin-top:20px; font-size:14px; color:#888;">Формат: ticker,date,open,high,low,close,volume<br>
        Или файл Финам: &lt;TICKER&gt;,&lt;PER&gt;,&lt;DATE&gt;,&lt;TIME&gt;,&lt;OPEN&gt;,&lt;HIGH&gt;,&lt;LOW&gt;,&lt;CLOSE&gt;,&lt;VOL&gt;</p>
        {msg}
        <hr style="margin:30px 0; border:1px solid #f0f0f0;">
        <h3>🗑️ Очистить все данные</h3>
        <form method="post" action="/clear-data" onsubmit="return confirm('Точно удалить ВСЕ котировки?');">
            <button type="submit" class="btn" style="background:#c62828; border-color:#c62828;">🗑️ Очистить</button>
        </form>
    </div>
</body>
</html>
"""

def render_base(content, title="Главная"):
    auth_link = '<a href="/profile">👤 Профиль</a>' if current_user.is_authenticated else '<a href="/login">🔐 Войти</a>'
    return BASE_TEMPLATE.replace('{style}', BASE_CSS).replace('{content}', content).replace('{title}', title).replace('{auth_link}', auth_link)