import asyncio
import http.client
import time
import json
import threading
from urllib.parse import urlparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from multiprocessing import Process, Lock, Manager
import _winapi
import multiprocessing.spawn

multiprocessing.spawn.set_executable(_winapi.GetModuleFileName(0))

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
        self.manager = Manager()
        self.results = self.manager.list()

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
                'send_time': start_time,
                'request_time': request_time,
                'response': str(e)
            }
            self.results.append(result)
        finally:
            conn.close()

    def worker(self):
        interval = 1.0 / self.requests_per_second
        total_requests = self.requests_per_second * self.duration

        threads = [threading.Thread(target=self.send_request) for _ in range(total_requests)]

        for thread in threads:
            thread.start()
            time.sleep(interval)
        
        for thread in threads:
            thread.join()

    def load_test(self):
        self.worker()

        processes = []

        delay = 1.0 / self.number_of_workers

        for i in range(self.number_of_workers):
            lock = self.manager.Lock()
            process = Process(target=self.worker)
            processes.append(process)
            process.start()
            time.sleep(delay)

        for process in processes:
            process.join()
        
        pass

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
        # time.sleep(self.duration)

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
    
    with open('body_data.json', 'r', encoding='utf-8') as f:
        data = f.read()
        body = json.dumps(data)

    # Duration in seconds
    duration = 1

    # Requests per second
    requests_per_second = 200

    # Number of worker threads
    number_of_workers = 3

    # Path to write data
    output_file = 'test_results.json'

    load_tester = LoadTester(
        url, requests_per_second, duration,
        headers, body, number_of_workers
    )
    load_tester.start()
    # time.sleep(duration * 5)
    load_tester.write_result_data(output_file)
