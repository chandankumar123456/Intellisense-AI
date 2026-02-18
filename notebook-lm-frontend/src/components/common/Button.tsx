import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

const sizeMap = {
  sm: { className: 'px-4 py-2 text-xs', minHeight: '36px', iconSize: 'w-3.5 h-3.5' },
  md: { className: 'px-5 py-2.5 text-sm', minHeight: '42px', iconSize: 'w-4 h-4' },
  lg: { className: 'px-7 py-3.5 text-base', minHeight: '48px', iconSize: 'w-4 h-4' },
};

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className = '',
  disabled,
  style,
  ...props
}) => {
  const sz = sizeMap[size];

  if (variant === 'primary') {
    return (
      <button
        className={`btn-primary-liquid ${sz.className} ${className}`}
        disabled={disabled || isLoading}
        style={{ minHeight: sz.minHeight, ...style }}
        {...props}
      >
        {isLoading && <Loader2 className={`${sz.iconSize} animate-spin z-content relative`} />}
        <span className="z-content relative">{children}</span>
      </button>
    );
  }

  if (variant === 'danger') {
    return (
      <button
        className={`btn-liquid ${sz.className} ${className}`}
        style={{
          minHeight: sz.minHeight,
          background: 'rgba(239, 68, 68, 0.08)',
          borderColor: 'rgba(239, 68, 68, 0.2)',
          color: '#EF4444',
          boxShadow: '0 2px 8px rgba(239, 68, 68, 0.06)',
          ...style,
        }}
        disabled={disabled || isLoading}
        onMouseEnter={(e) => {
          if (!disabled) {
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(239, 68, 68, 0.15)';
          }
        }}
        onMouseLeave={(e) => {
          if (!disabled) {
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(239, 68, 68, 0.06)';
          }
        }}
        {...props}
      >
        {isLoading && <Loader2 className={`${sz.iconSize} animate-spin z-content relative`} />}
        <span className="z-content relative">{children}</span>
      </button>
    );
  }

  // Secondary
  return (
    <button
      className={`btn-liquid ${sz.className} ${className}`}
      disabled={disabled || isLoading}
      style={{ minHeight: sz.minHeight, ...style }}
      {...props}
    >
      {isLoading && <Loader2 className={`${sz.iconSize} animate-spin z-content relative`} />}
      <span className="z-content relative">{children}</span>
    </button>
  );
};

export default Button;
