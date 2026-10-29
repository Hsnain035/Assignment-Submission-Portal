from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/report', methods=['POST'])
def receive_report():
    data = request.json
    # Save the received JSON payload to a local file
    with open('test-report.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print("\n[+] Success! Test report received and saved to test-report.json")
    return jsonify({"message": "Report saved successfully"}), 200

if __name__ == '__main__':
    # Running on port 5001 to avoid conflicting with your main app on 5000
    app.run(port=5001, debug=True)