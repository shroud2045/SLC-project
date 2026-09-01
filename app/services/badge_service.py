from typing import List, Dict
from app.extensions import db
from app.models.badge import Badge, UserBadge, BadgeCategory, BadgeRequirement, BadgeRarity
from app.models.post import LockInPost
from app.models.timer import TimerSession
from app.models.challenge import UserChallenge
from app.services.streak_service import StreakService


class BadgeService:
    """Service managing achievement badge catalog and deterministic unlocking evaluation."""

    DEFAULT_BADGES = [
        # Streak Badges
        {
            'slug': 'streak_1',
            'name': 'First Lock-In',
            'description': 'Completed your very first daily lock-in session.',
            'icon': '🔥',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 1.0,
            'rarity': BadgeRarity.COMMON
        },
        {
            'slug': 'streak_3',
            'name': '3 Day Warrior',
            'description': 'Maintained a locked-in streak for 3 consecutive days.',
            'icon': '⚔️',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 3.0,
            'rarity': BadgeRarity.COMMON
        },
        {
            'slug': 'streak_7',
            'name': '7 Day Streak',
            'description': '1 full week of relentless daily discipline.',
            'icon': '🛡️',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 7.0,
            'rarity': BadgeRarity.UNCOMMON
        },
        {
            'slug': 'streak_14',
            'name': '14 Day Disciple',
            'description': 'Two weeks unbroken consistency in the crib.',
            'icon': '⚡',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 14.0,
            'rarity': BadgeRarity.UNCOMMON
        },
        {
            'slug': 'streak_30',
            'name': '30 Day Grinder',
            'description': 'A full month of non-stop daily progress.',
            'icon': '💎',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 30.0,
            'rarity': BadgeRarity.RARE
        },
        {
            'slug': 'streak_50',
            'name': '50 Day Committer',
            'description': '50 consecutive days locked in.',
            'icon': '🎯',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 50.0,
            'rarity': BadgeRarity.RARE
        },
        {
            'slug': 'streak_75',
            'name': '75 Day Machine',
            'description': '75 days of iron discipline.',
            'icon': '⚙️',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 75.0,
            'rarity': BadgeRarity.EPIC
        },
        {
            'slug': 'streak_100',
            'name': '100 Day Monster',
            'description': 'Century club. 100 days of pure focus.',
            'icon': '👹',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 100.0,
            'rarity': BadgeRarity.EPIC
        },
        {
            'slug': 'streak_150',
            'name': '150 Day Titan',
            'description': '150 days of unshakeable work ethic.',
            'icon': '🏛️',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 150.0,
            'rarity': BadgeRarity.LEGENDARY
        },
        {
            'slug': 'streak_200',
            'name': '200 Day Master',
            'description': '200 days unbroken daily mastery.',
            'icon': '👑',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 200.0,
            'rarity': BadgeRarity.LEGENDARY
        },
        {
            'slug': 'streak_250',
            'name': '250 Day Unstoppable',
            'description': 'Quarter-thousand days of sheer dominance.',
            'icon': '🚀',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 250.0,
            'rarity': BadgeRarity.LEGENDARY
        },
        {
            'slug': 'streak_300',
            'name': '300 Day Savage',
            'description': 'Spartan level discipline for 300 days.',
            'icon': '🩸',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 300.0,
            'rarity': BadgeRarity.LEGENDARY
        },
        {
            'slug': 'streak_350',
            'name': '350 Day Apex',
            'description': 'Nearing a full year of pure lock-in.',
            'icon': '🦅',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 350.0,
            'rarity': BadgeRarity.MYTHIC
        },
        {
            'slug': 'streak_400',
            'name': '400 Day Immortal',
            'description': 'Over 400 days of relentless grinding.',
            'icon': '🌌',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 400.0,
            'rarity': BadgeRarity.MYTHIC
        },
        {
            'slug': 'streak_450',
            'name': '450 Day Overlord',
            'description': '450 days of supreme consistency.',
            'icon': '⚡',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 450.0,
            'rarity': BadgeRarity.MYTHIC
        },
        {
            'slug': 'streak_500',
            'name': '500 Day Legend',
            'description': 'Half a thousand days locked in. Legendary status attained.',
            'icon': '🌟',
            'category': BadgeCategory.STREAK,
            'requirement_type': BadgeRequirement.STREAK_DAYS,
            'threshold': 500.0,
            'rarity': BadgeRarity.MYTHIC
        },

        # Total Hours Badges
        {
            'slug': 'hours_10',
            'name': '10 Hours Locked',
            'description': 'Accumulated 10 total hours of deep focused work.',
            'icon': '⏱️',
            'category': BadgeCategory.HOURS,
            'requirement_type': BadgeRequirement.TOTAL_HOURS,
            'threshold': 10.0,
            'rarity': BadgeRarity.COMMON
        },
        {
            'slug': 'hours_50',
            'name': '50 Hours Locked',
            'description': 'Logged 50 solid hours of productive work.',
            'icon': '🔋',
            'category': BadgeCategory.HOURS,
            'requirement_type': BadgeRequirement.TOTAL_HOURS,
            'threshold': 50.0,
            'rarity': BadgeRarity.UNCOMMON
        },
        {
            'slug': 'hours_100',
            'name': '100 Hours Locked',
            'description': 'Triple digits. 100 hours of grind recorded.',
            'icon': '💯',
            'category': BadgeCategory.HOURS,
            'requirement_type': BadgeRequirement.TOTAL_HOURS,
            'threshold': 100.0,
            'rarity': BadgeRarity.RARE
        },
        {
            'slug': 'hours_500',
            'name': '500 Hours Locked',
            'description': 'Half a thousand hours dedicated to self-mastery.',
            'icon': '🏆',
            'category': BadgeCategory.HOURS,
            'requirement_type': BadgeRequirement.TOTAL_HOURS,
            'threshold': 500.0,
            'rarity': BadgeRarity.EPIC
        },
        {
            'slug': 'hours_1000',
            'name': '1000 Hours Locked',
            'description': '1,000 hours in the deep work arena.',
            'icon': '🔱',
            'category': BadgeCategory.HOURS,
            'requirement_type': BadgeRequirement.TOTAL_HOURS,
            'threshold': 1000.0,
            'rarity': BadgeRarity.MYTHIC
        },

        # Activity Badges
        {
            'slug': 'first_timer',
            'name': 'Clock In',
            'description': 'Completed your first validated timer session.',
            'icon': '⏲️',
            'category': BadgeCategory.ACTIVITY,
            'requirement_type': BadgeRequirement.TIMER_COUNT,
            'threshold': 1.0,
            'rarity': BadgeRarity.COMMON
        },
        {
            'slug': 'first_community_post',
            'name': 'Voice of the Crib',
            'description': 'Shared your first lock-in log with the community.',
            'icon': '📢',
            'category': BadgeCategory.ACTIVITY,
            'requirement_type': BadgeRequirement.POST_COUNT,
            'threshold': 1.0,
            'rarity': BadgeRarity.COMMON
        },
    ]

    @classmethod
    def seed_badges(cls) -> int:
        """Seeds default badges in database if they do not exist."""
        created_count = 0
        for badge_data in cls.DEFAULT_BADGES:
            existing = Badge.query.filter_by(slug=badge_data['slug']).first()
            if not existing:
                b = Badge(**badge_data)
                db.session.add(b)
                created_count += 1
        if created_count > 0:
            db.session.commit()
        return created_count

    @classmethod
    def evaluate_user_badges(cls, user_id: int) -> List[Badge]:
        """
        Evaluates a user's deterministic stats and grants any earned badges.
        Returns list of newly earned Badge objects.
        """
        streak_stats = StreakService.calculate_streaks(user_id)
        longest_streak = streak_stats['longest_streak']
        current_streak = streak_stats['current_streak']
        best_streak = max(longest_streak, current_streak)
        total_hours = streak_stats['total_hours']

        post_count = LockInPost.query.filter_by(user_id=user_id).count()
        timer_count = TimerSession.query.filter_by(user_id=user_id).count()
        challenge_count = UserChallenge.query.filter_by(user_id=user_id, is_completed=True).count()

        # Map metrics
        metrics = {
            BadgeRequirement.STREAK_DAYS: best_streak,
            BadgeRequirement.TOTAL_HOURS: total_hours,
            BadgeRequirement.POST_COUNT: post_count,
            BadgeRequirement.TIMER_COUNT: timer_count,
            BadgeRequirement.CHALLENGE_COUNT: challenge_count,
        }

        # Get already earned badge IDs
        earned_badge_ids = {
            ub.badge_id for ub in UserBadge.query.filter_by(user_id=user_id).all()
        }

        all_badges = Badge.query.all()
        newly_earned = []

        for badge in all_badges:
            if badge.id in earned_badge_ids:
                continue

            current_metric_val = metrics.get(badge.requirement_type, 0)
            if current_metric_val >= badge.threshold:
                # Award badge
                ub = UserBadge(user_id=user_id, badge_id=badge.id)
                db.session.add(ub)
                newly_earned.append(badge)

        if newly_earned:
            db.session.commit()

        return newly_earned
