import logging

import discord
from discord.ext import commands

from utils.checks import is_personal_server, is_owner
from utils.constants import BOT_MODS, APPROVAL_ROLES, ROLES_CHANNEL, AVRAE_CHANNEL
from utils.functions import create_default_embed

log = logging.getLogger('sheet approval')


class ToBeApproved:
    def __init__(self, message_id: int, approvals: list, channel_id: int, owner_id: int):
        """
        :param message_id: ID of Message that created this.
        :param approvals: List of Member ID's who have approved the Sheet
        :param channel_id: Channel ID that the message was sent in
        :param owner_id: Member ID of owner of sheet.
        """
        self.message_id = message_id
        self.approvals = approvals
        self.channel_id = channel_id
        self.owner_id = owner_id

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'approvals': self.approvals,
            'channel_id': self.channel_id,
            'owner_id': self.owner_id
        }

    async def get_message(self, guild):
        msg = guild.get_channel(self.channel_id)
        if msg is not None:
            msg = await msg.fetch_message(self.message_id)
        return msg

    async def commit(self, db):
        db.update_one({'message_id': self.message_id}, {'$set': self.to_dict()}, upsert=True)

    async def fields(self, guild, bot):
        message = await self.get_message(guild)
        embed = message.embeds[0]
        embed.clear_fields()
        for approval in self.approvals:
            x = guild.get_member(approval)
            if x is not None:
                embed.add_field(name='Approval', value=x.display_name)
        if len(self.approvals) >= 2:
            mention = guild.get_member(self.owner_id)
            embed.add_field(name=f'Approved!',
                            value=f'{mention.mention}, Your character has been approved! '
                                  f'Go to {ROLES_CHANNEL} and grab your player roles,'
                                  f' and then go to {AVRAE_CHANNEL} and do the pinned commands for your sheet!',
                            inline=False)
            general = None
            if bot.personal_server['general_channel'] is not None:
                general = guild.get_channel(bot.personal_server['general_channel'])
            if general is not None:
                await general.send(f'{mention.mention}, your character with the following content has been approved:\n'
                                   f'```\n{embed.description}\n```\n'
                                   f'Check your submission in {self.bot.personal_server["sheet_channel"]} for details on what to do next.',
                                   allowed_mentions=discord.AllowedMentions(users=[mention]))
        await message.edit(embed=embed)

    async def add_approval(self, guild, approver, bot):
        if approver.id in self.approvals:
            return
        if approver.id == self.owner_id:
            return

        self.approvals.append(approver.id)

        if len(self.approvals) >= 2:
            await self.approve(guild, bot)
        else:
            await self.fields(guild, bot)

    async def remove_approval(self, guild, user_id, bot):
        member = guild.get_member(user_id)
        if member.id not in self.approvals:
            return
        self.approvals.remove(member.id)
        await self.fields(guild, bot)

    async def approve(self, guild, bot):
        if len(self.approvals) < 2:
            return
        await self.fields(guild, bot)
        member = guild.get_member(self.owner_id)
        if member is None:
            return None
        # Add Player Role
        player_role = next((role for role in guild.roles if role.name == 'Player'), None)
        if player_role not in member.roles and player_role is not None:
            await member.add_roles(player_role, reason='Approved.')
        # Remove Commoner Role
        commoner_role = next((role for role in member.roles if role.name == 'Commoner'), None)
        if commoner_role is not None:
            await member.remove_roles(commoner_role, reason='Approved.')




class SheetApproval(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def sheet_from_emoji(self, payload) -> ToBeApproved:
        # Check the Guild
        guild_id = payload.guild_id
        if guild_id != self.bot.personal_server['server_id']:
            return None

        # Check the Roles
        member = payload.member
        if member is None:
            member = self.bot.get_guild(guild_id).get_member(payload.user_id)
            if member is None:
                return None
        if len([role for role in member.roles if role.name.lower() in APPROVAL_ROLES]) == 0:
            return None

        # Check to see if it's an existing sheet
        result = await self.bot.mdb['to_approve'].find_one({'message_id': payload.message_id})
        if result is None:
            return None
        # Get rid of object id
        result.pop('_id')

        sheet: ToBeApproved = ToBeApproved.from_dict(result)
        return sheet

    @commands.Cog.listener('on_raw_reaction_add')
    async def check_for_approval(self, payload):
        sheet: ToBeApproved = await self.sheet_from_emoji(payload)
        if sheet is None:
            return
        if len(sheet.approvals) >= 2:
            return

        guild = self.bot.get_guild(payload.guild_id)

        await sheet.add_approval(guild, payload.member, self.bot)
        await sheet.commit(self.bot.mdb['to_approve'])

    @commands.Cog.listener('on_raw_reaction_remove')
    async def check_for_deny(self, payload):
        sheet: ToBeApproved = await self.sheet_from_emoji(payload)
        if sheet is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        await sheet.remove_approval(guild, payload.user_id, self.bot)
        await sheet.commit(self.bot.mdb['to_approve'])

    @commands.command(name='sheet', aliases=['submit'])
    @is_personal_server()
    async def new_sheet(self, ctx, *, content: str):
        """
        Adds a sheet to be approved
        """
        embed = create_default_embed(ctx)
        embed.title = f'Sheet Approval - {ctx.author.display_name}'
        embed.description = content

        if '(url)' in content:
            return await ctx.author.send('You must include your *actual* sheet URL in the command, not `(url)`')

        # If not character-submission or FrogBot dev
        if (ctx.channel.id != self.bot.personal_server['sheet_channel']) and not (ctx.guild.id == 755202524859859004):
            return await ctx.send('This channel is not valid for submitting sheets.')

        msg = await ctx.send(embed=embed)

        new_sheet = ToBeApproved(message_id=msg.id,
                                 approvals=[],
                                 channel_id=ctx.channel.id,
                                 owner_id=ctx.author.id)
        await self.bot.mdb['to_approve'].insert_one(new_sheet.to_dict())

    @commands.command('cleanup_sheets')
    @is_personal_server()
    @commands.check_any(is_owner(), commands.has_any_role(*BOT_MODS))
    async def remove_sheets(self, ctx):
        """
        Removes deleted sheets from database. Run every once and a while.
        """
        db = self.bot.mdb['to_approve']

        embed = create_default_embed(ctx)
        embed.title = f'Pruning Old Sheets from Database.'
        all_sheets = await db.find().to_list(None)
        count = 0
        for sheet in all_sheets:
            sheet.pop('_id')
            sheet = ToBeApproved.from_dict(sheet)
            channel = ctx.guild.get_channel(sheet.channel_id)
            if channel is None:
                continue
            try:
                await channel.fetch_message(sheet.message_id)
            except discord.NotFound:
                count += 1
                await db.delete_one({'message_id': sheet.message_id})
        embed.description = f'Pruned {count} Sheet{"s" if count != 1 else ""} from the DB.'
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(SheetApproval(bot))
