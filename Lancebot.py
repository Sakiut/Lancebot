# -*- coding: utf-8 -*-

import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import formatter
from libraries.perms import *
from libraries.library import *
from libraries import anilist
from libraries import moderation
from libraries import feh

import random
import os
import math
import traceback
import pickle
import urllib

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

print('[FTS] Connecting...')

freshestMemes = [
    "mem/meme1.jpeg",
    "mem/meme2.jpeg",
    "mem/meme3.jpeg",
    "mem/meme6.jpeg",
    "mem/meme7.jpeg",
    "mem/meme8.jpeg",
    "mem/meme9.jpeg",
    "mem/meme10.jpeg",
    "mem/meme11.jpeg",
    "mem/meme12.jpeg",
    "mem/meme14.jpeg",
    "mem/meme15.jpeg"
]

bot = commands.Bot(command_prefix=commands.when_mentioned_or('.'), description="Lancebot")

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '`{0.title}` uploaded by *{0.uploader}* and requested by *{1.display_name}*'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: `{0[0]}m {0[1]}s`]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

class Anime:

    def __init__(self,bot):
        self.bot = bot
        self.token = None
        self.params = {
            "grant_type":"client_credentials",
            "client_id": getAniClientID(),
            "client_secret": getAniClientSecret()
        }

    @commands.group(pass_context=True)
    async def anilist(self, ctx):
        """Commandes de requêtes d'informations sur des animes et mangas
        de la base de données d'Anilist.
        Langue de la base de données : EN

        Utilisation :
            .anilist anime <anime à rechercher>
            .anilist manga <manga à rechercher>"""

        if ctx.invoked_subcommand is None:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("```md\nSyntaxe invalide. Voir .help anilist pour plus d'informations sur comment utiliser cette commande.\n```")

    @anilist.command(pass_context=True, no_pm=False)
    async def anime(self, ctx, *, anime : str):
        """Récupère les informations concernant un anime
        Base de données utilisée : AniList.co
        Langue de la base de données : EN"""

        await self.bot.delete_message(ctx.message)
        tmp = await self.bot.say('Processing request')

        if self.token == None:
            self.token = anilist.auth(self.params)

        try:
            results = anilist.getAnimes(anime, self.token)
            results = results[:9]
        except KeyError as e:
            await self.bot.delete_message(tmp)
            fmt = '```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
            return

        ResultsEmbed = discord.Embed()
        ResultsEmbed.title = "Choisissez parmi ces résultats :"
        ResultsEmbed.colour = 0x3498db
        ResultsEmbed.description = ""
        ResultsEmbed.set_footer(text = anime)

        i = 0
        for x in results:
            i += 1
            j = str(i)
            if i > 9:
                break
            else:
                ResultsEmbed.description += "[{}]() - {} - {}\n".format(j, x[0], x[1])

        await self.bot.delete_message(tmp)
        resultsMessage = await self.bot.say(embed=ResultsEmbed)

        emotes = [
            u"\u0031\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0032\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0033\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0034\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0035\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0036\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0037\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0038\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0039\N{COMBINING ENCLOSING KEYCAP}"
        ]

        listing = []
        for emote, title in zip(emotes, results):
            dc = {emote:title}
            listing.append(dc)

        for x in range(0, len(results)):
            await self.bot.add_reaction(resultsMessage, emotes[x])

        await asyncio.sleep(1)
        res = await self.bot.wait_for_reaction(emotes, message=resultsMessage)
        react = res.reaction.emoji
        await self.bot.clear_reactions(resultsMessage)
        await self.bot.delete_message(resultsMessage)

        for l in listing:
            try:
                title = l[react]
            except KeyError:
                continue

        index = results.index(title)

        tmp = await self.bot.say("Processing request for {}".format(title))

        data = anilist.getAnimeInfo(anime, self.token, int(index))

        AnimeEmbed = discord.Embed()
        AnimeEmbed.title = str(data['title_english']) + " | " + str(data['title_japanese']) + " (" + str(data['id']) + ")"
        AnimeEmbed.colour = 0x3498db
        AnimeEmbed.set_thumbnail(url=data["image_url_lge"])
        AnimeEmbed.add_field(name = "Type", value = data["type"])
        AnimeEmbed.add_field(name = "Episodes", value = data['total_episodes'])
        AnimeEmbed.add_field(name = "Source", value = data['source'])
        AnimeEmbed.add_field(name = "Status", value = data['airing_status'].capitalize())
        AnimeEmbed.add_field(name = "Genre(s)", value = anilist.getAnimeGenres(data), inline = False)
        AnimeEmbed.add_field(name = "Episode Length", value = str(data['duration']) + " mins/ep")
        AnimeEmbed.add_field(name = "Score", value = str(data['average_score']) + " / 100")
        AnimeEmbed.add_field(name = "Synopsis", value = anilist.formatAnimeDescription(data), inline = False)
        AnimeEmbed.set_footer(text = anilist.formatAnimeDate(data))

        await self.bot.delete_message(tmp)
        await self.bot.say(embed=AnimeEmbed)

    @anilist.command(pass_context=True, no_pm=False)
    async def manga(self, ctx, *, anime : str):
        """Récupère les informations concernant un manga
        Base de données utilisée : AniList.co
        Langue de la base de données : EN"""

        await self.bot.delete_message(ctx.message)
        tmp = await self.bot.say('Processing request')

        if self.token == None:
            self.token = anilist.auth(self.params)

        try:
            results = anilist.getMangas(anime, self.token)
            results = results[:9]
        except KeyError as e:
            await self.bot.delete_message(tmp)
            fmt = '```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
            return

        ResultsEmbed = discord.Embed()
        ResultsEmbed.title = "Choisissez parmi ces résultats :"
        ResultsEmbed.colour = 0x3498db
        ResultsEmbed.description = ""
        ResultsEmbed.set_footer(text = anime)

        i = 0
        for x in results:
            i += 1
            j = str(i)
            if i > 9:
                break
            else:
                ResultsEmbed.description += "[{}]() - {} - {}\n".format(j, x[0], x[1])

        await self.bot.delete_message(tmp)
        resultsMessage = await self.bot.say(embed=ResultsEmbed)

        emotes = [
            u"\u0031\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0032\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0033\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0034\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0035\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0036\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0037\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0038\N{COMBINING ENCLOSING KEYCAP}", 
            u"\u0039\N{COMBINING ENCLOSING KEYCAP}"
        ]

        listing = []
        for emote, title in zip(emotes, results):
            dc = {emote:title}
            listing.append(dc)

        for x in range(0, len(results)):
            await self.bot.add_reaction(resultsMessage, emotes[x])

        await asyncio.sleep(1)
        res = await self.bot.wait_for_reaction(emotes, message=resultsMessage)
        react = res.reaction.emoji
        await self.bot.clear_reactions(resultsMessage)
        await self.bot.delete_message(resultsMessage)

        for l in listing:
            try:
                title = l[react]
            except KeyError:
                continue

        index = results.index(title)

        tmp = await self.bot.say("Processing request for {}".format(title))

        data = anilist.getMangaInfo(anime, self.token, int(index))

        if data['total_volumes'] == 0:
            data['total_volumes'] = '-'

        if data['total_chapters'] == 0:
            data['total_chapters'] = '-'

        MangaEmbed = discord.Embed()
        MangaEmbed.title = str(data['title_english']) + " | " + str(data['title_japanese']) + "\n(" + str(data['id']) + ")"
        MangaEmbed.colour = 0x3498db
        MangaEmbed.set_thumbnail(url=data['image_url_lge'])
        MangaEmbed.add_field(name = 'Type', value = data['type'])
        MangaEmbed.add_field(name = 'Volumes', value = str(data['total_volumes']))
        MangaEmbed.add_field(name = 'Chapters', value = str(data['total_chapters']))
        MangaEmbed.add_field(name = 'Status', value = data["publishing_status"].capitalize())
        MangaEmbed.add_field(name = 'Genre(s)', value = anilist.getAnimeGenres(data), inline = False)
        MangaEmbed.add_field(name = 'Score', value = str(data['average_score']) + " / 100")
        MangaEmbed.add_field(name = "Synopsis", value = anilist.formatAnimeDescription(data), inline = False)
        MangaEmbed.set_footer(text = anilist.formatAnimeDate(data))

        await self.bot.delete_message(tmp)
        await self.bot.say(embed=MangaEmbed)

