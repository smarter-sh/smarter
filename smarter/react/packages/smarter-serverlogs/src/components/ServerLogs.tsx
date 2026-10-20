/**
 * The server log viewer: the user's server logs, as they stream in. The workbench's Console and the
 * Prompt Passthrough render it in their "Server Logs" tabs, with the records of useLogStream()
 * (src/lib/logStream.ts).
 *
 * The records are displayed as the Smarter web console's terminal displays them: their text, with
 * its ANSI colors, in the terminal's palette and font. Their text already has their time and level.
 * Long lines scroll horizontally, unless the user wraps them. Blocks of pretty-printed JSON, which
 * can be hundreds of lines long, are collapsed, each with a toggle, and the toolbar expands or
 * collapses them all. See src/lib/logJson.ts.
 *
 * The viewer has the keyboard shortcuts of src/lib/logViewerKeys.ts while it has the focus: w wraps,
 * s follows the newest record, / filters, Ctrl+Up and Ctrl+Down move to the top and the bottom, and
 * so on. "?" lists them.
 */
import { Fragment, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { gettext, interpolate, ngettext } from "@smarter/common";

import { ansiCss, parseAnsi, stripAnsi, type AnsiSegment } from "../lib/ansi";
import { hasJsonBlock, logNodes, type LogNode } from "../lib/logJson";
import type { LogEvent } from "../lib/logStream";
import { LOG_VIEWER_SHORTCUTS, logViewerAction, type LogViewerAction } from "../lib/logViewerKeys";
import { useLogWrap } from "../lib/logWrap";
import ToolbarButton from "./ToolbarButton";

import "../styles.css";

export interface ServerLogsProps {
  logs: LogEvent[];
  connected: boolean;
  error: string | null;
  /** The status while there is no stream yet, e.g. before the first prompt. */
  idleText?: string | null;
}

// the stream's own status messages, which older records in its history may have. These are the
// server's, in English.
const SUPPRESSED_LINES = new Set(["Waiting for log stream...", "[stream] connected"]);

/** How far the arrow keys scroll, in pixels: about a line, and a few characters. */
const LINE_HEIGHT = 18;
const COLUMN_WIDTH = 40;
/** How close to the bottom, in pixels, counts as the bottom, so that new records are followed. */
const BOTTOM_SLACK = 4;
const COPIED_MILLISECONDS = 1500;

function shortcutLabel(action: LogViewerAction): string {
  switch (action) {
    case "top":
      return gettext("Top");
    case "bottom":
      return gettext("Bottom, and follow new records");
    case "lineUp":
      return gettext("Up a line");
    case "lineDown":
      return gettext("Down a line");
    case "pageUp":
      return gettext("Up a page");
    case "pageDown":
      return gettext("Down a page");
    case "left":
      return gettext("Scroll left");
    case "right":
      return gettext("Scroll right");
    case "lineStart":
      return gettext("Start of the lines");
    case "lineEnd":
      return gettext("End of the longest line");
    case "wrap":
      return gettext("Wrap long lines, or scroll them");
    case "follow":
      return gettext("Follow new records, or stop");
    case "filter":
      return gettext("Filter the lines");
    case "copy":
      return gettext("Copy the lines");
    case "fullscreen":
      return gettext("Full screen, or not");
    case "help":
      return gettext("Show these shortcuts, or hide them");
    case "escape":
      return gettext("Leave full screen, hide the shortcuts, or clear the filter");
  }
}

function status(props: ServerLogsProps, shown: number, total: number, filter: string): string {
  if (props.error) return props.error;
  if (props.idleText) return props.idleText;
  if (!props.connected) return gettext("Connecting to the server log stream...");
  if (filter) return interpolate(gettext("%(shown)s of %(total)s lines match."), { shown, total });
  return total > 0 ? gettext("Streaming server logs...") : gettext("Streaming server logs... There are none yet.");
}

function Segments({ segments }: { segments: AnsiSegment[] }) {
  return segments.map((segment, index) => (
    <span key={index} style={ansiCss(segment.style)}>
      {segment.text}
    </span>
  ));
}

function JsonBlock({ node, expandAll }: { node: Extract<LogNode, { kind: "block" }>; expandAll: boolean }) {
  const [expanded, setExpanded] = useState(expandAll);
  const closing = node.close
    .map((segment) => segment.text)
    .join("")
    .trim();
  return (
    <>
      <Segments segments={node.open} />
      <button
        type="button"
        className="console-log-json-toggle"
        aria-expanded={expanded}
        aria-label={expanded ? gettext("Collapse the JSON") : gettext("Expand the JSON")}
        title={expanded ? gettext("Collapse the JSON") : gettext("Expand the JSON")}
        onClick={() => setExpanded((previous) => !previous)}
      >
        {expanded ? "\u2212" : "+"}
      </button>
      {expanded ? (
        <>
          {"\n"}
          <LogNodes nodes={node.children} expandAll={expandAll} />
          {"\n"}
          <Segments segments={node.close} />
        </>
      ) : (
        <span className="console-log-json-summary">
          {" \u2026 "}
          {closing}{" "}
          <span className="console-log-json-count">
            {interpolate(ngettext("(%(count)s line)", "(%(count)s lines)", node.lines), { count: node.lines })}
          </span>
        </span>
      )}
    </>
  );
}

function LogNodes({ nodes, expandAll }: { nodes: LogNode[]; expandAll: boolean }) {
  return nodes.map((node, index) => (
    <Fragment key={index}>
      {index > 0 && "\n"}
      {node.kind === "line" ? <Segments segments={node.segments} /> : <JsonBlock node={node} expandAll={expandAll} />}
    </Fragment>
  ));
}

function LogLine({ message, expandAll }: { message: string; expandAll: boolean }) {
  const nodes = useMemo(() => logNodes(message), [message]);
  return (
    <div className="console-log-line">
      {hasJsonBlock(nodes) ? (
        <LogNodes nodes={nodes} expandAll={expandAll} />
      ) : (
        <Segments segments={parseAnsi(message)} />
      )}
    </div>
  );
}

function ServerLogs(props: ServerLogsProps) {
  const [wrap, setWrap] = useLogWrap();
  const [follow, setFollow] = useState(true);
  const [filter, setFilter] = useState("");
  const [help, setHelp] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  // the blocks of JSON are collapsed, until the user expands them, one by one, or all of them.
  const [expandAll, setExpandAll] = useState(false);
  const [expandGeneration, setExpandGeneration] = useState(0);
  const linesRef = useRef<HTMLDivElement | null>(null);
  const filterRef = useRef<HTMLInputElement | null>(null);

  const messages = useMemo(
    () => props.logs.map((log) => String(log.message ?? "")).filter((line) => !SUPPRESSED_LINES.has(line.trim())),
    [props.logs],
  );
  const shownMessages = useMemo(() => {
    const query = filter.trim().toLowerCase();
    return query ? messages.filter((line) => stripAnsi(line).toLowerCase().includes(query)) : messages;
  }, [messages, filter]);

  // follow the newest record, while following. Before the browser paints, so that the lines don't jump.
  useLayoutEffect(() => {
    const lines = linesRef.current;
    if (follow && lines) lines.scrollTop = lines.scrollHeight;
  }, [follow, shownMessages, wrap, fullscreen]);

  const onScroll = () => {
    const lines = linesRef.current;
    if (!lines) return;
    // scrolling up stops following. Scrolling back to the bottom follows again.
    setFollow(lines.scrollHeight - lines.scrollTop - lines.clientHeight <= BOTTOM_SLACK);
  };

  const copy = () => {
    const text = shownMessages.map(stripAnsi).join("\n");
    navigator.clipboard
      ?.writeText(text)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), COPIED_MILLISECONDS);
      })
      .catch(() => {
        // e.g. the page isn't allowed to write to the clipboard. The lines can still be selected.
      });
  };

  const toggleExpandAll = () => {
    setExpandAll((previous) => !previous);
    // each block starts again from the new state, whichever way the user toggled it.
    setExpandGeneration((generation) => generation + 1);
  };

  const escape = () => {
    if (fullscreen) setFullscreen(false);
    else if (help) setHelp(false);
    else setFilter("");
  };

  const perform = (action: LogViewerAction) => {
    const lines = linesRef.current;
    if (!lines) return;
    const page = Math.max(lines.clientHeight - LINE_HEIGHT, LINE_HEIGHT);
    switch (action) {
      case "top":
        setFollow(false);
        lines.scrollTop = 0;
        break;
      case "bottom":
        setFollow(true);
        lines.scrollTop = lines.scrollHeight;
        break;
      case "lineUp":
        lines.scrollTop -= LINE_HEIGHT;
        break;
      case "lineDown":
        lines.scrollTop += LINE_HEIGHT;
        break;
      case "pageUp":
        lines.scrollTop -= page;
        break;
      case "pageDown":
        lines.scrollTop += page;
        break;
      case "left":
        lines.scrollLeft -= COLUMN_WIDTH;
        break;
      case "right":
        lines.scrollLeft += COLUMN_WIDTH;
        break;
      case "lineStart":
        lines.scrollLeft = 0;
        break;
      case "lineEnd":
        lines.scrollLeft = lines.scrollWidth;
        break;
      case "wrap":
        setWrap((previous) => !previous);
        break;
      case "follow":
        setFollow((previous) => !previous);
        break;
      case "filter":
        filterRef.current?.focus();
        break;
      case "copy":
        copy();
        break;
      case "fullscreen":
        setFullscreen((previous) => !previous);
        break;
      case "help":
        setHelp((previous) => !previous);
        break;
      case "escape":
        escape();
        break;
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const action = logViewerAction(event);
    if (!action) return;
    event.preventDefault();
    perform(action);
  };

  const onFilterKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Escape" && event.key !== "Enter") return;
    event.preventDefault();
    // Escape clears the filter, and Enter keeps it. Either returns to the lines.
    if (event.key === "Escape") setFilter("");
    linesRef.current?.focus();
  };

  const className = [
    "console-server-logs",
    wrap ? "console-server-logs-wrap" : "",
    fullscreen ? "console-server-logs-fullscreen" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <div className="console-server-logs-toolbar">
        <p className="mb-0 console-server-logs-status" role="status">
          {status(props, shownMessages.length, messages.length, filter.trim())}
        </p>
        <div className="console-server-logs-controls">
          <input
            ref={filterRef}
            type="search"
            className="console-server-logs-filter"
            aria-label={gettext("Filter the server logs")}
            placeholder={gettext("Filter (/)")}
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            onKeyDown={onFilterKeyDown}
          />
          <ToolbarButton
            icon="wrap"
            label={gettext("Wrap lines")}
            title={wrap ? gettext("Scroll long lines (w)") : gettext("Wrap long lines (w)")}
            pressed={wrap}
            onClick={() => setWrap((previous) => !previous)}
            showLabel
          />
          <ToolbarButton
            icon="expandJson"
            label={gettext("Expand JSON")}
            title={expandAll ? gettext("Collapse all the JSON") : gettext("Expand all the JSON")}
            pressed={expandAll}
            onClick={toggleExpandAll}
            showLabel
          />
          <ToolbarButton
            icon="follow"
            label={gettext("Follow")}
            title={follow ? gettext("Stop following new records (s)") : gettext("Follow new records (s)")}
            pressed={follow}
            onClick={() => perform(follow ? "follow" : "bottom")}
            showLabel
          />
          <ToolbarButton
            icon="copy"
            label={copied ? gettext("Copied") : gettext("Copy the lines")}
            title={copied ? gettext("Copied") : gettext("Copy the lines (c)")}
            onClick={copy}
          />
          <ToolbarButton
            icon="fullscreen"
            label={gettext("Full screen")}
            title={fullscreen ? gettext("Leave full screen (F, Esc)") : gettext("Full screen (F)")}
            pressed={fullscreen}
            onClick={() => setFullscreen((previous) => !previous)}
          />
          <ToolbarButton
            icon="help"
            label={gettext("Keyboard shortcuts")}
            title={gettext("Keyboard shortcuts (?)")}
            pressed={help}
            onClick={() => setHelp((previous) => !previous)}
          />
        </div>
      </div>
      {help && (
        <dl className="console-server-logs-help" aria-label={gettext("Keyboard shortcuts")}>
          {LOG_VIEWER_SHORTCUTS.map(({ keys, action }) => (
            <div key={action} className="console-server-logs-help-item">
              <dt>
                {keys.map((key) => (
                  <kbd key={key}>{key}</kbd>
                ))}
              </dt>
              <dd>{shortcutLabel(action)}</dd>
            </div>
          ))}
        </dl>
      )}
      {/* the lines are focusable, so that the keyboard scrolls them, and has their shortcuts. */}
      {/* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex -- a scrollable log must be focusable to be scrolled with the keyboard. */}
      <div
        ref={linesRef}
        className="console-server-logs-lines"
        role="log"
        aria-label={gettext("Server logs")}
        tabIndex={0}
        onKeyDown={onKeyDown}
        onScroll={onScroll}
      >
        {shownMessages.map((message, index) => (
          <LogLine key={`${expandGeneration}-${index}`} message={message} expandAll={expandAll} />
        ))}
      </div>
      {/* eslint-enable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}
    </div>
  );
}

export default ServerLogs;
