import { useState, useEffect } from 'react';
import { getNotes, createNote, updateNote, deleteNote } from '../api';
import {
  StickyNote, Plus, Trash2, Pencil,
  X, Check, AlertCircle, Search
} from 'lucide-react';

export default function Notes() {
  const [notes, setNotes]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editNote, setEditNote] = useState(null);
  const [search, setSearch]     = useState('');
  const [error, setError]       = useState('');
  const [saving, setSaving]     = useState(false);
  const [form, setForm]         = useState({ title:'', content:'' });

  useEffect(() => { fetchNotes(); }, []);

  const fetchNotes = async () => {
    try {
      const res = await getNotes();
      setNotes(res.data);
    } catch { setError('Failed to load notes'); }
    finally  { setLoading(false); }
  };

  const openCreate = () => {
    setEditNote(null);
    setForm({ title:'', content:'' });
    setShowForm(true);
  };

  const openEdit = (note) => {
    setEditNote(note);
    setForm({ title:note.title, content:note.content });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      if (editNote) {
        const res = await updateNote(editNote.id, form);
        setNotes(prev => prev.map(n => n.id === editNote.id ? res.data : n));
      } else {
        const res = await createNote(form);
        setNotes(prev => [res.data, ...prev]);
      }
      setShowForm(false);
    } catch { setError('Failed to save note'); }
    finally  { setSaving(false); }
  };

  const handleDelete = async (id) => {
    try {
      await deleteNote(id);
      setNotes(prev => prev.filter(n => n.id !== id));
    } catch { setError('Failed to delete note'); }
  };

  const filtered = notes.filter(n =>
    n.title.toLowerCase().includes(search.toLowerCase()) ||
    n.content.toLowerCase().includes(search.toLowerCase())
  );

  const cardAccents = [
    { border:'border-purple-700/40', top:'bg-purple-700/20' },
    { border:'border-cyan-700/40',   top:'bg-cyan-700/20'   },
    { border:'border-green-700/40',  top:'bg-green-700/20'  },
    { border:'border-yellow-700/40', top:'bg-yellow-700/20' },
    { border:'border-red-700/40',    top:'bg-red-700/20'    },
    { border:'border-pink-700/40',   top:'bg-pink-700/20'   },
  ];

  const formatDate = (str) =>
    new Date(str).toLocaleDateString('en-US', {
      month:'short', day:'numeric', year:'numeric'
    });

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col gap-5 max-w-5xl">

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <StickyNote size={22} className="text-primary" />
            Notes
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1">
            {notes.length} {notes.length === 1 ? 'note' : 'notes'} saved
          </p>
        </div>
        <button
          onClick={openCreate}
          className="btn-primary flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-xl"
        >
          <Plus size={15} />
          <span className="text-xs md:text-sm">New Note</span>
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

      {/* Search */}
      <div className="relative">
        <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
        <input
          className="input pl-10"
          placeholder="Search notes..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && (
          <button onClick={() => setSearch('')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-soft">
            <X size={14} />
          </button>
        )}
      </div>

      {/* Notes Grid */}
      {filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 gap-3">
          <div className="w-14 h-14 rounded-2xl bg-base flex items-center justify-center">
            <StickyNote size={26} className="text-border" />
          </div>
          <div className="text-soft font-semibold">
            {search ? 'No notes found' : 'No notes yet'}
          </div>
          <div className="text-muted text-sm text-center">
            {search ? 'Try a different search term' : 'Capture your thoughts and ideas'}
          </div>
          {!search && (
            <button onClick={openCreate}
              className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl mt-1">
              <Plus size={15} /> Write First Note
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((note, i) => {
            const accent = cardAccents[i % cardAccents.length];
            return (
              <div key={note.id}
                className={`bg-surface border ${accent.border} rounded-2xl overflow-hidden group
                  hover:scale-[1.01] transition-all duration-200 flex flex-col`}>
                <div className={`h-1.5 w-full ${accent.top}`} />
                <div className="p-4 flex flex-col flex-1">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="text-sm font-bold text-soft leading-snug flex-1">
                      {note.title}
                    </h3>
                    <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity flex-shrink-0">
                      <button onClick={() => openEdit(note)}
                        className="w-6 h-6 rounded-lg hover:bg-base flex items-center justify-center">
                        <Pencil size={12} className="text-muted hover:text-soft" />
                      </button>
                      <button onClick={() => handleDelete(note.id)}
                        className="w-6 h-6 rounded-lg hover:bg-red-900/40 flex items-center justify-center">
                        <Trash2 size={12} className="text-muted hover:text-red-400" />
                      </button>
                    </div>
                  </div>
                  {note.content && (
                    <p className="text-xs text-muted leading-relaxed flex-1 line-clamp-5">
                      {note.content}
                    </p>
                  )}
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
                    <span className="text-[10px] text-muted">{formatDate(note.created_at)}</span>
                    {note.updated_at !== note.created_at && (
                      <span className="text-[10px] text-muted italic">edited</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm
          flex items-end sm:items-center justify-center z-50 px-0 sm:px-4">
          <div className="card w-full sm:max-w-lg rounded-b-none sm:rounded-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <StickyNote size={18} className="text-primary" />
                <h2 className="text-base font-bold text-soft">
                  {editNote ? 'Edit Note' : 'New Note'}
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
                  Title
                </label>
                <input className="input" placeholder="Note title..."
                  value={form.title} onChange={e => setForm({ ...form, title:e.target.value })} autoFocus />
              </div>
              <div>
                <label className="text-xs text-muted font-semibold tracking-wider uppercase mb-1.5 block">
                  Content
                </label>
                <textarea className="input resize-none" rows={7} placeholder="Write your thoughts..."
                  value={form.content} onChange={e => setForm({ ...form, content:e.target.value })} />
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
                {editNote ? 'Save Changes' : 'Save Note'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}