###
# Copyright (c) 2014, Pierre-Yves Chibon
# Copyright (c) 2007, Mike McGrath
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import logging
import urllib

from datetime import datetime

import irc3
import koji

from irc3d import IrcServer
from irc3.compat import asyncio
from irc3.plugins.command import command


@irc3.plugin
class Koji(object):
    """ Plugin querying koji.
    """

    requires = [
        'irc3.plugins.core',
        'irc3.plugins.command',
    ]

    def __init__(self, bot):
        self.bot = bot

        koji_url = bot.config['koji']['url']
        self.koji_client = koji.ClientSession(koji_url, {})

    @command
    def building(self, mask, target, args):
        """building <builder>

        See what's building on a particular builder.

            %%building <builder>
        """
        builder = args['<builder>']

        k = self.koji_client
        try:
            for host in k.listHosts():
                if not host['name'].find(builder):
                    id = host['id']
        except AttributeError:
            msg = "Couldn't find builder: %s" % builder
            self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))
        else:
            try:
                tasks = k.listTasks(opts={
                    'host_id': id,
                    'method': 'buildArch',
                    'state': [koji.TASK_STATES['OPEN']],
                    'decode': True
                })
                for task in tasks:
                    msg = "%s - %s:%s" % (
                        builder, task['request'][0], task['request'][2])
                    self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))
                if not tasks:
                    msg = "%s - Not doing anything" % builder
                    self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))
            except UnboundLocalError:
                msg = "Builder %s doesn't exist" % builder
                self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))

    @command
    def taskload(self, mask, target, args):
        """ Return the number of running tasks.

            %%taskload
        """
        k = self.koji_client
        open = k.listTasks(opts={'state': [1]})
        total = k.listTasks(opts={'state': [0, 1, 4]})
        msg = "Tasks running - Open: %s Total: %s" % (len(open), len(total))
        self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))

    @command
    def buildload(self, mask, target, args):
        """Return the total load average of the build system.

            %%buildload
        """
        k = self.koji_client
        hosts = hosts = k.listHosts()
        total = 0
        load = 0
        for host in hosts:
            if host['enabled']:
                total = total + host['capacity']
                load = load + host['task_load']
        perc = (load / total * 100)
        if perc > 95:
            status = "Overload!"
        elif perc > 80:
            status = "Very High Load"
        elif perc > 60:
            status = "High Load"
        elif perc > 40:
            status = "Medium Load"
        elif perc > 30:
            status = "Light Load"
        elif perc > 0:
            status = "Very Light Load"
        elif perc == 0:
            status = "No Load"
        msg = 'Load: %.1f Total: %.1f Use: %.1f%% (%s)' % (
            load, total, perc, status)
        self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))

    @command
    def builders(self, mask, target, args):
        """ Check the status of the builders.

            %%builders
        """
        k = self.koji_client
        hosts = hosts = k.listHosts()
        total = 0
        ready = 0
        enabled = 0
        status = "Unknown"
        for host in hosts:
            ready = ready + host['ready']
            enabled = enabled + host['enabled']
            total = total + 1

        disabled = total - enabled

        msg = 'Enabled: %i Ready: %i Disabled: %i' % (
            enabled, ready, disabled)
        self.bot.privmsg(target, '%s: %s' % (mask.nick, msg))


def main():
    # logging configuration
    logging.config.dictConfig(irc3.config.LOGGING)

    loop = asyncio.get_event_loop()

    server = IrcServer.from_argv(loop=loop)
    bot = irc3.IrcBot.from_argv(loop=loop).run()

    loop.run_forever()


if __name__ == '__main__':
    main()
