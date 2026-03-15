"""
Management command: generate_checkin_qr

Bulk-creates CheckIn records for all confirmed registrants
of an event who do not yet have one. Safe to run multiple times (idempotent).

Usage:
    python manage.py generate_checkin_qr --event-id 42
    python manage.py generate_checkin_qr --event-id 42 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Bulk-generate QR check-in tokens for all confirmed registrants of an event"

    def add_arguments(self, parser):
        parser.add_argument(
            "--event-id",
            type=int,
            required=True,
            metavar="ID",
            help="Event ID to generate check-in QR tokens for",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without writing to the database",
        )

    def handle(self, *args, **options):
        from checkin.models import CheckIn
        from events.models import Event
        from registration.models import Registration, RegistrationStatus

        event_id = options["event_id"]
        dry_run = options["dry_run"]

        try:
            event = Event.all_objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise CommandError(f"Event with id={event_id} does not exist.")

        self.stdout.write(f"Event: {event.title} (id={event.pk})")

        registrations = Registration.objects.filter(
            event=event,
            status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
        ).select_related("user").exclude(checkin__isnull=False)

        count = registrations.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("All registrants already have QR tokens. Nothing to do."))
            return

        self.stdout.write(f"Found {count} registrant(s) without a check-in token.")

        if dry_run:
            for reg in registrations:
                self.stdout.write(
                    f"  [DRY RUN] Would create token for "
                    f"{reg.user.get_full_name() or reg.user.username} ({reg.registration_id})"
                )
            self.stdout.write(self.style.SUCCESS(f"\n[DRY RUN] Would create {count} token(s)."))
            return

        created = 0
        for reg in registrations:
            CheckIn.objects.get_or_create(
                registration=reg,
                defaults={"event": event, "user": reg.user},
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} check-in token(s)."))
