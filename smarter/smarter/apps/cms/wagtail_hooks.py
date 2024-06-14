"""Wagtail hooks for the CMS app."""

from wagtail import hooks
from wagtail.models import Page


# pylint: disable=W0613
@hooks.register("construct_explorer_page_queryset")
def show_root_page_in_explorer(parent_page, pages, request):
    if parent_page.is_root():
        # Include the root page itself in the listing
        pages = pages | Page.objects.filter(id=parent_page.id)
    return pages
