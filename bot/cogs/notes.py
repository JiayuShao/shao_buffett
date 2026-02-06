"""Slash commands for viewing and managing conversation notes."""

import discord
from discord.ext import commands
from storage.repositories.notes_repo import NotesRepository
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor


class NotesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    notes = discord.SlashCommandGroup("notes", "Manage your conversation notes")

    @notes.command(description="Show your recent notes")
    async def show(
        self,
        ctx: discord.ApplicationContext,
        note_type: discord.Option(  # type: ignore[valid-type]
            str,
            "Filter by type",
            choices=["all", "insight", "decision", "action_item", "preference", "concern"],
            required=False,
            default="all",
        ),
        limit: discord.Option(int, "Number of notes", required=False, default=10, min_value=1, max_value=25),  # type: ignore[valid-type]
    ) -> None:
        repo = NotesRepository(self.bot.db_pool)

        if note_type == "all":
            notes = await repo.get_recent(ctx.author.id, limit=limit)
        else:
            notes = await repo.get_by_type(ctx.author.id, note_type, limit=limit)

        if not notes:
            await ctx.respond(
                embed=make_embed("Your Notes", "No notes found. Chat with me and I'll take notes automatically!", color=EmbedColor.INFO),
                ephemeral=True,
            )
            return

        type_emoji = {
            "insight": "💡",
            "decision": "✅",
            "action_item": "📋",
            "preference": "⚙️",
            "concern": "⚠️",
        }

        lines = []
        for n in notes:
            emoji = type_emoji.get(n["note_type"], "📝")
            resolved = " ~~(resolved)~~" if n["is_resolved"] else ""
            symbols = f" [{', '.join(n['symbols'])}]" if n["symbols"] else ""
            date = n["created_at"].strftime("%m/%d")
            content = n["content"][:120] + "..." if len(n["content"]) > 120 else n["content"]
            lines.append(f"{emoji} `#{n['id']}` {date}{symbols}{resolved}\n{content}")

        embed = make_embed(
            f"Your Notes ({len(notes)})",
            "\n\n".join(lines),
            color=EmbedColor.INFO,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @notes.command(description="Show your open action items")
    async def actions(self, ctx: discord.ApplicationContext) -> None:
        repo = NotesRepository(self.bot.db_pool)
        items = await repo.get_active_action_items(ctx.author.id)

        if not items:
            await ctx.respond(
                embed=make_embed("Action Items", "No open action items.", color=EmbedColor.SUCCESS),
                ephemeral=True,
            )
            return

        lines = []
        for item in items:
            symbols = f" [{', '.join(item['symbols'])}]" if item["symbols"] else ""
            date = item["created_at"].strftime("%m/%d")
            lines.append(f"📋 `#{item['id']}` {date}{symbols}\n{item['content']}")

        embed = make_embed(
            f"Open Action Items ({len(items)})",
            "\n\n".join(lines),
            color=EmbedColor.WARNING,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @notes.command(description="Resolve an action item")
    async def resolve(
        self,
        ctx: discord.ApplicationContext,
        note_id: discord.Option(int, "Note ID to resolve"),  # type: ignore[valid-type]
    ) -> None:
        repo = NotesRepository(self.bot.db_pool)
        resolved = await repo.resolve_action_item(note_id, ctx.author.id)

        if resolved:
            await ctx.respond(
                embed=make_embed("Resolved", f"Action item #{note_id} marked as resolved.", color=EmbedColor.SUCCESS),
                ephemeral=True,
            )
        else:
            await ctx.respond(
                embed=error_embed(f"Could not resolve note #{note_id}. Check the ID and ensure it's your action item."),
                ephemeral=True,
            )

    @notes.command(description="Delete a note")
    async def delete(
        self,
        ctx: discord.ApplicationContext,
        note_id: discord.Option(int, "Note ID to delete"),  # type: ignore[valid-type]
    ) -> None:
        repo = NotesRepository(self.bot.db_pool)
        deleted = await repo.delete(note_id, ctx.author.id)

        if deleted:
            await ctx.respond(
                embed=make_embed("Deleted", f"Note #{note_id} deleted.", color=EmbedColor.SUCCESS),
                ephemeral=True,
            )
        else:
            await ctx.respond(
                embed=error_embed(f"Could not delete note #{note_id}. Check the ID."),
                ephemeral=True,
            )


def setup(bot: commands.Bot) -> None:
    bot.add_cog(NotesCog(bot))
