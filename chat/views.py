import aiohttp_jinja2
from aiohttp_session import get_session
from aiohttp import web, MsgType
from auth.models import User
from chat.models import Message


class ChatList(web.View):
    @aiohttp_jinja2.template('chat/index.html')
    async def get(self):
        message = Message(self.request.db)
        messages = message.get_messages()
        return {'message': messages}


class WebSocket(web.View):
    async def get(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        session = await get_session(self.request)
        user = User(self.request.db, {'id': session.get('user')})
        login = await user.get_login()

        for _ws in self.request.app['websockets']:
            _ws.send_str('%s joined' % login)
        self.request.app['websockets'].append(ws)

        async for msg in ws:
            if msg.tp == MsgType.text:
                if msg.data == 'close':
                    await ws.close()
                else:
                    for _ws in self.request.app['websockets']:
                        _ws.send_str('(%s) %s' % (login, msg.data))
            elif msg.tp == MsgType.error:
                print('ws connection closed with exception %s' % ws.exception())

        self.request.app['websockets'].remove(ws)
        for _ws in self.request.app['websockets']:
            _ws.send_str('%s disconected' % login)
        print('websocket connection closed')

        return ws
