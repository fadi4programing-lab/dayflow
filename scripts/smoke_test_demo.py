#!/usr/bin/env python
"""End-to-end smoke test for the seeded Dayflow demo environment."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'DemoUser@2026'


def api_request(method, url, token=None, payload=None):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except HTTPError as exc:
        body = exc.read()
        parsed = json.loads(body) if body else None
        return exc.code, parsed


class SmokeReport:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, condition, label, detail=''):
        if condition:
            self.passed += 1
            print(f'[PASS] {label}' + (f' - {detail}' if detail else ''))
        else:
            self.failed += 1
            print(f'[FAIL] {label}' + (f' - {detail}' if detail else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000/api')
    parser.add_argument('--username', default=DEMO_USERNAME)
    parser.add_argument('--password', default=DEMO_PASSWORD)
    args = parser.parse_args()

    base = args.base_url.rstrip('/')
    report = SmokeReport()

    status, login = api_request(
        'POST',
        f'{base}/token/',
        payload={'username': args.username, 'password': args.password},
    )
    report.check(
        status == 200 and bool(login and login.get('access')),
        'POST /token/ demo login',
        f'HTTP {status}',
    )
    if status != 200 or not login or not login.get('access'):
        print('\nVerification aborted: demo login failed.')
        return 1
    token = login['access']

    list_endpoints = {
        'tasks': '/tasks/',
        'goals': '/goals/',
        'events': '/events/',
        'notes': '/notes/',
        'timeblocks': '/timeblocks/',
    }
    record_counts = {}
    for name, path in list_endpoints.items():
        status, data = api_request('GET', f'{base}{path}', token=token)
        count = len(data) if isinstance(data, list) else 0
        record_counts[name] = count
        report.check(
            status == 200 and count > 0,
            f'GET {path}',
            f'HTTP {status}, {count} records',
        )

    overview_status, overview = api_request(
        'GET',
        f'{base}/analytics/overview/',
        token=token,
    )
    overview_ok = (
        overview_status == 200
        and isinstance(overview, dict)
        and overview.get('mode') == 'hybrid'
        and overview.get('cold_start') is False
        and int(overview.get('history_days', 0)) >= 14
        and 0 <= float(overview.get('rolling_consistency_score', -1)) <= 100
        and 0 <= float(overview.get('daily_score', -1)) <= 100
        and len(overview.get('daily_scores_7d', [])) == 7
        and len(overview.get('daily_scores_14d', [])) == 14
        and isinstance(overview.get('recommendations'), list)
        and len(overview.get('recommendations')) > 0
    )
    report.check(
        overview_ok,
        'GET /analytics/overview/ hybrid + 7/14-day series',
        (
            f'mode={overview.get("mode")}, '
            f'history={overview.get("history_days")}, '
            f'consistency={overview.get("rolling_consistency_score")}'
        ) if overview else f'HTTP {overview_status}',
    )

    forecast_status, forecast = api_request(
        'GET',
        f'{base}/analytics/goals-forecast/',
        token=token,
    )
    goals = forecast.get('goals', []) if isinstance(forecast, dict) else []
    forecast_ok = (
        forecast_status == 200
        and len(goals) >= 4
        and all(
            0 <= float(goal.get('completion_probability', -1)) <= 100
            and goal.get('risk_status') in {'low', 'moderate', 'high'}
            for goal in goals
        )
    )
    report.check(
        forecast_ok,
        'GET /analytics/goals-forecast/ goal predictions',
        f'HTTP {forecast_status}, {len(goals)} goals',
    )

    probe_title = f'Smoke test task {uuid.uuid4().hex[:8]}'
    create_status, created = api_request(
        'POST',
        f'{base}/tasks/',
        token=token,
        payload={
            'title': probe_title,
            'priority': 'high',
            'deadline': date.today().isoformat(),
            'estimated_minutes': 25,
        },
    )
    report.check(
        create_status == 201 and isinstance(created, dict) and created.get('id'),
        'POST /tasks/ creates a task',
        f'HTTP {create_status}',
    )

    if create_status == 201 and isinstance(created, dict) and created.get('id'):
        task_id = created['id']
        delete_status, _ = api_request(
            'DELETE',
            f'{base}/tasks/{task_id}/',
            token=token,
        )
        report.check(
            delete_status == 204,
            'DELETE /tasks/{id}/ removes the task',
            f'HTTP {delete_status}',
        )

        status, tasks = api_request('GET', f'{base}/tasks/', token=token)
        remaining_ids = {task['id'] for task in tasks} if isinstance(tasks, list) else set()
        report.check(
            status == 200 and task_id not in remaining_ids,
            'Task deletion persisted',
            f'{len(remaining_ids)} tasks remain',
        )

    post_signal_status, post_signal_overview = api_request(
        'GET',
        f'{base}/analytics/overview/',
        token=token,
    )
    report.check(
        post_signal_status == 200
        and isinstance(post_signal_overview, dict)
        and post_signal_overview.get('mode') == 'hybrid',
        'Analytics still healthy after task signals',
        f'HTTP {post_signal_status}',
    )

    recalc_status, recalc = api_request(
        'POST',
        f'{base}/analytics/recalculate/',
        token=token,
    )
    report.check(
        recalc_status == 200
        and isinstance(recalc, dict)
        and isinstance(recalc.get('metrics'), dict),
        'POST /analytics/recalculate/',
        f'HTTP {recalc_status}, snapshots={recalc.get("snapshots") if recalc else "?"}',
    )

    print('\nRecord counts:', json.dumps(record_counts, indent=2))
    if isinstance(overview, dict):
        print('\nDemo analytics sample:')
        print(
            json.dumps(
                {
                    'mode': overview.get('mode'),
                    'history_days': overview.get('history_days'),
                    'daily_score': overview.get('daily_score'),
                    'rolling_consistency_score': overview.get('rolling_consistency_score'),
                    'streak_days': overview.get('streak_days'),
                    'burnout_risk': overview.get('burnout_risk'),
                    'day_archetype': overview.get('day_archetype'),
                    'dominant_factor': overview.get('dominant_factor'),
                    'goal_completion_probability': overview.get(
                        'goal_completion_probability'
                    ),
                    'recommendations': overview.get('recommendations'),
                },
                indent=2,
            )
        )
    if goals:
        print('\nGoal forecast sample:')
        print(
            json.dumps(
                [
                    {
                        'title': goal.get('title'),
                        'progress': goal.get('progress'),
                        'completion_probability': goal.get('completion_probability'),
                        'risk_status': goal.get('risk_status'),
                    }
                    for goal in goals[:5]
                ],
                indent=2,
            )
        )

    print(
        f'\nSmoke result: {report.passed} passed, {report.failed} failed.'
    )
    return 0 if report.failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
