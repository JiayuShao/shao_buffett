"""Discord UI views — pagination for long content."""

import discord


class PaginatorView(discord.ui.View):
    """Paginator for long embed lists."""

    def __init__(self, embeds: list[discord.Embed], author_id: int, timeout: float = 120) -> None:
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.author_id = author_id
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= len(self.embeds) - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="◀")
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your pagination.", ephemeral=True)
            return
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        embed = self.embeds[self.current_page]
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)} • Shao Buffett")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶")
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your pagination.", ephemeral=True)
            return
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self._update_buttons()
        embed = self.embeds[self.current_page]
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)} • Shao Buffett")
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True


class ConfirmView(discord.ui.View):
    """Confirmation dialog with Yes/No buttons."""

    def __init__(self, author_id: int, timeout: float = 30) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed: bool | None = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your action.", ephemeral=True)
            return
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your action.", ephemeral=True)
            return
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)
