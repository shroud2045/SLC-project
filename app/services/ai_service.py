import os
import re
import json
from typing import Dict, Any, Optional
import requests
from flask import current_app


class AIService:
    """
    AI Productivity Assistant Service.
    Provides intelligent time-blocking, task decomposition, and lock-in motivation.
    Supports OpenAI, Gemini, or offline deterministic expert heuristic fallback.
    """

    @classmethod
    def generate_productivity_plan(cls, query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates a structured productivity breakdown and discipline advice.
        """
        provider = current_app.config.get('AI_PROVIDER', 'heuristic').lower()
        user_context = user_context or {}

        # 1. Try OpenAI if configured
        if provider == 'openai' and current_app.config.get('OPENAI_API_KEY'):
            try:
                return cls._query_openai(query, user_context)
            except Exception as e:
                current_app.logger.warning(f"OpenAI API failed, falling back to heuristic engine: {e}")

        # 2. Try Gemini if configured
        if provider == 'gemini' and current_app.config.get('GEMINI_API_KEY'):
            try:
                return cls._query_gemini(query, user_context)
            except Exception as e:
                current_app.logger.warning(f"Gemini API failed, falling back to heuristic engine: {e}")

        # 3. Fallback: Intelligent Heuristic Productivity Engine
        return cls._generate_heuristic_plan(query, user_context)

    @classmethod
    def _generate_heuristic_plan(cls, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligent offline heuristic parser that analyzes hours, subject, and builds a realistic schedule.
        """
        query_clean = query.strip()
        streak = user_context.get('streak', 0)
        total_hours = user_context.get('total_hours', 0.0)

        # Extract hours from query (e.g. "3 hours", "2h", "45 mins", "90 minutes")
        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours|hour|hrs|hr|h)\b', query_clean, re.IGNORECASE)
        mins_match = re.search(r'(\d+)\s*(?:minutes|minute|mins|min|m)\b', query_clean, re.IGNORECASE)

        total_available_minutes = 120  # default 2 hours

        if hours_match:
            total_available_minutes = int(float(hours_match.group(1)) * 60)
        elif mins_match:
            total_available_minutes = int(mins_match.group(1))

        # Clamp between 20 mins and 12 hours
        total_available_minutes = max(20, min(total_available_minutes, 720))

        # Detect domain
        topic = "Focused Deep Work"
        q_lower = query_clean.lower()
        if any(k in q_lower for k in ['network', 'cisco', 'wireshark', 'tcp', 'ip', 'subnet']):
            topic = "Networking & Protocols"
            blocks = [
                {"title": "Core Protocol Fundamentals & Architecture", "pct": 0.35, "desc": "Study theory, packet headers, and flow mechanics."},
                {"title": "Hands-On Packet Analysis & Terminal Labs", "pct": 0.40, "desc": "Execute terminal labs (Wireshark / Packet Tracer / Bandit)."},
                {"title": "Subnetting / Troubleshooting Drills", "pct": 0.15, "desc": "Active recall calculations and practical diagnostic drills."},
                {"title": "Review, Active Recall & Documentation", "pct": 0.10, "desc": "Summarize insights into your daily Lock-In post."}
            ]
        elif any(k in q_lower for k in ['cyber', 'security', 'hack', 'bandit', 'ctf', 'linux', 'pentest']):
            topic = "Cybersecurity & Hands-on Labs"
            blocks = [
                {"title": "Vulnerability Theory & Attack Vector Review", "pct": 0.30, "desc": "Deconstruct target mechanics and privilege escalation vectors."},
                {"title": "Live Target / Lab Exploitation (Hands-On)", "pct": 0.50, "desc": "Execute hands-on challenges (OverTheWire / HTB / TryHackMe)."},
                {"title": "Defense Posture & Log Analysis", "pct": 0.10, "desc": "Understand defensive detection rules and remediation."},
                {"title": "Write-up & Daily Log Entry", "pct": 0.10, "desc": "Document flags captured and techniques mastered."}
            ]
        elif any(k in q_lower for k in ['code', 'python', 'javascript', 'flask', 'react', 'sql', 'backend', 'frontend', 'bug']):
            topic = "Software Engineering & Architecture"
            blocks = [
                {"title": "Architecture Blueprint & Schema Design", "pct": 0.25, "desc": "Define interfaces, data structures, and edge cases."},
                {"title": "Core Feature Implementation & Deep Coding", "pct": 0.50, "desc": "Write test-driven modules with zero distractions."},
                {"title": "Unit Testing, Refactoring & Linting", "pct": 0.15, "desc": "Verify logic paths, eliminate bugs, and format code."},
                {"title": "Commit, Push & Log Progress", "pct": 0.10, "desc": "Commit clean code and log session time to SLC."}
            ]
        elif any(k in q_lower for k in ['gym', 'workout', 'fitness', 'lift', 'run', 'cardio', 'muscle']):
            topic = "Physical Conditioning & High-Performance Fitness"
            blocks = [
                {"title": "Dynamic Mobility & Warm-Up Activation", "pct": 0.15, "desc": "Joint priming, dynamic stretching, and heart rate ramp."},
                {"title": "Primary Compound Lifts / High-Intensity Core", "pct": 0.55, "desc": "Heavy compound sets with strict progressive overload."},
                {"title": "Accessory Work & Conditioning Finisher", "pct": 0.20, "desc": "Isolation volume or high-cadence cardio intervals."},
                {"title": "Cool-Down, Hydration & Log Completion", "pct": 0.10, "desc": "Post-workout recovery protocol and metric logging."}
            ]
        else:
            topic = "Deep Focus Lock-In"
            blocks = [
                {"title": "High-Priority Core Objective Execution", "pct": 0.45, "desc": "Tackle the hardest, highest-friction task first."},
                {"title": "Secondary Execution & Problem Solving", "pct": 0.35, "desc": "Iterate on supporting objectives with steady pace."},
                {"title": "Review, Quality Assurance & Synthesis", "pct": 0.10, "desc": "Test your work and verify deliverables against goals."},
                {"title": "Daily Lock-In Reflection & Journal", "pct": 0.10, "desc": "Document achievements and lock in your streak."}
            ]

        # Calculate time blocks
        schedule_items = []
        accumulated_mins = 0
        for i, b in enumerate(blocks):
            if i == len(blocks) - 1:
                duration = total_available_minutes - accumulated_mins
            else:
                duration = max(5, int(round(total_available_minutes * b['pct'])))
                accumulated_mins += duration
            schedule_items.append({
                "phase": f"Phase {i+1}",
                "title": b['title'],
                "duration_minutes": duration,
                "description": b['desc']
            })

        # Calculate pomodoros
        pomodoro_count = max(1, total_available_minutes // 30)

        motivation_quotes = [
            "Discipline is doing what needs to be done, even when you don't feel like it.",
            "You don't need motivation. You need relentless execution and consistency.",
            "Every single lock-in session stacks up. Stay locked in and build your legacy.",
            "The person you said you would become is built in the quiet hours right now."
        ]
        quote = motivation_quotes[streak % len(motivation_quotes)]

        return {
            "query": query_clean,
            "topic": topic,
            "total_minutes": total_available_minutes,
            "total_hours_formatted": f"{total_available_minutes // 60}h {total_available_minutes % 60}m" if total_available_minutes >= 60 else f"{total_available_minutes}m",
            "pomodoro_cycles": f"{pomodoro_count}x 25m focus blocks",
            "schedule": schedule_items,
            "motivation": quote,
            "provider_used": "SLC Expert Heuristic Engine (Offline Resilient)"
        }

    @classmethod
    def _query_openai(cls, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calls OpenAI API with JSON output format."""
        api_key = current_app.config.get('OPENAI_API_KEY')
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "You are the elite AI Productivity Assistant of Shroud's Lockin Crib (SLC). "
            "Your tone is disciplined, direct, inspiring, and tactical. "
            "You output strictly a JSON object with keys: topic, total_minutes, total_hours_formatted, "
            "pomodoro_cycles, schedule (array of objects with phase, title, duration_minutes, description), "
            "and motivation."
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User prompt: {query}\nUser context: {json.dumps(user_context)}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.5
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        content = data['choices'][0]['message']['content']
        parsed = json.loads(content)
        parsed['provider_used'] = 'OpenAI'
        return parsed

    @classmethod
    def _query_gemini(cls, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calls Gemini REST API."""
        api_key = current_app.config.get('GEMINI_API_KEY')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        prompt = (
            "You are the elite AI Productivity Assistant of Shroud's Lockin Crib (SLC). "
            "Output ONLY valid JSON with keys: topic, total_minutes, total_hours_formatted, "
            "pomodoro_cycles, schedule (list of {phase, title, duration_minutes, description}), motivation. "
            f"User request: {query}. User context: {json.dumps(user_context)}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        # Extract JSON from code fences if present
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            parsed['provider_used'] = 'Gemini'
            return parsed
        raise ValueError("Invalid response format from Gemini")
