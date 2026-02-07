"""AI Engine: model routing + agentic tool-use loop."""

import json
import asyncpg
import anthropic
import structlog
from typing import Any, Callable, Awaitable
from ai.models import ModelConfig, OPUS
from ai.router import route_request, record_opus_call
from ai.tools import FINANCIAL_TOOLS
from ai.conversation import ConversationManager
from ai.multimodal import process_attachments
from ai.prompts.system import BASE_SYSTEM_PROMPT, RESEARCH_SYSTEM_PROMPT
from config.settings import settings
from data.manager import DataManager
from storage.repositories.notes_repo import NotesRepository

log = structlog.get_logger(__name__)

MAX_TOOL_ROUNDS = 10  # Max agentic tool-use iterations


class AIEngine:
    """Orchestrates Claude API calls with tool use and model routing."""

    def __init__(self, data_manager: DataManager, db_pool: asyncpg.Pool) -> None:
        self.data_manager = data_manager
        self.db_pool = db_pool
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.conversation = ConversationManager(db_pool)
        self.notes_repo = NotesRepository(db_pool)

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
        # Summarize old messages if conversation is getting long
        await self.conversation.summarize_if_needed(user_id, channel_id, self)

        # Build user context
        profile = await self.conversation.get_user_profile(user_id)
        watchlist = await self.conversation.get_user_watchlist(user_id)
        history = await self.conversation.get_history(user_id, channel_id)

        # Check if user has portfolio for smarter routing
        has_portfolio = False
        try:
            from storage.repositories.portfolio_repo import PortfolioRepository
            portfolio_repo = PortfolioRepository(self.db_pool)
            portfolio_symbols = await portfolio_repo.get_symbols(user_id)
            has_portfolio = len(portfolio_symbols) > 0
        except Exception:
            pass

        model_config = route_request(content, force_tier=force_model, has_portfolio=has_portfolio)

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
        if profile.get("interests"):
            interests = profile["interests"]
            if isinstance(interests, dict) and interests.get("sectors"):
                sys_prompt += f"\nUser's sector interests: {', '.join(interests['sectors'])}"

        # Inject conversation notes for cross-conversation memory
        sys_prompt = await self._inject_user_context(user_id, sys_prompt)

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
            user_id=user_id,
        )

        # Track Opus usage
        if model_config == OPUS:
            record_opus_call()

        # Save assistant response
        await self.conversation.save_message(
            user_id, channel_id, "assistant", response_text, model_config.model_id
        )

        # Log user activity for proactive insight generation
        await self._log_activity(user_id, content)

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

    async def chat_stream(
        self,
        user_id: int,
        channel_id: int,
        content: str,
        attachments: list[Any] | None = None,
        on_tool_start: Callable[[str, dict], Awaitable[None]] | None = None,
        on_text_chunk: Callable[[str], Awaitable[None]] | None = None,
        send_file: Callable | None = None,
    ) -> str:
        """Handle a chat message with streaming final response and tool progress.

        Same setup as chat() but uses _run_tool_loop_stream() for real-time feedback.
        """
        await self.conversation.summarize_if_needed(user_id, channel_id, self)

        profile = await self.conversation.get_user_profile(user_id)
        watchlist = await self.conversation.get_user_watchlist(user_id)
        history = await self.conversation.get_history(user_id, channel_id)

        has_portfolio = False
        try:
            from storage.repositories.portfolio_repo import PortfolioRepository
            portfolio_repo = PortfolioRepository(self.db_pool)
            portfolio_symbols = await portfolio_repo.get_symbols(user_id)
            has_portfolio = len(portfolio_symbols) > 0
        except Exception:
            pass

        model_config = route_request(content, has_portfolio=has_portfolio)

        sys_prompt = BASE_SYSTEM_PROMPT
        if watchlist:
            sys_prompt += f"\n\nUser's watchlist: {', '.join(watchlist)}"
        if profile.get("focused_metrics"):
            metrics = profile["focused_metrics"]
            if isinstance(metrics, list):
                sys_prompt += f"\nUser's focused metrics: {', '.join(metrics)}"
        if profile.get("risk_tolerance"):
            sys_prompt += f"\nUser's risk tolerance: {profile['risk_tolerance']}"
        if profile.get("interests"):
            interests = profile["interests"]
            if isinstance(interests, dict) and interests.get("sectors"):
                sys_prompt += f"\nUser's sector interests: {', '.join(interests['sectors'])}"

        sys_prompt = await self._inject_user_context(user_id, sys_prompt)

        messages: list[dict[str, Any]] = []
        for msg in history[-10:]:
            messages.append(msg)

        user_content: list[dict[str, Any]] | str
        if attachments:
            user_content = [{"type": "text", "text": content}]
            attachment_blocks = await process_attachments(attachments)
            user_content.extend(attachment_blocks)
        else:
            user_content = content

        messages.append({"role": "user", "content": user_content})
        await self.conversation.save_message(user_id, channel_id, "user", content)

        response_text = await self._run_tool_loop_stream(
            model_config=model_config,
            system_prompt=sys_prompt,
            messages=messages,
            user_id=user_id,
            on_tool_start=on_tool_start,
            on_text_chunk=on_text_chunk,
            send_file=send_file,
        )

        if model_config == OPUS:
            record_opus_call()

        await self.conversation.save_message(
            user_id, channel_id, "assistant", response_text, model_config.model_id
        )
        await self._log_activity(user_id, content)

        return response_text

    async def _run_tool_loop_stream(
        self,
        model_config: ModelConfig,
        system_prompt: str,
        messages: list[dict[str, Any]],
        user_id: int | None = None,
        on_tool_start: Callable[[str, dict], Awaitable[None]] | None = None,
        on_text_chunk: Callable[[str], Awaitable[None]] | None = None,
        send_file: Callable | None = None,
    ) -> str:
        """Tool-use loop with streaming on the final text generation round."""
        system_blocks = [
            {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        cached_tools = list(FINANCIAL_TOOLS)
        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                create_params: dict[str, Any] = {
                    "model": model_config.model_id,
                    "max_tokens": model_config.max_tokens + (model_config.thinking_budget or 0),
                    "system": system_blocks,
                    "messages": messages,
                    "tools": cached_tools,
                }
                if model_config.thinking_budget:
                    create_params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": model_config.thinking_budget,
                    }

                # Non-streaming call first to check if tools are needed
                response = await self.client.messages.create(**create_params)

            except anthropic.APIError as e:
                log.error("anthropic_api_error", error=str(e), model=model_config.model_id)
                return f"Sorry, I encountered an API error: {e.message}"

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        if on_tool_start:
                            await on_tool_start(block.name, block.input)
                        result = await self._execute_tool(
                            block.name, block.input, user_id=user_id, send_file=send_file,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Final text round — stream it if we have a callback
                text_parts = [
                    block.text for block in response.content if block.type == "text"
                ]
                final_text = "\n".join(text_parts) if text_parts else "I wasn't able to generate a response."

                if on_text_chunk:
                    # Send the final text in chunks to simulate streaming
                    # (We already have the complete response from the non-streaming call)
                    await on_text_chunk(final_text)

                return final_text

        return "I reached the maximum number of analysis steps. Here's what I found so far."

    async def _run_tool_loop(
        self,
        model_config: ModelConfig,
        system_prompt: str,
        messages: list[dict[str, Any]],
        user_id: int | None = None,
        send_file: Any = None,
    ) -> str:
        """Execute the agentic tool-use loop until the model stops calling tools."""
        # Prompt caching: wrap system prompt and mark last tool for caching
        system_blocks = [
            {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        cached_tools = list(FINANCIAL_TOOLS)
        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                create_params: dict[str, Any] = {
                    "model": model_config.model_id,
                    "max_tokens": model_config.max_tokens + (model_config.thinking_budget or 0),
                    "system": system_blocks,
                    "messages": messages,
                    "tools": cached_tools,
                }
                # Extended thinking for Sonnet/Opus
                if model_config.thinking_budget:
                    create_params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": model_config.thinking_budget,
                    }
                response = await self.client.messages.create(**create_params)
            except anthropic.APIError as e:
                log.error("anthropic_api_error", error=str(e), model=model_config.model_id)
                return f"Sorry, I encountered an API error: {e.message}"

            # Check if the model wants to use tools
            if response.stop_reason == "tool_use":
                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(
                            block.name, block.input, user_id=user_id, send_file=send_file,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                # Add assistant message and tool results to continue the loop
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Model is done — extract text response (filter thinking blocks)
                text_parts = [
                    block.text for block in response.content
                    if block.type == "text"
                ]
                return "\n".join(text_parts) if text_parts else "I wasn't able to generate a response."

        return "I reached the maximum number of analysis steps. Here's what I found so far."

    async def _log_activity(self, user_id: int, content: str) -> None:
        """Log user activity for proactive insight generation."""
        try:
            import re
            from storage.repositories.activity_repo import ActivityRepository

            # Extract mentioned symbols (uppercase 1-5 letter words that look like tickers)
            symbols = re.findall(r'\b([A-Z]{1,5})\b', content)
            # Filter common English words that look like tickers
            noise = {"I", "A", "THE", "AND", "OR", "FOR", "IN", "ON", "AT", "TO", "IS", "IT", "AN", "OF", "MY", "AM", "DO", "IF", "SO", "NO", "UP", "VS"}
            symbols = [s for s in symbols if s not in noise]

            # Classify query type
            content_lower = content.lower()
            if any(w in content_lower for w in ["price", "quote", "how much"]):
                query_type = "price_check"
            elif any(w in content_lower for w in ["analyze", "analysis", "research"]):
                query_type = "analysis"
            elif any(w in content_lower for w in ["macro", "gdp", "cpi", "fed", "inflation", "rate"]):
                query_type = "macro"
            elif any(w in content_lower for w in ["news", "headline", "latest"]):
                query_type = "news"
            elif any(w in content_lower for w in ["earnings", "eps", "revenue"]):
                query_type = "earnings"
            elif any(w in content_lower for w in ["buy", "sell", "hold", "portfolio"]):
                query_type = "portfolio_decision"
            else:
                query_type = "general"

            repo = ActivityRepository(self.db_pool)
            await repo.log_activity(user_id, query_type, symbols[:10])
        except Exception as e:
            log.debug("activity_log_error", error=str(e))

    async def _inject_user_context(self, user_id: int, sys_prompt: str) -> str:
        """Inject user's notes and portfolio into the system prompt."""
        try:
            # Fetch recent notes
            recent_notes = await self.notes_repo.get_recent(user_id, limit=15)
            action_items = await self.notes_repo.get_active_action_items(user_id)

            if recent_notes:
                notes_text = "\n## Your Notes About This User\n"
                for n in recent_notes:
                    symbols = f" [{', '.join(n['symbols'])}]" if n['symbols'] else ""
                    notes_text += f"- [{n['note_type']}]{symbols} {n['content']}\n"
                sys_prompt += notes_text

            if action_items:
                items_text = "\n## Open Action Items\n"
                for item in action_items:
                    symbols = f" [{', '.join(item['symbols'])}]" if item['symbols'] else ""
                    items_text += f"- #{item['id']}{symbols}: {item['content']}\n"
                sys_prompt += items_text

            # Fetch portfolio holdings if available
            try:
                from storage.repositories.portfolio_repo import PortfolioRepository, FinancialProfileRepository
                portfolio_repo = PortfolioRepository(self.db_pool)
                profile_repo = FinancialProfileRepository(self.db_pool)

                holdings = await portfolio_repo.get_holdings(user_id)
                fin_profile = await profile_repo.get(user_id)

                if holdings:
                    portfolio_text = "\n## User's Portfolio Holdings\n"
                    for h in holdings:
                        cost = f" @ ${h['cost_basis']:.2f}" if h.get('cost_basis') else ""
                        acct = f" ({h['account_type']})" if h.get('account_type') else ""
                        portfolio_text += f"- {h['symbol']}: {h['shares']} shares{cost}{acct}\n"
                    sys_prompt += portfolio_text

                if fin_profile:
                    profile_parts = []
                    if fin_profile.get("investment_horizon"):
                        profile_parts.append(f"Investment horizon: {fin_profile['investment_horizon']}")
                    if fin_profile.get("tax_bracket"):
                        profile_parts.append(f"Tax bracket: {fin_profile['tax_bracket']}")
                    if fin_profile.get("goals"):
                        goals = fin_profile["goals"]
                        if isinstance(goals, list):
                            profile_parts.append(f"Goals: {', '.join(goals)}")
                    if profile_parts:
                        sys_prompt += "\n## User's Financial Profile\n" + "\n".join(f"- {p}" for p in profile_parts) + "\n"
            except ImportError:
                pass  # Portfolio repo not yet created (Phase 2)

        except Exception as e:
            log.warning("context_injection_error", error=str(e))

        return sys_prompt

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any], user_id: int | None = None, send_file: Any = None) -> Any:
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
                case "get_polymarket":
                    return await self.data_manager.get_polymarket(
                        query=tool_input["query"],
                        limit=tool_input.get("limit", 5),
                    )
                case "get_technical_indicators":
                    return await self.data_manager.get_technical_indicators(tool_input["symbol"])
                case "generate_chart":
                    if not send_file:
                        return {"status": "charts unavailable in this context"}
                    from dashboard.generator import DashboardGenerator
                    generator = DashboardGenerator(self.data_manager)
                    files = await generator.generate_chart(
                        chart_type=tool_input["chart_type"],
                        symbols=tool_input.get("symbols"),
                        series_id=tool_input.get("series_id"),
                        title=tool_input.get("title"),
                    )
                    for f in files:
                        await send_file(f)
                    return {"status": "chart_sent", "chart_type": tool_input["chart_type"]}

                # --- Personal Analyst Tools ---
                case "save_note":
                    if not user_id:
                        return {"error": "No user context for note-taking"}
                    note_id = await self.notes_repo.add(
                        discord_id=user_id,
                        note_type=tool_input["note_type"],
                        content=tool_input["content"],
                        symbols=tool_input.get("symbols"),
                    )
                    return {"status": "saved", "note_id": note_id, "type": tool_input["note_type"]}

                case "get_user_notes":
                    if not user_id:
                        return {"error": "No user context"}
                    if tool_input.get("query"):
                        return await self.notes_repo.search(user_id, tool_input["query"])
                    if tool_input.get("symbols"):
                        return await self.notes_repo.get_for_symbols(user_id, tool_input["symbols"])
                    if tool_input.get("note_type"):
                        return await self.notes_repo.get_by_type(user_id, tool_input["note_type"])
                    return await self.notes_repo.get_recent(user_id)

                case "resolve_action_item":
                    if not user_id:
                        return {"error": "No user context"}
                    resolved = await self.notes_repo.resolve_action_item(tool_input["note_id"], user_id)
                    return {"resolved": resolved, "note_id": tool_input["note_id"]}

                case "get_portfolio":
                    if not user_id:
                        return {"error": "No user context"}
                    from storage.repositories.portfolio_repo import PortfolioRepository
                    repo = PortfolioRepository(self.db_pool)
                    return await repo.get_holdings(user_id)

                case "update_portfolio":
                    if not user_id:
                        return {"error": "No user context"}
                    from storage.repositories.portfolio_repo import PortfolioRepository
                    repo = PortfolioRepository(self.db_pool)
                    action = tool_input.get("action", "add")
                    if action == "remove":
                        removed = await repo.remove(
                            user_id, tool_input["symbol"],
                            account_type=tool_input.get("account_type", "taxable"),
                        )
                        return {"status": "removed" if removed else "not_found", "symbol": tool_input["symbol"]}
                    else:
                        await repo.upsert(
                            discord_id=user_id,
                            symbol=tool_input["symbol"],
                            shares=tool_input.get("shares", 0),
                            cost_basis=tool_input.get("cost_basis"),
                            account_type=tool_input.get("account_type", "taxable"),
                            notes=tool_input.get("notes"),
                        )
                        return {"status": "updated", "symbol": tool_input["symbol"], "shares": tool_input.get("shares")}

                case "get_financial_profile":
                    if not user_id:
                        return {"error": "No user context"}
                    from storage.repositories.portfolio_repo import FinancialProfileRepository
                    repo = FinancialProfileRepository(self.db_pool)
                    return await repo.get(user_id) or {"status": "no_profile"}

                case "update_financial_profile":
                    if not user_id:
                        return {"error": "No user context"}
                    from storage.repositories.portfolio_repo import FinancialProfileRepository
                    repo = FinancialProfileRepository(self.db_pool)
                    await repo.upsert(
                        discord_id=user_id,
                        annual_income=tool_input.get("annual_income"),
                        investment_horizon=tool_input.get("investment_horizon"),
                        goals=tool_input.get("goals"),
                        tax_bracket=tool_input.get("tax_bracket"),
                        monthly_investment=tool_input.get("monthly_investment"),
                    )
                    return {"status": "updated"}

                case _:
                    return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            log.error("tool_error", tool=tool_name, error=str(e))
            return {"error": f"Tool '{tool_name}' failed: {str(e)}"}
