import discord
from discord import app_commands
import aiohttp
from discord.ext import commands, tasks
import json
import random
from datetime import timedelta
from cogs.ticket import ticket_launcher, main


class MyBot(commands.Bot):

    def __init__(self):
        def get_prefex(client, message):
            with open("jsons/prefixes.json", "r") as f:
                prefixes = json.load(f)
            return prefixes[str(message.guild.id)]

        super().__init__(command_prefix = get_prefex,
                         intents = discord.Intents.all(),
                         case_insensitive=True,
                         application_id = YOUR_APP_ID)
        self.anti_spam = commands.CooldownMapping.from_cooldown(5, 15, commands.BucketType.member)
        self.too_many_violations = commands.CooldownMapping.from_cooldown(4, 60, commands.BucketType.member)
        self.initial_extensions = [
            "cogs.help", "cogs.error_handler", "cogs.events", "cogs.ticket",
            "cogs.moderation", "cogs.general", "cogs.fun", "cogs.serverinfo",
            "cogs.settings", "cogs.connect4", "cogs.tictactoe", "cogs.rps"]
        self.added = False

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        for cogs in self.initial_extensions: 
            await self.load_extension(cogs)
        await self.tree.sync()
        print(f"Synced for {self.user}!")

    #closing
    async def close(self):
        await super().close()
        await self.session.close()

    #on_ready message
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        if not self.added:
            self.add_view(ticket_launcher())
            self.add_view(main())
            self.added = True
            # Setting `Playing ` status
            await bot.change_presence(activity=discord.Game(name="/sbhelp"))

    #anti spam
    async def on_message(self, message):
        if type(message.channel) is not discord.TextChannel or message.author.bot: return
        bucket = self.anti_spam.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, don't spam!", delete_after = 10)
            violations = self.too_many_violations.get_bucket(message)
            check = violations.update_rate_limit()
            if check:
                await message.author.timeout(timedelta(minutes = 10), reason = "Spamming")
                try: await message.author.send("You have been timed out for spamming!")
                except: pass

bot = MyBot()
bot.remove_command('help')


#feedback button
class feedbackButton(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 600, commands.BucketType.member)
    @discord.ui.button(label="Send Feedback", style=discord.ButtonStyle.blurple)
    async def feedback_button(self, interaction:discord.Interaction, button:discord.ui.Button):
        if interaction.user != author:
            return await interaction.response.send_message("> This is not for you!", ephemeral=True)
        retry = self.cooldown.get_bucket(interaction.message).update_rate_limit()
        if retry:
            return await interaction.response.send_message(f"Slow down! Try again in {round(retry, 1)} seconds!", ephemeral = True)
        await interaction.response.send_modal(feedbackModal())


#feedback modal
class feedbackModal(ui.Modal, title = "Send Your Feedback"):
    ftitle = ui.TextInput(label = "Title", style = discord.TextStyle.short, placeholder = "Write a title for the issue/suggestion.", required = True, max_length = 50)
    fdes = ui.TextInput(label = "Long Description", style = discord.TextStyle.short, placeholder = "Descripe the issue/suggestion.", required = True, max_length = 1000)
    fsol = ui.TextInput(label = "Solution (optional)", style = discord.TextStyle.short, placeholder = "Write a solution for the issue.", required = False, max_length = 1000)
    async def on_submit(self, interaction: discord.Interaction):
        channel = bot.get_channel(YOUR_CHANNEL_ID)
        try:
            embed = discord.Embed(title = f"User: {interaction.user}\nServer: {interaction.guild.name}", description = f"**{self.ftitle}**", timestamp = datetime.now())
            embed.add_field(name = "Description", value = self.fdes)
            embed.add_field(name = "Solution", value = self.fsol)
            embed.set_author(name = interaction.user, icon_url = interaction.user.avatar)
            await channel.send(embed = embed)
            await interaction.response.send_message("Your feedback has been sent succesfully!", ephemeral=True)
        except:
            embed = discord.Embed(title = f"User: {interaction.user}\nServer: {interaction.guild.name}", description = f"**{self.ftitle}**", timestamp = datetime.now())
            embed.add_field(name = "Description", value = self.fdes)
            embed.set_author(name = interaction.user, icon_url = interaction.user.avatar)
            await channel.send(embed = embed)
            await interaction.response.send_message("Your feedback has been sent succesfully!", ephemeral=True)


#feedback command
@bot.hybrid_command(name = "feedback", with_app_command = True, description = "Send your feedback directly to the developers.")
@commands.cooldown(1, 600, commands.BucketType.user)
async def feedback(ctx: commands.Context):
    global author
    author = ctx.author
    view = feedbackButton()
    embed = discord.Embed(title = "If you had faced any problems or have any suggestions, feel free to send your feedback!")
    await ctx.send(embed = embed, view=view, ephemeral=True)

