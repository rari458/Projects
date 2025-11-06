// client/src/api/axiosConfig.js

import axios from 'axios';

const apiClient = axios.create({
    baseURL: 'http://localhost:5001/api'
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