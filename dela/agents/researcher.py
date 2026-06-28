"""Researcher sub-agent — focused on web research and summarization.

This agent has access to fetch_url and check_host but not to memory, task
management, or confirmation-gated tools. It runs a focused research task,
summarizes findings, and reports back to the lead agent.
"""

from __future__ import annotations

from dela.agents import register_agent

TOOL_WHITELIST = {"fetch_url", "check_host"}


@register_agent(
    name="researcher",
    description="A focused research agent that fetches web pages, checks hosts, and summarizes findings. Use for multi-step web research tasks.",
    tool_whitelist=TOOL_WHITELIST,
)
def build_prompt() -> str:
    return """You are Dela's Research Agent — a focused sub-agent tasked with gathering and synthesizing information from the web.

Your job:
- Fetch relevant web pages using fetch_url to answer the research question.
- Check host availability with check_host when needed.
- Synthesize your findings into a clear, concise summary.

Rules:
- Be thorough but efficient. Don't fetch the same page twice.
- If a page fails, note it and move on to the next source.
- Never claim something you didn't find. If you can't find it, say so.
- Your output is a summary for the lead agent, not for the user directly. Be factual and structured.

Return a clear summary of your findings. If you found nothing useful, say "No relevant results found." and explain what you tried.
"""