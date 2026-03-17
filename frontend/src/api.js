import axios from 'axios';

const API = axios.create({
    baseURL: 'http://127.0.0.1:8000/api/',
});

// Attach token to every request automatically
API.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Token ${token}`;
    }
    return config;
});

// ── AUTH ──────────────────────────────────────
export const register = (data) => API.post('register/', data);
export const login    = (data) => API.post('login/', data);
export const getProfile = ()   => API.get('profile/');

// ── TASKS ─────────────────────────────────────
export const getTasks    = ()         => API.get('tasks/');
export const createTask  = (data)     => API.post('tasks/', data);
export const updateTask  = (id, data) => API.put(`tasks/${id}/`, data);
export const deleteTask  = (id)       => API.delete(`tasks/${id}/`);

// ── GOALS ─────────────────────────────────────
export const getGoals    = ()         => API.get('goals/');
export const createGoal  = (data)     => API.post('goals/', data);
export const updateGoal  = (id, data) => API.put(`goals/${id}/`, data);
export const deleteGoal  = (id)       => API.delete(`goals/${id}/`);

// ── NOTES ─────────────────────────────────────
export const getNotes    = ()         => API.get('notes/');
export const createNote  = (data)     => API.post('notes/', data);
export const updateNote  = (id, data) => API.put(`notes/${id}/`, data);
export const deleteNote  = (id)       => API.delete(`notes/${id}/`);

// ── TIME BLOCKS ───────────────────────────────
export const getTimeBlocks   = ()         => API.get('timeblocks/');
export const createTimeBlock = (data)     => API.post('timeblocks/', data);
export const updateTimeBlock = (id, data) => API.put(`timeblocks/${id}/`, data);
export const deleteTimeBlock = (id)       => API.delete(`timeblocks/${id}/`);

// ── EVENTS ────────────────────────────────────
export const getEvents    = ()         => API.get('events/');
export const createEvent  = (data)     => API.post('events/', data);
export const updateEvent  = (id, data) => API.put(`events/${id}/`, data);
export const deleteEvent  = (id)       => API.delete(`events/${id}/`);

// ── CALENDAR ──────────────────────────────────
export const getCalendarTasks    = (date) => API.get(`calendar/?date=${date}`);
export const addToCalendar       = (data) => API.post('calendar/', data);
export const removeFromCalendar  = (id)   => API.delete(`calendar/${id}/`);