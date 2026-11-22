"""Response schemas for the analytics REST API."""

from rest_framework import serializers


class DailyScorePointSerializer(serializers.Serializer):
    date = serializers.DateField()
    score = serializers.FloatField()


class AnalyticsMetricsSerializer(serializers.Serializer):
    rolling_consistency_score = serializers.FloatField()
    daily_score = serializers.FloatField()
    streak_days = serializers.IntegerField()
    burnout_risk = serializers.CharField()
    day_archetype = serializers.CharField()
    dominant_factor = serializers.CharField(allow_blank=True)
    weighted_completion_rate = serializers.FloatField(required=False)
    schedule_adherence = serializers.FloatField(required=False)
    goal_completion_probability = serializers.FloatField(required=False)
    hybrid_score = serializers.FloatField(required=False)
    mode = serializers.CharField(required=False)


class AnalyticsOverviewSerializer(AnalyticsMetricsSerializer):
    as_of = serializers.DateField()
    cold_start = serializers.BooleanField()
    history_days = serializers.IntegerField()
    recommendations = serializers.ListField(child=serializers.CharField())
    daily_scores_7d = DailyScorePointSerializer(many=True)
    daily_scores_14d = DailyScorePointSerializer(many=True)


class GoalForecastSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    progress = serializers.IntegerField()
    target_date = serializers.DateField(allow_null=True)
    tasks_total = serializers.IntegerField()
    tasks_completed = serializers.IntegerField()
    completion_probability = serializers.FloatField()
    risk_status = serializers.CharField()
    dominant_factor = serializers.CharField(allow_blank=True)


class GoalsForecastResponseSerializer(serializers.Serializer):
    as_of = serializers.DateField()
    mode = serializers.CharField()
    goals = GoalForecastSerializer(many=True)


class RecalculateResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    skipped = serializers.IntegerField()
    snapshots = serializers.IntegerField()
    metrics = AnalyticsMetricsSerializer()
