import { useState, useEffect } from 'react';
import {
  getCalendarTasks, addToCalendar, removeFromCalendar,
  getEvents, createEvent, deleteEvent, getTasks
} from '../api';
import {
  Calendar, Plus, Trash2, X, Check,
  AlertCircle, Bell, BellOff, Clock,
  ChevronLeft, ChevronRight, Tag
} from 'lucide-react';

export default function CalendarPage() {
  const [calTasks, setCalTasks]   = useState([]);
  const [events, setEvents]       = useState([]);
  const [allTasks, setAllTasks]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [showEventForm, setShowEventForm] = useState(false);
  const [showTaskForm, setShowTaskForm]   = useState(false);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');

  const [eventForm, setEventForm] = useState({
    title:'', description:'', event_type:'reminder',
    date:'', start_time:'', end_time:'',
    notify_by_email: true,
  });

  const [taskForm, setTaskForm] = useState({
    task_id:'', date:'', notify_by_email: true
  });

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [ct, ev, tk] = await Promise.all([
        getCalendarTasks(''),
        getEvents(),
        getTasks(),
      ]);
      // getCalendarTasks with empty string returns all
      setCalTasks(ct.data);
      setEvents(ev.data);
      setAllTasks(tk.data);
    } catch { setError('Failed to load calendar'); }
    finally  { setLoading(false); }
  };

  // ── Calendar grid helpers ──
  const getDaysInMonth = (date) => {
    const year  = date.getFullYear();
    const month = date.getMonth();
    const first = new Date(year, month, 1).getDay();
    const days  = new Date(year, month + 1, 0).getDate();
    const offset = first === 0 ? 6 : first - 1;
    return { days, offset };
  };

  const formatDate = (year, month, day) => {
    const m = String(month + 1).padStart(2,'0');
    const d = String(day).padStart(2,'0');
    return `${year}-${m}-${d}`;
  };

  const prevMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() + 1));
  };

  const { days, offset } = getDaysInMonth(currentMonth);
  const today = new Date().toISOString().split('T')[0];

  const getDateItems = (dateStr) => ({
    tasks:  calTasks.filter(ct => ct.date === dateStr),
    events: events.filter(ev => ev.date === dateStr),
  });

  const selectedItems = getDateItems(selectedDate);

  // ── Event form ──
  const openEventForm = () => {
    setEventForm({
      title:'', description:'', event_type:'reminder',
      date: selectedDate, start_time:'', end_time:'',
      notify_by_email: true,
    });
    setShowEventForm(true);
  };

  const handleCreateEvent = async () => {
    if (!eventForm.title.trim() || !eventForm.date) return;
    setSaving(true);
    try {
      const res = await createEvent(eventForm);
      setEvents(prev => [...prev, res.data]);
      setShowEventForm(false);
    } catch { setError('Failed to create event'); }
    finally  { setSaving(false); }
  };

  const handleDeleteEvent = async (id) => {
    try {
      await deleteEvent(id);
      setEvents(prev => prev.filter(e => e.id !== id));
    } catch { setError('Failed to delete event'); }
  };

  // ── Calendar task form ──
  const openTaskForm = () => {
    setTaskForm({ task_id:'', date: selectedDate, notify_by_email: true });
    setShowTaskForm(true);
  };

  const handleAddCalTask = async () => {
    if (!taskForm.task_id || !taskForm.date) return;
    setSaving(true);
    try {
      const res = await addToCalendar({
        task:            taskForm.task_id,
        date:            taskForm.date,
        notify_by_email: taskForm.notify_by_email,
      });
      setCalTasks(prev => [...prev, res.data]);
      setShowTaskForm(false);
    } catch { setError('Task already pinned to this date or failed'); }
    finally  { setSaving(false); }
  };

  const handleRemoveCalTask = async (id) => {
    try {
      await removeFromCalendar(id);
      setCalTasks(prev => prev.filter(ct => ct.id !== id));
    } catch { setError('Failed to remove task'); }
  };

  const typeStyle = {
    meeting:  { bg:'bg-purple-900/30', text:'text-purple-400', dot:'#7C6AF7'  },
    focus:    { bg:'bg-cyan-900/30',   text:'text-cyan-400',   dot:'#4FC3F7'  },
    deadline: { bg:'bg-red-900/30',    text:'text-red-400',    dot:'#F87171'  },
    reminder: { bg:'bg-yellow-900/30', text:'text-yellow-400', dot:'#F6AD55'  },
    personal: { bg:'bg-green-900/30',  text:'text-green-400',  dot:'#6EE7B7'  },
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-5xl">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Calendar size={24} className="text-primary" />
            Calendar
          </h1>
          <p className="text-muted text-sm mt-1">
            Plan tasks and events with email reminders
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openTaskForm}
            className="btn-ghost flex items-center gap-2 px-4 py-2.5 rounded-xl"
          >
            <Plus size={15} />
            Pin Task
          </button>
          <button
            onClick={openEventForm}
            className="btn-primary flex items-center gap-2 px-4 py-2.5 rounded-xl"
          >
            <Plus size={15} />
            New Event
          </button>
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
          <button onClick={() => setError('')} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Calendar Grid ── */}
        <div className="lg:col-span-2 card">

          {/* Month nav */}
          <div className="flex items-center justify-between mb-5">
            <button
              onClick={prevMonth}
              className="w-8 h-8 rounded-lg hover:bg-base flex items-center justify-center transition-all"
            >
              <ChevronLeft size={16} className="text-muted" />
            </button>
            <h2 className="text-base font-bold text-soft">
              {currentMonth.toLocaleDateString('en-US', { month:'long', year:'numeric' })}
            </h2>
            <button
              onClick={nextMonth}
              className="w-8 h-8 rounded-lg hover:bg-base flex items-center justify-center transition-all"
            >
              <ChevronRight size={16} className="text-muted" />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 mb-2">
            {['Mo','Tu','We','Th','Fr','Sa','Su'].map(d => (
              <div key={d} className="text-center text-[10px] font-bold text-muted tracking-widest py-1">
                {d}
              </div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-1">
            {/* Empty offset cells */}
            {Array.from({ length: offset }).map((_, i) => (
              <div key={`empty-${i}`} />
            ))}

            {/* Day cells */}
            {Array.from({ length: days }, (_, i) => {
              const day     = i + 1;
              const dateStr = formatDate(
                currentMonth.getFullYear(),
                currentMonth.getMonth(),
                day
              );
              const isToday    = dateStr === today;
              const isSelected = dateStr === selectedDate;
              const items      = getDateItems(dateStr);
              const hasItems   = items.tasks.length > 0 || items.events.length > 0;

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(dateStr)}
                  className={`relative aspect-square flex flex-col items-center justify-center rounded-xl text-sm font-semibold transition-all duration-150
                    ${isSelected
                      ? 'bg-primary text-white'
                      : isToday
                      ? 'bg-primary/20 text-primary border border-primary/40'
                      : 'text-muted hover:bg-base hover:text-soft'
                    }`}
                >
                  {day}
                  {hasItems && (
                    <div className="flex gap-0.5 mt-0.5">
                      {items.events.length > 0 && (
                        <div className={`w-1 h-1 rounded-full ${isSelected ? 'bg-white' : 'bg-yellow-400'}`} />
                      )}
                      {items.tasks.length > 0 && (
                        <div className={`w-1 h-1 rounded-full ${isSelected ? 'bg-white' : 'bg-primary'}`} />
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border">
            <div className="flex items-center gap-1.5 text-[10px] text-muted">
              <div className="w-2 h-2 rounded-full bg-yellow-400" /> Events
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-muted">
              <div className="w-2 h-2 rounded-full bg-primary" /> Tasks
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-muted">
              <div className="w-2 h-2 rounded-full bg-primary/40 border border-primary" /> Today
            </div>
          </div>
        </div>

        {/* ── Selected Day Panel ── */}
        <div className="flex flex-col gap-4">

          {/* Date header */}
          <div className="card py-3">
            <div className="text-xs text-muted font-semibold tracking-widest uppercase mb-1">
              Selected Day
            </div>
            <div className="text-base font-extrabold text-soft">
              {new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', {
                weekday:'long', month:'long', day:'numeric'
              })}
            </div>
            <div className="flex items-center gap-3 mt-2 text-xs text-muted">
              <span>{selectedItems.events.length} events</span>
              <span>{selectedItems.tasks.length} tasks</span>
            </div>
          </div>

          {/* Events */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Tag size={14} className="text-yellow-400" />
                <span className="text-xs font-bold text-soft">Events</span>
              </div>
              <button
                onClick={openEventForm}
                className="w-6 h-6 rounded-lg hover:bg-base flex items-center justify-center"
              >
                <Plus size={13} className="text-muted hover:text-primary" />
              </button>
            </div>

            {selectedItems.events.length === 0 ? (
              <div className="text-center py-4 text-muted text-xs">No events this day</div>
            ) : (
              <div className="flex flex-col gap-2">
                {selectedItems.events.map(ev => {
                  const s = typeStyle[ev.event_type] || typeStyle.reminder;
                  return (
                    <div
                      key={ev.id}
                      className={`${s.bg} rounded-xl p-3 border border-border group`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1">
                            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                              style={{ background: s.dot }} />
                            <span className={`text-[10px] font-bold uppercase tracking-wide ${s.text}`}>
                              {ev.event_type}
                            </span>
                          </div>
                          <div className="text-xs font-semibold text-soft">{ev.title}</div>
                          {ev.start_time && (
                            <div className="flex items-center gap-1 text-[10px] text-muted mt-1">
                              <Clock size={9} />
                              {ev.start_time.slice(0,5)}
                              {ev.end_time && ` → ${ev.end_time.slice(0,5)}`}
                            </div>
                          )}
                          {ev.notify_by_email && (
                            <div className="flex items-center gap-1 text-[10px] text-primary mt-1">
                              <Bell size={9} /> Reminder on
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => handleDeleteEvent(ev.id)}
                          className="w-6 h-6 rounded-lg hover:bg-red-900/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                        >
                          <Trash2 size={11} className="text-muted hover:text-red-400" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Pinned Tasks */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-primary" />
                <span className="text-xs font-bold text-soft">Pinned Tasks</span>
              </div>
              <button
                onClick={openTaskForm}
                className="w-6 h-6 rounded-lg hover:bg-base flex items-center justify-center"
              >
                <Plus size={13} className="text-muted hover:text-primary" />
              </button>
            </div>

            {selectedItems.tasks.length === 0 ? (
              <div className="text-center py-4 text-muted text-xs">No tasks pinned</div>
            ) : (
              <div className="flex flex-col gap-2">
                {selectedItems.tasks.map(ct => (
                  <div
                    key={ct.id}
                    className="flex items-center gap-2 p-2.5 rounded-xl bg-base border border-border group"
                  >
                    <div className={`w-3.5 h-3.5 rounded-md border-2 flex-shrink-0
                      ${ct.task_detail?.is_completed
                        ? 'bg-primary border-primary'
                        : 'border-border'}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-soft truncate">
                        {ct.task_detail?.title || 'Task'}
                      </div>
                      {ct.notify_by_email && (
                        <div className="flex items-center gap-1 text-[9px] text-primary mt-0.5">
                          <Bell size={8} /> Email reminder
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => handleRemoveCalTask(ct.id)}
                      className="w-5 h-5 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X size={11} className="text-muted hover:text-red-400" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Event Form Modal ── */}
      {showEventForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 px-4">
          <div className="card w-full max-w-md max-h-[90vh] overflow-y-auto">

            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Calendar size={18} className="text-primary" />
                <h2 className="text-base font-bold text-soft">New Event</h2>
              </div>
              <button
                onClick={() => setShowEventForm(false)}
                className="w-7 h-7 rounded-lg hover:bg-base flex items-center justify-center"
              >
                <X size={16} className="text-muted" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Event Title
                </label>
                <input
                  className="input"
                  placeholder="What's the event?"
                  value={eventForm.title}
                  onChange={e => setEventForm({ ...eventForm, title: e.target.value })}
                  autoFocus
                />
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {['meeting','focus','deadline','reminder','personal'].map(t => {
                    const s = typeStyle[t];
                    return (
                      <button
                        key={t}
                        onClick={() => setEventForm({ ...eventForm, event_type: t })}
                        className={`py-2 rounded-xl text-xs font-semibold capitalize transition-all border
                          ${eventForm.event_type === t
                            ? `${s.bg} ${s.text} border-current`
                            : 'bg-base border-border text-muted hover:border-muted'
                          }`}
                      >
                        {t}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Description
                </label>
                <textarea
                  className="input resize-none"
                  rows={2}
                  placeholder="Optional description..."
                  value={eventForm.description}
                  onChange={e => setEventForm({ ...eventForm, description: e.target.value })}
                />
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Date
                </label>
                <input
                  className="input"
                  type="date"
                  value={eventForm.date}
                  onChange={e => setEventForm({ ...eventForm, date: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                    Start Time
                  </label>
                  <input
                    className="input"
                    type="time"
                    value={eventForm.start_time}
                    onChange={e => setEventForm({ ...eventForm, start_time: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                    End Time
                  </label>
                  <input
                    className="input"
                    type="time"
                    value={eventForm.end_time}
                    onChange={e => setEventForm({ ...eventForm, end_time: e.target.value })}
                  />
                </div>
              </div>

              {/* Email notification toggle */}
              <div
                onClick={() => setEventForm({ ...eventForm, notify_by_email: !eventForm.notify_by_email })}
                className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all
                  ${eventForm.notify_by_email
                    ? 'bg-primary/10 border-primary/40'
                    : 'bg-base border-border'
                  }`}
              >
                {eventForm.notify_by_email
                  ? <Bell size={16} className="text-primary flex-shrink-0" />
                  : <BellOff size={16} className="text-muted flex-shrink-0" />
                }
                <div className="flex-1">
                  <div className="text-sm font-semibold text-soft">Email Reminder</div>
                  <div className="text-xs text-muted mt-0.5">
                    {eventForm.notify_by_email
                      ? 'You will receive an email on the event day'
                      : 'No email reminder will be sent'
                    }
                  </div>
                </div>
                <div className={`w-10 h-5 rounded-full transition-all flex items-center px-0.5
                  ${eventForm.notify_by_email ? 'bg-primary' : 'bg-border'}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-all
                    ${eventForm.notify_by_email ? 'translate-x-5' : 'translate-x-0'}`}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowEventForm(false)}
                className="btn-ghost flex-1 py-2.5 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateEvent}
                disabled={saving || !eventForm.title.trim() || !eventForm.date}
                className="btn-primary flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {saving
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Check size={15} />
                }
                Create Event
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Pin Task Modal ── */}
      {showTaskForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 px-4">
          <div className="card w-full max-w-md">

            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Clock size={18} className="text-primary" />
                <h2 className="text-base font-bold text-soft">Pin Task to Calendar</h2>
              </div>
              <button
                onClick={() => setShowTaskForm(false)}
                className="w-7 h-7 rounded-lg hover:bg-base flex items-center justify-center"
              >
                <X size={16} className="text-muted" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Select Task
                </label>
                <select
                  className="input"
                  value={taskForm.task_id}
                  onChange={e => setTaskForm({ ...taskForm, task_id: e.target.value })}
                >
                  <option value="">Choose a task...</option>
                  {allTasks.filter(t => !t.is_completed).map(t => (
                    <option key={t.id} value={t.id}>{t.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Pin to Date
                </label>
                <input
                  className="input"
                  type="date"
                  value={taskForm.date}
                  onChange={e => setTaskForm({ ...taskForm, date: e.target.value })}
                />
              </div>

              {/* Email toggle */}
              <div
                onClick={() => setTaskForm({ ...taskForm, notify_by_email: !taskForm.notify_by_email })}
                className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all
                  ${taskForm.notify_by_email
                    ? 'bg-primary/10 border-primary/40'
                    : 'bg-base border-border'
                  }`}
              >
                {taskForm.notify_by_email
                  ? <Bell size={16} className="text-primary flex-shrink-0" />
                  : <BellOff size={16} className="text-muted flex-shrink-0" />
                }
                <div className="flex-1">
                  <div className="text-sm font-semibold text-soft">Email Reminder</div>
                  <div className="text-xs text-muted mt-0.5">
                    {taskForm.notify_by_email
                      ? 'Get an email reminder on this day'
                      : 'No reminder will be sent'
                    }
                  </div>
                </div>
                <div className={`w-10 h-5 rounded-full transition-all flex items-center px-0.5
                  ${taskForm.notify_by_email ? 'bg-primary' : 'bg-border'}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-all
                    ${taskForm.notify_by_email ? 'translate-x-5' : 'translate-x-0'}`}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowTaskForm(false)}
                className="btn-ghost flex-1 py-2.5 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCalTask}
                disabled={saving || !taskForm.task_id || !taskForm.date}
                className="btn-primary flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {saving
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Check size={15} />
                }
                Pin Task
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}