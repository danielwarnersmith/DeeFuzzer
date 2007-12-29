#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2007-2007 Guillaume Pellerin <yomguy@parisson.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://svn.parisson.org/d-fuzz/wiki/DfuzzLicense.
#
# Author: Guillaume Pellerin <yomguy@parisson.com>

import os
import sys
import time
import string
import random
#import jack
import subprocess
from shout import Shout
from xmltodict import *
from threading import Thread
from Queue import Queue
from mutagen.oggvorbis import OggVorbis

version = '0.2.1a'

def prog_info():
        desc = '\n d-fuzz : easy and light streaming tool\n'
        ver = ' version : ' + version +'\n\n'
        info = """ Copyright (c) 2007-2007 Guillaume Pellerin <yomguy@parisson.com>
 All rights reserved.
        
 This software is licensed as described in the file COPYING, which
 you should have received as part of this distribution. The terms
 are also available at http://svn.parisson.org/d-fuzz/DFuzzLicense
        
 depends : python, python-xml, shout-python, libshout3, icecast2
 recommends : python-mutagen
 provides : shout-python
       
 Usage : d-fuzz $1
  where $1 is the path for a XML config file
  ex: d-fuzz /etc/d-fuzz/myfuzz.xml
 
 see http://parisson.com/d-fuzz/ for more details
        """
        text = desc + ver + info
        return text


class DFuzz:
    """A D-Fuzz station"""
    
    def __init__(self, conf_file):
        self.conf_file = conf_file

    def get_conf_dict(self):
        confile = open(self.conf_file,'r')
        conf_xml = confile.read()
        confile.close()
        dict = xmltodict(conf_xml,'utf-8')
        return dict

    def get_station_names(self):
        return self.conf['station']['name']

    def run(self):
        self.conf = self.get_conf_dict()
        #print self.conf

        # Fix wrong type data from xmltodict when one station (*)
        if isinstance(self.conf['d-fuzz']['station'], dict):
            nb_stations = 1
        else:
            nb_stations = len(self.conf['d-fuzz']['station'])
        print 'Number of stations : ' + str(nb_stations)

        # Create a Queue
        q = Queue()
        send = Stack()
        recv = Stack()
        s = Stations(q, send)
        station_timer = s.get_station_timer()
        print 'Station timer: ' + str(station_timer) + ' s'
        station_buffer = s.get_buffer_size()
        s.start()

        total_channel_number = 0
        for i in range(0,nb_stations):
            #time.sleep(0.1)
            # (*) idem
            if isinstance(self.conf['d-fuzz']['station'], dict):
                station = self.conf['d-fuzz']['station']
            else:
                station = self.conf['d-fuzz']['station'][i]
            #print station
            name = station['infos']['name']
            nb_channels = int(station['infos']['channels'])
            total_channel_number = total_channel_number + nb_channels
            print 'Station %s: %s has %s channels' % (str(i+1), name, str(nb_channels))

        channel_buffer = station_buffer * total_channel_number
        print 'Channel buffer size: ' + str(channel_buffer)
        
        for i in range(0,nb_stations):
            if isinstance(self.conf['d-fuzz']['station'], dict):
                station = self.conf['d-fuzz']['station']
            else:
                station = self.conf['d-fuzz']['station'][i]
            #print station
            name = station['infos']['name']
            nb_channels = int(station['infos']['channels'])
            for channel_id in range(0, nb_channels):
                #print channel_id
                #print channel_id
                c = Channel(station, channel_id + 1, channel_buffer, q, recv)
                c.start()
                time.sleep(0.1)

class Widget:
    pass

class Stack:
    def __init__(self):
        self.__stack = list()
    def __len__(self):
        return len(self.__stack)
    def push(self, item):
        self.__stack.append(item)
    def pop(self):
        return self.__stack.pop()

class Stations(Thread):
    """D-Fuzz Station (Producer) thread"""

    def __init__(self, station_q, send):
        Thread.__init__(self)
        self.station_q = station_q
        self.send = send
        self.buffer_size = 16384
        print 'Station buffer size: ' + str(self.buffer_size)
        self.frequency = 44100
        self.station_timer = float(int(self.buffer_size)) / self.frequency
        
    def get_station_timer(self):
        return self.station_timer

    def get_buffer_size(self):
        return self.buffer_size
    
    def run(self):
        station_q = self.station_q
        send = self.send
        #i=0  
        while True: 
            #print currentThread(),"Produced One Item:",i
            #time.sleep(self.station_timer)
            item = Widget()
            station_q.put(item)
            #send.push(item)
            #station_q.put(i,1)
            #i+=1
        station_q.join()
            


