from flask import Flask, render_template, request, send_file
import os
from converter import convert_mermaid_to_nsd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No file selected', 400

    if file:
        mermaid_content = file.read().decode('utf-8')
        svg_output = convert_mermaid_to_nsd(mermaid_content)
        return svg_output

if __name__ == '__main__':
    app.run(debug=True)
