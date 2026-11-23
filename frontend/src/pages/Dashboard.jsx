import { useState, useEffect } from 'react';
import { getTasks, getGoals, getEvents, analyticsAPI } from '../api';
import {
  CheckSquare, Target, TrendingUp, Calendar,
  Bell, Plus, Flame, Clock, AlertCircle, Sparkles, Activity
} from 'lucide-react';

export default function Dashboard() {
  const [tasks, setTasks]     = useState([]);
  const [goals, setGoals]     = useState([]);
  const [events, setEvents]   = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState(false);
  const [loading, setLoading] = useState(true);

  const user  = JSON.parse(localStorage.getItem('user') || '{}');
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

  useEffect(() => {
    let cancelled = false;

    const fetchCore = async () => {
      try {
        const [t, g, e] = await Promise.all([
          getTasks(), getGoals(), getEvents()
        ]);
        if (cancelled) return;
        setTasks(t.data);
        setGoals(g.data);
        setEvents(e.data);
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    const fetchAnalytics = async () => {
      try {
        const res = await analyticsAPI.getOverview();
        if (!cancelled) setAnalytics(res.data);
      } catch (err) {
        console.error(err);
        if (!cancelled) setAnalyticsError(true);
      } finally {
        if (!cancelled) setAnalyticsLoading(false);
      }
    };

    fetchCore();
    fetchAnalytics();
    return () => { cancelled = true; };
  }, []);

  const todayTasks     = tasks.filter(t => t.deadline === today);
  const completedToday = todayTasks.filter(t => t.is_completed).length;
  const completion     = todayTasks.length
    ? Math.round((completedToday / todayTasks.length) * 100)
    : 0;
  const todayEvents = events.filter(e => e.date === today);

  const weeklyScores = analytics?.daily_scores_7d || [];
  const chartData = weeklyScores.map((point) => {
    const pointDate = new Date(`${point.date}T00:00:00`);
    return {
      ...point,
      label: pointDate.toLocaleDateString('en-US', { weekday: 'short' }),
      isToday: point.date === today,
    };
  });
  const consistencyScore = Math.min(
    100,
    Math.max(0, Number(analytics?.rolling_consistency_score || 0))
  );
  const burnoutRisk = analytics?.burnout_risk || 'low';
  const burnoutLabel = burnoutRisk.charAt(0).toUpperCase() + burnoutRisk.slice(1);
  const burnoutStyles = {
    low: 'bg-green-900/40 text-green-400 border-green-800',
    moderate: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
    high: 'bg-red-900/40 text-red-400 border-red-800',
  };
  const burnoutClass = burnoutStyles[burnoutRisk] || burnoutStyles.low;
  const modelLabel = analytics?.mode === 'hybrid'
    ? 'Hybrid ML'
    : analytics?.cold_start
      ? 'Cold-start heuristic'
      : 'Heuristic engine';

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const typeStyle = {
    meeting:  { bg:'bg-purple-900/30', text:'text-purple-400', dot:'#7C6AF7' },
    focus:    { bg:'bg-cyan-900/30',   text:'text-cyan-400',   dot:'#4FC3F7' },
    deadline: { bg:'bg-red-900/30',    text:'text-red-400',    dot:'#F87171' },
    reminder: { bg:'bg-yellow-900/30', text:'text-yellow-400', dot:'#F6AD55' },
    personal: { bg:'bg-green-900/30',  text:'text-green-400',  dot:'#6EE7B7' },
  };

  const goalColors = ['#7C6AF7','#4FC3F7','#6EE7B7','#F6AD55'];

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col gap-5 max-w-6xl">

      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-soft tracking-tight">
            {getGreeting()}, {user.username}
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1">
            {new Date().toLocaleDateString('en-US', {
              weekday:'long', year:'numeric', month:'long', day:'numeric'
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost flex items-center gap-2 px-3 py-2 rounded-xl">
            <Bell size={15} />
            <span className="text-xs hidden sm:inline">Notifications</span>
          </button>
          <button
            onClick={() => window.location.href = '/tasks'}
            className="btn-primary flex items-center gap-2 px-3 md:px-4 py-2 rounded-xl"
          >
            <Plus size={15} />
            <span className="text-xs md:text-sm">Add Task</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {[
          { label:'Tasks Today',  value: todayTasks.length,                        sub:'scheduled',   accent:'text-primary',    bg:'bg-primary/10',    icon: CheckSquare },
          { label:'Completed',    value: completedToday,                           sub:'done today',  accent:'text-green-400',  bg:'bg-green-400/10',  icon: CheckSquare },
          { label:'Completion',   value:`${completion}%`,                          sub:'rate today',  accent:'text-cyan-400',   bg:'bg-cyan-400/10',   icon: TrendingUp  },
          { label:'Active Goals', value: goals.filter(g=>!g.is_completed).length,  sub:'in progress', accent:'text-yellow-400', bg:'bg-yellow-400/10', icon: Target      },
        ].map(s => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="card flex flex-col gap-2 p-3 md:p-5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] md:text-xs font-semibold tracking-widest uppercase text-muted">
                  {s.label}
                </span>
                <div className={`w-7 h-7 md:w-8 md:h-8 rounded-lg ${s.bg} flex items-center justify-center`}>
                  <Icon size={13} className={s.accent} />
                </div>
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold ${s.accent}`}>{s.value}</div>
              <div className="text-[10px] md:text-xs text-muted">{s.sub}</div>
            </div>
          );
        })}
      </div>

      {/* AI Consistency & Insights */}
      <div className="card">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-primary" />
            <span className="text-sm font-bold text-soft">AI Consistency & Insights</span>
          </div>
          {analytics && (
            <span className="text-[10px] font-bold uppercase tracking-wide text-primary
              bg-primary/10 border border-primary/30 px-2.5 py-1 rounded-lg">
              {modelLabel}
            </span>
          )}
        </div>

        {analyticsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 animate-pulse">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-28 rounded-xl bg-base border border-border" />
            ))}
          </div>
        ) : analytics ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-base border border-border rounded-xl p-4">
                <div className="section-title mb-2 text-[10px]">Rolling Consistency</div>
                <div className="flex items-center gap-4">
                  <div
                    className="relative w-20 h-20 rounded-full flex-shrink-0"
                    style={{
                      background: `conic-gradient(#7C6AF7 ${consistencyScore * 3.6}deg, #252340 0deg)`,
                    }}
                  >
                    <div className="absolute inset-2 rounded-full bg-surface flex items-center justify-center">
                      <span className="text-xl font-extrabold text-soft">
                        {Math.round(consistencyScore)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-extrabold text-primary">
                      {Math.round(consistencyScore)}
                      <span className="text-sm text-muted">/100</span>
                    </div>
                    <div className="text-[11px] text-muted mt-0.5">
                      14-day exponential score
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-base border border-border rounded-xl p-4">
                <div className="section-title mb-2 text-[10px]">Momentum</div>
                <div className="flex items-center gap-2">
                  <Flame size={18} className="text-yellow-400" />
                  <span className="text-2xl font-extrabold text-soft">
                    {analytics.streak_days || 0}
                  </span>
                  <span className="text-xs text-muted">day streak</span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-4">
                  <span className="text-[11px] text-muted">Burnout risk</span>
                  <span className={`text-[10px] font-bold uppercase tracking-wide
                    px-2 py-1 rounded-lg border ${burnoutClass}`}>
                    {burnoutLabel}
                  </span>
                </div>
              </div>

              <div className="bg-base border border-border rounded-xl p-4">
                <div className="section-title mb-2 text-[10px]">Behavioral Pattern</div>
                <div className="text-sm font-bold text-soft">
                  {analytics.day_archetype || 'Steady Flow'}
                </div>
                <p className="text-[11px] text-muted mt-2 line-clamp-3 leading-relaxed">
                  {analytics.dominant_factor ||
                    'Log a few days of activity to unlock a behavioral insight.'}
                </p>
              </div>
            </div>

            {analytics.recommendations?.[0] && (
              <div className="mt-3 flex items-start gap-2 rounded-xl border border-primary/20
                bg-primary/5 px-3 py-2.5">
                <Activity size={13} className="text-primary mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted">{analytics.recommendations[0]}</p>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-xl border border-border bg-base px-4 py-5 text-xs text-muted">
            {analyticsError
              ? 'AI insights are unavailable right now.'
              : 'AI insights will appear as you log daily activity.'}
          </div>
        )}
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Today's Tasks */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckSquare size={16} className="text-primary" />
              <span className="text-sm font-bold text-soft">Today's Tasks</span>
            </div>
            <span className="text-xs text-muted bg-base px-2 py-1 rounded-lg">
              {completedToday}/{todayTasks.length} done
            </span>
          </div>

          {todayTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <div className="w-12 h-12 rounded-2xl bg-base flex items-center justify-center">
                <CheckSquare size={22} className="text-border" />
              </div>
              <div className="text-muted text-sm">No tasks for today</div>
              <button
                onClick={() => window.location.href = '/tasks'}
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <Plus size={12} /> Add a task
              </button>
            </div>
          ) : (
            <div className="flex flex-col">
              {todayTasks.map(task => (
                <div key={task.id}
                  className="flex items-center gap-3 py-2.5 border-b border-border last:border-0">
                  <div className={`w-4 h-4 rounded-md border-2 flex items-center justify-center flex-shrink-0
                    ${task.is_completed ? 'bg-primary border-primary' : 'border-border'}`}>
                    {task.is_completed && <CheckSquare size={10} className="text-white" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm truncate
                      ${task.is_completed ? 'line-through text-muted' : 'text-soft'}`}>
                      {task.title}
                    </div>
                    {task.deadline && (
                      <div className="text-[10px] text-muted mt-0.5 flex items-center gap-1">
                        <Clock size={9} /> Due {task.deadline}
                      </div>
                    )}
                  </div>
                  <span className={`badge-${task.priority}`}>{task.priority}</span>
                </div>
              ))}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-muted mb-1.5">
                  <span>Progress</span><span>{completion}%</span>
                </div>
                <div className="h-1.5 bg-base rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-primary transition-all duration-700"
                    style={{ width:`${completion}%` }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Goals */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Target size={16} className="text-yellow-400" />
              <span className="text-sm font-bold text-soft">Goals Progress</span>
            </div>
            <button
              onClick={() => window.location.href = '/goals'}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              See all <TrendingUp size={11} />
            </button>
          </div>

          {goals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <div className="w-12 h-12 rounded-2xl bg-base flex items-center justify-center">
                <Target size={22} className="text-border" />
              </div>
              <div className="text-muted text-sm">No goals yet</div>
              <button
                onClick={() => window.location.href = '/goals'}
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <Plus size={12} /> Add a goal
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {goals.slice(0,4).map((goal, i) => {
                const c = goalColors[i % goalColors.length];
                return (
                  <div key={goal.id}>
                    <div className="flex justify-between items-center mb-1.5">
                      <div className="text-sm text-soft truncate flex-1 pr-3">{goal.title}</div>
                      <div className="text-xs font-bold flex-shrink-0" style={{ color:c }}>
                        {goal.progress}%
                      </div>
                    </div>
                    <div className="h-1.5 bg-base rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width:`${goal.progress}%`, background:c }} />
                    </div>
                    {goal.target_date && (
                      <div className="text-[10px] text-muted mt-1 flex items-center gap-1">
                        <Calendar size={9} /> Target: {goal.target_date}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Events */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-cyan-400" />
            <span className="text-sm font-bold text-soft">Today's Events</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted hidden sm:inline">
              {todayEvents.length} scheduled
            </span>
            <button
              onClick={() => window.location.href = '/calendar'}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View calendar <Calendar size={11} />
            </button>
          </div>
        </div>

        {todayEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="w-12 h-12 rounded-2xl bg-base flex items-center justify-center">
              <Calendar size={22} className="text-border" />
            </div>
            <div className="text-muted text-sm">No events today</div>
            <button
              onClick={() => window.location.href = '/calendar'}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              <Plus size={12} /> Add an event
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {todayEvents.map(event => {
              const s = typeStyle[event.event_type] || typeStyle.reminder;
              return (
                <div key={event.id} className={`${s.bg} rounded-xl p-4 border border-border`}>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full" style={{ background:s.dot }} />
                    <span className={`text-xs font-bold uppercase tracking-wide ${s.text}`}>
                      {event.event_type}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-soft">{event.title}</div>
                  {event.description && (
                    <div className="text-xs text-muted mt-1 line-clamp-2">{event.description}</div>
                  )}
                  {event.start_time && (
                    <div className="text-xs text-muted mt-2 flex items-center gap-1">
                      <Clock size={10} />
                      {event.start_time}
                      {event.end_time && ` → ${event.end_time}`}
                    </div>
                  )}
                  {event.notify_by_email && (
                    <div className="text-[10px] text-primary mt-2 flex items-center gap-1">
                      <Bell size={10} /> Email reminder on
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 7-Day Consistency */}
      <div className="card">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-primary" />
            <span className="text-sm font-bold text-soft">7-Day Consistency</span>
          </div>
          <div className="flex items-center gap-3">
            {analytics && (
              <span className="text-xs font-bold text-primary">
                {Math.round(consistencyScore)}/100 rolling
              </span>
            )}
            <div className="flex items-center gap-1.5 text-xs text-yellow-400 font-semibold">
              <Flame size={13} />
              <span className="hidden sm:inline">
                {analytics
                  ? `${analytics.streak_days || 0} day streak`
                  : `${tasks.filter(t => t.is_completed).length} tasks completed`}
              </span>
              <span className="sm:hidden">
                {analytics
                  ? `${analytics.streak_days || 0}d`
                  : `${tasks.filter(t => t.is_completed).length} done`}
              </span>
            </div>
          </div>
        </div>

        {chartData.length === 0 ? (
          <div className="h-24 flex items-center justify-center text-xs text-muted">
            Daily scores will appear after your first analytics snapshot.
          </div>
        ) : (
          <div className="flex items-end gap-1 md:gap-2 h-24 px-1">
            {chartData.map((point) => (
              <div
                key={point.date}
                className="flex-1 flex flex-col items-center gap-1"
                title={`${point.date}: ${Math.round(point.score)}%`}
              >
                {point.isToday && (
                  <div className="text-[9px] text-primary font-bold">
                    {Math.round(point.score)}%
                  </div>
                )}
                <div className="w-full flex-1 flex items-end">
                  <div
                    className="w-full rounded-t-lg transition-all duration-500"
                    style={{
                      height: `${Math.max(0, Math.min(100, point.score))}%`,
                      background: point.isToday
                        ? 'linear-gradient(180deg,#7C6AF7,#5B4ECC)'
                        : '#252340',
                      minHeight: '8px',
                    }}
                  />
                </div>
                <div className={`text-[10px] font-medium
                  ${point.isToday ? 'text-primary' : 'text-muted'}`}>
                  {point.label}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-4 md:gap-6 mt-4 pt-3 border-t border-border flex-wrap">
          <div className="flex items-center gap-2 text-xs text-muted">
            <div className="w-3 h-3 rounded-sm bg-primary" /> Today
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            <div className="w-3 h-3 rounded-sm bg-border" /> Daily score
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-xs text-muted">
            <AlertCircle size={11} />
            {todayTasks.length - completedToday} remaining
          </div>
        </div>
      </div>

    </div>
  );
}