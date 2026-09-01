from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.timer import TimerSession


def test_save_valid_timer_session(auth_client, regular_user, app):
    """Tests recording a valid Pomodoro timer session."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=25)
    end = now

    res = auth_client.post('/timer/save', json={
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'duration_seconds': 25 * 60,
        'mode': 'POMODORO',
        'category': 'CODING',
        'notes': 'Flask backend coding'
    })

    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['duration_formatted'] == '25m'

    with app.app_context():
        session_rec = TimerSession.query.filter_by(user_id=regular_user.id).first()
        assert session_rec is not None
        assert session_rec.duration_minutes == 25.0
        assert session_rec.category == 'CODING'


def test_timer_backend_validation_rejects_manipulation(auth_client):
    """Verifies that spoofed client-side durations and future dates are rejected."""
    now = datetime.now(timezone.utc)

    # 1. Spoofed duration: 5 hours claimed in a 10-second window
    start = now - timedelta(seconds=10)
    end = now
    res_spoof = auth_client.post('/timer/save', json={
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'duration_seconds': 5 * 3600,  # 5 hours
        'mode': 'POMODORO',
        'category': 'STUDY'
    })
    assert res_spoof.status_code == 400
    assert 'Duration exceeds' in res_spoof.get_json()['error']

    # 2. Too short (< 60s)
    res_short = auth_client.post('/timer/save', json={
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'duration_seconds': 30,
        'mode': 'POMODORO',
        'category': 'STUDY'
    })
    assert res_short.status_code == 400
    assert 'Session too short' in res_short.get_json()['error']

    # 3. Future timestamps
    future_start = now + timedelta(days=1)
    future_end = future_start + timedelta(minutes=30)
    res_future = auth_client.post('/timer/save', json={
        'start_time': future_start.isoformat(),
        'end_time': future_end.isoformat(),
        'duration_seconds': 30 * 60,
        'mode': 'POMODORO',
        'category': 'STUDY'
    })
    assert res_future.status_code == 400
    assert 'in the future' in res_future.get_json()['error']
