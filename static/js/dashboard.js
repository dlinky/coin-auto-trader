// 전역 변수
let isTrading = false;
let updateInterval;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    loadPerformanceData();
    loadRecentTrades();
    loadTradingStatus();
    
    // 5초마다 데이터 업데이트
    updateInterval = setInterval(function() {
        if (!isTrading) {
            loadPerformanceData();
            loadRecentTrades();
        }
    }, 5000);
    
    // 이벤트 리스너 등록
    setupEventListeners();
    
    // 전략 선택 시 추천 티커 자동 노출
    document.getElementById('strategy-select').addEventListener('change', recommendSymbolsByStrategy);
    // 고변동성 코인 불러오기 버튼 추가
    const symbolSelect = document.getElementById('symbol-select');
    if (symbolSelect && !document.getElementById('volatile-btn')) {
        const btn = document.createElement('button');
        btn.id = 'volatile-btn';
        btn.className = 'btn btn-outline-info btn-sm ms-2';
        btn.innerText = '고변동성 코인 불러오기';
        btn.onclick = function(e) {
            e.preventDefault();
            loadVolatileCoinsAndRecommend();
        };
        symbolSelect.parentNode.appendChild(btn);
    }
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 거래 시작 버튼
    document.getElementById('start-trading').addEventListener('click', startTrading);
    
    // 거래 중지 버튼
    document.getElementById('stop-trading').addEventListener('click', stopTrading);
}

// 성과 데이터 로드
async function loadPerformanceData() {
    try {
        const response = await fetch('/api/performance');
        const data = await response.json();
        
        if (data.success) {
            updatePerformanceDisplay(data.data);
        } else {
            console.error('성과 데이터 로드 실패:', data.error);
        }
    } catch (error) {
        console.error('API 호출 오류:', error);
    }
}

// 성과 표시 업데이트
function updatePerformanceDisplay(data) {
    document.getElementById('total-return').textContent = data.total_pnl_percentage.toFixed(2) + '%';
    document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
    document.getElementById('total-trades').textContent = data.total_trades;
    document.getElementById('current-balance').textContent = '$' + data.current_balance.toLocaleString();
    
    // 수익률에 따른 색상 변경
    const totalReturnElement = document.getElementById('total-return');
    if (data.total_pnl_percentage > 0) {
        totalReturnElement.style.color = '#28a745';
    } else if (data.total_pnl_percentage < 0) {
        totalReturnElement.style.color = '#dc3545';
    } else {
        totalReturnElement.style.color = '#fff';
    }
}

// 최근 거래 내역 로드
async function loadRecentTrades() {
    try {
        const response = await fetch('/api/recent_trades');
        const data = await response.json();
        
        if (data.success) {
            updateTradesTable(data.data);
        } else {
            console.error('거래 내역 로드 실패:', data.error);
        }
    } catch (error) {
        console.error('API 호출 오류:', error);
    }
}

// 거래 테이블 업데이트
function updateTradesTable(trades) {
    const tbody = document.getElementById('trades-table');
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">거래 내역이 없습니다.</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        
        const timestamp = new Date(trade.timestamp).toLocaleString('ko-KR');
        const typeClass = trade.type === 'buy' ? 'trade-buy' : 'trade-sell';
        const typeText = trade.type === 'buy' ? '매수' : '매도';
        
        row.innerHTML = `
            <td>${timestamp}</td>
            <td class="${typeClass}">${typeText}</td>
            <td>${trade.symbol}</td>
            <td>${parseFloat(trade.amount).toFixed(4)}</td>
            <td>$${parseFloat(trade.price).toFixed(2)}</td>
            <td>$${parseFloat(trade.value).toFixed(2)}</td>
        `;
        
        tbody.appendChild(row);
    });
}

// 거래 상태 로드
async function loadTradingStatus() {
    try {
        const response = await fetch('/api/trading_status');
        const data = await response.json();
        
        if (data.success) {
            updateTradingButtons(data.data.is_trading);
        }
    } catch (error) {
        console.error('거래 상태 로드 오류:', error);
    }
}

