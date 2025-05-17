import axios from 'axios';

// Erstelle einen Axios-Client für dein Backend
const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default API;
