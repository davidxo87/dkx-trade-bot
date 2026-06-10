import os
import json
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_TOPIC_ID = os.environ.get('TELEGRAM_TOPIC_ID', '3')
CHART_IMG_API_KEY = os.environ.get('CHART_IMG_API_KEY')

def get_chart_image(symbol, interval):
    try:
        interval_map = {
            '1': '1m', '3': '3m', '5': '5m', '15': '15m',
            '30': '30m', '60': '1h', '120': '2h', '240': '4h',
            'D': '1D', 'W': '1W'
        }
        chart_interval = interval_map.get(str(interval), '5m')
        url = 'https://api.chart-img.com/v1/tradingview/advanced-chart'
        params = {
            'symbol': symbol,
            'interval': chart_interval,
            'theme': 'dark',
            'width': 800,
            'height': 500,
            'key': CHART_IMG_API_KEY
        }
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        print(f'Chart error: {e}')
    return None

def send_photo(image_bytes, caption):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
    files = {'photo': ('chart.png', image_bytes, 'image/png')}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'message_thread_id': TELEGRAM_TOPIC_ID, 'caption': caption, 'parse_mode': 'HTML'}
    return requests.post(url, files=files, data=data, timeout=30).json()

def send_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'message_thread_id': TELEGRAM_TOPIC_ID, 'text': text, 'parse_mode': 'HTML'}
    return requests.post(url, json=data, timeout=30).json()

@app.route('/', methods=['GET'])
def index():
    return 'DKX Trade Bot is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        print(f'Raw body: {raw}')
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
            for part in raw.replace('\n', '').split(','):
                if ':' in part:
                    k, v = part.split(':', 1)
                    data[k.strip().strip('"')] = v.strip().strip('"')
        print(f'Parsed: {data}')
        symbol = data.get('symbol', 'UNKNOWN')
        direction = data.get('direction', 'N/A')
        entry = data.get('entry', 'N/A')
        sl = data.get('sl', 'N/A')
        tp = data.get('tp', 'N/A')
        interval = data.get('interval', '5')
        dir_emoji = '\U0001f7e2 LONG' if str(direction).upper() == 'LONG' else '\U0001f534 SHORT' if str(direction).upper() == 'SHORT' else direction
        caption = (
            f'<b>\U0001f4ca DKX Trade Idea</b>\n'
            f'\U0001f4c8 {symbol} | {dir_emoji}\n\n'
            f'\U0001f3af Entry: <code>{entry}</code>\n'
            f'\U0001f6d1 Stop Loss: <code>{sl}</code>\n'
            f'\U0001f3c6 Take Profit: <code>{tp}</code>\n\n'
            f'<i>\u26a0\ufe0f Kein Anlageberatung. CFDs sind riskant.</i>\n'
            f'<i>\u2014 DKX Market Insights</i>'
        )
        img = get_chart_image(symbol, interval)
        result = send_photo(img, caption) if img else send_message(caption)
        print(f'Telegram: {result}')
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f'Error: {e}')
        return jsonify({'status': 'error', 'msg': str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
