import time
import thread
import socket
from OSC import OSCServer, OSCClient, OSCMessage, decodeOSC
from mixerstate import MixerState

class XAirClient:
    """
    Handles the communication with the X-Air mixer via the OSC protocol
    """
    _CONNECT_TIMEOUT = 0.5
    _WAIT_TIME = 0.02
    _REFRESH_TIMEOUT = 5

    XAIR_PORT = 10024

    last_cmd_addr = ''
    last_cmd_time = 0
    info_response = []
    
    def __init__(self, address, state):
        self.state = state
        self.server = OSCServer(("", 0))
        self.server.addMsgHandler("default", self.msg_handler)
        self.client = OSCClient(server = self.server)
        self.client.connect((address, self.XAIR_PORT))
        thread.start_new_thread(self.run_server, ())
    
    def validate_connection(self):
        self.send('/xinfo')
        time.sleep(self._CONNECT_TIMEOUT)
        if len(self.info_response) > 0:
            print 'Successfully connected to %s with firmware %s at %s.' % (self.info_response[2], 
                    self.info_response[3], self.info_response[0])
        else:
            print 'Error: Failed to setup OSC connection to mixer. Please check for correct ip address.'
            exit()
        
    def run_server(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.client.close()
            self.server.close()
            exit()
        
    def msg_handler(self, addr, tags, data, client_address):
        if time.time() - self.last_cmd_time < self._WAIT_TIME and addr == self.last_cmd_addr:
            #print 'Ignoring %s' % addr
            self.last_cmd_addr = ''
        else:
            #print 'OSCReceived("%s", %s, %s)' % (addr, tags, data)
            if addr.endswith('/fader') or addr.endswith('/on') or addr.startswith('/config/mute') or addr.startswith('/fx/'):
                self.state.received_osc(addr, data[0])
            elif addr == '/xinfo':
                self.info_response = data[:]
    
    def refresh_connection(self):
        try:
            while True:
                if self.client != None:
                    self.send("/xremote")
                time.sleep(self._REFRESH_TIMEOUT)
        except KeyboardInterrupt:
            exit()
            
    def send(self, address, param = None):
        if self.client != None:
            msg = OSCMessage(address)
            if param != None:
                # when sending values, ignore ACK response
                self.last_cmd_time = time.time()
                self.last_cmd_addr = address
                if isinstance(param, list):
                    msg.extend(param)
                else:
                    msg.append(param)
            else:
                # sending parameter request, don't ignore response
                self.last_cmd_time = 0
                self.last_cmd_addr = ''
            self.client.send(msg)
            #print 'sending: %s' % (msg)
            
def find_mixer():
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
    client.sendto("/xinfo\0\0", ("<broadcast>", XAirClient.XAIR_PORT))
    try:
        response = decodeOSC(client.recv(512))
    except socket.timeout:
        print "No server found"
        return None
    client.close()

    if response[0] != '/xinfo':
        print "Unknown response"
        return None
    else:
        print "Found " + response[4] + " with firmware " + response[5] + " on IP " + response[2]
        return response[2]
