// client/src/components/StockSearch.jsx

import React, { useState } from 'react';
import apiClient from '../api/axiosConfig.js';
import './StockSearch.css';

function StockSearch({ onStockSelect }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (query.length < 2) {
            return;
        }

        setLoading(true);
        setResults([]);

        try {
            const response = await apiClient.get('/stocks/search', {
                params: { q: query }
            });

            setResults(response.data.result || []);
        } catch (err) {
            console.error('Stock search error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectForForm = async (symbol) => {
        setLoading(true);

        try {
            const response = await apiClient.get('/stocks/quote', {
                params: { symbol: symbol }
            });
            onStockSelect(symbol, response.data.c);
            setQuery('');
            setResults([]);
        } catch (err) {
            console.error('Stock quote error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAddToWatchlist = async (symbol) => {
        if (onAddToWatchlist) {
            await onAddToWatchlist(symbol);
        }
    };

    return (
        <div className="stock-search-container">
            <h3>주식 검색</h3>
            <form onSubmit={handleSearch} className="search-form">
                <input 
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="회사명 또는 심볼 (예: Apple)"
                  disabled={loading}
                />
                <button type="submit" disabled={loading}>
                    {loading ? '검색 중...' : '검색'}
                </button>
            </form>
            {results.length > 0 && (
                <ul className="search-results">
                    {results.map((item) => (
                        <li key={item.symbol}>
                            <div
                              className="result-info"
                              onClick={() => handleSelectForForm(item.symbol)}
                              title="클릭하여 매수/매도 폼에 채우기"
                            >
                                <span className="symbol">{item.symbol}</span>
                                <span className="description">{item.description}</span>
                            </div>
                            <button
                              className="watchlist-add-btn"
                              onClick={() => handleAddToWatchlist(item.symbol)}
                              title="관심 목록에 추가"
                              disabled={loading}
                            >
                            찜하기
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default StockSearch;