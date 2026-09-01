from datetime import date
from app.extensions import db
from app.models.post import LockInPost, PostPrivacy
from app.models.community import Comment, PostReaction
from app.models.chat import ChatMessage
from app.models.user import User


def test_post_comment_and_reaction(auth_client, regular_user, app):
    """Tests commenting and reacting to a community post."""
    with app.app_context():
        post = LockInPost(
            user_id=regular_user.id,
            title='Public Sprint',
            description='Community grind',
            hours_worked=2.0,
            privacy=PostPrivacy.COMMUNITY
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # 1. Add comment
    res_comment = auth_client.post(f'/community/post/{post_id}/comment', data={
        'content': 'Great work! Keep pushing.'
    }, follow_redirects=True)
    assert res_comment.status_code == 200

    with app.app_context():
        c = Comment.query.filter_by(post_id=post_id).first()
        assert c is not None
        assert c.content == 'Great work! Keep pushing.'

    # 2. Toggle reaction
    res_react = auth_client.post(f'/community/post/{post_id}/react', json={
        'reaction_type': 'FIRE'
    })
    assert res_react.status_code == 200
    data = res_react.get_json()
    assert data['success'] is True
    assert data['toggled'] is True
    assert data['counts']['FIRE'] == 1


def test_chat_messaging_and_polling(auth_client, regular_user, app):
    """Tests sending and polling live chatroom messages."""
    # Send message
    res_send = auth_client.post('/chat/api/send', json={
        'content': 'Locked in for 2 hours tonight!'
    })
    assert res_send.status_code == 200
    msg_data = res_send.get_json()['message']
    assert msg_data['content'] == 'Locked in for 2 hours tonight!'
    assert msg_data['username'] == regular_user.username
    msg_id = msg_data['id']

    # Poll message
    res_poll = auth_client.get(f'/chat/api/messages?after_id={msg_id - 1}')
    assert res_poll.status_code == 200
    poll_data = res_poll.get_json()
    assert len(poll_data['messages']) >= 1
    assert poll_data['messages'][-1]['id'] == msg_id


def test_muted_user_blocked_from_chat(auth_client, regular_user, app):
    """Verifies muted user cannot send chat messages."""
    with app.app_context():
        u = db.session.get(User, regular_user.id)
        u.is_muted = True
        db.session.commit()

    res = auth_client.post('/chat/api/send', json={'content': 'Hello?'})
    assert res.status_code == 403
    assert 'muted' in res.get_json()['error']
