from flask import Flask, render_template, jsonify, request
from binance.client import Client
import pandas as pd
from backtest import Backtest
import threading
import queue
import json
from datetime import datetime

app = Flask(__name__)

# API 클라이언트 초기화
client = Client()

# 작업 상태 및 결과를 저장할 큐
task_queue = queue.Queue()
result_queue = queue.Queue()

def get_futures_symbols():
    """선물 티커 목록 가져오기"""
    try:
        exchange_info = client.futures_exchange_info()
        return [
            symbol['symbol'] for symbol in exchange_info['symbols']
            if symbol['status'] == 'TRADING' and symbol['symbol'].endswith('USDT')
        ]
    except Exception as e:
        print(f"선물 티커 목록을 가져오는 중 오류 발생: {str(e)}")
        return []

def get_historical_data(symbol, interval, days):
    """과거 데이터 가져오기"""
    try:
        klines = client.get_historical_klines(
            symbol,
            interval,
            str(days) + " days ago UTC"
        )
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"데이터를 가져오는 중 오류 발생: {str(e)}")
        return None

def find_high_volatility_symbols():
    """변동성이 높은 티커 찾기"""
    try:
        futures_symbols = get_futures_symbols()
        volatility_data = []
        
        for symbol in futures_symbols:
            try:
                ticker = client.futures_ticker(symbol=symbol)
                
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
                open_price = float(ticker['openPrice'])
                volume = float(ticker['volume'])
                
                volatility = ((high - low) / open_price) * 100
                
                volatility_data.append({
                    'symbol': symbol,
                    'volatility': volatility,
                    'volume': volume
                })
                
            except Exception as e:
                print(f"{symbol} 데이터 가져오기 실패: {str(e)}")
                continue
        
        if not volatility_data:
            return []
        
        volatility_data.sort(key=lambda x: x['volatility'], reverse=True)
        top_volatile = volatility_data[:20]
        
        volume_threshold = sorted([x['volume'] for x in top_volatile])[len(top_volatile)//2]
        filtered_symbols = [x['symbol'] for x in top_volatile if x['volume'] >= volume_threshold]
        
        return filtered_symbols[:10]
        
    except Exception as e:
        print(f"변동성 분석 중 오류 발생: {str(e)}")
        return []

def run_backtest(symbol, interval, days):
    """백테스팅 실행"""
    try:
        data = get_historical_data(symbol, interval, days)
        if data is None:
            return None
        
        backtest = Backtest(data)
        return backtest.run()
    except Exception as e:
        print(f"백테스팅 중 오류 발생: {str(e)}")
        return None

def background_task():
    """백그라운드 작업 처리"""
    while True:
        task = task_queue.get()
        if task is None:
            break
            
        task_type = task.get('type')
        if task_type == 'test_multiple_symbols':
            try:
                volatile_symbols = find_high_volatility_symbols()
                results = []
                
                for symbol in volatile_symbols:
                    result = run_backtest(symbol, task['interval'], task['days'])
                    if result:
                        results.append({
                            'symbol': symbol,
                            'profit_factor': result['profit_factor'],
                            'total_return': result['total_return'],
                            'win_rate': result['win_rate'],
                            'max_drawdown': result['max_drawdown']
                        })
                
                if results:
                    results.sort(key=lambda x: x['profit_factor'], reverse=True)
                    result_queue.put({
                        'type': 'test_multiple_symbols',
                        'status': 'success',
                        'results': results[:3]  # 상위 3개만 반환
                    })
                else:
                    result_queue.put({
                        'type': 'test_multiple_symbols',
                        'status': 'error',
                        'message': '백테스팅 결과가 없습니다.'
                    })
                    
            except Exception as e:
                result_queue.put({
                    'type': 'test_multiple_symbols',
                    'status': 'error',
                    'message': str(e)
                })
        
        task_queue.task_done()

# 백그라운드 작업 스레드 시작
worker = threading.Thread(target=background_task)
worker.daemon = True
worker.start()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/symbols')
def get_symbols():
    """사용 가능한 티커 목록 반환"""
    symbols = get_futures_symbols()
    return jsonify({'symbols': symbols})

@app.route('/api/test', methods=['POST'])
def test_symbols():
    """다중 티커 테스트 시작"""
    data = request.json
    interval = data.get('interval', '1m')
    days = data.get('days', 30)
    
    task_queue.put({
        'type': 'test_multiple_symbols',
        'interval': interval,
        'days': days
    })
    
    return jsonify({'status': 'started'})

@app.route('/api/results')
def get_results():
    """테스트 결과 확인"""
    try:
        result = result_queue.get_nowait()
        return jsonify(result)
    except queue.Empty:
        return jsonify({'status': 'pending'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 