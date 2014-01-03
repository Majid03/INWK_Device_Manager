#!/usr/bin/python 

import pexpect
import re
import os
import sys
import time
import string
import colorprint
import logging
import datetime

# Compiled regular expressions to interact with the device
unprivileged_re   = re.compile("[\w\-_]+>")
privileged_re     = re.compile("[\w\-_]+#")
config_re         = re.compile("\(config[^\)]*\)")
initial_dialog_re = re.compile("initial\s+configuration\s+dialog")
auto_install_re   = re.compile("terminate\sautoinstall")
confirm_re        = re.compile("\[confirm\]")
yes_or_no_re      = re.compile("\[yes/no\]")
enable_passwd_re  = re.compile("assword")
comment_re        = re.compile("^(\s)*!")
blank_re          = re.compile("^(\s)*$")

class UnexpectedStream(Exception):
    def __init__(self,error_string):
        self.error_string = error_string
    def __str__(self):
        return repr(self.error_string)

class LoginException(Exception):
    def __init__(self):
        pass

class EnableException(Exception):
    def __init__(self):
        pass

class ResetException(Exception):
    def __init__(self):
        pass

class ExecuteCMDException(Exception):
    def __init__(self):
        pass

class PushConfigException(Exception):
    def __init__(self):
        pass

class NoConfigFile(Exception):
    def __init__(self):
        pass

class SaveConfigException(Exception):
    def __init__(self):
        pass

class Tee(object):
    """A class to duplicate an output stream to stdout/err.

    This works in a manner very similar to the Unix 'tee' command.

    When the object is closed or deleted, it closes the original file given to
    it for duplication.
    """

    def __init__(self, file_or_name, mode="w", channel='stdout'):
        """Construct a new Tee object.

        Parameters
        ----------
        file_or_name : filename or open filehandle (writable)
        File that will be duplicated

        mode : optional, valid mode for open().
        If a filename was give, open with this mode.

        channel : str, one of ['stdout', 'stderr']
        """
        if channel not in ['stdout', 'stderr']:
            raise ValueError('Invalid channel spec %s' % channel)

        if hasattr(file_or_name, 'write') and hasattr(file_or_name, 'seek'):
            self.file = file_or_name
        else:
            self.file = open(file_or_name, mode)
        self.channel = channel
        self.ostream = getattr(sys, channel)
        setattr(sys, channel, self)
        self.closed = False

    def close(self):
        """Close the file and restore the channel."""
        self.flush()
        setattr(sys, self.channel, self.ostream)
        self.file.close()
        self.closed = True

    def write(self, data):
        """Write data to both channels."""
        self.file.write(data)
        self.ostream.write(data)
        self.ostream.flush()

    def flush(self):
        """Flush both channels."""
        self.file.flush()
        self.ostream.flush()

    def __del__(self):
        if not self.closed:
            self.close()