class Vote:

    def __init__(self,bot):
        self.bot = bot
        self.VoteState = None
        self.Mess = None
        self.Requester = None
        self.subject = None
        self.Voters = []
        self.oui = None
        self.non = None

    @commands.group(pass_context=True)
    async def vote(self, ctx):
        """Commandes de vote.

        Utilisation :
            .vote start <sujet du vote>
            .vote stop"""

        if ctx.invoked_subcommand is None:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("```md\nSyntaxe invalide. Voir .help vote pour plus d'informations sur comment utiliser cette commande.\n```")

    @vote.command(pass_context=True, no_pm=True)
    async def start(self, ctx, *, subject : str):
        """Démarrer un vote"""

        await self.bot.delete_message(ctx.message)
        if self.VoteState == None:

            self.subject = subject
            self.Requester = ctx.message.author
            self.VoteState = True
            self.Voters = []
            self.oui = 0
            self.non = 0

            self.VoteEmbed = discord.Embed()
            self.VoteEmbed.title = "Vote : " + self.subject
            self.VoteEmbed.colour = 0x3498db
            self.VoteEmbed.set_footer(text = "Requested by {0}".format(self.Requester.name), icon_url = self.Requester.avatar_url)
            self.VoteEmbed.add_field(name = "✅", value = self.oui)
            self.VoteEmbed.add_field(name = "❎", value = self.non)

            mess = await self.bot.say(embed=self.VoteEmbed)
            self.Mess = mess

            await self.bot.add_reaction(mess, "✅")
            await self.bot.add_reaction(mess, "❎")
            await asyncio.sleep(1)

            while self.VoteState == True:
                res = await self.bot.wait_for_reaction(["✅","❎"], message = self.Mess)
                user = res.user
                reaction = res.reaction

                if user not in self.Voters:
                    if reaction.emoji == "✅":
                        await self.bot.remove_reaction(reaction.message, "✅", user)
                        self.Voters.append(user)
                        self.oui += 1
                        self.VoteEmbed.set_field_at(0, name = "✅", value = self.oui)

                        await self.bot.edit_message(self.Mess, embed=self.VoteEmbed)

                    elif reaction.emoji == "❎":
                        await self.bot.remove_reaction(reaction.message, "❎", user)
                        self.Voters.append(user)
                        self.non += 1
                        self.VoteEmbed.set_field_at(1, name = "❎", value = self.non)

                        await self.bot.edit_message(self.Mess, embed=self.VoteEmbed)
                    else:
                        await self.bot.remove_reaction(reaction.message, reaction.emoji, user)
                else:
                    await self.bot.remove_reaction(reaction.message, reaction.emoji, user)
                    tmp = await self.bot.send_message(self.Mess.channel, "{0.mention} Vous avez déjà voté".format(user))
                    await asyncio.sleep(5)
                    await self.bot.delete_message(tmp)

        else:
            tmp = await self.bot.say('Vote déjà en cours')
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

    @vote.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Arrêter le vote en cours
        Utilisable uniquement par le demandeur du vote déjà en cours."""

        await self.bot.delete_message(ctx.message)
        if self.VoteState == True:
            self.VoteEmbed.title = "Vote : " + self.subject + " [TERMINÉ]"
            await self.bot.edit_message(self.Mess, embed=self.VoteEmbed)
            await self.bot.clear_reactions(self.Mess)
            self.VoteState = None
        else:
            tmp = await self.bot.say('Aucun vote en cours')
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

class Admin:
    """Commandes d'administration et de gestion"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    @commands.command(pass_context=True, no_pm=True)
    async def setgame(self, ctx, *, game : str):
        """Définit le jeu du bot"""

        member = ctx.message.author
        await self.bot.delete_message(ctx.message)
        if member.server_permissions.administrator == True:
            await self.bot.change_presence(game=discord.Game(name=game))
            print('[FTS] Game changed to', game)
        else:
            await self.bot.say("Vous n'êtes pas administrateur")
            print('[FTS] SetGame : Command aborted : User is not an administrator')

    @commands.command(pass_context=True, no_pm=True)
    async def perms(self, ctx, *, user=None):
        """Donne les permissions du joueur choisi"""

        if user == None:
            member = ctx.message.author
        else:
            user = str(user)
            member = ctx.message.server.get_member_named(user)

        if member == None:
            await self.bot.say("{1} L'utilisateur {0} est inconnu".format(user, ctx.message.author.mention))
        else:
            tmp = await self.bot.say("Récupération des permissions...")

            perms = [
                get_perm_admin(member),
                get_perm_create_instant_invite(member),
                get_perm_kick_members(member),
                get_perm_ban_members(member),
                get_perm_manage_channels(member),
                get_perm_manage_server(member),
                get_perm_add_reactions(member),
                get_perm_send_tts_messages(member),
                get_perm_manage_messages(member),
                get_perm_mute(member),
                get_perm_deafen(member),
                get_perm_send_embed_links(member),
                get_perm_attach_files(member),
                get_perm_mention_everyone(member),
                get_perm_external_emojis(member),
                get_perm_change_nickname(member),
                get_perm_manage_nicknames(member),
                get_perm_manage_roles(member),
                get_perm_manage_webhooks(member),
                get_perm_manage_emojis(member),
                get_perm_view_audit_logs(member)
            ]

            titles = [
                "Permissions administrateur",
                "Créer invitations",
                "Éjecter les membres",
                "Bannir les membres",
                "Gérer les channels",
                "Gérer le serveur",
                "Ajouter des réactions",
                "Envoyer des messages tts",
                "Gérer les messages",
                "Rendre muet",
                "Rendre sourd",
                "Envoyer des messages Embed",
                "Envoyer des pièces jointes",
                "Mentionner @everyone",
                "Utiliser des emojis externes au serveur",
                "Changer son pseudo",
                "Gérer les pseudos",
                "Gérer les roles",
                "Gérer les WebHooks",
                "Gérer les Emojis",
                "Voir les logs"
            ]

            MsgBase = ctx.message.author.mention + " Voici les permissions de " + member.mention + " : ```scheme\n"
            Msg = MsgBase

            for perm, title in zip(perms, titles):
                fmt = "[>] {0:45} {1:12}\n".format(title, perm)
                Msg += fmt

            Msg += "```"

            await self.bot.delete_message(ctx.message)
            await self.bot.delete_message(tmp)
            await self.bot.say(Msg)

            print('[FTS] Permissions message sent')

    @commands.command(pass_context=True, no_pm=True)
    async def userinfo(self, ctx, *, user=None):
        """Donne les informations concernant le joueur cité"""

        if user == None:
            member = ctx.message.author
        else:
            user = str(user)
            member = ctx.message.server.get_member_named(user)

        if member == None:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("{1} L'utilisateur {0} est inconnu".format(user, ctx.message.author.mention))
        else:
            await self.bot.delete_message(ctx.message)
            tmp = await self.bot.say("Chargement des informations...")

            try:
                RolesList = get_user_roles(member)
                createdAt = dateConverter(member.created_at)
                joinedAt = dateConverter(member.joined_at)
                Statut = str(member.status)
                StatutFinal = Statut.capitalize()

                UserEmbed = discord.Embed()
                UserEmbed.title = "Userinfo for {0}#{1} [{2}]:".format(member.name, member.discriminator, member.top_role)
                UserEmbed.colour = 0x3498db
                UserEmbed.set_thumbnail(url=member.avatar_url)
                UserEmbed.add_field(name = "Surnom", value = member.nick)
                UserEmbed.add_field(name = "ID", value = member.id)
                UserEmbed.add_field(name = "Discriminateur", value = member.discriminator)
                UserEmbed.add_field(name = 'Statut', value = StatutFinal)
                UserEmbed.add_field(name = 'Joue à', value = member.game)
                UserEmbed.add_field(name = 'Compte créé le', value = createdAt)
                UserEmbed.add_field(name = 'A rejoint le serveur le', value = joinedAt)
                UserEmbed.add_field(name = "Roles", value = RolesList)
                UserEmbed.set_footer(text = "Requested by {0}".format(ctx.message.author.name), icon_url = ctx.message.author.avatar_url)

                await self.bot.delete_message(tmp)
                await self.bot.say(embed=UserEmbed)

            except Exception as e:
                fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
                await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    @commands.command(pass_context=True, no_pm=True)
    async def serverinfo(self, ctx):
        """Donne les informations du serveur"""

        server = ctx.message.server
        await self.bot.delete_message(ctx.message)
        tmp = await self.bot.say('Processing request...')
        VerifLevel = str(server.verification_level)

        ServerEmbed = discord.Embed()
        ServerEmbed.colour = 0x3498db
        ServerEmbed.set_thumbnail(url=server.icon_url)
        ServerEmbed.add_field(name = "Server Name", value = server.name)
        ServerEmbed.add_field(name = "Server ID", value = server.id)
        ServerEmbed.add_field(name = "Owner's Name", value = server.owner.name)
        ServerEmbed.add_field(name = "Owner's ID", value = server.owner.id)
        ServerEmbed.add_field(name = "Text Channels", value = str(len(getTextChannels(server))))
        ServerEmbed.add_field(name = "Voice Channels", value = str(len(getVoiceChannels(server))))
        ServerEmbed.add_field(name = "Users", value = server.member_count)
        ServerEmbed.add_field(name = "Verification level", value = VerifLevel.upper())
        ServerEmbed.add_field(name = "Roles Count", value = str(len(server.role_hierarchy)))
        ServerEmbed.add_field(name = "Region", value = formatServerRegion(server.region))
        ServerEmbed.add_field(name = "Creation Date", value = dateConverter(server.created_at))
        ServerEmbed.add_field(name = "Emotes Count", value = str(len(server.emojis)))
        ServerEmbed.add_field(name = "Roles", value = formatServerRoles(server.role_hierarchy), inline=False)
        ServerEmbed.add_field(name = "Emojis", value = formatEmojis(server.emojis), inline = False)
        ServerEmbed.set_footer(text = "Requested by {0}".format(ctx.message.author.name), icon_url = ctx.message.author.avatar_url)

        await self.bot.delete_message(tmp)
        await self.bot.say(embed=ServerEmbed)

    @commands.command(pass_context=True, no_pm=True)
    async def convoque(self, ctx, user=None, *, reason):
        """Envoie une convocation au joueur cité

        Nécessite le droit de ban"""

        author = ctx.message.author
        if author.server_permissions.ban_members == True:
            if user == None:
                member = ctx.message.author
            else:
                user = str(user)
                member = ctx.message.server.get_member_named(user)

            if member == None:
                await self.bot.delete_message(ctx.message)
                await self.bot.say("{1} L'utilisateur {0} est inconnu".format(user, ctx.message.author.mention))
            else:
                await self.bot.delete_message(ctx.message)
                tmp = await self.bot.say("Processing...")

                ConvocEmbed = discord.Embed()
                ConvocEmbed.title = "Convocation"
                ConvocEmbed.colour = 0x3498db
                ConvocEmbed.set_thumbnail(url=member.avatar_url)
                ConvocEmbed.description = "Vous avez été convoqué par l'administration du serveur **{0}** pour la raison qui suit.\n\
Vous êtes prié de vous rendre sur le serveur dans les plus brefs délais et de vous mettre en contact avec un des administrateurs ou des modérateurs".format(ctx.message.server.name)
                ConvocEmbed.add_field(name = 'Raison', value = reason)
                ConvocEmbed.set_footer(text = "Requested by {0}".format(ctx.message.author.name), icon_url = ctx.message.author.avatar_url)

                server = ctx.message.server
                Channels = server.channels
                End = []

                Return = False

                for chan in list(Channels):
                    Name = str(chan.name)
                    Type = str(chan.type)
                    if "moderation" in str(chan.name):
                        if Type is "text":
                            ModChan = chan
                            Return = True

                if Return is not True:
                    ModChan = await self.bot.create_channel(server, 'moderation', type=discord.ChannelType.text)

                await self.bot.delete_message(tmp)
                await self.bot.send_message(member, embed=ConvocEmbed)
                await self.bot.send_message(ModChan, "@here Une convocation a été envoyée à {0} par {1}, raison : {2}".format(member.mention, ctx.message.author.mention, reason))

        else:
            await self.bot.say("```\nVous n'avez pas la permission de convoquer un utilisateur\n```")

    @commands.command(pass_context=True, no_pm=False)
    async def rules(self, ctx, line="all", *, user:discord.Member=None):
        """Envoie le règlement du serveur à un joueur
        Si aucun joueur n'est spécifié, le règlement est envoyé dans le chat. 
        On peut spécifier une ligne précise du règlement."""
        try:
            rules = getServerRules()
            rulesLines = getSplittedRules()
            line = line.lower()

            await self.bot.delete_message(ctx.message)

            try:
                line = int(line)
                line -= 1
            except ValueError as e:
                if line == "all":
                    pass
                else:
                    raise ValueError("Seuls soit un entier soit la mention all (insensible à la casse) est attendue.")

            if user == None:
                user = ctx.message.channel

            if ctx.message.author.server_permissions.manage_messages == True:
                if line == "all":
                    rules = rules.split("--\n")
                    await self.bot.send_message(user, rules[0])
                    await self.bot.send_message(user, rules[1])
                else:
                    try:
                        base = "*Extrait du règlement :*"
                        if line >= 6 and line < 24:
                            base += "\nCe qui est interdit :"
                        msg = base + "\n```md\n" + rulesLines[line] + "\n```"
                    except IndexError as e:
                        raise IndexError("Cette règle n'existe pas")
                    await self.bot.send_message(user, msg)

                if type(user) != discord.Channel:
                    tmp = await self.bot.say("Message sent")
                    await asyncio.sleep(10)
                    await self.bot.delete_message(tmp)

        except Exception as e:
            print(e)
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    @commands.command(pass_context=True, no_pm=False)
    async def disconnect(self, ctx):
        """Déconnecte le bot - Bot Master uniquement"""
        requester = ctx.message.author
        await self.bot.delete_message(ctx.message)
        if requester.id == '187565415512276993':
            await self.bot.send_message(bot.get_channel('330033804330663937'), "```Déconnection du bot```")
            print('[FTS] Déconnexion...')
            bot.logout()
            print('[FTS] Logged out')
            bot.close()
            print('[FTS] Connexions closed')
            os.system('pause')
            exit()
        else:
            await self.bot.say("Vous n'êtes pas le Bot Master")

    @commands.command(pass_context=True, no_pm=False)
    async def test(self, ctx):
        """Teste le bot [10 secondes]"""
        await self.bot.delete_message(ctx.message)
        tmp = await self.bot.say("Test en cours :\n```\n|..........|\n```")
        i = 0
        bar = ""
        pt = ".........."
        while i < 10:
            i += 1
            bar += "█"
            pt = pt[:-1]
            await self.bot.edit_message(tmp, "Test en cours :\n```\n|"+ bar + pt +"|\n```")
            await asyncio.sleep(1)
        await self.bot.edit_message(tmp, "```Test terminé```")
        await asyncio.sleep(5)
        await self.bot.delete_message(tmp)

    @commands.command(pass_context=True, no_pm=True)
    async def randomplayer(self, ctx):
        """Retourne un membre du serveur au hasard"""
        await self.bot.delete_message(ctx.message)
        server = ctx.message.server
        members = getServerMembers(server)

        length = len(members) - 1
        rand = random.randint(0, length)

        member = members[rand]

        MbrEmbed = discord.Embed()
        MbrEmbed.colour = 0x3498db
        MbrEmbed.title = "Random Player :"
        MbrEmbed.description = member
        MbrEmbed.set_footer(text = "Requested by {0}".format(ctx.message.author.name), icon_url = ctx.message.author.avatar_url)
        await self.bot.say(embed=MbrEmbed)

