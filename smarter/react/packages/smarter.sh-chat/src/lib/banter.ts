/**
 * Idle banter: silly lines that the chat displays while it waits on a slow prompt.
 *
 * A prompt can take a while, e.g. when the LLM calls tools or MCP servers, and the platform may send nothing between
 * its progress events. Rather than leave the user staring at a typing indicator, BANTER_DELAY_MS after a prompt is
 * sent the assistant replies with a chat bubble of banter, e.g. "Hang on while I flabberjabber the doohickey…", whose
 * line changes every BANTER_INTERVAL_MS until the response replaces it. Progress events don't delay it: they are
 * reported in the typing indicator, and in sandbox mode in the thread. See components/SmarterChat/Component.tsx.
 *
 * Each line is a translated sentence with one made-up English verb and one silly English noun in it, e.g. "the
 * doohickey". About one line in three puts a real scientific English adjective in front of the noun, e.g. "the quantum
 * doohickey". The words are nonsense together, so they are not translated: every language gets the same silly words.
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
 * Silly, made-up or nearly made-up English nouns, singular, e.g. "the doohickey". Never translated.
 *
 * Each starts with a consonant other than "h", so that the translations' articles fit every one of them, e.g. Spanish
 * "el", French "le" and Portuguese "o", without the elision of French "l'". banter.test.ts checks it.
 */
export const BANTER_NOUNS: readonly string[] = [
  "doohickey",
  "thingamajig",
  "whatchamacallit",
  "gizmo",
  "widget",
  "gubbins",
  "doodad",
  "whatsit",
  "thingummy",
  "wotsit",
  "whoosit",
  "thingy",
  "gadget",
  "contraption",
  "whirligig",
  "gimcrack",
  "bauble",
  "trinket",
  "knickknack",
  "bric-a-brac",
  "gewgaw",
  "folderol",
  "jabberwock",
  "bandersnatch",
  "snark",
  "borogove",
  "flotsam",
  "jetsam",
  "sprocket",
  "flange",
  "grommet",
  "doodlebug",
  "dingus",
  "wingding",
  "framistan",
  "jiggamaree",
  "brouhaha",
  "gobbledygook",
  "flibbertigibbet",
  "snollygoster",
  "rigmarole",
  "codswallop",
  "balderdash",
  "malarkey",
  "poppycock",
  "flapdoodle",
  "kerfuffle",
  "shenanigan",
  "tomfoolery",
  "fiddle-faddle",
  "mumbo-jumbo",
  "razzmatazz",
  "bamboozle",
  "smidgen",
  "gobbet",
  "noodle",
  "snickerdoodle",
  "fluffernutter",
  "muffin",
  "crumpet",
  "pickle",
  "kumquat",
  "spatula",
  "kazoo",
  "bagpipe",
  "zeppelin",
  "zither",
  "sasquatch",
  "platypus",
  "narwhal",
  "wombat",
  "capybara",
  "quokka",
  "dodo",
  "mongoose",
  "yeti",
  "marshmallow",
  "pretzel",
  "bumblebee",
  "wigwam",
  "teapot",
  "toboggan",
  "pogo-stick",
  "yo-yo",
  "lollipop",
  "gumdrop",
  "buttonhook",
  "monocle",
  "periscope",
  "fez",
  "tutu",
  "caboodle",
  "shebang",
  "shindig",
  "fandango",
  "gazebo",
  "pinwheel",
  "pompom",
  "tiddlywink",
  "rutabaga",
  "pumpernickel",
  "sprinkle",
  "cupcake",
];

/**
 * Real scientific English adjectives, which qualify a noun in about one line in three, e.g. "the quantum doohickey".
 * Never translated, and, as the nouns do, each starts with a consonant other than "h". See BANTER_NOUNS.
 */
