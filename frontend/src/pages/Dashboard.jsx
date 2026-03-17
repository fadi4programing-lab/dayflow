import { useState, useEffect } from 'react';
import { getTasks, getGoals, getEvents } from '../api';
import {
  CheckSquare, Target, TrendingUp, Calendar,
  Bell, Plus, Flame, Clock, AlertCircle
} from 'lucide-react';

export default function Dashboard() {
  const [tasks, setTasks]     = useState([]);
  const [goals, setGoals]     = useState([]);
  const [events, setEvents]   = useState([]);
  const [loading, setLoading] = useState(true);

  const user  = JSON.parse(localStorage.getItem('user') || '{}');
  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [t, g, e] = await Promise.all([
          getTasks(), getGoals(), getEvents()
        ]);
        setTasks(t.data);
        setGoals(g.data);
        setEvents(e.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const todayTasks     = tasks.filter(t => t.deadline === today);
  const completedToday = todayTasks.filter(t => t.is_completed).length;
  const completion     = todayTasks.length
    ? Math.round((completedToday / todayTasks.length) * 100)
    : 0;
  const todayEvents = events.filter(e => e.date === today);

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
  const weekDays   = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const barHeights = [60, 40, 85, 70, 90, 30, 50];
  const todayIndex = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;

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

      {/* Performance */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-primary" />
            <span className="text-sm font-bold text-soft">This Week</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-yellow-400 font-semibold">
            <Flame size={13} />
            <span className="hidden sm:inline">
              {tasks.filter(t => t.is_completed).length} tasks completed
            </span>
            <span className="sm:hidden">
              {tasks.filter(t => t.is_completed).length} done
            </span>
          </div>
        </div>

        <div className="flex items-end gap-1 md:gap-2 h-24 px-1">
          {weekDays.map((day, i) => {
            const isToday = i === todayIndex;
            return (
              <div key={day} className="flex-1 flex flex-col items-center gap-1">
                {isToday && (
                  <div className="text-[9px] text-primary font-bold">{barHeights[i]}%</div>
                )}
                <div className="w-full flex-1 flex items-end">
                  <div
                    className="w-full rounded-t-lg transition-all duration-500"
                    style={{
                      height:`${barHeights[i]}%`,
                      background: isToday
                        ? 'linear-gradient(180deg,#7C6AF7,#5B4ECC)'
                        : '#252340',
                      minHeight:'8px',
                    }}
                  />
                </div>
                <div className={`text-[10px] font-medium ${isToday ? 'text-primary' : 'text-muted'}`}>
                  {day}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-4 md:gap-6 mt-4 pt-3 border-t border-border flex-wrap">
          <div className="flex items-center gap-2 text-xs text-muted">
            <div className="w-3 h-3 rounded-sm bg-primary" /> Today
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            <div className="w-3 h-3 rounded-sm bg-border" /> Other days
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