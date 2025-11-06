// client/src/pages/Dashboard.jsx

import React, { useContext, useState, useEffect, useMemo } from 'react';
import apiClient from '../api/axiosConfig.js';
import { AuthContext } from '../context/AuthContext.jsx';
import AddTransactionForm from '../components/AddTransactionForm.jsx';
import TransactionList from '../components/TransactionList.jsx';
import StockSearch from '../components/StockSearch.jsx';
import PortfolioChart from '../components/PortfolioChart.jsx';
import Watchlist from '../components/Watchlist.jsx';
import axios from 'axios';

const PORTFOLIO_API_URL = '/portfolio';
const FINNHUB_API_KEY = import.meta.env.VITE_FINNHUB_API_KEY;
const FINNHUB_API_URL = 'https://finnhub.io/api/v1';

function Dashboard() {
    const { user, logout } = useContext(AuthContext);
    const [transactions, setTransactions] = useState([]);
    const [holdings, setHoldings] = useState([]);
    const [realizedPnL, setRealizedPnL] = useState(0);
    const [watchlist, setWatchlist] = useState([]);
    const [livePrices, setLivePrices] = useState({});
    const [loadingTransactions, setLoadingTransactions] = useState(true);
    const [loadingSummary, setLoadingSummary] = useState(true);
    const [loadingWatchlist, setLoadingWatchlist] = useState(true);
    const [error, setError] = useState('');
    const [selectedStock, setSelectedStock] = useState(null);

    const fetchTransactions = async () => {
        setLoadingTransactions(true);
        try {
            const response = await apiClient.get(PORTFOLIO_API_URL);
            setTransactions(response.data);
        } catch (err) {
            console.error('Fetch transactions error:', err);
            setError('거래 내역 로드 실패');
        } finally {
            setLoadingTransactions(false);
        }
    };

    const fetchDashboardData = async () => {
        setLoadingSummary(true);
        setLoadingWatchlist(true);
        setError('');
        try {
            const [summaryRes, watchlistRes] = await Promise.all([
                apiClient.get(`${PORTFOLIO_API_URL}/summary`),
                apiClient.get('/watchlist')
            ]);

            const newHoldings = summaryRes.data.holdings;
            const newWatchlist = watchlistRes.data;
            setHoldings(newHoldings);
            setRealizedPnL(summaryRes.data.realizedPnL);
            setWatchlist(newWatchlist);

            const symbolsToFetch = [
                ...newHoldings.map(h => h.symbol),
                ...newWatchlist
            ];
            const uniqueSymbols = [...new Set(symbolsToFetch)];

            if (uniqueSymbols.length > 0) {
                const pricePromises = uniqueSymbols.map(symbol =>
                    axios.get(`${FINNHUB_API_URL}/quote`, {
                        params: { symbol: symbol, token: FINNHUB_API_KEY }
                    })
                );
                const priceResults = await Promise.all(pricePromises);

                const prices = {};
                priceResults.forEach((res, index) => {
                    const symbol = uniqueSymbols[index];
                    prices[symbol] = res.data.c;
                });
                setLivePrices(prices);
            }
        } catch (err) {
            console.error('Fetch dashboard data error:', err);
            setError('데이터 로드 실패');
        } finally {
            setLoadingSummary(false);
            setLoadingWatchlist(false);
        }
    };

    useEffect(() => {
        const symbolsToSubscribe = [
            ...holdings.map(h => h.symbol),
            ...watchlist
        ];
        const uniqueSymbols = [...new Set(symbolsToSubscribe)];

        if (uniqueSymbols.length === 0 || loadingSummary || loadingWatchlist) {
            return;
        }

        const socket = new WebSocket(`wss://ws.finnhub.io?token=${FINNHUB_API_KEY}`);

        socket.onopen = () => {
            console.log('WebSocket connected');
            uniqueSymbols.forEach(symbol => {
                socket.send(JSON.stringify({'type':'subscribe', 'symbol': symbol}));
            });
        };

        socket.onmessage = (event) => {
            const message = JSON.parse(event.data);

            if (message.type === 'trade') {
                message.data.forEach(trade => {
                    const symbol = trade.s;
                    const price = trade.p;

                    setLivePrices((prevPrices) => ({
                        ...prevPrices,
                        [symbol]: price,
                    }));
                });
            }
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };

        return () => {
            if (socket.readyState === 1) {
                console.log('WebSocket disconnecting');
                holdings.forEach(symbol => {
                    socket.send(JSON.stringify({'type':'unsubscribe', 'symbol': symbol}));
                });
                socket.close();
            }
        };
    }, [holdings, watchlist, loadingSummary, loadingWatchlist]);

    useEffect(() => {
        if (user) {
            fetchTransactions();
            fetchDashboardData();
        }
    }, [user]);

    const handleStockSelect = (symbol, price) => {
        setSelectedStock({ symbol, price });
        setLivePrices(prevPrices => ({ ...prevPrices, [symbol]: price }));
    };

    const handleTransactionAdded = () => {
        fetchTransactions();
        fetchDashboardData();
    };

    const handleAddToWatchlist = async (symbol) => {
        try {
            setError('');
            await apiClient.post('/watchlist/add', { symbol });
            fetchDashboardData();
        } catch (err) {
            setError('관심 목록 추가 실패');
        }
    };

    const handleRemoveFromWatchlist = async (symbol) => {
        try {
            setError('');
            await apiClient.delete(`/watchlist/remove/${symbol}`);
            fetchDashboardData();
        } catch (err) {
            setError('관심 목록 삭제 실패');
        }
    };

    const portfolioMetrics = useMemo(() => {
        let totalValue = 0;
        let totalInvested = 0;

        const holdingsWithValues = holdings.map(holding => {
            const currentPrice = livePrices[holding.symbol] || 0;
            const currentValue = holding.shares * currentPrice;
            totalValue += currentValue;
            totalInvested += holding.totalCost;

            return {
                ...holding,
                currentPrice,
                currentValue,
            };
        });

        const unrealizedPnL = totalValue - totalInvested;
        const totalPnL = unrealizedPnL + realizedPnL;

        return {
            holdingsWithValues,
            totalValue,
            totalInvested,
            totalPnL,
            unrealizedPnL,
        };
    }, [holdings, livePrices, realizedPnL]);

    return (
        <div className="dashboard-container">
            <h1>환영합니다, {user ? user.email : '방문자'}님!</h1>
            <p>주식 포트폴리오 대시보드입니다.</p>
            <div className="summary-chart-container">
                <h2>포트폴리오 요약</h2>
                {loadingSummary ? (
                    <p>요약 데이터 로딩 중...</p>
                ) : error ? (
                    <p className="form-error">{error}</p>
                ) : holdings.length > 0 ? (
                    <div className="summary-content">
                        <PortfolioChart holdings={portfolioMetrics.holdingsWithValues} />
                        <div className="summary-text">
                            <div className="summary-item">
                                <span>총 자산 가치</span>
                                <span className="value">${portfolioMetrics.totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            </div>
                            <div className="summary-item">
                                <span>총 투자 원금</span>
                                <span className="value">${portfolioMetrics.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            </div>
                            <div className="summary-item total-pnl">
                                <span>총 손익 (P/L)</span>
                                <span className={`value ${portfolioMetrics.totalPnL >= 0 ? 'positive' : 'negative'}`}>
                                    ${portfolioMetrics.totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                </span>
                            </div>
                        </div>
                    </div>
                ) : (
                    <p>요약 데이터가 없습니다. 거래 내역을 추가해 주세요.</p>
                )}
            </div>
            <StockSearch 
              onStockSelect={handleStockSelect}
              onAddToWatchlist={handleAddToWatchlist}
            />
            <hr />
            <AddTransactionForm 
              onTransactionAdded={handleTransactionAdded}
              selectedStock={selectedStock}
            />
            <hr />
            <div className="watchlist-container">
                <h2>내 관심 목록</h2>
                {loadingWatchlist ? (
                    <p>관심 목록 로딩 중...</p>
                ) : error ? (
                    null
                ) : (
                    <Watchlist
                      list={watchlist}
                      prices={livePrices}
                      onRemove={handleRemoveFromWatchlist}
                    />
                )}
            </div>
            <div className="transaction-list-container">
                <h2>내 거래 내역</h2>
                {loadingTransactions && <p>로딩 중...</p>}
                {error && <p className="form-error">{error}</p>}
                {error ? null : !loadingTransactions && (
                    <TransactionList transactions={transactions} />
                )}
            </div>
            <button onClick={logout} className="logout-button">
                로그아웃
            </button>
        </div>
    );
}

export default Dashboard;