class Messages:
    """Commandes Textuelles"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    @commands.command(pass_context=True, no_pm=False)
    async def hi(self, ctx):
        """Fall to Sky vous salue"""
        await self.bot.say("Salut {0.message.author.mention} !".format(ctx))
        print('[FTS] Hello Message sent')

    @commands.command(pass_context=True, no_pm=False)
    async def website(self, ctx):
        """Affiche le site web du serveur"""
        await self.bot.say("{0.message.author.mention} Site web du serveur : {1}".format(ctx, getWebSite()))
        print("[FTS] Website's URL sent")

    @commands.command(pass_context=True, no_pm=False)
    async def meme(self, ctx):
        """Affiche une meme random parmi la bibliothèque"""
        print('[FTS] Sending Meme...')
        mem = random.choice(freshestMemes)
        await self.bot.send_file(ctx.message.channel, mem)
        print('[FTS] Meme Sent')

    @commands.command(pass_context=True, no_pm=False)
    async def echo(self, ctx, *, mess : str):
        """Répète le message de l'utilisateur"""
        await self.bot.delete_message(ctx.message)
        await self.bot.say(mess)
        print('[FTS] Message sent :', mess)

    @commands.command(pass_context=True, no_pm=True)
    async def mpecho(self, ctx, user:discord.Member, *, mess : str):
        """Envoie un MP via le bot"""
        await self.bot.delete_message(ctx.message)
        await self.bot.send_message(user, mess)
        print('[FTS] Message sent to {0.name} : {1}'.format(user, mess))

    @commands.command(pass_context=True, no_pm=True)
    async def report(self, ctx, user: discord.Member, *, reason: str):
        """Reporte un utilisateur au staff"""
        
        await self.bot.delete_message(ctx.message)

        server = ctx.message.server
        Channels = server.channels
        End = []

        Return = False

        for chan in list(Channels):
            Name = str(chan.name)
            Type = str(chan.type)
            if "moderation" in str(chan.name):
                if Type is "text":
                    ModChan = chan
                    Return = True

        if Return is not True:
            ModChan = await self.bot.create_channel(server, 'moderation', type=discord.ChannelType.text)

        await self.bot.send_message(ModChan, "{0} a été report par {1}, raison : {2}, @here".format(user.mention, ctx.message.author.mention, reason))
        print('[FTS] {0} has been reported by {1}'.format(user, ctx.message.author))

    @commands.command(pass_context=True, no_pm=False)
    async def roll(self, ctx, start: int=0, end: int=10):
        """Donne un nombre aléatoire entre [start] et [end]"""
        rand = random.randint(start, end)

        try:

            RollEmbed = discord.Embed()
            RollEmbed.title = 'Roll'
            RollEmbed.colour = 0x3498db
            RollEmbed.description = str(rand)

            await self.bot.say(embed=RollEmbed)

        except Exception as e:
                fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
                await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))


    @commands.command(pass_context=True, no_pm=True)
    async def purge(self, ctx, limit=10):
        """Supprime le nombre de messages spécifié

        10 Messages seront supprimés par défaut

        Cette commande ne peut être utilisée que par les utilisateurs ayant la permission de gérer les messages
        """

        member = ctx.message.author
        if member.server_permissions.manage_messages == True:
            print('[FTS] Proceding purge...')

            await self.bot.purge_from(ctx.message.channel, limit = limit)

            print('[FTS] Purge done')
            print('[FTS] Deleted {0} messages'.format(limit))
        else:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("Vous n'avez pas l'autorisation de gérer les messages")
            print('[FTS] Purge : Command aborted : User do not have manage_messages permission')

    @commands.command(pass_context=True, no_pm=True)
    async def purgeuser(self, ctx, limit=10, *, user:discord.Member):
        """Supprime le nombre de messages spécifié du membre choisi

        10 Messages seront scannés par défaut

        Cette commande ne peut être utilisée que par les utilisateurs ayant la permission de gérer les messages
        """
        await self.bot.delete_message(ctx.message)

        member = ctx.message.author
        if member.server_permissions.manage_messages == True:

            def compare(m):
                return m.author == user 

            print('[FTS] Proceding purge...')

            deleted = await self.bot.purge_from(ctx.message.channel, limit = limit, check = compare)

            FeedBack = await self.bot.say("```{2} messages de {0} parmi les {1} derniers messages supprimés```".format(user.name, limit, len(deleted)))
            await asyncio.sleep(10)
            await self.bot.delete_message(FeedBack)

            print('[FTS] Purge done')
            print('[FTS] Deleted {0} messages'.format(limit))
        else:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("Vous n'avez pas l'autorisation de gérer les messages")
            print('[FTS] Purge : Command aborted : User do not have manage_messages permission')

    @commands.command(pass_context=True, no_pm=False)
    async def messcount(self, ctx, limit=1000):
        """Donne le nombre de messages envoyés dans le channel"""
        await self.bot.delete_message(ctx.message)
        counter = 0
        tmp = await self.bot.say('Calculating messages...')
        print('[FTS] Calculating...')
        async for log in bot.logs_from(ctx.message.channel, limit):
            if log.author == ctx.message.author:
                counter += 1

        await self.bot.delete_message(tmp)
        await self.bot.say('{0.message.author.mention} You have sent `{1}` messages in this channel'.format(ctx, counter))
        print('[FTS] Calculation done and sent')

    @commands.command(pass_context=True, no_pm=True)
    async def emojis(self, ctx):
        """Donne la liste des emojis du serveur"""
        
        await self.bot.delete_message(ctx.message)

        EmojiEmbed = discord.Embed()
        EmojiEmbed.colour = 0x3498db
        EmojiEmbed.title = "Emojis for {0}".format(ctx.message.server.name)
        EmojiEmbed.description = formatEmojis(ctx.message.server.emojis)

        await self.bot.say(embed = EmojiEmbed)

