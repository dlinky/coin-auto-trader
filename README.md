# 🚀 바이낸스 선물 자동 거래 시스템

바이낸스 선물 거래를 위한 자동화된 매매 시스템입니다. 백테스팅 기반 전략 최적화, 포트폴리오 자동 구성, 실시간 거래 기능을 제공합니다.

## 📋 주요 기능

### 1. 자동매매
- **포트폴리오 자동 구성**: 백테스팅으로 최적 티커/전략 매칭을 자동으로 찾아 포트폴리오 구성
- **수동 설정 매매**: 사용자가 직접 설정한 파라미터로 단일 코인 매매
- **24시간 결과 저장**: 매매 결과를 24시간마다 자동으로 파일로 저장

### 2. 전략 최적화
- **RSI 전략 최적화**: RSI 기반 매매 전략의 파라미터 자동 튜닝
- **이동평균 전략 최적화**: 이동평균 크로스오버 전략의 파라미터 자동 튜닝
- **최적화 결과 저장**: 최적화된 파라미터를 파일로 저장하고 관리

### 3. 고변동성 코인 찾기
- 거래량과 변동성을 기준으로 스캘핑에 적합한 코인 자동 탐지

## 🏗️ 시스템 구조

### 메인 모듈 (`main.py`)

#### 1. 데이터 수집 및 분석
- `get_major_coins()`: 거래량 기준 주요 코인 동적 탐지
- `get_volatile_coins()`: 고변동성 코인 탐지
- `get_price_data()`: 바이낸스 API를 통한 가격 데이터 수집

#### 2. 전략 구현
- `simple_ma_strategy()`: 이동평균 크로스오버 전략
- `rsi_strategy()`: RSI + 추세선 돌파 전략 (고급 필터)
- `calculate_rsi()`: RSI 지표 계산
- `find_pivot_points()`: 피벗 포인트 탐지
- `calculate_trendline()`: 추세선 계산

#### 3. 백테스팅 엔진 (`BacktestEngine`)
- `run_backtest()`: 백테스트 실행
- `execute_trade()`: 거래 실행 (레버리지 고려)
- `check_risk_management()`: 리스크 관리 (손절, 익절, 시간 제한)
- `generate_backtest_report()`: 백테스트 결과 리포트 생성

#### 4. 전략 최적화 엔진 (`StrategyOptimizer`)
- `optimize_strategy()`: 전략 파라미터 최적화
- `_generate_combinations()`: 파라미터 조합 생성
- `_run_backtest_with_params()`: 특정 파라미터로 백테스트 실행

#### 5. 거래 추적기 (`TradingTracker`)
- `add_trade()`: 거래 내역 추가
- `calculate_performance()`: 성과 계산
- `save_trading_log()`: 거래 로그 저장
- `save_daily_report()`: 24시간 결과 저장

#### 6. 메뉴 시스템
- `auto_trading_menu()`: 자동매매 메뉴
- `portfolio_auto_config()`: 포트폴리오 자동 구성
- `manual_trading_config()`: 수동 매매 설정
- `strategy_optimization_menu()`: 전략 최적화 메뉴

## 🎯 프로그램 진행 순서

### 0) 프로그램 실행
```bash
python main.py
```

### 1) 자동매매
#### 1-1) 매매할 방법 선택
- **포트폴리오 자동 구성**: 백테스팅으로 최적 조합 자동 선택
- **수동 설정**: 사용자가 직접 파라미터 설정

#### 1-1-1) 포트폴리오 자동 구성
1. 분석할 코인 수 선택 (5-20개)
2. 분석 기간 선택 (3-30일)
3. 각 코인에 대해 RSI/MA 전략 백테스팅 실행
4. 수익률 기준으로 순위 정렬
5. 사용자가 원하는 개수만큼 포트폴리오 구성
6. 포트폴리오 설정 파일로 저장
7. 매매 시작 여부 확인

#### 1-2) 매매 시작
- 중지 명령을 내릴 때까지 계속 매매
- 24시간마다 매매 결과를 파일로 자동 저장

### 2) 전략 최적화
#### 2-1) 튜닝할 전략 선택
- RSI 전략 최적화
- 이동평균 전략 최적화

#### 2-2) 테스트 설정
- 테스트할 티커 선택
- 타임프레임 선택
- 최적화 기간 설정

