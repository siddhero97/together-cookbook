import os
from flask import Flask, request, render_template, send_from_directory, session, redirect, url_for, jsonify
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management

# Create a directory for audio files if it doesn't exist
AUDIO_DIR = 'audio_files'
os.makedirs(AUDIO_DIR, exist_ok=True)

# Initialize AWS Polly client
polly_client = boto3.client(
    'polly',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

@app.route('/')
def index():
    # Clear the audio file from the session
    audio_file = session.pop('audio_file', None)
    return render_template('index.html', audio_file=audio_file)

@app.route('/convert-pdf', methods=['POST'])
def convert_pdf():
    """Endpoint for converting PDF to speech"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not pdf_file.filename.endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    # Read PDF content
    pdf_text = extract_text_from_pdf(pdf_file)
    
    # Convert to speech
    try:
        audio_filename = convert_text_to_speech(pdf_text)
        session['audio_file'] = os.path.basename(audio_filename)
        return redirect(url_for('index'))
    
    except NoCredentialsError:
        return jsonify({'error': 'AWS credentials not available'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert-text', methods=['POST'])
def convert_text():
    """Endpoint for converting plain text to speech"""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data.get('text')
    if not text.strip():
        return jsonify({'error': 'Text is empty'}), 400

    try:
        audio_filename = convert_text_to_speech(text)
        session['audio_file'] = os.path.basename(audio_filename)
        return jsonify({
            'success': True,
            'audio_file': os.path.basename(audio_filename)
        })
    
    except NoCredentialsError:
        return jsonify({'error': 'AWS credentials not available'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_text_to_speech(text):
    """Helper function to convert text to speech using AWS Polly"""
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna'  # Choose the voice you prefer
    )
    
    # Save the audio stream to a file in the audio directory
    audio_filename = os.path.join(AUDIO_DIR, f"{os.urandom(16).hex()}.mp3")
    with open(audio_filename, 'wb') as audio_file:
        audio_file.write(response['AudioStream'].read())
    
    return audio_filename

def extract_text_from_pdf(pdf_file):
    """Helper function to extract text from PDF"""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve the audio file from the audio directory"""
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)