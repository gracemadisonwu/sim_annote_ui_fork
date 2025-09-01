from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, send_file
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from whisper_transcribe import transcribe_with_whisper
from speaker_identification import FileProcessor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists for saving labels
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Global variables to store current session data
current_video = None
current_segments = []
current_speakers = []
current_file_processor = None
current_whisper_results = None

@app.route('/load_video', methods=['POST'])
def load_video():
    """Handle loading a video from local file path"""
    global current_video
    
    data = request.get_json()
    video_path = data.get('video_path', '').strip()
    # Get the absolute path of the current file
    current_file_path = os.path.abspath(__file__)

    # Get the directory name from the file path
    current_directory = os.path.dirname(current_file_path)
    video_path = os.path.join(current_directory, "uploads", video_path)
    
    if not video_path:
        return jsonify({'error': 'No video path provided'}), 400
    
    # Check if file exists
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 400
    
    # Store video information
    current_video = {
        'filepath': video_path,
        'filename': os.path.basename(video_path),
        'video_url': f'/serve_video/{os.path.basename(video_path)}'
    }
    
    return jsonify({
        'success': True,
        'filename': current_video['filename'],
        'filepath': video_path,
        'video_url': current_video['video_url']
    })

@app.route('/serve_video/<filename>')
def serve_video(filename):
    """Serve video files from the current video path"""
    global current_video
    
    if not current_video or not current_video.get('filepath'):
        return jsonify({'error': 'No video loaded'}), 400
    
    video_path = current_video['filepath']
    
    # Security: ensure the path is within allowed directories
    allowed_dirs = [
        str(Path.cwd()),  # Current working directory
        str(Path.cwd().parent),  # Parent directory
        str(Path.home())  # Home directory
    ]
    
    file_path = Path(video_path).resolve()
    is_allowed = any(str(file_path).startswith(allowed_dir) for allowed_dir in allowed_dirs)
    
    if not is_allowed:
        return jsonify({'error': 'Access denied'}), 403
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    # Determine MIME type based on file extension
    file_ext = file_path.suffix.lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.m4v': 'video/x-m4v'
    }
    
    mimetype = mime_types.get(file_ext, 'video/mp4')
    
    # Serve the video file
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False
    )

@app.route('/whisper_transcribe', methods=['POST'])
def whisper_transcribe():
    """Transcribe the current video using Whisper"""
    global current_video, current_whisper_results
    
    if not current_video:
        return jsonify({'error': 'No video loaded. Please load a video first.'}), 400
    
    video_path = current_video['filepath']

    try:
        # Create segments directory
        segments_dir = f'data/segments-{current_video["filepath"].split("/")[-1].split(".")[0]}'
        os.makedirs(segments_dir, exist_ok=True)
        
        # Transcribe using Whisper
        results, audio_path = transcribe_with_whisper(video_path, segments_dir)
        
        current_whisper_results = results
        current_video.update({'audio_path': audio_path})
        
        return jsonify({'success': True, 'result': results})
        
    except Exception as e:
        print(e)
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500




@app.route('/')
def index():
    """Main page with video transcription and labeling interface"""
    return render_template('index.html')

@app.route('/speaker_identification', methods=['POST'])
def speaker_identification():
    """Identify the speakers in the current video"""
    try:
        data = request.get_json()
        denoise = data.get('denoise', False)
        denoise_prop = data.get('denoise_prop', 0.1)
        verification_threshold = data.get('verification_threshold', 0.2)
    except Exception as e:
        print(e)
        return jsonify({'error': f'Error loading data: {str(e)}'}), 400

    global current_video
    global current_file_processor
    
    if not current_video:
        return jsonify({'error': 'No video loaded'}), 400
        
    whisper_results_file = f'data/segments-{current_video["filepath"].split("/")[-1].split(".")[0]}/whisper_results.json'

    current_file_processor = FileProcessor(current_video['audio_path'], whisper_results_file, denoise, denoise_prop, verification_threshold)

    current_file_processor.process()

    return jsonify({'success': True, 'message': 'Speaker identification completed successfully', 'results': current_file_processor.whisper_results})

@app.route('/get_segments')
def get_segments():
    """Get all current segments"""
    global current_whisper_results
    
    if not current_whisper_results:
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Extract segments from whisper results
    segments = []
    if 'segments' in current_whisper_results:
        for segment in current_whisper_results['segments']:
            if len(segment.get('text', '')):
                segments.append({
                    'id': segment.get('id', 0),
                    'start': segment.get('start', 0.0),
                    'end': segment.get('end', 0.0),
                    'text': segment.get('text', ''),
                    'speaker': segment.get('speaker', '')
                })
    
    return jsonify(segments)

@app.route('/update_segment_speaker', methods=['POST'])
def update_segment_speaker():
    """Update the speaker for a segment"""
    data = request.get_json()
    segment_id = data.get('segment_id')
    speaker = data.get('speaker')

    if segment_id is None or not speaker:
        return jsonify({'error': 'Missing segment_id or speaker'}), 400
    
    global current_whisper_results
    if not current_whisper_results:
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Update the speaker for the segment
    if 'segments' in current_whisper_results:
        for segment in current_whisper_results['segments']:
            if segment.get('id') == segment_id:
                segment['speaker'] = speaker
                break
    whisper_results_file = f'data/segments-{current_video["filepath"].split("/")[-1].split(".")[0]}/whisper_results.json'
    json.dump(current_whisper_results, open(whisper_results_file, "w"))
    
    return jsonify({'success': True, 'message': 'Speaker updated successfully'})

@app.route('/export_labels')
def export_labels():
    """Export labels in the required format for evaluation"""
    global current_whisper_results
    
    if not current_whisper_results or 'segments' not in current_whisper_results:
        return jsonify({'error': 'No segments to export'}), 400
    
    whisper_results_file = f'data/segments-{current_video["filepath"].split("/")[-1].split(".")[0]}/whisper_results.json'
    current_whisper_results = json.load(open(whisper_results_file))
    
    # Sort segments by start time
    sorted_segments = sorted(current_whisper_results['segments'], key=lambda x: x.get('start', 0))
    
    export_data = []
    for segment in sorted_segments:
        if segment.get('speaker'):  # Only export labeled segments
            export_data.append({
                'speaker': segment['speaker'],
                'start': segment['start'],
                'end': segment['end'],
                'text': segment.get('text', '')
            })
    
    return jsonify(export_data)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
