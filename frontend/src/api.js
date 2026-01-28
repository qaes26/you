import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
});

export const getVideoInfo = async (url) => {
    try {
        const response = await api.post('/api/info', { url });
        return response.data;
    } catch (error) {
        throw error.response ? error.response.data : error;
    }
};

export const getDownloadUrl = (url, formatId) => {
    // Stream endpoint is public for now, but if we protected it, we'd need to fetch 
    // a temporary signed URL or proxy via blob.
    // For this MVP, we link directly.
    return `${API_BASE_URL}/api/stream?url=${encodeURIComponent(url)}&format_id=${formatId}`;
};

export default api;
