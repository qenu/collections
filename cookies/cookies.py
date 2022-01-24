import asyncio
import contextlib
import discord
import random
import calendar
import typing
import datetime
from abc import ABC

from redbot.core import Config, commands, bank, errors
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from redbot.core.bot import Red

from .dev import DevMixin
from .settings import SettingsMixin


_MAX_BALANCE = 2 ** 63 - 1


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    pass


class Cookies(
    DevMixin,
    SettingsMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
    ):
    """
    收集還有偷取餅乾的遊戲
    """

    __version__ = "1.3.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=16548964843212314, force_registration=True
        )
        self.config.register_guild(
            amount=2,
            minimum=0,
            maximum=0,
            cooldown=21600,
            stealing=False,
            stealcd=3600,
            rate=0.5,
        )
        self.config.register_global(
            is_global=False,
            amount=2,
            minimum=0,
            maximum=0,
            cooldown=21600,
            stealing=False,
            stealcd=3600,
            rate=0.5,
        )

        self.config.register_member(cookies=0, next_cookie=0, next_steal=0)
        self.config.register_user(cookies=0, next_cookie=0, next_steal=0)

        self.config.register_role(cookies=0, multiplier=1)

        self.config.register_channel(cookies=0, time=0, taken=[])

    async def red_delete_data_for_user(self, *, requester, user_id):
        await self.config.user_from_id(user_id).clear()
        for guild in self.bot.guilds:
            await self.config.member_from_ids(guild.id, user_id).clear()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        context = super().format_help_for_context(ctx)
        return f"{context}\n\nVersion: {self.__version__}"

    @commands.command(aliases=["餅乾"])
    @commands.guild_only()
    async def cookie(self, ctx: commands.Context):
        """獲得每日餅乾"""
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

        if await self.config.is_global():
            conf = self.config
            um_conf = self.config.user(ctx.author)
        else:
            conf = self.config.guild(ctx.guild)
            um_conf = self.config.member(ctx.author)

        amount = await conf.amount()
        cookies = await um_conf.cookies()
        next_cookie = await um_conf.next_cookie()
        minimum = await conf.minimum()
        maximum = await conf.maximum()
        error_str = ""
        result_str = ""

        if cur_time >= next_cookie:
            if amount == 0:
                amount = int(random.choice(list(range(minimum, maximum))))

            multipliers = []
            for role in ctx.author.roles:
                role_multiplier = await self.config.role(role).multiplier()
                if not role_multiplier:
                    role_multiplier = 1
                multipliers.append(role_multiplier)
            amount *= max(multipliers)
            result_str = f"給你{amount}片 :cookie:"
            if remain := self._max_balance_check(cookies + amount):
                if remain == 0:
                    error_str = "你無法再獲得更多的餅乾。 :frowning:"
                else:
                    error_str = f"由於你的餅乾數量已達上限，你只能獲得 {remain} 片 :cookie:"
                    amount = remain
            next_cookie = cur_time + await conf.cooldown()
            await um_conf.next_cookie.set(next_cookie)
            await self.deposit_cookies(ctx.author, amount)
        else:
            dtime = self.display_time(next_cookie - cur_time)
            error_str = f"你還需要等待 `{dtime}` 才能拿到 :cookie:"

        cookies = await um_conf.cookies()
        embed = discord.Embed()
        embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.color=ctx.author.color
        embed.description = error_str or result_str
        embed.set_footer(text=f"餅乾版本: {self.__version__} | 你目前擁有 {cookies} 片餅乾")
        await ctx.send(embed=embed)

    @commands.command(aliases=["ccd", "冷卻"])
    @commands.guild_only()
    async def cookiecooldown(self, ctx: commands.Context):
        """查看餅乾相關冷卻時間"""
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

        if await self.config.is_global():
            conf = self.config
            um_conf = self.config.user(ctx.author)
        else:
            conf = self.config.guild(ctx.guild)
            um_conf = self.config.member(ctx.author)
        next_steal = await um_conf.next_steal()
        next_cookie = await um_conf.next_cookie()

        if cur_time >= next_cookie:
            cresult = "你已經可以獲得餅乾了!"
        else:
            dtime = self.display_time(next_cookie - cur_time)
            cresult = f"於 `{dtime}` 後可以獲得 :cookie:"

        if cur_time >= next_steal:
            sresult = "你已經準備好可以偷餅乾了!"
        else:
            dtime = self.display_time(next_steal - cur_time)
            sresult = f"再 `{dtime}` 後就可以偷 :cookie:"

        embed = discord.Embed()
        embed.color = ctx.author.color
        embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="餅乾", value=cresult, inline=False)
        embed.add_field(name="偷餅乾", value=sresult, inline=False)
        embed.set_footer(text=f"餅乾版本: {self.__version__} | {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["偷餅乾","偷"], usage="[@目標成員]")
    @commands.guild_only()
    async def steal(
        self, ctx: commands.Context, *, target: typing.Optional[discord.Member]
    ):
        """當一個餅乾小偷。"""
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

        if await self.config.is_global():
            conf = self.config
            um_conf = self.config.user(ctx.author)
        else:
            conf = self.config.guild(ctx.guild)
            um_conf = self.config.member(ctx.author)

        next_steal = await um_conf.next_steal()
        next_cookie = await um_conf.next_cookie()
        enabled = await conf.stealing()
        author_cookies = await um_conf.cookies()

        if not enabled:
            return await ctx.send("這個伺服器沒有開放偷餅乾...")
        if cur_time < next_steal:
            dtime = self.display_time(next_steal - cur_time)
            return await ctx.send(f"你還要再等待`{dtime}`才能偷餅乾。")
        if cur_time > next_cookie:
            return await ctx.send("你還沒領取你的餅乾欸，先領完餅乾再來偷吧!")

        if not target:
            # target can only be from the same server
            ids = await self._get_ids(ctx)
            while target is None or target.id == ctx.author.id:
                target_id = random.choice(ids)
                target = ctx.guild.get_member(target_id)

        elif target.id == ctx.author.id:
            return await ctx.reply("你不能偷自己的 :cookie:。", mention_author=False)
        if await self.config.is_global():
            target_cookies = await self.config.user(target).cookies()
        else:
            target_cookies = await self.config.member(target).cookies()
        if target_cookies == 0:
            return await ctx.send(
                f"{target.display_name} 身上沒有任何的 :cookie:, 要不要試試看偷別人?"
            )

        await um_conf.next_steal.set(cur_time + await conf.stealcd())

        if random.choice([True, False]):
            cookies_stolen = max(int(target_cookies * 0.4), 1)
            if crit := (random.random() < 0.08): # 8% crit chance
                stolen = random.randint(max(int(target_cookies*0.4), 1), max(int(target_cookies*0.6), 1))
            else:
                stolen = random.randint(1, cookies_stolen)
            if self._max_balance_check(author_cookies + stolen):
                return await ctx.send(
                    "你的餅乾罐罐已經裝不下更多餅乾了 :frowning:\n"
                    f"{ctx.author.display_name} 沒有從 {target.display_name} 偷到更多的 :cookie:。"
                )
            await self.deposit_cookies(ctx.author, stolen)
            await self.withdraw_cookies(target, stolen)
            if crit:
                await um_conf.next_steal.set(cur_time)
                await ctx.send(
                    f"{ctx.author.display_name} 從 {target.display_name} 偷了一大堆餅乾!!\n"
                    f"拿到了{stolen}片 :cookie: 以及一次額外的偷餅乾機會!"
                    )
            else:
                await ctx.send(
                    f"{ctx.author.display_name} 從 {target.display_name} 偷了 {stolen} 片 :cookie:!"
                )
            return

        cookies_penalty = max(int(author_cookies * 0.25), 1)
        if author_cookies == 0:
            return await ctx.send(
                f"{ctx.author.display_name} 想偷餅乾的時候被 {target.display_name} 抓到了!\n"
                f"不過因為你沒有任何餅乾，所以你沒有失去任何 :cookie:。"
            )
        penalty = random.randint(1, cookies_penalty)
        if author_cookies < penalty:
            penalty = author_cookies
        if self._max_balance_check(target_cookies + penalty):
            return await ctx.send(
                f"{ctx.author.display_name} 想偷餅乾的時候被 {target.display_name} 抓到了!\n"
                f"不過因為 {target.display_name} 的餅乾罐頭已經滿了，"
                "你沒有失去任何 :cookie:。"
            )
        await self.withdraw_cookies(ctx.author, penalty)
        refund = random.randint(1, penalty)
        await self.deposit_cookies(target, refund)

        await ctx.send(
            content=(
                f"{ctx.author.display_name} 想偷餅乾的時候被 {target.display_name} 抓到了!\n"
                f"慌忙逃跑的你掉落了{penalty}片 :cookie:\n"
                f"{target.display_name}在地板上撿到了 {refund}片餅乾!"
            )
        )

        # cookies dropped
        await self.config.channel(ctx.channel).cookies.set(penalty-refund)
        await self.config.channel(ctx.channel).time.set(cur_time)
        taken = []
        taken.append(target.id)
        await self.config.channel(ctx.channel).taken.set(taken)


    @commands.command(aliases=["送餅乾", "給餅乾", "給"], usage="<@成員> <數量>")
    @commands.guild_only()
    async def give(self, ctx: commands.Context, target: discord.Member, amount: int):
        """給予一些好吃的餅乾。"""
        um_conf = (
            self.config.user(ctx.author)
            if await self.config.is_global()
            else self.config.member(ctx.author)
        )

        author_cookies = await um_conf.cookies()
        if amount <= 0:
            return await ctx.send("給人的餅乾數量必須大於 0。")
        if target.id == ctx.author.id:
            return await ctx.send("好喔?")
        if target._user.bot:
            return await ctx.send("機器人不能吃餅乾。")
        if amount > author_cookies:
            return await ctx.send("你沒有那麼多的餅乾。")
        target_cookies = await self.config.member(target).cookies()
        if self._max_balance_check(target_cookies + amount):
            return await ctx.send(
                f"{target.display_name} 的餅乾罐罐已經滿了..."
            )
        await self.withdraw_cookies(ctx.author, amount)
        penalty = random.randint(0, amount) if amount < 10 else int(amount*0.2 + 3)
        await self.deposit_cookies(target, amount-penalty)
        if penalty == 0:
            return await ctx.send(f"{ctx.author.mention}給了 {target.mention} {amount} 片 :cookie:!")

        result = random.choice(
            [(
                f"{ctx.author.mention} 想給 {target.name} {amount} 片 :cookie:!\n"
                f"但是有 {penalty}片被{self.bot.user.name}給偷吃掉了!\n"
                f"{target.mention}拿到了 {amount-penalty}片餅乾!"
            ),
            (
                f"{ctx.author.mention} 想給 {target.name} {amount} 片 :cookie:!\n"
                f"但是有 {penalty}片被勞贖了! <:mice:928960429621936138>\n"
                f"{target.mention}拿到了 {amount-penalty}片餅乾!"
            ),
            (
                f"{ctx.author.mention} 想給 {target.name} {amount} 片 :cookie:!\n"
                f"路過的浣熊偷偷拿走了幾片... <:smugcoon:912536731927076915>\n"
                f"{target.mention}拿到了 {amount-penalty}片餅乾!"
            )]
        )
        await ctx.send(content=result)

    @commands.command(aliases=["jar", "餅乾罐", "罐罐"], usage="[@成員]")
    @commands.guild_only()
    async def cookies(
        self, ctx: commands.Context, *, target: typing.Optional[discord.Member]
    ):
        """檢查你有多少餅乾。"""
        embed = discord.Embed()
        if not target:
            um_conf = (
                self.config.user(ctx.author)
                if await self.config.is_global()
                else self.config.member(ctx.author)
            )
            cookies = await um_conf.cookies()
            embed.set_author(icon_url=ctx.author.avatar_url, name=ctx.author.display_name)
            embed.description = f"你的罐子裡有 {cookies} 片 :cookie:"
        else:
            um_conf = (
                self.config.user(target)
                if await self.config.is_global()
                else self.config.member(target)
            )
            cookies = await um_conf.cookies()
            embed.set_author(icon_url=target.avatar_url, name=target.display_name)
            embed.description = f"{target.display_name} 有 {cookies} 片 :cookie:"

        embed.set_footer(text=f"餅乾版本: {self.__version__} | 查看餅乾罐子")
        embed.color = ctx.author.color
        await ctx.send(embed=embed)

    @commands.command(aliases=["撿", "撿餅乾", "puc"])
    @commands.guild_only()
    async def pickup(self, ctx: commands.Context):
        """在地板上找找看有沒有餅乾。"""
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

        um_conf = (
            self.config.user(ctx.author)
            if await self.config.is_global()
            else self.config.member(ctx.author)
        )
        cookies = await um_conf.cookies()
        drops = await self.config.channel(ctx.channel).cookies()
        age = await self.config.channel(ctx.channel).time()
        taken = await self.config.channel(ctx.channel).taken()

        if drops == 0:
            return await ctx.send("地板上沒有任何餅乾... :frowning:")
        if (cur_time - age) > 180:
            await self.config.channel(ctx.channel).cookies.set(0)
            return await ctx.send("地板上的餅乾看起來已經不能吃了，還是不要撿了吧...")
        if ctx.author.id in taken:
            return await ctx.send("你已經撿過這裡的餅乾了... :thinking:")
        if self._max_balance_check(cookies):
            return await ctx.send("你無法再獲得更多的餅乾。 :frowning:")

        await self.config.channel(ctx.channel).cookies.set(drops-1)
        await self.deposit_cookies(ctx.author, 1)

        await ctx.send(f"你在地板上撿到了一片餅乾，現在你有 {cookies+1} 片 :cookie:!")
        taken.append(ctx.author.id)
        await self.config.channel(ctx.channel).taken.set(taken)

    @commands.command(hidden=True)
    @commands.guild_only()
    async def exchange(
        self,
        ctx: commands.Context,
        amount: int,
        to_currency: typing.Optional[bool] = False,
    ):
        """餅乾交易所"""
        if amount <= 0:
            return await ctx.send("數量必須大於零。")

        conf = (
            self.config
            if await self.config.is_global()
            else self.config.guild(ctx.guild)
        )

        rate = await conf.rate()
        currency = await bank.get_currency_name(ctx.guild)

        if not await self._can_spend(to_currency, ctx.author, amount):
            return await ctx.send(f"你太窮了，買不起餅乾。")

        if not to_currency:
            await bank.withdraw_credits(ctx.author, amount)
            new_cookies = int(amount * rate)
            if self._max_balance_check(new_cookies):
                return await ctx.send(f"你的餅乾罐罐太滿了，無法購買更多的餅乾。")
            await self.deposit_cookies(ctx.author, new_cookies)
            return await ctx.send(
                f"你付出 {amount} {currency} ，購買了 {new_cookies} 片 :cookie:"
            )
        new_currency = int(amount / rate)
        try:
            await bank.deposit_credits(ctx.author, new_currency)
        except errors.BalanceTooHigh:
            return await ctx.send(f"你的銀行太滿了，無法販賣更多的餅乾。")
        await self.withdraw_cookies(ctx.author, amount)
        return await ctx.send(
            f"你販賣了 {amount} 片 :cookie: ，獲得 {new_currency} {currency}"
        )

    @commands.command(aliases=["餅乾排行", "餅乾排名", "clb"])
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        """查看伺服器餅乾排行榜。"""
        ids = await self._get_ids(ctx)
        lst = []
        pos = 1
        author_pos = 0
        cookiesum = 0
        pound_len = len(str(len(ids)))
        header = "{pound:{pound_len}}{score:{bar_len}}{name:2}\n".format(
            pound="#",
            name="使用者名稱",
            score="餅乾",
            pound_len=pound_len + 3,
            bar_len=pound_len + 9,
        )
        temp_msg = header
        is_global = await self.config.is_global()
        for a_id in ids:
            a = self.bot.get_user(a_id) if is_global else ctx.guild.get_member(a_id)
            if not a:
                continue
            name = a.display_name
            cookies = (
                await self.config.user(a).cookies()
                if is_global
                else await self.config.member(a).cookies()
            )
            if cookies == 0:
                continue
            if a_id != ctx.author.id:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} {cookies: <{pound_len+8}} {name}\n"
                )
            else:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} "
                    f"{cookies: <{pound_len+8}} "
                    f"<<{name}>>\n"
                )
                author_pos = pos
            if pos % 10 == 0:
                lst.append(box(temp_msg, lang="md"))
                temp_msg = header
            cookiesum += cookies
            pos += 1

        if temp_msg != header:
            lst.append(box(temp_msg, lang="md"))

        embedded_lst = []
        for item in lst:
            info = f"{ctx.guild.name} 餅乾排行榜\n\n"
            embed = discord.Embed(title=info, description=item, color=ctx.author.color)
            embed.set_footer(text=f"餅乾版本: {self.__version__} | 共 {cookiesum}片餅乾")
            embed.set_author(icon_url=ctx.author.avatar_url, name=f"{ctx.author.display_name} ({author_pos}/{pos})")
            embedded_lst.append(embed)

        if embedded_lst:
            if len(embedded_lst) > 1:
                await menu(ctx, embedded_lst, DEFAULT_CONTROLS)
            else:
                await ctx.send(embed=embedded_lst[0])
        else:
            info = f"{ctx.guild.name} 餅乾排行榜\n\n"
            embed = discord.Embed(title=info, description=box("(以下空白)", lang="md"), color=ctx.author.color)
            embed.set_footer(text=f"餅乾版本: {self.__version__} | 共 {cookiesum} :cookie:")
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        b = set(before.roles)
        a = set(after.roles)
        after_roles = [list(a - b)][0]
        if after_roles:
            for role in after_roles:
                cookies = await self.config.role(role).cookies()
                if cookies != 0:
                    old_cookies = await self.config.member(after).cookies()
                    if self._max_balance_check(old_cookies + cookies):
                        continue
                    await self.deposit_cookies(after, cookies)

    async def _get_ids(self, ctx):
        if await self.config.is_global():
            data = await self.config.all_users()
        else:
            data = await self.config.all_members(ctx.guild)
        return sorted(data, key=lambda x: data[x]["cookies"], reverse=True)

    @staticmethod
    def display_time(seconds, granularity=2):
        intervals = (  # Source: from economy.py
            (("個禮拜"), 604800),  # 60 * 60 * 24 * 7
            (("天"), 86400),  # 60 * 60 * 24
            (("小時"), 3600),  # 60 * 60
            (("分鐘"), 60),
            (("秒"), 1),
        )

        result = []

        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                # if value == 1:
                #     name = name.rstrip("s")
                result.append(f"{value} {name}")
        return " ".join(result[:granularity])

    @staticmethod
    def _max_balance_check(value: int):
        if value > _MAX_BALANCE:
            return _MAX_BALANCE - value

    async def can_spend(self, user, amount):
        if await self.config.is_global():
            return await self.config.user(user).cookies() >= amount
        return await self.config.member(user).cookies() >= amount

    async def _can_spend(self, to_currency, user, amount):
        if to_currency:
            return bool(await self.can_spend(user, amount))
        return bool(await bank.can_spend(user, amount))

    async def withdraw_cookies(self, user, amount):
        if await self.config.is_global():
            cookies = await self.config.user(user).cookies() - amount
            await self.config.user(user).cookies.set(cookies)
        else:
            cookies = await self.config.member(user).cookies() - amount
            await self.config.member(user).cookies.set(cookies)

    async def deposit_cookies(self, user, amount):
        if await self.config.is_global():
            cookies = await self.config.user(user).cookies() + amount
            await self.config.user(user).cookies.set(cookies)
        else:
            cookies = await self.config.member(user).cookies() + amount
            await self.config.member(user).cookies.set(cookies)

    async def get_cookies(self, user) -> int:
        conf = (
            self.config.user(user)
            if await self.config.is_global()
            else self.config.member(user)
        )
        return await conf.cookies()

