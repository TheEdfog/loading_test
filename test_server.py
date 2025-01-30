import asyncio
import http.client
import time
import json
from urllib.parse import urlparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

async def send_request(url, results):
    start_time = time.time()
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else "/"
    
    try:
        conn = http.client.HTTPConnection(host)
        conn.request("GET", path)
        response = conn.getresponse()
        latency = time.time() - start_time
        request_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_time))
        results.append({'status': response.status, 'latency': latency, 'time': request_time})
    except Exception as e:
        latency = time.time() - start_time
        request_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_time))
        results.append({'status': 'error', 'latency': latency, 'error': str(e), 'time': request_time})
    finally:
        conn.close()

async def load_test(url, requests_per_second, duration, results):
    for second in range(duration):
        tasks = []
        for _ in range(requests_per_second):
            task = asyncio.create_task(send_request(url, results))
            tasks.append(task)
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)

def aggregate_results(results):
    aggregated = defaultdict(lambda: {'count': 0, 'latency_sum': 0.0, 'status_counts': defaultdict(int)})
    
    for result in results:
        time_key = result['time']
        status = result['status']
        latency = result['latency']
        
        aggregated[time_key]['count'] += 1
        aggregated[time_key]['latency_sum'] += latency
        aggregated[time_key]['status_counts'][status] += 1
    
    final_aggregated = {}
    for time_key, data in aggregated.items():
        final_aggregated[time_key] = {
            'total_requests': data['count'],
            'average_latency': data['latency_sum'] / data['count'],
            'status_counts': dict(data['status_counts'])
        }
    
    return final_aggregated

def run_load_test(url, requests_per_second, duration):
    results = []
    asyncio.run(load_test(url, requests_per_second, duration, results))
    return results

def main():
    name = 'Maria'
    url = r"http://127.0.0.1:8000/calculate/" + name
    requests_per_second = 500
    duration = 3
    output_file = 'test_results.json'
    number_of_workers = 10  # Adjust the number of workers as needed
    requests_per_worker = int(requests_per_second / number_of_workers)

    with ProcessPoolExecutor(max_workers=number_of_workers) as executor:
        futures = [executor.submit(run_load_test, url, requests_per_worker, duration) for _ in range(number_of_workers)]
        all_results = []
        for future in futures:
            all_results.extend(future.result())

    aggregated_results = aggregate_results(all_results)
    
    with open(output_file, 'w') as f:
        json.dump(aggregated_results, f, indent=4)

if __name__ == '__main__':
    main()

class LoadTester:
    def __init__(self, duration, requests_per_second, n_users=1, n_workers=1):
        self.duration = duration
        self.requests_per_second = requests_per_second
        self.n_users = n_users
        self.n_workers = n_workers
    
    def 