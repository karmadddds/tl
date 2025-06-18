from telethon import TelegramClient
from telethon.tl.types import PeerChannel, DocumentAttributeVideo
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError
import asyncio
import tempfile
import os
import subprocess

# API credentials
api_id = '26532636'  # Ganti dengan API ID Anda
api_hash = '66941d8d60f7ca710d6c58d0438905a9'  # Ganti dengan API Hash Anda
session_name = 'session_name'

# Source and target channel details
source_channel_id = 2579755803
target_channel_link = "https://t.me/+rJSz3wX9yXsxNjZh"
start_message = 1
end_message = 9155

def convert_video(input_path, output_path):
    """
    Mengonversi video ke format MP4 (H.264 + AAC) agar dapat langsung diputar di Telegram.
    """
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, check=True)

async def download_and_send_video(message, target, client):
    """
    Mengunduh video dari source channel, mengonversi jika perlu, dan mengunggah ke target channel.
    """
    try:
        # Buat file sementara untuk menyimpan video
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            file_path = temp_file.name
            await message.download_media(file=file_path)

        # Buat file sementara untuk video hasil konversi
        converted_file_path = file_path.replace(".mp4", "_converted.mp4")

        # Coba konversi video agar kompatibel dengan Telegram
        convert_video(file_path, converted_file_path)

        # Ambil metadata dari pesan asli
        duration = message.video.duration if message.video else 0
        width = message.video.w if message.video else 0
        height = message.video.h if message.video else 0

        # Upload sebagai video yang bisa langsung diputar di Telegram
        await client.send_file(
            target,
            converted_file_path,
            caption=message.text or "",
            attributes=[
                DocumentAttributeVideo(
                    duration=duration, w=width, h=height, supports_streaming=True
                )
            ],
            force_document=False,  # Kirim sebagai video, bukan dokumen
            parse_mode='html'
        )

        # Hapus file sementara setelah diunggah
        os.remove(file_path)
        os.remove(converted_file_path)
        print(f"✅ Video {message.id} berhasil dikirim.")
    
    except Exception as e:
        print(f"❌ Error mengirim video {message.id}: {e}")

async def main():
    """
    Menghubungkan ke Telegram, mengambil video dari source channel, dan mengirim ke target channel.
    """
    async with TelegramClient(session_name, api_id, api_hash) as client:
        try:
            # Ambil entity dari source channel
            source_channel = await client.get_entity(PeerChannel(source_channel_id))
            print(f"📡 Terhubung ke source channel: {source_channel.title}")

            # Join target channel dan ambil entity-nya
            await client(JoinChannelRequest(target_channel_link))
            target_channel = await client.get_entity(target_channel_link)
            print(f"📡 Terhubung ke target channel: {target_channel.title}")

            # Iterasi pesan dari source channel
            async for message in client.iter_messages(
                source_channel,
                reverse=True,
                offset_id=start_message - 1,
                limit=end_message - start_message + 1
            ):
                print(f"🔄 Memproses pesan {message.id}...")

                if message.video:
                    print(f"🎥 Pesan {message.id} adalah video.")
                    await download_and_send_video(message, target_channel, client)
                elif message.media:
                    print(f"📎 Pesan {message.id} memiliki media tapi bukan video: {message.media}")
                else:
                    print(f"⚠️ Pesan {message.id} dilewati (tidak memiliki media).")
                
                await asyncio.sleep(2)  # Delay agar tidak terkena rate limit

        except FloodWaitError as e:
            print(f"⏳ Rate limit, menunggu {e.seconds} detik...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"❌ Kesalahan kritis: {e}")

if __name__ == "__main__":
    asyncio.run(main())
