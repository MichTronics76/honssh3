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

from honssh.config import Config
from twisted.python import log as twisted_log

PLAIN = '\033[0m'
RED = '\033[0;31m'
LRED = '\033[1;31m'
GREEN = '\033[0;32m'
LGREEN = '\033[1;32m'
YELLOW = '\033[0;33m'
LYELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
LBLUE = '\033[1;34m'
PURPLE = '\033[0;35m'
LPURPLE = '\033[1;35m'
CYAN = '\033[0;36m'
LCYAN = '\033[1;36m'

cfg = Config.getInstance()


def msg(*args):
    """Unified logging helper.

    Supports two call patterns:
      msg(color, identifier, message) -> legacy HonSSH internal usage (preferred).
      msg(single_string)              -> backward compatibility / quick messages.

    Any other arity collapses all arguments into a space separated message.
    """
    if len(args) == 3:
        color, identifier, message = args
    elif len(args) == 1:
        color = ''
        identifier = '[HONSSH]'
        message = args[0]
    else:
        color = ''
        identifier = '[HONSSH]'
        message = ' '.join(repr(a) for a in args)

    if not isinstance(message, str):
        message = repr(message)

    # When devmode enabled include color codes (if provided)
    if cfg.has_option('devmode', 'enabled') and cfg.getboolean(['devmode', 'enabled']):
        twisted_log.msg(color + identifier + ' - ' + message + '\033[0m')
    else:
        twisted_log.msg(identifier + ' - ' + message)
