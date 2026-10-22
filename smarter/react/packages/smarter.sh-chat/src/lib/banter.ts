/**
 * Idle banter: silly lines that the chat displays while it waits on a slow prompt.
 *
 * A prompt can take a while, e.g. when the LLM calls tools or MCP servers, and the platform may send nothing between
 * its progress events. Rather than leave the user staring at a typing indicator, BANTER_DELAY_MS after a prompt is
 * sent the assistant replies with a chat bubble of banter, e.g. "Hang on while I flabberjabber your answer…", whose
 * line changes every BANTER_INTERVAL_MS until the response replaces it. Progress events don't delay it: they are
 * reported in the typing indicator, and in sandbox mode in the thread. See components/SmarterChat/Component.tsx.
 *
 * Each line is a translated sentence with one made-up English verb in it. The verbs are nonsense, so they are not
 * translated: every language gets the same silly words.
 */
import { gettext, interpolate } from "@/lib/i18n";

/** How long, in milliseconds, after a prompt is sent its first line of banter is displayed. A fast prompt has none. */
export const BANTER_DELAY_MS = 3_000;

/** How often, in milliseconds, a new line of banter replaces the last while a prompt runs. */
export const BANTER_INTERVAL_MS = 10_000;

/** Silly, made-up or nearly made-up English verbs, in their base form, e.g. "I flabberjabber". Never translated. */
export const BANTER_VERBS: readonly string[] = [
  "flabberjabber",
  "discombobulate",
  "recombobulate",
  "kerfuffle",
  "bamboozle",
  "hornswoggle",
  "skedaddle",
  "lollygag",
  "dillydally",
  "flummox",
  "galumph",
  "snickersnack",
  "wibble-wobble",
  "fandangle",
  "gobbledygookify",
  "brouhahify",
  "snorkelate",
  "fizzlewhisk",
  "bumfuzzle",
  "cattywampus",
  "collywobble",
  "hullabaloodle",
  "razzle-dazzle",
  "shenanigate",
  "tomfoolerate",
  "whatchamacallify",
  "thingamajiggle",
  "doohickify",
  "flibbertigibbetize",
  "skullduggerate",
  "malarkify",
  "balderdashify",
  "codswallop",
  "gallivant",
  "canoodle",
  "noodle",
  "doodle",
  "befuddle",
  "bedazzle",
  "frobnicate",
  "defrobnicate",
  "twiddle",
  "fiddle-faddle",
  "flapdoodle",
  "jibber-jabber",
  "blatherskitter",
  "higgledy-piggle",
  "hocus-pocusify",
  "zigzaggerate",
  "wigglewaggle",
  "snollygosterize",
  "rigmarolify",
  "shilly-shally",
  "willy-nillify",
  "hobnob",
  "kowtow",
  "skidoodle",
  "boondoggle",
  "gobsmack",
  "flimflam",
  "humbuggerate",
  "scuttlebuttle",
  "snuggle-wuggle",
  "cogitate",
  "ruminate",
  "percolate",
  "marinate",
  "triangulate",
  "reticulate",
  "spline-reticulate",
  "quantum-tunnel",
  "defenestrate",
  "transmogrify",
  "prestidigitate",
  "abracadabrate",
  "kaboodle",
  "zhuzh",
  "schmooze",
  "kibitz",
  "noodge",
  "spelunk",
  "bloviate",
  "confabulate",
  "pontificate",
  "absquatulate",
  "honeyfuggle",
  "lickety-splitify",
  "pettifog",
  "argle-bargle",
  "fuddle-duddle",
  "mumbo-jumbify",
  "yada-yadify",
  "rumpusify",
  "whirligiggle",
  "kerplunk",
  "snazzify",
  "fluffernutter",
  "squiggle",
  "jiggery-pokery",
  "wackadoodle",
];

/**
 * The sentences of the banter, translated, each with a %(verb)s placeholder.
 *
 * Translated when it's called, never in a module-level constant, so that the active language applies. See lib/i18n.tsx.
 */
function banterSentences(): string[] {
  return [
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Hang on while I %(verb)s your answer…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Give me a moment to %(verb)s the details…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Still working on it. I just need to %(verb)s a little more…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Almost there! Let me %(verb)s it one last time…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Hang in there, I'm about to %(verb)s something brilliant…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Please hold while I %(verb)s the bits and bobs…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("One sec, I have to %(verb)s the doohickey first…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Don't go anywhere, I'm still trying to %(verb)s your request…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("This is a big one. Time to %(verb)s harder…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Good answers take a while to %(verb)s. Thanks for your patience…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("I'll %(verb)s as fast as I can, promise…"),
    // Translators: %(verb)s is a made-up English nonsense verb, e.g. "flabberjabber", which is never translated.
    gettext("Still here! Just pausing to %(verb)s…"),
  ];
}

/** One of the items, at random. */
function pick<T>(items: readonly T[], random: () => number): T {
  return items[Math.min(items.length - 1, Math.floor(random() * items.length))];
}

/**
 * A random line of idle banter, in the active language, e.g. "Hang on while I flabberjabber your answer…".
 *
 * @param random A function that returns a number in [0, 1), like Math.random, which is the default. Tests pass their own.
 * @returns The line, as plain text.
 */
export function idleBanter(random: () => number = Math.random): string {
  return interpolate(pick(banterSentences(), random), { verb: pick(BANTER_VERBS, random) });
}
