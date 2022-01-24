import discord
from .abc import MixinMeta, _MAX_BALANCE
from typing import Optional
from redbot.core import commands, bank
import datetime
import typing
from redbot.core.utils.predicates import MessagePredicate
import asyncio


class SettingsMixin(MixinMeta):
    """Settings commands"""

    @commands.group(autohelp=True)
    @commands.admin()
    @commands.guild_only()
    async def cookieset(self, ctx):
        """餅乾設定"""

    @cookieset.command(name="gg")
    @commands.is_owner()
    async def cookieset_gg(
        self,
        ctx: commands.Context,
        make_global: bool,
        confirmation: typing.Optional[bool],
    ):
        """Switch from per-guild to global cookies and vice versa."""
        if await self.config.is_global() == make_global:
            return await ctx.send("Uh oh, you're not really changing anything.")
        if not confirmation:
            return await ctx.send(
                "This will delete **all** current settings. This action **cannot** be undone.\n"
                f"If you're sure, type `{ctx.clean_prefix}cookieset gg <make_global> yes`."
            )
        await self.config.clear_all_members()
        await self.config.clear_all_users()
        await self.config.clear_all_guilds()
        await self.config.clear_all_globals()
        await self.config.is_global.set(make_global)
        await ctx.send(f"Cookies are now {'global' if make_global else 'per-guild'}.")

    @cookieset.command(name="amount")
    async def cookieset_amount(self, ctx: commands.Context, amount: int):
        """Set the amount of cookies members can obtain.

        If 0, members will get a random amount."""
        if amount < 0:
            return await ctx.send("Uh oh, the amount cannot be negative.")
        if self._max_balance_check(amount):
            return await ctx.send(
                f"Uh oh, you can't set an amount of cookies greater than {_MAX_BALANCE:,}."
            )
        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )
        await conf.amount.set(amount)
        if amount != 0:
            return await ctx.send(f"Members will receive {amount} cookies.")

        pred = MessagePredicate.valid_int(ctx)
        await ctx.send("What's the minimum amount of cookies members can obtain?")
        try:
            await self.bot.wait_for("message", timeout=30, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long. Try again, please.")
        minimum = pred.result
        await conf.minimum.set(minimum)

        await ctx.send("What's the maximum amount of cookies members can obtain?")
        try:
            await self.bot.wait_for("message", timeout=30, check=pred)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long. Try again, please.")
        maximum = pred.result
        await conf.maximum.set(maximum)

        await ctx.send(
            f"Members will receive a random amount of cookies between {minimum} and {maximum}."
        )

    @cookieset.command(name="cooldown", aliases=["cd"])
    async def cookieset_cd(self, ctx: commands.Context, seconds: int):
        """Set the cooldown for `[p]cookie`.

        This is in seconds! Default is 43200 seconds (12 hours)."""
        if seconds <= 0:
            return await ctx.send("Uh oh, cooldown has to be more than 0 seconds.")
        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )
        await conf.cooldown.set(seconds)
        await ctx.send(f"Set the cooldown to {seconds} seconds.")

    @cookieset.command(name="stealcooldown", aliases=["stealcd"])
    async def cookieset_stealcd(self, ctx: commands.Context, seconds: int):
        """Set the cooldown for `[p]steal`.

        This is in seconds! Default is 43200 seconds (12 hours)."""
        if seconds <= 0:
            return await ctx.send("Uh oh, cooldown has to be more than 0 seconds.")
        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )
        await conf.stealcd.set(seconds)
        await ctx.send(f"Set the cooldown to {seconds} seconds.")

    @cookieset.command(name="steal")
    async def cookieset_steal(
        self, ctx: commands.Context, on_off: typing.Optional[bool]
    ):
        """Toggle cookie stealing for current server.

        If `on_off` is not provided, the state will be flipped."""
        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )
        target_state = on_off or not (await conf.stealing())
        await conf.stealing.set(target_state)
        if target_state:
            await ctx.send("Stealing is now enabled.")
        else:
            await ctx.send("Stealing is now disabled.")

    @cookieset.command(name="set")
    async def cookieset_set(
        self, ctx: commands.Context, target: discord.Member, amount: int
    ):
        """Set someone's amount of cookies."""
        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        if self._max_balance_check(amount):
            return await ctx.send(
                f"Uh oh, amount can't be greater than {_MAX_BALANCE:,}."
            )
        um_conf = (
            self.config.user(target)
            if await self.config.is_global()
            else self.config.member(target)
        )
        await um_conf.cookies.set(amount)
        await ctx.send(f"Set {target.mention}'s balance to {amount} :cookie:")

    @cookieset.command(name="add")
    async def cookieset_add(
        self, ctx: commands.Context, target: discord.Member, amount: int
    ):
        """Add cookies to someone."""
        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        um_conf = (
            self.config.user(target)
            if await self.config.is_global()
            else self.config.member(target)
        )
        target_cookies = await um_conf.cookies()
        if self._max_balance_check(target_cookies + amount):
            return await ctx.send(
                f"Uh oh, {target.display_name} has reached the maximum amount of cookies."
            )
        await self.deposit_cookies(target, amount)
        await ctx.send(f"Added {amount} :cookie: to {target.mention}'s balance.")

    @cookieset.command(name="take")
    async def cookieset_take(
        self, ctx: commands.Context, target: discord.Member, amount: int
    ):
        """Take cookies away from someone."""
        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        um_conf = (
            self.config.user(target)
            if await self.config.is_global()
            else self.config.member(target)
        )
        target_cookies = await um_conf.cookies()
        if amount <= target_cookies:
            await self.withdraw_cookies(target, amount)
            return await ctx.send(
                f"Took away {amount} :cookie: from {target.mention}'s balance."
            )
        await ctx.send(f"{target.mention} doesn't have enough :cookies:")

    @cookieset.command(name="reset")
    async def cookieset_reset(
        self, ctx: commands.Context, confirmation: typing.Optional[bool]
    ):
        """Delete all cookies from all members."""
        if not confirmation:
            return await ctx.send(
                "This will delete **all** cookies from all members. This action **cannot** be undone.\n"
                f"If you're sure, type `{ctx.clean_prefix}cookieset reset yes`."
            )
        if await self.config.is_global():
            await self.config.clear_all_users()
        else:
            await self.config.clear_all_members(ctx.guild)
        await ctx.send("All cookies have been deleted from all members.")

    @cookieset.command(name="rate")
    async def cookieset_rate(
        self, ctx: commands.Context, rate: typing.Union[int, float]
    ):
        """Set the exchange rate for `[p]cookieexchange`."""
        if rate <= 0:
            return await ctx.send("Uh oh, rate has to be more than 0.")
        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )
        await conf.rate.set(rate)
        currency = await bank.get_currency_name(ctx.guild)
        test_amount = 100 * rate
        await ctx.send(
            f"Set the exchange rate {rate}. This means that 100 {currency} will give you {test_amount} :cookie:"
        )

    @cookieset.command(name="settings")
    async def cookieset_settings(self, ctx: commands.Context):
        """See current settings."""
        is_global = await self.config.is_global()
        data = (
            await self.config.all()
            if is_global
            else await self.config.guild(ctx.guild).all()
        )

        amount = data["amount"]
        amount = (
            str(amount)
            if amount != 0
            else f"random amount between {data['minimum']} and {data['maximum']}"
        )

        stealing = data["stealing"]
        stealing = "Enabled" if stealing else "Disabled"

        embed = discord.Embed(
            colour=await ctx.embed_colour(), timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.title = "**__Cookies settings:__**"
        embed.set_footer(text="*required to function properly")

        embed.add_field(name="Global:", value=str(is_global))
        embed.add_field(name="Exchange rate:", value=str(data["rate"]))
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Amount:", value=amount)
        embed.add_field(name="Cooldown:", value=self.display_time(data["cooldown"]))
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Stealing:", value=stealing)
        embed.add_field(name="Cooldown:", value=self.display_time(data["stealcd"]))

        await ctx.send(embed=embed)

    @cookieset.group(autohelp=True)
    async def role(self, ctx):
        """Cookie rewards for roles."""
        pass

    @role.command(name="add")
    async def cookieset_role_add(
        self, ctx: commands.Context, role: discord.Role, amount: int
    ):
        """Set cookies for role."""
        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        await self.config.role(role).cookies.set(amount)
        await ctx.send(f"Gaining {role.name} will now give {amount} :cookie:")

    @role.command(name="del")
    async def cookieset_role_del(self, ctx: commands.Context, role: discord.Role):
        """Delete cookies for role."""
        await self.config.role(role).cookies.set(0)
        await ctx.send(f"Gaining {role.name} will now not give any :cookie:")

    @role.command(name="show")
    async def cookieset_role_show(self, ctx: commands.Context, role: discord.Role):
        """Show how many cookies a role gives."""
        cookies = int(await self.config.role(role).cookies())
        await ctx.send(f"Gaining {role.name} gives {cookies} :cookie:")

    @role.command(name="multiplier")
    async def cookieset_role_multiplier(
        self, ctx: commands.Context, role: discord.Role, multiplier: int
    ):
        """Set cookies multipler for role. Disabled when random amount is enabled.

        Default is 1 (aka the same amount)."""
        if multiplier <= 0:
            return await ctx.send("Uh oh, multiplier has to be more than 0.")
        await self.config.role(role).multiplier.set(multiplier)
        await ctx.send(
            f"Users with {role.name} will now get {multiplier} times more :cookie:"
        )
