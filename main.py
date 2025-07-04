import ccxt
import pandas as pd
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta
import itertools
from typing import Dict, List, Tuple, Optional, Any
import threading
import sys

with open('.env', 'r') as f:
    api_key = f.readline().strip().split('=')[1]
    secret_key = f.readline().strip().split('=')[1]

binance = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'sandbox': False,
    'options': {
        'defaultType': 'future',
    }
})

def get_major_coins():
    """거래량 기준으로 주요 코인을 동적으로 찾는 메소드"""
    try:
        # 모든 선물 티커 가져오기
        tickers = binance.fetch_tickers()
        
        # USDT 선물만 필터링하고 거래량 기준으로 정렬
        usdt_futures = []
        seen_symbols = set()  # 중복 방지를 위한 set
        
        for symbol, ticker in tickers.items():
            if ':USDT' in symbol and 'USDT' in symbol:
                # 심볼 정규화 (중복 제거)
                normalized_symbol = symbol
                
                # 이미 처리된 심볼인지 확인
                if normalized_symbol in seen_symbols:
                    continue
                
                # 거래량 계산 (여러 방법 시도)
                volume = 0
                if 'quoteVolume' in ticker and ticker['quoteVolume']:
                    volume = ticker['quoteVolume']
                elif 'baseVolume' in ticker and ticker['baseVolume'] and 'last' in ticker:
                    volume = ticker['baseVolume'] * ticker['last']
                
                if volume > 0:
                    usdt_futures.append({
                        'symbol': normalized_symbol,
                        'volume': volume,
                        'price': ticker['last'] if 'last' in ticker else 0
                    })
                    seen_symbols.add(normalized_symbol)
        
        # 거래량 순으로 정렬하고 상위 50개 선택
        usdt_futures.sort(key=lambda x: x['volume'], reverse=True)
        major_coins = [item['symbol'] for item in usdt_futures[:50]]
        
        print(f"거래량 기준 상위 50개 코인 발견")
        return major_coins
        
    except Exception as e:
        print(f"Error fetching major coins: {e}")
        # 폴백: 기본 주요 코인 리스트
        return [
            'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'SOL/USDT:USDT',
            'XRP/USDT:USDT', 'ADA/USDT:USDT', 'AVAX/USDT:USDT', 'DOGE/USDT:USDT',
            'DOT/USDT:USDT', 'MATIC/USDT:USDT', 'LINK/USDT:USDT', 'UNI/USDT:USDT',
            'LTC/USDT:USDT', 'BCH/USDT:USDT', 'ATOM/USDT:USDT', 'ETC/USDT:USDT',
            'XLM/USDT:USDT', 'FIL/USDT:USDT', 'TRX/USDT:USDT', 'NEAR/USDT:USDT',
            'APT/USDT:USDT', 'OP/USDT:USDT', 'ARB/USDT:USDT', 'MKR/USDT:USDT',
            'AAVE/USDT:USDT', 'SAND/USDT:USDT', 'MANA/USDT:USDT', 'ALGO/USDT:USDT',
            'VET/USDT:USDT', 'ICP/USDT:USDT', 'THETA/USDT:USDT', 'FTM/USDT:USDT',
            'AXS/USDT:USDT', 'GALA/USDT:USDT', 'ROSE/USDT:USDT', 'CHZ/USDT:USDT',
            'HOT/USDT:USDT', 'ZIL/USDT:USDT', 'ENJ/USDT:USDT', 'BAT/USDT:USDT',
            'DASH/USDT:USDT', 'ZEC/USDT:USDT', 'XMR/USDT:USDT', 'EOS/USDT:USDT',
            'WAVES/USDT:USDT', 'NEO/USDT:USDT', 'QTUM/USDT:USDT', 'IOTA/USDT:USDT',
            'XTZ/USDT:USDT', 'OMG/USDT:USDT', 'ZRX/USDT:USDT', 'KNC/USDT:USDT'
        ]

def get_volatile_coins(min_volume=1000000, min_volatility=0.02, top_n=10):
    """
    스캘핑에 적합한 고변동성 코인을 찾는 메소드
    
    Args:
        min_volume: 최소 24시간 거래량 (USDT)
        min_volatility: 최소 변동성 (2% = 0.02)
        top_n: 상위 N개 코인 반환
    
    Returns:
        변동성 순으로 정렬된 코인 리스트
    """
    try:
        # 동적으로 주요 코인 찾기
        major_coins = get_major_coins()
        
        print(f"총 {len(major_coins)}개의 주요 코인 분석 중...")
        
        # 변동성 계산
        volatile_coins = []
        for symbol in major_coins:
            try:
                # 티커 정보 가져오기
                ticker = binance.fetch_ticker(symbol)
                
                # 최근 24시간 OHLC 데이터 가져오기
                ohlcv = binance.fetch_ohlcv(symbol, '1h', limit=24)
                if len(ohlcv) >= 24:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # 변동성 계산 (고가-저가)/저가
                    high = df['high'].max()
                    low = df['low'].min()
                    volatility = (high - low) / low
                    
                    # 거래량 계산 (OHLCV 데이터에서)
                    total_volume = df['volume'].sum() * ticker['last']
                    
                    # 최소 변동성 조건 확인
                    if volatility >= min_volatility and total_volume >= min_volume:
                        # 추가 지표 계산
                        price_change_24h = (ticker['last'] - ticker['open']) / ticker['open'] if ticker['open'] else 0
                        
                        volatile_coins.append({
                            'symbol': symbol,
                            'current_price': ticker['last'],
                            'volume_24h': total_volume,
                            'volatility': volatility,
                            'price_change_24h': price_change_24h,
                            'high_24h': high,
                            'low_24h': low
                        })
                        
                        print(f"Found: {symbol} - Volatility: {volatility*100:.1f}%, Volume: {total_volume/1000000:.1f}M")
                        
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # 변동성 순으로 정렬
        volatile_coins.sort(key=lambda x: x['volatility'], reverse=True)
        
        # 상위 N개만 반환
        return volatile_coins[:top_n]
        
    except Exception as e:
        print(f"Error fetching volatile coins: {e}")
        return []

def print_volatile_coins(coins):
    """변동성 코인 정보를 예쁘게 출력"""
    print("\n" + "="*80)
    print("🔥 스캘핑 적합 코인 TOP 10 🔥")
    print("="*80)
    print(f"{'순위':<4} {'심볼':<15} {'현재가':<12} {'변동성':<8} {'24H변화':<8} {'거래량(백만)':<12}")
    print("-"*80)
    
    for i, coin in enumerate(coins, 1):
        symbol = coin['symbol'].replace(':USDT', '')
        current_price = f"${coin['current_price']:,.2f}"
        volatility = f"{coin['volatility']*100:.1f}%"
        price_change = f"{coin['price_change_24h']*100:+.1f}%"
        volume = f"{coin['volume_24h']/1000000:.1f}M"
        
        print(f"{i:<4} {symbol:<15} {current_price:<12} {volatility:<8} {price_change:<8} {volume:<12}")
    
    print("="*80)

def get_price_data(symbol, limit=100, timeframe='1h'):
    try:
        # 바이낸스 API 제한을 고려한 데이터 수집
        max_candles_per_request = 1000  # 바이낸스 API 최대 제한
        
        if limit <= max_candles_per_request:
            # 한 번에 가져올 수 있는 경우
            candles = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        else:
            # 여러 번에 나누어 가져오기
            all_candles = []
            total_requested = limit
            
            print(f"🔄 {symbol} 데이터 수집 중... (목표: {limit}개 캔들)")
            
            # 첫 번째 요청 (최신 데이터)
            candles = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=max_candles_per_request)
            if candles:
                all_candles.extend(candles)
                print(f"  📥 1차 수집: {len(candles)}개 캔들")
                
                # 추가 데이터가 필요한 경우
                if len(all_candles) < total_requested:
                    # 이전 데이터 요청 (since 파라미터 사용)
                    # 첫 번째 캔들의 타임스탬프에서 더 과거로 이동
                    since = candles[0][0] - (max_candles_per_request * get_timeframe_ms(timeframe))
                    
                    while len(all_candles) < total_requested:
                        time.sleep(0.1)  # API 제한 방지 (100ms)
                        
                        try:
                            candles = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=max_candles_per_request, since=since)
                            if not candles or len(candles) == 0:
                                break
                                
                            all_candles.extend(candles)
                            print(f"  📥 추가 수집: {len(candles)}개 캔들 (총 {len(all_candles)}개)")
                            
                            # 다음 since 값 업데이트 (가장 오래된 캔들의 타임스탬프에서 더 과거로)
                            since = candles[0][0] - (max_candles_per_request * get_timeframe_ms(timeframe))
                            
                        except Exception as e:
                            print(f"  ⚠️ 추가 데이터 수집 실패: {e}")
                            break
                
                # 중복 제거 및 정렬 (한 번만 실행)
                if len(all_candles) > 1:
                    all_candles = sorted(all_candles, key=lambda x: x[0])
                    unique_candles = []
                    seen_timestamps = set()
                    for candle in all_candles:
                        if candle[0] not in seen_timestamps:
                            unique_candles.append(candle)
                            seen_timestamps.add(candle[0])
                    all_candles = unique_candles
                    print(f"  🔄 중복 제거 후: {len(all_candles)}개 캔들")
                
                # API 호출 제한 방지 (바이낸스 정책: 1200 requests/minute = 50ms 간격)
                time.sleep(0.1)  # 100ms 딜레이 (안전 마진 포함)
            
            candles = all_candles
        
        if not candles:
            print(f"데이터를 가져올 수 없습니다: {symbol}")
            return None
            
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # 중복 제거 및 정렬
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()
        
        print(f"📊 {symbol} 데이터 수집 완료: {len(df)}개 캔들 ({df.index[0].strftime('%Y-%m-%d %H:%M')} ~ {df.index[-1].strftime('%Y-%m-%d %H:%M')})")
        
        return df
    except Exception as e:
        print(f"Error fetching price data for {symbol}: {e}")
        return None
    
def simple_ma_strategy(df, current_index=None, params=None, has_position=False):
    """이동평균 크로스오버 전략 (파라미터 기반)"""
    # 기본 파라미터 설정
    default_params = {
        'short_period': 5,       # 단기 이동평균
        'long_period': 20,       # 장기 이동평균
        'stop_loss': -0.02,      # 손절 비율
        'take_profit': 0.03,     # 익절 비율
        'max_hold_hours': 24     # 최대 보유 시간
    }
    
    # 파라미터 병합
    if params is None:
        params = {}
    strategy_params = {**default_params, **params}
    
    # 백테스팅을 위한 인덱스 처리
    if current_index is None:
        current_index = len(df) - 1
    
    # 이동평균 계산을 위한 최소 데이터 필요량
    min_required = max(strategy_params['short_period'], strategy_params['long_period']) + 5
    
    if len(df) < min_required or current_index < min_required:
        return 'HOLD', None
    
    # 현재 시점까지만 데이터 사용 (미래 데이터 사용 방지)
    current_df = df.iloc[:current_index + 1]
    
    # 이동평균 계산
    short_ma = current_df['close'].rolling(window=strategy_params['short_period']).mean()
    long_ma = current_df['close'].rolling(window=strategy_params['long_period']).mean()
    
    # 현재 이동평균 값
    current_short_ma = short_ma.iloc[-1]
    current_long_ma = long_ma.iloc[-1]
    
    # 이전 이동평균 값
    prev_short_ma = short_ma.iloc[-2] if len(short_ma) > 1 else current_short_ma
    prev_long_ma = long_ma.iloc[-2] if len(long_ma) > 1 else current_long_ma
    
    # NaN 체크
    if pd.isna(current_short_ma) or pd.isna(current_long_ma):
        return 'HOLD', None
    
    # 포지션이 있을 때는 매수하지 않음
    if has_position:
        # 매도 조건: 단기 이동평균이 장기 이동평균 아래로
        if current_short_ma < current_long_ma and prev_short_ma >= prev_long_ma:
            return 'SELL', '신호매도'
        else:
            return 'HOLD', None
    else:
        # 포지션이 없을 때만 매수 신호 생성
        # 매수 조건: 단기 이동평균이 장기 이동평균 위로
        if current_short_ma > current_long_ma and prev_short_ma <= prev_long_ma:
            return 'BUY', None
        else:
            return 'HOLD', None

