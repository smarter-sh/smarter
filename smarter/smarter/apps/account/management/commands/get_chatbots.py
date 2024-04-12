# -*- coding: utf-8 -*-
"""This module is used to generate a JSON list of all chatbots for an account, printed to the console."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot


# pylint: disable=E1101
class Command(BaseCommand):
    """generate a JSON list of all chatbots for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")

    def handle(self, *args, **options):
        account_number = options["account_number"]
        company_name = options["company_name"]

        account: Account = None

        if options["account_number"]:
            try:
                account = Account.objects.get(account_number=account_number)
            except Account.DoesNotExist:
                print(f"Account {account_number} not found.")
                return
        elif options["company_name"]:
            try:
                account = Account.objects.get(company_name=company_name)
            except Account.DoesNotExist:
                print(f"Account {company_name} not found.")
                return
        else:
            raise ValueError("You must provide either an account number or a company name.")

        chatbots = ChatBot.objects.filter(account=account)

        for chatbot in chatbots:
            print(f"{chatbot.hostname}")
