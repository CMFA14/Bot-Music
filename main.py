import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import os
import json
from aiohttp import web
import aiohttp_cors

import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
FILE_STATUS = "status.json"
FILE_COMANDOS = "comandos.json"
CAMINHO_FFMPEG = "./ffmpeg.exe"

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'musica_temp.%(ext)s', 
    'noplaylist': True,
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['configs', 'js'],
            'zerorating': ['1']
        }
    }
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents) # Mudei para ! para não confundir

music_queue = []
current_song_title = "Nada tocando"
is_playing = False

# --- LÓGICA DO BOT ---

def atualizar_status_file():
    dados = {
        "tocando": current_song_title,
        "fila": [m['title'] for m in music_queue],
        "status": "Tocando 🎵" if is_playing else "Parado ⏸️"
    }
    with open(FILE_STATUS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

async def tocar_proxima(voice_client):
    global current_song_title, is_playing
    if len(music_queue) > 0:
        song = music_queue.pop(0)
        search = song['source']
        current_song_title = f"Baixando: {search}..."
        atualizar_status_file()
        
        if os.path.exists("musica_temp.mp3"):
            try: os.remove("musica_temp.mp3")
            except: pass

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch:{search}" if "http" not in search else search, download=True))
                if 'entries' in info: info = info['entries'][0]
                current_song_title = info['title']
                is_playing = True
                atualizar_status_file()

            if os.path.exists("musica_temp.mp3"):
                source = discord.FFmpegPCMAudio("musica_temp.mp3", executable=CAMINHO_FFMPEG)
                def after_play(error):
                    global is_playing
                    is_playing = False
                    atualizar_status_file()
                    bot.loop.create_task(tocar_proxima(voice_client))
                voice_client.play(source, after=after_play)
        except Exception as e:
            print(f"Erro ao tocar: {e}")
            is_playing = False
            bot.loop.create_task(tocar_proxima(voice_client))
    else:
        current_song_title = "Fila Vazia"
        is_playing = False
        atualizar_status_file()

async def adicionar_musica(search, voice_channel=None):
    # Se um canal foi passado, garante que o bot está lá
    voice = None
    if voice_channel:
        guild = voice_channel.guild
        voice = guild.voice_client
        if not voice:
            voice = await voice_channel.connect()
        elif voice.channel != voice_channel:
            await voice.move_to(voice_channel)
    
    # Se não tem canal (comando vindo da Web), tenta achar o bot em algum lugar
    if not voice:
        for guild in bot.guilds:
            if guild.voice_client:
                voice = guild.voice_client
                break

    if voice:
        music_queue.append({'source': search, 'title': search + " (Fila)"})
        atualizar_status_file()
        if not voice.is_playing():
            # Inicia o download e o play em segundo plano, sem travar a resposta
            bot.loop.create_task(tocar_proxima(voice))
        return True
    return False

# --- SERVIDOR WEB (API) ---

async def handle_get_status(request):
    if not os.path.exists(FILE_STATUS):
        return web.json_response({"tocando": "Bot Offline", "fila": [], "status": "Iniciando..."})
    with open(FILE_STATUS, "r", encoding="utf-8") as f:
        return web.json_response(json.load(f))

async def handle_post_comando(request):
    data = await request.json()
    action = data.get('action')
    val = data.get('data')
    
    print(f"📡 Comando Web: {action}")
    
    if action == 'add':
        await adicionar_musica(val)
    elif action == 'skip':
        for guild in bot.guilds:
            if guild.voice_client and guild.voice_client.is_playing():
                guild.voice_client.stop()
    elif action == 'stop':
        for guild in bot.guilds:
            if guild.voice_client:
                music_queue.clear()
                guild.voice_client.stop()
                await guild.voice_client.disconnect()
    
    return web.json_response({"status": "ok"})

async def start_server():
    app = web.Application()
    
    # Configurar CORS para o Vercel conseguir acessar
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    resource_status = cors.add(app.router.add_resource("/api/status"))
    cors.add(resource_status.add_route("GET", handle_get_status))
    
    resource_cmd = cors.add(app.router.add_resource("/api/comando"))
    cors.add(resource_cmd.add_route("POST", handle_post_comando))

    # Servir arquivos estáticos da raiz
    app.router.add_static('/', path='.', name='static')
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    print("🌐 Servidor API rodando na porta 5000")

# --- EXECUÇÃO ---

@bot.event
async def on_ready():
    print(f'🔥 DJ Bot Online: {bot.user}')
    
    # Sincroniza os comandos de barra instantaneamente em todos os servidores
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print(f"✅ Comandos de barra sincronizados em {len(bot.guilds)} servidores!")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
        
    atualizar_status_file()
    await start_server()

# --- COMANDOS DE TEXTO (Fallback/Plano B) ---
@bot.command(name="play")
async def play_text(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("❌ Você precisa estar em um canal de voz!")
    
    success = await adicionar_musica(search, ctx.author.voice.channel)
    if success:
        await ctx.send(f"✅ Adicionado: **{search}**")

# --- COMANDOS DE BARRA (Slash Commands) ---
@bot.tree.command(name="play", description="Toca uma música no canal de voz")
@discord.app_commands.describe(search="Nome da música ou link do YouTube")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer() # Dá tempo pro bot processar
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Você precisa estar em um canal de voz!")
    
    # Passa o canal do usuário para o bot saber onde entrar
    success = await adicionar_musica(search, interaction.user.voice.channel)
    
    if success:
        await interaction.followup.send(f"✅ **{search}** adicionada à fila!")
    else:
        await interaction.followup.send("❌ Não consegui entrar no seu canal de voz.")

@bot.tree.command(name="skip", description="Pula a música atual")
async def skip(interaction: discord.Interaction):
    for guild in bot.guilds:
        if guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.stop()
            return await interaction.response.send_message("⏭️ Música pulada!")
    await interaction.response.send_message("❌ Nada está tocando no momento.")

@bot.tree.command(name="stop", description="Para tudo e desconecta o bot")
async def stop(interaction: discord.Interaction):
    for guild in bot.guilds:
        if guild.voice_client:
            music_queue.clear()
            guild.voice_client.stop()
            await guild.voice_client.disconnect()
            return await interaction.response.send_message("🛑 Bot desconectado e fila limpa!")
    await interaction.response.send_message("❌ O bot não está em nenhum canal.")

bot.run(TOKEN)
