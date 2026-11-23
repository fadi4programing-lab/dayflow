import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/';

const API = axios.create({
    baseURL: API_BASE_URL,
});

// A bare client is used for token refresh so a failed refresh cannot loop
// back through the response interceptor.
const rawAPI = axios.create({
    baseURL: API_BASE_URL,
});

let refreshPromise = null;

export const clearStoredAuth = () => {
    ['access', 'refresh', 'token', 'user'].forEach((key) => {
        localStorage.removeItem(key);
    });
};

const storeTokens = (access, refresh) => {
    if (access) {
        localStorage.setItem('access', access);
        // Keep the legacy key populated so existing auth guards keep working.
        localStorage.setItem('token', access);
    }
    if (refresh) {
        localStorage.setItem('refresh', refresh);
    }
};

const redirectToLogin = () => {
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login');
    }
};

const getAuthHeader = () => {
    const access = localStorage.getItem('access');
    if (access) return `Bearer ${access}`;

    const legacyToken = localStorage.getItem('token');
    if (!legacyToken) return null;

    // Existing sessions may hold an opaque DRF token while newer sessions
    // hold a JWT access token under the legacy key.
    return legacyToken.split('.').length === 3
        ? `Bearer ${legacyToken}`
        : `Token ${legacyToken}`;
};

// Attach the current access token to every request automatically.
API.interceptors.request.use((config) => {
    const authorization = getAuthHeader();
    if (authorization) {
        config.headers = config.headers || {};
        config.headers.Authorization = authorization;
    }
    return config;
});

// Refresh an expired JWT once, sharing the refresh request across concurrent
// failures, then replay the original request. Redirect only when refresh fails.
API.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config;
        const status = error.response?.status;
        const url = typeof original?.url === 'string' ? original.url : '';
        const isAuthRequest =
            url.includes('token/') ||
            url.includes('login/') ||
            url.includes('register/');

        if (status !== 401 || !original || original._retry || isAuthRequest) {
            return Promise.reject(error);
        }

        const refreshToken = localStorage.getItem('refresh');
        if (!refreshToken) {
            clearStoredAuth();
            redirectToLogin();
            return Promise.reject(error);
        }

        original._retry = true;

        try {
            if (!refreshPromise) {
                refreshPromise = rawAPI
                    .post('token/refresh/', { refresh: refreshToken })
                    .then(({ data }) => {
                        if (!data.access) {
                            throw new Error('Refresh response did not include an access token.');
                        }
                        storeTokens(data.access, data.refresh);
                        return data.access;
                    })
                    .finally(() => {
                        refreshPromise = null;
                    });
            }

            const access = await refreshPromise;
            original.headers = original.headers || {};
            original.headers.Authorization = `Bearer ${access}`;
            return API(original);
        } catch (refreshError) {
            clearStoredAuth();
            redirectToLogin();
            return Promise.reject(refreshError);
        }
    }
);

// ── AUTH ──────────────────────────────────────
export const register = (data) => rawAPI.post('register/', data);

export const login = async (data) => {
    const tokenResponse = await rawAPI.post('token/', data);
    const { access, refresh } = tokenResponse.data;
    storeTokens(access, refresh);

    try {
        const profileResponse = await rawAPI.get('profile/', {
            headers: { Authorization: `Bearer ${access}` },
        });
        return {
            data: {
                token: access,
                access,
                refresh,
                user_id: profileResponse.data.id,
                username: profileResponse.data.username,
                email: profileResponse.data.email,
                profile: profileResponse.data,
            },
        };
    } catch (error) {
        clearStoredAuth();
        throw error;
    }
};

export const getProfile = () => API.get('profile/');

// ── ANALYTICS ─────────────────────────────────
export const analyticsAPI = {
    getOverview: () => API.get('analytics/overview/'),
    getGoalsForecast: () => API.get('analytics/goals-forecast/'),
    recalculate: () => API.post('analytics/recalculate/'),
};

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
