# engine/plot.py
import pandas as pd
import numpy as np
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .indicators import compute_bollinger

def create_plot(df, result):
    import mplfinance as mpf
    
    df_plot = df.copy()
    df_plot.columns = [c.capitalize() for c in df_plot.columns]
    
    if len(df_plot) > 50:
        df_plot = df_plot.tail(50)
    
    is_dark = result.get('theme', 'light') == 'dark'
    bg_color = '#1a1a1a' if is_dark else '#ffffff'
    tp_color = '#00ff88' if is_dark else '#00b894'
    sl_color = '#ff4444' if is_dark else '#d63031'
    grid_color = '#444' if is_dark else '#d0d0d0'
    
    mc = mpf.make_marketcolors(up=tp_color, down=sl_color, edge='inherit', wick='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', gridcolor=grid_color, facecolor=bg_color)
    
    lines = []
    if len(df_plot) >= 10:
        sma = df_plot['Close'].rolling(10).mean()
        lines.append(mpf.make_addplot(sma, color='#f39c12', linestyle='-', width=1))
    if len(df_plot) >= 5:
        upper, mid, lower = compute_bollinger(df_plot['Close'], 5, 2)
        lines.append(mpf.make_addplot(upper, color='#95a5a6', linestyle=':', width=0.8))
        lines.append(mpf.make_addplot(lower, color='#95a5a6', linestyle=':', width=0.8))
    
    fig, axes = mpf.plot(df_plot, type='candle', style=s, addplot=lines, volume=False,
                         title="", returnfig=True, figsize=(14, 7),
                         datetime_format='%d.%m %H:%M', xrotation=30, tight_layout=True)
    
    ax_main = axes[0]
    
    # === ПРОГНОЗ НА 3 ПЕРИОДА ===
    prediction_periods = 3
    close_vals = df_plot['Close'].values
    last_date = df_plot.index[-1]
    last_close = close_vals[-1]
    
    if len(close_vals) >= 5:
        x_vals = np.arange(len(close_vals))
        lookback = min(10, len(close_vals))
        coeffs = np.polyfit(x_vals[-lookback:], close_vals[-lookback:], 1)
        poly = np.poly1d(coeffs)
        future_x = np.arange(len(close_vals), len(close_vals) + prediction_periods)
        future_y = poly(future_x)
        
        future_dates = []
        cur = last_date
        while len(future_dates) < prediction_periods:
            cur = cur + pd.Timedelta(hours=1)
            future_dates.append(cur)
        
        # === ВЕРТИКАЛЬНАЯ ЧЕРТА-РАЗДЕЛИТЕЛЬ ===
        ax_main.axvline(x=last_date, color='#f39c12', linewidth=3, linestyle='-', alpha=0.9)
        
        # === ЗОНА ПРОГНОЗА ===
        ax_main.axvspan(last_date, future_dates[-1], alpha=0.15, color='#f39c12')
        
        # === ЛИНИЯ ПРОГНОЗА ===
        extended_dates = [last_date] + future_dates
        extended_values = [last_close] + list(future_y)
        ax_main.plot(extended_dates, extended_values, color='#f39c12', linestyle='--',
                    linewidth=2.5, marker='o', markersize=10, zorder=5)
        
        # === ТОЧКИ TP И SL ===
        if result['take_profit']:
            ax_main.axhline(y=result['take_profit'], color=tp_color, linestyle='--', linewidth=1.5)
            ax_main.scatter(future_dates[-1], result['take_profit'], color=tp_color, s=120,
                          zorder=10, marker='D', edgecolors='white', linewidths=1)
            ax_main.annotate(f"TP: {result['take_profit']}", (future_dates[-1], result['take_profit']),
                           textcoords="offset points", xytext=(10, 0), fontsize=10,
                           color=tp_color, fontweight='bold', va='center',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor=bg_color, edgecolor=tp_color, alpha=0.9))
        
        if result['stop_loss']:
            ax_main.axhline(y=result['stop_loss'], color=sl_color, linestyle='--', linewidth=1.5)
            ax_main.scatter(future_dates[-1], result['stop_loss'], color=sl_color, s=120,
                          zorder=10, marker='D', edgecolors='white', linewidths=1)
            ax_main.annotate(f"SL: {result['stop_loss']}", (future_dates[-1], result['stop_loss']),
                           textcoords="offset points", xytext=(10, 0), fontsize=10,
                           color=sl_color, fontweight='bold', va='center',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor=bg_color, edgecolor=sl_color, alpha=0.9))
    
    ax_main.grid(True, alpha=0.3, color=grid_color)
    ax_main.legend(loc='upper left', fontsize=8)
    
    if is_dark:
        ax_main.set_facecolor('#1a1a1a')
        ax_main.tick_params(colors='#ccc')
        ax_main.yaxis.label.set_color('#ccc')
    
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=80, facecolor=bg_color)
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:image/png;base64,{img_base64}'