import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Validators } from '../../utils/validators';
import { SignupCredentials } from '../../types/api.types';
import Button from '../common/Button';
import Input from '../common/Input';
import toast from 'react-hot-toast';

const SignupForm: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<{
    username?: string;
    password?: string;
    confirmPassword?: string;
  }>({});
  const { signup, isLoading } = useAuth();
  const navigate = useNavigate();

  const validate = (): boolean => {
    const newErrors: {
      username?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    const usernameValidation = Validators.validateUsername(username);
    if (!usernameValidation.isValid) {
      newErrors.username = usernameValidation.message;
    }

    const passwordValidation = Validators.validatePassword(password);
    if (!passwordValidation.isValid) {
      newErrors.password = passwordValidation.message;
    }

    const confirmPasswordValidation = Validators.validateConfirmPassword(
      password,
      confirmPassword
    );
    if (!confirmPasswordValidation.isValid) {
      newErrors.confirmPassword = confirmPasswordValidation.message;
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
      await signup({ username, password, confirmPassword } as SignupCredentials);
      toast.success('Account created successfully!');
      navigate('/app/chat', { replace: true });
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Signup failed. Please try again.');
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
        placeholder="Choose a username"
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
        placeholder="Create a password"
        required
        autoComplete="new-password"
        aria-label="Password"
        helperText="Must be at least 6 characters long"
      />

      <Input
        label="Confirm Password"
        type="password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        error={errors.confirmPassword}
        placeholder="Confirm your password"
        required
        autoComplete="new-password"
        aria-label="Confirm Password"
      />

      <Button
        type="submit"
        variant="primary"
        isLoading={isLoading}
        className="w-full"
        aria-label="Sign up"
      >
        Sign Up
      </Button>

      <p className="text-center text-sm text-text_secondary">
        Already have an account?{' '}
        <Link
          to="/login"
          className="text-primary hover:text-primary_dark font-medium"
        >
          Login
        </Link>
      </p>
    </form>
  );
};

export default SignupForm;