def get_timeframe_ms(timeframe):
    """타임프레임을 밀리초로 변환"""
    timeframe_map = {
        '1m': 60 * 1000,
        '3m': 3 * 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '2h': 2 * 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '6h': 6 * 60 * 60 * 1000,
        '8h': 8 * 60 * 60 * 1000,
        '12h': 12 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
        '3d': 3 * 24 * 60 * 60 * 1000,
        '1w': 7 * 24 * 60 * 60 * 1000,
        '1M': 30 * 24 * 60 * 60 * 1000
    }
    return timeframe_map.get(timeframe, 60 * 1000)  # 기본값 1분

def calculate_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def find_pivot_points(df, window=5):
    """피벗 포인트 (고점/저점) 찾기"""
    highs = df['high'].rolling(window=window, center=True).max()
    lows = df['low'].rolling(window=window, center=True).min()
    
    pivot_highs = []
    pivot_lows = []
    
    for i in range(len(df)):
        if df['high'].iloc[i] == highs.iloc[i]:
            pivot_highs.append({
                'index': i,
                'price': df['high'].iloc[i],
                'timestamp': df.index[i]
            })
        if df['low'].iloc[i] == lows.iloc[i]:
            pivot_lows.append({
                'index': i,
                'price': df['low'].iloc[i],
                'timestamp': df.index[i]
            })
    
    return pivot_highs, pivot_lows

def calculate_trendline(df, pivot_points, direction='up', lookback=20):
    """추세선 계산"""
    if len(pivot_points) < 2:
        return None
    
    # 최근 lookback 기간 내의 피벗 포인트만 사용
    recent_pivots = [p for p in pivot_points if p['index'] >= len(df) - lookback]
    
    if len(recent_pivots) < 2:
        return None
    
    # 선형 회귀로 추세선 계산
    x = np.array([p['index'] for p in recent_pivots])
    if direction == 'up':
        y = np.array([p['price'] for p in recent_pivots])
    else:
        y = np.array([p['price'] for p in recent_pivots])
    
    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept

def check_trendline_breakout(df, trendline, current_price, direction='up'):
    """추세선 돌파 확인"""
    if trendline is None:
        return False
    
    slope, intercept = trendline
    # 현재 시점에서의 추세선 값
    current_index = len(df) - 1
    trendline_value = slope * current_index + intercept
    
    if direction == 'up':
        # 상향 돌파: 가격이 추세선 위로
        return current_price > trendline_value
    else:
        # 하향 돌파: 가격이 추세선 아래로
        return current_price < trendline_value

def rsi_strategy(df, current_index=None, params=None, has_position=False):
    """RSI 기반 매매 전략 (파라미터 기반) with risk management"""
    # 기본 파라미터 설정
    default_params = {
        'rsi_buy': 30,           # RSI 매수 조건
        'rsi_sell': 70,          # RSI 매도 조건
        'stop_loss': -0.015,     # 손절 비율
        'take_profit': 0.03,     # 익절 비율
        'max_hold_hours': 24,    # 최대 보유 시간
        'volume_ratio': 0.8,     # 거래량 비율
        'support_distance': 0.02 # 지지선 거리
    }
    
    # 파라미터 병합
    if params is None:
        params = {}
    strategy_params = {**default_params, **params}
    
    # 백테스팅을 위한 인덱스 처리
    if current_index is None:
        current_index = len(df) - 1
    
    # RSI 계산을 위한 최소 데이터 필요량
    min_required = 20  # RSI 14 + 기본 계산용
    
    if len(df) < min_required or current_index < min_required:
        return 'HOLD', None
    
    # 현재 시점까지만 데이터 사용 (미래 데이터 사용 방지)
    current_df = df.iloc[:current_index + 1]
    
    # RSI 계산
    rsi = calculate_rsi(current_df['close'], period=14)
    current_rsi = rsi.iloc[-1]
    
    # NaN 체크
    if pd.isna(current_rsi):
        return 'HOLD', None
    
    # RSI 모멘텀 계산 (RSI 변화율)
    rsi_momentum = 0
    if len(rsi) >= 2:
        rsi_momentum = rsi.iloc[-1] - rsi.iloc[-2]
    
    # 피벗 포인트 찾기
    pivot_highs, pivot_lows = find_pivot_points(current_df, window=5)
    
    # 지지/저항선 계산
    support_level = calculate_support_level(current_df, pivot_lows, lookback=10)
    resistance_level = calculate_resistance_level(current_df, pivot_highs, lookback=10)
    
    # 추세선 계산
    up_trendline = calculate_trendline(current_df, pivot_lows, direction='up', lookback=10)
    down_trendline = calculate_trendline(current_df, pivot_highs, direction='down', lookback=10)
    
    current_price = current_df['close'].iloc[-1]
    
    # 거래량 확인 (추가 필터)
    volume_avg = current_df['volume'].rolling(window=20).mean().iloc[-1]
    current_volume = current_df['volume'].iloc[-1]
    volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1
    
    # 포지션이 있을 때는 매수하지 않음 (엄격한 체크)
    if has_position:
        # 매도 조건: RSI > rsi_sell
        if current_rsi > strategy_params['rsi_sell']:
            return 'SELL', '신호매도'
        else:
            return 'HOLD', None
    else:
        # 포지션이 없을 때만 매수 신호 생성 (엄격한 체크)
        # 매수 조건: RSI < rsi_buy + 추가 필터
        if current_rsi < strategy_params['rsi_buy']:
            # 추가 필터: RSI 모멘텀 확인 (상승 모멘텀)
            if rsi_momentum > 0:
                # 지지선 근처에서 매수 (추가 필터)
                if support_level and current_price <= support_level * (1 + strategy_params['support_distance']):
                    # 거래량 확인 (추가 필터)
                    if volume_ratio > strategy_params['volume_ratio']:
                        print(f"🔍 RSI 전략 매수 신호 생성: RSI={current_rsi:.2f}, 모멘텀={rsi_momentum:.2f}, 지지선={support_level:.4f}, 거래량비율={volume_ratio:.2f}")
                        return 'BUY', None
        # 모든 조건을 만족하지 않으면 HOLD
        return 'HOLD', None
    
    # 기본 반환값 (모든 경우를 커버)
    return 'HOLD', None

def calculate_support_level(df, pivot_lows, lookback=10):
    """지지선 계산"""
    if len(pivot_lows) < 2:
        return None
    
    # 최근 피벗 로우들 중에서 지지선 찾기
    recent_lows = [low for low in pivot_lows if low['index'] >= len(df) - lookback]
    if not recent_lows:
        return None
    
    # 가장 최근의 주요 지지선 반환
    return recent_lows[-1]['price'] if recent_lows else None

def calculate_resistance_level(df, pivot_highs, lookback=10):
    """저항선 계산"""
    if len(pivot_highs) < 2:
        return None
    
    # 최근 피벗 하이들 중에서 저항선 찾기
    recent_highs = [high for high in pivot_highs if high['index'] >= len(df) - lookback]
    if not recent_highs:
        return None
    
    # 가장 최근의 주요 저항선 반환
    return recent_highs[-1]['price'] if recent_highs else None

def execute_strategy(symbol='BTC/USDT:USDT', position_ratio=0.3, timeframe='1h', strategy='ma', params=None):
    """전략 실행"""
    df = get_price_data(symbol, timeframe=timeframe)
    if df is None:
        return
    
    # 포지션 상태 확인 (실시간 거래에서는 별도로 관리)
    has_position = False  # 실시간 거래에서는 별도로 관리
    
    # 전략 선택
    if strategy == 'ma':
        signal, exit_reason = simple_ma_strategy(df, has_position=has_position, params=params)
        strategy_name = "이동평균 크로스오버"
    elif strategy == 'rsi':
        signal, exit_reason = rsi_strategy(df, has_position=has_position, params=params)
        strategy_name = "RSI + 추세선 돌파 (고급 필터)"
    else:
        signal, exit_reason = simple_ma_strategy(df, has_position=has_position, params=params)  # 기본값
        strategy_name = "이동평균 크로스오버"
    
    current_price = df['close'].iloc[-1]
    print(f"현재 가격: {current_price}")
    print(f"전략: {strategy_name}")
    print(f"현재 신호: {signal}")
    
    if signal == 'BUY':
        print("롱 포지션 진입")
        
        # 잔고 확인 및 거래 수량 계산
        try:
            balance = binance.fetchBalance()
            available_usdt = balance['USDT']['free']
            trade_amount = available_usdt * position_ratio  # 설정된 비율 사용
            
            # 최소 거래량 확인
            if trade_amount < 50:  # 최소 $50
                print(f"잔고 부족: ${available_usdt:.2f} (최소 $50 필요)")
                return
                
            position_size = trade_amount / current_price
            
            # 바이낸스 최소 거래량 확인 (0.001 BTC)
            if position_size < 0.001:
                position_size = 0.001
                trade_amount = position_size * current_price
                
            print(f"거래 금액: ${trade_amount:.2f} (잔고의 {position_ratio*100:.0f}%)")
            print(f"거래 수량: {position_size:.4f}")
            
            order = binance.create_market_buy_order(symbol, position_size)
            print(f"롱 포지션 진입: {order['id']}")
            
            # 거래 추적기에 추가
            if 'average' in order and order['average']:
                trading_tracker.add_trade('BUY', symbol, position_size, order['average'], order['id'])
            elif 'price' in order and order['price']:
                trading_tracker.add_trade('BUY', symbol, position_size, order['price'], order['id'])
                
        except Exception as e:
            print(f"롱 포지션 진입 실패: {e}")

    elif signal == 'SELL':
        print("숏 포지션 진입")
        
        # 잔고 확인 및 거래 수량 계산
        try:
            balance = binance.fetchBalance()
            available_usdt = balance['USDT']['free']
            trade_amount = available_usdt * position_ratio  # 설정된 비율 사용
            
            # 최소 거래량 확인
            if trade_amount < 50:  # 최소 $50
                print(f"잔고 부족: ${available_usdt:.2f} (최소 $50 필요)")
                return
                
            position_size = trade_amount / current_price
            
            # 바이낸스 최소 거래량 확인 (0.001 BTC)
            if position_size < 0.001:
                position_size = 0.001
                trade_amount = position_size * current_price
                
            print(f"거래 금액: ${trade_amount:.2f} (잔고의 {position_ratio*100:.0f}%)")
            print(f"거래 수량: {position_size:.4f}")
            
            order = binance.create_market_sell_order(symbol, position_size)
            print(f"숏 포지션 진입: {order['id']}")
            
            # 거래 추적기에 추가
            if 'average' in order and order['average']:
                trading_tracker.add_trade('SELL', symbol, position_size, order['average'], order['id'])
            elif 'price' in order and order['price']:
                trading_tracker.add_trade('SELL', symbol, position_size, order['price'], order['id'])
                
        except Exception as e:
            print(f"숏 포지션 진입 실패: {e}")