@feedback.error
async def feedback_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        cool_error = discord.Embed(title=f"Wait before sending another feedback", description=f"> Try again in {error.retry_after:.2f}s.",colour=discord.Colour.light_grey())
        await ctx.reply(embed=cool_error, ephemeral=True)


#on join
@bot.event
async def on_guild_join(guild):
    #add prefix
    with open("jsons/prefixes.json", "r") as f:
        prefixes = json.load(f)
    prefixes[str(guild.id)] = "_"
    with open("jsons/prefixes.json", "w") as f:
        json.dump(prefixes, f, indent=4)

    #add filter toggle
    with open("jsons/filter.json", "r") as f:
        toggle = json.load(f)
    toggle[str(guild.id)] = "disabled"
    with open("jsons/filter.json", "w") as f:
        json.dump(toggle, f, indent=4)

    #add suggest
    with open("jsons/suggest.json", "r", encoding="utf8") as f:
        channels = json.load(f)
    with open("jsons/suggest.json", "w", encoding="utf8") as f:
        channels[str(guild.id)] = {}
        channels[str(guild.id)]["suggch"] = 123
        channels[str(guild.id)]["revch"] = 123
        json.dump(channels, f, sort_keys=True, indent=4, ensure_ascii=False)

    #add ticket role
    with open("jsons/ticket_roles.json", "r", encoding="utf8") as f:
        user = json.load(f)
    with open("jsons/ticket_roles.json", "w", encoding="utf8") as f:
        user[str(guild.id)] = 123
        json.dump(user, f, sort_keys=True, indent=4, ensure_ascii=False)

    #add welcome
    with open("jsons/welcome.json", "r", encoding="utf8") as f:
        channel = json.load(f)
    with open("jsons/welcome.json", "w", encoding="utf8") as f:
        channel[str(guild.id)] = 123
        json.dump(channel, f, sort_keys=True, indent=4, ensure_ascii=False)

#on leave
@bot.event
async def on_guild_remove(guild):
    #remove prefix
    with open("jsons/prefixes.json", "r") as f:
        prefixes = json.load(f)
    prefixes.pop(str(guild.id))
    with open("jsons/prefixes.json", "w") as f:
        json.dump(prefixes, f, indent=4)

    #remove filter toggle
    with open("jsons/filter.json", "r") as f:
        toggle = json.load(f)
    toggle.pop(str(guild.id))
    with open("jsons/filter.json", "w") as f:
        json.dump(toggle, f, indent=4)

    #remove suggest
    with open("jsons/suggest.json", "r", encoding="utf8") as f:
        channels = json.load(f)
    channels.pop[str(guild.id)]
    with open("jsons/suggest.json", "w", encoding="utf8") as f:
        json.dump(channels, f, sort_keys=True, indent=4, ensure_ascii=False)

    #remove ticket role
    with open("jsons/ticket_roles.json", "r", encoding="utf8") as f:
        user = json.load(f)
    user.pop[str(guild.id)]
    with open("jsons/ticket_roles.json", "w", encoding="utf8") as f:
        json.dump(user, f, sort_keys=True, indent=4, ensure_ascii=False)

    #remove welcome
    with open("jsons/welcome.json", "r", encoding="utf8") as f:
        user = json.load(f)
    user.pop[str(guild.id)]
    with open("jsons/welcome.json", "w", encoding="utf8") as f:
        json.dump(user, f, sort_keys=True, indent=4, ensure_ascii=False)


#join voice
@bot.hybrid_command(name = "join", with_app_command = True, description = "Join voice channel.")
async def join(ctx):
    if ctx.author.voice is None:
        return await ctx.send("You are not connected to a voice channel.")
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
    await ctx.author.voice.channel.connect()
    await ctx.send("Joined")

#leave voice
@bot.hybrid_command(name = "leave", with_app_command = True, description = "Leave voice channel.")
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        return await ctx.send("Left")
    await ctx.send("I am not connected to a voice channel.")


#number of servers
@bot.hybrid_command(name = "guilds", with_app_command = True, description = "guilds.")
async def guilds(ctx):
    if ctx.author.id == YOUR_ID: # if you want only you to use this command
        await ctx.send(f"I'm in {str(len(bot.guilds))} servers!")
    else:
        await ctx.send("You can not use this command..", ephemeral=True)


#list of servers
@bot.hybrid_command(name = "guildslist", with_app_command = True, description = "guildslist.")
async def guildslist(ctx):
    if ctx.author.id == YOUR_ID: # if you want only you to use this command
        servers = list(bot.guilds)
        await ctx.send(f"Connected on {str(len(bot.guilds))} servers:\n>>> " + '\n'.join(server.name for server in servers))
    else:
        await ctx.send("You can not use this command..", ephemeral=True)


bot.run(YOUR_TOKEN)
