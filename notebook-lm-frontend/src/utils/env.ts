// Environment variable validation and helpers

const requiredEnvVars = ['REACT_APP_API_BASE_URL'] as const;

export const getEnvVar = (key: string, defaultValue?: string): string => {
  const value = process.env[key];
  if (!value && !defaultValue) {
    console.warn(`Environment variable ${key} is not set`);
  }
  return value || defaultValue || '';
};

export const validateEnv = (): void => {
  const missing: string[] = [];

  requiredEnvVars.forEach((key) => {
    if (!process.env[key]) {
      missing.push(key);
    }
  });

  if (missing.length > 0) {
    console.error(
      `Missing required environment variables: ${missing.join(', ')}`
    );
    console.warn(
      'Please create a .env file with the required variables. See .env.example for reference.'
    );
  }
};

export const API_BASE_URL =
  getEnvVar('REACT_APP_API_BASE_URL', 'http://localhost:8000');
export const ENV = getEnvVar('REACT_APP_ENV', 'development');
export const ENABLE_ANALYTICS =
  getEnvVar('REACT_APP_ENABLE_ANALYTICS', 'false') === 'true';

// Validate on module load in development
if (process.env.NODE_ENV === 'development') {
  validateEnv();
}
