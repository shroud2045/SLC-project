from datetime import datetime, timezone


def format_minutes_to_hours(minutes: float) -> str:
    """Formats float minutes to human readable string (e.g. 2h 30m or 45m)."""
    if not minutes or minutes <= 0:
        return "0m"
    total_mins = int(round(minutes))
    hours = total_mins // 60
    mins = total_mins % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    return f"{mins}m"


def format_time_ago(dt: datetime) -> str:
    """Returns humanized relative time (e.g. '5m ago', '2h ago', 'Yesterday')."""
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    elif seconds < 172800:
        return "Yesterday"
    else:
        return f"{int(seconds // 86400)}d ago"


def get_archetype_cards() -> list:
    """
    Returns motivational discipline archetype cards.
    Communicates discipline, relentless ambition, work ethic, and consistency.
    """
    return [
        {
            "name": "The Relentless Operator",
            "archetype": "Relentless Focus & Strategy",
            "quote": "In the quiet hours when others sleep, empires of skill and discipline are built.",
            "tag": "STRATEGY & DOMINANCE",
            "accent": "var(--accent-cyan)",
            "gradient": "linear-gradient(135deg, rgba(0, 229, 255, 0.15), rgba(15, 23, 42, 0.9))"
        },
        {
            "name": "The Iron Titan",
            "archetype": "Unbroken Consistency & Grit",
            "quote": "Success isn't always about greatness. It's about consistency. Consistent hard work leads to success.",
            "tag": "RELENTLESS GRIND",
            "accent": "var(--accent-emerald)",
            "gradient": "linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(15, 23, 42, 0.9))"
        },
        {
            "name": "The Cold Strategist",
            "archetype": "Mental Mastery & Composure",
            "quote": "No emotion. No excuses. Execute the plan with surgical precision.",
            "tag": "CALCULATED EXECUTION",
            "accent": "var(--accent-purple)",
            "gradient": "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(15, 23, 42, 0.9))"
        },
        {
            "name": "The Sovereign Mindset",
            "archetype": "Total Accountability & Ambition",
            "quote": "Refuse to be average. Your streak is the physical proof of your character.",
            "tag": "UNYIELDING WILL",
            "accent": "var(--accent-amber)",
            "gradient": "linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(15, 23, 42, 0.9))"
        },
        {
            "name": "The Heavyweight Champion",
            "archetype": "Ferocious Intensity & Drive",
            "quote": "Discipline is doing what you hate to do, but doing it like you love it.",
            "tag": "PURE POWER & FOCUS",
            "accent": "var(--accent-crimson)",
            "gradient": "linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(15, 23, 42, 0.9))"
        }
    ]
