# engine/idea.py
import pandas as pd
import numpy as np
from .indicators import *

def generate_idea(df, ticker, interval='D'):
    close = df['close']
    last_price = close.iloc[-1]

    if interval == 'H':
        rsi_period, sma_period, ema_period = 9, 20, 9
        bb_period, stoch_period, adx_period = 10, 9, 10
        atr_mult_tp, atr_mult_sl = 1.5, 1.0
        volume_period = 10
        score_buy, score_sell = 1, -1
    else:
        rsi_period, sma_period, ema_period = 14, 50, 20
        bb_period, stoch_period, adx_period = 20, 14, 14
        atr_mult_tp, atr_mult_sl = 2.5, 1.5
        volume_period = 20
        score_buy, score_sell = 1, -1

    rsi = compute_rsi(close, rsi_period).iloc[-1]
    sma50 = close.rolling(sma_period).mean().iloc[-1]
    macd_line, signal_line = compute_macd(close)
    macd_val = macd_line.iloc[-1]
    macd_signal_val = signal_line.iloc[-1]
    atr = compute_atr(df, adx_period).iloc[-1]

    upper_bb, mid_bb, lower_bb = compute_bollinger(close, bb_period, 2)
    bb_upper = upper_bb.iloc[-1]
    bb_lower = lower_bb.iloc[-1]

    stoch_k, stoch_d = compute_stochastic(df, stoch_period, 3)
    stoch_k_val = stoch_k.iloc[-1]
    stoch_d_val = stoch_d.iloc[-1]

    cci = compute_cci(df, bb_period).iloc[-1]

    adx, plus_di, minus_di = compute_adx(df, adx_period)
    adx_val = adx.iloc[-1]

    volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(volume_period).mean().iloc[-1]

    ema20 = compute_ema(close, ema_period).iloc[-1]
    sar, trend_sar = compute_sar(df)
    sar_val = sar[-1]
    sar_trend = trend_sar[-1]
    obv = compute_obv(df)
    obv_sma = pd.Series(obv).rolling(volume_period).mean().iloc[-1]
    obv_current = obv[-1]
    pivot = compute_pivot(df)
    tenkan, kijun = compute_ichimoku(df)
    tenkan_val = tenkan.iloc[-1]
    kijun_val = kijun.iloc[-1]

    score = 0
    details = []

    if rsi < 35: score += 1; details.append(f"RSI ({rsi:.1f}) – перепроданность")
    elif rsi > 65: score -= 1; details.append(f"RSI ({rsi:.1f}) – перекупленность")
    else: details.append(f"RSI ({rsi:.1f}) – нейтрально")
    if last_price > sma50: score += 1; details.append(f"Цена > SMA ({sma50:.2f}) – тренд вверх")
    else: score -= 1; details.append(f"Цена < SMA ({sma50:.2f}) – тренд вниз")
    if macd_val > macd_signal_val: score += 1; details.append("MACD > сигнал – бычий сигнал")
    else: score -= 1; details.append("MACD < сигнал – медвежий сигнал")
    if last_price < bb_lower: score += 2; details.append(f"Цена ниже ББ ({bb_lower:.2f}) – отскок вверх")
    elif last_price > bb_upper: score -= 2; details.append(f"Цена выше ББ ({bb_upper:.2f}) – отскок вниз")
    else: details.append("Цена внутри полос ББ")
    if stoch_k_val < 20 and stoch_k_val > stoch_d_val: score += 1; details.append(f"Stoch K<20, пересекает D вверх")
    elif stoch_k_val > 80 and stoch_k_val < stoch_d_val: score -= 1; details.append(f"Stoch K>80, пересекает D вниз")
    else: details.append(f"Stochastic K={stoch_k_val:.1f}, D={stoch_d_val:.1f}")
    if cci < -100: score += 1; details.append(f"CCI ({cci:.1f}) < -100 – перепроданность")
    elif cci > 100: score -= 1; details.append(f"CCI ({cci:.1f}) > 100 – перекупленность")
    else: details.append(f"CCI ({cci:.1f}) – нейтрально")
    if adx_val > 20:
        if plus_di.iloc[-1] > minus_di.iloc[-1]: score += 1; details.append(f"ADX>20, +DI>-DI – восходящий тренд")
        else: score -= 1; details.append(f"ADX>20, -DI>+DI – нисходящий тренд")
    else: details.append(f"ADX ({adx_val:.1f}) – слабый тренд")
    if volume_ratio > 1.5:
        if score > 0: score += 1; details.append("Объём подтверждает покупки")
        elif score < 0: score -= 1; details.append("Объём подтверждает продажи")
        else: details.append("Высокий объём при неопределенности")
    else: details.append("Объём средний")
    if last_price > ema20: score += 1; details.append(f"Цена > EMA ({ema20:.2f}) – бычий сигнал")
    else: score -= 1; details.append(f"Цена < EMA ({ema20:.2f}) – медвежий сигнал")
    if sar_trend == 1 and last_price > sar_val: score += 1; details.append("SAR – восходящий тренд")
    elif sar_trend == -1 and last_price < sar_val: score -= 1; details.append("SAR – нисходящий тренд")
    else: details.append("SAR – возможен разворот")
    if obv_current > obv_sma: score += 1; details.append("OBV > SMA – приток объёма")
    else: score -= 1; details.append("OBV < SMA – отток объёма")
    if last_price > pivot['pivot']: score += 1; details.append("Цена > Pivot – бычий настрой")
    else: score -= 1; details.append("Цена < Pivot – медвежий настрой")
    if tenkan_val > kijun_val: score += 1; details.append("Tenkan > Kijun – восходящий тренд")
    else: score -= 1; details.append("Tenkan < Kijun – нисходящий тренд")

    if score >= score_buy:
        direction = "ПОКУПКА"
        take_profit = round(last_price + atr_mult_tp * atr, 2)
        stop_loss = round(last_price - atr_mult_sl * atr, 2)
    elif score <= score_sell:
        direction = "ПРОДАЖА"
        take_profit = round(last_price - atr_mult_tp * atr, 2)
        stop_loss = round(last_price + atr_mult_sl * atr, 2)
    else:
        direction = "НЕТ СИГНАЛА"
        take_profit = None
        stop_loss = None

    rationale = ". ".join(details) + f". Сумма баллов: {score}."
    return {
        'ticker': ticker, 'direction': direction, 'last_price': last_price,
        'rsi': round(rsi, 2), 'sma50': round(sma50, 2),
        'macd': round(macd_val, 5), 'macd_signal': round(macd_signal_val, 5),
        'atr': round(atr, 2), 'take_profit': take_profit, 'stop_loss': stop_loss,
        'rationale': rationale, 'bb_lower': round(bb_lower, 2),
        'bb_upper': round(bb_upper, 2), 'stoch_k': round(stoch_k_val, 1),
        'stoch_d': round(stoch_d_val, 1), 'cci': round(cci, 1),
        'adx': round(adx_val, 1), 'volume_ratio': round(volume_ratio, 2),
        'ema20': round(ema20, 2), 'sar': round(sar_val, 2),
        'sar_trend': 'UP' if sar_trend == 1 else 'DOWN',
        'pivot': round(pivot['pivot'], 2), 'r1': round(pivot['r1'], 2),
        's1': round(pivot['s1'], 2), 'tenkan': round(tenkan_val, 2),
        'kijun': round(kijun_val, 2),
    }
