# -*- coding: utf-8 -*-
"""Account utilities."""

import random

from smarter.apps.account.models import Account


def randomized_account_number():
    """
    Generate a random account number of the format ####-####-####.
    """

    # Generate three 4-digit numbers
    def account_number_generator():
        parts = [str(random.randint(0, 9999)).zfill(4) for _ in range(3)]
        retval = "-".join(parts)
        return retval

    account_number = account_number_generator()
    while Account.objects.filter(account_number=account_number).exists():
        account_number = account_number_generator()

    return account_number
