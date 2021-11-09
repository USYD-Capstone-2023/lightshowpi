#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B

import cgi
import cgitb
import os
import sys
import fcntl
import csv
import subprocess
import configparser
import mutagen
import re
from time import sleep

import pwd
import grp

uid = pwd.getpwnam("pi").pw_uid
gid = grp.getgrnam("pi").gr_gid

file_types = [".wav", ".mp1", ".mp2", ".mp3", ".mp4", ".m4a", ".m4b", ".ogg", ".flac", ".oga", ".wma", ".wmv", ".aif"]

endmessage = ""

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')
import configuration_manager

state_file = HOME_DIR + '/web/microweb/config/webstate.cfg'
state = configparser.RawConfigParser()
state.read_file(open(state_file))
config_file = state.get('microweb','config')
if config_file:
    config_param = '--config=' + config_file 
else:
    config_param = None
    config_file = 'defaults.cfg'

cm = configuration_manager.Configuration(param_config=config_file)

music_path = (HOME_DIR + '/music/')

config_path = (HOME_DIR + '/config/' + config_file)
overrides = configparser.RawConfigParser()
overrides.read_file(open(config_path))
playlist_path = overrides.get('lightshow','playlist_path')
playlist_path = playlist_path.replace('$SYNCHRONIZED_LIGHTS_HOME',HOME_DIR)
playlist_dir = os.path.dirname(playlist_path)

cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
songplay = form.getvalue("songplay", "")
message = form.getvalue("message", "")
recreate = form.getvalue("recreate", "")
updown = form.getvalue("updown", "")
upload = form.getvalue("upload", "")
directory = form.getvalue("Directory", "")

if message == 'Change Directory':
    state.set('microweb','dirplay', directory)
    with open(state_file, 'w') as state_fp:
        state.write(state_fp)

if message == "Create Directory":
    p = re.compile('^\w+$', re.ASCII)
    if p.match(directory):
        os.mkdir(music_path + '/' + directory)
        os.chown(music_path + '/' + directory, uid, gid)
    else:
        endmessage = "Invalid Characters for Create Directory"

dirplay_path = state.get('microweb','dirplay')
if dirplay_path:
    playlist_dir = dirplay_path
else:
    dirplay_path = playlist_dir
    
if songplay:
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
    os.popen('python ${SYNCHRONIZED_LIGHTS_HOME}/py/synchronized_lights.py --file="' + playlist_dir + '/' + songplay + '" &')

if message == 'Start':
    os.system('rm $SYNCHRONIZED_LIGHTS_HOME/config/state.cfg')
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
    os.popen("${SYNCHRONIZED_LIGHTS_HOME}/bin/start_playlist_loop " + playlist_dir + '/.playlist' + " &")

if message == 'Start Once':
    os.system('rm $SYNCHRONIZED_LIGHTS_HOME/config/state.cfg')
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
    os.popen("${SYNCHRONIZED_LIGHTS_HOME}/bin/start_playlist_once " + playlist_dir + '/.playlist' + " &")

print ("Content-type: text/html")
print

print ("""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>LightShowPi Web Controls</title>
        <meta name="description" content="A very basic web interface for LightShowPi">
        <meta name="author" content="Ken B">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="shortcut icon" href="/favicon.png">
        <meta name="mobile-web-app-capable" content="yes">
        <link rel="icon" sizes="196x196" href="/favicon.png">
        <link rel="apple-touch-icon" sizes="152x152" href="/favicon.png">
        <link rel="stylesheet" href="/css/style.css">
    </head>
    <body>
            <h2> LightShowPi Web Controls </h2>
            <h3> Directory Play </h3>

            <form method="post" action="web_controls.cgi">
                <input id="playlist" type="submit" value="Home">
            </form>
            <form method="post" action="playlist.cgi">
                <input id="playlist" type="submit" value="Back">
            </form>

            <p></p>

            <form method="post" action="dir_play.cgi">
                <select name="Directory">
""") 
print ('<option value="' + os.path.dirname(playlist_path) + '">Config Default</option>')
for root,subdirs,files in os.walk(music_path):
    if root == dirplay_path:
        print ('<option value="' + root + '" selected>' + root + '</option>')
    elif root != music_path:
        print ('<option value="' + root + '">' + root + '</option>')

