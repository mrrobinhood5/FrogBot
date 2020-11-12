from discord.ext import commands
from utils.checks import is_owner, is_authorized
import discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---- Bot Owner Commands ----
    @commands.group(name='admin', invoke_without_command=True)
    @is_owner()
    async def admin(self, ctx):
        """
        Owner only commands for the bot.
        """
        await ctx.send('give a subcommand nerd')

    @admin.command(name="stop", description="Owner Only - Stops Bot")
    @is_owner()
    async def stop(self, ctx, really: str = "no"):
        """
        Shuts down the bot.
        """
        await ctx.send("Okay, shutting down...")
        if really == 'please':
            await ctx.send('Shutdown complete.')
            await self.bot.logout()
        else:
            await ctx.send('Invalid Control Sequence detected. Operation Aborted.')

    @admin.command(name='change_status', description='Owner Only - Changes the bot\'s status.')
    @is_owner()
    async def change_status(self, ctx, *, value: str):
        """
        Changes the bot's status. Will reset if `reset` is passed.
        """
        if value != 'reset':
            await ctx.bot.mdb['bot_settings'].update_one({'setting': 'status'},
                                                         {'$set': {'status': value}}, upsert=True)
        else:
            await ctx.bot.mdb['bot_settings'].delete_one({'setting': 'status'})
        await ctx.bot.change_presence(activity=await ctx.bot.update_status_from_db())

        return await ctx.send(f'Status changed to {value}' if value != 'reset' else 'Status Reset.')

    @admin.command(name='set_server')
    @is_owner()
    async def set_personal_server(self, ctx, guild_id: int):
        """
        Sets the bot's personal server. This is the server where SheetApproval works.
        """
        await ctx.bot.mdb['bot_settings'].update_one({'setting': 'personal_server'},
                                                     {'$set': {'server_id': guild_id}},
                                                     upsert=True
                                                     )
        self.bot.personal_server = guild_id

        return await ctx.send(f'Set {guild_id} to personal server.')

    @admin.command(name='authorize', description='Add user to authorized list.')
    @is_owner()
    async def authorize_add(self, ctx, to_auth: discord.Member):
        """
        Adds a user to the bot's authorized list.
        """
        uid = to_auth.id
        await ctx.bot.mdb['authorized'].update_one({'_id': uid}, {'$set': {'_id': uid}}, upsert=True)

        return await ctx.send(f'User {ctx.author.display_name} added to authorized list.')

    @admin.command(name='ban')
    @commands.guild_only()
    @is_owner()
    async def manual_ban(self, ctx, to_ban: discord.Member, hard: bool = False):
        """
        Bans a member from the server.
        """
        try:
            if hard:
                await ctx.guild.kick(to_ban)
            await ctx.guild.ban(to_ban, reason=f'Banned by {ctx.author.display_name}')
            await ctx.send(f'User `{to_ban.name}#{to_ban.discriminator}` has been banned from the server.')
        except discord.Forbidden:
            return await ctx.author.dm_channel.send('I do not have permissions to ban this user.')
        except discord.HTTPException:
            return await ctx.author.dm_channel.send('An unknown discord error occurred. Pleas try again later.')

    @admin.command(name='leave')
    @is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        """
        Leaves the specified guild
        """
        to_leave: discord.Guild = self.bot.get_guild(guild_id)
        if to_leave is not None:
            await ctx.send(f'Leaving Guild: `{to_leave.name}`')
            try:
                await to_leave.leave()
            except discord.HTTPException:
                pass
        else:
            return await ctx.send('Guild not found.')

    @admin.command(name='mute', description='Mutes a user. Prevents them from using the bot.')
    @is_owner()
    async def mute(self, ctx, to_mute: discord.Member):
        """
        Mutes a user from the bot.
        """
        record = {'_id': to_mute.id}
        db = self.bot.mdb['muted_clients']
        muted = await db.find_one(record)
        if muted is None:
            await db.insert_one(record)
            await self.bot.update_muted_from_db()
            return await ctx.send(f'User {to_mute.name}#{to_mute.discriminator} has been muted.')
        else:
            return await ctx.send(f'User {to_mute.name}#{to_mute.discriminator} has already been muted.')

    @admin.command(name='unmute', description='Un-mutes a user.')
    @is_owner()
    async def unmute(self, ctx, to_mute: discord.Member):
        """
        Unmutes a user from the bot.
        """
        record = {'_id': to_mute.id}
        db = self.bot.mdb['muted_clients']
        muted = await db.find_one(record)
        if muted:
            await db.delete_one(record)
            await self.bot.update_muted_from_db()
            return await ctx.send(f'User {to_mute.name}#{to_mute.discriminator} has been un-muted.')
        else:
            return await ctx.send(f'User {to_mute.name}#{to_mute.discriminator} is not muted.')

    # ---- Server Owner Commands ----

    @commands.command(name='prefix', description='Changes the Bot\'s Prefix. Must have Manage Server.')
    @commands.check_any(commands.has_guild_permissions(manage_guild=True), is_owner())
    @commands.guild_only()
    async def change_prefix(self, ctx, to_change: str = None):
        """
        Changes the prefix for the current guild

        Can only be ran in a guild. If no prefix is specified, will show the current prefix.
        """
        guild_id = str(ctx.guild.id)
        if to_change is None:
            if guild_id in self.bot.prefixes:
                prefix = self.bot.prefixes.get(guild_id, self.bot.prefix)
            else:
                dbsearch = await self.bot.mdb['prefixes'].find_one({'guild_id': guild_id})
                if dbsearch is not None:
                    prefix = dbsearch.get('prefix', self.bot.prefix)
                else:
                    prefix = self.bot.prefix
                self.bot.prefixes[guild_id] = prefix
            return await ctx.send(f'No prefix specified to Change. Current Prefix: `{prefix}`')
        else:
            await ctx.bot.mdb['prefixes'].update_one({'guild_id': guild_id},
                                                     {'$set': {'prefix': to_change}}, upsert=True)
            ctx.bot.prefixes[guild_id] = to_change
            return await ctx.send(f'Guild prefix updated to `{to_change}`')


def setup(bot):
    bot.add_cog(Admin(bot))
