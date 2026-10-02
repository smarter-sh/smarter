"""Add local files, e.g. a folder of PDFs, to a vectorstore, and load them."""

import os

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.vectorstore.extract import EXTENSIONS
from smarter.apps.vectorstore.models import (
    VectorstoreDocumentSource,
    VectorstoreMeta,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.apps.vectorstore.tasks import load_vectorstore_document
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py load_vectorstore_documents command.

    Adds a file, or every supported file in a folder and its subfolders, to a vectorstore:
    PDF, text, Markdown, CSV, JSON, YAML and HTML. Files whose text is already in the vectorstore
    are skipped. They are loaded by Celery, or now, with ``--now``.

    .. code-block:: console

        python manage.py load_vectorstore_documents --name example_knowledge_base --path /data/manuals
    """

    help = "Add a file, or a folder of files, e.g. PDFs, to a vectorstore, and load them."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="The vectorstore's name.")
        parser.add_argument("--path", required=True, help="A file, or a folder.")
        parser.add_argument(
            "--username", default=smarter_cached_objects.smarter_admin.username, help="The vectorstore's owner."
        )
        parser.add_argument("--now", action="store_true", help="Load them now, rather than with Celery.")

    @staticmethod
    def files(path: str) -> list[str]:
        if os.path.isfile(path):
            return [path]
        return sorted(
            os.path.join(root, name)
            for root, _, names in os.walk(path)
            for name in names
            if os.path.splitext(name.lower())[1] in EXTENSIONS
        )

    def handle(self, *args, **options):
        self.handle_begin()
        user = get_cached_user_for_username(username=options["username"])
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
        vectorstore = VectorstoreMeta.objects.filter(user_profile=user_profile, name=options["name"]).first()
        if vectorstore is None:
            self.handle_completed_failure(ValueError(options["name"]), f"Vectorstore {options['name']} not found.")
            return
        if vectorstore.status != VectorstoreStatus.READY:
            self.stdout.write(
                self.style.WARNING(f"{vectorstore.name} is {vectorstore.status}: deploy it to load them.")
            )
        service = VectorstoreService(vectorstore)
        for path in self.files(options["path"]):
            with open(path, "rb") as f:
                data = f.read()
            try:
                document, created = service.add_document(
                    name=os.path.basename(path), data=data, source=VectorstoreDocumentSource.FILE
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.stdout.write(self.style.ERROR(f"{path}: {e}"))
                continue
            if not created:
                self.stdout.write(f"{path}: already in {vectorstore.name}.")
                continue
            if vectorstore.status == VectorstoreStatus.READY:
                if options["now"]:
                    chunks = service.load_document(document)
                    self.stdout.write(self.style.SUCCESS(f"{path}: loaded {chunks} chunks."))
                else:
                    load_vectorstore_document.delay(document.pk)
                    self.stdout.write(self.style.SUCCESS(f"{path}: queued."))
            else:
                self.stdout.write(f"{path}: added.")
        self.handle_completed_success()
