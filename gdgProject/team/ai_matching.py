"""
AI-Powered Team Matching Service — [E15]

Scores open teams for a given user based on:
  1. Role complementarity   — user's preferred role is missing from team (40 pts)
  2. Skill complementarity  — skills user has that the team lacks (up to 30 pts)
  3. Size factor            — teams closer to full rank higher (up to 20 pts)
  4. Familiarity bonus      — shared tech stack (up to 10 pts)

Max raw score = 100.

Optional: call Claude via the Anthropic API for natural-language explanations.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("campusarena.ai_matching")


@dataclass
class TeamMatchResult:
    team_id: int
    team_name: str
    event_title: str
    score: float          # 0–100
    spots_remaining: int
    missing_roles: list[str]
    complementary_skills: list[str]
    shared_skills: list[str]
    match_reason: str


def get_team_recommendations(
    *,
    user,
    event_id: int,
    top_n: int = 10,
) -> list[TeamMatchResult]:
    """
    Return up to *top_n* ranked TeamMatchResult objects for *user* on *event_id*.
    """
    from team.models import Team

    # Resolve max_team_size from the event (fall back to 4 if no teams yet)
    first_team = (
        Team.objects.filter(event_id=event_id).select_related("event").first()
    )
    max_size = first_team.event.max_team_size if first_team else 4

    user_skills = _get_user_skills(user)
    user_role = _get_user_preferred_role(user, event_id)

    open_teams = (
        Team.objects.filter(event_id=event_id, status="open", is_deleted=False)
        .exclude(memberships__user=user)
        .exclude(leader=user)
        .prefetch_related("memberships__user")
        .select_related("event", "leader")
    )

    results = [
        result
        for team in open_teams
        if (result := _score_team(team=team, user_skills=user_skills, user_role=user_role, max_size=max_size))
    ]

    results.sort(key=lambda r: -r.score)
    return results[:top_n]


def _get_user_skills(user) -> set[str]:
    skills: set[str] = set()

    try:
        if user.profile.skills:
            for s in user.profile.skills.split(","):
                s = s.strip().lower()
                if s:
                    skills.add(s)
    except Exception:
        pass

    try:
        for ts in user.tech_stacks.all():
            skills.add(ts.tech_name.lower())
    except Exception:
        pass

    return skills


def _get_user_preferred_role(user, event_id: int) -> Optional[str]:
    try:
        from registration.models import Registration

        reg = Registration.objects.filter(event_id=event_id, user=user).first()
        if reg and reg.preferred_role:
            return reg.preferred_role
    except Exception:
        pass
    return None


def _get_team_skills(team) -> set[str]:
    skills: set[str] = set()
    for membership in team.memberships.all():
        if membership.skills:
            for s in membership.skills.split(","):
                s = s.strip().lower()
                if s:
                    skills.add(s)
        try:
            if membership.user.profile.skills:
                for s in membership.user.profile.skills.split(","):
                    s = s.strip().lower()
                    if s:
                        skills.add(s)
        except Exception:
            pass
    return skills


def _get_team_roles(team) -> set[str]:
    return {m.role for m in team.memberships.all() if m.role}


def _score_team(
    *,
    team,
    user_skills: set[str],
    user_role: Optional[str],
    max_size: int,
) -> Optional[TeamMatchResult]:
    member_count = team.memberships.count()
    spots = max_size - member_count
    if spots <= 0:
        return None

    from team.models import MemberRole

    team_skills = _get_team_skills(team)
    team_roles = _get_team_roles(team)

    complementary = [s for s in user_skills if s not in team_skills]
    shared = [s for s in user_skills if s in team_skills]

    all_roles = {r for r, _ in MemberRole.choices if r != MemberRole.OTHER}
    missing_roles = list(all_roles - team_roles)

    # --- Scoring ---
    role_score = 40 if (user_role and user_role in missing_roles) else 0
    skill_score = min(len(complementary), 3) * 10
    max_spots = max_size - 1
    size_score = round((1 - (spots - 1) / max(max_spots, 1)) * 20) if max_spots > 0 else 10
    familiarity_score = min(len(shared), 2) * 5

    total = role_score + skill_score + size_score + familiarity_score

    # Build human-readable reason
    reasons = []
    if role_score:
        role_label = dict(MemberRole.choices).get(user_role, user_role)
        reasons.append(f"team needs a {role_label}")
    if complementary:
        reasons.append(f"you bring {', '.join(complementary[:3])}")
    if not reasons:
        reasons.append("general skill diversity")

    return TeamMatchResult(
        team_id=team.pk,
        team_name=team.name,
        event_title=team.event.title,
        score=float(total),
        spots_remaining=spots,
        missing_roles=missing_roles,
        complementary_skills=complementary[:5],
        shared_skills=shared[:5],
        match_reason="Good match — " + " and ".join(reasons),
    )


# ── Optional: Claude-powered explanations ────────────────────────────────────


def get_ai_explanation(match: TeamMatchResult, user) -> str:
    """
    Generate a natural-language explanation via Claude.
    Falls back to rule-based match_reason if the anthropic package is absent or the call fails.
    """
    try:
        import anthropic

        all_skills = match.complementary_skills + match.shared_skills
        prompt = (
            f"A student named {user.get_full_name() or user.username} is looking for a hackathon team.\n\n"
            f"Their skills: {', '.join(all_skills) or 'not specified'}\n"
            f"Their preferred role: {user_role if (user_role := match.complementary_skills[0] if match.complementary_skills else None) else 'not specified'}\n\n"
            f"Team '{match.team_name}' has {match.spots_remaining} open spot(s).\n"
            f"Team already has: {', '.join(match.shared_skills) or 'none'}\n"
            f"Skills team is missing (student can fill): {', '.join(match.complementary_skills) or 'none'}\n"
            f"Roles still needed: {', '.join(match.missing_roles[:3]) or 'none'}\n\n"
            "In 2-3 sentences, explain why this student and team are a great match. "
            "Be specific. No bullet points."
        )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    except ImportError:
        logger.debug("anthropic package not installed — using rule-based explanation")
        return match.match_reason
    except Exception as exc:
        logger.warning("Claude explanation failed: %s", exc)
        return match.match_reason
