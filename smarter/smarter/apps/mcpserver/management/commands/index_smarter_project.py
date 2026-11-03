"""
The ``index_smarter_project`` management command: index The Smarter Project's repositories and blog.

The MCPServer's public endpoint searches an index of each repository's files, and of the blog's
posts. This command brings those indexes up to date, either in the foreground, which shows
each outcome, or by queueing the Celery tasks of :mod:`smarter.apps.mcpserver.tasks`, which is
how ``manage.py initialize_platform`` runs it.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.services.indexing.blog import index_blog
from smarter.apps.mcpserver.services.indexing.github import index_repository
from smarter.apps.mcpserver.services.repositories import repository_names
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

    A repository that cannot be indexed is reported as a warning, and the command still
    succeeds: the failure is recorded in the index's ``error``, and the previous index, if any,
    is still searched.

    **Side effects:** requests to the GitHub api and the blog, and the replacement of the
    indexed files in the database. With ``--queue``, Celery tasks are queued instead.

    **Example usage**::

        python manage.py index_smarter_project
        python manage.py index_smarter_project --repository smarter-cli --force
        python manage.py index_smarter_project --blog
        python manage.py index_smarter_project --queue
    """

    help = "Index The Smarter Project's GitHub repositories, and its blog, for the MCPServer's public endpoint."

    def add_arguments(self, parser):
        """
        Add the command's options: ``--repository``, ``--blog``, ``--force`` and ``--queue``.

        :param parser: The command's argument parser.
        """
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
        """
        Index the repositories and the blog that the options name, or queue their indexing.

        Without ``--repository`` or ``--blog``, every repository and the blog are indexed. With
        ``--queue`` and neither of them, one :func:`~smarter.apps.mcpserver.tasks.index_repositories`
        task is queued, which queues the others.

        :param args: Unused.
        :param options: The parsed options.
        """
        self.handle_begin()
        force = options["force"]
        requested_names = options["repository"]
        wants_blog = options["blog"]
        only_blog = wants_blog and not requested_names
        if only_blog:
            names = []
        elif requested_names:
            names = requested_names
        else:
            names = repository_names()
        include_blog = wants_blog or not requested_names

        if options["queue"]:
            if requested_names or only_blog:
                for name in names:
                    index_repository_task.delay(name, force=force)
                if include_blog:
                    index_blog_task.delay(force=force)
            else:
                index_repositories.delay(force=force)
            queued = list(names)
            if include_blog:
                queued.append("the blog")
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