print ("""
                </select>
                <p></p>
                <input type="hidden" name="message" value="Change Directory"/>
                <input id="playlist" type="submit" value="Change Directory">
            </form>

            <p></p>

            <form method="post" action="dir_play.cgi">
                <input type="text" name="Directory">
                <p></p>
                <input type="hidden" name="message" value="Create Directory"/>
                <input id="playlist" type="submit" value="Create Directory">
            </form>

            <p></p>

            <form method="post" action="dir_play.cgi">
                <input type="hidden" name="message" value="Edit Songs"/>
                <input id="playlist" type="submit" value="Edit Songs">
            </form>

            <p></p>

            <form method="post" action="dir_play.cgi" enctype="multipart/form-data">
                <input id="playlist" type="submit" value="Upload Files" />
                <p>
                <input type="file" name="upload" value="Select Files" multiple/>
                </p>
            </form>

            <p></p>


""") 


if upload:
    message = 'Edit Songs'
    if not os.path.isdir(playlist_dir):
        print ('<p><h2>Please create ' + playlist_dir + '</h2></p>')
        print ("</body></html>")
        sys.exit()
    filedata = form['upload']
    if isinstance(filedata, list):
        print ('<p><h2>Selected multiple</h2></p>')
        for fsel in filedata:
            filename = playlist_dir + '/' + fsel.filename
            print ('<p><h2>Uploading ' + filename + '</h2></p>')
            if os.path.splitext(filename)[1] in file_types:
                open(filename, 'wb').write(fsel.file.read())
                os.chown(filename, uid, gid)
    else:
        print ('<p><h2>Selected one</h2></p>')
        filename = playlist_dir + '/' + filedata.filename
        print ('<p><h2>Uploading ' + filename + '</h2></p>')
        if os.path.splitext(filename)[1] in file_types:
            open(filename, 'wb').write(filedata.file.read())
            os.chown(filename, uid, gid)
    

if recreate:
    message = 'Edit Songs'
    entries = []
    make_title = lambda s: s.replace("_", " ").replace(ext, "") + "\t"
    for song in sorted(os.listdir(playlist_dir)):
        ext = os.path.splitext(song)[1]
        if form.getvalue(song):
            metadata = mutagen.File(playlist_dir + '/' + song, easy=True)
            if metadata is not None:
                if "title" in metadata:
                    mtitle = ''.join([i if ord(i) < 128 else '_' for i in metadata["title"][0]])
                    title = mtitle + "\t"
                else:
                    title = make_title(song)
            else:
                title = make_title(song)

            entry = title + os.path.join(playlist_dir, song)
            entries.append(entry)
    if len(entries) > 0:
        with open(playlist_dir + '/.playlist', "w") as playlist:
            playlist.write("\n".join(str(entry) for entry in entries))
            playlist.write("\n")
        
        os.chown(playlist_dir + '/.playlist', uid, gid)

        print ("<p>Playlist Updated")

if updown:
    message = 'Edit Songs'
    songupdown = form.getvalue('songupdown')

    entries = []
    counter = 0
    for song in sorted(os.listdir(playlist_dir)):
        if os.path.splitext(song)[1] in file_types:
            pre = song.split(".")[0]
            if not pre.isdigit():
                os.rename(playlist_dir + '/' + song, playlist_dir + '/' + '%02d' % counter + '.' + song)
                entries.append('%02d' % counter + '.' + song)
                if (song == songupdown):
                    songupdown = '%02d' % counter + '.' + song
            else:
                entries.append(song)
            counter += 1

    if updown == 'UP':
        if entries.index(songupdown) > 0:
            a,b = entries.index(songupdown), entries.index(songupdown) - 1
            entries[a], entries[b] = entries[b], entries[a]
            counter = 0
            for song in entries:
                pre = song.split(".")[0]
                post = song.split(".")[1:]
                os.rename(playlist_dir + '/' + song, playlist_dir + '/' + '%02d' % counter + '.' + ".".join(post))
                if os.path.isfile(playlist_dir + '/' + '.' + song + '.sync'):
                    os.rename(playlist_dir + '/' + '.' + song + '.sync', playlist_dir + '/' + '.%02d' % counter + '.' + ".".join(post) + '.sync')
                if os.path.isfile(playlist_dir + '/' + '.' + song + '.cfg'):
                    os.rename(playlist_dir + '/' + '.' + song + '.cfg', playlist_dir + '/' + '.%02d' % counter + '.' + ".".join(post) + '.cfg')
                counter += 1

    if updown == 'DN':
        if entries.index(songupdown) < len(entries) - 1:
            a,b = entries.index(songupdown), entries.index(songupdown) + 1
            entries[a], entries[b] = entries[b], entries[a]
            counter = 0
            for song in entries:
                pre = song.split(".")[0]
                post = song.split(".")[1:]
                os.rename(playlist_dir + '/' + song, playlist_dir + '/' + '%02d' % counter + '.' + ".".join(post))
                if os.path.isfile(playlist_dir + '/' + '.' + song + '.sync'):
                    os.rename(playlist_dir + '/' + '.' + song + '.sync', playlist_dir + '/' + '.%02d' % counter + '.' + ".".join(post) + '.sync')
                if os.path.isfile(playlist_dir + '/' + '.' + song + '.cfg'):
                    os.rename(playlist_dir + '/' + '.' + song + '.cfg', playlist_dir + '/' + '.%02d' % counter + '.' + ".".join(post) + '.cfg')
                counter += 1
                
    
