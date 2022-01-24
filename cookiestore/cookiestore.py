import discord
import datetime
import typing

from discord.utils import get

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify, humanize_list
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from redbot.core.bot import Red


class CookieStore(commands.Cog):
    """
    餅乾 專用 餅乾商店
    """

    __version__ = "1.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=16548964843212315, force_registration=True
        )
        self.config.register_guild(
            enabled=False, items={}, roles={}, games={}, ping=None
        )
        self.config.register_global(
            is_global=False, enabled=False, items={}, roles={}, games={}, ping=None
        )

        self.config.register_member(inventory={})
        self.config.register_user(inventory={})

    async def red_delete_data_for_user(self, *, requester, user_id):
        await self.config.user_from_id(user_id).clear()
        for guild in self.bot.guilds:
            await self.config.member_from_ids(guild.id, user_id).clear()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        context = super().format_help_for_context(ctx)
        return f"{context}\n\nVersion: {self.__version__}"

    @commands.group(name="商店設定", autohelp=True, aliases=["cookiestoreset","cookiestore", "storeset"])
    @commands.admin()
    @commands.guild_only()
    async def cookiestoreset(self, ctx):
        """餅乾商店的相關設定"""

    @cookiestoreset.command(name="global")
    @commands.is_owner()
    async def cookiestoreset_gg(
        self,
        ctx: commands.Context,
        make_global: bool,
        confirmation: typing.Optional[bool],
    ):
        """Switch from per-guild to global cookie store and vice versa."""
        if await self.config.is_global() == make_global:
            return await ctx.send("Uh oh, you're not really changing anything.")
        if not confirmation:
            return await ctx.send(
                "This will delete **all** current settings. This action **cannot** be undone.\n"
                f"If you're sure, type `{ctx.clean_prefix}cookiestoreset gg <make_global> yes`."
            )
        await self.config.clear_all_members()
        await self.config.clear_all_users()
        await self.config.clear_all_guilds()
        await self.config.clear_all_globals()
        await self.config.is_global.set(make_global)
        await ctx.send(
            f"Cookie store is now {'global' if make_global else 'per-guild'}."
        )

    @cookiestoreset.command(name="開關", aliases=["toggle"], usage="[on_off]")
    async def cookiestoreset_toggle(
        self, ctx: commands.Context, on_off: typing.Optional[bool]
    ):
        """餅乾商店的開關。

        如果沒有指定`on_off`，則會切換開關狀態。"""
        conf = await self._get_conf_group(ctx.guild)
        target_state = on_off or not (await conf.enabled())
        await conf.enabled.set(target_state)
        await ctx.send(f"餅乾商店{'開啟' if target_state else '關閉'}了!")

    @cookiestoreset.group(name="新增", aliases=["add"])
    async def cookiestoreset_add(self, ctx: commands.Context):
        """新增可以購買的商品。"""

    @cookiestoreset_add.command(name="身分組", aliases=["role"], usage="[身分組] [價格] [數量]")
    async def cookiestoreset_add_role(
        self, ctx: commands.Context, role: discord.Role, price: int, quantity: int
    ):
        """放入一個可以購買的身分組"""
        if self._over_zero(price, quantity):
            return await ctx.send("價格或數量必須大於0。")
        conf = await self._get_conf_group(ctx.guild)
        if role.name in await conf.roles():
            return await ctx.send(f"{role.name}已經存在於商品架上了喔(´・ω・`)")
        await conf.roles.set_raw(
            role.name, value={"price": price, "quantity": quantity}
        )
        await ctx.tick()

    @cookiestoreset_add.command(name="物品", aliases=["item"], usage="[物品] [價格] [數量] [兌換?(yes/no)]")
    async def cookiestoreset_add_item(
        self, ctx: commands.Context, item: str, price: int, quantity: int, redeem: bool
    ):
        """放入一個可以購買的物品"""
        if self._over_zero(price, quantity):
            return await ctx.send("價格或數量必須大於0。")
        conf = await self._get_conf_group(ctx.guild)
        if item in await conf.items():
            return await ctx.send(f"{item}已經存在於商品架上了喔(´・ω・`)")
        await conf.items.set_raw(
            item,
            value={
                "price": price,
                "quantity": quantity,
                "redeemable": redeem,
            },
        )
        await ctx.tick()

    @cookiestoreset_add.command(name="兌換物", aliases=["game"], usage="[兌換物] [價格] [數量] [兌換?(yes/no)]")
    async def cookiestoreset_add_game(
        self, ctx: commands.Context, game: str, price: int, quantity: int, redeem: bool
    ):
        """放入一個可以購買的兌換物"""
        if self._over_zero(price, quantity):
            return await ctx.send("價格或數量必須大於0。")
        conf = await self._get_conf_group(ctx.guild)
        if game in await conf.games():
            return await ctx.send(f"{game}已經存在於商品架上了喔(´・ω・`)")
        await conf.games.set_raw(
            game,
            value={
                "price": price,
                "quantity": quantity,
                "redeemable": redeem,
            },
        )
        await ctx.tick()

    @cookiestoreset.group(name="移除", aliases=["remove"])
    async def cookiestoreset_remove(self, ctx: commands.Context):
        """從商店移除商品"""

    @cookiestoreset_remove.command(name="身分組", aliases=["role"], usage="[身分組]")
    async def cookiestoreset_remove_role(
        self, ctx: commands.Context, role: discord.Role
    ):
        """從商店移除一個身分組"""
        conf = await self._get_conf_group(ctx.guild)
        if not await conf.roles.get_raw(role):
            return await ctx.send(f"我在商品架上找不到{role.name}")
        await conf.roles.clear_raw(role)
        await ctx.tick()

    @cookiestoreset_remove.command(name="物品", aliases=["item"], usage="[物品]")
    async def cookiestoreset_remove_item(self, ctx: commands.Context, item: str):
        """從商店移除一個物品"""
        conf = await self._get_conf_group(ctx.guild)
        if not await conf.items.get_raw(item):
            return await ctx.send(f"我在商品架上找不到{item}")
        await conf.items.clear_raw(item)
        await ctx.tick()

    @cookiestoreset_remove.command(name="兌換物", aliases=["game"], usage="[兌換物]")
    async def cookiestoreset_remove_game(self, ctx: commands.Context, game: str):
        """從商店移除一個兌換物"""
        conf = await self._get_conf_group(ctx.guild)
        if not await conf.games.get_raw(game):
            return await ctx.send(f"我在商品架上找不到{game}")
        await conf.games.clear_raw(game)
        await ctx.tick()

    @cookiestoreset.command(name="查看", aliases=["show"], usage="[商品]")
    async def cookiestoreset_show(self, ctx: commands.Context, *, item: str):
        """查看一件商品的資訊"""
        item = item.strip("@")
        conf = await self._get_conf_group(ctx.guild)
        items = await conf.items.get_raw()
        roles = await conf.roles.get_raw()
        games = await conf.games.get_raw()

        if item in items:
            info = await conf.items.get_raw(item)
            item_type = "item"
        elif item in roles:
            info = await conf.roles.get_raw(item)
            item_type = "role"
        elif item in games:
            info = await conf.games.get_raw(item)
            item_type = "game"
        else:
            return await ctx.send("這個商品不在商店裡。")
        price = info.get("price")
        quantity = info.get("quantity")
        redeemable = info.get("redeemable")
        if not redeemable:
            redeemable = False
        await ctx.send(
            f"**__{item}:__**\n*類別:* {item_type}\n*價格:* {price}\n*庫存:* {quantity}\n*可兌換:* {redeemable}"
        )

    @cookiestoreset.command(name="補貨", aliases=["restock"], usage="[商品] [數量]")
    async def cookiestoreset_restock(
        self, ctx: commands.Context, item: str, quantity: int
    ):
        """變更商品的庫存"""
        if self._over_zero(quantity):
            return await ctx.send("數量必須大於0。")
        conf = await self._get_conf_group(ctx.guild)
        items = await conf.items.get_raw()
        roles = await conf.roles.get_raw()
        games = await conf.games.get_raw()

        if item in items:
            await conf.items.set_raw(item, "quantity", value=quantity)
            await ctx.tick()
        elif item in roles:
            await conf.roles.set_raw(item, "quantity", value=quantity)
            await ctx.tick()
        elif item in games:
            await conf.games.set_raw(item, "quantity", value=quantity)
            await ctx.tick()
        else:
            await ctx.send("我在商品架上找不到這個物品。")

    @cookiestoreset.command(name="標註", aliases=[""], usage="[標註]")
    async def cookiestoreset_ping(
        self,
        ctx: commands.Context,
        who: typing.Union[discord.Member, discord.Role, None],
    ):
        """
        設定當商品被兌換時所需要通知的身分組

        如果沒有提供`標註`，則會顯示目前設定。"""
        conf = await self._get_conf_group(ctx.guild)
        if not who:
            ping_id = await conf.ping()
            if not ping_id:
                return await ctx.send("目前沒有設定任何標註。")
            ping = ctx.guild.get_member(ping_id)
            if not ping:
                ping = ctx.guild.get_role(ping_id)
            if not ping:
                return await ctx.send(
                    "找不到成員或是身分組。"
                )
            return await ctx.send(f"當有人兌換物品時，我會標註{ping.name}")
        await conf.ping.set(who.id)
        await ctx.send(
            f"有人兌換物品時，我將會標註{who.name}"
        )

    @cookiestoreset.group(name="重置", aliases=["reset"], invoke_without_command=True)
    async def cookiestoreset_reset(
        self, ctx: commands.Context, confirmation: typing.Optional[bool]
    ):
        """重置餅乾商店所有內容物"""
        if not confirmation:
            return await ctx.send(
                "這個指令將會重置所有商店內容，這個行為不可逆。\n"
                "如果你確定要執行，請在指令後面加上`yes`。"
            )
        conf = await self._get_conf_group(ctx.guild)
        for i in await conf.items.get_raw():
            await conf.items.clear_raw(i)
        for r in await conf.roles.get_raw():
            await conf.roles.clear_raw(r)
        for g in await conf.games.get_raw():
            await conf.games.clear_raw(g)
        await ctx.send("餅乾商店商品已重置。")

    @cookiestoreset_reset.command(name="成員物品", aliases=["inventories"])
    @commands.is_owner()
    async def cookiestoreset_reset_inventories(
        self, ctx: commands.Context, confirmation: typing.Optional[bool]
    ):
        """重置所有成員的物品欄。"""
        if not confirmation:
            return await ctx.send(
                "這個指令將會重置成員物品欄內容，這個行為不可逆。\n"
                "如果你確定要執行，請在指令後面加上`yes`。"
            )
        if await self.config.is_global():
            await self.config.clear_all_users()
        else:
            await self.config.clear_all_members(ctx.guild)
        await ctx.send("重置了所有成員的物品欄。")

    @cookiestoreset.command(name="顯示", aliases=["settings"])
    async def cookiestoreset_settings(self, ctx: commands.Context):
        """顯示目前設定"""
        is_global = await self.config.is_global()
        data = (
            await self.config.all()
            if is_global
            else await self.config.guild(ctx.guild).all()
        )
        ping = ctx.guild.get_role(data["ping"])
        ping = ping.name if ping else "無"

        embed = discord.Embed(
            colour=await ctx.embed_colour(), timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.title = "**__餅乾商店設定:__**"
        embed.set_footer(text="*必要項目")

        embed.add_field(name="通用:", value=str(is_global))
        embed.add_field(name="執行中*:", value=str(data["enabled"]))
        embed.add_field(name="標註*:", value=ping)
        embed.add_field(
            name="商品:", value=f"`{ctx.clean_prefix}餅乾商店` 以查看所有商品。"
        )

        await ctx.send(embed=embed)

    @commands.command(name="餅乾商店", aliases=["shop", "商店"])
    @commands.guild_only()
    async def shop(self, ctx: commands.Context):
        """顯示餅乾商店"""
        conf = await self._get_conf_group(ctx.guild)
        enabled = await conf.enabled()
        if not enabled:
            return await ctx.send("這個伺服器目前沒有開放商店功能!")
        page_list = await self._show_store(ctx)
        if len(page_list) > 1:
            await menu(ctx, page_list, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=page_list[0])

    @commands.command(name="購買", aliases=["buy"], usage="<商品名稱>")
    @commands.guild_only()
    async def buy(self, ctx: commands.Context, *, item: typing.Optional[str]):
        """從餅乾商店購買一個商品"""
        conf = await self._get_conf_group(ctx.guild)
        enabled = await conf.enabled()
        if not enabled:
            return await ctx.send("目前沒有開放商店功能!")

        cookies_cog = self.bot.get_cog("Cookies").config
        if await cookies_cog.is_global():
            cookies = await cookies_cog.user(ctx.author).cookies()
        else:
            cookies = await cookies_cog.member(ctx.author).cookies()
        items = await conf.items.get_raw()
        roles = await conf.roles.get_raw()
        games = await conf.games.get_raw()

        if not item:
            page_list = await self._show_store(ctx)
            if len(page_list) > 1:
                return await menu(ctx, page_list, DEFAULT_CONTROLS)
            return await ctx.send(embed=page_list[0])
        item = item.strip("@")
        inventory = await self.config.member(ctx.author).inventory.get_raw()
        if item in inventory:
            return await ctx.send("這個物品只能擁有一個。")
        if item in roles:
            role_obj = get(ctx.guild.roles, name=item)
            if role_obj:
                role = await conf.roles.get_raw(item)
                price = int(role.get("price"))
                quantity = int(role.get("quantity"))
                if quantity == 0:
                    return await ctx.send("這個物品已經沒有庫存了!")
                if price > cookies:
                    return await ctx.send("你沒有足夠的餅乾!")
                await ctx.author.add_roles(role_obj)
                cookies -= price
                quantity -= 1
                await self.bot.get_cog("Cookies").config.member(ctx.author).cookies.set(
                    cookies
                )
                await self.config.member(ctx.author).inventory.set_raw(
                    item,
                    value={
                        "price": price,
                        "is_role": True,
                        "is_game": False,
                        "redeemable": False,
                        "redeemed": True,
                    },
                )
                await conf.roles.set_raw(item, "quantity", value=quantity)
                await ctx.send(f"你成功購買了 {item}。")
            else:
                await ctx.send("我找不到這個身分組。")
        elif item in items:
            item_info = await conf.items.get_raw(item)
            price = int(item_info.get("price"))
            quantity = int(item_info.get("quantity"))
            redeemable = item_info.get("redeemable")
            if not redeemable:
                redeemable = False
            if quantity == 0:
                return await ctx.send("這個物品已經沒有庫存了!")
            if price > cookies:
                return await ctx.send("你沒有足夠的餅乾!")
            cookies -= price
            quantity -= 1
            await self.bot.get_cog("Cookies").config.member(ctx.author).cookies.set(
                cookies
            )
            await conf.items.set_raw(item, "quantity", value=quantity)
            if redeemable:
                await self.config.member(ctx.author).inventory.set_raw(
                    item,
                    value={
                        "price": price,
                        "is_role": False,
                        "is_game": False,
                        "redeemable": True,
                        "redeemed": False,
                    },
                )
                await ctx.send(
                    f"你成功購買了 {item}。 你可以使用 `{ctx.clean_prefix}兌換 {item}` 來兌換這個物品。"
                )
            else:
                await self.config.member(ctx.author).inventory.set_raw(
                    item,
                    value={
                        "price": price,
                        "is_role": False,
                        "is_game": False,
                        "redeemable": False,
                        "redeemed": True,
                    },
                )
                await ctx.send(f"你成功購買了 {item}。")
        elif item in games:
            game_info = await self._show_thing(ctx, 2, item)
            price = int(game_info.get("price"))
            quantity = int(game_info.get("quantity"))
            redeemable = game_info.get("redeemable")
            if not redeemable:
                redeemable = False
            if quantity == 0:
                return await ctx.send("這個物品已經沒有庫存了!")
            if price > cookies:
                return await ctx.send("你沒有足夠的餅乾!")
            cookies -= price
            quantity -= 1
            await self.bot.get_cog("Cookies").config.member(ctx.author).cookies.set(
                cookies
            )
            await conf.games.set_raw(item, "quantity", value=quantity)
            if redeemable:
                await self.config.member(ctx.author).inventory.set_raw(
                    item,
                    value={
                        "price": price,
                        "is_role": False,
                        "is_game": True,
                        "redeemable": True,
                        "redeemed": False,
                    },
                )
                await ctx.send(
                    f"你成功購買了 {item}。 你可以使用 `{ctx.clean_prefix}兌換 {item}` 來兌換這個物品。"
                )
            else:
                await self.config.member(ctx.author).inventory.set_raw(
                    item,
                    value={
                        "price": price,
                        "is_role": False,
                        "is_game": True,
                        "redeemable": False,
                        "redeemed": True,
                    },
                )
                await ctx.send(f"你成功購買了 {item}。")
        else:
            page_list = await self._show_store(ctx)
            if len(page_list) > 1:
                return await menu(ctx, page_list, DEFAULT_CONTROLS)
            return await ctx.send(embed=page_list[0])

    @commands.command(name="退貨", aliases=["return"], usage="<商品名稱>")
    @commands.guild_only()
    async def cookiestore_return(self, ctx: commands.Context, *, item: str):
        """Return an item, you will only get 50% of the price."""
        conf = await self._get_conf_group(ctx.guild)
        enabled = await conf.enabled()
        if not enabled:
            return await ctx.send("Uh oh, store is disabled.")
        cookies = int(
            await self.bot.get_cog("Cookies").config.member(ctx.author).cookies()
        )
        inventory = await self.config.member(ctx.author).inventory.get_raw()

        if item not in inventory:
            return await ctx.send("You don't own this item.")
        info = await self.config.member(ctx.author).inventory.get_raw(item)

        is_game = info.get("is_game")
        if is_game:
            return await ctx.send("This item isn't returnable.")
        is_role = info.get("is_role")
        if is_role:
            role_obj = get(ctx.guild.roles, name=item)
            if role_obj:
                await ctx.author.remove_roles(role_obj)
        redeemed = info.get("redeemed")
        if not redeemed:
            redeemed = False
        if redeemed:
            return await ctx.send("You can't return an item you have redeemed.")
        price = int(info.get("price"))
        return_price = price * 0.5
        cookies += return_price
        await self.config.member(ctx.author).inventory.clear_raw(item)
        await self.bot.get_cog("Cookies").config.member(ctx.author).cookies.set(cookies)
        await ctx.send(
            f"You have returned {item} and got {return_price} :cookie: back."
        )

    @commands.group(name="物品欄", invoke_without_command=True, aliases=["包包", "inventory"])
    @commands.guild_only()
    async def inventory(self, ctx: commands.Context):
        """See all items you own."""
        inventory = await self.config.member(ctx.author).inventory.get_raw()

        lst = []
        for i in inventory:
            info = await self.config.member(ctx.author).inventory.get_raw(i)
            if not info.get("is_role"):
                lst.append(i)
            else:
                role_obj = get(ctx.guild.roles, name=i)
                lst.append(role_obj.mention)
        desc = "沒有東西。" if lst == [] else humanize_list(lst)
        embed = discord.Embed(
            description=desc,
            colour=ctx.author.colour,
            timestamp=datetime.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.display_name}的物品欄",
            icon_url=ctx.author.avatar_url,
        )

        await ctx.send(embed=embed)

    @inventory.command(name="移除", aliases=["remove"], usage="<商品名稱>")
    @commands.guild_only()
    async def inventory_remove(self, ctx: commands.Context, *, item: str):
        """Remove an item from your inventory."""
        inventory = await self.config.member(ctx.author).inventory.get_raw()
        if item not in inventory:
            return await ctx.send("你沒有這個物品。")
        await self.config.member(ctx.author).inventory.clear_raw(item)
        await ctx.send(f"{item} 已經移除。")

    @commands.command(name="兌換", aliases=["redeem"], usage="<物品名稱>")
    @commands.guild_only()
    async def redeem(self, ctx: commands.Context, *, item: str):
        """兌換你所擁有的物品。"""
        inventory = await self.config.member(ctx.author).inventory.get_raw()
        if item not in inventory:
            return await ctx.send("你沒有這個物品。")
        info = await self.config.member(ctx.author).inventory.get_raw(item)
        is_role = info.get("is_role")
        if is_role:
            return await ctx.send("身分組無法被兌換。")
        redeemable = info.get("redeemable")
        if not redeemable:
            return await ctx.send("這個物品無法被兌換。")
        redeemed = info.get("redeemed")
        if redeemed:
            return await ctx.send("你已經兌換過這個物品。")
        conf = await self._get_conf_group(ctx.guild)
        ping_id = await conf.ping()
        if not ping_id:
            return await ctx.send("管理員尚未設定完成。")
        ping = ctx.guild.get_member(ping_id)
        if ping:
            await ctx.send(
                f"{ping.mention}, {ctx.author.mention} 想要兌換 {item}."
            )
        else:
            ping = ctx.guild.get_role(ping_id)
            if not ping:
                return await ctx.send("管理員尚未設定完成。")
            if ping.mentionable:
                await ctx.send(
                    f"{ping.mention}, {ctx.author.mention} 想要兌換 {item}."
                )
            else:
                await ping.edit(mentionable=True)
                await ctx.send(
                    f"{ping.mention}, {ctx.author.mention} 想要兌換 {item}."
                )
                await ping.edit(mentionable=False)
        await self.config.member(ctx.author).inventory.set_raw(
            item, "redeemed", value=True
        )

    async def _show_store(self, ctx):
        items = await self._show_thing(ctx, 0, "None")
        roles = await self._show_thing(ctx, 1, "None")
        games = await self._show_thing(ctx, 2, "None")
        list_of_lists = [items, roles, games]
        stuff = []

        for index, list_of_objects in enumerate(list_of_lists):
            for _object in list_of_objects:
                if _object in roles:
                    role_obj = get(ctx.guild.roles, name=_object)
                    if not role_obj:
                        continue
                thing = await self._show_thing(ctx, index, _object)
                stuff.append(
                    f"__商品:__ **{_object}** | "
                    f"__價格:__ {thing.get('price')} :cookie: | "
                    f"__庫存:__ {thing.get('quantity')}"
                )

        desc = "目前沒有內容物。" if stuff == [] else "\n".join(stuff)
        page_list = []
        for page in pagify(desc, delims=["\n"], page_length=1000):
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                description=page,
                timestamp=datetime.datetime.now(),
            )
            embed.set_author(
                name=f"{ctx.guild.name}的餅乾商店",
                icon_url=ctx.guild.icon_url,
            )
            page_list.append(embed)
        return page_list

    async def _show_thing(self, ctx, number, item_name):
        conf = await self._get_conf_group(ctx.guild)
        if number == 0:
            if item_name == "None":
                return await conf.items.get_raw()
            return await conf.items.get_raw(item_name)
        if number == 1:
            if item_name == "None":
                return await conf.roles.get_raw()
            return await conf.roles.get_raw(item_name)
        if item_name == "None":
            return await conf.games.get_raw()
        return await conf.games.get_raw(item_name)

    @staticmethod
    def _over_zero(one: int, two: typing.Optional[int]):
        return (one <= 0 or two <= 0) if two else (one <= 0)

    async def _get_conf_group(self, guild):
        return (
            self.config if await self.config.is_global() else self.config.guild(guild)
        )

    async def _get_user_conf(self, is_global, user):
        return self.config.user(user) if is_global else self.config.member(user)
