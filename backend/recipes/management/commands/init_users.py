import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


def _create_or_update_user(
    *,
    is_superuser: bool,
    username: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> str:
    if not username or not email or not password:
        role = "superuser" if is_superuser else "user"
        return f"[init_users] Skipped {role}: missing required fields."

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "is_staff": True if is_superuser else False,
            "is_superuser": True if is_superuser else False,
        },
    )

    # Keep these idempotent: update email/names
    # if they changed and always set password.
    changed = False
    if user.email != email:
        user.email = email
        changed = True
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        changed = True
    if last_name and user.last_name != last_name:
        user.last_name = last_name
        changed = True

    # Always ensure password is set to
    # the provided one (safe to call repeatedly).
    user.set_password(password)
    if changed:
        user.save()
    else:
        # set_password already saves in Django >= 3.2? To be explicit:
        user.save(update_fields=["password"])

    return (f"[init_users] {'Created' if created else 'Updated'}"
            f"{'superuser' if is_superuser else 'user'}: {username}")


class Command(BaseCommand):
    help = "Initialize default users from environment variables (idempotent)."

    def handle(self, *args, **options):
        # Superuser
        # (standard env names compatible with `createsuperuser --noinput`)
        su_username = os.getenv("DJANGO_SUPERUSER_USERNAME", "")
        su_email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        su_password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if su_username and su_email and su_password:
            msg = _create_or_update_user(
                is_superuser=True,
                username=su_username,
                email=su_email,
                password=su_password,
                first_name=os.getenv("DJANGO_SUPERUSER_FIRST_NAME", ""),
                last_name=os.getenv("DJANGO_SUPERUSER_LAST_NAME", ""),
            )
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "[init_users] Superuser envs incomplete;skipping"
                    "(provide DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD)."
                )
            )

        # Two regular users
        for n in (1, 2):
            prefix = f"INIT_USER{n}_"
            username = os.getenv(prefix + "USERNAME", "")
            email = os.getenv(prefix + "EMAIL", "")
            password = os.getenv(prefix + "PASSWORD", "")
            first_name = os.getenv(prefix + "FIRST_NAME", "")
            last_name = os.getenv(prefix + "LAST_NAME", "")
            if username and email and password:
                msg = _create_or_update_user(
                    is_superuser=False,
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"[init_users] Skipping regular user {n}: "
                        f"set {prefix}USERNAME/EMAIL/PASSWORD."
                    )
                )
