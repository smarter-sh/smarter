"""Signals of SkillPlugin tool calls, and the retrieval of remote skills."""

from django.dispatch import Signal

skill_plugin_request_started = Signal()
"""
Signal sent when a SkillPlugin tool call begins: a request for the skill's instructions, or one of its bundled files.

Arguments:
    plugin: The SkillPlugin instance.
    function_args: The tool call's arguments, as the LLM sent them.

Example::

    skill_plugin_request_started.send(sender=self.__class__, plugin=self, function_args=function_args)
"""

skill_plugin_responded = Signal()
"""
Signal sent when a SkillPlugin tool call returns its response to the LLM.

Arguments:
    plugin: The SkillPlugin instance.
    response: The skill's instructions, or the bundled file.
    cached: Always False. A SkillPlugin reads the skill that was stored when its manifest was applied.
    resource: The bundled file that was requested, or None for the instructions.

Example::

    skill_plugin_responded.send(sender=self.__class__, plugin=self, response={"instructions": "..."}, cached=False, resource="assets/template.md")
"""

skill_plugin_failed = Signal()
"""
Signal sent when a SkillPlugin tool call fails, whether it raises or returns an empty response to the LLM.

Arguments:
    plugin: The SkillPlugin instance.
    error: What went wrong. It never contains credentials.

Example::

    skill_plugin_failed.send(sender=self.__class__, plugin=self, error="resource not found: assets/missing.md")
"""

skill_plugin_request_completed = Signal()
"""
Signal sent when a SkillPlugin tool call ends, successfully or not.

It is always the last signal of the call.

Arguments:
    plugin: The SkillPlugin instance.
    success: False if skill_plugin_failed was sent.
    duration: The seconds that the tool call took.

Example::

    skill_plugin_request_completed.send(sender=self.__class__, plugin=self, success=True, duration=0.42)
"""

skill_plugin_retrieval_started = Signal()
"""
Signal sent when a SkillPlugin begins to retrieve its skill from the manifest's ``skillData.source``, which happens when the manifest is applied.

Arguments:
    plugin: The SkillPlugin instance.
    url: The skill source URL.

Example::

    skill_plugin_retrieval_started.send(sender=self.__class__, plugin=self, url=url)
"""

skill_plugin_retrieved = Signal()
"""
Signal sent when a SkillPlugin has retrieved its skill.

Arguments:
    plugin: The SkillPlugin instance.
    url: The skill source URL.
    skill_name: The skill's name, from its SKILL.md.
    resource_count: The number of bundled files.
    duration: The seconds that the retrieval took.

Example::

    skill_plugin_retrieved.send(sender=self.__class__, plugin=self, url=url, skill_name="pdf", resource_count=4, duration=1.2)
"""

skill_plugin_retrieval_failed = Signal()
"""
Signal sent when a SkillPlugin cannot retrieve its skill, or the retrieved skill is invalid.

A GitHub api token that GitHub rejects is reported here, with the HTTP status in the error.

Arguments:
    plugin: The SkillPlugin instance.
    url: The skill source URL.
    error: What went wrong. It never contains the GitHub api token.
    duration: The seconds until the retrieval failed.

Example::

    skill_plugin_retrieval_failed.send(sender=self.__class__, plugin=self, url=url, error="SKILL.md was not found", duration=0.3)
"""
