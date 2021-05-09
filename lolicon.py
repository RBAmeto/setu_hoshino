import io
import base64
import aiohttp
import aiocqhttp
import PIL.Image

API = 'https://api.lolicon.app/setu/'
APIKEY = ''


async def fetch_setu(keyword: str = ''):
    params = {'apikey': APIKEY, 'keyword': keyword}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(API, params=params) as resp:
            return await resp.json()


async def fetch_image(url: str):
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            return await resp.read()


async def get_image(url: str):
    im_bytes = await fetch_image(url)
    byte_stream = io.BytesIO(im_bytes)
    im = PIL.Image.open(byte_stream)
    if im.mode in ('RGBA', 'LA'):
        im_new = PIL.Image.new(im.mode[:-1], im.size)
        im_new.paste(im, im.split()[-1])
        im = im_new
    im_buffer = io.BytesIO()
    im.save(im_buffer, format='JPEG', quality=60)
    im_value = im_buffer.getvalue()
    im_base64 = base64.b64encode(im_value)
    return f'base64://{im_base64.decode("UTF-8")}'


async def get_reply(keyword):
    res = None
    try:
        res = await fetch_setu(keyword)
    except:
        return '获取涩图失败，无法链接api'
    if res['code'] == 0:
        cishu = res['quota']
        setu = res['data'][0]
        url = setu['url']
        title = setu['title']
        author = f'画师：{setu["author"]}'
        pid = f'pid: {setu["pid"]}'
        print(url)
        try:
            im_base64 = await get_image(url)
            img = aiocqhttp.message.MessageSegment.image(im_base64)
            return f'\n{cishu}\n{title}\n{author}\n{pid}{img}'
        except:
            return '获取涩图失败，无法下载图片'
    elif keyword and res['code'] == 404:
        return f'没有找到"{keyword}"的涩图，试试输入"涩图蛋花"吧~'
    else:
        return f'涩图接口错误：{res["msg"]}'
    return '获取涩图失败，未知的错误'

async def get_replyr18(keyword):
    res = None
    try:
        res = await fetch_r18setu(keyword)
    except:
        return '获取涩图失败，无法链接api'
    if res['code'] == 0:
        cishu = res['quota']
        setu = res['data'][0]
        url = setu['url']
        title = setu['title']
        author = f'画师：{setu["author"]}'
        pid = f'pid: {setu["pid"]}'
        print(url)
        try:
            im_base64 = await get_image(url)
            img = aiocqhttp.message.MessageSegment.image(im_base64)
            return f'\n{cishu}\n{title}\n{author}\n{pid}{img}'
        except:
            return '获取涩图失败，无法下载图片'
    elif keyword and res['code'] == 404:
        return f'没有找到"{keyword}"的涩图，试试输入"涩图蛋花"吧~'
    else:
        return f'涩图接口错误：{res["msg"]}'
    return '获取涩图失败，未知的错误'

async def fetch_r18setu(keyword: str = ''):
    params = {'apikey': APIKEY, 'keyword': keyword, 'r18': 1}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(API, params=params) as resp:
            return await resp.json()

if __name__ == '__main__':
    import asyncio

    async def main():
        print(await get_reply(''))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
else:
    import hoshino
    sv = hoshino.service.Service('涩图')

    @sv.on_rex(r'^来?一?[份点张]?[涩色瑟]图(.{0,10})$')
    async def send_setu(bot, event: hoshino.typing.CQEvent):
        keyword = event['match'].group(1).strip()
        reply = await get_reply(keyword)
        await bot.send(event, reply, at_sender=True)
        
    @sv.on_rex(r'^好康的(.{0,10})$')
    async def send_r18setu(bot, event: hoshino.typing.CQEvent):
        keyword = event['match'].group(1).strip()
        reply = await get_replyr18(keyword)
        await bot.send(event, reply, at_sender=True)
