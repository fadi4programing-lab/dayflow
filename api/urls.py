from django.urls import path
from . import views

urlpatterns = [

    # ── AUTH ──────────────────────────────────────
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/',    views.login_view,              name='login'),
    path('profile/',  views.profile_view,            name='profile'),

    # ── TASKS ─────────────────────────────────────
    path('tasks/',            views.TaskListCreateView.as_view(),   name='task-list'),
    path('tasks/<int:pk>/',   views.TaskDetailView.as_view(),       name='task-detail'),

    # ── GOALS ─────────────────────────────────────
    path('goals/',            views.GoalListCreateView.as_view(),   name='goal-list'),
    path('goals/<int:pk>/',   views.GoalDetailView.as_view(),       name='goal-detail'),

    # ── TIME BLOCKS ───────────────────────────────
    path('timeblocks/',           views.TimeBlockListCreateView.as_view(),  name='timeblock-list'),
    path('timeblocks/<int:pk>/',  views.TimeBlockDetailView.as_view(),      name='timeblock-detail'),

    # ── NOTES ─────────────────────────────────────
    path('notes/',            views.NoteListCreateView.as_view(),   name='note-list'),
    path('notes/<int:pk>/',   views.NoteDetailView.as_view(),       name='note-detail'),

    # ── EVENTS ────────────────────────────────────
    path('events/',           views.EventListCreateView.as_view(),  name='event-list'),
    path('events/<int:pk>/',  views.EventDetailView.as_view(),      name='event-detail'),

    # ── CALENDAR ──────────────────────────────────
    path('calendar/',           views.CalendarTaskListCreateView.as_view(), name='calendar-list'),
    path('calendar/<int:pk>/',  views.CalendarTaskDetailView.as_view(),     name='calendar-detail'),
]