class Music:
    """Commandes Vocales"""
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel):
        """Rejoindre un channel vocal"""
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

        print('[FTS] Successfull joined {0} voice channel'.format(channel.name))

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Rejoint le channel vocal de l'émetteur"""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
            print('[FTS] Successfull Summoned')
        else:
            await state.voice.move_to(summoned_channel)

        return True


    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        """Lance une musique

        Rejoint la fin de la queue

        Cette commande cherche la musique sur YouTube en priorité
        Liste des sites supportés disponible ici :
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)

        print('[FTS] Playing ' + str(entry))

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int):
        """Changer le volume de la musique en cours"""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

        print('[FTS] Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Met la musique en pause"""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

        print('[FTS] Music Paused')

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Reprend la musique"""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

        print('[FTS] Music Resumed')

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Coupe la musique en cours et quitte le channel vocal

        Clear également la queue
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

        print('[FTS] Music Stopped')

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote pour passer la musique. 
        La personne qui a demandé la musique peut la passer sans vote.

        3 votes sont nécessaires pour que la musique soit passée
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
            print('[FTS] Music skipped by Requester')

        elif voter.server_permissions.administrator == True:
            await self.bot.say('Admin requested skipping song...')
            state.skip()
            print('[FTS] Music skipped by Admin')

        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
                print('[FTS] Music skipped by vote')
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Montre quelle musique est jouée actuellement"""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))
            print('[FTS] Now playing {} [skips: {}/3]'.format(state.current, skip_count))

