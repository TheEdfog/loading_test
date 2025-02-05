import asyncio
import http.client
import json
from urllib.parse import urlparse

async def send_post_request():
    url = "http://127.0.0.1:8000/add_name"
    data = {"name": "Alice"}
    
    # Parse the URL
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    
    # Convert data to JSON
    json_data = json.dumps(data)
    
    # Send POST request
    async def post_data():
        conn = http.client.HTTPConnection(host)
        headers = {'Content-type': 'application/json'}
        conn.request("POST", path, body=json_data, headers=headers)
        response = conn.getresponse()
        print(f'Status code: {response.status}')
        response_data = response.read().decode()
        print(f'Response: {response_data}')
        conn.close()

    await post_data()

if __name__ == '__main__':
    asyncio.run(send_post_request())
