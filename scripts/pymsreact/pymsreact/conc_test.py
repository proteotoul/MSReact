import asyncio
import concurrent.futures
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


def blocking_io():
    with open("some_text_file.txt", "rb") as f:
        return f.read(100)
        
async def some_async():
    print(f'I am the some_async function, starting now: {time.time()}')
    for i in range(5):
        await asyncio.sleep(0.1)
        print('I slept a bit')
    print(f'I am the some_async function, finishing now: {time.time()}')
    #return

        
def cpu_bound():
    print('I am the cpu_bound function')
    return sum(i * i for i in range(10 ** 7))
    
def cpu_bound_printing_loop():
    for i in range(10 ** 7):
        if (i % 10 ** 6) == 0:
            print('cpu bound printing loop still running')
            
async def cpu_bound_wrapped():
    cpu_bound_printing_loop()

async def trial_1():
        loop = asyncio.get_running_loop()
        
        result =await loop.run_in_executor(None, blocking_io)
        print("default thread pool", result)
        
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, blocking_io)
            print("custom thread pool", result)
            
        with concurrent.futures.ProcessPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, blocking_io)
        
        with concurrent.futures.ProcessPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, cpu_bound)
            print("custom process pool", result)
            
            

def trial_2():
    loop = asyncio.get_event_loop()
    executor = ProcessPoolExecutor()
    future = loop.run_in_executor(executor, cpu_bound)
    loop.run_until_complete(asyncio.gather(
            some_async(), future))
            
def trial_3():
    loop = asyncio.get_event_loop()
    executor = ProcessPoolExecutor()
    future = loop.run_in_executor(executor, cpu_bound_printing_loop)
    loop.run_until_complete(asyncio.gather(
            some_async(), future))
            
def trial_4():
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    future = loop.run_in_executor(executor, cpu_bound_printing_loop)
    loop.run_until_complete(asyncio.gather(
            some_async(), future))
            
def trial_5():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(some_async(), cpu_bound_wrapped()))
    
if __name__ == '__main__':
    #asyncio.run(trial_1())
    trial_5()