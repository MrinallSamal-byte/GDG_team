from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Event, EventCategory, EventMode, EventStatus


# --------------------------------------------------------------------------- #
#  Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _event_to_dict(event):
    """Convert an Event ORM object to the dict shape the templates expect."""
    registered = event.registrations.filter(
        status__in=["confirmed", "submitted"]
    ).count()
    spots_str = f"{registered}/{event.capacity}"
    return {
        "id": event.pk,
        "title": event.title,
        "slug": event.slug,
        "category": event.get_category_display(),
        "mode": event.get_mode_display(),
        "type": event.get_participation_type_display(),
        "date": (
            event.event_start.strftime("%b %d")
            if event.event_start.date() == event.event_end.date()
            else f"{event.event_start.strftime('%b %d')}–{event.event_end.strftime('%b %d')}"
        ),
        "prize": f"₹{int(event.prize_pool):,}" if event.prize_pool else "Certificates",
        "status": event.get_status_display(),
        "spots": spots_str,
        "registered": registered,
        "capacity": event.capacity,
        "banner": event.banner.url if event.banner else None,
        "participation_certificate": event.participation_certificate,
    }


# --------------------------------------------------------------------------- #
#  Views                                                                        #
# --------------------------------------------------------------------------- #

def home(request):
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    mode = request.GET.get("mode", "").strip()
    sort = request.GET.get("sort", "newest")

    qs = Event.objects.filter(
        status__in=[
            EventStatus.REGISTRATION_OPEN,
            EventStatus.PUBLISHED,
            EventStatus.ONGOING,
            EventStatus.REGISTRATION_CLOSED,
        ]
    )

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        qs = qs.filter(category=category)
    if mode:
        qs = qs.filter(mode=mode)

    if sort == "deadline":
        qs = qs.order_by("registration_end")
    elif sort == "popular":
        qs = qs.annotate(reg_count=Count("registrations")).order_by("-reg_count")
    else:
        qs = qs.order_by("-created_at")

    event_list = [_event_to_dict(e) for e in qs[:24]]

    # Featured = first 3 registration-open events
    featured_qs = Event.objects.filter(
        status=EventStatus.REGISTRATION_OPEN
    ).order_by("-created_at")[:3]
    featured_events = [_event_to_dict(e) for e in featured_qs]

    # If DB is empty fall back to demo stubs so the page never looks blank
    if not event_list:
        featured_events = [
            {"id": 1, "title": "HackFest 2026", "category": "Hackathon",
             "mode": "Hybrid", "date": "Apr 18-20, 2026", "prize": "₹2,50,000",
             "status": "Registration Open", "spots": "124/300", "registered": 124,
             "capacity": 300, "banner": None, "participation_certificate": True},
            {"id": 2, "title": "CloudSprint Workshop", "category": "Workshop",
             "mode": "Online", "date": "Mar 22, 2026", "prize": "Certificates",
             "status": "Registration Open", "spots": "218/500", "registered": 218,
             "capacity": 500, "banner": None, "participation_certificate": True},
            {"id": 3, "title": "Design Jam Pro", "category": "Design Challenge",
             "mode": "Offline", "date": "Apr 2, 2026", "prize": "₹75,000",
             "status": "Registration Open", "spots": "95/100", "registered": 95,
             "capacity": 100, "banner": None, "participation_certificate": False},
        ]
        event_list = [
            {"id": 1, "title": "HackFest 2026", "category": "Hackathon",
             "date": "Apr 18–20", "mode": "Hybrid", "type": "Team",
             "prize": "₹2,50,000", "status": "Registration Open", "banner": None,
             "participation_certificate": True},
            {"id": 2, "title": "AlgoRush", "category": "Coding Contest",
             "date": "Mar 27", "mode": "Online", "type": "Individual",
             "prize": "₹40,000", "status": "Registration Open", "banner": None,
             "participation_certificate": False},
            {"id": 3, "title": "PitchCraft", "category": "Case Study",
             "date": "Apr 5", "mode": "Offline", "type": "Both",
             "prize": "₹1,00,000", "status": "Registration Open", "banner": None,
             "participation_certificate": True},
            {"id": 4, "title": "QuizMania", "category": "Quiz",
             "date": "Mar 19", "mode": "Online", "type": "Individual",
             "prize": "₹15,000", "status": "Registration Closed", "banner": None,
             "participation_certificate": False},
            {"id": 5, "title": "BuildOps Sprint", "category": "Workshop",
             "date": "Apr 11", "mode": "Hybrid", "type": "Team",
             "prize": "Goodies + Internship", "status": "Registration Open",
             "banner": None, "participation_certificate": True},
            {"id": 6, "title": "VisionX AI Challenge", "category": "Ideathon",
             "date": "Apr 29", "mode": "Offline", "type": "Team",
             "prize": "₹1,20,000", "status": "Registration Open", "banner": None,
             "participation_certificate": True},
        ]

    categories = [(c.value, c.label) for c in EventCategory]
    modes = [(m.value, m.label) for m in EventMode]

    return render(request, 'events/home.html', {
        'featured_events': featured_events,
        'event_grid': event_list,
        'categories': categories,
        'modes': modes,
        'q': q,
        'active_category': category,
        'active_mode': mode,
        'active_sort': sort,
    })


