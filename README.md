# DIDI SIGNAL PRO v1 — SIMULAÇÃO

**Não opera na bolsa.** Lê CSVs de candles de 5 minutos já fechados e envia alertas opcionais ao Telegram.
Não há conexão automática com Profit, Rico ou bolsa nesta versão.

## Instalação Windows (PowerShell)

1. Instale Python 3.11 ou superior em python.org e habilite PATH.
2. Extraia o ZIP e abra PowerShell dentro da pasta `didi_signal_pro`.
3. Execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python make_demo.py
python bot.py --once
```

Se o PowerShell bloquear ativação, execute `.\.venv\Scripts\python.exe` no lugar de `python` sem ativar.

## Telegram

1. Converse com @BotFather no Telegram e crie um bot com `/newbot`.
2. Envie uma mensagem ao seu novo bot.
3. Abra `https://api.telegram.org/botSEU_TOKEN/getUpdates` e encontre `message.chat.id`.
4. No `.env`, configure `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` e `SEND_TELEGRAM=true`.
5. Nunca publique o token. Rode `python bot.py --once` para avaliar arquivos ou `python bot.py` para monitorar.

## Dados CSV

Substitua `data/WIN.csv` e `data/WDO.csv` por candles reais de fonte autorizada. Campos: `timestamp,open,high,low,close` (volume opcional). Timestamp deve indicar a **abertura** do candle e conter offset de fuso horário, preferencialmente `-03:00`. O sistema só usa candles cujo horário de fechamento já passou. Arquivos devem ser atualizados por processo externo: o programa **não coleta dados do Profit**.

Os exemplos são sintéticos, sem valor preditivo. O robô sinaliza aproximação de médias <= 0,35 ATR em um dos cinco candles anteriores; abertura >= 0,45 ATR; ordem das SMA 3/8/20; direção da SMA3; fechamento acima/abaixo da SMA3 e rompimento da máxima/mínima anterior. Parâmetros são hipóteses iniciais e precisam de backtest e validação. O stop de 1 ATR e alvo de 2 ATR são teóricos, sem slippage, corretagem, emolumentos ou simulação de execução.

## Rodar na nuvem

Em VPS Linux com Python 3.11+, copie a pasta, instale `requirements.txt`, configure `.env` e execute `python bot.py` em um serviço `systemd` ou container supervisionado. O servidor precisa receber CSVs novos de fornecedor autorizado; caso contrário não há alertas novos. Configure reinício automático, logs, firewall e proteção do `.env`.

## Limitações e segurança

- Sem envio de ordens e sem conta conectada.
- Não há filtro de horário do pregão ou de notícias; deve ser acrescentado antes de uso real.
- Sem controle de risco financeiro por contrato ou P&L realizado; stop e alvo são informativos.
- Não garante sinais ou lucratividade. Não use alertas como recomendação individual de investimento.
- Estado em `state.json` evita repetir sinal do mesmo candle após reinício.