class Device(object):
    """Device is the base class for handling interaction with routers and switches

    Device can be instantiated for logging in a device via telnet,resetting a device 
    back to its factory default,executing a command while capturing the output, pushing a 
    prepared configuration file to the device and disconnect from the telnet session.

    Attributes:
        _name    : a string to store the name of the device  
        _termsrv : a string to store the terminal server for logging into the device
        _port    : a string to store the tcp port for logging into the device
        _enabled : a boolean indicating whether we are in an enabled state
        _debug   : a boolean indicating whether to generate verbose information to stdout
        _proc    : a pexpect.spawn object to store the session with the device
        _tee     : a Tee object for duplicating the output to both stdout and a file
        _outfd   : a file descripter for the std output file
        _logger  : a logging logger object for the device
        _logfh   : a file descripter for the log file
        _logch   : a file descripter for the log output in stdout 
        _execution_name : a string holding the name of the running execution of the device object
    """

    def __init__(self,device_data,execution_name="",debug=False):
        """Constructor of Device class

        Args:
            device_data    : a tuple (device_name,[termsrv_name,termsrv_port])
            debug          : enable debug messages, by default is True
            execution_name : execution name of this device object,set to be the current 
                             year-month-day-hour
        """
        self._name    = device_data[0]
        self._termsrv = device_data[1][0]
        self._port    = device_data[1][1]
        self._enabled = False
        self._debug   = debug
        self._proc    = None
        self._tee     = None
        self._outfd   = None
        self._logger  = None
        self._logfh   = None
        self._logch   = None
        if execution_name == "":
            self._execution_name = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        else:
            self._execution_name = execution_name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self,name):
        self._name = name

    @property
    def termsrv(self):
        return self._termsrv

    @termsrv.setter
    def termsrv(self,termsrv):
        self._termsrv = termsrv

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self,port):
        self._port = port

    @property
    def proc(self):
        return self._proc

    @proc.setter
    def proc(self,proc):
        self._proc = proc

    @property
    def debug(self):
        return self._debug

    @property
    def enabled(self):
        return self.enabled

    @enabled.setter
    def enabled(self,enabled):
        self._enabled = enabled 

    @property
    def tee(self):
        return self._tee

    @tee.setter
    def tee(self,tee):
        self._tee = tee

    @property
    def outfd(self):
        return self._outfd

    @outfd.setter
    def outfd(self,outfd):
        self._outfd = outfd

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self,logger):
        self._logger = logger

    @property
    def logfh(self):
        return self._logfh

    @logfh.setter
    def logfh(self,logfh):
        self._logfh = logfh

    @property
    def logch(self):
        return self._logch

    @logch.setter
    def logch(self,logch):
        self._logch = logch

    @property
    def execution_name(self):
        return self._execution_name 

    def login(self,username,password,attempt=2,interval=0.5):
        """spawn a telnet session to a given device
    
            The login method spawns a telnet session to the device using the provisioned 
            username and password. By default it makes 2 attempts and a time interval of 
            0.5 second will be  applied in certain time-consuming login situations. After 
            logging in, it doesn't make attempt to enable to a privileged status if it's 
            in an unprivileged status, however it will exit to the privileged mode if 
            it is in configuration mode. 
    
            Args:
                self     : the device object
                username : a string holding the username of telnet session
                password : a string holding the password of telnet session
                attempt  : an integer indicating the number of attempts to be made
                interval : a float holding the time for waiting the correct attempt
    
            Returns:
                Upon succussful login,code 0 will be returned to indicate a clear status.
    
            Raises:
                LoginException    : login to the device failed
                KeyboardInterrupt : ctrl-c is received during the execution  
        """
        try:
            self.logger.info("Attempt to spawn telnet session to %s" % self.name)
            self.proc = pexpect.spawn('telnet %s %s' % (self.termsrv,self.port))

            stdout_log_path = "logs/" + self.execution_name + "/" + self.name + ".stdout"

            if self.debug:
                self.tee = Tee(stdout_log_path, "w") 
                self.proc.logfile_read = self.tee
            else:
                self.outfd = open(stdout_log_path, "w") 
                self.proc.logfile_read = self.outfd
            self.proc.expect("username")
            self.logger.debug("Get username prompt,sending username %s" % username)
            
            self.proc.send(username + "\r")
            self.logger.debug("Get password prompt,sending password ...")
            self.proc.expect("password")
            self.proc.send(password + "\r")
            
            ## Workaround for the banner messages
            self.logger.debug("Sending return character to skip over the banner message")
            time.sleep(0.2)
            self.proc.send("\r")
            
            attempt_counter = 1
            
            while (attempt > 0):
                index = self.proc.expect([unprivileged_re,privileged_re,\
                                    config_re,initial_dialog_re,auto_install_re,\
                                    pexpect.TIMEOUT])
                if index == 0:
                    self.logger.info("We are now in the unprivileged mode")
                    self.enabled = False
                    return 0;
                elif index == 1:
                    self.logger.info("We are now in the privileged mode")
                    self.enabled = True
                    return 0;
                elif index == 2:
                    self.logger.info("We are now in the configuration mode")
                    self.logger.debug("Sending end messages to exit to the privileged mode..")
                    self.proc.send("end\r")
                    self.proc.expect(privileged_re)
                    self.logger.info("We are now in the configuration mode")
                    self.enabled = True
                    return 0;
                elif index == 3:
                    self.logger.info("We are now in the initial configuration dialogue")
                    self.logger.debug("Sending no to exit out of the setup wizard..")
                    self.proc.send("no\r")
                    time.sleep(interval)
                    index2 = self.proc.expect([unprivileged_re,auto_install_re,pexpect.TIMEOUT])
                    if index2 == 0:
                        self.logger.info("We are now in the unprivileged mode")
                        self.enabled = False
                        return 0
                    elif index2 == 1:
                        self.logger.info("We are asked to confirm terminating the auto-install,sending yes..")
                        self.proc.send("yes\r")
                        time.sleep(interval)
                        continue
                    else:
                        time.sleep(interval)
                        self.proc.send("\r")
                        attempt = attempt - 1
                        self.logger.warning("#%s login attempt failed..now starting #%s attempt" \
                                             % (str(attempt_counter),str(attempt_counter+1)))
                        attempt_counter = attempt_counter + 1
                        continue
                elif index == 4:
                    self.logger.info("We are asked to confirm terminating the auto-install,sending yes..")
                    self.proc.send("yes\r")
                    time.sleep(interval)
                    continue
                else:
                    time.sleep(interval)
                    self.proc.send("\r")
                    self.logger.warning("#%s login attempt failed..now starting #%s attempt" \
                                             % (str(attempt_counter),str(attempt_counter+1)))
                    attempt_counter = attempt_counter + 1
                    attempt = attempt - 1
        
            raise UnexpectedStream("Expected Stream was encountered when attempting to login")

        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to login to device %s, refer %s.stdout for details" \
                                % (self.name, self.name))
            raise LoginException

    def enable(self,enable_passwd=["inwk","inwk01"],disable_paging=True,attempt=2):
        """enable an unprivileged session to priviledged and optionally disable terminal paging
    
            Enable method assumes the self._proc is in a status after the device.login() method.
            By default no enable_passwd should be present and we disable the terminal paging 
            after succussfully enabling to a priviledged status. 
    
            Args:
                self           : the device object
                enable_passwd  : a string holding the enable password
                disable_paging : a boolean indicating whether paging will be disabled 
                attempt        : an integer indicating the number of attempts to be made
    
            Returns:
                Upon succussful enabling, code 0 will be returned to indicate a clear status.
    
            Raises:
                EnableException   : when enabling to the priviledged mode on this device failed
                KeyboardInterrupt : ctrl-c is received during execution 
        """
        try :
            self.logger.debug("sending return character to get a new prompt")
            self.proc.send("\r")
    
            attempt_counter = 0
    
            while (attempt>0):
                index = self.proc.expect([unprivileged_re,enable_passwd_re,privileged_re,\
                                       config_re,pexpect.TIMEOUT])
                if index == 0:
                    self.logger.debug("We are in unprivileged mode, sending enable command...")
                    self.proc.send("enable" + "\r")
                    time.sleep(0.1)
                    continue;
                elif index == 1:
                    if attempt_counter > 1:
                        passwd_counter = 1
                    else:
                        passwd_counter = attempt_counter
                    self.logger.debug("We are prompted to enter enable password,"\
                                       "sending commonly used password %s"\
                                      % enable_passwd[passwd_counter] )
                    self.proc.send(enable_passwd[passwd_counter] + "\r")
                    attempt_counter = attempt_counter + 1
                    if attempt_counter > passwd_counter + 1:
                        attempt = 0
                    continue;
                elif index == 2:
                    self.logger.info("We successfully enter into privileged mode")
                    self.enabled = True
                    if disable_paging:
                        self.logger.debug("Sending terminal length 0 command to disable paging...")
                        self.proc.send("terminal length 0\r")
                        self.proc.expect(privileged_re)
                    return 0
                elif index == 3:
                    self.logger.debug("We are in configuration mode,sending end to exit to \
                                       privileged mode")
                    self.proc.send("end\r")
                    continue;
                else:
                    self.logger.warning("#%s enable attempt failed..now starting #%s attempt" \
                                             % (str(attempt_counter),str(attempt_counter+1)))
                    time.sleep(0.2)
                    self.proc.send("\r")
                    attempt = attempt - 1
    
            raise UnexpectedStream("Expected Stream was encountered when attempting to login")

        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to get privileged on device %s, refer %s.stdout for details" \
                                % (self.name, self.name))
            raise EnableException

    def reset(self,erase_vlan=False):
        """reset a device to its factory default
    
           Reset a router or switch to its factory default by clearing up the startup-config
           (optionally the vlan.dat file) and reloading the device. It assumes the telnet 
           session is in a priviledged status.
   
           Args:
               self       : the device object
               erase_vlan : a boolean indicating whether or not to remove the vlan.dat

           Returns:
               Upon succussful reset, code 0 will be returned to indicate a clear status.

           Raises:
               ResetException    : factory default reset on this device failed
               KeyboardInterrupt : ctrl-c received
        """ 
        try :
            self.logger.debug("Sending return character to get a new prompt..")       
            self.proc.send("\r")
            self.proc.expect(privileged_re)
            self.logger.debug("We are now in privileged mode")
    
            if erase_vlan:
                self.logger.info("Boolean erase_vlan set to be True,going to delete vlan database file")  
                self.proc.send("delete flash:vlan.dat\r")
                self.proc.expect("\[vlan.dat\]")
                self.logger.debug("Asked to check the file to delete,sending return..")  
                self.proc.send("\r")
                self.proc.expect(confirm_re)
                self.logger.debug("Asked to confirm deleting the vlan file,sending return..") 
                self.proc.send("\r")
                self.proc.expect(privileged_re)
                self.logger.info("Succssfully deleting vlan file, we are now back to privileged mode") 
    
            self.logger.info("Sending command erase startup-config...")
            self.proc.send("erase startup-config\r")
            self.proc.expect(confirm_re)
            self.logger.debug("Asked to confirm deleting the startup-config,sending return..")
            self.proc.send("\r")
            self.proc.expect(privileged_re)
            self.logger.info("Succssfully deleting startup-config, we are now back to privileged mode") 
            self.logger.info("Sending reload command to reboot the device") 
            self.proc.send("reload\r")
    
            index = self.proc.expect([yes_or_no_re,confirm_re])
            if index == 0:
                self.logger.debug("Asked whether or not to save the config, sending no..")
                self.proc.send("no\r")
                self.proc.expect(confirm_re)
                self.logger.debug("Asked to confirm to reload,sending return..")
                self.proc.send("\r")
            else:
                self.logger.debug("Asked to confirm to reload,sending return..")
                self.proc.send("\r")
    
            self.proc.expect("Reload\srequested")
            self.logger.info("Reload request has been submitted to the device")
            return 0

        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to reset the device %s, refer %s.stdout for details" \
                                % (self.name, self.name))
            raise ResetException
        

    def send_cmd(self,command,max_performance=False,interval=5):
        """execute a command on a device and capture its output
    
           send_cmd assumes the telnet session is an enabled status. when max_performance is 
           True, it captures the start of command out to the first word which matches the 
           privileged_re. This sometimes may not be the entire command output (buggy output
           with "show version" on a ISR router). By diabling max_performance, it captures all 
           the command output within the given amount of interval time.
   
           Args:
               self       : the device object
               command    : a string holding the command to be executed

           Returns:
               the command output is returned.

           Raises:
               ExecuteCMDException : failure to execute the given cmd on this device
               KeyboardInterrupt   : ctrl-c received
        """  
        try:
            cmd_output = ""
            self.logger.debug("Sending return character to get a new prompt..")  
            self.proc.send("\r")
            self.proc.expect(privileged_re)   
            self.logger.debug("We are now in privileged mode")
            
            self.proc.send(command + "\r")
            self.logger.info("Sending command %s..." % command)     
    
            if max_performance:
                self.logger.debug("Max_performace is turned on, command output" \
                                  "capture may not be accurate")  
                self.proc.expect(privileged_re)
                cmd_output = self.proc.before
            else:
                while (self.proc.expect([privileged_re,pexpect.TIMEOUT],timeout=interval) != 1) :
                    cmd_output = cmd_output + self.proc.before
    
            self.logger.info("Finished command execution and get privileged mode prompt again..")
            return cmd_output

        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to execute command %s on device %s," \
                              "refer %s.stdout for details" \
                                % (command,self.name, self.name))
            raise ExecuteCMDException

    def push_config(self,configfile=""):
        """push a prepared a configuration file to a device
    
           push_config pushes a prepared config file to a device. It assumes a priviledged 
           telnet session is present. By default,It will search for a config file with 
           filename of $devicename.cfg under the config directory if no configfile is 
           specified.
   
           Args:
               self       : the device object
               configfile : a string holding the full path of configuration file

           Returns:
               Upon successfully pushing the config, code 0 will be returned.

           Raises:
               PushConfigException : fails to push the config on the device
               KeyboardInterrupt   : ctrl-c received
        """
        try:  
            self.proc.send("\r")
            self.logger.debug("Sending return character to get a new prompt..") 
            self.proc.expect(privileged_re)
            self.logger.debug("We are now in privileged mode")

            if configfile == "":
                configfile = "config/" + self.name + ".cfg"

            if os.path.isfile(configfile) == False:
                raise NoConfigFile

            lines_to_send = []
            with open(configfile) as f:
                lines_to_send = [line.rstrip() + '\r' for line in f \
                                 if (comment_re.findall(line) == [] \
                                 and blank_re.findall(line) == []) ]
            
            self.proc.send("configure terminal\r")
            self.logger.debug("Sending configure terminal to get into config mode..") 
            self.proc.expect(config_re)
            self.logger.info("We are now in global configuration mode")
        
            for line in lines_to_send:
                self.proc.send(line)
                self.logger.debug("Sending configuration lines of %s" % line)
                index = self.proc.expect([config_re,privileged_re])
                if index == 0:
                    self.logger.debug("Getting config mode prompt")
                    continue
                else:
                    self.logger.debug("Getting privileged mode prompt")
                    return 0
        
            self.logger.debug("All config lines have been pushed..")
            self.logger.debug("Sending end to exit out of config mode..") 
            self.proc.send("end\r")
            self.proc.expect(privileged_re)
            self.logger.debug("We are now in privileged mode")
            return 0

        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to push configfile %s on device %s," \
                              "refer %s.stdout for details" \
                                % (configfile,self.name, self.name))
            raise PushConfigException

    def save_config(self):
        """save configs
        To be documented.
    
        """
        try:
            if os.path.isdir("config_archive/" + self.execution_name) == False:
                os.makedirs("config_archive/" + self.execution_name)
    
            self.proc.send("\r")
            self.logger.debug("Sending return character to get a new prompt..") 
            self.proc.expect(privileged_re)
    
            running_config = self.send_cmd("show run")
    
            config_archive_path = "config_archive/" + self.execution_name + "/" + self.name + ".cfg"
            fd = open(config_archive_path,"w")
            fd.write(running_config)
            fd.close()
        except KeyboardInterrupt:
            colorprint.error_print("Keyboard Interrup has been received..Exiting..")
            raise KeyboardInterrupt    
        except: 
            colorprint.error_print()
            self.logger.error("Unable to save configfile for device %s," \
                              "refer %s.stdout for details" \
                                % (self.name, self.name))
            raise SaveConfigException        

    def disconnect(self,force=False):
        """terminate an exsiting telnet session.
     
           disconnect method terminate the telnet process with SIGHUP and SIGINT,
           or with SIGKILL when the force is set to be True.
   
           Args:
               force : boolean to indicate whether force to terminate the process

           Returns:
               True when telnet process is successfully terminated, otherwise false.
        """  
        return self.proc.terminate(force)

    def pre_process(self,s="",log_filename=""):

        ## printing to stdout indicate starting execution sequence of the device
        if s == "":
            start_string = "STARTING EXECUTION SEQUENCE FOR %s" % self.name
        else:
            start_string = s
        colorprint.start_print(start_string)

        # Create the logging directory
        if os.path.isdir("logs/" + self.execution_name) == False:
            os.makedirs("logs/" + self.execution_name)

        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-6s - %(message)s',\
                     datefmt='%m/%d/%Y %I:%M:%S %p')

        self.logfh = logging.FileHandler("logs/" + self.execution_name + "/" + self.name + ".log")
        self.logfh.setLevel(logging.DEBUG)
        self.logfh.setFormatter(formatter)
        self.logger.addHandler(self.logfh)

        if self.debug == False:
            self.logch = logging.StreamHandler()
            self.logch.setLevel(logging.DEBUG)
            self.logch.setFormatter(formatter)
            self.logger.addHandler(self.logch)

    def post_process(self,s=""):

        if self.debug == True:
            self.tee.close()
        else:
            self.outfd.close()

        ## printing to stdout indicate ending execution sequence of the device
        if self.debug == True:
            if s == "":
                end_string = "ENDING EXECUTION SEQUENCE FOR %s" % self.name
            else:
                end_string = s
            colorprint.end_print(end_string)
            time.sleep(0.2)
            os.system("clear")
 
    # TODO : clear line function to be implemented when we have the credentials for
    # accessing the terminal server
    def clear_line(self):
        pass

    def __del__(self):
        pass

