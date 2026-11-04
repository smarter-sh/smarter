"""
The Doodle: the sign-in page's illustration of the day.

The web console's sign-in page shows a small, colorful illustration of a Smarter LLMClient and the
resources around it. On days worth celebrating, such as a holiday, a day of recognition or a
moment in computing history, the illustration is decorated for the day. Visitors in different
regions can see different doodles on the same day, according to their time zone.

- :mod:`smarter.apps.doodle.regions` maps a browser's time zone to a region, and its local date.
- :mod:`smarter.apps.doodle.schedule` decides the days on which a theme is due.
- :mod:`smarter.apps.doodle.artwork` draws a theme's props on the base scene.
- :mod:`smarter.apps.doodle.planner` chooses each region's doodle, a week ahead.
- :mod:`smarter.apps.doodle.tasks` runs the planner daily, from Celery Beat.
- :mod:`smarter.apps.doodle.api.v1` serves the doodle of the day, and its artwork.
"""
