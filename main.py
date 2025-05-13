import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import tkcalendar
from binance.client import Client
import pandas as pd
from backtest import Backtest
from binance.exceptions import BinanceAPIException
import numpy as np
from indicators import TechnicalIndicators
import time
import logging
import os
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)

class BacktestWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("바이낸스 선물 자동매매")
        self.root.geometry("1200x600")  # 창 크기 확대
        
        # API 클라이언트 초기화
        self.client = Client()
        
        # 작업 취소 플래그
        self.cancel_flag = False
        
        # 기본 설정
        self.symbol = tk.StringVar(value="DOGEUSDT")  # 기본 티커를 DOGEUSDT로 설정
        self.interval = tk.StringVar(value="1m")
        self.strategy = tk.StringVar(value="RSI_MACD_Stochastic")
        
        # 메인 프레임
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그 프레임 (오른쪽)
        log_frame = ttk.LabelFrame(root, text="진행 로그", padding="10")
        log_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        
        # 로그 텍스트 영역
        self.log_text = tk.Text(log_frame, width=50, height=30)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 스크롤바 추가
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 진행 상태 프레임
        self.progress_frame = ttk.Frame(log_frame)
        self.progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 진행 상태 표시
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        # 취소 버튼
        self.cancel_button = ttk.Button(self.progress_frame, text="작업 취소", command=self.cancel_operation)
        self.cancel_button.grid(row=0, column=1, padx=5)
        self.cancel_button.grid_remove()  # 초기에는 숨김
        
        # 선물 티커 목록 가져오기
        try:
            # 선물 거래소 정보 가져오기
            exchange_info = self.client.futures_exchange_info()
            # USDT 마진 선물만 필터링
            self.futures_symbols = [
                symbol['symbol'] for symbol in exchange_info['symbols']
                if symbol['status'] == 'TRADING' and symbol['symbol'].endswith('USDT')
            ]
            self.log(f"바이낸스 선물 티커 수: {len(self.futures_symbols)}개")
            self.log("사용 가능한 티커 목록:")
            for symbol in self.futures_symbols[:10]:  # 처음 10개만 표시
                self.log(f"- {symbol}")
            if len(self.futures_symbols) > 10:
                self.log(f"... 외 {len(self.futures_symbols)-10}개")
        except Exception as e:
            self.log(f"선물 티커 목록을 가져오는 중 오류 발생: {str(e)}")
            self.futures_symbols = []
        
        # 테스트할 티커 목록 (기본값)
        self.test_symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
            "ADAUSDT", "SOLUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT"
        ]
        
        # 거래 설정 프레임
        trade_frame = ttk.LabelFrame(main_frame, text="거래 설정", padding="5")
        trade_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 티커 선택
        ttk.Label(trade_frame, text="티커:").grid(row=0, column=0, padx=5, pady=2)
        ttk.Entry(trade_frame, textvariable=self.symbol, width=15).grid(row=0, column=1, padx=5, pady=2)
        
        # 시간단위 선택
        ttk.Label(trade_frame, text="시간단위:").grid(row=0, column=2, padx=5, pady=2)
        interval_combo = ttk.Combobox(trade_frame, textvariable=self.interval, width=10)
        interval_combo['values'] = ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d')
        interval_combo.grid(row=0, column=3, padx=5, pady=2)
        interval_combo.set('1m')
        
        # 다중 티커 테스트 버튼 추가
        self.multi_test_button = ttk.Button(trade_frame, text="다중 티커 테스트", command=self.test_multiple_symbols)
        self.multi_test_button.grid(row=0, column=4, padx=5, pady=2)
        
        # 전략 선택
        ttk.Label(main_frame, text="매매 전략:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.strategy_combo = ttk.Combobox(main_frame, values=["RSI + MACD + 스토캐스틱"], textvariable=self.strategy)
        self.strategy_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.strategy_combo.set("RSI + MACD + 스토캐스틱")
        
        # 전략 파라미터 표
        self.param_frame = ttk.LabelFrame(main_frame, text="전략 파라미터", padding="5")
        self.param_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 파라미터 표 헤더
        self.param_headers = ["파라미터", "값"]
        for col, header in enumerate(self.param_headers):
            ttk.Label(self.param_frame, text=header).grid(row=0, column=col, padx=5, pady=2)
        
        # 파라미터 표 내용
        self.param_entries = []
        params = [
            ("RSI 기간", "14"),
            ("MACD Fast", "12"),
            ("MACD Slow", "26"),
            ("MACD Signal", "9"),
            ("스토캐스틱 K", "14"),
            ("스토캐스틱 D", "3"),
            ("스토캐스틱 Slowing", "3")
        ]
        
        for i, (param_name, default_value) in enumerate(params, 1):
            ttk.Label(self.param_frame, text=param_name).grid(row=i, column=0, padx=5, pady=2)
            entry = ttk.Entry(self.param_frame, width=15)
            entry.insert(0, default_value)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.param_entries.append(entry)
        
        # 진입 방법
        ttk.Label(main_frame, text="진입 방법:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.entry_combo = ttk.Combobox(main_frame, values=["시장가", "지정가"])
        self.entry_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.entry_combo.set("시장가")
        
        # 투입 비율
        ttk.Label(main_frame, text="투입 비율 (%):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.investment_spin = ttk.Spinbox(main_frame, from_=1, to=100, width=10)
        self.investment_spin.grid(row=4, column=1, sticky=tk.W, pady=5)
        self.investment_spin.set(100)
        
        # 레버리지
        ttk.Label(main_frame, text="레버리지:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.leverage_spin = ttk.Spinbox(main_frame, from_=1, to=125, width=10)
        self.leverage_spin.grid(row=5, column=1, sticky=tk.W, pady=5)
        self.leverage_spin.set(1)
        
        # 백테스팅 기간
        ttk.Label(main_frame, text="조회 기간 (일):").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.period_spin = ttk.Spinbox(main_frame, from_=1, to=365, width=10)
        self.period_spin.grid(row=6, column=1, sticky=tk.W, pady=5)
        self.period_spin.set(30)
        
        # 백테스팅 시작 버튼
        self.start_button = ttk.Button(main_frame, text="백테스팅 시작", command=self.start_backtest)
        self.start_button.grid(row=7, column=0, columnspan=2, pady=20)
        
        # 결과 표시 영역
        self.result_label = ttk.Label(main_frame, text="백테스팅 결과가 여기에 표시됩니다.")
        self.result_label.grid(row=8, column=0, columnspan=2, pady=10)
        
    def log(self, message):
        """로그 메시지 추가"""
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)  # 자동 스크롤
        self.root.update()

    def get_historical_data(self):
        """바이낸스에서 과거 데이터 가져오기"""
        try:
            self.log("데이터 수집을 시작합니다...")
            
            # 심볼 설정
            symbol = self.symbol.get()
            
            # 기간 설정
            days = int(self.period_spin.get())
            self.log(f"조회 기간: {days}일")
            
            # 시간단위 설정
            interval = self.interval.get()
            self.log(f"시간 간격: {interval}")
            
            # 데이터 가져오기
            self.log("바이낸스에서 데이터를 가져오는 중...")
            klines = self.client.get_historical_klines(
                symbol,
                interval,
                str(days) + " days ago UTC"
            )
            
            # 데이터프레임으로 변환
            self.log("데이터 변환 중...")
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df.set_index('timestamp', inplace=True)
            self.log(f"데이터 수집 완료: {len(df)}개의 캔들")
            return df
            
        except Exception as e:
            self.log(f"에러 발생: {str(e)}")
            messagebox.showerror("에러", f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
            return None
        
    def start_backtest(self):
        """백테스팅 실행"""
        try:
            self.log("백테스팅을 시작합니다...")
            
            # 데이터 가져오기
            data = self.get_historical_data()
            if data is None:
                return
            
            # 백테스팅 실행
            self.log("백테스팅 실행 중...")
            backtest = Backtest(data)
            results = backtest.run()
            
            # 결과 표시
            result_text = f"""
            총 거래 횟수: {results['total_trades']}
            승률: {results['win_rate']:.2%}
            수익률: {results['total_return']:.2%}
            최대 손실폭: {results['max_drawdown']:.2%}
            수익 팩터: {results['profit_factor']:.2f}
            """
            self.result_label.config(text=result_text)
            
            # 로그에 상세 결과 표시
            self.log("\n=== 백테스팅 결과 ===")
            self.log(f"총 거래 횟수: {results['total_trades']}회")
            self.log(f"승률: {results['win_rate']:.2%}")
            self.log(f"총 수익률: {results['total_return']:.2%}")
            self.log(f"최대 손실폭: {results['max_drawdown']:.2%}")
            self.log(f"수익 팩터: {results['profit_factor']:.2f}")
            self.log("===================\n")
            
        except Exception as e:
            self.log(f"에러 발생: {str(e)}")
            messagebox.showerror("에러", f"백테스팅 중 오류가 발생했습니다: {str(e)}")

    def cancel_operation(self):
        """작업 취소"""
        self.cancel_flag = True
        self.log("작업 취소 요청됨...")
        self.cancel_button.grid_remove()
        self.progress_label.config(text="")

    def show_progress(self, message):
        """진행 상태 표시"""
        self.progress_label.config(text=message)
        self.cancel_button.grid()
        self.root.update()

    def hide_progress(self):
        """진행 상태 숨기기"""
        self.progress_label.config(text="")
        self.cancel_button.grid_remove()
        self.cancel_flag = False
        self.root.update()

    def find_high_volatility_symbols(self):
        """변동성이 높은 티커 찾기"""
        try:
            self.log("변동성이 높은 티커를 찾는 중...")
            volatility_data = []
            
            # 각 티커의 24시간 데이터 가져오기
            total_symbols = len(self.futures_symbols)
            for i, symbol in enumerate(self.futures_symbols, 1):
                if self.cancel_flag:
                    self.log("작업이 취소되었습니다.")
                    return []
                
                self.show_progress(f"변동성 분석 중... ({i}/{total_symbols})")
                
                try:
                    # 24시간 티커 정보
                    ticker = self.client.futures_ticker(symbol=symbol)
                    
                    # 변동성 계산 (고가-저가)/시가 * 100
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
                    
                    self.log(f"{symbol} 변동성: {volatility:.2f}%")
                    
                except Exception as e:
                    self.log(f"{symbol} 데이터 가져오기 실패: {str(e)}")
                    continue
            
            self.hide_progress()
            
            if not volatility_data:
                self.log("변동성 데이터를 가져올 수 없습니다.")
                return []
            
            # 변동성 기준으로 정렬
            volatility_data.sort(key=lambda x: x['volatility'], reverse=True)
            
            # 상위 20개 티커 선택
            top_volatile = volatility_data[:20]
            
            # 거래량 기준으로 필터링 (상위 50%만 선택)
            volume_threshold = sorted([x['volume'] for x in top_volatile])[len(top_volatile)//2]
            filtered_symbols = [x['symbol'] for x in top_volatile if x['volume'] >= volume_threshold]
            
            self.log("\n=== 변동성이 높은 티커 목록 ===")
            for i, symbol in enumerate(filtered_symbols[:10], 1):
                data = next(x for x in volatility_data if x['symbol'] == symbol)
                self.log(f"{i}. {symbol}")
                self.log(f"   변동성: {data['volatility']:.2f}%")
                self.log(f"   거래량: {data['volume']:,.0f}")
            
            return filtered_symbols[:10]  # 상위 10개만 반환
            
        except Exception as e:
            self.log(f"변동성 분석 중 오류 발생: {str(e)}")
            self.hide_progress()
            return []

    def test_multiple_symbols(self):
        """여러 티커를 테스트하고 수익 팩터 기반으로 투자"""
        try:
            self.log("다중 티커 테스트를 시작합니다...")
            
            # 변동성이 높은 티커 찾기
            volatile_symbols = self.find_high_volatility_symbols()
            if not volatile_symbols:
                self.log("변동성이 높은 티커를 찾을 수 없습니다.")
                return
            
            results = []
            
            # 각 티커에 대해 백테스팅 실행
            total_symbols = len(volatile_symbols)
            for i, symbol in enumerate(volatile_symbols, 1):
                if self.cancel_flag:
                    self.log("작업이 취소되었습니다.")
                    return
                
                self.show_progress(f"백테스팅 중... ({i}/{total_symbols})")
                
                self.log(f"\n{symbol} 테스트 중...")
                self.symbol.set(symbol)
                
                # 데이터 가져오기
                data = self.get_historical_data()
                if data is None:
                    continue
                
                # 백테스팅 실행
                backtest = Backtest(data)
                result = backtest.run()
                
                # 결과 저장
                results.append({
                    'symbol': symbol,
                    'profit_factor': result['profit_factor'],
                    'total_return': result['total_return'],
                    'win_rate': result['win_rate'],
                    'max_drawdown': result['max_drawdown']
                })
                
                self.log(f"{symbol} 테스트 완료:")
                self.log(f"수익 팩터: {result['profit_factor']:.2f}")
                self.log(f"총 수익률: {result['total_return']:.2%}")
                self.log(f"승률: {result['win_rate']:.2%}")
                self.log(f"최대 손실폭: {result['max_drawdown']:.2%}")
            
            self.hide_progress()
            
            if not results:
                self.log("백테스팅 결과가 없습니다.")
                return
            
            # 수익 팩터 기준으로 정렬
            results.sort(key=lambda x: x['profit_factor'], reverse=True)
            
            # 상위 3개 티커 선택
            top_symbols = results[:3]
            
            self.log("\n=== 최종 투자 추천 ===")
            self.log("수익 팩터 기준 상위 3개 티커:")
            for i, result in enumerate(top_symbols, 1):
                self.log(f"\n{i}위: {result['symbol']}")
                self.log(f"수익 팩터: {result['profit_factor']:.2f}")
                self.log(f"총 수익률: {result['total_return']:.2%}")
                self.log(f"승률: {result['win_rate']:.2%}")
                self.log(f"최대 손실폭: {result['max_drawdown']:.2%}")
                self.log(f"투자 비중: 10%")
            
            # 결과를 CSV 파일로 저장
            df = pd.DataFrame(results)
            df.to_csv('symbol_test_results.csv', index=False, encoding='utf-8-sig')
            self.log("\n테스트 결과가 'symbol_test_results.csv' 파일로 저장되었습니다.")
            
        except Exception as e:
            self.log(f"에러 발생: {str(e)}")
            self.hide_progress()
            messagebox.showerror("에러", f"다중 티커 테스트 중 오류가 발생했습니다: {str(e)}")

class AutoTrader:
    def __init__(self, symbol, interval='1m', leverage=1):
        # 환경 변수 로드
        load_dotenv()
        
        # API 클라이언트 초기화
        self.client = Client(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_API_SECRET')
        )
        
        self.symbol = symbol
        self.interval = interval
        self.leverage = leverage
        self.position = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.quantity = 0
        self.oversold = 0
        
        # 수수료와 슬리피지 설정
        self.commission_rate = 0.0002  # 0.02% 수수료
        self.slippage_rate = 0.0002    # 0.02% 슬리피지
        
        # 레버리지 설정
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logging.info(f"레버리지 {leverage}x로 설정 완료")
        except BinanceAPIException as e:
            logging.error(f"레버리지 설정 실패: {str(e)}")
            raise
    
    def get_historical_data(self, limit=100):
        """과거 데이터 가져오기"""
        try:
            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval=self.interval,
                limit=limit
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
        except BinanceAPIException as e:
            logging.error(f"데이터 가져오기 실패: {str(e)}")
            return None
    
    def calculate_indicators(self, data):
        """기술적 지표 계산"""
        # RSI
        data['rsi'] = TechnicalIndicators.calculate_rsi(data['close'])
        
        # MACD
        data['macd'], data['signal'] = TechnicalIndicators.calculate_macd(data['close'])
        data['macd_crossover'] = TechnicalIndicators.find_macd_crossovers(data['macd'], data['signal'])
        
        # 스토캐스틱
        data['stoch_k'], data['stoch_d'] = TechnicalIndicators.calculate_stochastic(data)
        
        return data
    
    def find_last_macd_death_cross_low(self, data):
        """MACD 데드크로스 이후의 최저가 찾기"""
        death_crosses = data[data['macd_crossover'] == -1]
        
        if len(death_crosses) == 0:
            return None
            
        last_death_cross = death_crosses.index[-1]
        low_after_death = data.loc[last_death_cross:, 'low'].min()
        return low_after_death
    
    def get_account_balance(self):
        """계정 잔고 조회"""
        try:
            account = self.client.futures_account_balance()
            for balance in account:
                if balance['asset'] == 'USDT':
                    return float(balance['balance'])
            return 0
        except BinanceAPIException as e:
            logging.error(f"잔고 조회 실패: {str(e)}")
            return 0
    
    def place_order(self, side, quantity, price=None, stop_price=None, take_profit_price=None):
        """주문 실행"""
        try:
            # 메인 주문
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type='LIMIT' if price else 'MARKET',
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
            
            # 스탑로스 주문
            if stop_price:
                self.client.futures_create_order(
                    symbol=self.symbol,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='STOP_MARKET',
                    stopPrice=stop_price,
                    closePosition=True
                )
            
            # 익절 주문
            if take_profit_price:
                self.client.futures_create_order(
                    symbol=self.symbol,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=take_profit_price,
                    closePosition=True
                )
            
            logging.info(f"주문 실행 완료: {side} {quantity} {self.symbol}")
            return order
        except BinanceAPIException as e:
            logging.error(f"주문 실행 실패: {str(e)}")
            return None
    
    def run(self):
        """트레이딩 실행"""
        logging.info(f"트레이딩 시작: {self.symbol}")
        
        while True:
            try:
                # 과거 데이터 가져오기
                data = self.get_historical_data()
                if data is None:
                    time.sleep(60)
                    continue
                
                # 지표 계산
                data = self.calculate_indicators(data)
                
                # 현재 가격과 지표값
                current_price = float(data['close'].iloc[-1])
                stoch_k = data['stoch_k'].iloc[-1]
                stoch_d = data['stoch_d'].iloc[-1]
                rsi = data['rsi'].iloc[-1]
                macd = data['macd'].iloc[-1]
                signal = data['signal'].iloc[-1]
                
                # 과매도 구간 진입 확인
                if stoch_k < 20 and stoch_d < 20:
                    self.oversold = 1
                
                # 포지션이 없는 경우 진입 조건 확인
                if self.position == 0:
                    # 1차 조건: 과매도 구간에 진입했다가 상향돌파
                    first_condition = (
                        self.oversold == 1 and
                        stoch_k >= 20 and
                        stoch_d >= 20
                    )
                    
                    # 2차 조건: RSI 중간선 돌파, MACD 상향, 과매수 구간 아님
                    second_condition = (
                        rsi > 50 and
                        macd > signal and
                        stoch_k < 80 and
                        stoch_d < 80
                    )
                    
                    # 두 조건 모두 만족하면 진입
                    if first_condition and second_condition:
                        # 진입 수량 계산
                        balance = self.get_account_balance()
                        quantity = (balance * 0.95 * self.leverage) / current_price
                        quantity = round(quantity, 3)  # 수량 반올림
                        
                        # 주문 실행
                        order = self.place_order('BUY', quantity)
                        if order:
                            self.position = 1
                            self.entry_price = current_price
                            self.quantity = quantity
                            self.oversold = 0
                            
                            # 손절가 설정
                            stop_loss = self.find_last_macd_death_cross_low(data)
                            if stop_loss is None:
                                stop_loss = current_price * 0.95
                            
                            # 익절가 설정
                            take_profit = stop_loss + (current_price - stop_loss) * 1.5
                            
                            # 스탑로스와 익절 주문
                            self.place_order('SELL', quantity, stop_price=stop_loss, take_profit_price=take_profit)
                            
                            logging.info(f"포지션 진입: 가격={current_price}, 수량={quantity}, 손절={stop_loss}, 익절={take_profit}")
                
                time.sleep(60)  # 1분 대기
                
            except Exception as e:
                logging.error(f"오류 발생: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    # 거래 설정
    SYMBOL = "BTCUSDT"
    INTERVAL = "1m"
    LEVERAGE = 1
    
    # 트레이더 실행
    trader = AutoTrader(SYMBOL, INTERVAL, LEVERAGE)
    trader.run() 