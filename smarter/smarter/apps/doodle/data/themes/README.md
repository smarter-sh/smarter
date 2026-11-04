# Doodle themes

The catalog of the sign-in page's doodles. Each theme is a `<slug>.yaml` file, and the SVG of its
props, `<slug>.svg`. `manage.py load_doodle_themes`, which `initialize_platform` runs, loads them,
and the planner (`smarter.apps.doodle.planner`) chooses each region's doodle from them, a week ahead.

## A theme's file

```yaml
slug: diwali # the file's name
name: Diwali # what it celebrates
category: celebration # evergreen, celebration, national, observance, science, culture, season or sport
caption: Happy Diwali! # below the artwork; empty for none
alt_text: Glowing diyas line the ground below a Smarter LLMClient, under a string of colorful lights.
link_url: https://en.wikipedia.org/wiki/Diwali # https only
priority: 70 # 0 to 100: when several themes are due, the highest wins
regions: [south-asia, southeast-asia, us, ca, europe, oceania, africa, global] # or ["*"]
schedule:
  kind: holiday # fixed, nth_weekday, holiday or never
  country: IN
  holiday: Diwali
props: diwali.svg # optional: <slug>.svg by default, or another theme's props
```

The schedules:

| kind          | fields                                                       | e.g.                                      |
| ------------- | ------------------------------------------------------------ | ----------------------------------------- |
| `fixed`       | `month`, `day`, and `days` (1 by default)                    | Christmas: 12, 24, and 2 days             |
| `nth_weekday` | `month`, `weekday` (0 is Monday), `nth` (1 to 5, -1 is last) | Ada Lovelace Day: 10, 1, 2                |
| `holiday`     | `country`, `holiday`: text in the English name of a holiday  | Diwali: IN, Diwali, from the holidays pkg |
| `never`       |                                                              | the default theme                         |

The `holidays` package dates some countries' moving holidays only a decade or so ahead: India's, for
Diwali, up to 2035. A `holiday` theme whose country isn't dated for a year is simply not due that
year, so upgrade the package (`smarter/requirements/in/base.in`) well before then.

The regions are `global`, `us`, `ca`, `mx`, `latam`, `europe`, `africa`, `middle-east`, `south-asia`,
`east-asia`, `southeast-asia` and `oceania` (`smarter.apps.doodle.regions`). A visitor's region comes
from the browser's time zone. `global` is the region of a time zone that has none, such as UTC.

## Drawing the props

The props are drawn on the base scene, `static/doodle/base.svg`: a Smarter LLMClient's chat window,
with a plugin, a guardrail, a vectorstore and a secret around it, and its manifest below.

- Use the base scene's `viewBox="0 0 520 340"`, with `xmlns="http://www.w3.org/2000/svg"`.
- Decorate the scene; don't cover it. The free areas are the sky (y < 95), the ground (y > 285, except
  the manifest at x 190 to 330), and the top edge of the chat window (y about 105, x 185 to 335), where
  a hat can sit. The nodes are circles of radius 26 at (92, 122), (89, 230), (428, 122) and (431, 230).
- Keep it flat and simple: a few shapes, the base scene's colors (`#ff5733`, `#ffc145`, `#00c2a8`,
  `#4fc3f7`, `#ff6b9a`, `#6c5ce7`) and white, on the page's dark purple background.
- Animate with CSS only, in a `<style>` whose class and keyframe names start with the theme's own
  prefix (e.g. `dw-` for Diwali). The base scene stops every animation for visitors who prefer
  reduced motion, and the `enable_doodle_animation` switch stops them for everyone.
- No scripts, no links, no images, no external references: the page shows the doodle with `<img>`,
  which would ignore them anyway.
- National days don't use flags, which are hard to draw right at this size. Use their colors.

Preview a theme on the base scene before you commit it: `load_doodle_themes`, then open
`/api/v1/doodles/artwork/<sha256>.svg`, whose hash the admin shows, or the theme's artwork in the
admin's Doodle Themes.
