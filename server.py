import os
import re
from flask import Flask, request, jsonify, send_from_directory
from pytubefix import YouTube
from moviepy.editor import VideoFileClip
import logging

app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.DEBUG)

def sanitize_filename(filename):

    return re.sub(r'[<>:"/\\|?*]', '', filename)


@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format = data.get('format')

    if not url or not format:
        return jsonify({'error': 'Missing url or format parameter'}), 400

    try:
        youtube = YouTube(url, use_oauth=False, allow_oauth_cache=True, use_po_token=True)
        filename = sanitize_filename(youtube.title)
        logging.debug(f"Downloading: {filename}")

        if format == "mp4":
            video_stream = youtube.streams.filter(file_extension='mp4').get_highest_resolution()
            if video_stream is None:
                return jsonify({'error': 'No suitable stream found!'}), 404

            filepath = os.path.join(DOWNLOAD_FOLDER, f'{filename}.mp4')
            video_stream.download(output_path=DOWNLOAD_FOLDER, filename=f'{filename}.mp4')

        elif format == "mp3":
            video_stream = youtube.streams.filter(only_audio=True, file_extension='mp4').first()
            if video_stream is None:
                return jsonify({'error': 'No suitable audio stream found!'}), 404

            temp_video_path = os.path.join(DOWNLOAD_FOLDER, f'{filename}.mp4')
            video_stream.download(output_path=DOWNLOAD_FOLDER, filename=f'{filename}.mp4')

            audio_filepath = os.path.join(DOWNLOAD_FOLDER, f'{filename}.mp3')
            video_clip = VideoFileClip(temp_video_path)
            video_clip.audio.write_audiofile(audio_filepath)
            video_clip.close()
            os.remove(temp_video_path)
            filepath = audio_filepath
        else:
            return jsonify({'error': 'Invalid format specified'}), 400

        return jsonify({'fileUrl': f'/files/{os.path.basename(filepath)}', 'filename': filename})

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html', as_attachment=False)

@app.route('/files/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
