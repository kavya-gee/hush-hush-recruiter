import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import Candidate, User


class Command(BaseCommand):
    help = 'Import github candidate data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file')
        if not file_path:
            file_path = os.path.join(settings.BASE_DIR, 'candidate_data', 'github.csv')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        total_imported = 0

        with open(file_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                display_name = row.get('Git_UserName', '')
                if not display_name:
                    continue

                user, created = User.objects.get_or_create(
                    username=display_name,
                    defaults={
                        'password': 'default',
                        'email': f"{display_name}@gmail.com",  # Keeping it for now ..... don't want to accidentally send emails to the users
                        'full_name': display_name,
                        'is_candidate': True,
                        'is_active': True,
                        'is_staff': False,
                        'is_superuser': False,
                        'is_hiring_manager': False,
                        'first_name': ' ',
                        'last_name': ' ',
                        'date_joined': datetime.now(),
                    }
                )

                candidate, created = Candidate.objects.update_or_create(
                    user=user,
                    defaults={
                        'source': 'GITHUB',
                        'source_score': float(row.get('combined_score', 0)),
                        'skills': 'none',
                        'profile_completed': True,
                        'generated_password': 'default',
                        'data_cleanup_status': 'ACTIVE',
                        'interview_status': 'PENDING',
                    }
                )

                total_imported += 1

                if total_imported % 100 == 0:
                    self.stdout.write(f"Imported {total_imported} candidates...")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {total_imported} candidates'))