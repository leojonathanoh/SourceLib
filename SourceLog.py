#!/usr/bin/python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# SourceLog - Python class for parsing logs of Source Dedicated Servers
# Copyright (c) 2010 Andreas Klauer <Andreas.Klauer@metamorpher.de>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#------------------------------------------------------------------------------

# TODO:  Support games other than Team Fortress 2

"""http://developer.valvesoftware.com/wiki/HL_Log_Standard"""

import re
import socket
import asyncore

PACKETSIZE=1400

# --- Regular Expressions: ---

TOKEN = {
    'attacker': '(?P<attacker_name>.*?)<(?P<attacker_uid>[0-9]{1,3}?)><(?P<attacker_steamid>(Console|BOT|STEAM_[01]:[01]:[0-9]{1,12}))><(?P<attacker_team>[^<>"]*)>',
    'timestamp': '(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<year>[0-9]{4}) - (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2}): ',
    'player': '(?P<name>.*?)<(?P<uid>[0-9]{1,3}?)><(?P<steamid>(Console|BOT|STEAM_[01]:[01]:[0-9]{1,12}))><(?P<team>[^<>"]*)>',
    'position': '^(?P<x>-?[0-9]+) (?P<y>-?[0-9]+) (?P<z>-?[0-9]+)',
    'property': ' \((?P<key>[^() ]+) "(?P<value>[^"]*)"\)',
    'rest': '(?P<rest>.*)',
    'string': '"(?P<string>[^"]*)"',
    'type': '(?P<type>RL|L) ',
    'victim': '(?P<victim_name>.*?)<(?P<victim_uid>[0-9]{1,3}?)><(?P<victim_steamid>(Console|BOT|STEAM_[01]:[01]:[0-9]{1,12}))><(?P<victim_team>[^<>"]*)>',
}

REHEADER = re.compile('^'+TOKEN['type']+TOKEN['timestamp']+TOKEN['rest']+'$', re.U)
REPROPERTY = re.compile('^'+TOKEN['rest']+TOKEN['property']+'$', re.U)

RELOG = [
]

REVALUE = [
    ['position', re.compile('^'+TOKEN['position']+'$', re.U)],
    ['player', re.compile('^'+TOKEN['player']+'$', re.U)],
]

# There is nothing we can do about malicious players, but we are restrictive
class SourceLogParser(object):
    def parse_value(self, key, value):
        for k, v in REVALUE:
            match = v.match(value)

            if match:
                r = match.groupdict()
                r['type'] = k

        return value

    def action(self, remote, timestamp, key, value, properties):
        print "action", repr(remote), repr(timestamp), repr(key), repr(value), repr(properties)

    def parse(self, line):
        line = line.strip('\x00\xff\r\n\t ')

        print "parse", repr(line)

        # parse header (type and date)
        match = REHEADER.match(line)

        if not match:
            # invalid log entry
            return

        line = match.group('rest')

        remote = False
        if match.group('type') == 'RL':
            remote = True

        timestamp = map(int, match.group('year', 'month', 'day', 'hour', 'minute', 'second'))

        # parse properties (key "value"), optional
        properties = {}

        while 1:
            match = REPROPERTY.match(line)

            if not match:
                break

            line = match.group('rest')
            key = match.group('key')
            value = match.group('value')
            value = self.parse_value(key, value)
            properties[key] = value

        # parse the log entry
        for k, v in RELOG:
            match = v.match(line)

            if match:
                self.action(remote, timestamp, k, match.groupdict(), properties)
                return

        # not sure what to do here
        self.unknown_action(remote, timestamp, properties, line)

    def parse_file(self, filename):
        f = open(filename, 'r')

        for line in f:
            self.parse(line)

class SourceLogListenerError(Exception):
    pass

class SourceLogListener(asyncore.dispatcher):
    def __init__(self, local, remote, parser):
        asyncore.dispatcher.__init__(self)
        self.parser = parser
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(local)
        self.connect(remote)

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(PACKETSIZE)

        if data.startswith('\xff\xff\xff\xff') and data.endswith('\n\x00'):
            self.parser.parse(data)

        else:
            print "invalid packet", repr(data)
            raise SourceLogListenerError("Received invalid packet.")

    def writable(self):
        return False

    def handle_write(self):
        pass
