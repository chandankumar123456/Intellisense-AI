import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import toast from 'react-hot-toast';
import { apiCache } from '../utils/cache';
import { Storage } from '../utils/storage';

// API Client Configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor - attach JWT token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('notebook_lm_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Log request for debugging
        console.log('API Request:', {
          method: config.method?.toUpperCase(),
          url: config.url,
          data: config.data,
        });

        return config;
      },
      (error: AxiosError) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor - handle errors globally
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Log successful responses
        console.log('API Response:', {
          status: response.status,
          url: response.config.url,
          data: response.data,
        });

        return response;
      },
      (error: AxiosError) => {
        console.error('API Error:', error);

        if (error.response) {
          const { status, data } = error.response;

          switch (status) {
            case 401:
              // Unauthorized - try token refresh first
              this.refreshToken()
                .then((refreshSuccess) => {
                  if (!refreshSuccess) {
                    // Refresh failed - clear token and redirect
                    Storage.clearAll();
                    apiCache.clear();
                    toast.error('Your session has expired. Please login again.');
                    window.location.href = '/login';
                  } else {
                    // Retry the original request
                    const originalRequest = error.config;
                    if (originalRequest) {
                      const token = Storage.getToken();
                      if (token && originalRequest.headers) {
                        originalRequest.headers.Authorization = `Bearer ${token}`;
                      }
                      return this.client(originalRequest);
                    }
                  }
                })
                .catch(() => {
                  Storage.clearAll();
                  apiCache.clear();
                  toast.error('Your session has expired. Please login again.');
                  window.location.href = '/login';
                });
              break;

            case 403:
              // Forbidden
              toast.error('You don\'t have permission to access this resource.');
              break;

            case 400:
              // Bad request - show validation errors
              if (data && typeof data === 'object' && 'message' in data) {
                toast.error(data.message as string);
              } else {
                toast.error('Please check your input and try again.');
              }
              break;

            case 500:
              // Server error
              toast.error('Something went wrong. Please try again.');
              break;

            default:
              toast.error('An unexpected error occurred.');
          }
        } else if (error.request) {
          // Network error
          toast.error('No internet connection. Please check your network.');
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Refresh JWT token
   */
  private async refreshToken(): Promise<boolean> {
    try {
      const token = Storage.getToken();
      if (!token) return false;

      // Verify token is still valid
      await this.client.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // Token is still valid, no refresh needed
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }

  // Generic request methods with caching support
  public async get<T = any>(
    url: string,
    config?: AxiosRequestConfig,
    useCache: boolean = false
  ): Promise<T> {
    const cacheKey = apiCache.generateKey(url, config?.params);
    
    // Check cache first
    if (useCache) {
      const cached = apiCache.get<T>(cacheKey);
      if (cached !== null) {
        return cached;
      }
    }

    const response = await this.client.get(url, config);
    
    // Cache the response
    if (useCache) {
      apiCache.set(cacheKey, response.data);
    }
    
    return response.data;
  }

  public async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post(url, data, config);
    
    // Invalidate related cache entries on POST
    if (url.includes('/chat/query')) {
      apiCache.delete(apiCache.generateKey(url));
    }
    
    return response.data;
  }

  public async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  public async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete(url, config);
    return response.data;
  }

  // Get the underlying axios instance for advanced usage
  public getClient(): AxiosInstance {
    return this.client;
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();
export default apiClient;
