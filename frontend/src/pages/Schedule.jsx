import { useState, useEffect } from 'react';
import { getTimeBlocks, createTimeBlock, updateTimeBlock, deleteTimeBlock } from '../api';
import {
  Clock, Plus, Trash2, Pencil,
  X, Check, AlertCircle, Calendar
} from 'lucide-react';

export default function Schedule() {
  const [blocks, setBlocks]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editBlock, setEditBlock] = useState(null);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [error, setError]   = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm]     = useState({
    title:'', date:'', start_time:'', end_time:'', color:'#7C6AF7'
  });

  useEffect(() => { fetchBlocks(); }, []);

  const fetchBlocks = async () => {
    try {
      const res = await getTimeBlocks();
      setBlocks(res.data);
    } catch { setError('Failed to load schedule'); }
    finally  { setLoading(false); }
  };

  const openCreate = () => {
    setEditBlock(null);
    setForm({ title:'', date:selectedDate, start_time:'09:00', end_time:'10:00', color:'#7C6AF7' });
    setShowForm(true);
  };

  const openEdit = (block) => {
    setEditBlock(block);
    setForm({
      title:      block.title,
      date:       block.date,
      start_time: block.start_time,
      end_time:   block.end_time,
      color:      block.color,
    });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.title.trim() || !form.date) return;
    setSaving(true);
    try {
      if (editBlock) {
        const res = await updateTimeBlock(editBlock.id, form);
        setBlocks(prev => prev.map(b => b.id === editBlock.id ? res.data : b));
      } else {
        const res = await createTimeBlock(form);
        setBlocks(prev => [...prev, res.data]);
      }
      setShowForm(false);
    } catch { setError('Failed to save block'); }
    finally  { setSaving(false); }
  };

  const handleDelete = async (id) => {
    try {
      await deleteTimeBlock(id);
      setBlocks(prev => prev.filter(b => b.id !== id));
    } catch { setError('Failed to delete block'); }
  };

  const getWeekDays = () => {
    const today  = new Date();
    const day    = today.getDay();
    const diff   = today.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(today.setDate(diff));
    return Array.from({ length:7 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d.toISOString().split('T')[0];
    });
  };

  const weekDays  = getWeekDays();
  const dayLabels = ['M','T','W','T','F','S','S'];
  const today     = new Date().toISOString().split('T')[0];
  const dayBlocks = blocks
    .filter(b => b.date === selectedDate)
    .sort((a,b) => a.start_time.localeCompare(b.start_time));

  const getDuration = (start, end) => {
    const [sh, sm] = start.split(':').map(Number);
    const [eh, em] = end.split(':').map(Number);
    const mins = (eh * 60 + em) - (sh * 60 + sm);
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  };

  const colorOptions = [
    '#7C6AF7','#4FC3F7','#6EE7B7',
    '#F6AD55','#F87171','#C4B5FD',
    '#34D399','#FB923C',
  ];

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
            <Clock size={22} className="text-primary" />
            Schedule
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1">
            {dayBlocks.length} blocks on {selectedDate === today ? 'today' : selectedDate}
          </p>
        </div>
        <button onClick={openCreate}
          className="btn-primary flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-xl">
          <Plus size={15} />
          <span className="text-xs md:text-sm">New Block</span>
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

      {/* Week Selector */}
      <div className="card p-3">
        <div className="grid grid-cols-7 gap-1">
          {weekDays.map((date, i) => {
            const dayNum     = new Date(date).getDate();
            const isToday    = date === today;
            const isSelected = date === selectedDate;
            const hasBlocks  = blocks.some(b => b.date === date);
            return (
              <button
                key={date}
                onClick={() => setSelectedDate(date)}
                className={`flex flex-col items-center py-2 rounded-xl transition-all duration-200
                  ${isSelected
                    ? 'bg-primary text-white'
                    : isToday
                    ? 'bg-primary/20 text-primary border border-primary/40'
                    : 'text-muted hover:bg-base hover:text-soft'
                  }`}
              >
                <span className="text-[9px] md:text-[10px] font-semibold tracking-wider uppercase mb-0.5">
                  {dayLabels[i]}
                </span>
                <span className="text-sm md:text-base font-extrabold">{dayNum}</span>
                {hasBlocks && (
                  <div className={`w-1 h-1 rounded-full mt-0.5
                    ${isSelected ? 'bg-white' : 'bg-primary'}`} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Timeline */}
      <div className="card">
        <div className="flex items-center gap-2 mb-5">
          <Calendar size={15} className="text-primary" />
          <span className="text-sm font-bold text-soft">
            {selectedDate === today ? "Today's" : selectedDate} Timeline
          </span>
          <span className="ml-auto text-xs text-muted bg-base px-2 py-1 rounded-lg">
            {dayBlocks.length} blocks
          </span>
        </div>

        {dayBlocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 gap-3">
            <div className="w-14 h-14 rounded-2xl bg-base flex items-center justify-center">
              <Clock size={26} className="text-border" />
            </div>
            <div className="text-soft font-semibold">No blocks scheduled</div>
            <div className="text-muted text-sm">Plan your day by adding time blocks</div>
            <button onClick={openCreate}
              className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl mt-1">
              <Plus size={15} /> Add Time Block
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            {dayBlocks.map((block, i) => (
              <div key={block.id} className="flex gap-3 items-stretch group">
                <div className="w-12 flex-shrink-0 flex flex-col items-end pt-3">
                  <span className="text-[10px] text-muted font-mono">
                    {block.start_time.slice(0,5)}
                  </span>
                </div>
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="w-3 h-3 rounded-full mt-2.5 flex-shrink-0 ring-2 ring-base"
                    style={{ background:block.color }} />
                  {i < dayBlocks.length - 1 && (
                    <div className="w-px flex-1 bg-border mt-1 mb-1" />
                  )}
                </div>
                <div className="flex-1 rounded-xl p-3 mb-2 flex items-center justify-between"
                  style={{
                    background: block.color + '15',
                    border: `1px solid ${block.color}30`,
                    borderLeftWidth: '3px',
                    borderLeftColor: block.color,
                  }}
                >
                  <div>
                    <div className="text-sm font-semibold text-soft">{block.title}</div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <Clock size={9} className="text-muted" />
                      <span className="text-[10px] md:text-[11px] text-muted font-mono">
                        {block.start_time.slice(0,5)} → {block.end_time.slice(0,5)}
                      </span>
                      <span className="text-[9px] md:text-[10px] font-semibold px-1.5 py-0.5 rounded"
                        style={{ background:block.color+'25', color:block.color }}>
                        {getDuration(block.start_time, block.end_time)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    <button onClick={() => openEdit(block)}
                      className="w-7 h-7 rounded-lg bg-base/60 hover:bg-base flex items-center justify-center">
                      <Pencil size={12} className="text-muted" />
                    </button>
                    <button onClick={() => handleDelete(block.id)}
                      className="w-7 h-7 rounded-lg hover:bg-red-900/40 flex items-center justify-center">
                      <Trash2 size={12} className="text-muted hover:text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm
          flex items-end sm:items-center justify-center z-50 px-0 sm:px-4">
          <div className="card w-full sm:max-w-md rounded-b-none sm:rounded-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Clock size={18} className="text-primary" />
                <h2 className="text-base font-bold text-soft">
                  {editBlock ? 'Edit Block' : 'New Time Block'}
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
                  Block Title
                </label>
                <input className="input" placeholder="e.g. Deep Work, Gym, Meeting..."
                  value={form.title} onChange={e => setForm({ ...form, title:e.target.value })} autoFocus />
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Date
                </label>
                <input className="input" type="date" value={form.date}
                  onChange={e => setForm({ ...form, date:e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                    Start
                  </label>
                  <input className="input" type="time" value={form.start_time}
                    onChange={e => setForm({ ...form, start_time:e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                    End
                  </label>
                  <input className="input" type="time" value={form.end_time}
                    onChange={e => setForm({ ...form, end_time:e.target.value })} />
                </div>
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-2 block">
                  Color
                </label>
                <div className="flex gap-2 flex-wrap">
                  {colorOptions.map(c => (
                    <button key={c} onClick={() => setForm({ ...form, color:c })}
                      className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
                      style={{ background:c }}>
                      {form.color === c && <Check size={14} className="text-white" />}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="btn-ghost flex-1 py-2.5 rounded-xl">
                Cancel
              </button>
              <button onClick={handleSubmit} disabled={saving || !form.title.trim() || !form.date}
                className="btn-primary flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50">
                {saving
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Check size={15} />
                }
                {editBlock ? 'Save Changes' : 'Add Block'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}