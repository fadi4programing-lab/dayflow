import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { login } from '../api';

const DEMO_CREDENTIALS = { username: 'demo', password: 'DemoUser@2026' };

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const performLogin = async (credentials, failureMessage = 'Invalid username or password') => {
    setLoading(true);
    setError('');
    try {
      const res = await login(credentials);
      if (res.data.access) localStorage.setItem('access', res.data.access);
      if (res.data.refresh) localStorage.setItem('refresh', res.data.refresh);
      if (res.data.token) localStorage.setItem('token', res.data.token);
      localStorage.setItem('user', JSON.stringify({
        username: res.data.username,
        email: res.data.email,
      }));
      navigate('/');
    } catch {
      setError(failureMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    performLogin(form);
  };

  const handleDemoLogin = () => {
    setForm(DEMO_CREDENTIALS);
    performLogin(DEMO_CREDENTIALS, 'Demo account is not available yet.');
  };

  return (
    <div className="min-h-screen bg-base flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-4xl font-extrabold text-soft">
            day<span className="text-primary">flow</span>
          </div>
          <div className="text-muted text-sm mt-2">Welcome back — sign in to your account</div>
        </div>

        {/* Card */}
        <div className="card">
          <h2 className="text-lg font-bold text-soft mb-6">Sign In</h2>

          {error && (
            <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-4 py-3 rounded-xl mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                Username
              </label>
              <input
                className="input"
                placeholder="Enter your username"
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                Password
              </label>
              <input
                className="input"
                type="password"
                placeholder="Enter your password"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 rounded-xl mt-2 text-base"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-surface px-3 text-[10px] uppercase tracking-widest text-muted">
                or explore instantly
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full py-3 rounded-xl border border-primary/30 bg-primary/5
              text-primary text-sm font-semibold hover:bg-primary/10 transition-all
              flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Sparkles size={15} />
            {loading ? 'Loading demo...' : 'Try Demo Account'}
          </button>
          <p className="text-center text-[10px] text-muted mt-2">
            21 days of demo AI history included.
          </p>

          <p className="text-center text-muted text-sm mt-5">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-semibold">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}