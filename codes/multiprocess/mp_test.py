import multiprocessing as mp
import time
import os


# 测试进程间利用队列进行通信
# 设置进程启动函数
def start_process(process_name, target_function, **kwargs):
    interrupt = mp.Event()
    process = mp.Process(name=process_name, target=target_function, kwargs=dict(external_interrupt=interrupt, **kwargs))
    process.start()
    return process, interrupt

# 测试函数1，写入队列
def test1(external_interrupt:mp.Event() = None, que:mp.Queue = None):
    for i in ['a', 'b', 'c', 'd']:
        que.put(i)
        
# 测试函数2，读取队列
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


'''
# 测试进程间的共享变量
def test(flag):
    while True:
        flag.value = 1

if __name__ == '__main__':
    # 定义f为共享的整数型变量，初始化为0
    f = mp.Value('d', 0)
    test1_process = mp.Process(target=test, args=(f, ))
    test1_process.start()
    while True:
        if f.value == 1:
            print(f.value)
            break
    test1_process.terminate()
'''
