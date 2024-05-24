import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from easyocr import Reader
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
from openai import OpenAI
import os
import time
import json

from dateutil import parser
import pytz

load_dotenv()

client = OpenAI()

app = Flask(__name__)
CORS(app)

reader = Reader(['en'], gpu=False)

UPLOAD_FOLDER = '../captured_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_to_utc(date_str, time_zone_str):
    local = pytz.timezone(time_zone_str)
    dt = parser.parse(date_str)
    # Make sure the datetime object is naive before localizing
    if dt.tzinfo is None:
        local_dt = local.localize(dt, is_dst=None)
    else:
        local_dt = dt.astimezone(local)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt.strftime('%Y%m%dT%H%M%SZ')


@app.route('/process', methods=['POST'])
def process_image():
    data = request.get_json()
    image_data = data['image']
    image = Image.open(BytesIO(base64.b64decode(image_data.split(',')[1])))

    image_np = np.array(image)
    results = reader.readtext(image_np)
    
    extracted_text = ' '.join([res[1] for res in results])
    user_input = f"""
    Extract the following details from the text:
    - Title
    - Start date and time (in the format YYYYMMDDTHHmmssZ)
    - End date and time (in the format YYYYMMDDTHHmmssZ)
    - Description
    - Location

    Text:
    {extracted_text}

    Output in JSON format with keys 'title', 'start', 'end', 'description', and 'location'.
    """

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are a helpful assistant. "},
            {"role": "user", "content": user_input}
        ]
    )

    structured_data = completion.choices[0].message.content
    structured_data_json = json.loads(structured_data)

    # Ensure 'timezone' key exists and has a default value
    structured_data_json.setdefault('timezone', 'UTC')

    # Convert start and end times to UTC
    if structured_data_json.get('start') and structured_data_json['start'] != 'TODO':
        structured_data_json['start'] = convert_to_utc(structured_data_json['start'], structured_data_json['timezone'])
    if structured_data_json.get('end') and structured_data_json['end'] != 'TODO':
        structured_data_json['end'] = convert_to_utc(structured_data_json['end'], structured_data_json['timezone'])

    # Save the image
    timestamp = int(time.time())
    filename = f"{timestamp}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    image.save(filepath)

    return jsonify({
        'text': extracted_text, 
        'structured_data': structured_data_json, 
    })


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/uploads', methods=['GET'])
def list_images():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify(files), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

