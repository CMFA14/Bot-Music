import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import os
import json
import time

# --- CONFIGURAÇÃO ---
TOKEN = os.getenv('DISCORD_TOKEN') # Carregado via .env

# Arquivos de comunicação
FILE_STATUS = "status.json"
FILE_COMANDOS = "comandos.json"

# Configurações YT-DLP (O mesmo que funcionou pra você)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'musica_temp.%(ext)s', 
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
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

CAMINHO_FFMPEG = "./ffmpeg.exe"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

music_queue = []
current_song_title = "Nada tocando"
is_playing = False

# --- FUNÇÕES DE INTERFACE ---
def atualizar_status():
    """Escreve o estado atual para o Streamlit ler"""
    dados = {
        "tocando": current_song_title,
        "fila": [m['title'] for m in music_queue],
        "status": "Tocando 🎵" if is_playing else "Parado ⏸️"
    }
    with open(FILE_STATUS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

@tasks.loop(seconds=2)
async def checar_comandos_externos():
    """Lê se o Streamlit mandou fazer algo"""
    if os.path.exists(FILE_COMANDOS):
        try:
            with open(FILE_COMANDOS, "r", encoding="utf-8") as f:
                cmd = json.load(f)
            
            # Executa o comando e deleta o arquivo
            os.remove(FILE_COMANDOS)
            
            print(f"📡 Comando recebido do Site: {cmd['action']}")

            if cmd['action'] == 'add':
                # Simula o comando /play
                # Precisamos achar um canal de voz válido
                for guild in bot.guilds:
                    if guild.voice_client:
                        await adicionar_musica(guild.voice_client, cmd['data'])
                        return
                    # Se não estiver conectado, tenta conectar no canal do dono (simplificado)
                    for channel in guild.voice_channels:
                        if len(channel.members) > 0:
                            await channel.connect()
                            await adicionar_musica(guild.voice_client, cmd['data'])
                            return
            
            elif cmd['action'] == 'skip':
                for guild in bot.guilds:
                    if guild.voice_client and guild.voice_client.is_playing():
                        guild.voice_client.stop()

            elif cmd['action'] == 'stop':
                for guild in bot.guilds:
                    if guild.voice_client:
                        music_queue.clear()
                        guild.voice_client.stop()
                        await guild.voice_client.disconnect()
                        
        except Exception as e:
            print(f"Erro ao ler comando: {e}")

# --- LÓGICA DO BOT ---

@bot.event
async def on_ready():
    print(f'🔥 Bot com Interface Online! {bot.user}')
    checar_comandos_externos.start() # Inicia o loop de ouvir o site
    atualizar_status()

async def adicionar_musica(voice_client, search):
    global current_song_title
    
    # Adiciona na fila lógica
    music_queue.append({'source': search, 'title': search + " (Carregando...)"})
    atualizar_status()

    # Se não estiver tocando, toca agora
    if not voice_client.is_playing():
        await tocar_proxima(voice_client)

async def tocar_proxima(voice_client):
    global current_song_title, is_playing
    
    if len(music_queue) > 0:
        song = music_queue.pop(0)
        search = song['source']
        
        current_song_title = f"Baixando: {search}..."
        atualizar_status()

        # Limpa arquivo anterior
        if os.path.exists("musica_temp.mp3"):
            try: os.remove("musica_temp.mp3")
            except: pass

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                if "http" not in search:
                    info = ydl.extract_info(f"ytsearch:{search}", download=True)['entries'][0]
                else:
                    info = ydl.extract_info(search, download=True)
                
                real_title = info['title']
                current_song_title = real_title
                is_playing = True
                atualizar_status()

            if os.path.exists("musica_temp.mp3"):
                source = discord.FFmpegPCMAudio("musica_temp.mp3", executable=CAMINHO_FFMPEG)
                
                def after_play(error):
                    global is_playing
                    is_playing = False
                    atualizar_status()
                    asyncio.run_coroutine_threadsafe(tocar_proxima(voice_client), bot.loop)

                voice_client.play(source, after=after_play)
            
        except Exception as e:
            print(f"Erro: {e}")
            is_playing = False
            tocar_proxima(voice_client)
    else:
        current_song_title = "Fila Vazia"
        is_playing = False
        atualizar_status()

# Comandos de chat (pra manter compatibilidade)
@bot.command(name='play')
async def play(ctx, *, search: str):
    if not ctx.author.voice: return await ctx.send("Entre na call!")
    if ctx.voice_client is None: await ctx.author.voice.channel.connect()
    await ctx.send(f"✅ Adicionado pelo Discord: {search}")
    await adicionar_musica(ctx.voice_client, search)

bot.run(TOKEN)