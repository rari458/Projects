// client/src/api/axiosConfig.js

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api';

const apiClient = axios.create({
    baseURL: BASE_URL
});

apiClient.interceptors.response.use(
    (response) => {
        return response;
    },

    (error) => {
        if (error.response &&
            error.response.status === 401 &&
            error.response.data.error !== 'No token, authorization denied')
        {
            console.error('Inceptor: Invalid or expired token. Logging out...');

            localStorage.removeItem('token');
            localStorage.removeItem('user');
            delete axios.defaults.headers.common['Authorization'];

            window.location.href = '/';
        }

        return Promise.reject(error);
    }
);

export default apiClient;