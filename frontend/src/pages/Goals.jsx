import { useState, useEffect } from 'react';
import { getGoals, createGoal, updateGoal, deleteGoal } from '../api';
import {
  Target, Plus, Trash2, Pencil, X,
  Check, AlertCircle, Calendar, TrendingUp, CheckCircle
} from 'lucide-react';

export default function Goals() {
  const [goals, setGoals]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editGoal, setEditGoal] = useState(null);
  const [error, setError]       = useState('');
  const [saving, setSaving]     = useState(false);
  const [form, setForm]         = useState({
    title:'', description:'', progress:0, target_date:'', is_completed:false
  });

  useEffect(() => { fetchGoals(); }, []);

  const fetchGoals = async () => {
    try {
      const res = await getGoals();
      setGoals(res.data);
    } catch { setError('Failed to load goals'); }
    finally  { setLoading(false); }
  };

  const openCreate = () => {
    setEditGoal(null);
    setForm({ title:'', description:'', progress:0, target_date:'', is_completed:false });
    setShowForm(true);
  };

  const openEdit = (goal) => {
    setEditGoal(goal);
    setForm({
      title:        goal.title,
      description:  goal.description  || '',
      progress:     goal.progress,
      target_date:  goal.target_date  || '',
      is_completed: goal.is_completed,
    });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      if (editGoal) {
        const res = await updateGoal(editGoal.id, form);
        setGoals(prev => prev.map(g => g.id === editGoal.id ? res.data : g));
      } else {
        const res = await createGoal(form);
        setGoals(prev => [res.data, ...prev]);
      }
      setShowForm(false);
    } catch { setError('Failed to save goal'); }
    finally  { setSaving(false); }
  };

  const handleDelete = async (id) => {
    try {
      await deleteGoal(id);
      setGoals(prev => prev.filter(g => g.id !== id));
    } catch { setError('Failed to delete goal'); }
  };

  const handleToggleComplete = async (goal) => {
    try {
      const res = await updateGoal(goal.id, {
        ...goal,
        is_completed: !goal.is_completed,
        progress: !goal.is_completed ? 100 : goal.progress,
      });
      setGoals(prev => prev.map(g => g.id === goal.id ? res.data : g));
    } catch { setError('Failed to update goal'); }
  };

  const goalColors = ['#7C6AF7','#4FC3F7','#6EE7B7','#F6AD55','#F87171','#C4B5FD'];
  const active     = goals.filter(g => !g.is_completed);
  const completed  = goals.filter(g => g.is_completed);
  const avgProgress = goals.length
    ? Math.round(goals.reduce((s,g) => s + g.progress, 0) / goals.length)
    : 0;

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col gap-5 max-w-4xl">

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Target size={22} className="text-yellow-400" />
            Goals
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1">
            {active.length} active · {completed.length} completed
          </p>
        </div>
        <button
          onClick={openCreate}
          className="btn-primary flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-xl"
        >
          <Plus size={15} />
          <span className="text-xs md:text-sm">New Goal</span>
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm
          px-4 py-3 rounded-xl flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
        {[
          { label:'Total Goals',  value:goals.length,    accent:'text-primary',    bg:'bg-primary/10',    icon:Target     },
          { label:'In Progress',  value:active.length,   accent:'text-cyan-400',   bg:'bg-cyan-400/10',   icon:TrendingUp },
          { label:'Avg Progress', value:`${avgProgress}%`,accent:'text-yellow-400',bg:'bg-yellow-400/10', icon:TrendingUp },
        ].map(s => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="card flex flex-col gap-2 p-3 md:p-5">
              <div className="flex items-center justify-between">
                <span className="section-title mb-0">{s.label}</span>
                <div className={`w-7 h-7 rounded-lg ${s.bg} flex items-center justify-center`}>
                  <Icon size={13} className={s.accent} />
                </div>
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold ${s.accent}`}>{s.value}</div>
            </div>
          );
        })}
      </div>

      {/* Active Goals */}
      {active.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp size={15} className="text-primary" />
            <span className="text-sm font-bold text-soft">In Progress</span>
          </div>
          {active.map((goal, i) => {
            const c = goalColors[i % goalColors.length];
            return (
              <div key={goal.id} className="card group">
                <div className="flex items-start gap-3 md:gap-4">
                  <div className="w-12 h-12 md:w-14 md:h-14 rounded-full flex items-center
                    justify-center flex-shrink-0 border-2"
                    style={{ borderColor:c, background:c+'15' }}
                  >
                    <span className="text-xs font-extrabold" style={{ color:c }}>
                      {goal.progress}%
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-soft mb-0.5">{goal.title}</div>
                    {goal.description && (
                      <div className="text-xs text-muted mb-2 line-clamp-2">
                        {goal.description}
                      </div>
                    )}
                    <div className="h-1.5 bg-base rounded-full overflow-hidden mb-1.5">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width:`${goal.progress}%`, background:c }} />
                    </div>
                    {goal.target_date && (
                      <div className="flex items-center gap-1 text-[10px] text-muted">
                        <Calendar size={9} /> Target: {goal.target_date}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    <button onClick={() => handleToggleComplete(goal)}
                      className="w-7 h-7 rounded-lg bg-base hover:bg-green-900/40 flex items-center justify-center">
                      <CheckCircle size={13} className="text-muted hover:text-green-400" />
                    </button>
                    <button onClick={() => openEdit(goal)}
                      className="w-7 h-7 rounded-lg bg-base hover:bg-border flex items-center justify-center">
                      <Pencil size={13} className="text-muted" />
                    </button>
                    <button onClick={() => handleDelete(goal.id)}
                      className="w-7 h-7 rounded-lg bg-base hover:bg-red-900/40 flex items-center justify-center">
                      <Trash2 size={13} className="text-muted hover:text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Completed Goals */}
      {completed.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <CheckCircle size={15} className="text-green-400" />
            <span className="text-sm font-bold text-soft">Completed</span>
          </div>
          {completed.map(goal => (
            <div key={goal.id} className="card group opacity-60 hover:opacity-100 transition-opacity">
              <div className="flex items-center gap-3 md:gap-4">
                <div className="w-12 h-12 rounded-full flex items-center justify-center
                  flex-shrink-0 border-2 border-green-700 bg-green-900/20">
                  <CheckCircle size={18} className="text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-soft line-through mb-0.5">{goal.title}</div>
                  {goal.target_date && (
                    <div className="flex items-center gap-1 text-[10px] text-muted">
                      <Calendar size={9} /> {goal.target_date}
                    </div>
                  )}
                  <div className="h-1.5 bg-base rounded-full overflow-hidden mt-2">
                    <div className="h-full rounded-full bg-green-500 w-full" />
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                  <button onClick={() => handleToggleComplete(goal)}
                    className="w-7 h-7 rounded-lg bg-base hover:bg-border flex items-center justify-center">
                    <X size={13} className="text-muted" />
                  </button>
                  <button onClick={() => handleDelete(goal.id)}
                    className="w-7 h-7 rounded-lg bg-base hover:bg-red-900/40 flex items-center justify-center">
                    <Trash2 size={13} className="text-muted hover:text-red-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {goals.length === 0 && (
        <div className="card flex flex-col items-center justify-center py-16 gap-3">
          <div className="w-14 h-14 rounded-2xl bg-base flex items-center justify-center">
            <Target size={26} className="text-border" />
          </div>
          <div className="text-soft font-semibold">No goals yet</div>
          <div className="text-muted text-sm text-center">
            Set your first goal and start tracking progress
          </div>
          <button onClick={openCreate}
            className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl mt-1">
            <Plus size={15} /> Create First Goal
          </button>
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm
          flex items-end sm:items-center justify-center z-50 px-0 sm:px-4">
          <div className="card w-full sm:max-w-md rounded-b-none sm:rounded-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Target size={18} className="text-yellow-400" />
                <h2 className="text-base font-bold text-soft">
                  {editGoal ? 'Edit Goal' : 'New Goal'}
                </h2>
              </div>
              <button onClick={() => setShowForm(false)}
                className="w-7 h-7 rounded-lg hover:bg-base flex items-center justify-center">
                <X size={16} className="text-muted" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Goal Title
                </label>
                <input className="input" placeholder="What do you want to achieve?"
                  value={form.title} onChange={e => setForm({ ...form, title:e.target.value })} autoFocus />
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Description
                </label>
                <textarea className="input resize-none" rows={3} placeholder="Describe your goal..."
                  value={form.description} onChange={e => setForm({ ...form, description:e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Progress: {form.progress}%
                </label>
                <input type="range" min={0} max={100} value={form.progress}
                  onChange={e => setForm({ ...form, progress:parseInt(e.target.value) })}
                  className="w-full accent-primary" />
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>0%</span><span>50%</span><span>100%</span>
                </div>
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Target Date
                </label>
                <input className="input" type="date" value={form.target_date}
                  onChange={e => setForm({ ...form, target_date:e.target.value })} />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="btn-ghost flex-1 py-2.5 rounded-xl">
                Cancel
              </button>
              <button onClick={handleSubmit} disabled={saving || !form.title.trim()}
                className="btn-primary flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50">
                {saving
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Check size={15} />
                }
                {editGoal ? 'Save Changes' : 'Create Goal'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}