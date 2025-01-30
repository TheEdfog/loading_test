import asyncio
import http.client
import time
import json
import numpy as np
from urllib.parse import urlparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

class LoadTester:
    def __init__(self, url, requests_per_second, duration, output_file, number_of_workers):
        self.url = url
        self.requests_per_second = requests_per_second
        self.duration = duration
        self.output_file = output_file
        self.number_of_workers = number_of_workers
        self.results = []

    async def send_request(self):
        start_time = time.time()
        parsed_url = urlparse(self.url)
        host = parsed_url.netloc
        path = parsed_url.path if parsed_url.path else "/"

        try:
            conn = http.client.HTTPConnection(host)
            conn.request("GET", path)
            response = conn.getresponse()
            latency = time.time() - start_time
            request_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_time))
            self.results.append({'status': response.status, 'latency': latency, 'time': request_time})
        except Exception as e:
            latency = time.time() - start_time
            request_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_time))
            self.results.append({'status': 'error', 'latency': latency, 'error': str(e), 'time': request_time})
        finally:
            conn.close()

    async def wait_until_next_second():
        current_time = time.time()
        next_second = current_time - current_time % 1 + 1
        wait_time = next_second - current_time
        await asyncio.sleep(wait_time)
    
    async def load_test(self):
        start_time = time.time()
        for second in range(self.duration):
            if time.time() > start_time + self.duration:
                break

            tasks = []
            requests_per_worker = int(self.requests_per_second / self.number_of_workers)
            for _ in range(requests_per_worker):
                task = asyncio.create_task(self.send_request())
                tasks.append(task)
            await LoadTester.wait_until_next_second()

        await asyncio.gather(*tasks)

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
            latencies = np.array(data['latencies'])
            final_aggregated[time_key] = {
                'total_requests': data['count'],
                'average_latency': data['latency_sum'] / data['count'],
                '98th_percentile_latency': np.percentile(latencies, 98),
                'max_latency': np.max(latencies),
                'status_counts': dict(data['status_counts'])
            }

        return final_aggregated

    def run_load_test(self):
        asyncio.run(self.load_test())
        return self.results

    def start(self):
        with ProcessPoolExecutor(max_workers=self.number_of_workers) as executor:
            futures = [executor.submit(self.run_load_test) for _ in range(self.number_of_workers)]
            for future in futures:
                self.results.extend(future.result())

    def write_data(self):
        data = self.aggregate_results()
        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=4)

if __name__ == '__main__':
    name = 'Maria'
    url = r"http://127.0.0.1:8000/calculate/" + name
    requests_per_second = 1000
    duration = 3
    output_file = 'test_results.json'
    number_of_workers = 5  # Adjust the number of workers as needed

    load_tester = LoadTester(url, requests_per_second, duration, output_file, number_of_workers)
    load_tester.start()
    load_tester.write_data()
