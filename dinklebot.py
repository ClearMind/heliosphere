# -*- coding: utf-8 -*-
__author__ = 'artemredkin'

import json
import urllib
import urlparse
import db
import telegram
import collections

from datetime import datetime, timedelta
from google.appengine.api import urlfetch


def parse(message):
    values = message.split(None, 1)
    if len(values) == 1:
        return values[0], None
    return values


class Command:

    def call(self, chat, author, arguments):
        pass

    def help(self):
        pass

    def name(self):
        pass

    def description(self):
        pass


class EchoCommand(Command):

    def call(self, chat, author, arguments):
        telegram.send(chat, arguments)

    def help(self):
        return "Usage: !echo <string>"

    def name(self):
        return "!echo"

    def description(self):
        return "Send back message"


class RsvpCommand(Command):

    @staticmethod
    def pretty_date(event):
        date = event.date
        today = datetime.today().date()
        if date.date() == today:
            return "Today"
        elif date.date() == today - timedelta(hours=24):
            return "Tomorrow"
        else:
            return date.strftime('%A, %B %d')

    def pretty_event(self, event):
        event_name = db.find_type(event.type.id()).name
        participants = '[' + ', '.join(event.participants) + ']'
        s = self.pretty_date(event) + '\t' + event.date.strftime('%H:%M') + '\t' + event_name + '\t' + participants
        if len(event.comment) > 0:
            s = s + u'\t–\t' + event.comment
        return s

    def call(self, chat, author, cmd):
        if cmd.startswith('register'):
            psn_id = cmd.split(None, 1)[1]
            player = db.find_player_by_psn_id(psn_id)
            if player is None:
                return
            db.register_player_telegram(player, author)
            telegram.send(chat, psn_id + " registered")
            return
        player = db.find_player_by_telegram_id(author)
        if player is None:
            telegram.send(chat, "Introduce yourself by providing your psn id: !r register <psn-id>")
            return
        if cmd == 'list':
            event_list = db.find_events()
            if len(event_list) == 0:
                telegram.send(author, "No events")
                return
            events = '\n'.join(map(self.pretty_event, event_list)).encode('utf-8')
            telegram.send(chat, events)

    def help(self):
        return """Usage
register:
    !r register <psn-id>

list all events:
    !r list

list your events:
    !r list my

add event:
    !r new <event type> <date> at <time>

join event:
    !r join <event id>

leave event:
    !r leave <event id>

delete event:
    !r rm <event id>

update event:
    !r <event id> <event type> <date> at <time>
"""

    def name(self):
        return "!r"

    def description(self):
        return "Heliosphere LFG"


class ImageCommand(Command):

    def __init__(self):
        self.google_search_key = db.get_key('google_search')

    def call(self, chat, author, q):
        data = {
            'key': self.google_search_key,
            'cx': '009373417816394415455:i3e_omr58us',
            'q': q,
            'searchType': 'image',
            'num': 1
        }
        response = urlfetch.fetch(url='https://www.googleapis.com/customsearch/v1?' + urllib.urlencode(data), method=urlfetch.GET)
        items = json.loads(response.content)['items']
        if len(items) == 0:
            telegram.send(chat, "Nothing found")
            return
        image = items[0]
        image_url = image['link']
        image_response = urlfetch.fetch(image_url, method=urlfetch.GET)
        if image_response.status_code != 200:
            telegram.send(chat, "Error retrieving image")
            return
        image_name = urlparse.urlsplit(image_url).path.split('/')[-1]
        telegram.send_image(chat, image_response.content, image_name, image['mime'])

    def help(self):
        return "Usage: !img <query>"

    def name(self):
        return "!img"

    def description(self):
        return "Google Image Search"


commands = collections.OrderedDict({
    '!echo': EchoCommand(),
    '!img': ImageCommand(),
    '!r': RsvpCommand(),
})


def recieve(request):
    (chat, author, message) = telegram.recieve(request)
    if message.startswith('!'):
        (command, arguments) = parse(message)
        if command == '!help':
            if arguments is not None:
                cmd = '!' + arguments
                if cmd not in commands:
                    telegram.send(chat, "Uknown command: " + str(arguments))
                    return
                telegram.send(chat, commands[cmd].help())
                return

            response = 'Commands:'
            for name, command in commands.iteritems():
                response += '\n' + name + ': ' + command.description()
            response += '\n\nType !help <command> to know more'
            telegram.send(chat, response)
            return
        if command in commands:
            commands[command](chat, author, arguments)
