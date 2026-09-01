from app.services.moderation_service import ModerationService
from app.models.post import PostPrivacy


def test_moderation_service_filtering(app):
    """Tests server-side content filter actions."""
    with app.app_context():
        # Clean text
        allowed, cleaned, reason = ModerationService.check_content("Studied Python algorithms for 3 hours.")
        assert allowed is True
        assert reason is None

        # Blocked text
        allowed, cleaned, reason = ModerationService.check_content("Go kill yourself right now")
        assert allowed is False
        assert reason is not None


def test_abusive_post_rejected(auth_client):
    """Tests that submitting a lock-in post with abusive language is rejected."""
    res = auth_client.post('/posts/create', data={
        'title': 'Bad title',
        'description': 'You should kys and quit.',
        'hours_worked': '1.0',
        'privacy': PostPrivacy.COMMUNITY
    }, follow_redirects=True)

    assert b'violates community guidelines' in res.data or b'prohibited abusive' in res.data
