import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Validators } from '../../utils/validators';
import { LoginCredentials } from '../../types/api.types';
import Button from '../common/Button';
import Input from '../common/Input';
import toast from 'react-hot-toast';

const LoginForm: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ username?: string; password?: string }>({});
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/app/chat';

  const validate = (): boolean => {
    const newErrors: { username?: string; password?: string } = {};

    const usernameValidation = Validators.validateUsername(username);
    if (!usernameValidation.isValid) {
      newErrors.username = usernameValidation.message;
    }

    const passwordValidation = Validators.validatePassword(password);
    if (!passwordValidation.isValid) {
      newErrors.password = passwordValidation.message;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    try {
      await login({ username, password } as LoginCredentials);
      toast.success('Login successful!');
      navigate(from, { replace: true });
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Login failed. Please try again.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Username"
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        error={errors.username}
        placeholder="Enter your username"
        required
        autoComplete="username"
        aria-label="Username"
      />

      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={errors.password}
        placeholder="Enter your password"
        required
        autoComplete="current-password"
        aria-label="Password"
      />

      <Button
        type="submit"
        variant="primary"
        isLoading={isLoading}
        className="w-full"
        aria-label="Login"
      >
        Login
      </Button>

      <p className="text-center text-sm text-text_secondary">
        Don't have an account?{' '}
        <Link
          to="/signup"
          className="text-primary hover:text-primary_dark font-medium"
        >
          Sign up
        </Link>
      </p>
    </form>
  );
};

export default LoginForm;
