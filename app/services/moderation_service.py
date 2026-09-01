import re
from typing import Tuple, Optional, List
from app.extensions import db
from app.models.moderation import BannedWord, ModerationSeverity


class ModerationService:
    """Server-side content filtering, profanity/abuse blocking, and text sanitization."""

    # Default baseline filter keywords
    DEFAULT_BANNED_WORDS = [
        ('kill yourself', ModerationSeverity.BLOCK, False),
        ('kys', ModerationSeverity.BLOCK, False),
        ('die in a fire', ModerationSeverity.BLOCK, False),
        ('threat', ModerationSeverity.FLAG, False),
        ('doxx', ModerationSeverity.BLOCK, False),
        ('swat', ModerationSeverity.BLOCK, False),
        ('nigger', ModerationSeverity.BLOCK, False),
        ('faggot', ModerationSeverity.BLOCK, False),
        ('retard', ModerationSeverity.WARN, False),
        ('cunt', ModerationSeverity.BLOCK, False),
        ('whore', ModerationSeverity.WARN, False),
        ('slut', ModerationSeverity.WARN, False),
    ]

    @classmethod
    def seed_default_filters(cls) -> int:
        """Seeds default moderation words in database if missing."""
        count = 0
        for word, sev, is_rgx in cls.DEFAULT_BANNED_WORDS:
            existing = BannedWord.query.filter_by(word_or_pattern=word).first()
            if not existing:
                bw = BannedWord(word_or_pattern=word, severity=sev, is_regex=is_rgx)
                db.session.add(bw)
                count += 1
        if count > 0:
            db.session.commit()
        return count

    @classmethod
    def check_content(cls, text: str) -> Tuple[bool, str, Optional[str]]:
        """
        Checks user-submitted text against the moderation database.
        Returns:
            is_allowed: bool (False if BLOCK severity triggered)
            cleaned_text: str (with WARN words masked)
            rejection_reason: Optional[str]
        """
        if not text:
            return True, "", None

        banned_terms = BannedWord.query.all()
        cleaned_text = text
        is_blocked = False
        rejection_reason = None

        text_lower = text.lower()

        for term in banned_terms:
            pattern_str = term.word_or_pattern
            if term.is_regex:
                try:
                    match = re.search(pattern_str, cleaned_text, re.IGNORECASE)
                    if match:
                        if term.severity == ModerationSeverity.BLOCK:
                            is_blocked = True
                            rejection_reason = "Content contains prohibited abusive or harmful language."
                            break
                        elif term.severity == ModerationSeverity.WARN:
                            cleaned_text = re.sub(pattern_str, lambda m: '*' * len(m.group()), cleaned_text, flags=re.IGNORECASE)
                except re.error:
                    continue
            else:
                # Word boundary match for standard terms
                escaped_term = re.escape(pattern_str.lower())
                regex_pattern = rf"\b{escaped_term}\b"
                if re.search(regex_pattern, text_lower):
                    if term.severity == ModerationSeverity.BLOCK:
                        is_blocked = True
                        rejection_reason = "Your submission contains language that violates community guidelines."
                        break
                    elif term.severity == ModerationSeverity.WARN:
                        cleaned_text = re.sub(regex_pattern, lambda m: '*' * len(m.group()), cleaned_text, flags=re.IGNORECASE)

        if is_blocked:
            return False, cleaned_text, rejection_reason

        return True, cleaned_text, None
