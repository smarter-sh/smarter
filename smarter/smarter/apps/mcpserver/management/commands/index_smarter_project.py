"""Index The Smarter Project's GitHub repositories, and its blog, for the Smarter Project MCP server."""

from smarter.apps.mcpserver.index.blog import index_blog
from smarter.apps.mcpserver.index.indexer import index_repository
from smarter.apps.mcpserver.repositories import repository_names
from smarter.apps.mcpserver.tasks import index_blog as index_blog_task
from smarter.apps.mcpserver.tasks import index_repositories
from smarter.apps.mcpserver.tasks import index_repository as index_repository_task
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py index_smarter_project command.

    Brings the index of each of The Smarter Project's repositories up to date with its
    branch, and the index of its blog up to date with its published posts. A repository
    whose branch has not moved since it was indexed, or a blog whose posts have not changed,
    is skipped, unless ``--force`` is given. ``--repository`` indexes only the named
    repositories, and ``--blog`` only the blog. With ``--queue``, the repositories are indexed by the Celery
    worker instead, which is how ``manage.py initialize_platform`` runs it.

    **Example usage**::

        python manage.py index_smarter_project
        python manage.py index_smarter_project --repository smarter-cli --force
        python manage.py index_smarter_project --blog
        python manage.py index_smarter_project --queue
    """

    help = "Index The Smarter Project's GitHub repositories, and its blog, for the Smarter Project MCP server."

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--repository",
            action="append",
            choices=repository_names(),
            help="A repository to index. May be repeated. Defaults to every repository.",
        )
        parser.add_argument("--blog", action="store_true", help="Index the blog. Without --repository, only the blog.")
        parser.add_argument("--force", action="store_true", help="Index even if the latest commit is already indexed.")
        parser.add_argument("--queue", action="store_true", help="Queue the indexing for the Celery worker.")

    def handle(self, *args, **options):
        """Index the repositories."""
        self.handle_begin()
        force = options["force"]
        only_blog = options["blog"] and not options["repository"]
        names = [] if only_blog else options["repository"] or repository_names()
        include_blog = options["blog"] or not options["repository"]

        if options["queue"]:
            if options["repository"] or only_blog:
                for name in names:
                    index_repository_task.delay(name, force=force)
                if include_blog:
                    index_blog_task.delay(force=force)
            else:
                index_repositories.delay(force=force)
            queued = names + (["the blog"] if include_blog else [])
            self.stdout.write(f"Queued the indexing of {', '.join(queued)}.")
            self.handle_completed_success()
            return

        failed = []
        if include_blog:
            index = index_blog(force=force)
            if index.error:
                failed.append(index.repository)
                self.stdout.write(self.style.WARNING(f"{index.repository}: {index.status}, {index.error}"))
            else:
                self.stdout.write(f"{index.repository}: {index.status}, {index.file_count} posts.")
        for name in names:
            index = index_repository(name, force=force)
            if index.error:
                failed.append(name)
                self.stdout.write(self.style.WARNING(f"{name}: {index.status}, {index.error}"))
            else:
                self.stdout.write(f"{name}: {index.status} at {index.commit_sha}, {index.file_count} files.")
        if failed:
            self.stdout.write(self.style.WARNING(f"Could not be indexed: {', '.join(failed)}."))
        self.handle_completed_success()
