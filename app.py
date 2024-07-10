import os
import re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import time
import pygame
import threading
import glob

app = Flask(__name__)

# Set up OpenAI client

# If there is a file called openai_key.txt, use that as the API key
if os.path.exists('openai_key.txt'):
    with open('openai_key.txt', 'r') as f:
        api_key = f.read().strip()

# Otherwise, use openai_key_template.txt
else:
    with open('openai_key_template.txt', 'r') as f:
        api_key = f.read().strip()

client = OpenAI(api_key=api_key)

# Global variables to track progress and playback state
total_parts = 0
completed_parts = 0
is_paused = False
pause_event = threading.Event()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        prompt = request.form['prompt']
        duration = int(request.form['duration'])

        # Clean up old audio files
        cleanup_old_files()

        # Generate meditation script
        script = generate_meditation_script(prompt, duration)

        # Start audio generation in a separate thread
        threading.Thread(target=generate_and_play_audio, args=(script,)).start()

        return jsonify({'script': script})

    return render_template('index.html')


@app.route('/progress')
def progress():
    global total_parts, completed_parts
    percentage = (completed_parts / total_parts * 100) if total_parts > 0 else 0
    return jsonify({
        'completed': completed_parts,
        'total': total_parts,
        'percentage': round(percentage, 2)
    })


@app.route('/pause')
def pause_playback():
    global is_paused
    is_paused = True
    pause_event.set()
    return jsonify({'status': 'paused'})


@app.route('/resume')
def resume_playback():
    global is_paused
    is_paused = False
    pause_event.clear()
    return jsonify({'status': 'resumed'})


def cleanup_old_files():
    for file in glob.glob("meditation_part_*.mp3"):
        os.remove(file)


def generate_meditation_script(prompt, duration):
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a meditation guide. Create a guided meditation script."},
            {"role": "user",
             "content": f"""Create a {duration}-minute guided meditation on {prompt}. 
             Include [PAUSE X] indicators for moments of silence, where X is the duration of the pause in minutes.
             There should be plenty of long pauses between guidance. Do not guide too much, use instructions sparingly. Have about 4 instructions for each meditation OR LESS, with only pauses between. ONLY 4 instructions per meditation.
             The style of meditation should be inspired by the teachings of Thich Nhat Hanh and Joseph Goldstein, but do not mention this. Can also take inspiration from Vipassana techniques.
             The aim is not NOT 'relaxation' or 'stress-reduction', but to cultivate mindfulness and awareness - to be present with whatever arises in the moment, in all its detail and subtlety. No visualisations or imaginations.
             The meditation should be aimed at intermediate to advanced practitioners.
             Be precise and concise in your guidance.
             """}
        ]
    )
    return response.choices[0].message.content


def generate_and_play_audio(script):
    global total_parts, completed_parts
    audio_files = generate_audio_files(script)
    play_audio(audio_files, script)


def generate_audio_files(script):
    global total_parts, completed_parts
    script_parts = re.split(r'\[PAUSE \d+(?:\.\d+)?\]', script)
    total_parts = len(script_parts)
    completed_parts = 0
    audio_files = []

    for i, part in enumerate(script_parts):
        if part.strip():  # Only process non-empty parts
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=part.strip()
            )

            audio_file = f"meditation_part_{i}.mp3"
            response.stream_to_file(audio_file)
            audio_files.append(audio_file)

            completed_parts += 1

    return audio_files


def play_audio(audio_files, script):
    global is_paused
    pygame.mixer.init()
    pause_durations = [float(x) for x in re.findall(r'\[PAUSE (\d+(?:\.\d+)?)\]', script)]

    for i, audio_file in enumerate(audio_files):
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()

        # Wait for the audio to finish playing or for pause
        while pygame.mixer.music.get_busy() or is_paused:
            if is_paused:
                pygame.mixer.music.pause()
                pause_event.wait()  # Wait for resume signal
                pygame.mixer.music.unpause()
            time.sleep(0.1)

        # Add the specified pause after each part (except the last one)
        if i < len(pause_durations):
            pause_start = time.time()
            pause_duration = pause_durations[i] * 60  # Convert minutes to seconds
            while time.time() - pause_start < pause_duration:
                if is_paused:
                    pause_event.wait()  # Wait for resume signal
                time.sleep(0.1)

    # Clean up audio files
    for audio_file in audio_files:
        os.remove(audio_file)


if __name__ == '__main__':
    app.run(debug=True)