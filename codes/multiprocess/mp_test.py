import multiprocessing as mp
import time
import os
import random

def start_process(process_name, target_function, **kwargs):
    interrupt = mp.Event()
    process = mp.Process(name=process_name, target=target_function, kwargs=dict(external_interrupt=interrupt, **kwargs))
    process.start()
    return process, interrupt


def test1(external_interrupt:mp.Event() = None, que:mp.Queue = None):
    for i in ['a', 'b', 'c', 'd']:
        que.put(i)
        

def test2(external_interrupt:mp.Event() = None, que:mp.Queue = None):
    while not que.empty():
        item = que.get_nowait()
        if item == 'c':
            
            alrm_flag = True
            print(alrm_flag)
            send_file = True
            send_mqtt = True
    print('Goodbye')

if __name__=="__main__":
    state_que = mp.Queue(maxsize=4)
    test1_process, test1_inter = start_process('test1', test1, que=state_que)
    test2_process, test2_inter = start_process('test2', test2, que=state_que)

