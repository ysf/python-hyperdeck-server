#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pip3 install websockets
# pip3 install aiohttp
import asyncio

import websockets

import aiohttp
import async_timeout
from aiohttp import web

from hdplayer import HyperDeckPlayer

import os
import shlex
import subprocess
import json

import re

class HyperDeckInterface:
    hd =  HyperDeckPlayer()
    _files = None
    _active_clip = None

    def ActiveClip(self):
        if self._active_clip:
            return str(self._active_clip)
        else:
            return 'none'

    def buildSlotInfo(self, slot_id):
        if slot_id:
            out = [
                "slot id: " + str(slot_id),
                "status: mounted",
                "volume name: test",
                "recording time: 0",
                "video format: 1080p30"
                ]
            return out
        return None

    def get_media(self, clip_id):
        return self._files[clip_id-1]

    def list_media(self):
        if self._files == None:
            self._files = os.listdir('videos')

        return self._files
    
    def load_clip(self, clip_id):
        self.hd.load("videos/" + self.get_media(clip_id))
        self._active_clip = clip_id

    def buildRemote(self):
        out = [
                "enabled: true",
                "override: false"
                ]
        return out

    def buildTransportInfo(self):
        if self.hd.is_playing():
            state = 'play'
        else:
            state = 'stopped'
        rate = int(self.hd.get_rate())
        if rate == 0:
            rate = 1;
        speed = str(int(self.hd.get_rate() * 100))
        (h,m,s,f) = self.hd.time_to_timecode(self.hd.get_time(), self.hd.get_fps())
        tc = f'{h:02}:{m:02}:{s:02}:{f:02}'
        out = [
                'status: ' + state,
                "speed: " + speed,
                "slot id: 1",
                "display timecode: " + tc,
                "timecode: " + tc,
                "clip id: " + self.ActiveClip(),
                "video format: 1080p30",
                "loop: false"
                ]
        return out
    def ffprobeFind(self, data, field):
        for item in data['streams']:
            if field in item:
                return item[field]

    def findClipMetadata(self, clip_id):
            return self.findVideoMetada("videos/" + self.get_media(clip_id))

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
        print(ffprobeOutput)
        height = ffprobeOutput['streams'][0]['height']
        width = ffprobeOutput['streams'][0]['width']
        duration = self.ffprobeFind(ffprobeOutput, 'duration_ts')
        fps = ffprobeOutput['streams'][0]['avg_frame_rate']
        #print(width, height, duration, fps)
        return width, height, duration, fps


async def ws_handler(websocket, path):
    while True:
        try:
            name = await websocket.recv()
            print(f"< {name}")

            greeting = f"Hello {name}!"

            await websocket.send(greeting)
            print(f"> {greeting}")
        except websockets.exceptions.ConnectionClosed:
            print(f'{websocket.remote_address} lost connection')
            return

# HTTP:
async def index_handle(request):
    return web.FileResponse('html/index.html')
    #name = request.match_info.get('name', "Anonymous")
    #text = "Hello, " + name
    return web.Response(text=text)

async def send(writer, arr):
    out = ""
    for item in arr:
        out += item + "\r\n"

    out += "\r\n"
    response = bytes(out, 'ascii')
    writer.write(response)
    await writer.drain()

# HyperDeck Server
class HDClient:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
    def genResponse(self, response):
        out = ""
        qty = 0
        for item in response:
            if isinstance(item, list):
                for subitem in item:
                    out += subitem + "\r\n"
                    qty += 1
            else:
                out += item + "\r\n"
                qty += 1
        if qty > 1:
            out += "\r\n"
        return out

    async def send(self, msg):
        data = self.genResponse(msg)
        response = bytes(data, 'ascii')
        self.writer.write(response)
        await self.writer.drain()

