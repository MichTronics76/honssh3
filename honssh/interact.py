# Copyright (c) 2016 Thomas Nicholson <tnnich@googlemail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The names of the author(s) may not be used to endorse or promote
#    products derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHORS ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import json
import base64

from twisted.internet import protocol
from honssh import log


class Interact(protocol.Protocol):
    def __init__(self):
        self.interact = None

    def connectionMade(self):
        pass
           
    def dataReceived(self, data):
        # Normalize to str
        if isinstance(data, bytes):
            try:
                data = data.decode(errors='ignore')
            except Exception:
                data = ''
        datagrams = data.split('_')
        total = len(datagrams) // 3
        for i in range(total):
            datagram = datagrams[3 * i:(3 * i) + 3]
            if len(datagram) == 3 and datagram[0] == 'honssh' and datagram[1] == 'c':
                self.parsePacket(datagram[2])
            else:
                log.msg(log.LRED, '[INTERACT]', 'Bad packet received')
                self.transport.loseConnection()

    def sendData(self, the_json):
        # Accept bytes (terminal data), str, dict, list. Convert bytes -> latin1 string for 1:1 byte mapping.
        try:
            if isinstance(the_json, (bytes, bytearray)):
                the_json = the_json.decode('latin1', 'ignore')
            # Ensure only basic JSON types
            # (If someone passes an unsupported type we fallback to an error object below)
            payload = json.dumps(the_json, separators=(',', ':')).encode()
            # Only log preview for structured (dict/list) responses or short strings
            if isinstance(the_json, (dict, list)):
                preview_src = the_json
            elif isinstance(the_json, str) and len(the_json) <= 120:
                preview_src = the_json
            else:
                preview_src = '<omitted large payload>'
            preview = json.dumps(preview_src)[:300]
            log.msg(log.LBLUE, '[INTERACT][DEBUG]', 'Sending response preview: ' + preview)
        except Exception as ex:
            err = {'msg': f'ERROR: Serialization failed: {ex.__class__.__name__}: {ex}'}
            try:
                payload = json.dumps(err).encode()
            except Exception:
                # Last resort minimal JSON
                payload = b'{"msg":"ERROR: Serialization failed"}'
            log.msg(log.LRED, '[INTERACT][ERROR]', 'Failed to serialize response – sending error object')
        the_data = base64.b64encode(payload).decode()
        self.transport.write(f'honssh_s_{the_data}_'.encode())
        
    def sendKeystroke(self, data):
        # Data is raw bytes from terminal output. Convert & send as plain string JSON.
        if isinstance(data, (bytes, bytearray)):
            try:
                data = data.decode('latin1', 'ignore')
            except Exception:
                data = ''
        self.sendData(data)

    def getData(self, theData):
        try:
            raw = base64.b64decode(theData)
            return json.loads(raw.decode(errors='replace'))
        except Exception:
            return {'msg': 'ERROR: Malformed packet'}

    def parsePacket(self, theData):
        the_json = self.getData(theData)
        if not self.interact:
            the_command = the_json.get('command')
            if the_command:
                if the_command == 'list':
                    raw_list = self.factory.connections.return_connections()
                    try:
                        log.msg(log.LBLUE, '[INTERACT][DEBUG]', 'List request: sensors=%s session_counts=%s' % (
                            len(raw_list), [len(s.get('sessions', [])) for s in raw_list]))
                    except Exception:
                        pass
                    safe_list = []
                    for sensor in raw_list:
                        safe_sensor = {
                            'sensor_name': sensor.get('sensor_name'),
                            'honey_ip': sensor.get('honey_ip'),
                            'honey_port': sensor.get('honey_port'),
                            'sessions': []
                        }
                        for session in sensor.get('sessions', []):
                            safe_session = {
                                'session_id': session.get('session_id'),
                                'peer_ip': session.get('peer_ip'),
                                'peer_port': session.get('peer_port'),
                                'start_time': session.get('start_time'),
                                'end_time': session.get('end_time') if 'end_time' in session else None,
                                'channels': []
                            }
                            for channel in session.get('channels', []):
                                safe_channel = {
                                    'uuid': channel.get('uuid'),
                                    'name': channel.get('name'),
                                    'start_time': channel.get('start_time')
                                }
                                if 'end_time' in channel:
                                    # Only include end_time if the channel actually closed; absence signals active
                                    safe_channel['end_time'] = channel.get('end_time')
                                safe_session['channels'].append(safe_channel)
                            safe_sensor['sessions'].append(safe_session)
                        safe_list.append(safe_sensor)
                    if len(safe_list) == 0:
                        log.msg(log.LBLUE, '[INTERACT][DEBUG]', 'Sending empty session list')
                    self.sendData(safe_list)
                elif the_command in ['view', 'interact', 'disconnect']:
                    the_uuid = the_json['uuid']
                    if the_uuid:
                        sensor, session, chan = self.factory.connections.get_channel(the_uuid)
                        if chan is not None:
                            if the_command in ['view', 'interact']:
                                if 'TERM' in chan['name']:
                                    chan['class'].addInteractor(self)
                                    if the_command == 'interact':
                                        self.interact = chan['class']
                                else:
                                    self.sendData({'msg':'ERROR: Cannot connect to a non-TERM session'})
                            elif the_command == 'disconnect':
                                chan['class'].inject_disconnect()
                                self.sendData({'msg':'SUCCESS: Disconnected session: ' + the_uuid})
                        else:
                            self.sendData({'msg':'ERROR: UUID does not exist'})
                    else:
                        self.sendData({'msg':'ERROR: Must specify a UUID'})                       
                else:
                    self.sendData({'msg':'ERROR: Unknown Command'})
            else:
                self.sendData({'msg':'ERROR: Must specify a command'})
        else:
            self.interact.inject(the_json)


def make_interact_factory(honeypot_factory):
    ifactory = protocol.Factory()
    ifactory.protocol = Interact
    ifactory.server = honeypot_factory
    ifactory.connections = honeypot_factory.connections

    return ifactory
