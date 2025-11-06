// client/src/components/TransactionList.jsx

import React from 'react';
import './TransactionList.css';

function TransactionList({ transactions }) {
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR',{
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        });
    };

    const getTransactionTypeName = (type) => {
        if (type === 'buy') return '매수';
        if (type === 'sell') return '매도';
        if (type === 'dividend') return '배당';
        return type;
    };

    return (
        <div className="transaction-list">
            {transactions.length === 0 ? (
                <p className="empty-message">아직 추가된 거래 내역이 없습니다.</p>
            ) : (
              <ul>
                {transactions.map((tx) => (
                    <li key={tx._id} className="transaction-item">
                        <div className={`indicator ${tx.transactionType}`}></div>
                        <div className="info">
                            <span className="symbol">{tx.symbol}</span>
                            <span className="type">
                                {getTransactionTypeName(tx.transactionType)}
                            </span>
                        </div>
                        <div className="details">
                            {tx.transactionType === 'dividend' ? (
                                <span className="dividend-amount">배당금 입금</span>
                            ) : (
                                <>
                                    <span className="shares">{tx.shares}주</span>
                                    <span className="separator">@</span>
                                    <span className="price">${tx.pricePerShare.toLocaleString()}</span>
                                </>
                            )}
                        </div>
                        <div className="date-info">
                            {formatDate(tx.date)}
                        </div>
                        <div className="total">
                            <span>
                                {tx.transactionType === 'buy' ? '-' : '+'}
                                ${(tx.shares * tx.pricePerShare).toLocaleString()}
                            </span>
                        </div>
                    </li>
                ))}
              </ul>
            )}
        </div>
    );
}

export default TransactionList;