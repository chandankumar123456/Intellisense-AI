import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || `input-${label?.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-text_secondary mb-1.5">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`input-field ${error ? 'border-error focus:ring-error' : ''} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
        {...props}
      />
      {error && <p id={`${inputId}-error`} className="mt-1 text-xs text-error" role="alert">{error}</p>}
      {helperText && !error && <p id={`${inputId}-helper`} className="mt-1 text-xs text-text_muted">{helperText}</p>}
    </div>
  );
};

export default Input;
