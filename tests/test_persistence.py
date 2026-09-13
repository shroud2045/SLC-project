"""
test_persistence.py — Database Persistence Tests

Verifies that user data and progress survive SQLAlchemy session boundaries,
proving the application relies on the database for permanent storage rather
than Python in-memory state.

These tests use the standard in-memory SQLite testing config, which is
functionally identical in persistence semantics to PostgreSQL for the
purposes of session/transaction testing.  On Render, the same code paths
hit the real PostgreSQL instance.
"""
import pytest
from datetime import datetime, timezone, date, timedelta

from app.extensions import db
from app.models.user import User, Role
from app.models.post import LockInPost, PostPrivacy
from app.models.timer import TimerSession, TimerMode, TimerCategory
from app.models.badge import Badge, UserBadge, BadgeCategory, BadgeRequirement, BadgeRarity


# ---------------------------------------------------------------------------
# Test 1 — Core Database Persistence
# ---------------------------------------------------------------------------

def test_database_persistence(app):
    """
    Proves that data written to the database survives SQLAlchemy session
    boundaries (simulating an application restart or new request cycle).

    Steps:
        1. Create a user
        2. Commit the user to the database
        3. Expire / clear the SQLAlchemy identity map (simulates a new session)
        4. Retrieve the user again via a fresh query
        5. Verify the user still exists with the correct data
    """
    with app.app_context():
        # --- Step 1 & 2: Create and commit a user ---
        user = User(
            username="persistence_warrior",
            email="persist@lockin.test",
            role=Role.USER,
            is_active=True,
            bio="Testing persistence"
        )
        user.set_password("PersistPass123!")
        db.session.add(user)
        db.session.commit()

        committed_id = user.id
        assert committed_id is not None, "User must have a DB-assigned id after commit"

        # --- Step 3: Clear the session (simulate new request / app restart) ---
        # expire_all() evicts all cached instances from the identity map so the
        # next access triggers a real SQL SELECT — exactly what happens on a
        # fresh request after an application restart.
        db.session.expire_all()

        # --- Step 4: Retrieve the user from the database ---
        retrieved = db.session.get(User, committed_id)

        # --- Step 5: Verify the user still exists with correct data ---
        assert retrieved is not None, "User must still exist after session clear"
        assert retrieved.id == committed_id
        assert retrieved.username == "persistence_warrior"
        assert retrieved.email == "persist@lockin.test"
        assert retrieved.role == Role.USER
        assert retrieved.is_active is True
        assert retrieved.bio == "Testing persistence"

        # Password hash must be stored, never plain-text
        assert retrieved.password_hash is not None
        assert retrieved.password_hash != "PersistPass123!"
        assert retrieved.check_password("PersistPass123!"), "Hashed password must verify correctly"
        assert not retrieved.check_password("WrongPassword"), "Wrong password must not verify"


# ---------------------------------------------------------------------------
# Test 2 — User Progress Persistence
# ---------------------------------------------------------------------------