class Channel(Thread):
    """A channel shouting thread"""

    def __init__(self, station, channel_id, channel_buffer, channel_q, recv):
        Thread.__init__(self)
        self.channel_q = channel_q
        self.recv = recv
        self.station = station
        self.main_command = 'cat'
        self.channel_id = channel_id
        self.channel = Shout()
        self.id = 999999
        self.counter = 0
        self.frequency = 44100
        self.buffer_size = channel_buffer
        self.timer = self.buffer_size / self.frequency
        self.rand_list = []
        # Media
        self.media_dir = self.station['media']['dir']
        self.channel.format = self.station['media']['format']
        self.mode_shuffle = int(self.station['media']['shuffle'])
        # Infos
        self.short_name = self.station['infos']['short_name'] + '_' + str(self.channel_id)
        self.channel.name = self.station['infos']['name'] + '_' + str(self.channel_id)
        self.channel.genre = self.station['infos']['genre']
        self.channel.description = self.station['infos']['description']
        self.channel.url = self.station['infos']['url']
        # Server
        self.channel.protocol = 'http'     # | 'xaudiocast' | 'icy'
        self.channel.host = self.station['server']['host']
        self.channel.port = int(self.station['server']['port'])
        self.channel.user = 'source'
        #self.channel.nonblocking = True
        self.channel.password = self.station['server']['sourcepassword']
        self.channel.mount = '/' + self.short_name + '.' + self.channel.format
        #print self.channel.mount
        self.channel.public = int(self.station['server']['public'])
        # s.audio_info = { 'key': 'val', ... }
        #  (keys are shout.SHOUT_AI_BITRATE, shout.SHOUT_AI_SAMPLERATE,
        #   shout.SHOUT_AI_CHANNELS, shout.SHOUT_AI_QUALITY)
        self.formats = ['mp3', 'ogg', 'flac']


    def get_file_extension(self, file):
        file_split = file.split('.')
        return file_split[len(file_split)-1]
    
    def get_playlist(self):
        file_list = []
        for root, dirs, files in os.walk(self.media_dir):
            for file in files:
                extension = self.get_file_extension(file)
                if extension in self.formats:
                    file_list.append(root + os.sep + file)
        return file_list

    def get_next_media_lin(self, playlist):
        lp = len(playlist)
        if self.id >= (lp -1):
            playlist = self.get_playlist()
            self.id = 0
        else:
            self.id = self.id + 1
        return playlist, playlist[self.id]
    
    def get_next_media_rand(self, playlist):
        lp = len(playlist)
        if self.id >= (lp - 1):
            #print 'Get random list...'
            playlist = self.get_playlist()
            lp_new = len(playlist)
            if lp_new != lp or self.counter == 0:
                self.rand_list = range(0,lp_new)
                random.shuffle(self.rand_list)
                #print self.rand_list
            self.id = 0
        else:
            self.id = self.id + 1
        index = self.rand_list[self.id]
        #print str(self.id) +':'+ str(index)
        return playlist, playlist[index]

    def core_process(self, command, buffer_size):
        """Apply command and stream data through a generator. 
        Taken from Telemeta..."""
        __chunk = 0
        try:
            proc = subprocess.Popen(command,
                                    shell = True,
                                    bufsize = buffer_size,
                                    stdin = subprocess.PIPE,
                                    stdout = subprocess.PIPE,
                                    close_fds = True)
        except:
            raise DFuzzError('Command failure:', command, proc)
        # Core processing
        while True:
            __chunk = proc.stdout.read(buffer_size)
            status = proc.poll()
            if status != None and status != 0:
                raise DFuzzError('Command failure:', command, proc)
            if len(__chunk) == 0:
                break
            yield __chunk

    def run(self):
        #print "Using libshout version %s" % shout.version()
        #__chunk = 0
        recv = self.recv
        channel_q = self.channel_q
        self.channel.open()
        print 'Opening ' + self.channel.name + '...'
        #time.sleep(0.1)

        # Playlist
        playlist = self.get_playlist()
        lp = len(playlist)
	print 'There are ' + str(lp) + ' items in your playlist'
        self.rand_list = range(0,lp)
        
        while True:
            if lp == 0:
                break
            if self.mode_shuffle == 1:
                #print 'Shuffle mode'
                playlist, media = self.get_next_media_rand(playlist)
            else:
                playlist, media = self.get_next_media_lin(playlist)
            self.counter += 1
            file_name = string.replace(media, self.media_dir + os.sep, '')
            #print 'Playlist (%s ch%s) : %s' % (self.short_name, self.channel_id, file_name)
            #print playlist
            #print media
            self.channel.set_metadata({'song': file_name})
            command = self.main_command + ' "%s"' % media
            stream = self.core_process(command, self.buffer_size)
            #stream = Stream(self.media_dir, media)
            print 'D-fuzzing this file on %s (channel: %s, track: %s): %s' % (self.short_name, self.channel_id, self.id, file_name)

            for __chunk in stream:
                # Wait
                #time.sleep(self.timer)
                q = channel_q.get()
                #if q is None:
                #    break
                #recv.push(channel_q.get())
                #self.channel_q.get(1)
                #print self.channel.delay()
                self.channel.send(__chunk)
                #print self.channel.delay()
                self.channel.sync()
                #channel_q.task_done()
                #print self.channel.queuelen()

        self.channel.close()


class Jack:
    """A connexion to the JACK server"""

    def __init__(self):
        self.name = 'D-Fuzz'
        pass
        


class DFuzzError:
    """The D-Fuzz main error class"""
    def __init__(self, message, command, subprocess):
        self.message = message
        self.command = str(command)
        self.subprocess = subprocess

    def __str__(self):
        if self.subprocess.stderr != None:
            error = self.subprocess.stderr.read()
        else:
            error = ''
        return "%s ; command: %s; error: %s" % (self.message,
                                                self.command,
                                                error)

def main():    
    if len(sys.argv) == 2:
        print "D-fuzz v"+version
        dfuzz_main = DFuzz(sys.argv[1])
        dfuzz_main.run()
    else:
        text = prog_info()
        sys.exit(text)

if __name__ == '__main__':
    main()

