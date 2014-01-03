import data.data_fetcher
import device

my_data_list = data.data_fetcher.get_pod_routers([1,2],[1,2,3,4])
my_data_list = my_data_list + data.data_fetcher.get_pod_switches([1,2,3,4,5,6],[1])
print my_data_list

my_device_list = []

for i in my_data_list:
    my_device_list.append(device.Device(i))

"""
for i in my_device_list:
    i.pre_process()
    i.login("username","password")
    i.enable()
    i.save_config()
    i.disconnect()
    i.post_process()

""" 
for i in my_device_list:
    try:
        i.pre_process()
        i.login("username","password")
        i.enable()
        i.reset()
        i.disconnect()
        i.post_process()
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        continue
