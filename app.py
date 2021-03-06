import websockets
from websockets.http import read_line
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None
    async def handler(self):
        try:
            #request_line, headers = await websockets.http.read_message(self.reader)
            request_line = await read_line(self.reader)
            print("received a message request: {}".format(request_line))
            
            method, path, version = request_line.split(b" ", 2)
            print("split message into method:{} path:{}  and version:{}".format(method, path, version))
            #method, path, version = request_line[:-2].decode().split(None, 2)
            
            
            #path, headers = await read_request(self.reader)
            #method, path, version = request_line[:-2].decode().split(None, 2)
            #method, path, version = request_line[:-2].split(None, 2)
            #websockets.accept()
        except Exception as e:
            print("Got exception in the first try of handler".format(e.args))
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            #self.reader.feed_data(bytes(request_line))
            #self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))
            print("Special Hacking would have taken place")
            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print("Got exception during http_handler method".format(e))
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try:

            googleRequest = self.reader._buffer.decode('utf-8')
            googleRequestJson = json.loads(googleRequest)

            #{"location": "living", "state": "on", "device": "lights"}
            if 'what' in googleRequestJson['result']['resolvedQuery']:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = '?'
            else:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = 'cmd'
            # send command to ESP over websocket
            if self.rwebsocket== None:
                print("Device is not connected!")
                return
            await self.rwebsocket.send(json.dumps(ESPparameters))

            #wait for response and send it back to API.ai as is
            self.rddata = await self.rwebsocket.recv()
            #{"speech": "It is working", "displayText": "It is working"}
            print("Received rddata {}".format(self.rddata))
            state = json.loads(self.rddata)['state']
            self.rddata = '{"speech": "It is turned '+state+'", "displayText": "It is turned '+state+'"}'

            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: text/json',
                '',
                ''+self.rddata+'',
            ])
            print("Response would look like this {}".format(response))
        except Exception as e:
            print("Exception in the first try of http_handler {}".format(e))
        self.writer.write(response.encode())

def updateData(data):
    print("UpdateData : {}".format(data))
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("")


print("Version of websockets {}".format(websockets.__version__))
        
port = int(os.getenv('PORT', 5687))
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