class Moderation:
    """Commandes de modération"""

    def __init__(self, bot):
        self.bot = bot
        self.data = moderation.start()

    def getModChan(self, server):
        Channels = server.channels
        End = []
        Return = False
        for chan in list(Channels):
            Name = str(chan.name)
            Type = str(chan.type)
            if "moderation" in str(chan.name):
                if Type is "text":
                    ModChan = chan
                    Return = True
        if Return is not True:
            ModChan = self.bot.create_channel(server, 'moderation', type=discord.ChannelType.text)
        return ModChan

    @commands.command(pass_context=True, no_pm=True)
    async def warn(self, ctx, user:discord.Member):
        """Avertit un utilisateur
        Utilisable uniquement par la modération (permissions de ban et au-dessus)"""
        await self.bot.delete_message(ctx.message)
        if ctx.message.author.server_permissions.ban_members == True:
            server = ctx.message.server
            ModChan = self.getModChan(server)
            self.data = moderation.warn(server, user, self.data)
            try:
                level = self.data[server.name][user.name]
            except KeyError:
                level = 1
            if level < 3:
                fmt = discord.Embed()
                fmt.title = ("ATTENTION")
                fmt.colour = 0x3498db
                fmt.set_thumbnail(url=server.icon_url)
                fmt.description = "Vous avez été averti-e par un-e modérateur-trice du serveur **{0}** en raison de votre comportement.\n\
Vous avez actuellement {1} avertissement(s) à votre actif. Au bout de trois, une motion de convocation disciplinaire sera lancée et vous serez lourdement sanctionné-e par l'administration de notre serveur.\n\
Merci de prendre garde à votre comportement à l'avenir.".format(server.name, str(level))
                await self.bot.send_message(user, embed=fmt)
                msg = "@here {0.name} a atteint {1} avertissement(s).".format(user, str(level))
                await self.bot.send_message(ModChan, msg)
            elif level == 3:
                fmt = discord.Embed()
                fmt.title = ("ATTENTION")
                fmt.colour = 0x3498db
                fmt.set_thumbnail(url=server.icon_url)
                fmt.description = "Vous avez été averti-e par un-e modérateur-trice du serveur **{0}** en raison de votre comportement.\n\
Vous avez actuellement {1} avertissement(s) à votre actif. Au bout de trois, une motion de convocation disciplinaire sera lancée et vous serez lourdement sanctionné-e par l'administration de notre serveur.\n\
Merci de prendre garde à votre comportement à l'avenir.".format(server.name, str(level))
                await self.bot.send_message(user, embed=fmt)
                msg = "@here {0.name} a atteint 3 avertissements. Merci de prendre les mesures nécessaires.".format(user)
                await self.bot.send_message(ModChan, msg)
            else:
                msg = "@here {0.name} a atteint {1} avertissements. Il ou elle a dépassé la limite. Merci de prendre les mesures nécessaires.".format(user, str(level))
                await self.bot.send_message(ModChan, msg)
        else:
            await self.bot.say("```\nVous n'avez pas la permission d'avertir un utilisateur\n```")


    @commands.command(pass_context=True, no_pm=True)
    async def pardon(self, ctx, user:discord.Member):
        """Pardonne un utilisateur (lui retire un avertissement)
        Utilisable uniquement par la modération (permissions de ban et au-dessus)"""
        await self.bot.delete_message(ctx.message)
        if ctx.message.author.server_permissions.ban_members == True:
            server = ctx.message.server
            ModChan = self.getModChan(server)
            if server.name in self.data.keys():
                if user.name in self.data[server.name].keys():
                    level = self.data[server.name][user.name]
                    if level <= 1:
                        del self.data[server.name][user.name]
                        msg = "Un-e modérateur-trice a retiré votre seul avertissement. Vous n'avez plus aucun antécédent."
                        fmt = "@here {0.mention} a pardonné à {1.mention}. Il n'a plus aucun antécédent.".format(ctx.message.author, user)
                    else:
                        self.data[server.name][user.name] -= 1
                        level = self.data[server.name][user.name]
                        msg = "Un-e modérateur-trice vous a retiré un avertissement. Il vous reste {0} avertissement(s).".format(str(level))
                        fmt = "@here {0.mention} a pardonné à {1.mention}. Il n'a plus que {2} avertissements.".format(ctx.message.author, user, str(level))
                    await self.bot.send_message(user, msg)
                    await self.bot.send_message(ModChan, fmt)
                    f = open(fileName, "wb")
                    p = pickle.Pickler(f)
                    p.dump(self.data)
                    f.close()
                else:
                    await self.bot.say("```\nL'utilisateur n'a aucun antécédent\n```")
            else:
                await self.bot.say("```\nL'utilisateur n'a aucun antécédent\n```")
        else:
            await self.bot.say("```\nVous n'avez pas la permission de pardonner un utilisateur\n```")

    @commands.command(pass_context=True, no_pm=True)
    async def checkwarn(self, ctx, user:discord.Member):
        """Montre le nombre d'avertissements d'un utilisateur"""
        await self.bot.delete_message(ctx.message)
        server = ctx.message.server
        level = moderation.getWarns(server, user, self.data)
        fmt = discord.Embed()
        fmt.colour = 0x3498db
        fmt.set_author(name = user.name, icon_url=user.avatar_url)
        fmt.description = "{0} avertissements".format(str(level))
        await self.bot.say(embed=fmt)

