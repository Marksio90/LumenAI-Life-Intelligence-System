'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, UserPlus, Loader2, Check, X } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export default function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const router = useRouter();
  const { register: registerUser, isLoading: storeLoading } = useAuthStore();
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const isLoading = storeLoading;

  // Password strength validation
  const getPasswordStrength = (password: string) => {
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
    };

    const passed = Object.values(checks).filter(Boolean).length;
    return { checks, strength: passed };
  };

  const { checks, strength } = getPasswordStrength(formData.password);

  const getStrengthColor = () => {
    if (strength <= 1) return 'bg-red-500';
    if (strength === 2) return 'bg-yellow-500';
    if (strength === 3) return 'bg-blue-500';
    return 'bg-green-500';
  };

  const getStrengthText = () => {
    if (strength <= 1) return 'Weak';
    if (strength === 2) return 'Fair';
    if (strength === 3) return 'Good';
    return 'Strong';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (strength < 4) {
      setError('Password does not meet requirements');
      return;
    }

    try {
      await registerUser({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        full_name: formData.fullName,
      });

      // Success
      if (onSuccess) {
        onSuccess();
      } else {
        router.push('/dashboard');
        router.refresh();
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(''); // Clear error on input change
  };

  return (
    <div className="w-full max-w-md mx-auto p-4 sm:p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-h-[90vh] overflow-y-auto">
      <div className="text-center mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
          Create Account
        </h2>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mt-1 sm:mt-2">
          Join LumenAI and start your journey
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
        {/* Full Name */}
        <div>
          <label
            htmlFor="fullName"
            className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            value={formData.fullName}
            onChange={(e) => handleChange('fullName', e.target.value)}
            className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="John Doe"
          />
        </div>

        {/* Email */}
        <div>
          <label
            htmlFor="email"
            className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            required
            className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="john@example.com"
          />
        </div>

        {/* Username */}
        <div>
          <label
            htmlFor="username"
            className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Username
          </label>
          <input
            id="username"
            type="text"
            value={formData.username}
            onChange={(e) => handleChange('username', e.target.value)}
            required
            pattern="[a-zA-Z0-9_]+"
            className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="john_doe"
          />
          <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 mt-0.5 sm:mt-1">
            Only letters, numbers, and underscores
          </p>
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="password"
            className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              required
              className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white pr-10"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={18} className="sm:w-5 sm:h-5" /> : <Eye size={18} className="sm:w-5 sm:h-5" />}
            </button>
          </div>

          {/* Password Strength */}
          {formData.password && (
            <div className="mt-1.5 sm:mt-2">
              <div className="flex gap-1 mb-1.5 sm:mb-2">
                {[1, 2, 3, 4].map((level) => (
                  <div
                    key={level}
                    className={`h-1 flex-1 rounded-full ${
                      level <= strength ? getStrengthColor() : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  />
                ))}
              </div>
              <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400">
                Strength: <span className="font-medium">{getStrengthText()}</span>
              </p>

              {/* Password Requirements */}
              <div className="mt-1.5 sm:mt-2 space-y-0.5 sm:space-y-1">
                {[
                  { label: 'At least 8 characters', check: checks.length },
                  { label: 'One uppercase letter', check: checks.uppercase },
                  { label: 'One lowercase letter', check: checks.lowercase },
                  { label: 'One number', check: checks.number },
                ].map((req, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs">
                    {req.check ? (
                      <Check size={12} className="sm:w-3.5 sm:h-3.5 text-green-500 flex-shrink-0" />
                    ) : (
                      <X size={12} className="sm:w-3.5 sm:h-3.5 text-red-500 flex-shrink-0" />
                    )}
                    <span
                      className={
                        req.check
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-gray-600 dark:text-gray-400'
                      }
                    >
                      {req.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            value={formData.confirmPassword}
            onChange={(e) => handleChange('confirmPassword', e.target.value)}
            required
            className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="••••••••"
          />
          {formData.confirmPassword && formData.password !== formData.confirmPassword && (
            <p className="text-[10px] sm:text-xs text-red-500 mt-0.5 sm:mt-1">Passwords do not match</p>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-2.5 sm:p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-xs sm:text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading || strength < 4}
          className="w-full py-2.5 sm:py-3 px-4 text-sm sm:text-base bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 touch-manipulation"
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="sm:w-5 sm:h-5 animate-spin" />
              <span>Creating account...</span>
            </>
          ) : (
            <>
              <UserPlus size={18} className="sm:w-5 sm:h-5" />
              <span>Create Account</span>
            </>
          )}
        </button>

        {/* Login Link */}
        {onSwitchToLogin && (
          <div className="text-center mt-3 sm:mt-4">
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              Already have an account?{' '}
              <button
                type="button"
                onClick={onSwitchToLogin}
                className="text-blue-600 dark:text-blue-400 hover:underline font-medium touch-manipulation"
              >
                Sign in
              </button>
            </p>
          </div>
        )}
      </form>
    </div>
  );
}
