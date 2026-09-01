from datetime import date
from app.extensions import db
from app.models.post import LockInPost, PostPrivacy


def test_post_creation_and_privacy_default(auth_client, regular_user, app):
    """Tests creating a post and verifying private state."""
    res = auth_client.post('/posts/create', data={
        'title': 'Networking Session',
        'description': 'Studied TCP handshake and packet structures.',
        'hours_worked': '2.5',
        'privacy': PostPrivacy.PRIVATE,
        'post_date': date.today().isoformat()
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        post = LockInPost.query.filter_by(user_id=regular_user.id).first()
        assert post is not None
        assert post.title == 'Networking Session'
        assert post.hours_worked == 2.5
        assert post.privacy == PostPrivacy.PRIVATE


def test_idor_private_post_protection(client, regular_user, other_user, app):
    """
    IDOR Security Test:
    Ensures that other_user cannot access, view, or modify regular_user's private post.
    """
    with app.app_context():
        private_post = LockInPost(
            user_id=regular_user.id,
            title='Secret Research Log',
            description='Top secret findings.',
            hours_worked=3.0,
            privacy=PostPrivacy.PRIVATE
        )
        db.session.add(private_post)
        db.session.commit()
        post_id = private_post.id

    # 1. Unauthenticated request to private post
    res_unauth = client.get(f'/posts/{post_id}')
    assert res_unauth.status_code == 403

    # 2. Authenticated as other_user
    with client.session_transaction() as sess:
        sess['user_id'] = other_user.id

    # View attempt -> 403
    res_view = client.get(f'/posts/{post_id}')
    assert res_view.status_code == 403

    # Edit attempt -> 403
    res_edit = client.post(f'/posts/{post_id}/edit', data={'title': 'Hacked', 'description': 'Hacked'}, follow_redirects=True)
    assert res_edit.status_code == 403

    # Delete attempt -> 403
    res_del = client.post(f'/posts/{post_id}/delete', follow_redirects=True)
    assert res_del.status_code == 403


def test_community_feed_isolation(client, regular_user, other_user, app):
    """Verifies that private posts never leak into the community feed."""
    with app.app_context():
        priv_post = LockInPost(
            user_id=regular_user.id,
            title='Private Journal Entry 12345',
            description='Private content.',
            hours_worked=1.0,
            privacy=PostPrivacy.PRIVATE
        )
        pub_post = LockInPost(
            user_id=other_user.id,
            title='Public Victory Log 67890',
            description='Public content.',
            hours_worked=2.0,
            privacy=PostPrivacy.COMMUNITY
        )
        db.session.add_all([priv_post, pub_post])
        db.session.commit()

    res = client.get('/community/')
    assert res.status_code == 200
    assert b'Public Victory Log 67890' in res.data
    assert b'Private Journal Entry 12345' not in res.data