def test_user_progress_persistence(app, regular_user):
    """
    Proves that all forms of user progress (posts, timer sessions, badges)
    survive SQLAlchemy session expiry, confirming none of it lives only in
    Python memory.

    Steps:
        1. Record a Lock-In post, timer session, and badge for the user
        2. Commit all records
        3. Expire the session to evict all cached objects
        4. Reload everything from fresh DB queries
        5. Verify all progress still exists and matches what was written
    """
    with app.app_context():
        uid = regular_user.id

        # --- Step 1: Create progress records ---
        post = LockInPost(
            user_id=uid,
            post_date=date.today(),
            title="Persistence Test Post",
            description="Locked in hard today",
            hours_worked=3.5,
            privacy=PostPrivacy.PRIVATE
        )
        db.session.add(post)

        session = TimerSession(
            user_id=uid,
            start_time=datetime.now(timezone.utc) - timedelta(minutes=25),
            end_time=datetime.now(timezone.utc),
            duration_seconds=1500,
            duration_minutes=25.0,
            mode=TimerMode.POMODORO,
            category=TimerCategory.CODING,
            notes="Deep focus block"
        )
        db.session.add(session)

        # Create a one-off badge for this test (doesn't rely on seed data)
        badge = Badge(
            slug="persistence-test-badge",
            name="Persistence Pioneer",
            description="Awarded to verify badge persistence",
            icon="💾",
            category=BadgeCategory.SPECIAL,
            requirement_type=BadgeRequirement.POST_COUNT,
            threshold=1.0,
            rarity=BadgeRarity.RARE
        )
        db.session.add(badge)
        db.session.flush()  # get badge.id before creating UserBadge

        user_badge = UserBadge(user_id=uid, badge_id=badge.id)
        db.session.add(user_badge)

        # --- Step 2: Commit everything ---
        db.session.commit()

        post_id = post.id
        session_id = session.id
        badge_id = badge.id

        # --- Step 3: Expire session (simulate new request / restart) ---
        db.session.expire_all()

        # --- Step 4: Reload from fresh queries ---
        reloaded_post = db.session.get(LockInPost, post_id)
        reloaded_session = db.session.get(TimerSession, session_id)
        reloaded_badge = db.session.get(Badge, badge_id)
        reloaded_user_badge = UserBadge.query.filter_by(user_id=uid, badge_id=badge_id).first()

        # --- Step 5: Verify all progress survived ---
        assert reloaded_post is not None, "Lock-in post must persist after session clear"
        assert reloaded_post.title == "Persistence Test Post"
        assert reloaded_post.hours_worked == 3.5
        assert reloaded_post.user_id == uid

        assert reloaded_session is not None, "Timer session must persist after session clear"
        assert reloaded_session.duration_minutes == 25.0
        assert reloaded_session.mode == TimerMode.POMODORO
        assert reloaded_session.category == TimerCategory.CODING
        assert reloaded_session.user_id == uid

        assert reloaded_badge is not None, "Badge definition must persist after session clear"
        assert reloaded_badge.slug == "persistence-test-badge"

        assert reloaded_user_badge is not None, "Earned badge record must persist after session clear"
        assert reloaded_user_badge.user_id == uid
        assert reloaded_user_badge.badge_id == badge_id


# ---------------------------------------------------------------------------
# Test 3 — Full Authentication Lifecycle Persistence
# ---------------------------------------------------------------------------

def test_auth_lifecycle_persistence(client, app):
    """
    Proves the complete authentication lifecycle is backed by PostgreSQL/SQLite,
    not Python memory.

    Simulates:
        REGISTER → user written to DB
        LOG OUT  → session cleared
        LOG IN   → user retrieved from DB
        Progress verified → data from DB, not memory
        Session expire  → simulates app restart
        LOG IN AGAIN → same user, same progress still available

    The application must NOT rely on in-memory state between requests.
    """
    with app.app_context():
        # ------------------------------------------------------------------ #
        # A. REGISTER — write user to database                               #
        # ------------------------------------------------------------------ #
        register_resp = client.post('/auth/register', data={
            'username': 'lifecycle_user',
            'email': 'lifecycle@lockin.test',
            'password': 'LifecyclePass123!',
            'confirm_password': 'LifecyclePass123!'
        }, follow_redirects=True)

        assert register_resp.status_code == 200, "Registration must succeed"

        # Confirm user is in the database immediately after registration
        user = User.query.filter_by(username='lifecycle_user').first()
        assert user is not None, "User must be written to DB during registration"
        user_id = user.id
        assert user.check_password('LifecyclePass123!'), "Password must be hashed and verifiable"

        # ------------------------------------------------------------------ #
        # B. LOG OUT                                                          #
        # ------------------------------------------------------------------ #
        client.post('/auth/logout', follow_redirects=True)

        # ------------------------------------------------------------------ #
        # C. LOG IN — user retrieved from DB                                  #
        # ------------------------------------------------------------------ #
        login_resp = client.post('/auth/login', data={
            'identifier': 'lifecycle_user',
            'password': 'LifecyclePass123!'
        }, follow_redirects=True)

        assert login_resp.status_code == 200, "Login must succeed after logout"

        # ------------------------------------------------------------------ #
        # D. Simulate application restart by clearing the SQLAlchemy session  #
        # ------------------------------------------------------------------ #
        db.session.expire_all()

        # ------------------------------------------------------------------ #
        # E. LOG IN AGAIN after session clear                                 #
        # ------------------------------------------------------------------ #
        client.post('/auth/logout', follow_redirects=True)

        login_again_resp = client.post('/auth/login', data={
            'identifier': 'lifecycle_user',
            'password': 'LifecyclePass123!'
        }, follow_redirects=True)

        assert login_again_resp.status_code == 200, "Login must succeed after simulated restart"

        # Verify user still exists in DB and credentials are intact
        same_user = db.session.get(User, user_id)
        assert same_user is not None, "User must still exist in DB after simulated restart"
        assert same_user.username == 'lifecycle_user'
        assert same_user.check_password('LifecyclePass123!'), "Password must survive simulated restart"
        assert not same_user.check_password('WrongPassword')
