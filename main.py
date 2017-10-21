import aiohttp
from aiohttp import web
import vk
import json


def find_audio_messages(obj):
    doc_previews = map(
        lambda att: att['doc']['preview'],
        filter(lambda att: att['type'] == 'doc', obj.get('attachments', {}))
    )
    audio_msgs = map(
        lambda doc: doc['audio_msg'],
        filter(lambda doc: 'audio_msg' in doc, doc_previews)
    )

    urls = list(map(lambda audio: (audio['link_mp3'], audio['link_ogg']), audio_msgs))
    if 'fwd_messages' in obj:
        for msg in obj['fwd_messages']:
            urls += find_audio_messages(msg)

    return urls

async def process_message(request):
    body = await request.json()
    print(body)
    request_type = body['type']
    if request_type == 'confirmation':
        return web.Response(text=confirmation_key)
    elif request_type != 'message_new':
        return web.Response(text='ok')
    else:
        audio_messages = find_audio_messages(body['object'])
        user_id = body['object']['user_id']
        message_id = body['object']['id']

        session = vk.Session()
        api = vk.API(session, v='5.68')

        if not audio_messages:
            api.messages.send(access_token=access_token, user_id=user_id, message='Не вижу аудиосообщений &#128584;')
            return web.Response(text='ok')

        async with aiohttp.ClientSession() as session:
            messages = []
            api.messages.send(access_token=access_token,
                              user_id=user_id,
                              message='Обрабатываю сообщение, это может занять некоторое время...&#128164;')
            for (mp3, ogg) in audio_messages:
                async with session.post(server_host, json={'url_mp3': mp3, 'url_ogg': ogg, 'url': ogg}) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        api.messages.send(access_token=access_token,
                                          user_id=user_id,
                                          message='Ошибка при анализировании сообщения &#128586;\nПопробуйте позже!',
                                          forward_messages=[message_id])
                        return web.Response(text='ok')
                    else:
                        messages.append(response_text)

        api.messages.send(access_token=access_token,
                          user_id=user_id,
                          message='\n'.join(messages),
                          forward_messages=[message_id])

        return web.Response(text='ok')

with open('config/config.json', 'r') as f:
    config = json.load(f)
    app_host = config['app_host']
    app_port = config['app_port']
    server_host = config['server_host']
    confirmation_key = config['confirmation_key']
    access_token = config['access_token']

app = web.Application()
app.router.add_post('/', process_message)
web.run_app(app, host=app_host, port=app_port)
