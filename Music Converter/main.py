import os
import subprocess

# FFmpeg ka sahi path yahan likho (Use 'r' before string)
ffmpeg_path = r'C:\ffmpeg\bin\ffmpeg.exe'
music_dir = r'C:\Users\gk\Music\MUSIC 1'

files = [f for f in os.listdir(music_dir) if f.endswith(".m4a")]

for filename in files:
    input_file = os.path.join(music_dir, filename)
    output_file = os.path.join(music_dir, filename.rsplit('.', 1)[0] + ".mp3")
    
    print(f"Converting: {filename}")
    
    # 'ffmpeg' ki jagah ffmpeg_path variable use karo
    subprocess.run([
        ffmpeg_path, 
        '-i', input_file, 
        '-codec:a', 'libmp3lame', 
        '-b:a', '320k', 
        '-y', 
        output_file
    ])