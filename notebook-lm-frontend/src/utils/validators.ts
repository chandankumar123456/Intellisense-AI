// Validation utilities

export interface ValidationResult {
  isValid: boolean;
  message?: string;
}

export class Validators {
  static validateUsername(username: string): ValidationResult {
    if (!username || username.trim().length === 0) {
      return { isValid: false, message: 'Username is required' };
    }

    if (username.length < 3) {
      return { isValid: false, message: 'Username must be at least 3 characters long' };
    }

    if (username.length > 50) {
      return { isValid: false, message: 'Username must be less than 50 characters' };
    }

    // Only allow alphanumeric characters, underscores, and hyphens
    const usernameRegex = /^[a-zA-Z0-9_-]+$/;
    if (!usernameRegex.test(username)) {
      return { isValid: false, message: 'Username can only contain letters, numbers, underscores, and hyphens' };
    }

    return { isValid: true };
  }

  static validatePassword(password: string): ValidationResult {
    if (!password || password.length === 0) {
      return { isValid: false, message: 'Password is required' };
    }

    if (password.length < 6) {
      return { isValid: false, message: 'Password must be at least 6 characters long' };
    }

    if (password.length > 128) {
      return { isValid: false, message: 'Password must be less than 128 characters' };
    }

    return { isValid: true };
  }

  static validateConfirmPassword(password: string, confirmPassword: string): ValidationResult {
    if (password !== confirmPassword) {
      return { isValid: false, message: 'Passwords do not match' };
    }

    return { isValid: true };
  }

  static validateEmail(email: string): ValidationResult {
    if (!email || email.trim().length === 0) {
      return { isValid: false, message: 'Email is required' };
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return { isValid: false, message: 'Please enter a valid email address' };
    }

    return { isValid: true };
  }

  static validateQuery(query: string): ValidationResult {
    if (!query || query.trim().length === 0) {
      return { isValid: false, message: 'Query cannot be empty' };
    }

    if (query.length > 10000) {
      return { isValid: false, message: 'Query is too long (max 10,000 characters)' };
    }

    return { isValid: true };
  }

  static validateMaxLength(maxLength: number): ValidationResult {
    if (maxLength < 100 || maxLength > 1000) {
      return { isValid: false, message: 'Max length must be between 100 and 1000' };
    }

    return { isValid: true };
  }
}
