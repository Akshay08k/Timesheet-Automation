import React, { useState } from 'react';
import { api } from '../api/client';
import type { User } from '../types';
import { Clock, Sparkles, Shield, ArrowRight, Lock } from 'lucide-react';

interface AuthViewProps {
  onAuthSuccess: (user: User, token: string) => void;
}

const ALLOWED_DOMAIN = '@rysun.com';

export const AuthView: React.FC<AuthViewProps> = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const trimmedEmail = email.trim().toLowerCase();

    // Security check: only allow @rysun.com domain
    if (!trimmedEmail.endsWith(ALLOWED_DOMAIN)) {
      setError(`Access Restricted: Only official ${ALLOWED_DOMAIN} email addresses are permitted.`);
      setLoading(false);
      return;
    }

    try {
      if (isLogin) {
        const formData = new FormData();
        formData.append('username', trimmedEmail);
        formData.append('password', password);
        const data = await api.login(formData);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        onAuthSuccess(data.user, data.access_token);
      } else {
        const derivedUsername = trimmedEmail.split('@')[0];
        await api.register({
          username: derivedUsername,
          password,
          full_name: fullName.trim(),
          email: trimmedEmail,
          timezone,
        });
        // Auto login after register
        const formData = new FormData();
        formData.append('username', trimmedEmail);
        formData.append('password', password);
        const data = await api.login(formData);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        onAuthSuccess(data.user, data.access_token);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Banner */}
        <div className="bg-gradient-to-br from-blue-700 via-indigo-700 to-slate-900 p-8 text-white text-center">
          <div className="inline-flex p-3 bg-white/10 rounded-2xl backdrop-blur-md mb-3">
            <Clock className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">DevTimesheet</h1>
          <p className="text-xs text-blue-100 mt-1">
            Enterprise Azure DevOps & Google Gemini AI Timesheet Automation
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/15 rounded-full text-xs font-semibold backdrop-blur-xs">
              <Sparkles className="w-3.5 h-3.5 text-yellow-300" />
              Gemini 2.5 Flash
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-200 border border-emerald-400/30 rounded-full text-xs font-semibold backdrop-blur-xs">
              <Shield className="w-3.5 h-3.5 text-emerald-300" />
              Restricted: @rysun.com
            </div>
          </div>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-200">
          <button
            onClick={() => {
              setIsLogin(true);
              setError(null);
            }}
            className={`flex-1 py-3 text-xs font-bold text-center transition ${
              isLogin ? 'text-blue-600 border-b-2 border-blue-600 bg-white' : 'text-slate-500 bg-slate-50 hover:bg-slate-100'
            }`}
          >
            Sign In with Email
          </button>
          <button
            onClick={() => {
              setIsLogin(false);
              setError(null);
            }}
            className={`flex-1 py-3 text-xs font-bold text-center transition ${
              !isLogin ? 'text-blue-600 border-b-2 border-blue-600 bg-white' : 'text-slate-500 bg-slate-50 hover:bg-slate-100'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-8 space-y-4">
          {error && (
            <div className="p-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2">
              <Lock className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Work Email <span className="text-slate-400 font-normal">(@rysun.com)</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
              placeholder="e.g. your.name@rysun.com"
            />
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  placeholder="e.g. Akshay Komale"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Timezone</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York (EST/EDT)</option>
                  <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                  <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                  <option value="Europe/London">Europe/London (GMT/BST)</option>
                </select>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
              placeholder="••••••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-xs transition"
          >
            {loading ? 'Processing...' : isLogin ? 'Sign In to DevTimesheet' : 'Register & Start'}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* Footer info */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 text-center text-[11px] text-slate-500 flex items-center justify-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span>Security enforced: Access limited exclusively to @rysun.com accounts.</span>
        </div>
      </div>
    </div>
  );
};
