from discord.ext import commands
import discord
from utils.functions import create_default_embed, member_in_guild
from datetime import datetime
from utils.constants import STATUS_EMOJIS, STATUS_NAMES, BADGE_EMOJIS, SUPPORT_SERVER_ID


def time_to_readable(delta_uptime):
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d, {hours}h, {minutes}m, {seconds}s"


DATE_FORMAT = '%A, %B %d, %Y at %I:%M:%S %p'


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx):
        """
        Gets the ping of the bot.
        """
        now = datetime.now()
        message = await ctx.send('Ping!')
        await message.edit(content=f'Pong!\nBot: {int(ctx.bot.latency*1000)} ms\n'
                                   f'Discord: {int((datetime.now() - now).total_seconds()*1000)} ms')

    @commands.command(name='uptime', aliases=['up', 'alive'])
    async def uptime(self, ctx):
        """
        Displays the current uptime of the bot.
        """
        embed = create_default_embed(ctx)
        embed.title = 'FrogBot Uptime'
        bot_up = time_to_readable(self.bot.uptime)
        embed.add_field(name='Bot Uptime', value=f'{bot_up}')
        if ctx.bot.is_ready():
            embed.add_field(name='Ready Uptime',
                            value=f'{time_to_readable(datetime.utcnow() - self.bot.ready_time)}')
        return await ctx.send(embed=embed)

    @commands.command(name='info', aliases=['stats', 'about'])
    async def info(self, ctx):
        """
        Displays some information about the bot.
        """
        embed = create_default_embed(ctx)
        embed.title = 'FrogBot Information'
        embed.description = 'Bot built by Dr Turtle#1771 made for D&D and personal servers!'
        members = sum([guild.member_count for guild in self.bot.guilds])
        embed.add_field(name='Guilds', value=f'{len(self.bot.guilds)}')
        embed.add_field(name='Members', value=f'{members}')
        embed.url = 'https://github.com/1drturtle/FrogBot'

        await ctx.send(embed=embed)

    @commands.command(name='servinfo', aliases=['sinfo'])
    @commands.guild_only()
    async def server_info(self, ctx):
        """
        Displays information about the current server.
        """
        embed = create_default_embed(ctx)
        guild = ctx.guild
        embed.title = f'{guild.name} - Server Information'
        general_info = f'**ID:** {guild.id}\n' \
                       f'**Owner:** {guild.owner.mention}\n' \
                       f'Created: {guild.created_at.strftime(DATE_FORMAT)}'
        embed.add_field(name='General Info', value=general_info, inline=False)
        emoji_x = 0
        emojis = []
        for emoji in guild.emojis:
            emoji_x += 1
            if emoji_x >= 10:
                break
            emojis.append(emoji)
        emoji_info = f'{len(guild.emojis)} emoji{"s" if len(guild.emojis) != 1 else ""}\n' \
                     f'{",".join([str(e) for e in emojis])} {"..." if emoji_x >= 10 else ""}'
        embed.add_field(name='Emojis', value=emoji_info, inline=False)
        bots = [member for member in guild.members if member.bot]
        member_stats = f'{guild.member_count - len(bots)} members ({len(bots)} bots)'
        embed.add_field(name='Member Info', value=member_stats)
        channels = f'{len([c for c in guild.categories])} categories, ' \
                   f'{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])} text channels, ' \
                   f'{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])} voice channels.'
        embed.add_field(name='Channel Info', value=channels)
        embed.set_thumbnail(url=str(guild.icon_url))

        return await ctx.send(embed=embed, allowed_mentions=None)

    @commands.command(name='memberinfo', aliases=['minfo'])
    @commands.guild_only()
    async def member_inf(self, ctx, who: discord.Member = None):
        """
        Shows information about a member in this server.
        """
        if who is None:
            who = ctx.author
        embed = create_default_embed(ctx)
        badges = ''
        if who.id == self.bot.owner:
            badges += f'{BADGE_EMOJIS["bot_owner"]} '
        if who.id == ctx.guild.owner.id:
            badges += f'{BADGE_EMOJIS["server_owner"]} '
        support_server = self.bot.get_guild(SUPPORT_SERVER_ID)
        if support_server is not None and member_in_guild(who.id, support_server):
            badges += f'{BADGE_EMOJIS["support_server"]}'

        embed.title = f'Member Information - {who.display_name} {badges}'

        embed.add_field(name='Basics', value=f'Mention: {who.mention}\n'
                                             f'Username: {who.name}#{who.discriminator}\n'
                                             f'ID: {who.id}\n'
                                             f'Status: {STATUS_EMOJIS[str(who.status)]}'
                                             f' ({STATUS_NAMES[str(who.status)]})')
        embed.add_field(name='Roles', value=f'Top Role: {who.top_role.mention}\n'
                                            f'{len(who.roles)} role(s)\n'
                                            f'Server Owner: {"True" if ctx.guild.owner.id == who.id else "False"}',
                        inline=False)
        embed.add_field(name='Date Information', value=f'Created at: {who.created_at.strftime(DATE_FORMAT)}\n'
                                                       f'Joined at: {who.joined_at.strftime(DATE_FORMAT)}',
                        inline=False)
        embed.set_thumbnail(url=who.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name='say')
    async def say(self, ctx, *, repeat: str):
        """
        Repeats what you say.
        """
        out = repeat
        if ctx.author.id != self.bot.owner:
            out = f'{ctx.author.display_name}: ' + repeat
        return await ctx.send(out)

    @commands.command(name='avatar')
    async def avatar(self, ctx, who: discord.Member = None):
        """
        Gives you the avatar of whoever you specify, or yourself if you don't specify anyone.
        """
        url = ctx.author.avatar_url
        if who:
            url = who.avatar_url
        return await ctx.send(url)

    @commands.command(name='source')
    async def source(self, ctx):
        """
        Returns the link to the source code of the bot.
        """
        embed = create_default_embed(ctx)
        embed.title = 'FrogBot Source'
        embed.description = '[Click here for the Source Code.](https://github.com/1drturtle/FrogBot)'
        embed.set_thumbnail(url=str(self.bot.user.avatar_url))
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utility(bot))