// 거래 버튼 상태 업데이트
function updateTradingButtons(trading) {
    const startBtn = document.getElementById('start-trading');
    const stopBtn = document.getElementById('stop-trading');
    
    if (trading) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        isTrading = true;
    } else {
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        isTrading = false;
    }
}

// 거래 시작
async function startTrading() {
    const strategy = document.getElementById('strategy-select').value;
    const symbol = document.getElementById('symbol-select').value;
    const timeframe = document.getElementById('timeframe-select').value;
    
    // 버튼 로딩 상태
    const startBtn = document.getElementById('start-trading');
    const originalText = startBtn.innerHTML;
    startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 시작 중...';
    startBtn.disabled = true;
    
    try {
        const response = await fetch('/api/start_trading', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                strategy: strategy,
                symbol: symbol,
                timeframe: timeframe
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('success', data.message);
            updateTradingButtons(true);
            
            // 실시간 업데이트 시작
            startRealTimeUpdates();
        } else {
            showAlert('danger', '거래 시작 실패: ' + data.error);
        }
    } catch (error) {
        console.error('거래 시작 오류:', error);
        showAlert('danger', '거래 시작 중 오류가 발생했습니다.');
    } finally {
        // 버튼 상태 복원
        startBtn.innerHTML = originalText;
        startBtn.disabled = false;
    }
}

// 거래 중지
async function stopTrading() {
    const stopBtn = document.getElementById('stop-trading');
    const originalText = stopBtn.innerHTML;
    stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 중지 중...';
    stopBtn.disabled = true;
    
    try {
        const response = await fetch('/api/stop_trading', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('success', data.message);
            updateTradingButtons(false);
            
            // 실시간 업데이트 중지
            stopRealTimeUpdates();
        } else {
            showAlert('danger', '거래 중지 실패: ' + data.error);
        }
    } catch (error) {
        console.error('거래 중지 오류:', error);
        showAlert('danger', '거래 중지 중 오류가 발생했습니다.');
    } finally {
        // 버튼 상태 복원
        stopBtn.innerHTML = originalText;
        stopBtn.disabled = false;
    }
}

// 실시간 업데이트 시작
function startRealTimeUpdates() {
    // 기존 업데이트 중지
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // 1초마다 실시간 업데이트
    updateInterval = setInterval(function() {
        loadPerformanceData();
        loadRecentTrades();
    }, 1000);
}

// 실시간 업데이트 중지
function stopRealTimeUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // 5초마다 일반 업데이트로 변경
    updateInterval = setInterval(function() {
        loadPerformanceData();
        loadRecentTrades();
    }, 5000);
}

// 알림 표시
function showAlert(type, message) {
    // 기존 알림 제거
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // 새 알림 생성
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 페이지 상단에 추가
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});

// 고변동성 코인 불러오기 및 추천 티커 기능 추가
function loadVolatileCoinsAndRecommend() {
    fetch('/api/volatile_coins')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const coins = data.coins || data.data;
                const symbolSelect = document.getElementById('symbol-select');
                // 기존 옵션 제거 후 대형주 2개 + 고변동성 옵션 추가
                symbolSelect.innerHTML = '';
                symbolSelect.innerHTML += '<option value="BTC/USDT:USDT">BTC/USDT</option>';
                symbolSelect.innerHTML += '<option value="ETH/USDT:USDT">ETH/USDT</option>';
                symbolSelect.innerHTML += '<option disabled>──────────────</option>';
                coins.forEach(coin => {
                    symbolSelect.innerHTML += `<option value="${coin.symbol}">${coin.symbol.replace(':USDT','')}</option>`;
                });
            }
        });
}

// 전략 선택 시 추천 티커 자동 노출
function recommendSymbolsByStrategy() {
    const strategy = document.getElementById('strategy-select').value;
    if (strategy === 'rsi') {
        // RSI/스캘핑은 고변동성 추천
        loadVolatileCoinsAndRecommend();
    } else {
        // MA 등은 대형주 추천
        const symbolSelect = document.getElementById('symbol-select');
        symbolSelect.innerHTML = '';
        symbolSelect.innerHTML += '<option value="BTC/USDT:USDT">BTC/USDT</option>';
        symbolSelect.innerHTML += '<option value="ETH/USDT:USDT">ETH/USDT</option>';
    }
} 