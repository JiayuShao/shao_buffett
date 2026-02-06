"""AI Engine: model routing + agentic tool-use loop."""

import json
import asyncpg
import anthropic
import structlog
from typing import Any
from ai.models import ModelConfig, OPUS
from ai.router import route_request, record_opus_call
from ai.tools import FINANCIAL_TOOLS
from ai.conversation import ConversationManager
from ai.multimodal import process_attachments
from ai.prompts.system import BASE_SYSTEM_PROMPT, RESEARCH_SYSTEM_PROMPT
from config.settings import settings
from data.manager import DataManager

log = structlog.get_logger(__name__)

MAX_TOOL_ROUNDS = 10  # Max agentic tool-use iterations


class AIEngine:
    """Orchestrates Claude API calls with tool use and model routing."""

    def __init__(self, data_manager: DataManager, db_pool: asyncpg.Pool) -> None:
        self.data_manager = data_manager
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.conversation = ConversationManager(db_pool)

    async def chat(
        self,
        user_id: int,
        channel_id: int,
        content: str,
        attachments: list[Any] | None = None,
        force_model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Handle a chat message with tool-use agentic loop.

        Returns the final text response.
        """
        model_config = route_request(content, force_tier=force_model)

        # Build user context
        profile = await self.conversation.get_user_profile(user_id)
        watchlist = await self.conversation.get_user_watchlist(user_id)
        history = await self.conversation.get_history(user_id, channel_id)

        # Build system prompt with user context
        sys_prompt = system_prompt or BASE_SYSTEM_PROMPT
        if watchlist:
            sys_prompt += f"\n\nUser's watchlist: {', '.join(watchlist)}"
        if profile.get("focused_metrics"):
            metrics = profile["focused_metrics"]
            if isinstance(metrics, list):
                sys_prompt += f"\nUser's focused metrics: {', '.join(metrics)}"
        if profile.get("risk_tolerance"):
            sys_prompt += f"\nUser's risk tolerance: {profile['risk_tolerance']}"

        # Build messages
        messages: list[dict[str, Any]] = []
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append(msg)

        # Build current user message with potential attachments
        user_content: list[dict[str, Any]] | str
        if attachments:
            user_content = [{"type": "text", "text": content}]
            attachment_blocks = await process_attachments(attachments)
            user_content.extend(attachment_blocks)
        else:
            user_content = content

        messages.append({"role": "user", "content": user_content})

        # Save user message
        await self.conversation.save_message(user_id, channel_id, "user", content)

        # Agentic tool-use loop
        response_text = await self._run_tool_loop(
            model_config=model_config,
            system_prompt=sys_prompt,
            messages=messages,
        )

        # Track Opus usage
        if model_config == OPUS:
            record_opus_call()

        # Save assistant response
        await self.conversation.save_message(
            user_id, channel_id, "assistant", response_text, model_config.model_id
        )

        return response_text

    async def analyze(
        self,
        prompt: str,
        force_model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Run a one-shot analysis (no conversation history).

        Used by processors, scheduler, etc.
        """
        model_config = route_request(prompt, force_tier=force_model)
        messages = [{"role": "user", "content": prompt}]

        return await self._run_tool_loop(
            model_config=model_config,
            system_prompt=system_prompt or BASE_SYSTEM_PROMPT,
            messages=messages,
        )

    async def _run_tool_loop(
        self,
        model_config: ModelConfig,
        system_prompt: str,
        messages: list[dict[str, Any]],
    ) -> str:
        """Execute the agentic tool-use loop until the model stops calling tools."""
        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await self.client.messages.create(
                    model=model_config.model_id,
                    max_tokens=model_config.max_tokens,
                    system=system_prompt,
                    messages=messages,
                    tools=FINANCIAL_TOOLS,
                )
            except anthropic.APIError as e:
                log.error("anthropic_api_error", error=str(e), model=model_config.model_id)
                return f"Sorry, I encountered an API error: {e.message}"

            # Check if the model wants to use tools
            if response.stop_reason == "tool_use":
                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                # Add assistant message and tool results to continue the loop
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Model is done — extract text response
                text_parts = [
                    block.text for block in response.content if hasattr(block, "text")
                ]
                return "\n".join(text_parts) if text_parts else "I wasn't able to generate a response."

        return "I reached the maximum number of analysis steps. Here's what I found so far."

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute a financial data tool and return the result."""
        log.info("tool_call", tool=tool_name, input=tool_input)

        try:
            match tool_name:
                case "get_quote":
                    return await self.data_manager.get_quote(tool_input["symbol"])
                case "get_company_profile":
                    return await self.data_manager.get_company_profile(tool_input["symbol"])
                case "get_fundamentals":
                    return await self.data_manager.get_fundamentals(tool_input["symbol"])
                case "get_analyst_data":
                    return await self.data_manager.get_analyst_data(tool_input["symbol"])
                case "get_earnings":
                    return await self.data_manager.get_earnings(tool_input["symbol"])
                case "get_news":
                    return await self.data_manager.get_news(
                        symbol=tool_input.get("symbol"),
                        limit=tool_input.get("limit", 5),
                    )
                case "get_macro_data":
                    return await self.data_manager.get_macro_data(
                        series_id=tool_input.get("series_id")
                    )
                case "get_sector_performance":
                    return await self.data_manager.get_sector_performance()
                case "get_earnings_transcript":
                    return await self.data_manager.get_earnings_transcript(
                        tool_input["symbol"],
                        tool_input["year"],
                        tool_input["quarter"],
                    )
                case "get_sec_filings":
                    return await self.data_manager.get_sec_filings(
                        tool_input["symbol"],
                        form_types=tool_input.get("form_types"),
                    )
                case "get_research_papers":
                    return await self.data_manager.get_research_papers(
                        query=tool_input.get("query"),
                        max_results=tool_input.get("max_results", 10),
                    )
                case "generate_chart":
                    # Chart generation is handled separately — return a placeholder
                    return {"status": "chart_requested", "params": tool_input}
                case _:
                    return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            log.error("tool_error", tool=tool_name, error=str(e))
            return {"error": f"Tool '{tool_name}' failed: {str(e)}"}
