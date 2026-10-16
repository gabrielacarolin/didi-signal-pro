"""DIDI SIGNAL PRO: alertas educativos com candles CSV de 5 minutos.
Não envia ordens. Não possui integração nativa com Profit/Rico.
CSV esperado: timestamp,open,high,low,close (volume opcional).
"""
import argparse
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

TZ = ZoneInfo('America/Sao_Paulo')
STATE_FILE = Path('state.json')
TICK = {'WIN': 5.0, 'WDO': 0.5}  # incrementos de preço em pontos

def load_candles(path):
    df = pd.read_csv(path)
    required = {'timestamp', 'open', 'high', 'low', 'close'}
    if not required.issubset(df.columns):
        raise ValueError(f'Colunas ausentes: {required - set(df.columns)}')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='raise')
    if df['timestamp'].dt.tz is None:
        df['timestamp'] = df['timestamp'].dt.tz_localize(TZ, ambiguous='raise', nonexistent='raise')
    else:
        df['timestamp'] = df['timestamp'].dt.tz_convert(TZ)
    df = df.sort_values('timestamp').drop_duplicates('timestamp', keep='last').reset_index(drop=True)
    for col in ('open', 'high', 'low', 'close'):
        df[col] = pd.to_numeric(df[col], errors='raise')
    if (df['high'] < df[['open', 'close', 'low']].max(axis=1)).any() or (df['low'] > df[['open','close','high']].min(axis=1)).any():
        raise ValueError('OHLC inconsistente')
    return df

def calculate(df, asset):
    """Sinal no último candle FECHADO informado. CSV não pode conter candle em formação."""
    if len(df) < 30:
        return None
    d = df.copy()
    for n in (3, 8, 20):
        d[f'sma{n}'] = d['close'].rolling(n).mean()
    d['range_ma'] = d[['sma3', 'sma8', 'sma20']].max(axis=1) - d[['sma3', 'sma8', 'sma20']].min(axis=1)
    d['atr'] = pd.concat([(d.high-d.low), (d.high-d.close.shift()).abs(), (d.low-d.close.shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    last = d.iloc[-1]
    if pd.isna(last.atr) or last.atr <= 0:
        return None
    # Aproximação recente: dispersão das médias <= 0.35 ATR, em pelo menos um dos 5 candles anteriores.
    prior = d.iloc[-6:-1]
    compressed = ((prior.range_ma <= 0.35 * prior.atr) & prior.atr.gt(0)).any()
    if not compressed or last.range_ma < 0.45 * last.atr:
        return None
    prev = d.iloc[-2]
    buy = (last.sma3 > last.sma8 > last.sma20 and last.sma3 > prev.sma3
           and last.close > last.sma3 and last.close > prev.high)
    sell = (last.sma3 < last.sma8 < last.sma20 and last.sma3 < prev.sma3
            and last.close < last.sma3 and last.close < prev.low)
    if not (buy or sell):
        return None
    side = 'COMPRA' if buy else 'VENDA'
    # Stop técnico ilustrativo: 1 ATR, alvo 2 ATR; arredondamento conservador ao tick.
    import math
    tick = TICK[asset]
    entry = float(last.close)
    risk_ticks = max(1, math.ceil(float(last.atr) / tick))
    risk = risk_ticks * tick
    stop = entry - risk if buy else entry + risk
    target = entry + 2 * risk if buy else entry - 2 * risk
    return {'asset': asset, 'side': side, 'timestamp': last.timestamp.isoformat(),
            'entry': entry, 'stop': stop, 'target': target, 'risk_points': risk,
            'atr': round(float(last.atr), 2), 'mode': 'SIMULAÇÃO'}

def notify(signal):
    msg = (f"DIDI SIGNAL PRO | {signal['mode']}\n{signal['asset']} - {signal['side']} (5 min)\n"
           f"Candle: {signal['timestamp']}\nEntrada referência: {signal['entry']}\n"
           f"Stop teórico: {signal['stop']} | Alvo teórico: {signal['target']}\n"
           'Sinal experimental. Não é ordem nem garantia de resultado.')
    print(msg, flush=True)
    if os.getenv('SEND_TELEGRAM', 'false').lower() != 'true':
        return True
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat:
        raise RuntimeError('Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID')
    response = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                             json={'chat_id': chat, 'text': msg}, timeout=15)
    response.raise_for_status()
    if not response.json().get('ok'):
        raise RuntimeError('Telegram recusou mensagem')
    return True

def run_once(data_dir, state):
    for asset in ('WIN', 'WDO'):
        path = Path(data_dir) / f'{asset}.csv'
        if not path.exists():
            logging.warning('Arquivo ausente: %s', path)
            continue
        try:
            df = load_candles(path)
            if df.empty:
                continue
            # Evita usar candle ainda aberto, assumindo timestamp de ABERTURA do candle.
            now = pd.Timestamp.now(tz=TZ)
            df = df[df.timestamp + pd.Timedelta(minutes=5) <= now]
            if df.empty:
                continue
            signal = calculate(df, asset)
            if not signal:
                logging.info('%s: AGUARDAR', asset)
                continue
            key = f"{asset}:{signal['timestamp']}:{signal['side']}"
            if state.get(asset) == key:
                continue
            notify(signal)
            state[asset] = key
            STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')
        except Exception:
            logging.exception('Falha ao processar %s', asset)
    return state

def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    state = json.loads(STATE_FILE.read_text(encoding='utf-8')) if STATE_FILE.exists() else {}
    while True:
        run_once(os.getenv('DATA_DIR', 'data'), state)
        if args.once:
            break
        time.sleep(max(10, int(os.getenv('POLL_SECONDS', '30'))))

if __name__ == '__main__':
    main()
