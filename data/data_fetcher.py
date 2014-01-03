from raw_data import all_routers,all_switches

class PodNumberError(Exception):
    def __init__(self,error_string):
        self.error_string = error_string
    def __str__(self):
        return repr(self.error_string)

class RouterNumberError(Exception):
    def __init__(self,error_string):
        self.error_string = error_string
    def __str__(self):
        return repr(self.error_string)

class SwitchNumberError(Exception):
    def __init__(self,error_string):
        self.error_string = error_string
    def __str__(self):
        return repr(self.error_string)

def get_pod_term_serv(pod_number_list):
    """ retrieve a list of terminal servers by specifying the pod_number_list

    the get_pod_term_serv fetches a list of terminal servers based on the pod_number_list.
        
    Args:
        pod_number_list : a list containing integers(pod_numbers)

    Returns:
        A list of terminal servers in the structure of [('term_srv','port')]

    Raises:
        PodNumberError : when pod number is given out of range
    """   
    term_srvs = []
    for pod_number in pod_number_list:
        if (pod_number < 0 or pod_number > 20):
            raise PodNumberError("Pod number %s is out of range" % pod_number)
        elif (pod_number == 11):
            raise PodNumberError("Pod number 11 is in construction")
        else:
            if (pod_number < 11):
                term_srvs.append((all_routers[pod_number-1][0][1][0],"23"))
            else:
                term_srvs.append((all_routers[pod_number-2][0][1][0],"23"))
    return term_srvs


def get_pod_routers(pod_number_list,router_number_list):
    """ retrieve a router_list by specifying the pod_number_list and router_number_list

    the get_pod_routers fetches a list of router data which can be used to instantiate 
    the device objects. The pod number ranges from 1~10,12~20, the router number ranges
    from 1~4.
        
    Args:
        pod_number_list    : a list containing integers(pod_numbers)
        router_number_list : a list containing integers(router_numbers)

    Returns:
        A list of routers in the structure of ['router_name',('term_srv','port')]

    Raises:
        PodNumberError    : when pod number is given out of range
        RouterNumberError : when router number is given out of range
    """      

    ###Preprocessing of router_number_list###
    for i in range(len(router_number_list)):
            if (router_number_list[i] < 1) or (router_number_list[i] > 4):
                raise RouterNumberError("Router number %s is out of range" % router_number_list[i])
            else:
                router_number_list[i] = router_number_list[i] - 1

    routers = []
    for pod_number in pod_number_list:
        if (pod_number < 0 or pod_number > 20):
            raise PodNumberError("Pod number %s is out of range" % pod_number)
        elif (pod_number == 11):
            raise PodNumberError("Pod number 11 is in construction")
        else:
            if (pod_number < 11):
                for router_number in router_number_list:
                    routers.append(all_routers[pod_number-1][router_number])
            else:
                for router_number in router_number_list:
                    routers.append(all_routers[pod_number-2][router_number])
    return routers


def get_pod_switches(pod_number_list,switch_number_list):
    """ retrieve a switch_list by specifying the pod_number_list and switch_number_list

    the get_pod_routers fetches a list of switch data which can be used to instantiate 
    the device objects. The pod number ranges from 1~10,12~20, the switch number ranges
    from 1~3.
        
    Args:
        pod_number_list    : a list containing integers(pod_numbers)
        switch_number_list : a list containing integers(switch_numbers)

    Returns:
        A list of switches in the structure of ['switch_name',('term_srv','port')]

    Raises:
        PodNumberError    : when pod number is given out of range
        SwitchNumberError : when switch number is given out of range
    """  
    ###Preprocessing of switch_number_list###
    print switch_number_list
    for i in range(len(switch_number_list)):
            if (switch_number_list[i] < 1) or (switch_number_list[i] > 3):
                raise SwitchNumberError("Switch number %s is out of range" % switch_number_list[i])
            else:
                switch_number_list[i] = switch_number_list[i] - 1

    switches = []
    for pod_number in pod_number_list:
        if (pod_number < 0 or pod_number > 20):
            raise PodNumberError("Pod Number %s is out of range" % pod_number)
        elif (pod_number == 11):
            raise PodNumberError("Pod Number 11 is in construction")
        else:
            if (pod_number < 11):
                for switch_number in switch_number_list:
                    switches.append(all_switches[pod_number-1][switch_number])
            else:
                for switch_number in switch_number_list:
                    switches.append(all_switches[pod_number-2][switch_number])
    return switches
