from django.contrib import admin

from .models import (
    Task,
    Goal,
    TimeBlock,
    Note,
    Event,
    CalendarTask,
    DailyPerformanceSnapshot,
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'user',
        'priority',
        'deadline',
        'is_completed',
        'goal',
        'estimated_minutes',
        'postponed_count',
        'completed_at',
    )
    list_filter = ('is_completed', 'priority')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'completed_at', 'postponed_count')
    list_select_related = ('user', 'goal')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'progress', 'is_completed', 'target_date', 'created_at')
    list_filter = ('is_completed',)
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'date', 'start_time', 'end_time', 'task', 'is_executed')
    list_filter = ('is_executed', 'date')
    search_fields = ('title', 'user__username')
    list_select_related = ('user', 'task')


@admin.register(DailyPerformanceSnapshot)
class DailyPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'user',
        'tasks_scheduled',
        'tasks_completed',
        'weighted_completion_rate',
        'daily_score',
        'rolling_consistency_score',
        'streak_days',
        'burnout_risk',
        'day_archetype',
    )
    list_filter = ('date', 'day_archetype')
    search_fields = ('user__username', 'day_archetype', 'dominant_factor')
    ordering = ('-date',)
    list_select_related = ('user',)


admin.site.register(Note)
admin.site.register(Event)
admin.site.register(CalendarTask)
