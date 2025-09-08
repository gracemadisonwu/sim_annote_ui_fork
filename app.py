from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, send_file
import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from whisper_transcribe import transcribe_with_whisper
from speaker_identification import FileProcessor
from flask import session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = '/home/jovyan/shared/Siyanli/inspire-data/uploads/'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure upload directory exists for saving labels
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

file_processor_dict = {}


def load_whisper_results():
    """Load whisper results from file if available"""
    if not session.get("current_whisper_results_file"):
        return None
    
    try:
        with open(session["current_whisper_results_file"], 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load whisper results from {session['current_whisper_results_file']}: {e}")
        return None


@app.route('/load_video', methods=['POST'])
def load_video():
    """Handle loading a video from local file path"""
    logger.info("Received request to load video")
    data = request.get_json()
    video_path = data.get('video_path', '').strip()
    logger.info(f"Video path requested: {video_path}")
    
    # # Get the absolute path of the current file
    # current_file_path = os.path.abspath(__file__)

    # # Get the directory name from the file path
    # current_directory = os.path.dirname(current_file_path)
    # Global variables to store current session data
    session["current_segments"] = []
    session["current_speakers"] = []
    session["current_file_processor"] = None
    session["current_whisper_results_file"] = None
    # video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_path)
    video_path = os.path.join("/home/jovyan/shared/Siyanli/inspire-data/uploads/", video_path)
    
    if not video_path:
        logger.error("No video path provided in request")
        return jsonify({'error': 'No video path provided'}), 400
    
    # Check if file exists
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return jsonify({'error': 'Video file not found'}), 400
    
    # Store video information
    current_video = {
        'filepath': video_path,
        'filename': os.path.basename(video_path),
        'video_url': f'/serve_video/{os.path.basename(video_path)}'
    }
    session["current_video"] = current_video
    logger.info(f"Successfully loaded video: {current_video['filename']}")
    
    return jsonify({
        'success': True,
        'filename': current_video['filename'],
        'filepath': video_path,
        'video_url': current_video['video_url']
    })

@app.route('/serve_video/<filename>')
def serve_video(filename):
    """Serve video files from the current video path"""
    logger.info(f"Request to serve video file: {filename}")
    
    if not session["current_video"] or not session["current_video"].get('filepath'):
        logger.error("No video loaded in session")
        return jsonify({'error': 'No video loaded'}), 400
    
    video_path = session["current_video"]['filepath']
    
    # Security: ensure the path is within allowed directories
    # allowed_dirs = [
    #     str(Path.cwd()),  # Current working directory
    #     str(Path.cwd().parent),  # Parent directory
    #     str(Path.home())  # Home directory
    # ]
    
    file_path = Path(video_path).resolve()
    logger.debug(f"Resolved file path: {file_path}")
    # is_allowed = any(str(file_path).startswith(allowed_dir) for allowed_dir in allowed_dirs)
    
    # if not is_allowed:
    #     return jsonify({'error': 'Access denied'}), 403
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
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
    logger.info(f"Serving video file: {filename} with MIME type: {mimetype}")
    
    # Serve the video file
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False
    )

@app.route('/whisper_transcribe', methods=['POST'])
def whisper_transcribe():
    """Transcribe the current video using Whisper"""
    logger.info("Received request to transcribe video with Whisper")
    
    if not session["current_video"]:
        logger.error("No video loaded for transcription")
        return jsonify({'error': 'No video loaded. Please load a video first.'}), 400
    
    video_path = session["current_video"]['filepath']
    logger.info(f"Starting transcription for video: {video_path}")

    try:
        # Create segments directory
        segments_dir = f'data/segments-{session["current_video"]["filepath"].split("/")[-2]}'
        os.makedirs(segments_dir, exist_ok=True)
        logger.info(f"Created segments directory: {segments_dir}")
        
        # Transcribe using Whisper
        logger.info("Starting Whisper transcription process")
        results, audio_path = transcribe_with_whisper(video_path, segments_dir)
        logger.info("Whisper transcription completed successfully")
        
        # Store the file path instead of the full results
        whisper_results_file = f'{segments_dir}/whisper_results.json'
        session["current_whisper_results_file"] = whisper_results_file
        json.dump(results, open(whisper_results_file, "w"))
        session["current_video"].update({'audio_path': audio_path})
        logger.info(f"Transcription results file path stored: {whisper_results_file}, audio path: {audio_path}")
        
        return jsonify({'success': True, 'result': results})
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}", exc_info=True)
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500




@app.route('/')
def index():
    """Main page with video transcription and labeling interface"""
    logger.info("Serving main page")
    return render_template('index.html')

