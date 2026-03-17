import { useState, useEffect } from 'react';
import { getProfile, getTasks, getGoals, getNotes, getTimeBlocks } from '../api';
import {
  User, Mail, Shield, Calendar,
  CheckSquare, Target, StickyNote,
  Clock, TrendingUp, Edit, Save, X
} from 'lucide-react';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [error, setError]     = useState('');
  const [form, setForm]       = useState({ first_name:'', last_name:'', email:'' });

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [prof, tasks, goals, notes, blocks] = await Promise.all([
        getProfile(), getTasks(), getGoals(), getNotes(), getTimeBlocks()
      ]);
      setProfile(prof.data);
      setForm({
        first_name: prof.data.first_name || '',
        last_name:  prof.data.last_name  || '',
        email:      prof.data.email      || '',
      });
      setStats({
        tasks:          tasks.data.length,
        completedTasks: tasks.data.filter(t => t.is_completed).length,
        goals:          goals.data.length,
        completedGoals: goals.data.filter(g => g.is_completed).length,
        notes:          notes.data.length,
        timeBlocks:     blocks.data.length,
        avgGoalProgress: goals.data.length
          ? Math.round(goals.data.reduce((s,g) => s + g.progress, 0) / goals.data.length)
          : 0,
      });
    } catch { setError('Failed to load profile'); }
    finally  { setLoading(false); }
  };

  const getInitials = () => {
    if (profile?.first_name && profile?.last_name) {
      return `${profile.first_name[0]}${profile.last_name[0]}`.toUpperCase();
    }
    return profile?.username?.[0]?.toUpperCase() || 'U';
  };

  const joinDate = profile?.date_joined
    ? new Date(profile.date_joined).toLocaleDateString('en-US', {
        month:'long', day:'numeric', year:'numeric'
      })
    : 'N/A';

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col gap-5 max-w-3xl">

      {/* Header */}
      <div>
        <h1 className="page-title flex items-center gap-2">
          <User size={22} className="text-primary" />
          Profile
        </h1>
        <p className="text-muted text-xs md:text-sm mt-1">
          Your account and statistics
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm
          px-4 py-3 rounded-xl flex items-center gap-2">
          {error}
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {/* Profile Card */}
      <div className="card">
        <div className="flex items-start gap-4 flex-wrap sm:flex-nowrap">

          {/* Avatar */}
          <div className="w-16 h-16 md:w-20 md:h-20 rounded-2xl bg-primary/20
            border-2 border-primary/40 flex items-center justify-center flex-shrink-0">
            <span className="text-xl md:text-2xl font-extrabold text-primary">
              {getInitials()}
            </span>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            {!editing ? (
              <>
                <div className="text-lg md:text-xl font-extrabold text-soft">
                  {profile?.first_name && profile?.last_name
                    ? `${profile.first_name} ${profile.last_name}`
                    : profile?.username
                  }
                </div>
                <div className="text-muted text-sm mt-0.5">@{profile?.username}</div>
                <div className="flex items-center gap-1.5 text-muted text-sm mt-1">
                  <Mail size={13} />
                  {profile?.email || 'No email set'}
                </div>
                <div className="flex items-center gap-1.5 text-muted text-xs mt-1">
                  <Calendar size={11} /> Joined {joinDate}
                </div>
              </>
            ) : (
              <div className="flex flex-col gap-3 w-full">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                      First Name
                    </label>
                    <input className="input py-2 text-sm" value={form.first_name}
                      onChange={e => setForm({ ...form, first_name:e.target.value })}
                      placeholder="First name" />
                  </div>
                  <div>
                    <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                      Last Name
                    </label>
                    <input className="input py-2 text-sm" value={form.last_name}
                      onChange={e => setForm({ ...form, last_name:e.target.value })}
                      placeholder="Last name" />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                    Email
                  </label>
                  <input className="input py-2 text-sm" type="email" value={form.email}
                    onChange={e => setForm({ ...form, email:e.target.value })}
                    placeholder="your@email.com" />
                </div>
              </div>
            )}
          </div>

          {/* Edit buttons */}
          <div className="flex gap-2 flex-shrink-0">
            {!editing ? (
              <button onClick={() => setEditing(true)}
                className="btn-ghost flex items-center gap-2 px-3 py-2 rounded-xl">
                <Edit size={14} />
                <span className="text-xs">Edit</span>
              </button>
            ) : (
              <>
                <button onClick={() => setEditing(false)}
                  className="btn-ghost flex items-center gap-2 px-3 py-2 rounded-xl">
                  <X size={14} />
                  <span className="text-xs">Cancel</span>
                </button>
                <button onClick={() => setEditing(false)}
                  className="btn-primary flex items-center gap-2 px-3 py-2 rounded-xl">
                  <Save size={14} />
                  <span className="text-xs">Save</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Badge */}
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border flex-wrap">
          <div className="flex items-center gap-1.5 bg-primary/10 border border-primary/30
            text-primary text-xs font-semibold px-3 py-1.5 rounded-lg">
            <Shield size={11} /> Active Account
          </div>
          <div className="text-xs text-muted">
            Username: <span className="text-soft font-semibold">{profile?.username}</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp size={15} className="text-primary" />
          <span className="text-sm font-bold text-soft">Your Statistics</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          {[
            { label:'Total Tasks',  value:stats?.tasks||0,      sub:`${stats?.completedTasks||0} completed`, accent:'text-primary',    bg:'bg-primary/10',    icon:CheckSquare },
            { label:'Goals',        value:stats?.goals||0,      sub:`${stats?.completedGoals||0} completed`, accent:'text-yellow-400', bg:'bg-yellow-400/10', icon:Target      },
            { label:'Notes',        value:stats?.notes||0,      sub:'saved thoughts',                        accent:'text-cyan-400',   bg:'bg-cyan-400/10',   icon:StickyNote  },
            { label:'Time Blocks',  value:stats?.timeBlocks||0, sub:'scheduled',                             accent:'text-green-400',  bg:'bg-green-400/10',  icon:Clock       },
          ].map(s => {
            const Icon = s.icon;
            return (
              <div key={s.label} className="card flex flex-col gap-2 p-3 md:p-5">
                <div className="flex items-center justify-between">
                  <span className="section-title mb-0 text-[9px] md:text-[10px]">{s.label}</span>
                  <div className={`w-6 h-6 md:w-7 md:h-7 rounded-lg ${s.bg} flex items-center justify-center`}>
                    <Icon size={12} className={s.accent} />
                  </div>
                </div>
                <div className={`text-2xl md:text-3xl font-extrabold ${s.accent}`}>{s.value}</div>
                <div className="text-[10px] text-muted">{s.sub}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Progress bars */}
      <div className="card">
        <div className="flex items-center gap-2 mb-5">
          <TrendingUp size={15} className="text-primary" />
          <span className="text-sm font-bold text-soft">Progress Overview</span>
        </div>
        <div className="flex flex-col gap-4">
          {[
            {
              label:   'Task Completion Rate',
              value:   stats?.tasks ? Math.round((stats.completedTasks/stats.tasks)*100) : 0,
              color:   'bg-primary',
              accent:  'text-primary',
              icon:    CheckSquare,
            },
            {
              label:   'Goal Completion Rate',
              value:   stats?.goals ? Math.round((stats.completedGoals/stats.goals)*100) : 0,
              color:   'bg-yellow-400',
              accent:  'text-yellow-400',
              icon:    Target,
            },
            {
              label:   'Average Goal Progress',
              value:   stats?.avgGoalProgress || 0,
              color:   'bg-cyan-400',
              accent:  'text-cyan-400',
              icon:    TrendingUp,
            },
          ].map(b => {
            const Icon = b.icon;
            return (
              <div key={b.label}>
                <div className="flex justify-between items-center mb-1.5">
                  <div className="flex items-center gap-2 text-xs md:text-sm text-soft">
                    <Icon size={13} className={b.accent} />
                    {b.label}
                  </div>
                  <span className={`text-xs font-bold ${b.accent}`}>{b.value}%</span>
                </div>
                <div className="h-2 bg-base rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${b.color} transition-all duration-700`}
                    style={{ width:`${b.value}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Account Info */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={15} className="text-primary" />
          <span className="text-sm font-bold text-soft">Account Info</span>
        </div>
        <div className="flex flex-col gap-3">
          {[
            { label:'Username',     value:profile?.username,          icon:User     },
            { label:'Email',        value:profile?.email||'Not set',  icon:Mail     },
            { label:'Member Since', value:joinDate,                   icon:Calendar },
          ].map(item => {
            const Icon = item.icon;
            return (
              <div key={item.label}
                className="flex items-center gap-3 p-3 bg-base rounded-xl border border-border">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Icon size={14} className="text-primary" />
                </div>
                <div>
                  <div className="text-[10px] text-muted font-semibold tracking-widest uppercase">
                    {item.label}
                  </div>
                  <div className="text-sm font-semibold text-soft">{item.value}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}