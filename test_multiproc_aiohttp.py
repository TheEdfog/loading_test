import json
import numpy as np
import multiprocessing
import threading
import time
from datetime import datetime
import aiohttp
import asyncio

async def send_request(session, request_data, results, lock):
    headers = request_data['headers']
    body = request_data['body']
    url = request_data['url']

    start_time = time.time()

    try:
        async with session.post(url, headers=headers, data=body) as response:
            response_data = await response.text()
            latency = time.time() - start_time
            response_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            start_time_str = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            result = {
                'status': response.status,
                'latency': latency,
                'request_time': start_time_str,
                'response_time': response_time,
                'response': response_data
            }
    except Exception as e:
        latency = time.time() - start_time
        response_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        start_time_str = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        result = {
            'status': 'error',
            'latency': latency,
            'request_time': start_time_str,
            'response_time': response_time,
            'response': str(e)
        }
    finally:
        with lock:
            results.put(result)

async def worker(queue, results, lock, done_flag, request_data):
    async with aiohttp.ClientSession() as session:
        while True:
            if not queue.empty():
                num_requests = queue.get()

                if num_requests == -1:
                    break

                tasks = []
                for _ in range(num_requests):
                    task = send_request(session, request_data, results, lock)
                    tasks.append(task)

                await asyncio.gather(*tasks)

            await asyncio.sleep(0.1)  # Prevent CPU hogging

        with lock:
            done_flag.value = 1

def start_worker(queue, results, lock, done_flag, request_data):
    asyncio.run(worker(queue, results, lock, done_flag, request_data))

if __name__ == '__main__':
    url = r"http://localhost:8000/add_name"
    
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json'
    }
    
    with open('body_data.json', 'r', encoding='utf-8') as f:
        data = f.read()
        body = json.dumps(
            json.loads(data)
            )

    duration = 60
    start_freq = 50
    end_freq = 500
    num_processes = 6
    output_file = 'test_results.json'

    request_data = {
        'headers': headers,
        'body': body,
        'url': url
    }

    manager = multiprocessing.Manager()
    results = manager.Queue()
    lock = manager.Lock()
    queues = [multiprocessing.Queue() for _ in range(num_processes)]

    processes = []
    processes_done = [multiprocessing.Value('i', 0) for _ in range(num_processes)]
    for i in range(num_processes):
        p = multiprocessing.Process(target=start_worker, args=(
                    queues[i], results, lock, 
                    processes_done[i], request_data
                    ))
        p.start()
        processes.append(p)

    requests_schedule = np.linspace(start_freq, end_freq, duration, dtype=int)
    mid_process_interval = 1.0 / num_processes
    total_send = 0
    time_since_start = 0

    def monitor():
        t = datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S.%f')[:-1]
        if time_since_start == 1:
            print('-' * 25)
        print(f"current time: {t}")
        print(f"time since start: {time_since_start}")
        print(f"total requests sent: {total_send}")
        print(f"total responses: {results.qsize()}")
        print('-' * 25)

    t = datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(t)
    for batch_size in requests_schedule:
        batch_size_per_process = round(1.0 * batch_size / num_processes)

        for i in range(num_processes):
            queues[i].put(batch_size_per_process)
            total_send += batch_size_per_process
            time.sleep(mid_process_interval)
        
        time_since_start += 1
        monitor()
    
    for i in range(num_processes):
        queues[i].put(-1)

    while True:
        total_done = True
        for i in range(num_processes):
            total_done &= processes_done[i].value
        if total_done:
            break
        time.sleep(1)
        time_since_start += 1
        monitor()

    for p in processes:
        p.terminate()
        p.join()

    print(results.qsize())

    statuses = dict()
    l_results = []
    while not results.empty():
        result = results.get_nowait()
        l_results.append(result)
        statuses[result['status']] = statuses.get(result['status'], 0) + 1
    l_results.sort(key=lambda x: x['request_time'])
    print(len(l_results))
    print(statuses)
    print(l_results[0])
    print(l_results[-1])

    print("All processes terminated")
