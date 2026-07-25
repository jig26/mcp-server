"""
MCP server (Streamable HTTP transport) exposing exactly one tool:
solve_challenge.

The tool takes no meaningful input (its schema has no properties/required
fields) and instead reads the per-call exam headers directly off the raw
HTTP request for that specific tools/call — not from the JSON-RPC body —
because the grader issues a fresh X-Exam-Challenge on every call within
the same session.

Why this is safe to read per-call rather than per-connection:
the official MCP Python SDK threads the actual Starlette `Request` for
each individual JSON-RPC message through `ctx.request_context.request`,
so even though tools/list and the five tools/call requests all belong to
one logical MCP session, each one is its own HTTP POST and this handler
sees that specific request's headers, not a cached copy from initialize.

stateless_http=True: every request is handled independently (no server-side
session store), which also happens to match how serverless platforms like
Vercel invoke functions — there's no guarantee two calls land on the same
process.
json_response=True: respond with a single application/json body instead of
opening an SSE stream, since solve_challenge only ever returns one message.
"""

import hashlib

from mcp.server.fastmcp import Context, FastMCP

REGISTERED_EMAIL = "25f1001599@ds.study.iitm.ac.in".strip().lower()

mcp = FastMCP(
    "exam-solver",
    instructions="Exposes solve_challenge, which answers a per-call exam challenge read from HTTP headers.",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def solve_challenge(ctx: Context) -> str:
    """Compute the exam answer for this call's X-Exam-Challenge header.

    Takes no arguments. Reads X-Exam-Challenge from the raw HTTP request for
    this specific call and returns the first 16 hex characters of
    SHA-256("{challenge}:{registered_email}").
    """
    request = ctx.request_context.request
    challenge = ""
    if request is not None:
        challenge = request.headers.get("x-exam-challenge") or ""

    digest = hashlib.sha256(f"{challenge}:{REGISTERED_EMAIL}".encode("utf-8")).hexdigest()
    return digest[:16]


# ASGI app Vercel's Python runtime serves directly.
app = mcp.streamable_http_app()
