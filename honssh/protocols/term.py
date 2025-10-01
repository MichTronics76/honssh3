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

from honssh import log
from honssh.protocols import baseProtocol 
import datetime


class Term(baseProtocol.BaseProtocol):
    def __init__(self, out, uuid, chan_name, ssh, client_id):
        super(Term, self).__init__(uuid, chan_name, ssh)

        self.command = ''
        self.pointer = 0
        self.tabPress = False
        self.upArrow = False

        self.out = out
        self.clientID = client_id
        self.ttylog_file = self.out.logLocation + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") \
                           + '_' + self.name[1:-1] + '.tty'
        self.out.open_tty(self.uuid, self.ttylog_file)
        self.interactors = []
        self.out.register_self(self)

    def channel_closed(self):
        self.out.close_tty(self.ttylog_file)
        for i in self.interactors:
            i.transport.loseConnection()
    
    def parse_packet(self, parent, payload):
        # Ensure payload stored as bytes for logging; keep a working string view for command parsing
        raw = payload if isinstance(payload, (bytes, bytearray)) else payload.encode('utf-8', 'ignore')
        self.data = raw
        # Working text (single-byte control assumptions) decoded latin1 to preserve byte values 0x00-0xff
        work = raw.decode('latin1', 'ignore')
         
        if parent == '[SERVER]':
            # Log raw bytes to TTY file as INPUT
            self.out.input_tty(self.ttylog_file, self.data)

            while len(work) > 0:
                # If Tab Pressed
                if work[:1] == '\x09':
                    self.tabPress = True 
                    work = work[1:]
                # If Backspace Pressed
                elif work[:1] == '\x7f' or work[:1] == '\x08':
                    if self.pointer > 0:
                        self.command = self.command[:self.pointer-1] + self.command[self.pointer:]
                        self.pointer -= 1
                    work = work[1:]
                # If enter or ctrl+c or newline
                elif work[:1] == '\x0d' or work[:1] == '\x03' or work[:1] == '\x0a':
                    if work[:1] == '\x03':
                        self.command += "^C"
                    work = work[1:]
                    if self.command != '':
                        log.msg(log.LPURPLE, '[TERM]', 'Entered command: %s' % self.command)
                        self.out.command_entered(self.uuid, self.command)
                    
                    self.command = ''
                    self.pointer = 0
                # If Home Pressed
                elif work[:3] == '\x1b\x4f\x48':
                    self.pointer = 0
                    work = work[3:]
                # If End Pressed
                elif work[:3] == '\x1b\x4f\x46':
                    self.pointer = len(self.command)
                    work = work[3:]
                # If Right Pressed
                elif work[:3] == '\x1b\x5b\x43':
                    if self.pointer != len(self.command):
                        self.pointer += 1
                    work = work[3:]
                # If Left Pressed
                elif work[:3] == '\x1b\x5b\x44':
                    if self.pointer != 0:
                        self.pointer -= 1
                    work = work[3:]
                # If up or down arrow
                elif work[:3] == '\x1b\x5b\x41' or work[:3] == '\x1b\x5b\x42':
                    self.upArrow = True
                    work = work[3:]
                else:                   
                    self.command = self.command[:self.pointer] + work[:1] + self.command[self.pointer:]
                    self.pointer += 1
                    work = work[1:]
        
        elif parent == '[CLIENT]':
            # Log raw bytes to TTY file as OUTPUT
            self.out.output_tty(self.ttylog_file, self.data)
            for i in self.interactors:
                i.sendKeystroke(self.data)
            
            if self.tabPress:
                if not work.startswith('\x0d'):
                    if work != '\x07':
                        self.command = self.command + work
                self.tabPress = False

            if self.upArrow:
                while len(work) != 0:
                    # Backspace
                    if work[:1] == '\x08':
                        self.command = self.command[:-1]
                        self.pointer -= 1
                        work = work[1:]
                    # ESC[K - Clear Line
                    elif work[:3] == '\x1b\x5b\x4b':
                        self.command = self.command[:self.pointer]
                        work = work[3:]
                    elif work[:1] == '\x0d':
                        self.pointer = 0
                        work = work[1:]
                    # Right Arrow
                    elif work[:3] == '\x1b\x5b\x43':
                        self.pointer += 1
                        work = work[3:]
                    elif work[:2] == '\x1b\x5b' and work[3] == '\x50':
                        work = work[4:]
                    # Needed?!
                    elif work[:1] != '\x07' and work[:1] != '\x0d':
                        self.command = self.command[:self.pointer] + work[:1] + self.command[self.pointer:]
                        self.pointer += 1
                        work = work[1:]
                    else:
                        self.pointer += 1
                        work = work[1:]

                self.upArrow = False
            
    def addInteractor(self, interactor):
        self.interactors.append(interactor)

    def del_interactor(self, interactor):
        self.interactors.remove(interactor)

    def inject(self, message):
        message = message.encode('utf8')
        # Log to TTY File
        self.out.interact_tty(self.ttylog_file, message)
        self.ssh.inject_key(self.clientID, message)
