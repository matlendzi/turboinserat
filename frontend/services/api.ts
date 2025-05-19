import axios from 'axios';

const isDevelopment = import.meta.env.VITE_APP_ENV === 'development';

// Create an Axios client for your backend
const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for development logging
if (isDevelopment) {
  API.interceptors.request.use(request => {
    console.log('Starting Request:', request);
    return request;
  });

  API.interceptors.response.use(
    response => {
      console.log('Response:', response);
      return response;
    },
    error => {
      console.error('Response Error:', error);
      return Promise.reject(error);
    }
  );
}

export default API;
