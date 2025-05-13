import numpy as np
import pandas as pd

class TechnicalIndicators:
    @staticmethod
    def calculate_rsi(data, period=14):
        """RSI 계산"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_macd(data, fast=12, slow=26, signal=9):
        """MACD 계산"""
        exp1 = data.ewm(span=fast, adjust=False).mean()
        exp2 = data.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    @staticmethod
    def calculate_stochastic(data, k_period=14, d_period=3, slowing=3):
        """스토캐스틱 계산"""
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()
        
        k = 100 * ((data['close'] - low_min) / (high_max - low_min))
        k = k.rolling(window=slowing).mean()
        d = k.rolling(window=d_period).mean()
        
        return k, d

    @staticmethod
    def find_macd_crossovers(macd, signal):
        """MACD 크로스오버 포인트 찾기"""
        crossovers = pd.Series(0, index=macd.index)
        crossovers[macd > signal] = 1  # 골든 크로스
        crossovers[macd < signal] = -1  # 데드 크로스
        return crossovers.diff()  # 1: 상향돌파, -1: 하향돌파, 0: 변화없음 