def event_detail(request, event_id):
    # ── Try DB first ───────────────────────────────────────────────────────
    try:
        event_obj = Event.objects.get(pk=event_id)
        registered_count = event_obj.registrations.filter(
            status__in=["confirmed", "submitted"]
        ).count()
        pct = int(registered_count / event_obj.capacity * 100) if event_obj.capacity else 0
        rounds_qs = event_obj.rounds.order_by("order")
        rounds = [
            {
                "name": f"Round {r.order}: {r.name}",
                "date": r.start_date.strftime("%b %d"),
                "status": r.get_status_display(),
                "description": r.description,
            }
            for r in rounds_qs
        ]
        individual_regs = event_obj.registrations.filter(
            status__in=["confirmed", "submitted"], type="individual"
        ).select_related("user__profile")
        participants = [
            {
                "name": reg.user.get_full_name() or reg.user.username,
                "college": getattr(reg.user, "profile", None) and reg.user.profile.college or "",
            }
            for reg in individual_regs[:20]
        ]
        open_teams = event_obj.teams.filter(status="open").prefetch_related("memberships")
        teams_open = [
            {
                "id": t.pk,
                "name": t.name,
                "members": f"{t.member_count}/{event_obj.max_team_size}",
                "spots": t.spots_available,
                "needs": "Members needed",
            }
            for t in open_teams
        ]
        looking_for_team = event_obj.registrations.filter(
            status__in=["confirmed", "submitted"], type="individual"
        ).select_related("user__profile")
        lft_participants = [
            {
                "name": reg.user.get_full_name() or reg.user.username,
                "college": getattr(reg.user, "profile", None) and reg.user.profile.college or "",
            }
            for reg in looking_for_team[:10]
        ]
        is_registered = (
            request.user.is_authenticated
            and event_obj.registrations.filter(
                user=request.user, status__in=["pending", "confirmed", "submitted"]
            ).exists()
        )
        faqs = event_obj.faqs if isinstance(event_obj.faqs, list) else []
        event = {
            "id": event_obj.pk,
            "title": event_obj.title,
            "description": event_obj.description,
            "category": event_obj.get_category_display(),
            "mode": event_obj.get_mode_display(),
            "timeline": (
                f"{event_obj.event_start.strftime('%b %d')}–"
                f"{event_obj.event_end.strftime('%b %d, %Y')}"
            ),
            "registration": f"{registered_count}/{event_obj.capacity} spots filled",
            "registered_count": registered_count,
            "capacity": event_obj.capacity,
            "pct": pct,
            "registration_end_iso": event_obj.registration_end.isoformat(),
            "eligibility": event_obj.eligibility,
            "rules": event_obj.rules,
            "prize_1st": event_obj.prize_1st,
            "prize_2nd": event_obj.prize_2nd,
            "prize_3rd": event_obj.prize_3rd,
            "prize_special": event_obj.prize_special,
            "prize_pool": event_obj.prize_pool,
            "participation_certificate": event_obj.participation_certificate,
            "merit_certificate": event_obj.merit_certificate,
            "contact_info": event_obj.contact_info,
            "is_registration_open": event_obj.is_registration_open,
            "is_registered": is_registered,
            "banner": event_obj.banner.url if event_obj.banner else None,
        }
        return render(request, 'events/event_detail.html', {
            'event': event,
            'rounds': rounds,
            'participants': participants,
            'teams_open': teams_open,
            'lft_participants': lft_participants,
            'faqs': faqs,
        })
    except Event.DoesNotExist:
        pass

    # ── Fallback stub data (while DB is empty during development) ─────────
    event = {
        'id': event_id,
        'title': 'HackFest 2026',
        'category': 'Hackathon',
        'mode': 'Hybrid',
        'timeline': 'Apr 18–20, 2026',
        'registration': '124/300 spots filled',
        'registered_count': 124,
        'capacity': 300,
        'pct': 41,
        'registration_end_iso': '2026-04-15T23:59:00',
        'description': (
            'A 36-hour campus hackathon focused on solving real student-life '
            'and sustainability problems.'
        ),
        'eligibility': 'Open to all branches. Team size 2–4. Bring your own idea or pick from challenge tracks.',
        'rules': 'Original work only. No plagiarism. All submissions before the final deadline.',
        'prize_1st': '₹1,50,000 + Internship Fast Track',
        'prize_2nd': '₹70,000 + Cloud Credits',
        'prize_3rd': '₹30,000 + Swag Kits',
        'prize_special': 'Best Social Impact: ₹20,000',
        'prize_pool': 270000,
        'participation_certificate': True,
        'merit_certificate': True,
        'contact_info': 'hackfest@campusarena.in | +91 98765 43210',
        'is_registration_open': True,
        'is_registered': False,
        'banner': None,
    }
    rounds = [
        {'name': 'Round 1: Idea Screening', 'date': 'Apr 10', 'status': 'Upcoming', 'description': 'Submit a 500-word abstract.'},
        {'name': 'Round 2: Prototype Review', 'date': 'Apr 18', 'status': 'Upcoming', 'description': 'Live demo of your working prototype.'},
        {'name': 'Round 3: Final Demo', 'date': 'Apr 20', 'status': 'Upcoming', 'description': 'Pitch to judges. Top 10 teams present.'},
    ]
    participants = [
        {'name': 'Priya Verma', 'college': 'NIT Rourkela'},
        {'name': 'Rahul S.', 'college': 'KIIT University'},
        {'name': 'Neha Kulkarni', 'college': 'VIT Chennai'},
    ]
    teams_open = [
        {'id': 1, 'name': 'Team Alpha', 'members': '3/4', 'spots': 1, 'needs': 'ML/AI'},
        {'id': 2, 'name': 'Binary Builders', 'members': '2/5', 'spots': 3, 'needs': 'Backend, DevOps'},
    ]
    faqs = [
        {'q': 'Can first-year students join?', 'a': 'Yes, absolutely. All are welcome regardless of year of study.'},
        {'q': 'Is prior hackathon experience required?', 'a': 'No, beginner-friendly tracks are included alongside advanced challenges.'},
        {'q': 'What tools can we use?', 'a': 'Any programming language, framework, or tool. Open-source libraries are encouraged.'},
    ]
    return render(request, 'events/event_detail.html', {
        'event': event,
        'rounds': rounds,
        'participants': participants,
        'teams_open': teams_open,
        'lft_participants': [],
        'faqs': faqs,
    })

# ── Contact organizer ────────────────────────────────────────────────────────
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@login_required
@require_POST
def contact_organizer(request, event_id):
    """Accept a question from a participant and redirect back to the event page."""
    message_text = request.POST.get("message", "").strip()
    if not message_text:
        django_messages.error(request, "Message cannot be empty.")
    else:
        # Future: store as a ContactMessage model or send via email
        django_messages.success(request, "Your message has been sent to the organizers.")
    return redirect("events:event_detail", event_id=event_id)