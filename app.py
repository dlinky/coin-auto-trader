from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from main import (
    binance, get_major_coins, get_volatile_coins, get_price_data,
    simple_ma_strategy, rsi_strategy,
    StrategyOptimizer, BacktestEngine, TradingTracker
)

app = Flask(__name__)

# 전역 변수
trading_tracker = TradingTracker()
current_strategy = None
current_params = None
is_trading = False
optimizer = StrategyOptimizer()

@app.route('/')
def dashboard():
    """메인 대시보드"""
    return render_template('dashboard.html')

@app.route('/strategy')
def strategy_page():
    """전략 설정 페이지"""
    return render_template('strategy.html')

# 실시간 잔고 조회
@app.route('/api/balance')
def get_balance():
    try:
        balance = binance.fetch_balance()
        usdt = balance['total']['USDT']
        return jsonify({'success': True, 'usdt': usdt})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 실매매(포지션 진입/청산) 예시
@app.route('/api/order', methods=['POST'])
def order():
    data = request.json
    symbol = data.get('symbol')
    side = data.get('side')  # 'buy' or 'sell'
    amount = data.get('amount')
    try:
        if side == 'buy':
            order = binance.create_market_buy_order(symbol, amount)
        else:
            order = binance.create_market_sell_order(symbol, amount)
        return jsonify({'success': True, 'order': order})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/performance')
def get_performance():
    """성과 데이터 API"""
    try:
        balance = binance.fetch_balance()
        usdt = balance['total']['USDT']
        performance = trading_tracker.calculate_performance()
        if performance:
            return jsonify({
                'success': True,
                'data': {
                    'total_trades': performance['total_trades'],
                    'win_rate': performance['win_rate'],
                    'total_pnl': performance['total_pnl'],
                    'total_pnl_percentage': performance['total_pnl_percentage'],
                    'current_balance': usdt,
                    'initial_balance': trading_tracker.initial_balance or usdt
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'current_balance': usdt,
                    'initial_balance': usdt
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent_trades')
def get_recent_trades():
    """최근 거래 내역 API"""
    try:
        trades = trading_tracker.trades[-10:]  # 최근 10개 거래
        formatted_trades = []
        
        for trade in trades:
            formatted_trades.append({
                'timestamp': trade['timestamp'],
                'type': trade['type'],
                'symbol': trade['symbol'],
                'amount': trade['amount'],
                'price': trade['price'],
                'value': trade['value']
            })
        
        return jsonify({'success': True, 'data': formatted_trades})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volatile_coins')
def get_volatile_coins_api():
    """고변동성 코인 목록 API"""
    try:
        coins = get_volatile_coins()
        return jsonify({'success': True, 'data': coins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/optimization_status')
def get_optimization_status():
    """최적화 상태 API"""
    try:
        # 저장된 최적화 결과 확인
        rsi_optimized = optimizer.load_latest_optimization('rsi')
        ma_optimized = optimizer.load_optimization('ma')
        
        status = {
            'rsi': {
                'has_optimization': rsi_optimized is not None,
                'best_return': rsi_optimized['best_result']['total_return'] if rsi_optimized else 0,
                'timestamp': rsi_optimized['timestamp'] if rsi_optimized else None
            },
            'ma': {
                'has_optimization': ma_optimized is not None,
                'best_return': ma_optimized['best_result']['total_return'] if ma_optimized else 0,
                'timestamp': ma_optimized['timestamp'] if ma_optimized else None
            }
        }
        
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/optimization')
def optimization_page():
    """최적화 페이지"""
    return render_template('optimization.html')

@app.route('/api/strategy', methods=['GET', 'POST'])
def strategy_api():
    if request.method == 'POST':
        params = request.json
        with open('strategy_params.json', 'w') as f:
            json.dump(params, f)
        return jsonify({'success': True})
    else:
        if os.path.exists('strategy_params.json'):
            with open('strategy_params.json', 'r') as f:
                params = json.load(f)
            return jsonify({'success': True, 'params': params})
        else:
            return jsonify({'success': False, 'error': 'No params saved'})

@app.route('/api/optimize', methods=['POST'])
def optimize():
    data = request.json
    symbol = data.get('symbol')
    timeframe = data.get('timeframe')
    strategy = data.get('strategy')
    days = data.get('days', 7)
    max_combinations = data.get('max_combinations', 50)
    try:
        result = optimizer.optimize_strategy(symbol, timeframe, strategy, days, max_combinations)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start_optimization', methods=['POST'])
def start_optimization():
    """최적화 시작 API"""
    try:
        data = request.json
        strategy = data.get('strategy')
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        optimization_days = data.get('optimization_days', 7)
        max_combinations = data.get('max_combinations', 50)
        
        # 최적화 실행 (백그라운드에서)
        results = optimizer.optimize_strategy(
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            optimization_days=optimization_days,
            max_combinations=max_combinations
        )
        
        if results:
            return jsonify({
                'success': True,
                'message': '최적화 완료!',
                'data': {
                    'best_return': results['best_result']['total_return'],
                    'best_params': results['best_params']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '최적화 실패'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start_trading', methods=['POST'])
def start_trading():
    """거래 시작 API"""
    global is_trading, current_strategy, current_params
    
    try:
        data = request.json
        strategy = data.get('strategy')
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        params = data.get('params', {})
        
        # 거래 설정 저장
        current_strategy = strategy
        current_params = params
        
        # 거래 시작 (실제로는 백그라운드 스레드에서 실행)
        is_trading = True
        
        return jsonify({
            'success': True,
            'message': f'{symbol} {strategy} 전략으로 거래를 시작합니다.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop_trading', methods=['POST'])
def stop_trading():
    """거래 중지 API"""
    global is_trading
    
    try:
        is_trading = False
        return jsonify({
            'success': True,
            'message': '거래를 중지했습니다.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trading_status')
def get_trading_status():
    """거래 상태 API"""
    global is_trading, current_strategy, current_params
    
    return jsonify({
        'success': True,
        'data': {
            'is_trading': is_trading,
            'current_strategy': current_strategy,
            'current_params': current_params
        }
    })

# 백테스트
@app.route('/api/backtest', methods=['POST'])
def backtest():
    data = request.json
    symbol = data.get('symbol')
    timeframe = data.get('timeframe')
    strategy = data.get('strategy')
    params = data.get('params')
    try:
        df = get_price_data(symbol, limit=1000, timeframe=timeframe)
        engine = BacktestEngine()
        report = engine.run_backtest(df, symbol, timeframe, strategy, params)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 포트폴리오 관리 (예시)
@app.route('/api/portfolio', methods=['GET', 'POST'])
def portfolio():
    if request.method == 'POST':
        portfolio = request.json
        with open('portfolio.json', 'w') as f:
            json.dump(portfolio, f)
        return jsonify({'success': True})
    else:
        if os.path.exists('portfolio.json'):
            with open('portfolio.json', 'r') as f:
                portfolio = json.load(f)
            return jsonify({'success': True, 'portfolio': portfolio})
        else:
            return jsonify({'success': False, 'error': 'No portfolio saved'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 