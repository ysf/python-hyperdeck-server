#!/usr/bin/env python3
import vlc
import socket
import threading
import socketserver
import time
import os
import math

import subprocess
import shlex
import json

class HyperDeckPlayer():
    
    def __init__(self):
        self._instance = vlc.Instance(['--video-on-top', '--start-paused'])
        self._player = self._instance.media_player_new()
        self._player.set_fullscreen(True)
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
        pass#print(time)
    def ePlaying(self):
        pass#self.is_playing = True
    def eStopped(self):
        pass#self.is_playing = False
    def ePaused(self):
        pass#self.is_playing = False
    def is_playing(self):
        return self._player.is_playing()
    def get_fps(self):
        return self._player.get_fps()
    def get_rate(self):
        return self._player.get_rate()
    def set_rate(self, rate):
        self._player.set_rate(rate)
    def load(self, path):
        self.media = self._instance.media_new(path)
        self._player.set_media(self.media)
        #time.sleep(1)
        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self.SongFinished)
        events.event_attach(vlc.EventType.MediaPlayerPlaying, self.ePlaying)
        events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.poschanged)
        events.event_attach(vlc.EventType.MediaPlayerStopped, self.eStopped)
        events.event_attach(vlc.EventType.MediaPlayerPaused, self.ePaused)
        events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.poschanged)

        self._player.play()
        #    self._player.pause()
        print ("NEXT")
        #self._player.set_pause(1)
        #self._player.next_frame()
        #self._player.set_time(30000)
        #time.sleep(1)
        #self._player.pause()

    def play(self):
        self._player.play()

    def stop(self):
        self._player.stop()
    def pause(self):
        if self._player.is_playing():
            self._player.pause()

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    hd =  HyperDeckPlayer()
    _files = []
    _active_clip = None

    def findVideoMetada(self, pathToInputVideo):
        cmd = "ffprobe -v quiet -print_format json -show_streams"
        args = shlex.split(cmd)
        args.append(pathToInputVideo)
        # run the ffprobe process, decode stdout into utf-8 & convert to JSON
        ffprobeOutput = subprocess.check_output(args).decode('utf-8')
        ffprobeOutput = json.loads(ffprobeOutput)
    
        # prints all the metadata available:
        #import pprint
        #pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(ffprobeOutput)
    
        # for example, find height and width
        height = ffprobeOutput['streams'][0]['height']
        width = ffprobeOutput['streams'][0]['width']
        duration = ffprobeOutput['streams'][2]['duration_ts']
        fps = ffprobeOutput['streams'][0]['avg_frame_rate']
        print(width, height, duration, fps)
        return width, height, duration, fps

    def handle(self):
        while True:
            data = str(self.request.recv(1500), 'ascii')
            print(data)
            self.process(data)

    def list_media(self):
        self._files = os.listdir('videos')
        return self._files
    def process(self, data_recv):
        lines = data_recv.split('\n')
        data = lines[0]
        if 1==1:
            print (data)
            cur_thread = threading.current_thread()
            response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
            s = data.strip().split(":", 1)
            if s[0] == 'play':
                self.hd.play()
                for line in lines:
                    s = line.strip().split(':', 1)
                    if s[0] == 'speed':
                        rate = int(s[1].strip())
                        self.hd.set_rate(rate/100) 
                response = bytes("200 ok\n", 'ascii')
                #single clip: true
                #loop: false
                #speed: 100
            elif s[0] == 'stop':
                self.hd.pause()
                response = bytes("200 ok\n", 'ascii')

            elif s[0] == 'goto':
                s2 = s[1].strip().split(":", 1)
                if s2[0] == 'clip id':
                    if s2[1].strip()[:1] == '+':
                        self._active_clip += int(s2[1].strip()[1:])
                    elif s2[1].strip()[:1] == '-':
                        self._active_clip -= int(s2[1].strip()[1:])

                    else:
                        clipid = int(s2[1].strip())
                        self._active_clip = clipid-1
                    self.hd.load("videos/" + self._files[self._active_clip])
                    response = bytes("200 ok\n", 'ascii')
                else:
                    response = bytes("100 syntax error\n", 'ascii')
                goto: cl
            elif s[0] == 'clips get':
                out = "205 clips info:\n"
                fl = self.list_media()
                out += "clip count: " + str(len(fl)) + "\n"
                at = 0
                for f in self.list_media():
                    at += 1
                    (width, height, duration, fps) = self.findVideoMetada('videos/' + f)
                    fps_s = fps.split('/')
                    fps_out = int(fps_s[0]) / int(fps_s[1])
                    (h,m,s,fr) = self.hd.time_to_timecode(duration, fps_out)
                    tc = f'{h:02}:{m:02}:{s:02}:{fr:02}'
                    print(at, f,tc)
                    out += str(at) + ": " + f + " 01:00:00:00 " + tc + "\n" 
                out += "\r\n"
                response = bytes(out, 'ascii')
                print (response)
            elif s[0] == 'transport info':
                """208 transport info:↵
	
status: {“preview”, “stopped”, “play”, “forward”, “rewind”,
“jog”, “shuttle”,”record”}↵
speed: {Play speed between -1600 and 1600 %}↵
slot id: {Slot ID or “none”}↵
display timecode: {timecode}↵
timecode: {timecode}↵
clip id: {Clip ID or “none”}↵
video format: {Video format}↵
loop: {“true”, “false”}↵
↵""" # https://youtu.be/4CxXM_YlAqc?t=416
                if self.hd.is_playing():
                    state = 'play'
                else:
                    state = 'stopped'
                (h,m,s,f) = self.hd.time_to_timecode(self.hd.get_time(), self.hd.get_fps())
                tc = f'{h:02}:{m:02}:{s:02}:{f:02}'
                response = bytes("""208 transport info:
status: """ + state + """
speed: """ + str(self.hd.get_rate()) + """
slot id: none
display timecode: """ + tc + """
timecode: """ + tc + """
clip id: none
video format: 1080p30
loop: "false"

""", 'ascii')
            else :
                response = bytes("100 syntax error\n", 'ascii')
            self.request.sendall(response)

#        cur_thread = threading.current_thread()
#        response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
#        self.request.sendall(response)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Received: {}".format(response))

if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "", 9993
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    with server:
        ip, port = server.server_address

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)

        server_thread.join()
#        server.shutdown()