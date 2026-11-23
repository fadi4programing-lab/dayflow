"""Create an idempotent, recruiter-ready demo environment for Dayflow."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.analytics.predictor import predict_user
from api.analytics.snapshots import recalculate_user_snapshots
from api.models import (
    CalendarTask,
    DailyPerformanceSnapshot,
    Event,
    Goal,
    Note,
    Task,
    TimeBlock,
)

DEMO_USERNAME = 'demo'
DEMO_EMAIL = 'demo@dayflow.app'
DEMO_PASSWORD = 'DemoUser@2026'

GOAL_SPECS = [
    {
        'title': 'Ship Dayflow AI v2.0',
        'description': (
            'Deliver the hybrid analytics engine, demo environment, and '
            'recruiter-ready product experience.'
        ),
        'progress': 72,
        'target_days': 20,
    },
    {
        'title': 'Master Applied ML & System Design',
        'description': (
            'Build practical depth in feature engineering, model evaluation, '
            'and scalable system design.'
        ),
        'progress': 55,
        'target_days': 45,
    },
    {
        'title': 'Consistent Morning Deep Work',
        'description': (
            'Protect a repeatable morning focus block and sustain a daily '
            'execution streak.'
        ),
        'progress': 84,
        'target_days': 10,
    },
    {
        'title': 'Technical Portfolio Overhaul',
        'description': (
            'Turn Dayflow and the ML work into a concise, evidence-backed '
            'engineering portfolio.'
        ),
        'progress': 38,
        'target_days': 60,
    },
]

PAST_TITLES = [
    'Implement JWT refresh flow',
    'Review PostgreSQL query plan',
    'Train burnout classifier v1',
    'Write analytics API contract tests',
    'Refactor snapshot signal handler',
    'Build goal forecast serializer',
    'Design 14-day consistency features',
    'Profile dashboard render performance',
    'Fix postponed task scoring edge case',
    'Write README architecture section',
    'Add OpenAPI response schemas',
    'Review ML feature importances',
    'Plan portfolio case study',
    'Practice system design: rate limiter',
    'Morning deep work: distributed systems',
    'Clean up demo environment scripts',
    'Tune random forest class weights',
    'Validate KMeans cluster labels',
    'Test JWT expiry and refresh',
    'Prepare v2.0 release checklist',
]

EXTRA_PAST_TASKS = [
    ('Document hybrid routing decisions', 18, False),
    ('Add API data isolation tests', 13, True),
    ('Review accessibility on dashboard', 9, True),
    ('Tune exponential decay lambda', 4, True),
    ('Refine goal progress recalculation', 1, True),
]

TODAY_TASKS = [
    {
        'title': 'Ship analytics overview endpoint',
        'priority': 'high',
        'goal': 'Ship Dayflow AI v2.0',
        'minutes': 90,
        'estimated': 90,
        'completed': True,
        'completed_minutes_ago': 45,
        'postponed': 0,
    },
    {
        'title': 'Review burnout classifier metrics',
        'priority': 'high',
        'goal': 'Master Applied ML & System Design',
        'minutes': 60,
        'estimated': 60,
        'completed': True,
        'completed_minutes_ago': 150,
        'postponed': 0,
    },
    {
        'title': 'Write smoke tests for demo data',
        'priority': 'medium',
        'goal': 'Ship Dayflow AI v2.0',
        'minutes': 45,
        'estimated': 45,
        'completed': True,
        'completed_minutes_ago': 30,
        'postponed': 1,
    },
    {
        'title': 'Refactor goal forecast serializers',
        'priority': 'medium',
        'goal': 'Ship Dayflow AI v2.0',
        'minutes': 60,
        'estimated': 60,
        'completed': False,
        'postponed': 0,
    },
    {
        'title': 'Prepare portfolio case study',
        'priority': 'low',
        'goal': 'Technical Portfolio Overhaul',
        'minutes': 45,
        'estimated': 45,
        'completed': False,
        'postponed': 2,
    },
    {
        'title': 'Evening consistency check-in',
        'priority': 'low',
        'goal': 'Consistent Morning Deep Work',
        'minutes': 20,
        'estimated': 20,
        'completed': False,
        'postponed': 0,
    },
]

FUTURE_TASKS = [
    ('Integration test JWT refresh flow', 1, 'high', 60, 'Ship Dayflow AI v2.0'),
    ('Draft ML system design doc', 2, 'high', 90, 'Master Applied ML & System Design'),
    ('Update demo walkthrough', 2, 'medium', 45, 'Technical Portfolio Overhaul'),
    ('Portfolio deployment rehearsal', 3, 'medium', 60, 'Technical Portfolio Overhaul'),
    ('Retrain consistency model', 4, 'high', 75, 'Master Applied ML & System Design'),
    ('Weekly review and retro', 4, 'low', 30, 'Consistent Morning Deep Work'),
    ('Ship v2.0 release notes', 5, 'medium', 45, 'Ship Dayflow AI v2.0'),
]

DEFAULT_PRIORITIES = ['high', 'medium', 'high', 'low', 'medium', 'high', 'low', 'medium']
DEFAULT_ESTIMATES = [45, 60, 90, 30, 75]
LATE_COMPLETION_INDICES = {4, 10, 16}
INCOMPLETE_INDICES = {2, 7, 13}


class Command(BaseCommand):
    help = (
        'Seed or reset a realistic 21-day demo account with AI analytics history.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo-user data before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        demo = User.objects.filter(username=DEMO_USERNAME).first()

        if options['reset'] and demo is not None:
            self._clear_demo_data(demo)
            self.stdout.write('Cleared existing demo-user data.')

        if demo is None:
            demo = User(username=DEMO_USERNAME)
            self.stdout.write('Creating demo user.')

        demo.email = DEMO_EMAIL
        demo.first_name = 'Demo'
        demo.last_name = 'User'
        demo.is_active = True
        demo.set_password(DEMO_PASSWORD)
        demo.save()

        goals = self._seed_goals(demo, today)
        tasks = self._seed_tasks(demo, goals, today)
        self._seed_time_blocks(demo, tasks, today)
        self._seed_events(demo, today)
        self._seed_calendar_tasks(demo, tasks, today)
        self._seed_notes(demo)

        # Task saves intentionally recalculate goal progress. Override the
        # results afterwards so the portfolio demo shows varied goal states.
        for spec in GOAL_SPECS:
            goal = goals[spec['title']]
            Goal.objects.filter(pk=goal.pk).update(
                progress=spec['progress'],
                is_completed=False,
            )

        recalc = recalculate_user_snapshots(
            demo,
            days=None,
            end_date=today,
        )
        prediction = predict_user(demo, today)

        tasks_qs = Task.objects.filter(user=demo)
        snapshot_count = DailyPerformanceSnapshot.objects.filter(user=demo).count()
        self.stdout.write(self.style.SUCCESS('Dayflow demo environment ready.'))
        self.stdout.write(
            f'  Verify: {DEMO_USERNAME} / {DEMO_PASSWORD} '
            f'({DEMO_EMAIL})'
        )
        self.stdout.write(
            f'  Data: {Goal.objects.filter(user=demo).count()} goals, '
            f'{tasks_qs.count()} tasks, '
            f'{tasks_qs.filter(is_completed=True).count()} completed, '
            f'{tasks_qs.filter(deadline=today).count()} scheduled today'
        )
        self.stdout.write(
            f'  Planning: {TimeBlock.objects.filter(user=demo).count()} time blocks, '
            f'{Event.objects.filter(user=demo).count()} events, '
            f'{CalendarTask.objects.filter(user=demo).count()} calendar pins, '
            f'{Note.objects.filter(user=demo).count()} notes'
        )
        self.stdout.write(
            f'  Analytics: {snapshot_count} snapshots '
            f'({recalc["created"]} created, {recalc["updated"]} updated), '
            f'mode={prediction["mode"]}, '
            f'history={prediction["history_days"]} days'
        )
        self.stdout.write(
            f'  AI output: consistency='
            f'{prediction["heuristic"]["rolling_consistency_score"]:.1f}, '
            f'streak={prediction["heuristic"]["streak_days"]}, '
            f'burnout={prediction["prediction"]["burnout_risk"]}, '
            f'archetype={prediction["prediction"]["cluster_label"]}'
        )
        self.stdout.write(
            f'  Next: log in at http://localhost:5173/login with '
            f'{DEMO_USERNAME} / {DEMO_PASSWORD}'
        )

    def _clear_demo_data(self, demo):
        CalendarTask.objects.filter(user=demo).delete()
        TimeBlock.objects.filter(user=demo).delete()
        Task.objects.filter(user=demo).delete()
        Goal.objects.filter(user=demo).delete()
        Event.objects.filter(user=demo).delete()
        Note.objects.filter(user=demo).delete()
        DailyPerformanceSnapshot.objects.filter(user=demo).delete()

    def _aware(self, day, hour, minute=0):
        value = datetime.combine(day, time(hour, minute))
        return timezone.make_aware(value) if settings.USE_TZ else value

    def _recent_completion(self, today, minutes_ago):
        value = timezone.now() - timedelta(minutes=minutes_ago)
        value_date = timezone.localtime(value).date() if settings.USE_TZ else value.date()
        if value_date != today:
            value = self._aware(today, 0, 5)
        return value

    def _seed_goals(self, demo, today):
        goals = {}
        for spec in GOAL_SPECS:
            goal, _ = Goal.objects.update_or_create(
                user=demo,
                title=spec['title'],
                defaults={
                    'description': spec['description'],
                    'target_date': today + timedelta(days=spec['target_days']),
                    'is_completed': False,
                },
            )
            goals[spec['title']] = goal
        return goals

    def _upsert_task(
        self,
        demo,
        *,
        title,
        deadline,
        priority,
        estimated_minutes,
        goal,
        is_completed,
        completed_at,
        postponed_count,
    ):
        task, _ = Task.objects.update_or_create(
            user=demo,
            title=title,
            deadline=deadline,
            defaults={
                'priority': priority,
                'estimated_minutes': estimated_minutes,
                'goal': goal,
                'is_completed': is_completed,
                'completed_at': completed_at,
                'postponed_count': postponed_count,
            },
        )
        return task

    def _seed_tasks(self, demo, goals, today):
        goal_titles = [spec['title'] for spec in GOAL_SPECS]
        tasks = {}

        # Twenty days of varied historical execution.
        for index, title in enumerate(PAST_TITLES):
            day = today - timedelta(days=20 - index)
            is_completed = index not in INCOMPLETE_INDICES
            completed_at = None
            if is_completed:
                completion_day = (
                    day + timedelta(days=1)
                    if index in LATE_COMPLETION_INDICES
                    else day
                )
                completed_at = self._aware(
                    completion_day,
                    9 + (index % 8),
                    15,
                )

            goal = None
            if index % 5 != 4:
                goal = goals[goal_titles[index % len(goal_titles)]]

            tasks[title] = self._upsert_task(
                demo,
                title=title,
                deadline=day,
                priority=DEFAULT_PRIORITIES[index % len(DEFAULT_PRIORITIES)],
                estimated_minutes=DEFAULT_ESTIMATES[index % len(DEFAULT_ESTIMATES)],
                goal=goal,
                is_completed=is_completed,
                completed_at=completed_at,
                postponed_count=1 if index % 6 == 0 else (2 if index % 11 == 0 else 0),
            )

        for index, (title, days_ago, is_completed) in enumerate(EXTRA_PAST_TASKS):
            day = today - timedelta(days=days_ago)
            tasks[title] = self._upsert_task(
                demo,
                title=title,
                deadline=day,
                priority=DEFAULT_PRIORITIES[(index + 3) % len(DEFAULT_PRIORITIES)],
                estimated_minutes=DEFAULT_ESTIMATES[(index + 2) % len(DEFAULT_ESTIMATES)],
                goal=goals[goal_titles[(index + 1) % len(goal_titles)]],
                is_completed=is_completed,
                completed_at=(
                    self._aware(day, 16, 45) if is_completed else None
                ),
                postponed_count=2 if not is_completed else 0,
            )

        # A busy, partly complete today.
        for spec in TODAY_TASKS:
            completed_at = (
                self._recent_completion(today, spec['completed_minutes_ago'])
                if spec['completed']
                else None
            )
            tasks[spec['title']] = self._upsert_task(
                demo,
                title=spec['title'],
                deadline=today,
                priority=spec['priority'],
                estimated_minutes=spec['estimated'],
                goal=goals[spec['goal']],
                is_completed=spec['completed'],
                completed_at=completed_at,
                postponed_count=spec['postponed'],
            )

        # The next five days are planned but intentionally unfinished.
        for title, days_ahead, priority, minutes, goal_title in FUTURE_TASKS:
            day = today + timedelta(days=days_ahead)
            tasks[title] = self._upsert_task(
                demo,
                title=title,
                deadline=day,
                priority=priority,
                estimated_minutes=minutes,
                goal=goals[goal_title],
                is_completed=False,
                completed_at=None,
                postponed_count=0,
            )

        return tasks

    def _seed_time_blocks(self, demo, tasks, today):
        monday = today - timedelta(days=today.weekday())
        block_specs = [
            ('Deep Work', time(9, 0), time(10, 30), '#7C6AF7'),
            ('AI Model Training', time(11, 0), time(12, 15), '#4FC3F7'),
            ('Code Review', time(14, 0), time(15, 0), '#6EE7B7'),
            ('Workout', time(17, 30), time(18, 30), '#F6AD55'),
        ]
        today_links = {
            'Deep Work': tasks.get('Ship analytics overview endpoint'),
            'AI Model Training': tasks.get('Review burnout classifier metrics'),
            'Code Review': tasks.get('Refactor goal forecast serializers'),
            'Workout': tasks.get('Evening consistency check-in'),
        }

        for day_index in range(7):
            day = monday + timedelta(days=day_index)
            if day < today:
                executed = True
            elif day == today:
                executed = None
            else:
                executed = False

            for spec_index, (title, start, end, color) in enumerate(block_specs):
                is_executed = (
                    executed
                    if executed is not None
                    else spec_index < 2
                )
                TimeBlock.objects.update_or_create(
                    user=demo,
                    title=title,
                    date=day,
                    start_time=start,
                    defaults={
                        'end_time': end,
                        'color': color,
                        'is_executed': is_executed,
                        'task': today_links.get(title) if day == today else None,
                    },
                )

    def _seed_events(self, demo, today):
        events = [
            (
                'AI v2.0 demo review',
                today,
                'meeting',
                time(15, 0),
                time(15, 45),
                'Walk through the hybrid analytics engine, live demo account, '
                'and goal forecasting.',
            ),
            (
                'Model evaluation deep work',
                today,
                'focus',
                time(9, 30),
                time(11, 0),
                'Review consistency features and burnout risk precision.',
            ),
            (
                'Portfolio review with mentor',
                today + timedelta(days=2),
                'meeting',
                time(14, 0),
                time(14, 30),
                'Get feedback on the Dayflow case study narrative.',
            ),
            (
                'ML system design milestone',
                today + timedelta(days=3),
                'deadline',
                None,
                None,
                'Finish the batch/online feature pipeline design draft.',
            ),
            (
                'Ship analytics polish',
                today + timedelta(days=1),
                'deadline',
                None,
                None,
                'Close remaining UI and API polish items before the demo.',
            ),
            (
                'Weekly consistency retro',
                today + timedelta(days=5),
                'reminder',
                None,
                None,
                'Review streak, archetype, and next week’s workload.',
            ),
        ]

        for title, day, event_type, start, end, description in events:
            Event.objects.update_or_create(
                user=demo,
                title=title,
                date=day,
                defaults={
                    'event_type': event_type,
                    'start_time': start,
                    'end_time': end,
                    'description': description,
                    'notify_by_email': True,
                    'notification_sent': False,
                    'is_completed': False,
                },
            )

    def _seed_calendar_tasks(self, demo, tasks, today):
        pinned = [
            (
                'Refactor goal forecast serializers',
                today,
                'Primary demo task for today’s AI forecast.',
            ),
            (
                'Evening consistency check-in',
                today,
                'Close the day with a short review.',
            ),
            (
                'Integration test JWT refresh flow',
                today + timedelta(days=1),
                'Verify token refresh before the demo.',
            ),
            (
                'Draft ML system design doc',
                today + timedelta(days=2),
                'Portfolio deep-work block.',
            ),
            (
                'Retrain consistency model',
                today + timedelta(days=4),
                'Refresh model artifacts with the latest signals.',
            ),
        ]

        for title, day, note in pinned:
            task = tasks.get(title)
            if task is None:
                continue
            CalendarTask.objects.update_or_create(
                user=demo,
                task=task,
                date=day,
                defaults={
                    'note': note,
                    'notify_by_email': True,
                    'notification_sent': False,
                },
            )

    def _seed_notes(self, demo):
        notes = [
            (
                'System design: consistency scoring',
                'The daily score blends priority-weighted completion, schedule '
                'adherence, deadline adherence, and output regularity. '
                'Postponements apply a capped penalty. Rolling consistency uses '
                'exponential decay so recent execution dominates.',
            ),
            (
                'ML experiment log — burnout classifier',
                'RandomForest with balanced subsampling produced the best '
                'trade-off between recall on high-risk days and false alarms. '
                'Top signals: workload intensity, postponement rate, and a '
                'negative completion trend.',
            ),
            (
                'PostgreSQL indexing notes',
                'Task indexes cover (user, deadline) and (user, completed_at). '
                'Snapshot uniqueness is enforced on (user, date). Keep the '
                'analytics query path read-heavy and predictable.',
            ),
            (
                'Demo script for Dayflow v2.0',
                'Sign in with the demo account, open the dashboard, show the '
                '7-day consistency chart and burnout badge, then visit Goals '
                'to show ML completion probabilities. Finish with Swagger at '
                '/api/docs/.',
            ),
            (
                'Weekly review template',
                'Wins: what moved the goals forward? '
                'Friction: which tasks were postponed repeatedly? '
                'Next: one high-priority outcome and one recovery block.',
            ),
        ]

        for title, content in notes:
            Note.objects.update_or_create(
                user=demo,
                title=title,
                defaults={'content': content},
            )
