#!/usr/bin/env python3
"""
Draw the diagram of docs/source/smarter-resources/llmtool/runner.rst: how an LLM tool call runs.

Usage: tool-runner-diagram.py [output folder]   (default: docs/source/_static, from the repository root)

- tool-runner.svg: a tool call resolved in the app (permissions, cache, the decrypted credential), handed to
  the tool runner as a serializable ToolCall, executed by its kind's executor without the database, and
  returned as a ToolCallResult.

It describes smarter.apps.llmtool.runner, and the tools that go through it (TOOL_EXECUTORS): keep it true when
a kind of tool moves behind the runner, or the runner moves into a worker (ADR-038). Edit the function, run the
script, and render the result to check it: rsvg-convert -w 1875 <svg> -o <scratchpad>/tool-runner.png.

It draws with the Diagram class of security-diagrams.py, loaded from beside this file, so that the diagrams
share one look and one copy of their drawing code.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static")


def load_security_diagrams():
    """Return the security-diagrams.py module, whose name isn't importable, writing to this script's folder."""
    path = os.path.join(HERE, "security-diagrams.py")
    spec = importlib.util.spec_from_file_location("security_diagrams", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # it reads its output folder from sys.argv when it loads, so it is given ours.
    saved_argv = sys.argv
    sys.argv = [path, OUT_DIR]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


security = load_security_diagrams()
Diagram = security.Diagram


def tool_runner():
    """How an LLM tool call is resolved in the app, run by the tool runner, and returned."""
    d = Diagram(
        "tool-runner",
        1300,
        930,
        "How an LLM tool call runs",
        "resolved in the app, where the credentials are; executed by the tool runner, without them (ADR-038)",
        "When the LLM asks for a tool, the tool's code in the app, such as MCPToolkit.call() or "
        "ApiConnection.execute_query(), checks the permissions and the cache. On a cache miss it resolves the call: "
        "it reads the credential from its Smarter Secret, decrypts it, signs the acting user, and builds a ToolCall, "
        "such as an MCPToolCall, an ApiToolCall, an HttpToolCall or a WebFetchToolCall, of plain values that travel "
        "as JSON. It hands the call to the tool runner, from get_tool_runner(), which finds the executor of the call's "
        "kind in TOOL_EXECUTORS: execute_mcp_call for MCP clients, execute_api_call for API plugins, "
        "execute_http_call for the web search apis (Brave, Tavily), the Brave image search, the checks of each image's "
        "url and websites' robots.txt, and execute_webfetch_call for the pages the web search plugin reads, with its "
        "domain policy and robots.txt checked again on each redirect. The executor reads no database and no Secret: "
        "it calls the MCP server, the api, the search api or the website, through safe_http, to public addresses "
        "only. It "
        "returns a ToolCallResult, with a value, is_error, failure and status_code, and the tool's code in the app "
        "sends the signals, stores the result in the cache, and gives it to the LLM. Today the runner executes the "
        "call in the app's process; in phase 2 of ADR-038 a remote runner sends the same call to a worker that holds "
        "no credentials.",
    )

    # 1. in the app
    d.heading(28, 100, 300, "1 · In the app")
    d.box(
        "llm",
        28,
        150,
        300,
        "The LLM's tool call",
        ["OpenAICompatibleChatProvider", "one call for each tool the LLM asks for"],
        code="process_tool_call()",
    )
    d.box(
        "toolkit",
        28,
        290,
        300,
        "The tool's code",
        ["checks the permissions", "checks the cache: a hit stops here", "sends the signals, caches, answers"],
        code="MCPToolkit · ApiConnection · plugins",
    )
    d.box(
        "resolve",
        28,
        450,
        300,
        "Resolve the call",
        ["decrypts the credential", "signs the acting user", "plain values, no database objects"],
        "core",
        code="MCPToolCall · ApiToolCall · ...",
    )
    d.box(
        "secrets",
        28,
        620,
        300,
        "Smarter Secrets",
        ["the credentials, encrypted"],
        "data",
        code="MariaDB · the Fernet key",
    )

    # 2. the boundary
    d.heading(380, 100, 250, "2 · The tool runner")
    d.box(
        "runner",
        380,
        300,
        250,
        "The tool runner",
        ["InProcessToolRunner today", "a remote runner in phase 2"],
        "core",
        code="get_tool_runner()",
    )
    d.box(
        "registry",
        380,
        440,
        250,
        "Executors, by kind",
        [
            "mcp: execute_mcp_call",
            "api: execute_api_call",
            "http: execute_http_call",
            "webfetch: execute_webfetch_call",
        ],
        code="TOOL_EXECUTORS",
    )
    d.box(
        "result",
        380,
        740,
        250,
        "ToolCallResult",
        ["value · is_error", "failure · status_code"],
        code="JSON",
    )

    # 3. execution, without the database
    d.heading(690, 100, 300, "3 · Execution")
    d.region(676, 166, 328, 524, "no database · no Secrets", note="in the app today; in a worker, phase 2")
    d.box(
        "exec_mcp",
        690,
        210,
        300,
        "execute_mcp_call()",
        ["checks the permissions again", "connects, calls, disconnects"],
        code="MCPServerConnection(endpoint=)",
    )
    d.box(
        "exec_api",
        690,
        330,
        300,
        "execute_api_call()",
        ["API plugins: the api's JSON, limited", "http or https, any port"],
        code="safe_http.fetch()",
    )
    d.box(
        "exec_http",
        690,
        450,
        300,
        "execute_http_call()",
        ["web search apis, image search,", "image checks, robots.txt"],
        code="safe_http.fetch()",
    )
    d.box(
        "exec_webfetch",
        690,
        570,
        300,
        "execute_webfetch_call()",
        ["a page that the LLM chose", "policy and robots.txt on each hop"],
        code="safe_http.fetch(redirect_policy=)",
    )

    # 4. the internet
    d.heading(1046, 100, 226, "4 · The internet")
    d.box("mcpservers", 1046, 210, 226, "MCP servers", ["the MCPClient's endpoint"], "outside", code="https · 443")
    d.box("apis", 1046, 330, 226, "APIs", ["the ApiConnection's base url"], "outside", code="http or https · any port")
    d.box(
        "searches",
        1046,
        450,
        226,
        "Search apis, image hosts",
        ["Brave, Tavily", "each image's own host"],
        "outside",
        code="https · 443",
    )
    d.box(
        "pages",
        1046,
        570,
        226,
        "Web pages",
        ["the pages the LLM reads", "and their robots.txt"],
        "outside",
        code="https · 443",
    )

    # the call, down the app
    d.arrow([d.bottom("llm"), d.top("toolkit")])
    d.arrow(
        [d.bottom("toolkit"), d.top("resolve")],
        "blue",
        label="on a cache miss",
        label_at=(190, 432),
        label_anchor="start",
    )
    d.arrow(
        [d.top("secrets"), d.bottom("resolve")],
        "green",
        label="read, decrypted",
        label_at=(190, 600),
        label_anchor="start",
    )

    # the call, across the boundary
    resolve_x, resolve_y = d.right("resolve")
    runner_x, runner_y = d.left("runner")
    d.arrow(
        [(resolve_x, resolve_y), (358, resolve_y), (358, runner_y), (runner_x, runner_y)],
        "blue",
        label="a ToolCall, as JSON",
        label_at=(392, 292),
        label_anchor="start",
    )
    d.arrow([d.bottom("runner"), d.top("registry")], label="by its kind", label_at=(515, 424), label_anchor="start")
    registry_x, registry_y = d.right("registry")
    for key in ("exec_mcp", "exec_api", "exec_http", "exec_webfetch"):
        exec_x, exec_y = d.left(key)
        d.arrow([(registry_x, registry_y), (660, registry_y), (660, exec_y), (exec_x, exec_y)])

    # out to the internet
    d.arrow([d.right("exec_mcp"), d.left("mcpservers")], "green")
    d.arrow([d.right("exec_api"), d.left("apis")], "green")
    d.arrow([d.right("exec_http"), d.left("searches")], "green")
    d.arrow([d.right("exec_webfetch"), d.left("pages")], "green")

    # the result, from either executor (the region's edge), back to the tool's code
    region_bottom_x = 676 + 328 / 2
    region_bottom_y = 166 + 524
    result_x, result_y = d.right("result")
    d.arrow(
        [(region_bottom_x, region_bottom_y), (region_bottom_x, result_y), (result_x, result_y)],
        "blue",
        dashed=True,
    )
    result_left_x, result_left_y = d.left("result")
    toolkit_x, toolkit_y = d.right("toolkit")
    d.arrow(
        [(result_left_x, result_left_y), (344, result_left_y), (344, toolkit_y), (toolkit_x, toolkit_y)],
        "blue",
        dashed=True,
    )

    d.legend(
        866,
        [
            ("blue", False, "the call"),
            ("blue", True, "its result"),
            ("green", False, "a credential, or a request that leaves the cluster"),
            ("grey", False, "in the same process"),
            (None, False, "where the runner will draw the line"),
        ],
    )
    d.save()


if __name__ == "__main__":
    tool_runner()
