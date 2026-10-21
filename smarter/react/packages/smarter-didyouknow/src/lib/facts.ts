/**
 * The Did you know? facts: trivia about The Smarter Project, and the two ways to pick one, at random
 * (the welcome dialog) or the fact of the day (the note below the web console's title).
 *
 * Each fact is something that the project's repositories show, so that it stays true: keep them that
 * way when you add one. A fact that mentions a resource, such as a docs page, links to it.
 */
import { gettext } from "@smarter/common";

import { BLOG_URLS, DOCS_URLS, GITHUB_URLS, NPM_URLS, SITE_URLS } from "./const";

/** A piece of trivia, and an optional link to the resource that it mentions. */
export interface DidYouKnowFact {
  text: string;
  link?: { label: string; url: string };
}

/** The facts, in the order that the fact of the day goes through them. */
export function didYouKnowFacts(): DidYouKnowFact[] {
  return [
    {
      text: gettext(
        "The Smarter Project is coded in part using Agentic AI techniques that you can learn about by following this project on GitHub.",
      ),
      link: { label: gettext("Follow Smarter on GitHub"), url: GITHUB_URLS.smarter },
    },
    {
      text: gettext("The Smarter Project has around 500,000 lines of code, across two dozen repositories."),
      link: { label: gettext("Browse the repositories"), url: GITHUB_URLS.organization },
    },
    {
      text: gettext(
        "The main Smarter repository alone has about 400,000 lines of code, including about 180,000 lines of Python and 45,000 of TypeScript.",
      ),
      link: { label: gettext("Browse the repository"), url: GITHUB_URLS.smarter },
    },
    {
      text: gettext(
        "Smarter is written in Python, with Django and Django REST Framework, and its web console is written in React.",
      ),
      link: { label: gettext("Read about its technologies"), url: DOCS_URLS.technologies },
    },
    {
      text: gettext(
        "In October 2026, Claude Code wrote Smarter's source code at almost 30 times the long-run pace of its author, a senior developer.",
      ),
      link: { label: gettext("Read the story"), url: BLOG_URLS.agenticAi },
    },
    {
      text: gettext("More than 95% of Smarter's code is covered by its automated tests."),
      link: { label: gettext("Read how it got there"), url: BLOG_URLS.agenticAi },
    },
    {
      text: gettext(
        "Smarter is a Docker application that runs on Debian Linux, so it can run anywhere, from your own laptop to any data center in the world.",
      ),
      link: { label: gettext("Read why Smarter uses Docker"), url: DOCS_URLS.adrDocker },
    },
    {
      text: gettext("You can install Smarter on your own laptop in around 20 minutes."),
      link: { label: gettext("Get started"), url: DOCS_URLS.gettingStarted },
    },
    {
      text: gettext(
        "Smarter closely follows the 12-Factor App methodology, a set of principles for building software that runs in the cloud.",
      ),
      link: { label: gettext("Read the 12-Factor App decision"), url: DOCS_URLS.adrTwelveFactor },
    },
    {
      text: gettext(
        "Smarter's web console users can watch the real server logs of their own prompts, live, as the server writes them.",
      ),
      link: { label: gettext("Read about the live server logs"), url: DOCS_URLS.serverLogs },
    },
    {
      text: gettext(
        "Smarter's major design decisions, from Django and Kubernetes to Pydantic, are written down as Architecture Decision Records in its documentation.",
      ),
      link: { label: gettext("Read the Architecture Decision Records"), url: DOCS_URLS.adr },
    },
    {
      text: gettext(
        "Every Smarter platform runs an MCP server that answers questions about The Smarter Project from its own source code and documentation.",
      ),
      link: { label: gettext("Read about the MCP server"), url: DOCS_URLS.mcpServer },
    },
    {
      text: gettext(
        "Smarter has SDKs for Python, Node.js and Go, a command-line interface written in Go, and a VS Code extension for its YAML manifests.",
      ),
      link: { label: gettext("See the APIs and SDKs"), url: DOCS_URLS.sdks },
    },
    {
      text: gettext(
        "The Smarter Project was inspired by the Kubernetes Project, which is open source software for declarative cloud infrastructure management.",
      ),
      link: { label: gettext("Read about manifests"), url: DOCS_URLS.manifests },
    },
    {
      text: gettext(
        "Smarter's manifests are programmed with Pydantic, the popular open source Python data validation library on PyPI.",
      ),
      link: { label: gettext("Read why Smarter uses Pydantic"), url: DOCS_URLS.pydantic },
    },
    {
      text: gettext(
        "Smarter's repository has Agent Skills: instructions that teach AI coding agents its conventions, from its tests to its translations.",
      ),
      link: { label: gettext("Browse the skills"), url: GITHUB_URLS.skills },
    },
    {
      text: gettext(
        "Smarter was first used in a classroom in January 2026, by AI students at the University of British Columbia.",
      ),
      link: { label: gettext("Read the Instructor Guide"), url: DOCS_URLS.instructors },
    },
    {
      text: gettext(
        "Smarter has a Free Course Catalog of ready-to-teach courses, from prompt engineering for non-programmers to Kubernetes for platform engineers.",
      ),
      link: { label: gettext("Read the Instructor Guide"), url: DOCS_URLS.instructors },
    },
    {
      text: gettext(
        "Every Smarter account starts with two course advisors, stackademy_sql and stackademy_api, that answer from a private database and a web API with no code. A case study on smarter.sh teaches how they work.",
      ),
      link: { label: gettext("Read the case study"), url: SITE_URLS.stackademyCaseStudy },
    },
    {
      text: gettext(
        "The chat in the Prompt Engineer's Workbench is its own open source npm package, @smarter.sh/ui-chat, which you can embed in any website.",
      ),
      link: { label: gettext("See it on npm"), url: NPM_URLS.chat },
    },
    {
      text: gettext(
        "Claude Code translated Smarter's web console into Spanish, French and Brazilian Portuguese in a single day, October 16, 2026.",
      ),
      link: { label: gettext("Read about the translations"), url: DOCS_URLS.translations },
    },
    {
      text: gettext(
        "Smarter's ImageSearchPlugin was written by Claude Code during a live, in-class demonstration for AI students at the University of British Columbia. It went into production the following day.",
      ),
      link: { label: gettext("Read about the ImageSearchPlugin"), url: DOCS_URLS.imageSearch },
    },
    {
      text: gettext(
        "The web console speaks English, Spanish, French and Brazilian Portuguese. You can choose a language from the user menu.",
      ),
    },
    {
      text: gettext(
        "Smarter Chat has a WordPress plugin, a Drupal module and a Shopify app block, which put a deployed LLMClient on your site.",
      ),
      link: { label: gettext("Read about Smarter Chat"), url: DOCS_URLS.chat },
    },
    {
      text: gettext(
        "Smarter's manifests can be edited not only in the web console, but also in code editors such as VS Code.",
      ),
      link: { label: gettext("Read about the VS Code extension"), url: DOCS_URLS.vscode },
    },
    {
      text: gettext(
        "Smarter's VS Code extension checks your YAML manifests as you type, completes their keys and values, and fixes common mistakes.",
      ),
      link: { label: gettext("Read about the VS Code extension"), url: DOCS_URLS.vscode },
    },
    {
      text: gettext(
        "Smarter's command-line interface works much like kubectl and runs on Windows, macOS and Linux. Like the aws cli, you set it up with one command: smarter configure.",
      ),
      link: { label: gettext("Read about the command-line interface"), url: DOCS_URLS.cli },
    },
    {
      text: gettext("On a Mac, you can install the smarter command-line interface with Homebrew."),
      link: { label: gettext("Read about the command-line interface"), url: DOCS_URLS.cli },
    },
    {
      text: gettext(
        "Every Smarter platform publishes an OpenAPI document of its REST API, which SDKs and AI agents can read.",
      ),
      link: { label: gettext("Read about the OpenAPI document"), url: DOCS_URLS.openapi },
    },
    {
      text: gettext(
        "Smarter's server log messages are designed to help AI agents diagnose run-time errors: each one starts with the dotted path of the code that wrote it, so it reads like a stack trace.",
      ),
      link: { label: gettext("Read the logging style guide"), url: DOCS_URLS.logging },
    },
    {
      text: gettext(
        "Smarter has more than 50 Waffle switches that turn optional features and logging on and off, including whether these Did you know? notes appear.",
      ),
      link: { label: gettext("Read about the Waffle switches"), url: DOCS_URLS.waffle },
    },
    {
      text: gettext(
        "Smarter's authors invented their own object caching system, the @cache_results() decorator, which builds each cache key from the arguments of the function that it caches.",
      ),
      link: { label: gettext("Read about @cache_results()"), url: DOCS_URLS.cacheResults },
    },
    {
      text: gettext(
        "Smarter's authors created their own Django base model, MetaDataWithOwnershipModel, which gives each AI resource its name, description, version, tags and owner.",
      ),
      link: { label: gettext("Read its source code"), url: GITHUB_URLS.ownershipModel },
    },
    {
      text: gettext(
        "Smarter's version numbers and changelogs are generated from its commit messages, by semantic-release.",
      ),
      link: { label: gettext("See the releases"), url: GITHUB_URLS.releases },
    },
    {
      text: gettext(
        "Smarter's authors designed their own Django-React integration: Vite builds each page's React app, and a Django template tag mounts it.",
      ),
      link: { label: gettext("Read about the React integration"), url: DOCS_URLS.react },
    },
    {
      text: gettext(
        "Most pages of this web console are small React apps that Django hosts, and every one of their Storybook stories also runs as a unit test.",
      ),
      link: { label: gettext("Read about the React integration"), url: DOCS_URLS.react },
    },
    {
      text: gettext("Smarter is an open source project, and anyone can contribute to it, including you."),
      link: { label: gettext("Read how to contribute"), url: DOCS_URLS.contributing },
    },
    {
      text: gettext(
        "The Get Weather LLMClient's tool is a Smarter Extension written in Python. Beginning Python programmers can write extensions too.",
      ),
      link: { label: gettext("Read the extension developer guide"), url: DOCS_URLS.extensionGuide },
    },
    {
      text: gettext(
        "Smarter Extensions, such as weather, calculator and date-calculator, are published in a public registry on GitHub.",
      ),
      link: { label: gettext("Browse the extensions registry"), url: GITHUB_URLS.extensionsRegistry },
    },
    {
      text: gettext(
        "Smarter's Python docstrings are published, by Sphinx, as the technical reference of its documentation.",
      ),
      link: { label: gettext("Read the documentation"), url: DOCS_URLS.home },
    },
    {
      text: gettext(
        "The first drafts of the Sphinx docstrings of Smarter's Python modules, classes and functions were written with GitHub Copilot.",
      ),
      link: { label: gettext("Read the documentation"), url: DOCS_URLS.home },
    },
    {
      text: gettext("Agentic AI wrote more than 70% of Smarter's unit tests."),
      link: { label: gettext("Read the story"), url: BLOG_URLS.agenticAi },
    },
    {
      text: gettext("Smarter's first commit was made in February 2023."),
    },
  ];
}

/**
 * Picks a fact at random.
 *
 * :param random: A function that returns a number from 0 up to, but not including, 1.
 * :returns: The fact.
 */
export function randomFact(random: () => number = Math.random): DidYouKnowFact {
  const facts = didYouKnowFacts();
  return facts[Math.floor(random() * facts.length)];
}

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * The fact of the day: the same fact for everyone, from midnight to midnight UTC, and the next one
 * the next day.
 *
 * :param date: The moment whose day picks the fact.
 * :returns: The fact.
 */
export function factOfTheDay(date: Date = new Date()): DidYouKnowFact {
  const facts = didYouKnowFacts();
  const day = Math.floor(date.getTime() / DAY_MS);
  return facts[((day % facts.length) + facts.length) % facts.length];
}