class FEH:
    """Commandes de profil Fire Emblem Heroes"""

    def __init__(self,bot):
        self.bot = bot
        self.data = feh.dataGet()

    @commands.group(pass_context=True, no_pm=True)
    async def feh(self, ctx):
        """Commandes Fire Emblem Heroes

        Ces commandes vous permettront de gérer et de consulter des profils utilisateur appartenant
        aux membres du serveur.

        Ces profils sont remplis par les utilisateurs - donc par vous - sans aucun filtre. Merci donc
        de respecter le règlement du serveur pour une bonne entente générale, et de signaler toute
        donnée non appropriée sur un profil via la commande .report (anonyme)

        Utilisation des commandes :
            .feh create <pseudo du compte FEH>
            .feh delete
            .feh add [nom de la case à ajouter] <donnée à mettre dans la case>
            .feh remove [nom de la case à supprimer]
            .feh seticon <url de l'icône à ajouter>
            .feh info <pseudo Discord du profil à consulter>"""

        if ctx.invoked_subcommand is None:
            await self.bot.delete_message(ctx.message)
            await self.bot.say("```md\nSyntaxe invalide. Voir .help feh pour plus d'informations sur comment utiliser cette commande.\n```")

    @feh.command(pass_context=True, no_pm=True)
    async def create(self, ctx, pseudo):
        """Créer son profil
        
        Commande qui crée un profil utilisateur FEH qui sera accessible à tous les membres du serveur.
        Merci d'indiquer votre pseudonyme in-game.
        
        Il s'agit d'un profil que vous remplirez vous-même, aucune donnée n'est filtrée, merci
        de respecter le règlement du serveur pour une bonne entente générale."""

        await self.bot.delete_message(ctx.message)

        perso = feh.User(pseudo)
        feh.dataUpdate(self.data, perso, ctx.message.author.id)
        feh.dataSave(self.data)

        tmp = await self.bot.say("```\nProfil créé\n```")
        await asyncio.sleep(5)
        await self.bot.delete_message(tmp)

    @feh.command(pass_context=True, no_pm=True)
    async def delete(self, ctx):
        """Supprime votre profil"""

        await self.bot.delete_message(ctx.message)

        try:
            feh.dataRemove(self.data, ctx.message.author.id)
            feh.dataSave(self.data)

            tmp = await self.bot.say("```\nProfil supprimé\n```")
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)
        
        except KeyError as e:
            tmp = await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, e))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

    @feh.command(pass_context=True, no_pm=True)
    async def add(self, ctx, name, *, value):
        """Ajoute une information à votre profil
        
        Vous devez avoir déjà créé un profil avec .fehcreate pour utiliser cette commande.
        Votre profil est un tableau en deux colonnes, un titre et une valeur.
        
        [name] est le titre et [value] est la valeur de cette ligne.
        Il s'agit d'un profil que vous remplirez vous-même, aucune donnée n'est filtrée, merci
        de respecter le règlement du serveur pour une bonne entente générale."""

        await self.bot.delete_message(ctx.message)

        try:
            perso = feh.getFromData(self.data, ctx.message.author.id)
            perso.add(name, value)
            feh.dataUpdate(self.data, perso, ctx.message.author.id)
            feh.dataSave(self.data)

            tmp = await self.bot.say("```\nProfil de {}, ID {} mis à jour\n```".format(perso.pseudo, str(ctx.message.author.id)))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

        except KeyError as e:
            tmp = await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, e))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

    @feh.command(pass_context=True, no_pm=True)
    async def seticon(self, ctx, icon_url:str):
        """Ajoute une url d'icône à votre profil.
        Rappel : URL = Hyperlien = lien = "http://exemple.com/nomdemonicone.img"

        L'icône que vous avez choisie doit être entrée sous forme d'url conduisant 
        directementà l'image en question. Elle n'est pas téléchargée par le bot 
        et doit donc rester hébergée sur l'url que vous avez indiquée.

        Aucune donnée n'est filtrée, merci de respecter le règlement du serveur 
        pour une bonne entente générale."""

        await self.bot.delete_message(ctx.message)

        try:
            perso = feh.getFromData(self.data, ctx.message.author.id)
            perso.setIcon(icon_url)
            feh.dataUpdate(self.data, perso, ctx.message.author.id)
            feh.dataSave(self.data)

            tmp = await self.bot.say("```\nProfil de {}, ID {} mis à jour\n```".format(perso.pseudo, str(ctx.message.author.id)))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

        except KeyError as e:
            tmp = await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, e))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

    @feh.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, name):
        """Retire une information de votre profil
        
        Vous devez avoir déjà créé un profil avec .fehcreate pour utiliser cette commande.
        Votre profil est un tableau en deux colonnes, un titre et une valeur.
        [name] est le titre que vous avez donné à la ligne que vous souhaitez supprimer.
        
        Il s'agit d'un profil que vous remplirez vous-même, aucune donnée n'est filtrée, merci
        de respecter le règlement du serveur pour une bonne entente générale."""

        await self.bot.delete_message(ctx.message)

        try:
            perso = feh.getFromData(self.data, ctx.message.author.id)
            perso.remove(name)
            feh.dataUpdate(self.data, perso, ctx.message.author.id)
            feh.dataSave(self.data)

            tmp = await self.bot.say("```\nProfil de {}, ID {} mis à jour\n```".format(perso.pseudo, str(ctx.message.author.id)))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

        except KeyError as e:
            tmp = await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, e))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

    @feh.command(pass_context=True, no_pm=True)
    async def info(self, ctx, *, user=None):
        """Montre la fiche d'informations de la personne choisie.

        Les profils sont remplis sans filtre, merci de signaler tout problème, manquement
        aux conditions d'utilisation aux développeurs et aux modérateurs / administrateurs."""

        if user == None:
            user = ctx.message.author
        else:
            user = str(user)
            user = ctx.message.server.get_member_named(user)

        await self.bot.delete_message(ctx.message)

        try:
            perso = feh.getFromData(self.data, user.id)

            fmt = formatter.Paginator()

            bar = "+---------------+------------------------------------------+"
            head = "|{0:^15}| {1:^40} |".format("Title", "Value")
            fmt.add_line(bar)
            fmt.add_line(head)
            fmt.add_line(bar)

            for name, value in zip(perso.names, perso.values):
                lines = splitLength(value, 40)
                fmt.add_line("|{0:^15}| {1:40} |".format(str(name), str(lines[0])))
                del lines[0]

                for line in lines:
                    fmt.add_line("|{0:^15}| {1:40} |".format(str(""), str(line)))
                fmt.add_line("|{0:^15}| {1:40} |".format(str(""), str("")))

            fmt.add_line(bar)
            fmt.close_page()

            fehEmbed = discord.Embed()
            fehEmbed.set_author(name = user.name + " ({})".format(user.id), icon_url = user.avatar_url)
            fehEmbed.add_field(name = "Pseudo in-game", value = perso.pseudo, inline = False)
            fehEmbed.colour = 0x3498db
            fehEmbed.set_footer(text = "Requested by {0}".format(ctx.message.author.name), icon_url = ctx.message.author.avatar_url)

            if perso.icon != None:
                fehEmbed.set_thumbnail(url = perso.icon)

            fmtEmbed = discord.Embed()
            fmtEmbed.colour = 0x3498db

            await self.bot.say(embed = fehEmbed)
            for page in fmt.pages:
                fmtEmbed.description = page
                await self.bot.say(embed = fmtEmbed)
            
        except KeyError as e:
            tmp = await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, e))
            await asyncio.sleep(5)
            await self.bot.delete_message(tmp)

