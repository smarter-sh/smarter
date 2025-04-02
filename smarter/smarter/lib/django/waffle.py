from django.db.utils import OperationalError

from smarter.lib.django import waffle as waffle_orig


def switch_is_active(switch_name: str) -> bool:
    try:
        switch = waffle_orig.get_waffle_switch_model().get(switch_name)
        return switch.is_active()
    except OperationalError:
        # Handle the case where the database is not ready
        # or the switch does not exist
        return False
