// client/src/components/Watchlist.jsx

import React from 'react';
import './Watchlist.css';

function Watchlist({ list, prices, onRemove }) {

    const getPrice = (symbol) => {
        const price = prices[symbol];
        return price ? `$${price.toLocaleString()}` : 'Loading...';
    };

    return (
        <div className="watchlist">
            {list.length === 0 ? (
                <p className="empty-message">관심 목록에 추가된 주식이 없습니다.</p>
            ) : (
                <ul className="watchlist-items">
                    {list.map((symbol) => (
                        <li key={symbol} className="watchlist-item">
                            <div className="item-info">
                                <span className="symbol">{symbol}</span>
                            </div>
                            <div className="item-price">
                                {getPrice(symbol)}
                            </div>
                            <button
                              className="remove-btn"
                              onClick={() => onRemove(symbol)}
                              title="관심 목록에서 삭제"
                            >
                              &times;
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default Watchlist;