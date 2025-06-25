from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
from image_processor.models import ImageProcessingSession

class Command(BaseCommand):
    help = 'Clean up old image processing sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete sessions older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Find old sessions
        old_sessions = ImageProcessingSession.objects.filter(created_at__lt=cutoff_time)
        count = old_sessions.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Would delete {count} sessions older than {hours} hours'
                )
            )
            return
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No old sessions to clean up')
            )
            return
        
        # Delete old sessions and their files
        deleted_count = 0
        
        for session in old_sessions:
            try:
                # With Cloudinary storage, files are automatically managed by the cloud provider
                # No need to manually delete files
                
                # Delete session (this will cascade delete all related objects)
                session.delete()
                deleted_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error deleting session {session.session_id}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} old sessions'
            )
        ) 