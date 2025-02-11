import http.client
import json
from urllib.parse import urlparse
import numpy as np
import multiprocessing
import threading
import time
from datetime import datetime
import urllib.parse

def send_request(request_data, results, lock):
    headers = request_data['headers']
    body = request_data['body']
    # body = urllib.parse.urlencode(request_data['body'])
    url = request_data['url']

    start_time = time.time()
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    port = parsed_url.port
    path = parsed_url.path if parsed_url.path else "/"

    try:
        conn = http.client.HTTPConnection(host, port)
        conn.request("POST", path, body=body, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode()
        latency = time.time() - start_time
        conn.close()
        response_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        start_time = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        result = {
            'status': response.status,
            'latency': latency,
            'request_time': start_time,
            'response_time': response_time,
            'response': response_data
        }
    except Exception as e:
        latency = time.time() - start_time
        response_time = datetime.utcfromtimestamp(start_time + latency).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        start_time = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        result = {
            'status': 'error',
            'latency': latency,
            'request_time': start_time,
            'response_time': response_time,
            'response': str(e)
        }
    finally:
        with lock:
            results.put(result)

# # Define the function that has the waiting logic
# def foo():
#     print("foo() called")
#     time.sleep(3)  # Simulate some waiting logic
#     print('foo() done')

# Worker function for each process
def worker(queue, results, lock, done_flag, request_data):
    threads = []
    while True:
        if not queue.empty():
            # Get the number of times to call foo
            num_requests = queue.get()

            if num_requests == -1:
                break

            for i in range(num_requests):
                thread = threading.Thread(target=send_request, args=(request_data, results, lock))
                thread.start()
                threads.append(thread)
        
        # Prevent CPU hogging by sleeping for a short duration
        time.sleep(0.1)

    # Finish all threads before killing process
    for thread in threads:
        thread.join()

    # Mark as done process
    with lock:
        done_flag.value = 1

if __name__ == '__main__':
    url = r"http://localhost:8000/add_name"
    
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json'
    }
    
    with open('body_data.json', 'r', encoding='utf-8') as f:
        data = f.read()
        body = json.loads(data)
        body = json.dumps(data)

    # body = { 'name': 'Maria' }
    # Duration in seconds
    duration = 3

    start_freq = 50
    end_freq = 500

    # Number of worker threads
    num_processes = 3

    # Path to write data
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

    # Initialize and start the processes
    processes = []
    processes_done = [multiprocessing.Value('i', 0) for _ in range(num_processes)]
    for i in range(num_processes):
        p = multiprocessing.Process(target=worker, args=(
                    queues[i], results, lock, 
                    processes_done[i], request_data
                    ))
        p.start()
        processes.append(p)

    # Example: adding items to the queue
    # for i in range(num_processes):
    #     queues[i].put(2)  # Each process will call foo() 5 times
        # queues[i].put(10) # Each process will call foo() 10 times

    # Let the processes run for a while
    # time.sleep(5)

    requests_schedule = np.linspace(start_freq, end_freq, duration, dtype=int)

    # Time to wait till loading a process with new tasks
    mid_process_interval = 1.0 / num_processes

    total_send = 0
    time_since_start = 0

    def monitor():
        t = datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S.%f')[:-1]
        if time_since_start == 1:
            print('-' * 25)
        print(f"current time: {t}")
        print(f"time since start: {time_since_start}")
        print(f"total requests send: {total_send}")
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
    
    # end processes
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

    # Terminate the processes
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
