# engine/moex_api.py
import requests
import pandas as pd
from datetime import datetime, timedelta

def get_moex_candles(ticker, interval='day', days=90):
    """
    Загружает свечи с MOEX ISS API (бесплатно, задержка 15 минут)
    ticker: SBER, GAZP, LKOH и т.д.
    interval: 'day', 'hour', 'minute'
    days: количество дней истории
    """
    
    # Интервалы MOEX
    interval_map = {
        'day': 24,
        'hour': 60,
        'minute': 1
    }
    
    engine = 'stock'
    market = 'shares'
    
    url = f"https://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{ticker}/candles.json"
    
    params = {
        'interval': interval_map.get(interval, 24),
        'from': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
        'till': datetime.now().strftime('%Y-%m-%d')
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        candles_data = data['candles']['data']
        columns = data['candles']['columns']
        
        df = pd.DataFrame(candles_data, columns=columns)
        
        # Переименовываем колонки под наш стандарт
        df = df.rename(columns={
            'begin': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('date')
        
        return df
        
    except Exception as e:
        print(f"MOEX API error: {e}")
        return None


def get_available_tickers():
    """Получает список всех тикеров Мосбиржи"""
    url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/tqbr/securities.json"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        securities = data['securities']['data']
        columns = data['securities']['columns']
        
        tickers = []
        for row in securities:
            ticker = row[columns.index('SECID')]
            name = row[columns.index('SHORTNAME')] if 'SHORTNAME' in columns else ticker
            tickers.append({'ticker': ticker, 'name': name})
        
        return tickers[:50]  # первые 50 для старта
        
    except:
        # fallback на популярные
        return [
            {'ticker': 'SBER', 'name': 'Сбербанк'},
            {'ticker': 'GAZP', 'name': 'Газпром'},
            {'ticker': 'LKOH', 'name': 'Лукойл'},
            {'ticker': 'ROSN', 'name': 'Роснефть'},
            {'ticker': 'NVTK', 'name': 'НОВАТЭК'},
            {'ticker': 'GMKN', 'name': 'Норникель'},
            {'ticker': 'VTBR', 'name': 'ВТБ'},
            {'ticker': 'CHMF', 'name': 'Северсталь'},
            {'ticker': 'AFLT', 'name': 'Аэрофлот'},
            {'ticker': 'MGNT', 'name': 'Магнит'},
            {'ticker': 'YNDX', 'name': 'Яндекс'},
            {'ticker': 'OZON', 'name': 'OZON'},
            {'ticker': 'TCSG', 'name': 'Т-Технологии'},
            {'ticker': 'POSI', 'name': 'Positive Technologies'},
            {'ticker': 'PHOR', 'name': 'Фосагро'},
            {'ticker': 'RUAL', 'name': 'Русал'},
            {'ticker': 'IRAO', 'name': 'Инарктика'},
            {'ticker': 'HYDR', 'name': 'РусГидро'},
            {'ticker': 'PIKK', 'name': 'ПИК'},
            {'ticker': 'VKCO', 'name': 'VK'}
        ]