// client/src/App.jsx

import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; 

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

function App() {
  const [originalUrl, setOriginalUrl] = useState('');
  const [customCode, setCustomCode] = useState('');
  const [expiration, setExpiration] = useState('never');
  const [shortUrl, setShortUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isCopied, setIsCopied] = useState(false);
  const [clicks, setClicks] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault(); 
    
    setShortUrl('');
    setError('');
    setIsCopied(false);
    setClicks(null);

    if (!originalUrl) {
      setError('URL을 입력해 주세요.');
      return;
    }
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/shorten`, {
        originalUrl: originalUrl,
        customCode: customCode || null,
        expiration: expiration,
      });
      
      setShortUrl(response.data.shortUrl);
      setClicks(response.data.clicks);

    } catch (err) {
      if (err.response && err.response.status === 409) {
        setError(err.response.data.error);
      } else {
        setError('오류가 발생했습니다. 다시 시도해 주세요.');
      }
      console.error('API Error:', err.response || err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- 2. 변경점: 클립보드 복사 핸들러 함수 추가 ---
  const handleCopyClick = () => {
    if (!shortUrl) return; // 복사할 URL이 없으면 아무것도 안 함

    // navigator.clipboard API를 사용해 텍스트 복사
    navigator.clipboard.writeText(shortUrl)
      .then(() => {
        // 성공 시
        setIsCopied(true);
        // 2초 후에 '복사됨' 메시지 숨기기
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      })
      .catch((err) => {
        console.error('Failed to copy text: ', err);
        // (선택) 복사 실패 시 사용자에게 알릴 수 있음
        setError('복사에 실패했습니다. 수동으로 복사해 주세요.');
      });
  };


  return (
    <div className="container">
      <h1>URL 단축 서비스</h1>
      <p>긴 URL을 입력하면 짧은 URL로 줄여줍니다.</p>

      <form onSubmit={handleSubmit} className="url-form">
        <input
          type="url"
          placeholder="단축할 URL을 입력하세요 (예: https://...)"
          value={originalUrl}
          onChange={(e) => setOriginalUrl(e.target.value)}
          disabled={loading}
          required
        />
        <div className="custom-url-group">
          <span>{API_BASE_URL.replace(/^https?:\/\//, '')}</span>
          <input
            type="text"
            className="custom-url-input"
            placeholder="(선택) 사용자 정의 코드"
            value={customCode}
            onChange={(e) => setCustomCode(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="expiration-group">
          <label htmlFor="expiration">만료 기한:</label>
          <select
            id="expiration"
            value={expiration}
            onChange={(e) => setExpiration(e.target.value)}
            disabled={loading}
          >
            <option value="never">설정 안 함</option>
            <option value="1hour">(테스트) 1시간</option>
            <option value="1day">1일</option>
            <option value="7days">7일</option>
          </select>
        </div>

        <button type="submit" disabled={loading}>
          {loading ? '생성 중...' : '단축하기'}
        </button>
      </form>

      <div className="result-container">
        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        {shortUrl && (
          <div className="short-url-result">
            <h3>
              생성된 짧은 URL
              {clicks !== null && (
                <span className="click-count">(클릭: {clicks}회)</span>
              )}
            </h3>
            <div className="short-url-box">
              <a href={shortUrl} target="_blank" rel="noopener noreferrer">
                {shortUrl}
              </a>
              <button onClick={handleCopyClick} className="copy-button">
                {isCopied ? '복사됨!' : '복사'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;