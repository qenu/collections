import discord
from .abc import MixinMeta
from typing import Optional

import tabulate
import calendar

from redbot.core import commands

class DevMixin(MixinMeta):
    """Dev Commands"""

    @commands.group(name="cookiedev")
    @commands.is_owner()
    async def cookiedev(self, ctx):
        """Cookie dev commands."""
        pass


    @cookiedev.command(name="massassign")
    async def cookiedev_massassign(self, ctx: commands.Context, *, data):
        """Set all data."""
        import ast
        data = ast.literal_eval(data)
        if isinstance(data, list):
            for user in data:
                await self.config.member_from_ids(guild_id=ctx.guild.id, member_id=user[0]).cookies.set(user[1])
            await ctx.send(f"Done, {len(data)} users updated.")
        else:
            await ctx.send("Data is not a list.")

    @cookiedev.command(name="resetcooldown")
    async def cookiedev_resetcooldown(self, ctx: commands.Context, user: discord.Member):
        """Reset user cooldown."""
        await self.config.member(user).next_cookie.set(0)
        await self.config.member(user).next_steal.set(0)
        await ctx.tick()

    @cookiedev.command(name="floor")
    async def cookiedev_floor(self, ctx: commands.Context):
        """Checks the cookies on the floor"""
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

        cookies = await self.config.channel(ctx.channel).cookies()
        time = await self.config.channel(ctx.channel).time()
        taken = await self.config.channel(ctx.channel).taken()
        dtime = self.display_time(cur_time-time)

        members = [ctx.guild.get_member(m) for m in taken]

        content = f"地板上有 {cookies} :cookie:\n掉落時間: {dtime}前\n"
        if members:
            content += f"目前有 {len(members)} 人已經撿取\n"
            content += "```yaml\n"
            for member in members:
                content += f"\t{member.display_name}"
            content += "```"
        embed = discord.Embed()
        embed.title = f"{ctx.channel.name} 地板"
        embed.color = await ctx.embed_colour()
        embed.description = content
        embed.set_footer(text=f"餅乾版本: {self.__version__} | 地板功能")

        await ctx.send(embed=embed)