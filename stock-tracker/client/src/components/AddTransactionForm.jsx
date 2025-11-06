// client/src/components/AddTransactionForm.jsx

import React, { useState, useEffect } from 'react';
import apiClient from '../api/axiosConfig.js';
import './AddTransactionForm.css';

function AddTransactionForm({ onTransactionAdded, selectedStock }) {
    const [symbol, setSymbol] = useState('');
    const [shares, setShares] = useState('');
    const [pricePerShare, setPricePerShare] = useState('');
    const [transactionType, setTransactionType] = useState('buy');
    const [totalAmount, setTotalAmount] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (selectedStock) {
            setSymbol(selectedStock.symbol);
            setPricePerShare(selectedStock.price);
            setTotalAmount('');
            setTransactionType('buy');
            setError('');
            setSuccess('');
        }
    }, [selectedStock]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);

        let dataToSend = {};

        if (transactionType === 'dividend') {
            dataToSend = {
                symbol,
                shares: 1,
                pricePerShare: Number(totalAmount),
                transactionType,
            };
        } else {
            dataToSend = {
                symbol,
                shares: Number(shares),
                pricePerShare: Number(pricePerShare),
                transactionType,
            };
        }

        try {
            await apiClient.post('/portfolio/add', dataToSend);

            setSuccess('거래 내역이 성공적으로 추가되었습니다!');
            setSymbol('');
            setShares('');
            setPricePerShare('');
            setTotalAmount('');

            if (onTransactionAdded) {
                onTransactionAdded();
            }
        } catch (err) {
            if (err.response && err.response.data.error) {
                setError(err.response.data.error);
            } else {
                setError('거래 추가 중 오류가 발생했습니다.');
            }
            console.error('Transaction Error:', err.response || err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="transaction-form-container">
            <h3>새 거래 내역 추가</h3>
            <form onSubmit={handleSubmit} className="transaction-form">
                {error && <p className="form-error">{error}</p>}
                {success && <p className="form-success">{success}</p>}
                <div className="form-row">
                    <div className="form-group">
                        <label htmlFor="symbol">주식 심볼 (예: AAPL)</label>
                        <input
                            type="text"
                            id="symbol"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                            required
                            disabled={loading}
                        />  
                    </div>
                    <div className="form-group">
                        <label htmlFor="transactionType">거래 유형</label>
                        <select
                            id="transactionType"
                            value={transactionType}
                            onChange={(e) => setTransactionType(e.target.value)}
                            disabled={loading}
                        >
                            <option value="buy">매수 (Buy)</option>
                            <option value="sell">매도 (Sell)</option>
                            <option value="dividend">배당 (Dividend)</option>
                        </select>
                    </div>
                </div>
                {transactionType === 'buy' || transactionType === 'sell' ? (
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="shares">수량</label>
                            <input
                                type="number"
                                id="shares"
                                value={shares}
                                onChange={(e) => setShares(e.target.value)}
                                required
                                min="0"
                                step="any"
                                disabled={loading}
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="price">1주당 가격 ($)</label>
                            <input
                                type="number"
                                id="price"
                                value={pricePerShare}
                                onChange={(e) => setPricePerShare(e.target.value)}
                                required
                                min="0"
                                step="any"
                                disabled={loading}
                            />
                        </div>
                    </div>
                ) : (
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="totalAmount">총 배당금액 ($)</label>
                            <input
                                type="number"
                                id="totalAmount"
                                value={totalAmount}
                                onChange={(e) => setTotalAmount(e.target.value)}
                                required
                                min="0"
                                step="any"
                                disabled={loading}
                            />
                        </div>
                    </div>
                )}
                <button type="submit" className="submit-button" disabled={loading}>
                    {loading ? '추가 중...' : '거래 내역 추가'}
                </button>
            </form>
        </div>
    );
}

export default AddTransactionForm;