if message:

    if message == "Stop":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')

    if message == 'Edit Songs':
        checkedfiles = []
        if os.path.isfile(playlist_dir + '/.playlist'):
            with open(playlist_dir + '/.playlist', "r") as playlist:
                for line in playlist:
                    line = line.split("\t")[1]
                    line = os.path.basename(line)
                    line = line.rstrip("\r\n")
                    pre = line.split(".")[0]
                    if pre.isdigit():
                        post = ".".join(line.split(".")[1:])
                    else:
                        post = line
                    checkedfiles.append(post)

        if not os.path.isdir(playlist_dir):
            print ('<p><h2>Please create ' + playlist_dir + '</h2></p>')
            print ("</body></html>")
            sys.exit()
        print ('<p><div id="songlist">')
        print ('<form method="post" action="dir_play.cgi">')
        print ('<table>')
        for song in sorted(os.listdir(playlist_dir)):
            if os.path.splitext(song)[1] in file_types:
                pre = song.split(".")[0]
                if pre.isdigit():
                    post = ".".join(song.split(".")[1:])
                else:
                    post = song
                if post in checkedfiles:
                    chk = 'checked="checked"'
                else:
                    chk = ''
                print ('<tr>')
                print ('<td><input type="checkbox" name="' + song + '" value="' + song + '" ' + chk + '>' + song + '</td>')
                print ('<td><form method="post" name="updown"><input type="hidden" name="songupdown" value="' + song + '"/><input id="updown" name="updown" type="submit" value="UP"></form></td>')
                print ('<td><form method="post" name="updown"><input type="hidden" name="songupdown" value="' + song + '"/><input id="updown" name="updown" type="submit" value="DN"></form></td>')
                print ('</tr>')
        print ('</table>')
        print ('<p><input id="recreate" name="recreate" type="submit" value="Recreate Playlist">')
        print ('</form>')
        print ('</div>')
       
print ('<form method="post" action="dir_play.cgi">')
print ('<input type="hidden" name="message" value="Stop">')
print ('<input id="playitem" type="submit" name="Stop" value="Stop Playback">')
print ('</form>')

if os.path.isfile(playlist_dir + '/.playlist'):

    print ('<form method="post" action="dir_play.cgi">')
    print ('<input type="hidden" name="message" value="Start">')
    print ('<input id="playitem" type="submit" name="Start" value="Loop Playlist">')
    print ('</form>')

    print ('<form method="post" action="dir_play.cgi">')
    print ('<input type="hidden" name="message" value="Start Once">')
    print ('<input id="playitem" type="submit" name="Start Once" value="Play Playlist Once">')
    print ('</form>')

    with open(playlist_dir + '/.playlist' , 'r') as playlist_fp:
        fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
        playlist = csv.reader(playlist_fp, delimiter='\t')

        for song in playlist:
            print ('<form method="post" action="dir_play.cgi?songplay=' + os.path.basename(song[1]) + '">')
            print ('<input id="playnext" type="submit" name="' + os.path.basename(song[1]) + '" value="' + song[0] + '">')
            print ('</form>')

        fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

else:
    print ('Playlist must be created')

if endmessage:
    print(endmessage)
        
if songplay:
    print("playing " + songplay)

print ("</body></html>")
