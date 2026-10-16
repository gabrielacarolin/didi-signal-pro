"""Gera dados SINTÉTICOS para testar leitura e loop, não para avaliar desempenho."""
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import csv, math
out = Path('data'); out.mkdir(exist_ok=True)
start = datetime.now(ZoneInfo('America/Sao_Paulo')).replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=2)
for asset, base, step in [('WIN', 140000, 5), ('WDO', 5300, 0.5)]:
    with (out / f'{asset}.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['timestamp','open','high','low','close'])
        last = base
        for i in range(80):
            delta = round((math.sin(i/5)*3 + (0.15 if i>60 else 0))*step/step)*step
            close = last + delta
            w.writerow([(start + timedelta(minutes=5*i)).isoformat(), last, max(last,close)+2*step, min(last,close)-2*step, close])
            last = close
print('Arquivos sintéticos gerados em data/. Não representam mercado real.')
