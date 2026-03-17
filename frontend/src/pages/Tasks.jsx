import { useState, useEffect } from 'react';
import { getTasks, createTask, updateTask, deleteTask } from '../api';
import {
  Plus, Trash2, Pencil, X, Check,
  CheckSquare, Clock, AlertCircle, Filter
} from 'lucide-react';

export default function Tasks() {
  const [tasks, setTasks]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [filter, setFilter]     = useState('all');
  const [showForm, setShowForm] = useState(false);
  const [editTask, setEditTask] = useState(null);
  const [form, setForm]         = useState({ title:'', priority:'medium', deadline:'' });
  const [error, setError]       = useState('');
  const [saving, setSaving]     = useState(false);

  useEffect(() => { fetchTasks(); }, []);

  const fetchTasks = async () => {
    try {
      const res = await getTasks();
      setTasks(res.data);
    } catch { setError('Failed to load tasks'); }
    finally  { setLoading(false); }
  };

  const openCreate = () => {
    setEditTask(null);
    setForm({ title:'', priority:'medium', deadline:'' });
    setShowForm(true);
  };

  const openEdit = (task) => {
    setEditTask(task);
    setForm({ title:task.title, priority:task.priority, deadline:task.deadline || '' });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      if (editTask) {
        const res = await updateTask(editTask.id, form);
        setTasks(prev => prev.map(t => t.id === editTask.id ? res.data : t));
      } else {
        const res = await createTask(form);
        setTasks(prev => [res.data, ...prev]);
      }
      setShowForm(false);
    } catch { setError('Failed to save task'); }
    finally  { setSaving(false); }
  };

  const handleToggle = async (task) => {
    try {
      const res = await updateTask(task.id, { ...task, is_completed: !task.is_completed });
      setTasks(prev => prev.map(t => t.id === task.id ? res.data : t));
    } catch { setError('Failed to update task'); }
  };

  const handleDelete = async (id) => {
    try {
      await deleteTask(id);
      setTasks(prev => prev.filter(t => t.id !== id));
    } catch { setError('Failed to delete task'); }
  };

  const filtered = tasks.filter(t => {
    if (filter === 'all')       return true;
    if (filter === 'active')    return !t.is_completed;
    if (filter === 'completed') return t.is_completed;
    return t.priority === filter;
  });

  const counts = {
    all:       tasks.length,
    active:    tasks.filter(t => !t.is_completed).length,
    completed: tasks.filter(t => t.is_completed).length,
    high:      tasks.filter(t => t.priority === 'high').length,
  };

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
            <CheckSquare size={22} className="text-primary" />
            Tasks
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1">
            {counts.active} remaining · {counts.completed} completed
          </p>
        </div>
        <button
          onClick={openCreate}
          className="btn-primary flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-xl"
        >
          <Plus size={15} />
          <span className="text-xs md:text-sm">New Task</span>
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm
          px-4 py-3 rounded-xl flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
          <button onClick={() => setError('')} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} className="text-muted hidden sm:block" />
        {[
          { key:'all',       label:`All (${counts.all})`       },
          { key:'active',    label:`Active (${counts.active})` },
          { key:'completed', label:`Done (${counts.completed})`},
          { key:'high',      label:`High (${counts.high})`     },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
              ${filter === f.key
                ? 'bg-primary text-white'
                : 'bg-surface border border-border text-muted hover:text-soft'
              }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="card p-0 overflow-hidden">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="w-14 h-14 rounded-2xl bg-base flex items-center justify-center">
              <CheckSquare size={26} className="text-border" />
            </div>
            <div className="text-muted text-sm">No tasks here</div>
            <button
              onClick={openCreate}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              <Plus size={12} /> Create your first task
            </button>
          </div>
        ) : (
          filtered.map((task, i) => (
            <div
              key={task.id}
              className={`flex items-center gap-3 px-4 py-4 transition-all
                hover:bg-base group
                ${i !== filtered.length - 1 ? 'border-b border-border' : ''}`}
            >
              <button
                onClick={() => handleToggle(task)}
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0
                  transition-all duration-200
                  ${task.is_completed
                    ? 'bg-primary border-primary'
                    : 'border-border hover:border-primary'
                  }`}
              >
                {task.is_completed && <Check size={11} className="text-white" />}
              </button>

              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium
                  ${task.is_completed ? 'line-through text-muted' : 'text-soft'}`}>
                  {task.title}
                </div>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  {task.deadline && (
                    <div className="flex items-center gap-1 text-[11px] text-muted">
                      <Clock size={10} /> {task.deadline}
                    </div>
                  )}
                  <span className={`badge-${task.priority} sm:hidden`}>
                    {task.priority}
                  </span>
                </div>
              </div>

              <span className={`badge-${task.priority} flex-shrink-0 hidden sm:inline`}>
                {task.priority}
              </span>

              <div className="flex items-center gap-1 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => openEdit(task)}
                  className="w-7 h-7 rounded-lg bg-base hover:bg-border
                    flex items-center justify-center transition-all"
                >
                  <Pencil size={13} className="text-muted" />
                </button>
                <button
                  onClick={() => handleDelete(task.id)}
                  className="w-7 h-7 rounded-lg bg-base hover:bg-red-900/40
                    flex items-center justify-center transition-all"
                >
                  <Trash2 size={13} className="text-muted hover:text-red-400" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm
          flex items-end sm:items-center justify-center z-50 px-0 sm:px-4">
          <div className="card w-full sm:max-w-md rounded-b-none sm:rounded-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <CheckSquare size={18} className="text-primary" />
                <h2 className="text-base font-bold text-soft">
                  {editTask ? 'Edit Task' : 'New Task'}
                </h2>
              </div>
              <button
                onClick={() => setShowForm(false)}
                className="w-7 h-7 rounded-lg hover:bg-base flex items-center justify-center"
              >
                <X size={16} className="text-muted" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Task Title
                </label>
                <input
                  className="input"
                  placeholder="What do you need to do?"
                  value={form.title}
                  onChange={e => setForm({ ...form, title: e.target.value })}
                  autoFocus
                />
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Priority
                </label>
                <div className="flex gap-2">
                  {['low','medium','high'].map(p => (
                    <button
                      key={p}
                      onClick={() => setForm({ ...form, priority: p })}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold uppercase tracking-wide transition-all
                        ${form.priority === p
                          ? p === 'high'   ? 'bg-red-900/60 text-red-400 border border-red-700'
                          : p === 'medium' ? 'bg-yellow-900/60 text-yellow-400 border border-yellow-700'
                          :                  'bg-green-900/60 text-green-400 border border-green-700'
                          : 'bg-base border border-border text-muted hover:border-muted'
                        }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Deadline
                </label>
                <input
                  className="input"
                  type="date"
                  value={form.deadline}
                  onChange={e => setForm({ ...form, deadline: e.target.value })}
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowForm(false)}
                className="btn-ghost flex-1 py-2.5 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving || !form.title.trim()}
                className="btn-primary flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {saving
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Check size={15} />
                }
                {editTask ? 'Save Changes' : 'Create Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}