bot.add_cog(Messages(bot))
bot.add_cog(Music(bot))
bot.add_cog(Admin(bot))
bot.add_cog(Vote(bot))
bot.add_cog(Anime(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(FEH(bot))

@bot.event
async def on_member_join(member):
    server = member.server
    fmt = 'Bienvenue à {0.mention} sur {1.name} !'
    await bot.send_message(bot.get_channel('328262970364788738'), fmt.format(member, server))
    rules = getServerRules()
    await bot.send_message(member, rules)
    print('[FTS] {0.name} has joined the server'.format(member))

@bot.event
async def on_member_remove(member):
    server = member.server
    fmt = '{0.mention} est parti-e du serveur {1.name} !'
    await bot.send_message(bot.get_channel('328262970364788738'), fmt.format(member, server))
    print('[FTS] {0.name} has left the server'.format(member))

@bot.event
async def on_member_ban(member):
    server = member.server
    fmt = '{0.mention} a été banni-e du serveur {1.name} !'
    await bot.send_message(bot.get_channel('328262970364788738'), fmt.format(member, server))
    print('[FTS] {0.name} has been banned of the server'.format(member))

@bot.event
async def on_member_unban(server, member):
    fmt = "{0.mention} a été pardonné-e, il-elle n'est plus banni-e du serveur {1.name} !"
    await bot.send_message(bot.get_channel('328262970364788738'), fmt.format(member, server))
    print('[FTS] {0.name} has been unbanned of the server'.format(member))

@bot.event
async def on_server_emojis_update(before, after):
    before = set(before)
    after = set(after)

    n_e = after - before
    n_e = list(n_e)

    for e in n_e:
        Emoji = "<:{0}:{1}>".format(e.name, e.id)
        Embed = discord.Embed()
        Embed.colour = 0x3498db
        Embed.description = Emoji
        await bot.send_message(bot.get_channel('328263588911251456'), "Nouvel emoji !", embed = Embed)

@bot.event
async def on_ready():
    print('--------------------------')
    print('[FTS] Logged in as')
    print('[FTS]', bot.user.name)
    print('[FTS]', bot.user.id)
    print('--------------------------')
    await bot.change_presence(game=discord.Game(name='Fire Emblem Heroes'))

token = getToken()
bot.run(token)
