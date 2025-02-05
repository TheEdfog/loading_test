import asyncio
import http.client
import time
import json
import threading
from urllib.parse import urlparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

class LoadTester:
    '''
    url - URL to send requests
    requests_per_second - number of requests sent each second
    duration - max duration of the test in seconds
    number_of_workers - number of threads created to send requests in parallel
    '''
    def __init__(self, url, requests_per_second, duration, headers, body, number_of_workers=1):
        self.url = url
        self.requests_per_second = requests_per_second
        self.duration = duration
        self.number_of_workers = number_of_workers
        self.headers = headers
        self.body = body.encode('utf-8')  # Ensure body is bytes
        self.results = []
        self.lock = threading.Lock()  # Lock for thread-safe results collection

    '''
    Function to send POST requests.
    For each request, a new connection is established and closed after finishing.
    '''
    def send_request(self):
        headers = self.headers
        body = self.body

        start_time = time.time()
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path if parsed_url.path else "/"

        try:
            conn = http.client.HTTPConnection(host, port)
            conn.request("POST", path, body=body, headers=headers)
            response = conn.getresponse()
            latency = time.time() - start_time
            request_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            start_time = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            response_data = response.read().decode()
            result = {
                'status': response.status,
                'latency': latency,
                'send_time': start_time,
                'request_time': request_time,
                'response': response_data
            }
            self.results.append(result)
        except Exception as e:
            latency = time.time() - start_time
            request_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            start_time = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            result = {
                'status': 'error',
                'latency': latency,
                'error': str(e),
                'send_time': start_time,
                'request_time': request_time
            }
            self.results.append(result)
        finally:
            conn.close()

    def load_test(self):
        headers = self.headers
        body = self.body
        total_requests = self.requests_per_second * self.duration
        interval = 1.0 / self.requests_per_second

        def worker():
            for _ in range(total_requests):
                start_time = time.time()
                asyncio.run(self.send_request(headers, body))
                asyncio.sleep(interval)

        # with ThreadPoolExecutor(max_workers=self.number_of_workers) as executor:
        #     futures = [executor.submit(worker) for _ in range(1)]
        #     wait(futures)  # Wait for all threads to complete
        # s = sched.scheduler(time.time, asyncio.sleep)
        # for jj in range(total_requests):
        #     s.enter(interval * jj, 1, asyncio.run(self.send_request(headers, body)))
        
        def worker():
            for _ in range(self.number_of_requests // self.duration):
                start_time = time.time()
                thread = threading.Thread(target=self.send_request)
                thread.start()
                time_to_sleep = max(0, interval - (time.time() - start_time))
                time.sleep(time_to_sleep)

        threads = [threading.Thread(target=self.send_request) for _ in range(total_requests)]

        for thread in threads:
            thread.start()
            time.sleep(interval)
        
        for thread in threads:
            thread.join()

    def aggregate_results(self):
        aggregated = defaultdict(lambda: {
            'count': 0, 'latency_sum': 0.0,
            'status_counts': defaultdict(int),
            'latencies': []
        })

        for result in self.results:
            time_key = result['time']
            status = result['status']
            latency = result['latency']

            aggregated[time_key]['count'] += 1
            aggregated[time_key]['latency_sum'] += latency
            aggregated[time_key]['status_counts'][status] += 1
            aggregated[time_key]['latencies'].append(latency)

        final_aggregated = {}
        for time_key, data in aggregated.items():
            final_aggregated[time_key] = {
                'total_requests': data['count'],
                'average_latency': data['latency_sum'] / data['count'],
                'max_latency': max(data['latencies']),
                'status_counts': dict(data['status_counts'])
            }

        return final_aggregated

    def start(self):
        self.load_test()
        # Wait until the duration is over before writing the file
        time.sleep(self.duration)

    def write_aggregated_data(self, output_file):
        data = self.aggregate_results()
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    def write_result_data(self, output_file):
        data = self.results
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)

if __name__ == '__main__':
    name = 'Maria'
    url = r"http://localhost:8000/add_name"
    
    headers = {'Content-type': 'application/json'}
    
    data = {"name": name}
    body = json.dumps(data)

    # Duration in seconds
    duration = 2

    # Requests per second
    requests_per_second = 20

    # Number of worker threads
    number_of_workers = requests_per_second

    # Path to write data
    output_file = 'test_results.json'

    load_tester = LoadTester(
        url, requests_per_second, duration,
        headers, body, number_of_workers
    )
    load_tester.start()
    # time.sleep(duration * 5)
    load_tester.write_result_data(output_file)