export const BANTER_ADJECTIVES: readonly string[] = [
  "quantum",
  "thermodynamic",
  "photosynthetic",
  "piezoelectric",
  "paramagnetic",
  "ferromagnetic",
  "diamagnetic",
  "superconducting",
  "cryogenic",
  "centrifugal",
  "tectonic",
  "volcanic",
  "galvanic",
  "catalytic",
  "chiral",
  "crystalline",
  "colloidal",
  "viscous",
  "polymeric",
  "mitochondrial",
  "ribosomal",
  "cytoplasmic",
  "nuclear",
  "subatomic",
  "relativistic",
  "gravitational",
  "geostationary",
  "geothermal",
  "tidal",
  "lunar",
  "solar",
  "stellar",
  "galactic",
  "nebular",
  "planetary",
  "seismic",
  "sedimentary",
  "metamorphic",
  "magmatic",
  "tropospheric",
  "stratospheric",
  "barometric",
  "stochastic",
  "probabilistic",
  "Bayesian",
  "Newtonian",
  "Cartesian",
  "Gaussian",
  "Laplacian",
  "Boolean",
  "binary",
  "logarithmic",
  "polynomial",
  "differential",
  "tangential",
  "perpendicular",
  "parabolic",
  "spherical",
  "toroidal",
  "fractal",
  "recursive",
  "monoclonal",
  "genomic",
  "transgenic",
  "phylogenetic",
  "symbiotic",
  "pelagic",
  "benthic",
  "nocturnal",
  "migratory",
  "carnivorous",
  "botanical",
  "deciduous",
  "coniferous",
  "photovoltaic",
  "thermonuclear",
  "radioactive",
  "fissile",
  "luminescent",
  "bioluminescent",
  "fluorescent",
  "phosphorescent",
  "spectroscopic",
  "microscopic",
  "telescopic",
  "nanoscale",
  "biochemical",
  "kinetic",
  "volumetric",
  "gaseous",
  "plasmonic",
  "photonic",
  "supersonic",
  "tetrahedral",
  "covalent",
  "sulfuric",
  "nitrogenous",
  "calcareous",
  "siliceous",
  "quaternary",
  "Jurassic",
  "Cretaceous",
  "Pleistocene",
  "Precambrian",
  "Paleozoic",
  "Mesozoic",
  "Cambrian",
];

/** The share of the lines whose noun has an adjective. */
export const BANTER_ADJECTIVE_ODDS = 1 / 3;

/**
 * The sentences of the banter, translated, each with a %(verb)s and a %(noun)s placeholder.
 *
 * Translated when it's called, never in a module-level constant, so that the active language applies. See lib/i18n.tsx.
 */
function banterSentences(): string[] {
  return [
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Hang on while I %(verb)s the %(noun)s…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Give me a moment to %(verb)s the %(noun)s…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Still working on it. I just need to %(verb)s the %(noun)s a little more…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Almost there! Let me %(verb)s the %(noun)s one last time…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Hang in there, I'm about to %(verb)s a brilliant %(noun)s…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Please hold while I %(verb)s your %(noun)s…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("One sec, I have to %(verb)s the %(noun)s first…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Don't go anywhere, I'm still trying to %(verb)s your %(noun)s…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("This is a big one. Time to %(verb)s the %(noun)s harder…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Good answers take a while to %(verb)s, and so does the %(noun)s. Thanks for your patience…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("I'll %(verb)s the %(noun)s as fast as I can, promise…"),
    /* Translators: %(verb)s is a made-up English verb, e.g. "flabberjabber", and %(noun)s a silly English noun,
       e.g. "doohickey", sometimes after a scientific English adjective, e.g. "quantum doohickey". None of them is
       translated. Every noun and adjective starts with a consonant other than "h". */
    gettext("Still here! Just pausing to %(verb)s the %(noun)s…"),
  ];
}

/** One of the items, at random. */
function pick<T>(items: readonly T[], random: () => number): T {
  return items[Math.min(items.length - 1, Math.floor(random() * items.length))];
}

/**
 * A random line of idle banter, in the active language, e.g. "Hang on while I flabberjabber the doohickey…".
 *
 * @param random A function that returns a number in [0, 1), like Math.random, which is the default. Tests pass their own.
 * @returns The line, as plain text.
 */
export function idleBanter(random: () => number = Math.random): string {
  const sentence = pick(banterSentences(), random);
  const verb = pick(BANTER_VERBS, random);
  const noun = pick(BANTER_NOUNS, random);
  // the last third of the random numbers adds an adjective, so that a random number of 0 has none.
  const adjective = random() >= 1 - BANTER_ADJECTIVE_ODDS ? pick(BANTER_ADJECTIVES, random) : null;
  return interpolate(sentence, { verb, noun: adjective ? `${adjective} ${noun}` : noun });
}
