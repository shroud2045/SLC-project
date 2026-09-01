from app.services.ai_service import AIService


def test_ai_heuristic_plan_generation(app):
    """Tests the offline heuristic productivity engine."""
    with app.app_context():
        # Scenario 1: Networking
        plan_net = AIService.generate_productivity_plan(
            "I have 3 hours tonight and need to study networking.",
            user_context={'streak': 5, 'total_hours': 15.0}
        )
        assert plan_net['total_minutes'] == 180
        assert 'Networking' in plan_net['topic']
        assert len(plan_net['schedule']) >= 3
        assert 'motivation' in plan_net

        # Scenario 2: Coding sprint
        plan_code = AIService.generate_productivity_plan(
            "I have 45 minutes for Python backend coding.",
            user_context={'streak': 1, 'total_hours': 2.0}
        )
        assert plan_code['total_minutes'] == 45
        assert len(plan_code['schedule']) >= 2


def test_ai_api_endpoint(auth_client):
    """Tests the /ai/suggest JSON endpoint."""
    res = auth_client.post('/ai/suggest', json={
        'query': 'I have 2 hours for cybersecurity CTF labs.'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'plan' in data
    assert len(data['plan']['schedule']) > 0
