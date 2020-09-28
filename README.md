# Python HyperDeck Server

This is a prototyping repo at this moment.

2020-09-27 : I've created a new prototype version which will allow for additional features and easier integration of new functionnality.  It also tested with the Atem Mini and the Atem Software.  It run off an Raspberry Pi, but I haven't tested the audio yet (only did my testing from a computer monitor with no audio input).

2020-09-22 : This was tested ONLY with the BM Hyperdeck Python SDK Client you can download at : https://downloads.blackmagicdesign.com/Developer/HyperDeck/20191021-c99749/Blackmagic_HyperDeck_Developer_SDK_1.0.zip

To use this software, you put your video file in the videos folders (basic ascii with no space in file name... I haven't done any escaping at all yet), then just start python3 src/prototype_server.py 

You can now connect to your computer IP address to port 9993 which is the standard hyperdeck port

Required packages (for v2 prototype) :
Python3
python3-vlc
python3-aiohttp
python3-websockets
ffmpeg (for ffprobe)
videolan


New Additional packages
pip3 install pyudev
pip3 install psutil


Python PIP:
python-vlc can be installed using pip3 software
Install on Linux : # apt install python3 pip3
Install on Windows : 
Install on OSX : https://evansdianga.com/install-pip-osx/