#### 2-3) 최적화 실행 및 저장
- 다양한 파라미터 조합으로 백테스트 실행
- 최적 파라미터 자동 선택
- 결과를 JSON 파일로 저장

## 📊 전략 파라미터

### RSI 전략
```python
{
    'rsi_buy': 30,           # RSI 매수 조건
    'rsi_sell': 70,          # RSI 매도 조건
    'stop_loss': -0.015,     # 손절 비율 (-1.5%)
    'take_profit': 0.03,     # 익절 비율 (+3%)
    'max_hold_hours': 24,    # 최대 보유 시간
    'volume_ratio': 0.8,     # 거래량 비율
    'support_distance': 0.02 # 지지선 거리
}
```

### 이동평균 전략
```python
{
    'short_period': 5,       # 단기 이동평균
    'long_period': 20,       # 장기 이동평균
    'stop_loss': -0.02,      # 손절 비율 (-2%)
    'take_profit': 0.03,     # 익절 비율 (+3%)
    'max_hold_hours': 24     # 최대 보유 시간
}
```

## 🔧 설정 파일

### 환경 설정 (`.env`)
```
API_KEY=your_binance_api_key
SECRET_KEY=your_binance_secret_key
```

### 포트폴리오 설정 (`portfolio_config_*.json`)
```json
{
    "timestamp": "2024-01-01T12:00:00",
    "portfolio": [
        {
            "symbol": "BTC/USDT:USDT",
            "strategy": "rsi",
            "params": {...},
            "return": 5.2,
            "win_rate": 65.0,
            "max_drawdown": 2.1
        }
    ]
}
```

### 최적화 결과 (`optimization_*.json`)
```json
{
    "strategy": "rsi",
    "timestamp": "2024-01-01T12:00:00",
    "best_params": {...},
    "best_result": {
        "total_return": 5.2,
        "win_rate": 65.0,
        "max_drawdown": 2.1
    }
}
```

## 📈 거래 결과 파일

### 24시간 리포트 (`daily_report_*.json`)
```json
{
    "timestamp": "2024-01-01T12:00:00",
    "performance": {
        "total_trades": 15,
        "pnl": 125.50,
        "pnl_percentage": 1.25
    },
    "trades_count": 15,
    "trading_duration": "1 day, 0:00:00"
}
```

### 거래 로그 (`trading_log_*.json`)
```json
{
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-02T00:00:00",
    "trades": [...],
    "performance": {...}
}
```

## ⚠️ 주의사항

1. **API 키 보안**: `.env` 파일에 API 키를 저장하고, 절대 공개하지 마세요.
2. **리스크 관리**: 자동 거래는 위험할 수 있으므로, 충분한 테스트 후 사용하세요.
3. **자본 관리**: 전체 자본의 일부만 사용하여 리스크를 제한하세요.
4. **모니터링**: 자동 거래 중에는 정기적으로 성과를 확인하세요.

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install ccxt pandas numpy
```

### 2. 환경 설정
```bash
# .env 파일 생성
echo "API_KEY=your_binance_api_key" > .env
echo "SECRET_KEY=your_binance_secret_key" >> .env
```

### 3. 프로그램 실행
```bash
python main.py
```

## 📝 로직 타당성 점검

### 메인 로직 흐름
1. **메인 메뉴**: 계층적 메뉴 구조로 사용자 친화적 인터페이스
2. **포트폴리오 구성**: 백테스팅 기반 객관적 코인/전략 선택
3. **전략 최적화**: 파라미터 자동 튜닝으로 성과 최적화
4. **실시간 거래**: 24시간 결과 저장으로 지속적 모니터링

### 데이터 처리
- **API 제한 고려**: 바이낸스 API 호출 제한을 고려한 데이터 수집
- **중복 제거**: 심볼 중복 및 데이터 중복 제거
- **에러 처리**: API 오류 및 네트워크 문제에 대한 예외 처리

### 리스크 관리
- **손절/익절**: 자동 손절매 및 익절매
- **시간 제한**: 최대 보유 시간 설정
- **포지션 관리**: 단일 포지션으로 추격매수 방지

이 시스템은 체계적인 접근으로 자동 거래의 위험을 최소화하면서도 효율적인 수익을 추구할 수 있도록 설계되었습니다. 