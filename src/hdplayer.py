#!/usr/bin/env python3
import vlc
import socket
import socketserver
import time
import os
import math

import subprocess
import shlex
import json

import re

from asyncio_event import asyncio_event

class HyperDeckPlayer():
    _playing = False 
    _debug = False
    media = None
    _event = asyncio_event()

    def __init__(self):
        self._instance = vlc.Instance(['--video-on-top'])#, '--start-paused'])
        self._medialist = self._instance.media_list_new()
        self._listplayer = self._instance.media_list_player_new()
        #self._listplayer.set_media_player(player)
        self._player = self._instance.media_player_new()
        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self.SongFinished)
        events.event_attach(vlc.EventType.MediaPlayerPlaying, self.ePlaying)
        events.event_attach(vlc.EventType.MediaPlayerStopped, self.eStopped)
        events.event_attach(vlc.EventType.MediaPlayerPaused, self.ePaused)
        events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.poschanged)
        events.event_attach(vlc.EventType.MediaPlayerPausableChanged, self.ePausable)
        events.event_attach(vlc.EventType.MediaPlayerUncorked, self.eUncorked)
        events.event_attach(vlc.EventType.MediaPlayerVout, self.eVout)
        events.event_attach(vlc.EventType.MediaPlayerOpening, self.eOpening)
        events.event_attach(vlc.EventType.MediaPlayerBuffering, self.eBuffering)
        events.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.eTimeChanged)
        events.event_attach(vlc.EventType.MediaPlayerMediaChanged, self.eMediaChanged)
        events.event_attach(vlc.EventType.MediaPlayerAudioVolume, self.eAudioVolume)
        events.event_attach(vlc.EventType.MediaPlayerLengthChanged, self.eLengthChanged)
        self._listplayer.set_media_player(self._player)
        self._player.set_fullscreen(True)
    def registerEvent(self, name, func):
        self._event.register(name, func)
    def time_to_timecode(self, time, fps):
        h = 0
        m = 0
        s = 0
        f = 0
        t = time
        s = t/1000
        if s >= 61:
            m = math.floor(s / 60)
            s -= m * 60
        if m > 60:
            h = math.floor(m / 60)
            m -= h * 60
        (milli, s) = math.modf(s)
        s = int(s)
        f = math.floor(fps * milli)
        return (h,m,s,f)
    def get_time(self):
        return self._player.get_time()
    def get_length(self):
        return self._player.get_length()
    def SongFinished(self, event):
        global finish
        print ("Event reports - finished")
        #self._player.pause()
        #self._player.set_time(30000)
        finish = 1
    def poschanged(self, event):
        #print("poschanged")
        if self._playing == False and self._player.has_vout():
            self._player.pause()

        pass#print(time)
    def ePlaying(self, event):
        self._event.emitX("statechanged", None)
        if self._debug:
            print("ePlaying")
        if self._playing == False and self._player.has_vout():
            self._player.pause()
        pass#self.is_playing = True
    def eStopped(self, event):
        self._event.emitX("statechanged", None)

        print("eStopped")
        pass#self.is_playing = False
    def ePaused(self, event):
        self._event.emitX("statechanged", None)

        if self._debug:
            print("ePaused")
        pass#self.is_playing = False
    def eTimeChanged(self, event):
        #self._event.emitX("statechanged", None)
        if self._debug:
            print("eTimeChanged")
    def ePausable(self, event):
        if self._playing == False:
            self._player.pause()
        if self._debug:
            print("ePausable")
    def eUncorked(self, event):
        print("eUncorked")
    def eOpening(self, event):
        self._event.emitX("statechanged", None)

        if self._debug:
            print("eOpening")
    def eBuffering(self, event):
        if self._debug:
            print("eBuffering") #, event.getBuffering())
    def get_state(self):
        return self._player.get_state()
    def eMediaState(self, event):
        self._event.emitX("statechanged", None)

        print ("eMedia", self.media.get_state())
    def eVout(self, event):
        if self._debug:
            print ("eVout")
        if self._playing == False and self._player.has_vout():
            self._player.pause()

    def eLengthChanged(self, event):
        self._event.emitX("statechanged", None)
        if self._debug:
            print("eLengthChanged")

    def eMediaChanged(self, event):
        self._event.emitX("statechanged", None)
        if self._debug:
            print("eMediaChanged")

    def eAudioVolume(self, event):
        self._event.emitX("statechanged", None)

        if self._debug:
            print("eAudioVolume")

    def audio_get_volume(self):
        return self._player.audio_get_volume()
    def audio_set_volume(self, vol):
        return self._player.audio_set_volume(vol)
    def is_playing(self):
        return self._player.is_playing()
    def get_fps(self):
        return self._player.get_fps()
    def get_rate(self):
        return self._player.get_rate()
    def get_duration(self):
        if self.media:
            return self.media.get_duration()
        return None
    def set_rate(self, rate):
        self._player.set_rate(rate)
    def set_time(self, time):
        self._player.set_time(time)

    def load(self, path):
        self.media = self._instance.media_new(path)
        self.media.add_option(':network-caching=90000')
        events = self.media.event_manager()
        events.event_attach(vlc.EventType.MediaStateChanged, self.eMediaState)

        self._player.set_media(self.media)
        self.media.parse()
        #mfps = int(1000 / (self._player.get_fps() or 30))

        #self._player.set_time(1)
        #t = self._player.get_time()
        #print("TIME: ", t)
        #while self._player.get_state() in [vlc.State.Playing, vlc.State.Opening, vlc.State.NothingSpecial]:
        #    self._player.pause()
        #    print(self._player.get_state(), self._player.is_playing())
        #print(self._player.get_state())
        #self._player.set_time(0)
        #self._player.pause()
        print(self._player.get_state())
        #time.sleep(1)
        self._player.play()

        self._player.play()
        print ("NEXT")
        #self._player.set_pause(1)
        #self._player.next_frame()
        #self._player.set_time(30000)
        #time.sleep(1)
        #self._player.pause()
        #while self._player.get_state() == 4 or self._player.get_state() == 0:
        #    print(self._player.get_state())
        print(self._player.get_state())
        print("XX", self._player.get_state())
        
    def play(self):
        if self.media:
            self._playing = True
            self._player.play()
            return True
        else:
            return False
    def stop(self):
        self._playing = False
        self._player.stop()
    def pause(self):
        if self._player.is_playing():
            self._playing = False
            self._player.pause()