class HDServer:
    hdi = HyperDeckInterface()

    def __init__(self):
        self._clients = set()

    def parseArg(self, arg):
        return re.findall('([a-zA-Z][^:]+): ([^ ]+)', arg)
    def parseArgGet(self, params, field):
        if params:
            for arg in params:
                (param, val) = arg
                if param == field:
                    return val
        return None

    def parseLineGet(self, lines, field):
        for line in lines:
            s = line.strip().split(':', 1)
            if s[0] == field:
                return s[1].strip()
        return None

    def parseGet(self, args, lines, field):
        res = self.parseArgGet(args, field)
        if not res:
            res = self.parseLineGet(lines, field)
        print("XXXXXX", field, res)
        return res

    async def new_conn(self, reader, writer):
        client = HDClient(reader, writer)
        self._clients.add(client)

        await client.send([
                    "500 connection info:",
                    "protocol version: 1.6",
                    "model: Python Hyperdeck Server"
                    ])

        while not reader.at_eof() and not writer.is_closing():
            response = ["100 syntax error"]
            data = await reader.read(1500)
            message = str(data, 'ascii')
            addr = writer.get_extra_info('peername')

            print(f"Received {message!r} from {addr!r}")

            lines = message.split('\n')
            data = lines[0]
            s = data.strip().split(":", 1)
            cmd = s[0]
            if len(s) > 1 and s[1]:
                params = self.parseArg(s[1].strip())
            else:
                params = None

            if cmd == 'play':
                self.hdi.hd.play()
                rate = self.parseGet(params, lines, 'speed')
                if rate:
                    rate = int(rate)
                    if rate == 0:
                        self.hdi.hd.pause()
                    self.hdi.hd.set_rate(rate/100)
                    response = ["200 ok"]
            elif cmd == 'stop':
                self.hdi.hd.pause()
                response = ["200 ok"]
            elif cmd == 'goto':
                clip_id = self.parseGet(params, lines, 'clip id')
                if clip_id:
                    if clip_id[:1] == '+':
                        clip_id = self.hdi.hd.ActiveClip() + int(val[1:])
                    elif clip_id[:1] == '-':
                        clip_id = self.hdi.hd.ActiveClip() - int(val[1:])
                    else:
                        clip_id = int(clip_id)
                    self.hdi.load_clip(clip_id)
                    response = ["200 ok"]
                else:
                    response = ["100 syntax error"]
            elif cmd == 'slot info':
                slot_id = self.parseGet(params, lines, 'slot id')
                if slot_id:
                    response = [
                                "202 slot info:",
                                self.hdi.buildSlotInfo(int(slot_id))
                                ]
            elif cmd == 'clips count':
                fl = self.hd.list_media()
                response = [
                        "214 clips count:",
                        "clip count: " + str(len(fl))
                        ]
            elif cmd == 'clips get':
                clip_id = self.parseGet(params, lines, 'clip id')
                response = [ 
                            "205 clips info:"
                            ]
                fl = self.hdi.list_media()
                at = 1

                if clip_id:
                    clip_id = int(clip_id)
                    fl = [fl[clip_id-1]]
                    at = clip_id
                else:
                    response.append("clip count: " + str(len(fl)))
                for f in fl:
                    (width, height, duration, fps) = self.hdi.findClipMetadata(at)
                    fps_s = fps.split('/')
                    fps_out = int(fps_s[0]) / int(fps_s[1])
                    (h,m,s,fr) = self.hdi.hd.time_to_timecode(duration, fps_out)
                    tc = f'{h:02}:{m:02}:{s:02}:{fr:02}'
                    #f = 'video' + str(at) + '.mp4'
                    response.append(str(at) + ":  " + f + " 00:00:00:00 " + tc)
                    at += 1
            elif cmd == 'remote':
                response = [
                    "210 remote info:",
                    self.hdi.buildRemote()
                    ]
            elif cmd == 'transport info':
                response = [
                        "208 transport info:",
                        self.hdi.buildTransportInfo()
                        ]
            await client.send(response)
            print(f"Send: {response!r}")

        print("Close the connection")
        writer.close()
        self._clients.remove(client)

async def serve():                                                                                           
    # Telnet
    hds = HDServer()
    ts = await asyncio.start_server( hds.new_conn, '127.0.0.1', 9993)
  
    addr = ts.sockets[0].getsockname()
    print(f'Serving on {addr}')

    
    #async with ts:
    #    await ts.serve_forever()
        #async with server:
    #await ts.wait_closed()
    #    serve_forever()
    
    #http
    app = aiohttp.web.Application()
    # index, loaded for all application uls.
    app.router.add_get('/', index_handle)
    app.router.add_static('/videos/', path='videos/', name='static')
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, 'localhost', '8082')
    await site.start()

    #ws
    wsserver = await websockets.serve(ws_handler, 'localhost', 8765)
    await wsserver.wait_closed()



asyncio.run(serve())
#asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()