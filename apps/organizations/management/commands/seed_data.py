
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.organizations.models import Organization
from apps.companies.models import Company
from apps.integrations.alegra.models import AlegraCredential

class Command(BaseCommand):
    help = 'Seeds the database with initial data for organizations, companies, and credentials.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))

        # --- 1. Create Organization ---
        org, created = Organization.objects.get_or_create(
            slug='latam',
            defaults={'uuid': '880d175f-bac8-4eca-a48c-aabc559bc093', 'is_active': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Organization "{org.slug}" created.'))
        else:
            self.stdout.write(self.style.WARNING(f'Organization "{org.slug}" already exists.'))

        # --- 2. Define the complete metadata for the Company ---
        company_metadata = {
          "metadata": {
            "erpnext_config": {
              "notifications": {
                "on_new_order": True,
                "on_stock_change": False
              },
              "default_warehouse": "Sucursal - DM",
              "preferred_currency": "COP"
            },
            "alegra_config": {
              "number_template_id": 19, # <-- PLEASE CHANGE THIS ID
              "number_template_prefix": "FEDI", # <-- PLEASE CHANGE THIS PREFIX
              "payment_method_mappings": {
                "Efectivo": 1, # <-- PLEASE CHANGE THIS MAPPING
                "Tarjeta de Crédito": 5 # <-- PLEASE CHANGE THIS MAPPING
              },
              "default_bank_id": 1 # <-- PLEASE CHANGE THIS ID
            }
          }
        }

        # --- 3. Create or Update Company ---
        company, created = Company.objects.update_or_create(
            organization=org,
            name='Diem',
            defaults={'metadata': company_metadata}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Company "{company.name}" created with correct metadata.'))
        else:
            self.stdout.write(self.style.WARNING(f'Company "{company.name}" already exists. Metadata has been updated.'))

        # --- 4. Create Alegra Credentials (with placeholders) ---
        credential, created = AlegraCredential.objects.get_or_create(
            company=company,
            defaults={
                'api_key': 'info@diem.com.co', # <-- !!! CHANGE THIS !!!
                'api_secret': 'dd25e346ccfb2b06ff9e' # <-- !!! CHANGE THIS !!!
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Placeholder credentials for "{company.name}" created.'))
            self.stdout.write(self.style.NOTICE('Please update the placeholder credentials in the database!'))
        else:
            self.stdout.write(self.style.WARNING(f'Credentials for "{company.name}" already exist. Please verify them.'))

        self.stdout.write(self.style.SUCCESS('Database seeding finished.'))

