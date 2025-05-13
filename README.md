# 바이낸스 선물 자동매매 시스템

이 프로젝트는 바이낸스 선물 시장에서 변동성이 높은 코인을 찾아 자동으로 매매하는 시스템입니다.

## 주요 기능

- 변동성이 높은 선물 티커 자동 탐색
- 다중 티커 백테스팅
- 웹 기반 모니터링 인터페이스
- 실시간 거래 신호 생성

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 바이낸스 API 키 설정:
- `.env` 파일을 생성하고 다음 내용을 추가:
```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

## 실행 방법

1. 웹 서버 실행:
```bash
python app.py
```

2. 브라우저에서 접속:
```
http://localhost:5000
```

## 백그라운드 실행 (24/7)

```bash
nohup python app.py > autotrade.log 2>&1 &
```

## 로그 확인

```bash
tail -f autotrade.log
```

## 주의사항

- 실제 거래에 사용하기 전에 반드시 백테스팅을 통해 전략을 검증하세요.
- API 키는 절대 공개되지 않도록 주의하세요.
- 거래는 항상 리스크 관리 원칙을 준수하세요. # coin-auto-trader
