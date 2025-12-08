import { apiClient } from './api';
import { LoginCredentials, SignupCredentials, AuthResponse, User } from '../types/api.types';

export class AuthService {
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
    return response;
  }

  static async signup(credentials: SignupCredentials): Promise<AuthResponse> {
    const { confirmPassword, ...signupData } = credentials;
    const response = await apiClient.post<AuthResponse>('/auth/signup', signupData);
    return response;
  }

  static async verifyToken(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response;
  }
}
