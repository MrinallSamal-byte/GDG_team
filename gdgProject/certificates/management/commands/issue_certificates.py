"""
Management command: issue_certificates

Bulk-issues participation certificates for all confirmed registrants
of one or more completed events.

Usage:
    python manage.py issue_certificates --event-id 42
    python manage.py issue_certificates --all-completed
    python manage.py issue_certificates --event-id 42 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Bulk-issue participation certificates for completed events"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--event-id",
            type=int,
            metavar="ID",
            help="Issue certificates for a specific event ID",
        )
        group.add_argument(
            "--all-completed",
            action="store_true",
            help="Issue certificates for ALL completed events that have participation_certificate=True",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without writing to the database",
        )

    def handle(self, *args, **options):
        from certificates.models import Certificate, CertificateType
        from events.models import Event, EventStatus
        from registration.models import Registration, RegistrationStatus

        dry_run = options["dry_run"]

        # Resolve which events to process
        if options["event_id"]:
            events = Event.all_objects.filter(
                pk=options["event_id"],
                participation_certificate=True,
            )
            if not events.exists():
                raise CommandError(
                    f"Event {options['event_id']} not found or does not offer participation certificates."
                )
        else:
            events = Event.all_objects.filter(
                status=EventStatus.COMPLETED,
                participation_certificate=True,
                is_deleted=False,
            )

        if not events.exists():
            self.stdout.write(self.style.WARNING("No eligible events found."))
            return

        total_issued = 0
        total_skipped = 0

        for event in events:
            self.stdout.write(f"\nProcessing: {event.title} (id={event.pk})")

            registrations = Registration.objects.filter(
                event=event,
                status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
            ).select_related("user")

            event_issued = 0
            event_skipped = 0

            for reg in registrations:
                already_exists = Certificate.objects.filter(
                    registration=reg,
                    cert_type=CertificateType.PARTICIPATION,
                ).exists()

                if already_exists:
                    event_skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] Would issue cert for "
                        f"{reg.user.get_full_name() or reg.user.username} ({reg.registration_id})"
                    )
                    event_issued += 1
                else:
                    with transaction.atomic():
                        Certificate.objects.create(
                            registration=reg,
                            user=reg.user,
                            event=event,
                            cert_type=CertificateType.PARTICIPATION,
                        )
                    event_issued += 1

            self.stdout.write(
                f"  Issued: {event_issued}  |  Already existed (skipped): {event_skipped}"
            )
            total_issued += event_issued
            total_skipped += event_skipped

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}Done. Total issued: {total_issued} | Total skipped: {total_skipped}"
            )
        )