def get_strategy_settings():
    """전략 설정을 사용자로부터 입력받는 함수"""
    print("\n" + "="*50)
    print("🎯 전략 선택")
    print("="*50)
    
    # 기존 최적화 결과 확인
    optimizer = StrategyOptimizer()
    rsi_optimized = optimizer.load_latest_optimization('rsi')
    ma_optimized = optimizer.load_latest_optimization('ma')
    
    print("\n📊 사용할 전략을 선택하세요:")
    print("1. 이동평균 크로스오버 (MA5/MA20)")
    if ma_optimized:
        is_relaxed = "_relaxed" in ma_optimized['strategy']
        opt_type = "완화된 조건" if is_relaxed else "일반"
        print(f"   📂 최적화됨 ({opt_type}): {ma_optimized['best_result']['total_return']:.2f}% 수익률")
    print("2. RSI + 추세선 돌파 (고급 필터)")
    if rsi_optimized:
        is_relaxed = "_relaxed" in rsi_optimized['strategy']
        opt_type = "완화된 조건" if is_relaxed else "일반"
        print(f"   📂 최적화됨 ({opt_type}): {rsi_optimized['best_result']['total_return']:.2f}% 수익률")
    print("3. 전략 최적화 (자동 파라미터 튜닝)")
    print("4. 최적화된 전략 자동 선택")
    
    try:
        strategy_choice = int(input("\n번호를 입력하세요 (1-4): "))
        
        if strategy_choice == 1:
            strategy = 'ma'
            strategy_name = "이동평균 크로스오버"
            
            # 최적화된 파라미터가 있으면 사용
            if ma_optimized:
                is_relaxed = "_relaxed" in ma_optimized['strategy']
                opt_type = "완화된 조건" if is_relaxed else "일반"
                print(f"✅ {opt_type} 최적화된 파라미터를 사용합니다!")
                params = ma_optimized['best_params']
                strategy_name = f"이동평균 크로스오버 ({opt_type} 최적화됨)"
            else:
                # 기본 파라미터
                params = {
                    'stop_loss': -0.02,      # -2%
                    'take_profit': 0.03,     # +3%
                    'max_hold_hours': 24
                }
                
        elif strategy_choice == 2:
            strategy = 'rsi'
            strategy_name = "RSI + 추세선 돌파 (고급 필터)"
            
            # 최적화된 파라미터가 있으면 사용
            if rsi_optimized:
                is_relaxed = "_relaxed" in rsi_optimized['strategy']
                opt_type = "완화된 조건" if is_relaxed else "일반"
                print(f"✅ {opt_type} 최적화된 파라미터를 사용합니다!")
                params = rsi_optimized['best_params']
                strategy_name = f"RSI + 추세선 돌파 ({opt_type} 최적화됨)"
            else:
                # 기본 파라미터
                params = {
                    'stop_loss': -0.015,     # -1.5%
                    'take_profit': 0.03,     # +3%
                    'max_hold_hours': 24     # 24시간
                }
                
        elif strategy_choice == 3:
            # 전략 최적화 실행
            return run_strategy_optimization()
            
        elif strategy_choice == 4:
            # 최적화된 전략 자동 선택
            if rsi_optimized and ma_optimized:
                # 더 좋은 성과를 보인 전략 선택
                if rsi_optimized['best_result']['total_return'] > ma_optimized['best_result']['total_return']:
                    strategy = 'rsi'
                    is_relaxed = "_relaxed" in rsi_optimized['strategy']
                    opt_type = "완화된 조건" if is_relaxed else "일반"
                    strategy_name = f"RSI + 추세선 돌파 ({opt_type} 최적화됨)"
                    params = rsi_optimized['best_params']
                    print(f"✅ RSI 전략이 더 좋은 성과를 보여 자동 선택되었습니다! ({opt_type})")
                else:
                    strategy = 'ma'
                    is_relaxed = "_relaxed" in ma_optimized['strategy']
                    opt_type = "완화된 조건" if is_relaxed else "일반"
                    strategy_name = f"이동평균 크로스오버 ({opt_type} 최적화됨)"
                    params = ma_optimized['best_params']
                    print(f"✅ 이동평균 전략이 더 좋은 성과를 보여 자동 선택되었습니다! ({opt_type})")
            elif rsi_optimized:
                strategy = 'rsi'
                is_relaxed = "_relaxed" in rsi_optimized['strategy']
                opt_type = "완화된 조건" if is_relaxed else "일반"
                strategy_name = f"RSI + 추세선 돌파 ({opt_type} 최적화됨)"
                params = rsi_optimized['best_params']
                print(f"✅ RSI 전략 최적화 결과를 사용합니다! ({opt_type})")
            elif ma_optimized:
                strategy = 'ma'
                is_relaxed = "_relaxed" in ma_optimized['strategy']
                opt_type = "완화된 조건" if is_relaxed else "일반"
                strategy_name = f"이동평균 크로스오버 ({opt_type} 최적화됨)"
                params = ma_optimized['best_params']
                print(f"✅ 이동평균 전략 최적화 결과를 사용합니다! ({opt_type})")
            else:
                print("❌ 최적화된 전략이 없습니다. 기본 전략을 사용합니다.")
                strategy = 'ma'
                strategy_name = "이동평균 크로스오버"
                params = {
                    'stop_loss': -0.02,
                    'take_profit': 0.03,
                    'max_hold_hours': 24
                }
        else:
            print("잘못된 선택입니다. 이동평균 전략으로 설정합니다.")
            strategy = 'ma'
            strategy_name = "이동평균 크로스오버"
            params = {
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
            
        print(f"선택된 전략: {strategy_name}")
        print(f"손절매: {params['stop_loss']*100:.1f}%")
        print(f"익절매: {params['take_profit']*100:.1f}%")
        if 'max_hold_hours' in params:
            print(f"최대 보유: {params['max_hold_hours']}시간")
        
    except ValueError:
        print("숫자를 입력해주세요. 이동평균 전략으로 설정합니다.")
        strategy = 'ma'
        strategy_name = "이동평균 크로스오버"
        params = {
            'stop_loss': -0.02,
            'take_profit': 0.03,
            'max_hold_hours': 24
        }
    
    print("\n" + "="*50)
    print(f"✅ 최종 설정: {strategy_name}")
    print("="*50)
    
    return strategy, strategy_name, params

def run_strategy_optimization():
    """전략 최적화 실행"""
    print("\n" + "="*60)
    print("🔧 전략 최적화 시스템")
    print("="*60)
    
    # 최적화할 전략 선택
    print("\n📊 최적화할 전략을 선택하세요:")
    print("1. RSI 전략 최적화")
    print("2. 이동평균 전략 최적화")
    
    try:
        strategy_choice = int(input("\n번호를 입력하세요 (1-2): "))
        
        if strategy_choice == 1:
            strategy = 'rsi'
            strategy_name = "RSI 전략"
        elif strategy_choice == 2:
            strategy = 'ma'
            strategy_name = "이동평균 전략"
        else:
            print("잘못된 선택입니다. RSI 전략으로 설정합니다.")
            strategy = 'rsi'
            strategy_name = "RSI 전략"
    except ValueError:
        print("숫자를 입력해주세요. RSI 전략으로 설정합니다.")
        strategy = 'rsi'
        strategy_name = "RSI 전략"
    
    # 최적화 설정
    print(f"\n🎯 {strategy_name} 최적화 설정")
    
    try:
        optimization_days = int(input("최적화 기간 (일): ") or "7")
        max_combinations = int(input("최대 테스트 조합 수: ") or "50")
    except ValueError:
        print("기본값을 사용합니다.")
        optimization_days = 7
        max_combinations = 50
    
    # 코인 선택
    print("\n📈 최적화할 코인을 선택하세요:")
    print("1. BTC/USDT")
    print("2. ETH/USDT")
    print("3. 고변동성 코인 자동 선택")
    
    try:
        coin_choice = int(input("\n번호를 입력하세요 (1-3): "))
        
        if coin_choice == 1:
            symbol = 'BTC/USDT:USDT'
        elif coin_choice == 2:
            symbol = 'ETH/USDT:USDT'
        elif coin_choice == 3:
            # 고변동성 코인 자동 선택
            volatile_coins = get_volatile_coins(min_volume=1000000, min_volatility=0.02, top_n=5)
            if volatile_coins:
                print("\n🔍 고변동성 코인 목록:")
                for i, coin in enumerate(volatile_coins, 1):
                    print(f"{i}. {coin['symbol']} (변동성: {coin['volatility']:.2%})")
                try:
                    coin_idx = int(input("\n번호를 선택하세요: ")) - 1
                    if 0 <= coin_idx < len(volatile_coins):
                        # 이미 올바른 형식으로 반환되므로 그대로 사용
                        symbol = volatile_coins[coin_idx]['symbol']
                    else:
                        symbol = 'BTC/USDT:USDT'
                except ValueError:
                    symbol = 'BTC/USDT:USDT'
            else:
                symbol = 'BTC/USDT:USDT'
        else:
            symbol = 'BTC/USDT:USDT'
    except ValueError:
        symbol = 'BTC/USDT:USDT'
    
    # 타임프레임 선택
    print("\n⏰ 타임프레임을 선택하세요:")
    print("1. 1분봉")
    print("2. 5분봉")
    print("3. 15분봉")
    print("4. 1시간봉")
    
    try:
        tf_choice = int(input("\n번호를 입력하세요 (1-4): "))
        
        if tf_choice == 1:
            timeframe = '1m'
        elif tf_choice == 2:
            timeframe = '5m'
        elif tf_choice == 3:
            timeframe = '15m'
        elif tf_choice == 4:
            timeframe = '1h'
        else:
            timeframe = '5m'
    except ValueError:
        timeframe = '5m'
    
    print(f"\n🚀 최적화 시작!")
    print(f"전략: {strategy_name}")
    print(f"코인: {symbol}")
    print(f"타임프레임: {timeframe}")
    print(f"최적화 기간: {optimization_days}일")
    print(f"최대 조합 수: {max_combinations}")
    
    # 전략 최적화 실행
    optimizer = StrategyOptimizer()
    
    # 기존 최적화 결과 확인
    existing_result = optimizer.load_latest_optimization(strategy)
    
    if existing_result:
        print(f"\n📂 기존 최적화 결과를 발견했습니다!")
        print(f"🏆 기존 최고 성과: {existing_result['best_result']['total_return']:.2f}%")
        print(f"📅 최적화 날짜: {existing_result['timestamp'][:10]}")
        
        use_existing = input("\n기존 결과를 사용하시겠습니까? (y/n): ").lower().strip()
        
        if use_existing == 'y':
            print("✅ 기존 최적화 결과를 사용합니다.")
            return strategy, strategy_name, existing_result['best_params']
        else:
            print("🔄 새로운 최적화를 실행합니다.")
    
    # 새로운 최적화 실행
    results = optimizer.optimize_strategy(
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        optimization_days=optimization_days,
        max_combinations=max_combinations
    )
    
    if results and results.get('best_params'):
        # 최적화 결과 출력
        optimizer.print_optimization_summary(results)
        
        # 최적화된 파라미터로 전략 반환
        best_params = results['best_params']
        strategy_name = f"{strategy_name} (최적화됨)"
        
        print(f"\n✅ 최적화 완료! 최적 파라미터로 전략을 설정합니다.")
        
        return strategy, strategy_name, best_params
    else:
        print("\n⚠️ 최적화 결과가 부족합니다. 기본 파라미터를 사용합니다.")
        
        if strategy == 'rsi':
            default_params = {
                'rsi_buy': 30,
                'rsi_sell': 70,
                'stop_loss': -0.015,
                'take_profit': 0.03,
                'max_hold_hours': 24,
                'volume_ratio': 0.8,
                'support_distance': 0.02
            }
        else:
            default_params = {
                'short_period': 5,
                'long_period': 20,
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        
        return strategy, strategy_name, default_params

class TradingTracker:
    """거래 내역 추적 및 성과 분석 클래스"""
    
    def __init__(self):
        self.trades = []
        self.initial_balance = None
        self.current_balance = None
        self.start_time = datetime.now()
        
    def add_trade(self, trade_type, symbol, amount, price, order_id):
        """거래 내역 추가"""
        trade = {
            'timestamp': datetime.now().isoformat(),
            'type': trade_type,  # 'BUY' or 'SELL'
            'symbol': symbol,
            'amount': amount,
            'price': price,
            'order_id': order_id,
            'value': amount * price
        }
        self.trades.append(trade)
        print(f"거래 기록: {trade_type} {amount} {symbol} @ ${price:,.2f}")
        
    def set_initial_balance(self, balance):
        """초기 잔고 설정"""
        self.initial_balance = balance
        
    def set_current_balance(self, balance):
        """현재 잔고 설정"""
        self.current_balance = balance
        
    def calculate_performance(self):
        """성과 계산"""
        if not self.trades:
            return None
            
        # 기본 통계
        total_trades = len(self.trades)
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        
        # 수익률 계산
        total_buy_value = sum(t['value'] for t in buy_trades)
        total_sell_value = sum(t['value'] for t in sell_trades)
        
        # P&L 계산
        if total_buy_value > 0 and total_sell_value > 0:
            pnl = total_sell_value - total_buy_value
            pnl_percentage = (pnl / total_buy_value) * 100
        else:
            pnl = 0
            pnl_percentage = 0
            
        # 거래 통계
        avg_trade_value = sum(t['value'] for t in self.trades) / total_trades
        
        # 시간 통계
        trading_duration = datetime.now() - self.start_time
        trades_per_hour = total_trades / (trading_duration.total_seconds() / 3600) if trading_duration.total_seconds() > 0 else 0
        
        return {
            'total_trades': total_trades,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'pnl': pnl,
            'pnl_percentage': pnl_percentage,
            'avg_trade_value': avg_trade_value,
            'trading_duration': trading_duration,
            'trades_per_hour': trades_per_hour,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance
        }
        
    def print_performance_report(self):
        """성과 리포트 출력"""
        performance = self.calculate_performance()
        if not performance:
            print("거래 내역이 없습니다.")
            return
            
        print("\n" + "="*80)
        print("📊 거래 성과 리포트 📊")
        print("="*80)
        
        # 기본 정보
        print(f"거래 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"거래 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"총 거래 시간: {performance['trading_duration']}")
        print()
        
        # 거래 통계
        print("📈 거래 통계:")
        print(f"  총 거래 횟수: {performance['total_trades']}회")
        print(f"  매수 거래: {performance['buy_trades']}회")
        print(f"  매도 거래: {performance['sell_trades']}회")
        print(f"  시간당 거래: {performance['trades_per_hour']:.1f}회")
        print()
        
        # 금액 통계
        print("💰 금액 통계:")
        print(f"  총 매수 금액: ${performance['total_buy_value']:,.2f}")
        print(f"  총 매도 금액: ${performance['total_sell_value']:,.2f}")
        print(f"  평균 거래 금액: ${performance['avg_trade_value']:,.2f}")
        print()
        
        # 수익률
        print("📊 수익률:")
        if performance['pnl'] >= 0:
            print(f"  총 수익: +${performance['pnl']:,.2f} (+{performance['pnl_percentage']:+.2f}%)")
        else:
            print(f"  총 손실: ${performance['pnl']:,.2f} ({performance['pnl_percentage']:+.2f}%)")
        print()
        
        # 잔고 변화
        if performance['initial_balance'] and performance['current_balance']:
            balance_change = performance['current_balance'] - performance['initial_balance']
            balance_change_pct = (balance_change / performance['initial_balance']) * 100
            print("🏦 잔고 변화:")
            print(f"  초기 잔고: ${performance['initial_balance']:,.2f}")
            print(f"  현재 잔고: ${performance['current_balance']:,.2f}")
            if balance_change >= 0:
                print(f"  잔고 변화: +${balance_change:,.2f} (+{balance_change_pct:+.2f}%)")
            else:
                print(f"  잔고 변화: ${balance_change:,.2f} ({balance_change_pct:+.2f}%)")
            print()
        
        # 상세 거래 내역
        print("📋 상세 거래 내역:")
        print(f"{'시간':<20} {'타입':<6} {'심볼':<15} {'수량':<10} {'가격':<12} {'금액':<12}")
        print("-"*80)
        for trade in self.trades:
            time_str = datetime.fromisoformat(trade['timestamp']).strftime('%H:%M:%S')
            trade_type = trade['type']
            symbol = trade['symbol'].replace(':USDT', '')
            amount = f"{trade['amount']:.4f}"
            price = f"${trade['price']:,.2f}"
            value = f"${trade['value']:,.2f}"
            print(f"{time_str:<20} {trade_type:<6} {symbol:<15} {amount:<10} {price:<12} {value:<12}")
        
        print("="*80)
    
    def save_trading_log(self):
        """거래 로그를 파일로 저장"""
        if not self.trades:
            print("저장할 거래 내역이 없습니다.")
            return
        
        filename = f"trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'trades': self.trades,
            'performance': self.calculate_performance()
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 거래 로그 저장: {filename}")
        except Exception as e:
            print(f"❌ 거래 로그 저장 실패: {e}")
    
    def save_daily_report(self):
        """24시간 거래 결과를 파일로 저장"""
        performance = self.calculate_performance()
        if not performance:
            return
        
        filename = f"daily_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'performance': performance,
            'trades_count': len(self.trades),
            'trading_duration': str(performance['trading_duration'])
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 24시간 거래 결과 저장: {filename}")
        except Exception as e:
            print(f"❌ 24시간 결과 저장 실패: {e}")

class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(self, initial_balance=10000, balance_ratio=0.3, commission=0.0004, leverage=1):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.balance_ratio = balance_ratio  # 잔고의 30% 사용
        self.commission = commission  # 바이낸스 선물 수수료 0.04%
        self.leverage = leverage  # 레버리지
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
    def reset(self):
        """백테스트 초기화"""
        self.balance = self.initial_balance
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
    def execute_trade(self, signal, price, timestamp, symbol, exit_reason=None):
        """거래 실행 - 단일 포지션 관리 방식 (레버리지 단순화)"""
        if signal == 'BUY':
            # 이미 포지션이 있으면 매수하지 않음 (추격매수 방지)
            if self.positions:
                print(f"🚫 매수 거부: 이미 포지션이 {len(self.positions)}개 존재")
                return False
                
            # 거래 수량 계산 (레버리지 고려)
            available_balance = self.balance * self.balance_ratio
            
            # 레버리지를 고려한 포지션 크기
            position_value = available_balance * self.leverage
            position_size = position_value / price
            
            # 최소 거래량 확인 (0.001 BTC)
            if position_size < 0.001:
                position_size = 0.001
                position_value = position_size * price
            
            # 실제 차감될 증거금
            margin_required = position_value / self.leverage
            
            # 수수료 계산
            commission_cost = position_value * self.commission
            
            # 총 차감 금액
            total_cost = margin_required + commission_cost
            
            if self.balance >= total_cost:
                self.balance -= total_cost
                
                trade = {
                    'timestamp': timestamp,
                    'type': 'BUY',
                    'symbol': symbol,
                    'price': price,
                    'amount': position_size,
                    'value': position_value,
                    'margin': margin_required,
                    'commission': commission_cost,
                    'balance': self.balance,
                    'exit_reason': exit_reason if exit_reason else None
                }
                self.trades.append(trade)
                
                # 단일 포지션으로 관리
                self.positions = [{
                    'type': 'LONG',
                    'symbol': symbol,
                    'amount': position_size,
                    'price': price,
                    'timestamp': timestamp,
                    'max_hold_time': timestamp + pd.Timedelta(hours=24),
                    'margin': margin_required
                }]
                
                print(f"💰 매수 완료: ${self.balance:,.2f} (수량: {position_size:.4f}, 레버리지: {self.leverage}x)")
                return True
                
        elif signal == 'SELL' and self.positions:
            # 단일 포지션 매도
            position = self.positions[0]
            position_amount = position['amount']
            entry_price = position['price']
            entry_margin = position['margin']
            
            # 수수료 계산
            current_position_value = position_amount * price
            commission_cost = current_position_value * self.commission
            
            # 레버리지 P&L 계산 (단순화)
            price_change_pct = (price - entry_price) / entry_price
            leveraged_pnl = entry_margin * price_change_pct * self.leverage
            
            # 총 반환 금액
            total_return = entry_margin + leveraged_pnl - commission_cost
            
            self.balance += total_return
            
            # 수익률 계산
            pnl_percentage = (leveraged_pnl / entry_margin) * 100 if entry_margin > 0 else 0
            
            trade = {
                'timestamp': timestamp,
                'type': 'SELL',
                'symbol': symbol,
                'price': price,
                'amount': position_amount,
                'value': current_position_value,
                'commission': commission_cost,
                'pnl': leveraged_pnl,
                'pnl_percentage': pnl_percentage,
                'balance': self.balance,
                'exit_reason': exit_reason if exit_reason else '신호매도'
            }
            self.trades.append(trade)
            
            # 포지션 제거
            self.positions = []
            
            print(f"💰 매도 완료: ${self.balance:,.2f} (P&L: ${leveraged_pnl:+.2f}, 수량: {position_amount:.4f})")
            return True
            
        return False
    
    def calculate_equity(self, current_price, timestamp):
        """현재 자산 가치 계산 (레버리지 단순화)"""
        total_equity = self.balance
        
        # 미결 포지션 가치 추가 (레버리지 고려)
        for position in self.positions:
            # 레버리지를 고려한 미결 포지션 가치 (단순화)
            # 마지막 가격은 진입가로 대체 (임시)
            last_price = position['price']
            price_change_pct = (last_price - position['price']) / position['price']
            unrealized_pnl = position['margin'] * price_change_pct * self.leverage
            position_equity = position['margin'] + unrealized_pnl
            total_equity += position_equity
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': total_equity,
            'balance': self.balance,
            'positions_value': total_equity - self.balance
        })
        
        return total_equity
    
    def run_backtest(self, df, symbol, timeframe='1h', strategy='ma', params=None):
        """백테스트 실행"""
        print(f"🔍 백테스트 시작 - 포지션 상태: 없음")
        
        # 파라미터 설정
        if params is None:
            params = {}
        
        # 전략별 기본 파라미터 설정
        if strategy == 'rsi':
            default_params = {
                'stop_loss': -0.015,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        elif strategy == 'ma':
            default_params = {
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        else:
            default_params = {
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        
        # 파라미터 병합
        strategy_params = {**default_params, **params}
        
        # 워밍업 기간 (이동평균 계산용)
        warmup_period = 20
        
        for i in range(warmup_period, len(df)):
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            current_time = current_candle.name
            
            # 포지션 상태 확인
            has_position = len(self.positions) > 0
            
            # 디버깅: 포지션 상태 출력 (처음 몇 개만)
            if i < warmup_period + 10:
                print(f"🔍 캔들 {i}: {current_time} - 포지션: {len(self.positions)}개, has_position: {has_position}")
            
            # 리스크 관리 체크 (포지션이 있을 때만)
            if has_position:
                positions_to_sell = self.check_risk_management(current_price, current_time, strategy_params)
                if positions_to_sell:
                    for pos_idx, reason, amount in positions_to_sell:
                        self.execute_trade('SELL', current_price, current_time, symbol, reason)
                        # 리스크 관리 실행 시 전략 신호 무시
                        continue
            
            # 전략 신호 생성
            if strategy == 'ma':
                signal, exit_reason = simple_ma_strategy(df, i, params, has_position)
            elif strategy == 'rsi':
                signal, exit_reason = rsi_strategy(df, i, params, has_position)
            else:
                signal, exit_reason = simple_ma_strategy(df, i, params, has_position)
            
            # 거래 실행
            if signal == 'BUY' and not has_position:
                self.execute_trade('BUY', current_price, current_time, symbol)
            elif signal == 'SELL' and has_position:
                self.execute_trade('SELL', current_price, current_time, symbol, exit_reason)
            
            # 자산 가치 계산
            self.calculate_equity(current_price, current_time)
        
        # 최종 청산 (미결 포지션이 있는 경우)
        if self.positions:
            final_price = df['close'].iloc[-1]
            final_time = df.index[-1]
            for position in self.positions:
                self.execute_trade('SELL', final_price, final_time, symbol, '최종청산')
        
        print(f"✅ 백테스트 완료 - 총 거래: {len(self.trades)}회")

    def check_risk_management(self, current_price, current_time, params):
        """단일 포지션 리스크 관리 체크 (파라미터 기반)"""
        positions_to_sell = []
        
        # 단일 포지션만 체크
        if self.positions:
            position = self.positions[0]  # 유일한 포지션
            entry_price = position['price']
            position_amount = position['amount']
            
            # 손절 체크
            stop_loss_threshold = 1 + params.get('stop_loss', -0.02)
            if current_price <= entry_price * stop_loss_threshold:
                positions_to_sell.append((0, '손절', position_amount))
            # 익절 체크
            elif current_price >= entry_price * (1 + params.get('take_profit', 0.03)):
                positions_to_sell.append((0, '익절', position_amount))
            # 최대 보유 시간 체크
            elif current_time >= position['max_hold_time']:
                positions_to_sell.append((0, '시간초과', position_amount))
        
        return positions_to_sell
    
    def generate_backtest_report(self):
        """백테스트 리포트 생성"""
        if not self.trades:
            return None
            
        # 기본 통계
        total_trades = len(self.trades)
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        
        # 수익률 계산
        total_pnl = sum(t.get('pnl', 0) for t in sell_trades)
        total_commission = sum(t['commission'] for t in self.trades)
        
        # 최종 자산 (미결 포지션 가치 포함, 레버리지 단순화)
        final_equity = self.balance
        # 미결 포지션 가치 추가 (레버리지 고려)
        for position in self.positions:
            # 레버리지를 고려한 미결 포지션 가치 (단순화)
            # 마지막 가격은 진입가로 대체 (임시)
            last_price = position['price']
            price_change_pct = (last_price - position['price']) / position['price']
            unrealized_pnl = position['margin'] * price_change_pct * self.leverage
            position_equity = position['margin'] + unrealized_pnl
            final_equity += position_equity
        
        total_return = final_equity - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100
        
        # 승률 계산 (최종청산 제외)
        completed_trades = [t for t in sell_trades if t.get('exit_reason') != '최종청산']
        profitable_trades = len([t for t in completed_trades if t.get('pnl', 0) > 0])
        win_rate = (profitable_trades / len(completed_trades)) * 100 if completed_trades else 0
        
        # 최대 낙폭 (MDD) 계산
        peak = self.initial_balance
        mdd = 0
        for equity_data in self.equity_curve:
            equity = equity_data['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > mdd:
                mdd = drawdown
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_commission': total_commission,
            'max_drawdown': mdd,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def print_backtest_report(self, report):
        """백테스트 리포트 출력"""
        if not report:
            print("거래 내역이 없습니다.")
            return
            
        print("\n" + "="*80)
        print("🔬 백테스트 결과 리포트 🔬")
        print("="*80)
        
        # 기본 성과
        print("📊 기본 성과:")
        print(f"  초기 자본: ${report['initial_balance']:,.2f}")
        print(f"  최종 자본: ${report['final_balance']:,.2f}")
        if report['total_return'] >= 0:
            print(f"  총 수익: +${report['total_return']:,.2f} (+{report['total_return_pct']:+.2f}%)")
        else:
            print(f"  총 손실: ${report['total_return']:,.2f} ({report['total_return_pct']:+.2f}%)")
        print()
        
        # 거래 통계
        completed_sells = [t for t in report['trades'] if t['type'] == 'SELL' and t.get('exit_reason') != '최종청산']
        final_sells = [t for t in report['trades'] if t['type'] == 'SELL' and t.get('exit_reason') == '최종청산']
        
        print("📈 거래 통계:")
        print(f"  총 거래 횟수: {report['total_trades']}회")
        print(f"  매수 거래: {report['buy_trades']}회")
        print(f"  매도 거래: {report['sell_trades']}회 (완료: {len(completed_sells)}회, 최종청산: {len(final_sells)}회)")
        print(f"  승률: {report['win_rate']:.1f}% (완료 거래 기준)")
        
        # 최종 포지션 상태 확인
        if final_sells:
            print(f"  ⚠️ 최종청산 거래: {len(final_sells)}회 (백테스팅 종료 시 미결 포지션)")
        print()
        
        # 수익률 분석
        print("💰 수익률 분석:")
        print(f"  총 P&L: ${report['total_pnl']:,.2f}")
        print(f"  총 수수료: ${report['total_commission']:,.2f}")
        print(f"  최대 낙폭 (MDD): {report['max_drawdown']:.2f}%")
        print()
        
        # 상세 거래 내역
        print("📋 상세 거래 내역:")
        print(f"{'시간':<20} {'타입':<6} {'가격':<12} {'수량':<10} {'P&L':<12} {'잔고':<12} {'사유':<10}")
        print("-"*90)
        
        for trade in report['trades']:
            time_str = trade['timestamp'].strftime('%m-%d %H:%M')
            trade_type = trade['type']
            price = f"${trade['price']:,.2f}"
            amount = f"{trade['amount']:.4f}"
            
            if trade_type == 'SELL':
                pnl = f"${trade.get('pnl', 0):+.2f}"
                exit_reason = trade.get('exit_reason', '신호매도')
                # None 값 처리
                if exit_reason is None:
                    exit_reason = '신호매도'
            else:
                pnl = "-"
                exit_reason = "-"
                
            balance = f"${trade['balance']:,.2f}"
            print(f"{time_str:<20} {trade_type:<6} {price:<12} {amount:<10} {pnl:<12} {balance:<12} {exit_reason:<10}")
        
        print("="*90)

    def run_backtest_vectorized(self, df, symbol, timeframe='1h', strategy='ma', params=None):
        """벡터화된 백테스트 실행 (훨씬 빠름)"""
        print(f"🔍 벡터화 백테스트 시작")
        
        # 파라미터 설정
        if params is None:
            params = {}
        
        # 전략별 기본 파라미터 설정
        if strategy == 'rsi':
            default_params = {
                'rsi_buy': 30,
                'rsi_sell': 70,
                'stop_loss': -0.015,
                'take_profit': 0.03,
                'max_hold_hours': 24,
                'volume_ratio': 0.8,
                'support_distance': 0.02
            }
        elif strategy == 'ma':
            default_params = {
                'short_period': 5,
                'long_period': 20,
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        else:
            default_params = {
                'stop_loss': -0.02,
                'take_profit': 0.03,
                'max_hold_hours': 24
            }
        
        # 파라미터 병합
        strategy_params = {**default_params, **params}
        
        # 모든 지표를 한 번에 계산 (벡터화)
        df_indicators = self._calculate_all_indicators(df, strategy, strategy_params)
        
        # 거래 실행 (포지션 상태 기반)
        self._execute_trades_vectorized(df_indicators, None, symbol, strategy_params)
        
        print(f"✅ 벡터화 백테스트 완료 - 총 거래: {len(self.trades)}회")
    
    def _calculate_all_indicators(self, df, strategy, params):
        """모든 지표를 한 번에 계산 (벡터화)"""
        df_indicators = df.copy()
        
        if strategy == 'rsi':
            # RSI 계산 (벡터화)
            df_indicators['rsi'] = calculate_rsi(df_indicators['close'], period=14)
            
            # 이동평균 계산 (벡터화)
            df_indicators['ma_short'] = df_indicators['close'].rolling(window=5).mean()
            df_indicators['ma_long'] = df_indicators['close'].rolling(window=20).mean()
            
            # 거래량 이동평균 (벡터화)
            df_indicators['volume_ma'] = df_indicators['volume'].rolling(window=20).mean()
            df_indicators['volume_ratio'] = df_indicators['volume'] / df_indicators['volume_ma']
            
            # 피벗 포인트 계산 (벡터화)
            df_indicators['pivot_high'] = df_indicators['high'].rolling(window=5, center=True).max()
            df_indicators['pivot_low'] = df_indicators['low'].rolling(window=5, center=True).min()
            
        elif strategy == 'ma':
            # 이동평균 계산 (벡터화)
            short_period = params.get('short_period', 5)
            long_period = params.get('long_period', 20)
            
            df_indicators['ma_short'] = df_indicators['close'].rolling(window=short_period).mean()
            df_indicators['ma_long'] = df_indicators['close'].rolling(window=long_period).mean()
            
            # 크로스오버 시그널 (벡터화)
            df_indicators['ma_cross'] = (df_indicators['ma_short'] > df_indicators['ma_long']).astype(int)
            df_indicators['ma_cross_prev'] = df_indicators['ma_cross'].shift(1)
        
        return df_indicators
    
    def _generate_signals_vectorized(self, df, strategy, params):
        """벡터화된 시그널 생성"""
        signals = pd.Series('HOLD', index=df.index)
        
        # NaN 값 처리
        df = df.ffill().bfill()
        
        if strategy == 'rsi':
            # RSI 시그널 (벡터화) - 조건 완화
            rsi_buy = params.get('rsi_buy', 30)
            rsi_sell = params.get('rsi_sell', 70)
            
            # 매수 조건 (벡터화) - 더 완화
            buy_condition = (
                (df['rsi'] < rsi_buy) & 
                (df['volume_ratio'] > 0.3) &  # 거래량 조건 더 완화
                (df['rsi'].notna()) &  # NaN 체크
                (df['volume_ratio'].notna())
            )
            
            # 매도 조건 (벡터화) - 포지션이 있을 때만
            sell_condition = (
                (df['rsi'] > rsi_sell)
            )
            
            signals[buy_condition] = 'BUY'
            signals[sell_condition] = 'SELL'
            
        elif strategy == 'ma':
            # 이동평균 크로스오버 시그널 (벡터화)
            golden_cross = (df['ma_cross'] == 1) & (df['ma_cross_prev'] == 0)
            death_cross = (df['ma_cross'] == 0) & (df['ma_cross_prev'] == 1)
            
            # NaN 체크 추가
            golden_cross = golden_cross & df['ma_short'].notna() & df['ma_long'].notna()
            death_cross = death_cross & df['ma_short'].notna() & df['ma_long'].notna()
            
            signals[golden_cross] = 'BUY'
            signals[death_cross] = 'SELL'
        
        return signals
    
    def _execute_trades_vectorized(self, df, signals, symbol, params):
        """벡터화된 시그널로 거래 실행"""
        position = None
        
        # 워밍업 기간 (이동평균 계산용)
        warmup_period = 30
        
        # 전략 타입 확인
        strategy = 'ma'  # 기본값
        if 'rsi_buy' in params and 'rsi_sell' in params:
            strategy = 'rsi'
        elif 'short_period' in params and 'long_period' in params:
            strategy = 'ma'
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            # 워밍업 기간 동안은 거래하지 않음
            if i < warmup_period:
                continue
            
            price = row['close']
            
            if strategy == 'rsi':
                # RSI 전략 로직
                rsi = row['rsi'] if 'rsi' in row else 50
                volume_ratio = row.get('volume_ratio', 1.0)
                
                # 포지션 상태에 따른 시그널 생성
                if position is None:
                    # 포지션 없을 때: 롱/숏 진입 조건
                    rsi_buy = params.get('rsi_buy', 30)
                    rsi_sell = params.get('rsi_sell', 70)
                    
                    # 롱 진입: RSI < 30 (과매도)
                    if rsi < rsi_buy and volume_ratio > 0.3:
                        position = {
                            'type': 'LONG',
                            'entry_price': price,
                            'entry_time': timestamp,
                            'amount': self.balance * self.balance_ratio / price
                        }
                        self.execute_trade('BUY', price, timestamp, symbol)
                        
                    # 숏 진입: RSI > 70 (과매수)
                    elif rsi > rsi_sell and volume_ratio > 0.3:
                        position = {
                            'type': 'SHORT',
                            'entry_price': price,
                            'entry_time': timestamp,
                            'amount': self.balance * self.balance_ratio / price
                        }
                        self.execute_trade('SELL', price, timestamp, symbol)
                        
                else:
                    # 포지션 있을 때: 롱/숏별 정리 조건
                    entry_price = position['entry_price']
                    position_type = position['type']
                    
                    if position_type == 'LONG':
                        # 롱 포지션 정리 조건
                        price_change = (price - entry_price) / entry_price
                        
                        # 1. RSI 과매수 (롱 정리)
                        rsi_sell = params.get('rsi_sell', 70)
                        if rsi > rsi_sell:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱RSI과매수')
                            position = None
                            continue
                        
                        # 2. 손절 (롱)
                        stop_loss = params.get('stop_loss', -0.02)
                        if price_change <= stop_loss:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱손절')
                            position = None
                            continue
                        
                        # 3. 익절 (롱)
                        take_profit = params.get('take_profit', 0.03)
                        if price_change >= take_profit:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱익절')
                            position = None
                            continue
                            
                    elif position_type == 'SHORT':
                        # 숏 포지션 정리 조건
                        price_change = (entry_price - price) / entry_price  # 숏은 반대
                        
                        # 1. RSI 과매도 (숏 정리)
                        rsi_buy = params.get('rsi_buy', 30)
                        if rsi < rsi_buy:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏RSI과매도')
                            position = None
                            continue
                        
                        # 2. 손절 (숏)
                        stop_loss = params.get('stop_loss', -0.02)
                        if price_change <= stop_loss:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏손절')
                            position = None
                            continue
                        
                        # 3. 익절 (숏)
                        take_profit = params.get('take_profit', 0.03)
                        if price_change >= take_profit:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏익절')
                            position = None
                            continue
                
            elif strategy == 'ma':
                # 이동평균 전략 로직
                ma_short = row.get('ma_short', price)
                ma_long = row.get('ma_long', price)
                
                # 포지션 상태에 따른 시그널 생성
                if position is None:
                    # 포지션 없을 때: 골든크로스/데스크로스 진입
                    ma_cross = row.get('ma_cross', 0)
                    ma_cross_prev = row.get('ma_cross_prev', 0)
                    
                    # 골든크로스 (단기 > 장기): 롱 진입
                    if ma_cross == 1 and ma_cross_prev == 0:
                        position = {
                            'type': 'LONG',
                            'entry_price': price,
                            'entry_time': timestamp,
                            'amount': self.balance * self.balance_ratio / price
                        }
                        self.execute_trade('BUY', price, timestamp, symbol)
                        
                    # 데스크로스 (단기 < 장기): 숏 진입
                    elif ma_cross == 0 and ma_cross_prev == 1:
                        position = {
                            'type': 'SHORT',
                            'entry_price': price,
                            'entry_time': timestamp,
                            'amount': self.balance * self.balance_ratio / price
                        }
                        self.execute_trade('SELL', price, timestamp, symbol)
                        
                else:
                    # 포지션 있을 때: 반대 크로스로 정리
                    entry_price = position['entry_price']
                    position_type = position['type']
                    ma_cross = row.get('ma_cross', 0)
                    ma_cross_prev = row.get('ma_cross_prev', 0)
                    
                    if position_type == 'LONG':
                        # 롱 포지션 정리 조건
                        price_change = (price - entry_price) / entry_price
                        
                        # 1. 데스크로스 (롱 정리)
                        if ma_cross == 0 and ma_cross_prev == 1:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱데스크로스')
                            position = None
                            continue
                        
                        # 2. 손절 (롱)
                        stop_loss = params.get('stop_loss', -0.02)
                        if price_change <= stop_loss:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱손절')
                            position = None
                            continue
                        
                        # 3. 익절 (롱)
                        take_profit = params.get('take_profit', 0.03)
                        if price_change >= take_profit:
                            self.execute_trade('SELL', price, timestamp, symbol, '롱익절')
                            position = None
                            continue
                            
                    elif position_type == 'SHORT':
                        # 숏 포지션 정리 조건
                        price_change = (entry_price - price) / entry_price  # 숏은 반대
                        
                        # 1. 골든크로스 (숏 정리)
                        if ma_cross == 1 and ma_cross_prev == 0:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏골든크로스')
                            position = None
                            continue
                        
                        # 2. 손절 (숏)
                        stop_loss = params.get('stop_loss', -0.02)
                        if price_change <= stop_loss:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏손절')
                            position = None
                            continue
                        
                        # 3. 익절 (숏)
                        take_profit = params.get('take_profit', 0.03)
                        if price_change >= take_profit:
                            self.execute_trade('BUY', price, timestamp, symbol, '숏익절')
                            position = None
                            continue
            
            # 최대 보유 시간 체크
            if position:
                max_hold_hours = params.get('max_hold_hours', 24)
                hold_time = timestamp - position['entry_time']
                if hold_time.total_seconds() / 3600 > max_hold_hours:
                    if position['type'] == 'LONG':
                        self.execute_trade('SELL', price, timestamp, symbol, '최대보유시간')
                    else:
                        self.execute_trade('BUY', price, timestamp, symbol, '최대보유시간')
                    position = None

# 전역 거래 추적기
trading_tracker = TradingTracker()

def auto_trading_loop(symbol='BTC/USDT:USDT', leverage=1, position_ratio=0.3, timeframe='1h', strategy='ma', params=None):
    """자동 거래 루프 (24시간 결과 저장 포함)"""
    strategy_name = "이동평균 크로스오버" if strategy == 'ma' else "RSI + 추세선 돌파"
    print(f"자동 거래 시작 - {symbol}")
    print(f"전략: {strategy_name}")
    print(f"타임프레임: {timeframe}")
    print(f"레버리지: {leverage}x, 포지션 크기: 잔고의 {position_ratio*100:.0f}%")
    
    # 레버리지 설정
    try:
        binance.set_leverage(leverage, symbol)
        print(f"레버리지 설정 완료: {leverage}x")
    except Exception as e:
        print(f"레버리지 설정 실패: {e}")
    
    # 초기 잔고 설정
    try:
        balance = binance.fetchBalance()
        initial_usdt = balance['USDT']['free']
        trading_tracker.set_initial_balance(initial_usdt)
        print(f"초기 USDT 잔고: ${initial_usdt:,.2f}")
    except Exception as e:
        print(f"잔고 조회 실패: {e}")
    
    # 24시간 결과 저장을 위한 타이머
    last_save_time = datetime.now()
    save_interval = timedelta(hours=24)
    
    while True:
        try:
            execute_strategy(symbol, position_ratio, timeframe, strategy, params)
            
            # 24시간마다 결과 저장
            current_time = datetime.now()
            if current_time - last_save_time >= save_interval:
                print(f"\n📊 24시간 경과 - 거래 결과 저장 중...")
                trading_tracker.save_daily_report()
                last_save_time = current_time
            
            # 타임프레임에 따른 대기 시간 설정
            if timeframe == '1m':
                sleep_time = 30  # 30초마다 체크
            elif timeframe == '5m':
                sleep_time = 60  # 1분마다 체크
            elif timeframe == '15m':
                sleep_time = 300  # 5분마다 체크
            elif timeframe == '1h':
                sleep_time = 1800  # 30분마다 체크
            elif timeframe == '4h':
                sleep_time = 3600  # 1시간마다 체크
            elif timeframe == '1d':
                sleep_time = 14400  # 4시간마다 체크
            else:
                sleep_time = 60  # 기본값
            
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n자동 거래 종료 요청됨...")
            
            # 현재 잔고 설정
            try:
                balance = binance.fetchBalance()
                current_usdt = balance['USDT']['free']
                trading_tracker.set_current_balance(current_usdt)
            except Exception as e:
                print(f"최종 잔고 조회 실패: {e}")
            
            # 성과 리포트 출력
            trading_tracker.print_performance_report()
            
            # 거래 로그 저장
            trading_tracker.save_trading_log()
            
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(10) # 오류 시 10초 대기

def get_trading_settings():
    """거래 설정을 사용자로부터 입력받는 함수"""
    print("\n" + "="*50)
    print("⚙️ 거래 설정")
    print("="*50)
    
    # 레버리지 설정
    print("\n📊 레버리지 설정:")
    print("1. 1x (무레버리지)")
    print("2. 3x")
    print("3. 5x")
    print("4. 10x")
    print("5. 20x")
    print("6. 직접 입력")
    
    try:
        leverage_choice = int(input("\n레버리지를 선택하세요 (1-6): "))
        
        if leverage_choice == 1:
            leverage = 1
        elif leverage_choice == 2:
            leverage = 3
        elif leverage_choice == 3:
            leverage = 5
        elif leverage_choice == 4:
            leverage = 10
        elif leverage_choice == 5:
            leverage = 20
        elif leverage_choice == 6:
            leverage = int(input("레버리지를 직접 입력하세요 (1-125): "))
            if leverage < 1 or leverage > 125:
                print("레버리지는 1-125 사이여야 합니다. 1로 설정합니다.")
                leverage = 1
        else:
            print("잘못된 선택입니다. 1로 설정합니다.")
            leverage = 1
            
        print(f"설정된 레버리지: {leverage}x")
        
    except ValueError:
        print("숫자를 입력해주세요. 1로 설정합니다.")
        leverage = 1
    
    # 포지션 크기 설정
    print("\n💰 포지션 크기 설정:")
    print("1. 잔고의 10%")
    print("2. 잔고의 20%")
    print("3. 잔고의 30%")
    print("4. 잔고의 50%")
    print("5. 잔고의 70%")
    print("6. 직접 입력")
    
    try:
        position_choice = int(input("\n포지션 크기를 선택하세요 (1-6): "))
        
        if position_choice == 1:
            position_ratio = 0.1
        elif position_choice == 2:
            position_ratio = 0.2
        elif position_choice == 3:
            position_ratio = 0.3
        elif position_choice == 4:
            position_ratio = 0.5
        elif position_choice == 5:
            position_ratio = 0.7
        elif position_choice == 6:
            position_ratio = float(input("포지션 크기를 직접 입력하세요 (0.1-1.0): "))
            if position_ratio < 0.1 or position_ratio > 1.0:
                print("포지션 크기는 0.1-1.0 사이여야 합니다. 0.3으로 설정합니다.")
                position_ratio = 0.3
        else:
            print("잘못된 선택입니다. 0.3으로 설정합니다.")
            position_ratio = 0.3
            
        print(f"설정된 포지션 크기: 잔고의 {position_ratio*100:.0f}%")
        
    except ValueError:
        print("숫자를 입력해주세요. 0.3으로 설정합니다.")
        position_ratio = 0.3
    
    print("\n" + "="*50)
    print(f"✅ 최종 설정: 레버리지 {leverage}x, 포지션 크기 {position_ratio*100:.0f}%")
    print("="*50)
    
    return leverage, position_ratio

# 전략 파라미터 정의
class StrategyParams:
    """전략 파라미터 클래스"""
    
    @staticmethod
    def get_rsi_params() -> Dict[str, List]:
        """RSI 전략 파라미터 범위 (빠른 최적화용)"""
        return {
            'rsi_buy': [28, 30, 32],              # RSI 매수 조건 (3개)
            'rsi_sell': [68, 70, 72],             # RSI 매도 조건 (3개)
            'stop_loss': [-0.015, -0.02],         # 손절 비율 (2개)
            'take_profit': [0.03, 0.04],          # 익절 비율 (2개)
            'support_distance': [0.02, 0.03]      # 지지선 거리 (2개)
        }
    
    @staticmethod
    def get_ma_params() -> Dict[str, List]:
        """이동평균 전략 파라미터 범위 (빠른 최적화용)"""
        return {
            'short_period': [5, 7, 10],           # 단기 이동평균 (3개)
            'long_period': [15, 20, 25],          # 장기 이동평균 (3개)
            'stop_loss': [-0.015, -0.02],         # 손절 비율 (2개)
            'take_profit': [0.03, 0.04],          # 익절 비율 (2개)
            'max_hold_hours': [24]                # 최대 보유 시간 (1개)
        }

class StrategyOptimizer:
    """전략 최적화 엔진"""
    
    def __init__(self, initial_balance=10000, balance_ratio=0.3, commission=0.0004, leverage=1):
        self.initial_balance = initial_balance
        self.balance_ratio = balance_ratio
        self.commission = commission
        self.leverage = leverage
        self.backtest_engine = BacktestEngine(initial_balance, balance_ratio, commission, leverage)
        self.optimization_results = []
    
    def optimize_strategy(self, symbol: str, timeframe: str, strategy: str, 
                         optimization_days: int = 7, max_combinations: int = 100) -> Dict:
        """전략 최적화 실행"""
        print(f"\n🔧 {strategy.upper()} 전략 최적화 시작...")
        print(f"📊 최적화 기간: {optimization_days}일")
        print(f"🎯 최대 조합 수: {max_combinations}")
        
        # 데이터 수집
        df = get_price_data(symbol, timeframe=timeframe, limit=optimization_days * 1440)  # 1분봉 기준
        if df is None or len(df) < 100:
            print("❌ 충분한 데이터를 수집할 수 없습니다.")
            return {}
        
        # 파라미터 조합 생성
        if strategy == 'rsi':
            param_ranges = StrategyParams.get_rsi_params()
        elif strategy == 'ma':
            param_ranges = StrategyParams.get_ma_params()
        else:
            print(f"❌ 지원하지 않는 전략: {strategy}")
            return {}
        
        # 모든 조합 생성 (최대 조합 수 제한)
        combinations = self._generate_combinations(param_ranges, max_combinations)
        print(f"📈 테스트할 조합 수: {len(combinations)}")
        
        # 각 조합 테스트
        best_result = None
        best_params = None
        
        for i, params in enumerate(combinations):
            print(f"\r🔄 진행률: {i+1}/{len(combinations)} ({((i+1)/len(combinations)*100):.1f}%)", end="")
            
            # 백테스트 실행
            result = self._run_backtest_with_params(df, symbol, timeframe, strategy, params)
            
            if result:  # 모든 결과를 저장 (조건 완화)
                self.optimization_results.append({
                    'params': params,
                    'result': result
                })
                
                # 최고 성과 업데이트
                if best_result is None or result['total_return'] > best_result['total_return']:
                    best_result = result
                    best_params = params
        
        print(f"\n✅ 최적화 완료!")
        
        if best_result:
            print(f"🏆 최고 성과: {best_result['total_return']:.2f}%")
            print(f"🎯 최적 파라미터: {best_params}")
            
            # 결과 저장
            self._save_optimization_result(strategy, best_params, best_result)
            
            return {
                'strategy': strategy,
                'best_params': best_params,
                'best_result': best_result,
                'all_results': self.optimization_results
            }
        else:
            print("⚠️ 모든 파라미터 조합에서 수익률이 낮습니다.")
            
            # 최고 성과 선택 (손실이어도)
            if self.optimization_results:
                best_result = max(self.optimization_results, key=lambda x: x['result']['total_return'])
                best_params = best_result['params']
                best_result = best_result['result']
                
                print(f"🏆 최고 성과: {best_result['total_return']:.2f}%")
                print(f"🎯 최적 파라미터: {best_params}")
                
                # 조건 완화 테스트 제안
                print(f"\n💡 모든 결과가 손실입니다. 조건을 완화해서 다시 테스트하시겠습니까?")
                print(f"   - 더 보수적인 파라미터 (손절 완화, 익절 완화)")
                print(f"   - 더 긴 보유 기간")
                print(f"   - 더 엄격한 진입 조건")
                
                retry_choice = input("\n조건을 완화해서 다시 테스트하시겠습니까? (y/n): ").lower().strip()
                
                if retry_choice == 'y':
                    print("🔄 조건을 완화해서 다시 최적화를 실행합니다...")
                    return self._retry_optimization_with_relaxed_conditions(symbol, timeframe, strategy, optimization_days, max_combinations)
                else:
                    print("✅ 현재 최고 성과를 선택합니다.")
                    # 결과 저장
                    self._save_optimization_result(strategy, best_params, best_result)
                    
                    return {
                        'strategy': strategy,
                        'best_params': best_params,
                        'best_result': best_result,
                        'all_results': self.optimization_results
                    }
        
        return {}
    
    def _generate_combinations(self, param_ranges: Dict[str, List], max_combinations: int) -> List[Dict]:
        """파라미터 조합 생성"""
        keys = list(param_ranges.keys())
        values = list(param_ranges.values())
        
        # 모든 조합 생성
        all_combinations = list(itertools.product(*values))
        
        # 최대 조합 수 제한
        if len(all_combinations) > max_combinations:
            # 랜덤 샘플링
            indices = np.random.choice(len(all_combinations), max_combinations, replace=False)
            all_combinations = [all_combinations[i] for i in indices]
        
        # 딕셔너리 형태로 변환
        combinations = []
        for combo in all_combinations:
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _run_backtest_with_params(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                                 strategy: str, params: Dict) -> Optional[Dict]:
        """특정 파라미터로 백테스트 실행 (벡터화)"""
        try:
            # 백테스트 엔진 초기화
            self.backtest_engine.reset()
            
            # 벡터화된 백테스트 실행 (훨씬 빠름)
            self.backtest_engine.run_backtest_vectorized(df, symbol, timeframe, strategy, params)
            
            # 결과 생성
            result = self.backtest_engine.generate_backtest_report()
            
            return result
            
        except Exception as e:
            print(f"\n❌ 백테스트 오류: {e}")
            return None
    
    def _convert_timestamps_to_strings(self, obj):
        """Timestamp 객체를 문자열로 변환하여 JSON 직렬화 가능하게 만듦"""
        if isinstance(obj, dict):
            return {key: self._convert_timestamps_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_timestamps_to_strings(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # Timestamp 객체
            return obj.isoformat()
        else:
            return obj
    
    def _save_optimization_result(self, strategy: str, best_params: Dict, best_result: Dict):
        """최적화 결과 저장"""
        # 타임스탬프가 포함된 파일명
        timestamp_filename = f"optimization_{strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 최신 결과를 나타내는 파일명 (덮어쓰기)
        latest_filename = f"optimization_{strategy}_latest.json"
        
        # Timestamp 객체를 문자열로 변환
        serializable_best_result = self._convert_timestamps_to_strings(best_result)
        
        data = {
            'strategy': strategy,
            'timestamp': datetime.now().isoformat(),
            'best_params': best_params,
            'best_result': serializable_best_result,
            'all_results_count': len(self.optimization_results)
        }
        
        try:
            # 타임스탬프 파일 저장
            with open(timestamp_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 최신 결과 파일 저장 (덮어쓰기)
            with open(latest_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            print(f"💾 최적화 결과 저장: {timestamp_filename}")
            print(f"💾 최신 결과 저장: {latest_filename}")
        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")
    
    def load_latest_optimization(self, strategy: str) -> Optional[Dict]:
        """최신 최적화 결과 불러오기"""
        # 일반 최적화 결과 먼저 확인
        latest_filename = f"optimization_{strategy}_latest.json"
        relaxed_filename = f"optimization_{strategy}_relaxed_latest.json"
        
        try:
            # 완화된 조건 결과가 있는지 확인
            if os.path.exists(relaxed_filename):
                with open(relaxed_filename, 'r', encoding='utf-8') as f:
                    relaxed_data = json.load(f)
                
                # 저장된 시간 확인 (7일 이내인지)
                saved_time = datetime.fromisoformat(relaxed_data['timestamp'])
                days_old = (datetime.now() - saved_time).days
                
                if days_old <= 7:
                    print(f"📂 완화된 조건 최적화 결과 발견 ({days_old}일 전)")
                    return relaxed_data
            
            # 일반 최적화 결과 확인
            if os.path.exists(latest_filename):
                with open(latest_filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 저장된 시간 확인 (7일 이내인지)
                saved_time = datetime.fromisoformat(data['timestamp'])
                days_old = (datetime.now() - saved_time).days
                
                if days_old <= 7:
                    print(f"📂 최신 최적화 결과 발견 ({days_old}일 전)")
                    return data
                else:
                    print(f"⚠️ 최적화 결과가 너무 오래됨 ({days_old}일 전)")
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"❌ 최적화 결과 불러오기 실패: {e}")
            return None
    
    def _retry_optimization_with_relaxed_conditions(self, symbol: str, timeframe: str, strategy: str, 
                                                   optimization_days: int, max_combinations: int) -> Dict:
        """조건을 완화한 재최적화 실행"""
        print(f"\n🔄 조건 완화 최적화 시작...")
        
        # 기존 결과 초기화
        self.optimization_results = []
        
        # 완화된 파라미터 범위 설정
        if strategy == 'rsi':
            param_ranges = {
                'rsi_buy': [25, 28, 30],              # 더 낮은 RSI 매수 조건
                'rsi_sell': [70, 72, 75],             # 더 높은 RSI 매도 조건
                'stop_loss': [-0.025, -0.03],         # 더 완화된 손절
                'take_profit': [0.02, 0.025],         # 더 보수적인 익절
                'support_distance': [0.025, 0.03]     # 더 넓은 지지선 거리
            }
        elif strategy == 'ma':
            param_ranges = {
                'short_period': [3, 5, 7],            # 더 짧은 단기 이동평균
                'long_period': [10, 15, 20],          # 더 짧은 장기 이동평균
                'stop_loss': [-0.025, -0.03],         # 더 완화된 손절
                'take_profit': [0.02, 0.025],         # 더 보수적인 익절
                'max_hold_hours': [12, 18]            # 더 짧은 보유 기간
            }
        else:
            print(f"❌ 지원하지 않는 전략: {strategy}")
            return {}
        
        print(f"📊 완화된 파라미터 범위:")
        for key, values in param_ranges.items():
            print(f"   {key}: {values}")
        
        # 모든 조합 생성
        combinations = self._generate_combinations(param_ranges, max_combinations)
        print(f"📈 테스트할 조합 수: {len(combinations)}")
        
        # 데이터 재사용 (이미 수집된 데이터 사용)
        df = get_price_data(symbol, timeframe=timeframe, limit=optimization_days * 1440)
        if df is None or len(df) < 100:
            print("❌ 충분한 데이터를 수집할 수 없습니다.")
            return {}
        
        # 각 조합 테스트
        best_result = None
        best_params = None
        
        for i, params in enumerate(combinations):
            print(f"\r🔄 진행률: {i+1}/{len(combinations)} ({((i+1)/len(combinations)*100):.1f}%)", end="")
            
            # 백테스트 실행
            result = self._run_backtest_with_params(df, symbol, timeframe, strategy, params)
            
            if result:
                self.optimization_results.append({
                    'params': params,
                    'result': result
                })
                
                # 최고 성과 업데이트
                if best_result is None or result['total_return'] > best_result['total_return']:
                    best_result = result
                    best_params = params
        
        print(f"\n✅ 완화된 조건 최적화 완료!")
        
        if best_result:
            print(f"🏆 최고 성과: {best_result['total_return']:.2f}%")
            print(f"🎯 최적 파라미터: {best_params}")
            
            # 결과 저장 (완화된 조건임을 표시)
            self._save_optimization_result(f"{strategy}_relaxed", best_params, best_result)
            
            return {
                'strategy': f"{strategy}_relaxed",
                'best_params': best_params,
                'best_result': best_result,
                'all_results': self.optimization_results
            }
        
        return {}
    
    def print_optimization_summary(self, results: Dict):
        """최적화 결과 요약 출력"""
        if not results:
            print("❌ 최적화 결과가 없습니다.")
            return
        
        print("\n" + "="*60)
        print("🏆 전략 최적화 결과 요약")
        print("="*60)
        
        strategy = results['strategy']
        best_params = results['best_params']
        best_result = results['best_result']
        
        # 완화된 조건인지 확인
        is_relaxed = "_relaxed" in strategy
        display_strategy = strategy.replace("_relaxed", "")
        
        print(f"📊 전략: {display_strategy.upper()}")
        if is_relaxed:
            print(f"🔧 최적화 유형: 완화된 조건")
        print(f"📈 최고 수익률: {best_result['total_return']:.2f}%")
        print(f"💰 최종 자본: ${best_result['final_balance']:.2f}")
        print(f"📊 승률: {best_result['win_rate']:.1f}%")
        print(f"🔄 거래 횟수: {best_result['total_trades']}회")
        print(f"📉 최대 낙폭: {best_result['max_drawdown']:.2f}%")
        
        print(f"\n🎯 최적 파라미터:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")
        
        print(f"\n📋 전체 테스트 조합: {len(results['all_results'])}개")
        
        # 상위 5개 결과 출력
        sorted_results = sorted(results['all_results'], 
                              key=lambda x: x['result']['total_return'], reverse=True)
        
        print(f"\n🏅 상위 5개 결과:")
        for i, result in enumerate(sorted_results[:5]):
            print(f"  {i+1}. 수익률: {result['result']['total_return']:.2f}% "
                  f"(승률: {result['result']['win_rate']:.1f}%)")

def auto_trading_menu():
    """자동매매 메뉴"""
    while True:
        print("\n📊 자동매매 메뉴")
        print("="*40)
        print("1. 포트폴리오 자동 구성")
        print("2. 수동 설정으로 매매")
        print("3. 이전 메뉴로")
        
        try:
            choice = int(input("\n번호를 선택하세요 (1-3): "))
            
            if choice == 1:
                # 포트폴리오 자동 구성
                portfolio_auto_config()
            elif choice == 2:
                # 수동 설정으로 매매
                manual_trading_config()
            elif choice == 3:
                break
            else:
                print("잘못된 선택입니다.")
                
        except ValueError:
            print("숫자를 입력해주세요.")
        except KeyboardInterrupt:
            break


    """자동매매 메뉴"""
    while True:
        print("\n📊 자동매매 메뉴")
        print("="*40)
        print("1. 포트폴리오 자동 구성")
        print("2. 수동 설정으로 매매")
        print("3. 이전 메뉴로")
        
        try:
            choice = int(input("\n번호를 선택하세요 (1-3): "))
            
            if choice == 1:
                # 포트폴리오 자동 구성
                portfolio_auto_config()
            elif choice == 2:
                # 수동 설정으로 매매
                manual_trading_config()
            elif choice == 3:
                break
            else:
                print("잘못된 선택입니다.")
                
        except ValueError:
            print("숫자를 입력해주세요.")
        except KeyboardInterrupt:
            break

def portfolio_auto_config():
    """포트폴리오 자동 구성"""
    print("\n🎯 포트폴리오 자동 구성")
    print("="*50)
    
    # 백테스팅으로 최적 티커/전략 매칭 찾기
    print("🔍 백테스팅으로 최적 티커/전략 매칭을 분석 중...")
    
    # 분석할 코인 수 선택
    try:
        num_coins = int(input("분석할 코인 수 (5-20): ") or "10")
        if num_coins < 5:
            num_coins = 5
        elif num_coins > 20:
            num_coins = 20
    except ValueError:
        num_coins = 10
    
    # 분석 기간 선택
    try:
        analysis_days = int(input("분석 기간 (일, 3-30): ") or "7")
        if analysis_days < 3:
            analysis_days = 3
        elif analysis_days > 30:
            analysis_days = 30
    except ValueError:
        analysis_days = 7
    
    # 고변동성 코인 가져오기
    volatile_coins = get_volatile_coins(min_volume=1000000, min_volatility=0.02, top_n=num_coins)
    
    # 심볼 중복 제거 및 정규화
    unique_coins = []
    seen_symbols = set()
    
    for coin in volatile_coins:
        # 심볼 정규화 완전히 제거
        clean_symbol = coin['symbol']
        if clean_symbol not in seen_symbols:
            seen_symbols.add(clean_symbol)
            coin['symbol'] = clean_symbol
            unique_coins.append(coin)
    
    volatile_coins = unique_coins
    
    if not volatile_coins:
        print("❌ 분석할 코인을 찾을 수 없습니다.")
        return
    
    print(f"\n📊 {len(volatile_coins)}개 코인에 대해 백테스팅 분석 시작...")
    
    # 각 코인에 대해 전략별 백테스팅 실행
    results = []
    optimizer = StrategyOptimizer()
    
    for i, coin in enumerate(volatile_coins):
        symbol = coin['symbol']
        print(f"\n🔄 {i+1}/{len(volatile_coins)}: {symbol} 분석 중...")
        
        # RSI 전략 백테스팅
        rsi_result = optimizer.optimize_strategy(
            symbol=symbol,
            timeframe='5m',
            strategy='rsi',
            optimization_days=analysis_days,
            max_combinations=20
        )
        
        # MA 전략 백테스팅
        ma_result = optimizer.optimize_strategy(
            symbol=symbol,
            timeframe='5m',
            strategy='ma',
            optimization_days=analysis_days,
            max_combinations=20
        )
        
        # 최고 성과 전략 선택
        best_strategy = None
        best_result = None
        
        if rsi_result and ma_result:
            if rsi_result['best_result']['total_return'] > ma_result['best_result']['total_return']:
                best_strategy = 'rsi'
                best_result = rsi_result
            else:
                best_strategy = 'ma'
                best_result = ma_result
        elif rsi_result:
            best_strategy = 'rsi'
            best_result = rsi_result
        elif ma_result:
            best_strategy = 'ma'
            best_result = ma_result
        
        if best_result:
            results.append({
                'symbol': symbol,
                'strategy': best_strategy,
                'params': best_result['best_params'],
                'return': best_result['best_result']['total_return'],
                'win_rate': best_result['best_result']['win_rate'],
                'max_drawdown': best_result['best_result']['max_drawdown']
            })
    
    # 결과 정렬 (수익률 기준)
    results.sort(key=lambda x: x['return'], reverse=True)
    
    # 결과 출력
    print("\n" + "="*80)
    print("🏆 포트폴리오 자동 구성 결과")
    print("="*80)
    print(f"{'순위':<4} {'심볼':<15} {'전략':<8} {'수익률':<8} {'승률':<6} {'MDD':<6}")
    print("-"*80)
    
    for i, result in enumerate(results, 1):
        symbol = result['symbol'].replace(':USDT', '')
        strategy = result['strategy'].upper()
        return_pct = f"{result['return']:+.1f}%"
        win_rate = f"{result['win_rate']:.1f}%"
        mdd = f"{result['max_drawdown']:.1f}%"
        print(f"{i:<4} {symbol:<15} {strategy:<8} {return_pct:<8} {win_rate:<6} {mdd:<6}")
    
    # 포트폴리오 구성
    try:
        portfolio_size = int(input(f"\n포트폴리오에 포함할 코인 수 (1-{len(results)}): ") or "5")
        if portfolio_size < 1:
            portfolio_size = 1
        elif portfolio_size > len(results):
            portfolio_size = len(results)
    except ValueError:
        portfolio_size = 5
    
    selected_portfolio = results[:portfolio_size]
    
    print(f"\n✅ 포트폴리오 구성 완료! {portfolio_size}개 코인 선택됨")
    
    # 포트폴리오 저장
    save_portfolio_config(selected_portfolio)
    
    # 매매 시작 여부 확인
    try:
        start_trading = input("\n포트폴리오로 매매를 시작하시겠습니까? (y/n): ").lower()
        if start_trading == 'y':
            start_portfolio_trading(selected_portfolio)
    except KeyboardInterrupt:
        print("\n매매 시작을 취소했습니다.")

def manual_trading_config():
    """수동 설정으로 매매"""
    print("\n⚙️ 수동 매매 설정")
    print("="*40)
    
    # 거래 설정
    leverage, position_ratio = get_trading_settings()
    
    # 전략 설정
    strategy, strategy_name, strategy_params = get_strategy_settings()
    
    # 거래 정보 입력
    symbol = input("거래할 심볼 (예: BTC/USDT:USDT): ") or "BTC/USDT:USDT"
    timeframe = input("타임프레임 (1m/5m/15m/1h/4h/1d): ") or "1h"
    
    print(f"\n🚀 수동 설정 매매 시작!")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {timeframe}")
    print(f"전략: {strategy_name}")
    print(f"레버리지: {leverage}x")
    print(f"포지션 크기: 잔고의 {position_ratio*100:.0f}%")
    
    # 매매 시작
    auto_trading_loop(symbol, leverage, position_ratio, timeframe, strategy, strategy_params)

def strategy_optimization_menu():
    """전략 최적화 메뉴"""
    while True:
        print("\n🔧 전략 최적화 메뉴")
        print("="*40)
        print("1. 전략 최적화 실행")
        print("2. 저장된 최적화 결과 보기")
        print("3. 이전 메뉴로")
        
        try:
            choice = int(input("\n번호를 선택하세요 (1-3): "))
            
            if choice == 1:
                # 전략 최적화 실행
                run_strategy_optimization()
            elif choice == 2:
                # 저장된 최적화 결과 보기
                show_saved_optimizations()
            elif choice == 3:
                break
            else:
                print("잘못된 선택입니다.")
                
        except ValueError:
            print("숫자를 입력해주세요.")
        except KeyboardInterrupt:
            break

def save_portfolio_config(portfolio):
    """포트폴리오 설정 저장"""
    filename = f"portfolio_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'portfolio': portfolio
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 포트폴리오 설정 저장: {filename}")
    except Exception as e:
        print(f"❌ 포트폴리오 저장 실패: {e}")

def start_portfolio_trading(portfolio):
    """포트폴리오 매매 시작"""
    print(f"\n🚀 포트폴리오 매매 시작!")
    print(f"총 {len(portfolio)}개 코인으로 구성된 포트폴리오")
    
    # 거래 설정
    leverage, position_ratio = get_trading_settings()
    
    # 각 코인별 매매 시작
    trading_threads = []
    
    for coin_config in portfolio:
        symbol = coin_config['symbol']
        strategy = coin_config['strategy']
        params = coin_config['params']
        
        print(f"📊 {symbol} 매매 시작 (전략: {strategy.upper()})")
        
        # 개별 코인 매매 스레드 시작 (실제 구현에서는 threading 사용)
        # 여기서는 순차적으로 실행
        try:
            auto_trading_loop(symbol, leverage, position_ratio, '5m', strategy, params)
        except Exception as e:
            print(f"❌ {symbol} 매매 오류: {e}")

def show_saved_optimizations():
    """저장된 최적화 결과 보기"""
    import glob
    import os
    
    # 최적화 결과 파일 찾기
    optimization_files = glob.glob("optimization_*.json")
    
    if not optimization_files:
        print("❌ 저장된 최적화 결과가 없습니다.")
        return
    
    print(f"\n📋 저장된 최적화 결과 ({len(optimization_files)}개)")
    print("="*60)
    
    for i, filename in enumerate(optimization_files, 1):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            timestamp = datetime.fromisoformat(data['timestamp']).strftime('%Y-%m-%d %H:%M')
            strategy = data['strategy'].upper()
            return_pct = data['best_result']['total_return']
            
            print(f"{i}. {strategy} 전략 - {return_pct:+.2f}% ({timestamp})")
            
        except Exception as e:
            print(f"{i}. {filename} (읽기 오류)")
    
    # 상세 보기
    try:
        choice = int(input(f"\n상세 보기할 결과 번호 (1-{len(optimization_files)}): "))
        if 1 <= choice <= len(optimization_files):
            show_optimization_detail(optimization_files[choice-1])
    except ValueError:
        print("숫자를 입력해주세요.")
    except KeyboardInterrupt:
        pass

def show_optimization_detail(filename):
    """최적화 결과 상세 보기"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📊 {filename} 상세 결과")
        print("="*50)
        
        strategy = data['strategy'].upper()
        best_params = data['best_params']
        best_result = data['best_result']
        
        print(f"전략: {strategy}")
        print(f"최고 수익률: {best_result['total_return']:.2f}%")
        print(f"승률: {best_result['win_rate']:.1f}%")
        print(f"거래 횟수: {best_result['total_trades']}회")
        print(f"최대 낙폭: {best_result['max_drawdown']:.2f}%")
        
        print(f"\n최적 파라미터:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")

# 24시간 결과 저장 기능 추가
def save_daily_trading_results():
    """24시간마다 거래 결과 저장"""
    while True:
        try:
            # 24시간 대기
            time.sleep(24 * 60 * 60)
            
            # 현재 거래 결과 저장
            performance = trading_tracker.calculate_performance()
            if performance:
                filename = f"trading_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'performance': performance,
                    'trades': trading_tracker.trades
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"💾 24시간 거래 결과 저장: {filename}")
                
        except Exception as e:
            print(f"❌ 결과 저장 오류: {e}")
            time.sleep(60)  # 오류 시 1분 대기

def print_live_performance(tracker: TradingTracker):
    perf = tracker.calculate_performance()
    if perf:
        print(f"[실시간 성과] 거래 횟수: {perf['total_trades']} | 승률: {perf['win_rate']:.2f}% | 수익률: {perf['total_pnl_percentage']:.2f}%")
    else:
        print("[실시간 성과] 거래 내역이 없습니다.")

if __name__ == "__main__":
    # 기존 CLI/자동매매 루프 등은 생략
    tracker = TradingTracker()  # 실제 거래 트래커 인스턴스 사용
    print("\n[백그라운드 자동매매 실행 중...]")
    print("아무 명령어나 엔터를 입력하면 현재까지의 거래 횟수, 승률, 수익률을 보여줍니다. (Ctrl+C로 종료)")
    
    def input_loop():
        while True:
            try:
                _ = input()
                print_live_performance(tracker)
            except (KeyboardInterrupt, EOFError):
                print("\n[프로그램 종료]")
                sys.exit(0)
    
    input_thread = threading.Thread(target=input_loop)
    input_thread.daemon = True
    input_thread.start()
    
    # 여기에 기존 자동매매/트레이딩 루프가 있다면 계속 실행
    while True:
        time.sleep(1)