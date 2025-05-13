import pandas as pd
import numpy as np
from indicators import TechnicalIndicators

class Backtest:
    def __init__(self, data, initial_capital=10000, leverage=1):
        self.data = data
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage  # 레버리지 추가
        self.positions = pd.DataFrame(index=data.index)
        self.positions['position'] = 0
        self.positions['entry_price'] = 0.0
        self.positions['stop_loss'] = 0.0
        self.positions['take_profit'] = 0.0
        self.positions['pnl'] = 0.0
        self.positions['oversold'] = 0
        self.positions['quantity'] = 0.0  # 보유 수량
        
        # 수수료와 슬리피지 설정
        self.commission_rate = 0.0002  # 0.02% 수수료 (바이낸스 지정가 주문)
        self.slippage_rate = 0.0002    # 0.02% 슬리피지
        
        # 지표 계산
        self.calculate_indicators()
        
    def calculate_indicators(self):
        """모든 기술적 지표 계산"""
        # RSI
        self.data['rsi'] = TechnicalIndicators.calculate_rsi(self.data['close'])
        
        # MACD
        self.data['macd'], self.data['signal'] = TechnicalIndicators.calculate_macd(self.data['close'])
        self.data['macd_crossover'] = TechnicalIndicators.find_macd_crossovers(self.data['macd'], self.data['signal'])
        
        # 스토캐스틱
        self.data['stoch_k'], self.data['stoch_d'] = TechnicalIndicators.calculate_stochastic(self.data)
        
    def find_last_macd_death_cross_low(self, current_idx):
        """현재 시점에서 가장 최근 MACD 데드크로스 이후의 최저가 찾기"""
        current_time = self.data.index[current_idx]
        current_data = self.data.loc[:current_time]
        death_crosses = current_data[current_data['macd_crossover'] == -1]
        
        if len(death_crosses) == 0:
            return None
            
        last_death_cross = death_crosses.index[-1]
        low_after_death = current_data.loc[last_death_cross:current_time, 'low'].min()
        return low_after_death
        
    def run(self):
        """백테스팅 실행"""
        # 로그 데이터를 저장할 리스트
        log_data = []
        
        for i in range(len(self.data)):
            if i < 50:  # 초기 데이터는 스킵
                continue
                
            current_price = self.data['close'].iloc[i]
            current_time = self.data.index[i]
            prev_time = self.data.index[i-1]
            
            # 이전 캔들의 포지션 정보 복사
            self.positions.loc[current_time, 'position'] = self.positions.loc[prev_time, 'position']
            self.positions.loc[current_time, 'entry_price'] = self.positions.loc[prev_time, 'entry_price']
            self.positions.loc[current_time, 'stop_loss'] = self.positions.loc[prev_time, 'stop_loss']
            self.positions.loc[current_time, 'take_profit'] = self.positions.loc[prev_time, 'take_profit']
            self.positions.loc[current_time, 'quantity'] = self.positions.loc[prev_time, 'quantity']
            self.positions.loc[current_time, 'oversold'] = self.positions.loc[prev_time, 'oversold']
            
            # 지표값 계산
            stoch_k = self.data['stoch_k'].iloc[i]
            stoch_d = self.data['stoch_d'].iloc[i]
            rsi = self.data['rsi'].iloc[i]
            macd = self.data['macd'].iloc[i]
            signal = self.data['signal'].iloc[i]
            
            # 과매도 구간 진입 확인
            if stoch_k < 20 and stoch_d < 20:
                self.positions.loc[current_time, 'oversold'] = 1
            
            # 포지션이 없는 경우 진입 조건 확인
            if self.positions.loc[current_time, 'position'] == 0:
                # 1차 조건: 과매도 구간에 진입했다가 상향돌파
                first_condition = (
                    self.positions.loc[current_time, 'oversold'] == 1 and  # 과매도 구간 진입 기록이 있음
                    stoch_k >= 20 and  # K선이 20을 상향돌파
                    stoch_d >= 20      # D선이 20을 상향돌파
                )
                
                # 2차 조건: RSI 중간선 돌파, MACD 상향, 과매수 구간 아님
                second_condition = (
                    rsi > 50 and           # RSI 중간선 위
                    macd > signal and      # MACD가 시그널선 위
                    stoch_k < 80 and       # K선 과매수 아님
                    stoch_d < 80           # D선 과매수 아님
                )
                
                # 두 조건 모두 만족하면 진입
                if first_condition and second_condition:
                    # 진입 수량 계산 (자금의 95% 사용, 레버리지 적용)
                    entry_price = current_price * (1 + self.slippage_rate)  # 슬리피지 적용
                    quantity = (self.current_capital * 0.95 * self.leverage) / entry_price
                    
                    # 수수료 계산
                    commission = entry_price * quantity * self.commission_rate
                    self.current_capital -= commission
                    
                    # 포지션 진입
                    self.positions.loc[current_time, 'position'] = 1
                    self.positions.loc[current_time, 'entry_price'] = entry_price
                    self.positions.loc[current_time, 'quantity'] = quantity
                    self.positions.loc[current_time, 'oversold'] = 0  # 과매도 기록 초기화
                    
                    # 손절가 설정 (MACD 데드크로스 이후 최저가)
                    stop_loss = self.find_last_macd_death_cross_low(i)
                    if stop_loss is None:
                        stop_loss = entry_price * 0.95  # 기본값으로 5% 손절
                    self.positions.loc[current_time, 'stop_loss'] = stop_loss
                    
                    # 익절가 설정 (손절가 대비 1.5배)
                    self.positions.loc[current_time, 'take_profit'] = stop_loss + (entry_price - stop_loss) * 1.5
            
            # 포지션이 있는 경우 청산 조건 확인
            elif self.positions.loc[current_time, 'position'] == 1:
                entry_price = self.positions.loc[current_time, 'entry_price']
                stop_loss = self.positions.loc[current_time, 'stop_loss']
                take_profit = self.positions.loc[current_time, 'take_profit']
                quantity = self.positions.loc[current_time, 'quantity']
                
                # 손절 또는 익절 조건 확인
                if current_price <= stop_loss or current_price >= take_profit:
                    # 청산가 계산 (슬리피지 적용)
                    exit_price = current_price * (1 - self.slippage_rate)
                    
                    # 수수료 계산
                    commission = exit_price * quantity * self.commission_rate
                    
                    # 포지션 청산
                    self.positions.loc[current_time, 'position'] = 0
                    pnl = (exit_price - entry_price) / entry_price * self.leverage  # 레버리지 적용
                    self.positions.loc[current_time, 'pnl'] = pnl
                    
                    # 자금 업데이트 (수수료 차감)
                    self.current_capital *= (1 + pnl)
                    self.current_capital -= commission
                    
                    # 포지션 정보 초기화
                    self.positions.loc[current_time, 'entry_price'] = 0
                    self.positions.loc[current_time, 'stop_loss'] = 0
                    self.positions.loc[current_time, 'take_profit'] = 0
                    self.positions.loc[current_time, 'quantity'] = 0
            
            # 모든 캔들에 대해 로그 데이터 저장
            log_data.append({
                '시간': current_time,
                '가격': f"{current_price:.2f}",
                'K': f"{stoch_k:.2f}",
                'D': f"{stoch_d:.2f}",
                'RSI': f"{rsi:.2f}",
                'MACD': f"{macd:.2f}",
                'Signal': f"{signal:.2f}",
                '과매도': self.positions.loc[current_time, 'oversold'] == 1,
                'K>20': stoch_k >= 20,
                'D>20': stoch_d >= 20,
                'RSI>50': rsi > 50,
                'MACD>Signal': macd > signal,
                'K<80': stoch_k < 80,
                'D<80': stoch_d < 80,
                '포지션': self.positions.loc[current_time, 'position'],
                '수량': f"{self.positions.loc[current_time, 'quantity']:.4f}",
                '진입가': f"{self.positions.loc[current_time, 'entry_price']:.2f}",
                '손절가': f"{self.positions.loc[current_time, 'stop_loss']:.2f}",
                '익절가': f"{self.positions.loc[current_time, 'take_profit']:.2f}",
                '수익률': f"{self.positions.loc[current_time, 'pnl']:.2%}" if self.positions.loc[current_time, 'pnl'] != 0 else "",
                '자본금': f"{self.current_capital:.2f}"
            })
        
        # 로그 데이터를 DataFrame으로 변환하여 CSV 파일로 저장
        if log_data:
            log_df = pd.DataFrame(log_data)
            log_df.to_csv('backtest_log.csv', index=False, encoding='utf-8-sig')
            print("\n백테스팅 로그가 'backtest_log.csv' 파일로 저장되었습니다.")
            print(f"최종 자본금: {self.current_capital:.2f}")
            print(f"총 수익률: {((self.current_capital / self.initial_capital) - 1):.2%}")
        
        return self.calculate_performance()
    
    def calculate_performance(self):
        """백테스팅 성과 계산"""
        trades = self.positions[self.positions['pnl'] != 0]
        
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_return': 0,
                'max_drawdown': 0
            }
        
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        cumulative_returns = (1 + trades['pnl']).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1 if len(cumulative_returns) > 0 else 0
        
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = cumulative_returns / rolling_max - 1
        max_drawdown = drawdowns.min()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'max_drawdown': max_drawdown
        } 