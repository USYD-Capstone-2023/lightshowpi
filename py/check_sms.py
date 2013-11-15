#!/usr/bin/env python
#
# Author: Todd Giles (todd.giles@gmail.com)
#
# Feel free to use as you'd like, but I'd love to hear back from you on any
# improvements, changes, etc...

"""Check SMS messages from a Google Voice account

When executed, this script will check all the SMS messages from a Google Voice account
checking for either the "help" command, which will cause a help message to be sent back
to the original sender, or a single number indicating which song they are voting for.

When a song is voted for, the playlist file will be updated with the sender's cell 
phone number to indicate it has received a vote from that caller.  This also enforces
only a single vote per phone number per song (until that song is played).

Sample usage:

sudo check_sms.py --playlist=/home/pi/music/.playlist

Third party dependencies:

pygooglevoice: http://sphinxdoc.github.io/pygooglevoice/
Beautiful Soup: http://www.crummy.com/software/BeautifulSoup/

Note, I used the following version of pygooglevoice w/auth fix:
https://code.google.com/r/bwpayne-pygooglevoice-auth-fix/
"""

import argparse 
import csv
import fcntl
import sys
import time

from googlevoice import Voice
from bs4 import BeautifulSoup

import log as l

parser = argparse.ArgumentParser()
parser.add_argument('--playlist', required=True, help='filename with the song playlist, one song per line in the format: <song name><tab><path to song>')
parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2], default=1, help='change output logging verbosity')
args = parser.parse_args()
l.verbosity = args.verbosity

# Setup username / password in ~/.gvoice file as follows:
#
# [auth]
# email=<google voice email address>
# password=<google voice password>
#
voice = Voice()
voice.login()

def song_played(song) :
    """Send an sms message to each requesting user that their song is now playing"""
    global voice
    for phonenumber in song[2]:
        voice.send_sms(phonenumber, '"' + song[0] + '" is playing!')

# extractsms - taken from http://sphinxdoc.github.io/pygooglevoice/examples.html
# originally written by John Nagle (nagle@animats.com)
def extractsms(htmlsms) :
    """
    extractsms  --  extract SMS messages from BeautifulSoup tree of Google Voice SMS HTML.

    Output is a list of dictionaries, one per message.
    """
    msgitems = []
    tree = BeautifulSoup(htmlsms)			# parse HTML into tree
    conversations = tree("div",attrs={"id" : True, "class" : "gc-message-unread"},recursive=False)
    for conversation in conversations :
        #	For each conversation, extract each row, which is one SMS message.
        rows = conversation(attrs={"class" : "gc-message-sms-row"})
        for row in rows :								# for all rows
            #	For each row, which is one message, extract all the fields.
            msgitem = {"id" : conversation["id"]}		# tag this message with conversation ID
            spans = row("span",attrs={"class" : True}, recursive=False)
            for span in spans :							# for all spans in row
                cl = span['class'][0].replace('gc-message-sms-', '')
                msgitem[cl] = (" ".join(span.findAll(text=True))).strip()	# put text in dict
            msgitems.append(msgitem)					# add msg dictionary to list
    return msgitems

# Load playlist from file, notifying users of any of their requests that have now played
l.log('Loading playlist ' + args.playlist, 2)
with open(args.playlist, 'rb') as f:
    fcntl.lockf(f, fcntl.LOCK_SH)
    playlist = csv.reader(f, delimiter='\t')
    songs = []
    for song in playlist:
        l.log(song, 2)
        if len(song) < 2 or len(song) > 4:
            l.log('Invalid playlist', 0)
            sys.exit()
        elif len(song) == 2:
            song.append(set())
        elif len(song) >= 3:
            song[2] = set(song[2].split(','))
            if len(song) == 4:
                song_played(song)
                del song[3]
                song[2] = set()
        songs.append(song)
    fcntl.lockf(f, fcntl.LOCK_UN)

# Parse and act on any new sms messages
messages = voice.sms().messages
for msg in extractsms(voice.sms.html):
    l.log(str(msg), 2)
    try:
        song_num = int(msg['text'])
    except ValueError:
        song_num = 0
    if msg['from'] != 'Me' and song_num > 0 and song_num <= len(songs):
        song = songs[song_num-1]
        song[2].add(msg['from'])
        l.log('Song requested: ' + str(song))
        voice.send_sms(msg['from'], 'Thank you for requesting "' + song[0] + '", we\'ll notify you when it starts!')
    elif 'help' in msg['text'].lower():
        l.log('Help requested from ' + msg['from'])
        songlist = ['']
        division = 0
        index = 1
        for song in songs:
            songlist[division] += str(index) + ' - ' + song[0] + '\n'
            index += 1
            if (index - 1) % 5 == 0:
                division += 1
                songlist.append('')
        header = 'Vote by texting the song #:\n'
        for division in songlist:
            voice.send_sms(msg['from'], header + division)
            header = ''
            time.sleep(5)
    else:
        l.log('Unknown request: "' + msg['text'] + '" from ' + msg['from'])
        voice.send_sms(msg['from'], 'Hrm, not sure what you want.  Try texting "help" for... well some help!')

# Update playlist with latest votes
with open(args.playlist, 'wb') as f:
    fcntl.lockf(f, fcntl.LOCK_EX)
    writer = csv.writer(f, delimiter='\t')
    for song in songs:
        if len(song[2]) > 0:
            song[2] = ",".join(song[2])
        else:
            del song[2]
    writer.writerows(songs)
    fcntl.lockf(f, fcntl.LOCK_UN)

# Delete all mesages now that we've processed them
for msg in messages:
    msg.delete(1)

