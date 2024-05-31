import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
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

UPLOAD_FOLDER = '../captured_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_to_utc(date_str, time_zone_str):
    local = pytz.timezone(time_zone_str)
    dt = parser.parse(date_str)
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

    # Convert image to base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    command = """
    Extract the following details from the image:
    - Title
    - Start date and time (in the format YYYYMMDDTHHmmssZ)
    - End date and time (in the format YYYYMMDDTHHmmssZ)
    - Description
    - Location

    Output in JSON format with keys 'title', 'start', 'end', 'description', and 'location'.
    """

    user_input = [
        {
            "type": "text",
            "text": command
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_str}"
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are a helpful assistant. "},
            {"role": "user", "content": user_input}
        ],
        max_tokens=300
    )

    structured_data = response.choices[0].message.content
    structured_data_json = json.loads(structured_data)
    print(structured_data_json)

    structured_data_json.setdefault('timezone', 'UTC')

    if structured_data_json.get('start') and structured_data_json['start'] != 'TODO':
        structured_data_json['start'] = convert_to_utc(structured_data_json['start'], structured_data_json['timezone'])
    if structured_data_json.get('end') and structured_data_json['end'] != 'TODO':
        structured_data_json['end'] = convert_to_utc(structured_data_json['end'], structured_data_json['timezone'])

    # If one of the dates is missing, set start and end dates to be the same
    if structured_data_json.get('start') == 'TODO' and structured_data_json.get('end') != 'TODO':
        structured_data_json['start'] = structured_data_json['end']
    if structured_data_json.get('end') == 'TODO' and structured_data_json.get('start') != 'TODO':
        structured_data_json['end'] = structured_data_json['start']

    # Save the image
    timestamp = int(time.time())
    filename = f"{timestamp}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    image.save(filepath)

    return jsonify({
        'text': structured_data_json.get('description', 'TODO'),
        'structured_data': structured_data_json,
        'filepath': filepath
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
