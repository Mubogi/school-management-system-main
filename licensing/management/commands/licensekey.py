"""Generate and apply license keys for the offline edition.

Resellers run this on their own machine to issue signed activation codes for
schools, without any internet connection:

    # Perpetual PREMIUM key (not bound to a machine)
    python manage.py licensekey generate --tier PREMIUM

    # 1-year STANDARD key bound to a specific school PC
    python manage.py licensekey generate --tier STANDARD --days 365 \
        --hwid ABCD-1234-EF56-7890 --school "St. Mary's"

A school applies a key from the activation page, or from the command line:

    python manage.py licensekey apply SMS-PREMIUM-....-AABBCCDDEEFF0011

The signing secret must match between the reseller tool and the school
installation. Set JDHUB_LICENSE_SECRET in both environments.
"""
from django.core.management.base import BaseCommand, CommandError

from licensing.activation import (
    LICENSE_TIERS,
    LICENSE_SIGNING_SECRET,
    build_license_key,
    activate_license,
)
from licensing.hwid import _get_hardware_id


class Command(BaseCommand):
    help = 'Generate or apply offline license keys.'

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='subcommand', required=True)

        gen = sub.add_parser('generate', help='Generate a signed license key.')
        gen.add_argument('--tier', required=True,
                         choices=['BASIC', 'STANDARD', 'PREMIUM'])
        gen.add_argument('--days', type=int, default=0,
                         help='Validity in days; 0 (default) = perpetual.')
        gen.add_argument('--hwid', default=None,
                         help='Bind the key to a machine HWID.')
        gen.add_argument('--school', default='',
                         help='Optional school name recorded in the key.')
        gen.add_argument('--show-hwid', action='store_true',
                         help="Print this machine's HWID first.")

        apply = sub.add_parser('apply', help='Apply a license key locally.')
        apply.add_argument('key', help='The license key to activate.')

    def handle(self, *args, **options):
        sub = options['subcommand']
        if sub == 'generate':
            self._generate(options)
        elif sub == 'apply':
            self._apply(options)

    def _generate(self, options):
        if options.get('show_hwid'):
            self.stdout.write(f"This machine HWID: {_get_hardware_id()}")

        tier = options['tier']
        features = LICENSE_TIERS[tier]['features']
        key = build_license_key(
            tier=tier,
            duration_days=options['days'] or None,
            hwid=options['hwid'],
            school_name=options['school'],
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('License key generated'))
        self.stdout.write(f'  Tier      : {tier}')
        self.stdout.write(f'  Validity  : {"perpetual" if not options["days"] else str(options["days"]) + " days"}')
        self.stdout.write(f'  HWID bound: {options["hwid"] or "no (any machine)"}')
        self.stdout.write(f'  Features  : {", ".join(features)}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('KEY:'))
        self.stdout.write(key)
        self.stdout.write('')
        if LICENSE_SIGNING_SECRET.startswith('jdhub-license-signing-2026'):
            self.stdout.write(self.style.WARNING(
                'WARNING: using the default signing secret. Set '
                'JDHUB_LICENSE_SECRET to a private value before selling keys.'
            ))
            self.stdout.write('')

    def _apply(self, options):
        key = options['key'].strip()
        hwid = _get_hardware_id()
        ok, message = activate_license(key, hwid)
        if ok:
            self.stdout.write(self.style.SUCCESS(f'Activated: {message}'))
        else:
            raise CommandError(f'Activation failed: {message}')
