import os
import re
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_TOPIC_ID  = os.environ.get('TELEGRAM_TOPIC_ID', '3')
CHART_IMG_API_KEY  = os.environ.get('CHART_IMG_API_KEY')

DISCLAIMER = 'Diese Trade Idea dient ausschliesslich zu Informations- und Bildungszwecken und stellt keine Anlageberatung dar.'

def parse_body(raw):
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    data = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith('Trade-Idea:'):
            parts = line.replace('Trade-Idea:', '').strip().split('|')
            if parts:
                data['symbol'] = parts[0].strip()
            if len(parts) > 1:
                data['interval'] = parts[1].strip()
        elif line.startswith('Richtung:'):
            data['direction'] = line.replace('Richtung:', '').strip()
        elif line.startswith('Entry:'):
            data['entry'] = line.replace('Entry:', '').strip()
        elif line.startswith('Stop Loss:'):
            data['sl'] = line.replace('Stop Loss:', '').strip()
        elif line.startswith('Take Profit 1:'):
            data['tp1'] = line.replace('Take Profit 1:', '').strip()
        elif line.startswith('Take Profit 2:'):
            data['tp2'] = line.replace('Take Profit 2:', '').strip()
        elif line.startswith('Take Profit 3:'):
            data['tp3'] = line.replace('Take Profit 3:', '').strip()
    return data

def get_chart_image(symbol, interval):
    try:
        interval_map = {
            '1': '1m', '3': '3m', '5': '5m', '15': '15m',
            '30': '30m', '60': '1h', '1h': '1h', '120': '2h',
            '240': '4h', '4h': '4h', 'D': '1D', '1D': '1D', 'W': '1W'
        }
        tf = interval_map.get(str(interval), '5m')
        url = 'https://api.chart-img.com/v2/tradingview/advanced-chart/storage'
        params = {
            'symbol': symbol,
            'interval': tf,
            'theme': 'dark',
            'width': 800,
            'height': 500,
            'key': CHART_IMG_API_KEY
        }
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.content
        print(f'Chart-IMG: {r.status_code} {r.text[:200]}')
    except Exception as e:
        print(f'Chart error: {e}')
    return None

def send_photo(image_bytes, caption):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
    files = {'photo': ('chart.png', image_bytes, 'image/png')}
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_thread_id': TELEGRAM_TOPIC_ID,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    return requests.post(url, files=files, data=data, timeout=30).json()

def send_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_thread_id': TELEGRAM_TOPIC_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    return requests.post(url, json=data, timeout=30).json()

@app.route('/', methods=['GET'])
def index():
    return 'DKX Trade Bot is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        print(f'RAW: {repr(raw)}')
        data = parse_body(raw)
        print(f'PARSED: {data}')

        symbol    = data.get('symbol', 'N/A')
        direction = data.get('direction', 'N/A')
        entry     = data.get('entry', 'N/A')
        sl        = data.get('sl', 'N/A')
        tp1       = data.get('tp1', '')
        tp2       = data.get('tp2', '')
        tp3       = data.get('tp3', '')
        interval  = data.get('interval', '5m')

        d = direction.upper()
        dir_emoji = '\U0001f7e2 LONG' if d == 'LONG' else '\U0001f534 SHORT' if d == 'SHORT' else direction

        tp_lines = ''
        if tp1:
            tp_lines += f'\U0001f3c6 Take Profit 1: <code>{tp1}</code>\n'
        if tp2:
            tp_lines += f'\U0001f3c6 Take Profit 2: <code>{tp2}</code>\n'
        if tp3:
            tp_lines += f'\U0001f3c6 Take Profit 3: <code>{tp3}</code>\n'

        caption = (
            f'<b>\U0001f4ca DKX Trade Idea</b>\n'
            f'\U0001f4c8 <b>{symbol}</b> | {dir_emoji}\n\n'
            f'\U0001f3af Entry:      <code>{entry}</code>\n'
            f'\U0001f6d1 Stop Loss: <code>{sl}</code>\n'
            f'{tp_lines}\n'
            f'<i>\u26a0\ufe0f {DISCLAIMER}</i>\n'
            f'<i>\u2014 DKX Market Insights</i>'
        )

        img = get_chart_image(symbol, interval)
        result = send_photo(img, caption) if img else send_message(caption)
        print(f'Telegram: {result}')
        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        print(f'ERROR: {e}')
        return jsonify({'status': 'error', 'msg': str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
