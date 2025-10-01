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

from twisted.conch.ssh import transport
from honssh import log


class HonsshServer(transport.SSHServerTransport):
    def connectionMade(self):
        """Invoke the base class connectionMade to correctly initialise ciphers and buffers."""
        # ourVersionString is a str in the config – Twisted expects bytes when writing.
        # Base class will handle sending the version string; ensure it's bytes-friendly.
        if isinstance(self.ourVersionString, str):
            # Twisted's transport.py builds bytes with (self.ourVersionString + b'\r\n') if already bytes.
            # It checks for isinstance(ourVersionString, bytes); so coerce to bytes here.
            self.ourVersionString = self.ourVersionString.encode('utf-8')
        transport.SSHServerTransport.connectionMade(self)

    def sendDisconnect(self, reason, desc):
        """
        http://kbyte.snowpenguin.org/portal/2013/04/30/kippo-protocol-mismatch-workaround/
        Workaround for the "bad packet length" error message.

        @param reason: the reason for the disconnect.  Should be one of the
                       DISCONNECT_* values.
        @type reason: C{int}
        @param desc: a description of the reason for the disconnection.
        @type desc: C{str}
        """
        desc_text = desc.decode(errors='ignore') if isinstance(desc, (bytes, bytearray)) else desc
        if 'bad packet length' not in desc_text:
            transport.SSHServerTransport.sendDisconnect(self, reason, desc)
        else:
            self.transport.write(b'Protocol mismatch.\n')
            log.msg(log.LRED, '[SERVER]', 'Disconnecting with error, code %s\nreason: %s' % (reason, desc_text))
            self.transport.loseConnection()
