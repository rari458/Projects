// client/src/pages/AuthCallback.jsx

import React, { useEffect, useContext, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext.jsx';

function AuthCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { login } = useContext(AuthContext);
    const hasRun = useRef(false);

    useEffect(() => {
        if (hasRun.current) return;

        const token = searchParams.get('token');
        const userString = searchParams.get('user');

        if (token && userString) {
            try {
                const user = JSON.parse(userString);
                login(token, user);
                hasRun.current = true;
                navigate('/');
            } catch (error) {
                console.error('Failed to parse user data from URL', error);
                navigate('/login');
            }
        } else {
            navigate('/login');
        }
    }, [searchParams]);

    return (
        <div className="loading-container">
            <h2>인증 처리 중...</h2>
        </div>
    );
}

export default AuthCallback;