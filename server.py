import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Config from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_TOPIC_ID = os.environ.get('TELEGRAM_TOPIC_ID', '3')
CHART_IMG_API_KEY = os.environ.get('CHART_IMG_API_KEY')

def get_chart_image(symbol, interval):
    """Get chart screenshot from chart-img.com API"""
    try:
        # Map TradingView interval to chart-img format
        interval_map = {
            '1': '1m', '3': '3m', '5': '5m', '15': '15m',
            '30': '30m', '60': '1h', '120': '2h', '240': '4h',
            'D': '1D', 'W': '1W'
        }
        chart_interval = interval_map.get(str(interval), '1h')
        
        url = 'https://api.chart-img.com/v1/tradingview/advanced-chart'
        params = {
            'symbol': symbol,
            'interval': chart_interval,
            'theme': 'dark',
            'width': 800,
            'height': 500,
            'key': CHART_IMG_API_KEY
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f'Chart image error: {e}')
    return None

def send_telegram_photo(image_bytes, caption):
    """Send photo with caption to Telegram topic"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
    files = {'photo': ('chart.png', image_bytes, 'image/png')}
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_thread_id': TELEGRAM_TOPIC_ID,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, files=files, data=data, timeout=30)
    return response.json()

def send_telegram_message(text):
    """Send text message to Telegram topic"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_thread_id': TELEGRAM_TOPIC_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, json=data, timeout=30)
    return response.json()

@app.route('/', methods=['GET'])
def index():
    return 'DKX Trade Bot is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Parse the incoming JSON from TradingView alert
        data = request.get_json(force=True)
        if not data:
            raw = request.data.decode('utf-8')
            data = json.loads(raw)
        
        print(f'Received webhook: {data}')
        
        symbol = data.get('symbol', 'N/A')
        direction = data.get('direction', 'N/A')
        entry = data.get('entry', 'N/A')
        sl = data.get('sl', 'N/A')
        tp = data.get('tp', 'N/A')
        interval = data.get('interval', '60')
        time_str = data.get('time', '')
        
        # Build direction emoji
        if str(direction).upper() in ['LONG', 'BUY', 'UP']:
            dir_emoji = '\U0001f7e2 LONG'
        elif str(direction).upper() in ['SHORT', 'SELL', 'DOWN']:
            dir_emoji = '\U0001f534 SHORT'
        else:
            dir_emoji = direction
        
        # Build message
        caption = (
            f'<b>\U0001f4ca DKX Trade Idea</b>\n'
            f'\U0001f4c8 {symbol} | {dir_emoji}\n\n'
            f'\U0001f3af Entry: <code>{entry}</code>\n'
            f'\U0001f6d1 Stop Loss: <code>{sl}</code>\n'
            f'\U0001f3c6 Take Profit: <code>{tp}</code>\n'
        )
        if time_str:
            caption += f'\n\U000023f0 Zeit: {time_str}'
        caption += '\n\n<i>\u26a0\ufe0f Kein Anlageberatung. CFDs sind riskant.</i>\n<i>- DKX Market Insights</i>'
        
        # Try to get chart image
        image_bytes = get_chart_image(symbol, interval)
        
        if image_bytes:
            result = send_telegram_photo(image_bytes, caption)
        else:
            result = send_telegram_message(caption)
        
        print(f'Telegram result: {result}')
        return jsonify({'status': 'ok', 'result': result})
    
    except Exception as e:
        print(f'Webhook error: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