@app.route('/speaker_identification', methods=['POST'])
def speaker_identification():
    """Identify the speakers in the current video"""
    logger.info("Received request for speaker identification")
    
    try:
        data = request.get_json()
        denoise = data.get('denoise', False)
        denoise_prop = data.get('denoise_prop', 0.1)
        verification_threshold = data.get('verification_threshold', 0.2)
        logger.info(f"Speaker identification parameters - denoise: {denoise}, denoise_prop: {denoise_prop}, verification_threshold: {verification_threshold}")
    except Exception as e:
        logger.error(f"Error loading speaker identification data: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error loading data: {str(e)}'}), 400
    
    if not session["current_video"]:
        logger.error("No video loaded for speaker identification")
        return jsonify({'error': 'No video loaded'}), 400
        
    whisper_results_file = f'data/segments-{session["current_video"]["filepath"].split("/")[-2]}/whisper_results.json'
    logger.info(f"Using whisper results file: {whisper_results_file}")

    new_file_processor = FileProcessor(session["current_video"]['audio_path'], whisper_results_file, denoise, denoise_prop, verification_threshold)
    file_processor_dict.update({
        session["current_video"]["filepath"]: new_file_processor
    })

    logger.info("Starting speaker identification process")
    file_processor_dict[session["current_video"]["filepath"]].process()
    logger.info("Speaker identification process completed")


    return jsonify({'success': True, 'message': 'Speaker identification completed successfully', 'results': file_processor_dict[session["current_video"]["filepath"]].speaker_results})

@app.route('/get_segments')
def get_segments():
    """Get all current segments"""
    logger.info("Request to get segments")
    
    whisper_results = load_whisper_results()
    if not whisper_results:
        logger.error("No transcription results available")
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Extract segments from whisper results
    segments = []
    if 'segments' in whisper_results:
        for segment in whisper_results['segments']:
            if len(segment.get('text', '')):
                segments.append({
                    'id': segment.get('id', 0),
                    'start': segment.get('start', 0.0),
                    'end': segment.get('end', 0.0),
                    'text': segment.get('text', ''),
                    'speaker': segment.get('speaker', '')
                })
    
    logger.info(f"Returning {len(segments)} segments")
    return jsonify(segments)

@app.route('/update_segment_speaker', methods=['POST'])
def update_segment_speaker():
    """Update the speaker for a segment"""
    data = request.get_json()
    segment_id = data.get('segment_id')
    speaker = data.get('speaker')
    
    logger.info(f"Request to update segment {segment_id} speaker to: {speaker}")

    if segment_id is None or not speaker:
        logger.error("Missing segment_id or speaker in request")
        return jsonify({'error': 'Missing segment_id or speaker'}), 400
    
    whisper_results = load_whisper_results()
    if not whisper_results:
        logger.error("No transcription results available for speaker update")
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Update the speaker for the segment
    if 'segments' in whisper_results:
        for segment in whisper_results['segments']:
            if segment.get('id') == segment_id:
                segment['speaker'] = speaker
                logger.info(f"Updated segment {segment_id} speaker to: {speaker}")
                break
    
    # Save the updated results back to file
    whisper_results_file = session["current_whisper_results_file"]
    with open(whisper_results_file, "w") as f:
        json.dump(whisper_results, f)
    logger.info(f"Saved updated results to: {whisper_results_file}")
    
    return jsonify({'success': True, 'message': 'Speaker updated successfully'})

@app.route('/export_labels')
def export_labels():
    """Export labels in the required format for evaluation"""
    logger.info("Request to export labels")
    
    whisper_results = load_whisper_results()
    if not whisper_results or 'segments' not in whisper_results:
        logger.error("No segments available for export")
        return jsonify({'error': 'No segments to export'}), 400
    
    logger.info(f"Loaded whisper results from: {session['current_whisper_results_file']}")
    
    # Sort segments by start time
    sorted_segments = sorted(whisper_results['segments'], key=lambda x: x.get('start', 0))
    
    export_data = []
    for segment in sorted_segments:
        if segment.get('speaker'):  # Only export labeled segments
            export_data.append({
                'speaker': segment['speaker'],
                'start': segment['start'],
                'end': segment['end'],
                'text': segment.get('text', '')
            })
    
    logger.info(f"Exported {len(export_data)} labeled segments")
    return jsonify(export_data)



if __name__ == '__main__':
    logger.info("Starting Flask application")
    logger.info("Application will run on host=0.0.0.0, port=8000")
    app.run(debug=True, host='0.0.0.0', port=8000)
