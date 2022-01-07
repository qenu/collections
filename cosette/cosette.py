from typing import Literal
import logging

import discord
from redbot.core import commands, Config, bank
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.common_filters import filter_invites
import datetime

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.qenu.cosette")
status_to_zh = {
    "online": "在線",
    "idle": "閒置中",
    "dnd": "請勿打擾",
    "offline": "離線",
    "mobile": "在手機上",
    "streaming": "實況中",
}

class Cosette(commands.Cog):
    """
    Cogs made for Cosette.
    """

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx: commands.Context) -> str:

        return f"{super().format_help_for_context(ctx)}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x722f328773fed426,
            force_registration=True,
        )
        default_global = {
            "status_emojis": {
                "mobile": 749067110931759185,
                "online": 749221433552404581,
                "away": 749221433095356417,
                "dnd": 749221432772395140,
                "offline": 749221433049088082,
                "streaming": 749221434039205909,
            },
            "badge_emojis": {
                "staff": 848556248832016384,
                "early_supporter": 706198530837970998,
                "hypesquad_balance": 706198531538550886,
                "hypesquad_bravery": 706198532998299779,
                "hypesquad_brilliance": 706198535846101092,
                "hypesquad": 706198537049866261,
                "verified_bot_developer": 706198727953612901,
                "bug_hunter": 848556247632052225,
                "bug_hunter_level_2": 706199712402898985,
                "partner": 848556249192202247,
                "verified_bot": 848561838974697532,
                "verified_bot2": 848561839260434482,
            },
        }
        self.config.register_global(**default_global)
        self.emojis = self.bot.loop.create_task(self.init())

    def cog_unload(self):
        if self.emojis:
            self.emojis.cancel()

    def cog_unload(self):
        # Remove command logic are from: https://github.com/mikeshardmind/SinbadCogs/tree/v3/messagebox
        global _old_userinfo
        if _old_userinfo:
            try:
                self.bot.remove_command("userinfo")
            except Exception as error:
                log.info(error)
            self.bot.add_command(_old_userinfo)


    async def init(self):
        await self.bot.wait_until_ready()
        await self.gen_emojis()

    async def gen_emojis(self):
        config = await self.config.all()
        self.status_emojis = {
            "mobile": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["mobile"]),
            "online": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["online"]),
            "away": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["away"]),
            "dnd": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["dnd"]),
            "offline": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["offline"]),
            "streaming": discord.utils.get(
                self.bot.emojis, id=config["status_emojis"]["streaming"]
            ),
        }
        self.badge_emojis = {
            "staff": discord.utils.get(self.bot.emojis, id=config["badge_emojis"]["staff"]),
            "early_supporter": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["early_supporter"]
            ),
            "hypesquad_balance": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_balance"]
            ),
            "hypesquad_bravery": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_bravery"]
            ),
            "hypesquad_brilliance": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_brilliance"]
            ),
            "hypesquad": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad"]
            ),
            "verified_bot_developer": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot_developer"]
            ),
            "bug_hunter": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["bug_hunter"]
            ),
            "bug_hunter_level_2": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["bug_hunter_level_2"]
            ),
            "partner": discord.utils.get(self.bot.emojis, id=config["badge_emojis"]["partner"]),
            "verified_bot": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot"]
            ),
            "verified_bot2": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot2"]
            ),
        }

    @commands.command(name="查看", aliases=["userinfo", "ui"], usage="[成員]")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """查看成員資料"""
        mod = self.bot.get_cog("Mod")
        async with ctx.typing():
            author = ctx.author
            guild = ctx.guild

            if not user:
                user = author
            sharedguilds = (
                user.mutual_guilds
                if hasattr(user, "mutual_guilds")
                else {
                    guild
                    async for guild in AsyncIter(self.bot.guilds, steps=100)
                    if user in guild.members
                }
            )
            roles = user.roles[-1:0:-1]
            names, nicks = await mod.get_names_and_nicks(user)

            joined_at = user.joined_at
            since_created = f"<t:{int(user.created_at.timestamp())}:R>"
            if joined_at := user.joined_at:
                joined_at = joined_at.replace(tzinfo=datetime.timezone.utc)
            user_created = int(user.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())
            voice_state = user.voice
            member_number = (
                sorted(guild.members, key=lambda m: m.joined_at or ctx.message.created_at).index(
                    user
                )
                + 1
            )

            created_on = "<t:{0}>\n(<t:{0}:R>)".format(user_created)
            if joined_at is not None:
                joined_on = "<t:{0}>\n(<t:{0}:R>)".format(int(joined_at.timestamp()))
            else:
                joined_on = "不明"

            if user.is_on_mobile():
                statusemoji = self.status_emojis["mobile"] or "\N{MOBILE PHONE}"
            elif any(a.type is discord.ActivityType.streaming for a in user.activities):
                statusemoji = self.status_emojis["streaming"] or "\N{LARGE PURPLE CIRCLE}"
            elif user.status.name == "online":
                statusemoji = self.status_emojis["online"] or "\N{LARGE GREEN CIRCLE}"
            elif user.status.name == "offline":
                statusemoji = self.status_emojis["offline"] or "\N{MEDIUM WHITE CIRCLE}"
            elif user.status.name == "dnd":
                statusemoji = self.status_emojis["dnd"] or "\N{LARGE RED CIRCLE}"
            elif user.status.name == "idle":
                statusemoji = self.status_emojis["away"] or "\N{LARGE ORANGE CIRCLE}"
            else:
                statusemoji = "\N{MEDIUM BLACK CIRCLE}\N{VARIATION SELECTOR-16}"
            activity = "用戶目前{}".format(status_to_zh[user.status.name])
            status_string = mod.get_status_string(user)

            if roles:

                role_str = ", ".join([x.mention for x in roles])
                # 400 BAD REQUEST (error code: 50035): Invalid Form Body
                # In embed.fields.2.value: Must be 1024 or fewer in length.
                if len(role_str) > 1024:
                    # Alternative string building time.
                    # This is not the most optimal, but if you're hitting this, you are losing more time
                    # to every single check running on users than the occasional user info invoke
                    # We don't start by building this way, since the number of times we hit this should be
                    # infintesimally small compared to when we don't across all uses of Red.
                    continuation_string = (
                        "以及額外{numeric_number}個身分組...\n"
                    )

                    available_length = 1024 - len(
                        continuation_string
                    )  # do not attempt to tweak, i18n

                    role_chunks = []
                    remaining_roles = 0

                    for r in roles:
                        chunk = f"{r.mention}, "
                        chunk_size = len(chunk)

                        if chunk_size < available_length:
                            available_length -= chunk_size
                            role_chunks.append(chunk)
                        else:
                            remaining_roles += 1
                    role_chunks.append(continuation_string.format(numeric_number=remaining_roles))

                    role_str = "".join(role_chunks)
            else:
                role_str = None
            data = discord.Embed(
                description=(status_string or activity)
                + f"\n\n{len(sharedguilds)}個共同伺服器。"
                if len(sharedguilds) > 1
                else f"\n\n{len(sharedguilds)}個共同伺服器。",
                colour=user.colour,
            )

            data.add_field(name="加入Discord時間", value=created_on)
            data.add_field(name="加入伺服器時間", value=joined_on)
            if role_str is not None:
                data.add_field(name="身分組", value=role_str, inline=False)
            if names:
                # May need sanitizing later, but mentions do not ping in embeds currently
                val = filter_invites(", ".join(names))
                data.add_field(name="過去的使用者名稱", value=val, inline=False)
            if nicks:
                # May need sanitizing later, but mentions do not ping in embeds currently
                val = filter_invites(", ".join(nicks))
                data.add_field(name="過去的暱稱", value=val, inline=False)
            if voice_state and voice_state.channel:
                data.add_field(
                    name="目前所在語音頻道",
                    value="{0.mention} ID: {0.id}".format(voice_state.channel),
                    inline=False,
                )
            data.set_footer(text="成員#{} | 使用者ID: {}".format(member_number, user.id))

            name = str(user)
            name = " ~ ".join((name, user.nick)) if user.nick else name
            name = filter_invites(name)

            avatar = user.avatar_url_as(static_format="png")
            data.title = f"{statusemoji} {name}"
            data.set_thumbnail(url=avatar)

            flags = [f.name for f in user.public_flags.all()]
            badges = ""
            badge_count = 0
            if flags:
                for badge in sorted(flags):
                    if badge == "verified_bot":
                        emoji1 = self.badge_emojis["verified_bot"]
                        emoji2 = self.badge_emojis["verified_bot2"]
                        emoji = f"{emoji1}{emoji2}" if emoji1 else None
                    else:
                        emoji = self.badge_emojis[badge]
                    if emoji:
                        badges += f"{emoji} {badge.replace('_', ' ').title()}\n"
                    else:
                        badges += f"\N{BLACK QUESTION MARK ORNAMENT}\N{VARIATION SELECTOR-16} {badge.replace('_', ' ').title()}\n"
                    badge_count += 1
            if badges:
                data.add_field(name="徽章", value=badges)
            if "Economy" in self.bot.cogs:
                balance_count = 1
                bankstat = f"**Bank**: {humanize_number(await bank.get_balance(user))} {await bank.get_currency_name(ctx.guild)}\n"

                if "Unbelievaboat" in self.bot.cogs:
                    cog = self.bot.get_cog("Unbelievaboat")
                    state = await cog.walletdisabledcheck(ctx)
                    if not state:
                        balance_count += 1
                        balance = await cog.walletbalance(user)
                        bankstat += f"**Wallet**: {humanize_number(balance)} {await bank.get_currency_name(ctx.guild)}\n"

                if "Adventure" in self.bot.cogs:
                    cog = self.bot.get_cog("Adventure")
                    if getattr(cog, "_separate_economy", False):
                        global adventure_bank
                        if adventure_bank is None:
                            try:
                                from adventure import bank as adventure_bank
                            except:
                                pass
                        if adventure_bank:
                            adventure_currency = await adventure_bank.get_balance(user)
                            balance_count += 1
                            bankstat += f"**Adventure**: {humanize_number(adventure_currency)} {await adventure_bank.get_currency_name(ctx.guild)}"

                data.add_field(name="Balances" if balance_count > 1 else "Balance", value=bankstat)
            banner = (
                await self.bot.http.request(discord.http.Route("GET", f"/users/{user.id}"))
            ).get("banner", None)
            if banner is not None:
                ext = ".gif" if banner.startswith("a_") else ".png"
                banner_url = (
                    f"https://cdn.discordapp.com/banners/{user.id}/{banner}{ext}?size=4096"
                )
                data.set_image(url=banner_url)
            await ctx.send(embed=data)






try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


async def setup(bot):
    if discord.version_info <= (1, 4):
        raise CogLoadError("This cog requires d.py 1.4+ to work.")
    cog = Cosette(bot)
    if "Mod" not in bot.cogs:
        raise CogLoadError("This cog requires the Mod cog to be loaded.")
    global _old_userinfo
    _old_userinfo = bot.get_command("userinfo")
    if _old_userinfo:
        bot.remove_command(_old_userinfo.name)
    bot.add_cog(cog)