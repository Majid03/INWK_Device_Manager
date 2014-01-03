import data.data_fetcher
import device
import time
import Queue
import threading

my_data_list = data.data_fetcher.get_pod_routers([1,2,3,4,5,6,7,8,9,10],[1,2,3,4])
my_data_list = my_data_list + data.data_fetcher.get_pod_switches([1,2,3,4,5,6,7,8,9,10],[1])

my_device_list = []

for i in my_data_list:
    my_device_list.append(device.Device(i))

queue = Queue.Queue()

class ThreadDevice(threading.Thread):
    
    def __init__(self,queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            try:
                device = self.queue.get()
                device.pre_process()
                device.login("username","password")
                device.enable()
                device.reset()
                device.disconnect()
                device.post_process()
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                continue
            finally:
                self.queue.task_done()

start = time.time()

for i in range(10):
    t = ThreadDevice(queue)
    t.setDaemon(True)
    t.start()

for device in my_device_list:
    queue.put(device)

queue.join()

print "Elapsed Time : %s" %(time.time() - start)
