import os
from flask import Flask, request, render_template, send_from_directory, session, redirect, url_for
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

@app.route('/convert', methods=['POST'])
def convert():
    # Get PDF file from request
    pdf_file = request.files['file']
    
    # Read PDF content
    pdf_text = extract_text_from_pdf(pdf_file)

    # Convert text to speech using AWS Polly
    try:
        response = polly_client.synthesize_speech(
            Text=pdf_text,
            OutputFormat='mp3',
            VoiceId='Joanna'  # Choose the voice you prefer
        )
        
        # Save the audio stream to a file in the audio directory
        audio_filename = os.path.join(AUDIO_DIR, f"{os.urandom(16).hex()}.mp3")
        with open(audio_filename, 'wb') as audio_file:
            audio_file.write(response['AudioStream'].read())

        # Store the filename in the session
        session['audio_file'] = os.path.basename(audio_filename)
        
        return redirect(url_for('index'))  # Redirect to the index route to render the audio player
    
    except NoCredentialsError:
        return "Credentials not available", 403

def extract_text_from_pdf(pdf_file):
    # Implement text extraction from PDF (using PyPDF2)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    # Serve the audio file from the audio directory
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)