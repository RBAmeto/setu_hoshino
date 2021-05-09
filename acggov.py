import os
import re
import time
import datetime
import random
import urllib
import urllib.request
import io
import base64
import aiohttp
import aiocqhttp
import PIL.Image
import PIL.ImageDraw
import hoshino
from hoshino import Service, aiorequests
from hoshino.config import NICKNAME

sv = Service('acggov', enable_on_default=True, help_='''ACGGOV涩图，多P时随机一张
setu #随机涩图
日涩图排行榜|日图排行榜|周涩图排行榜|周图排行榜|今月图排行榜|男性向涩图排行榜|男性向图排行榜|女性向涩图排行榜|女性向图排行榜 [数字] #查看排行榜的指定页
看日涩图|看日图|看周涩图|看周图|看月图|看男性向涩图|看男性向图|看女性向涩图|看女性向图 [数字] #查看对应排行榜中指定数字的图
sousetu 关键字 #p站搜索关键字图(没过滤质量很差''')


class AcgGov:

    @staticmethod
    def get_token():
        return hoshino.modules.acggov.config.ACG_GOV_API_KEY

    @staticmethod
    def get_url():
        return hoshino.modules.acggov.config.ACG_GOV_AMAZING_PIC_URL

    @staticmethod
    def get_path():
        return hoshino.modules.acggov.config.ACG_GOV_IMG_PATH

    @staticmethod
    def get_origin():
        return hoshino.modules.acggov.config.ACG_GOV_PIC_ORIGIN

    @staticmethod
    def get_admin():
        return hoshino.config.__bot__.SUPERUSERS

    @staticmethod
    def set_origin(boolean):
        hoshino.modules.acggov.config.ACG_GOV_PIC_ORIGIN = boolean
        return hoshino.modules.acggov.config.ACG_GOV_PIC_ORIGIN

async def fetch_image(url: str):
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            return await resp.read()


async def get_image(url: str):
    im_bytes = await fetch_image(url)
    im = PIL.Image.open(io.BytesIO(im_bytes))
    if im.mode != 'RGB':
        im = im.convert('RGB')
    width, height = im.size
    draw = PIL.ImageDraw.Draw(im)
    draw.point((random.randint(1, width), random.randint(1, height)), fill=(random.randint(0, 255),
			                                                                random.randint(0, 255),
			                                                                random.randint(0, 255)))
    im_buffer = io.BytesIO()
    im.save(im_buffer, format='JPEG', quality=60)
    im_value = im_buffer.getvalue()
    im_base64 = base64.b64encode(im_value)
    return f'base64://{im_base64.decode("UTF-8")}'

@sv.on_fullmatch({'setu'})
async def send_Amazing_Pic(bot, ev):
    try:
        robotId = ev['self_id']
        userId = ev['user_id']
        headers = {'token': AcgGov.get_token()}
        resp = await aiorequests.get(AcgGov.get_url(), headers=headers, timeout=10, stream=True)
        # 判断调用次数已超标
        if resp.status_code != 201:
            await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
            return
        res = await resp.json()
        illust = res['data']['illust']
        pageCount = res['data']['pageCount']
        originals = res['data']['originals']
        suffix = None
        r = None
        img = None
        resp1 = await aiorequests.get(f'https://api.acgmx.com/illusts/detail?illustId={illust}&reduction=true',
                                     headers=headers, timeout=10, stream=True)
        if resp1.status_code != 201:
            await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
            return
        res1 = await resp1.json()
        page_count = res1['data']['illust']['page_count']
        title = res1['data']['illust']['title']
        uri = None
        if page_count == 1:
            uri = res1['data']['illust']['meta_single_page']['original_image_url'].replace("https://i.pximg.net", "https://i.pixiv.cat")
        else:
            meta_pages = res1['data']['illust']['meta_pages']
            num = random.randint(1, len(meta_pages))
            uri = meta_pages[num-1]['image_urls']['original'].replace("https://i.pximg.net", "https://i.pixiv.cat")
        print(uri)
        im_base64 = await get_image(uri)
        setu = aiocqhttp.message.MessageSegment.image(im_base64)
        await bot.send(ev, f'[CQ:at,qq={userId}]{setu}\nid:{illust}\ntitle:{title}')
    except Exception as e:
            sv.logger.error(f'Error: {e}')


@sv.on_fullmatch({'修改涩图模式'})
async def change_type(bot, ev):
    try:
        userId = ev['user_id']
        # 判断是否是超级管理员
        if userId in AcgGov.get_admin():
            # 修改模式，如果是原图修改缩略图，反之亦然
            if AcgGov.get_origin():
                AcgGov.set_origin(False)
            else:
                AcgGov.set_origin(True)

            if AcgGov.get_origin():
                msg = '缩略图'
            else:
                msg = '高清图'

            await bot.send(ev, f'[CQ:at,qq={userId}]修改成功，当前模式为{msg}')
        else:
            # 拼接超级管理员
            message = f'[CQ:at,qq={userId}]您无权限，今命令只有'
            for i in AcgGov.get_admin():
                message += '[CQ:at,qq=' + str(i) + ']'

            await bot.send(ev, message + '可使用')
    except Exception as e:
        sv.logger.error(f'Error: {e}')


# 以下是读取pixiv的中转18xranking
@sv.on_rex(r'(本日涩图|本日图|本周涩图|本周图|本月图|男性向涩图|男性向图|女性向涩图|女性向图).*排行榜')
async def ranking(bot, ev):
    try:
        robotId = ev['self_id']
        userId = ev['user_id']
        # 每页显示的数量
        per_page = 10
        arg = str(ev.raw_message)
        rex1 = re.compile(r'本日涩图排行榜')
        rex2 = re.compile(r'本日图排行榜')
        rex3 = re.compile(r'本周涩图排行榜')
        rex4 = re.compile(r'本周图排行榜')
        rex5 = re.compile(r'本月图排行榜')
        rex6 = re.compile(r'男性向涩图排行榜')
        rex7 = re.compile(r'男性向图排行榜')
        rex8 = re.compile(r'女性向涩图排行榜')
        rex9 = re.compile(r'女性向图排行榜')
        if rex1.search(arg):
            mode = 'illust&mode=daily_r18'
            page = ev['raw_message'].replace("本日涩图排行榜", "").replace(" ", "")
        elif rex2.search(arg):
            mode = 'illust&mode=daily'
            page = ev['raw_message'].replace("本日图排行榜", "").replace(" ", "")
        elif rex3.search(arg):
            mode = 'illust&mode=weekly_r18'
            page = ev['raw_message'].replace("本周涩图排行榜", "").replace(" ", "")
        elif rex4.search(arg):
            mode = 'illust&mode=weekly'
            page = ev['raw_message'].replace("本周图排行榜", "").replace(" ", "")
        elif rex5.search(arg):
            mode = 'illust&mode=monthly'
            page = ev['raw_message'].replace("本月图排行榜", "").replace(" ", "")
        elif rex6.search(arg):
            mode = 'all&mode=male_r18'
            page = ev['raw_message'].replace("男性向涩图排行榜", "").replace(" ", "")
        elif rex7.search(arg):
            mode = 'all&mode=male'
            page = ev['raw_message'].replace("男性向图排行榜", "").replace(" ", "")
        elif rex8.search(arg):
            mode = 'all&mode=female_r18'
            page = ev['raw_message'].replace("女性向涩图排行榜", "").replace(" ", "")
        elif rex9.search(arg):
            mode = 'all&mode=female'
            page = ev['raw_message'].replace("女性向图排行榜", "").replace(" ", "")         
            
        # 判断是否是数字，不是则给默认值
        if not is_number(page):
            page = '1'
        headers = {'token': AcgGov.get_token()}
        t1 = '00:00'
        t2 = '12:01'
        nowt = datetime.datetime.now().strftime("%H:%M")
        if t1 < nowt < t2:
            nowtime = (datetime.datetime.now() + datetime.timedelta(days=-2)).strftime("%Y-%m-%d")            
        else:
            nowtime = (datetime.datetime.now() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")   

        resp = await aiorequests.get('https://api.acgmx.com/public/ranking?ranking_type=' + mode + '&date=' + nowtime + '&per_page=' + str(per_page) + '&page=' + page, headers=headers, timeout=10, stream=True)
        # 判断调用次数已超标
        if resp.status_code != 200:
            await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
            return
        res = await resp.json()

        data = res['response'][0]['works']
        pages = res['pagination']['pages']
        current = res['pagination']['current']
        num = int(page) * per_page - per_page + 1
        message = f'[CQ:at,qq={userId}]' + '\n'
        pathc = AcgGov.get_path()
        for i in data:
            pid1 = i['work']['id']
            pid = f'preview{pid1}'
            urld = i['work']['image_urls']['px_128x128'].replace("https://i.pximg.net", "https://i.pixiv.cat").replace("128x128", "150x150")
            im_base64 = await get_image(urld)
            yulan = aiocqhttp.message.MessageSegment.image(im_base64)
            message += f'{num}、' + i['work']['title'] + '-' + str(i['work']['user']['name']) + '\n' + f'{yulan}' + '\n'
            num += 1
        message += f'=======第{current}页，共{str(pages)}页======='
        tas_list=[]
        data = {
            "type": "node",
            "data": {
                    "name": str(NICKNAME[0]),
                    "uin": str(ev.self_id),
                    "content":message
                    }
            }
        tas_list.append(data)
        await bot.send_group_forward_msg(group_id=ev['group_id'], messages=tas_list)
        
    except Exception as e:
        sv.logger.error(f'Error: {e}')


@sv.on_rex(r'(看日涩图|看日图|看周涩图|看周图|看月图|看男性向涩图|看男性向图|看女性向涩图|看女性向图)')
async def look_ranking(bot, ev):
    try:
        robotId = ev['self_id']
        userId = ev['user_id']
        # 每页显示的数量
        per_page = 10
        
        arg = str(ev.raw_message)
        rex1 = re.compile(r'看日涩图')
        rex2 = re.compile(r'看日图')
        rex3 = re.compile(r'看周涩图')
        rex4 = re.compile(r'看周图')
        rex5 = re.compile(r'看月图')
        rex6 = re.compile(r'看男性向涩图')
        rex7 = re.compile(r'看男性向图')
        rex8 = re.compile(r'看女性向涩图')
        rex9 = re.compile(r'看女性向图')
        if rex1.search(arg):
            mode = 'illust&mode=daily_r18'
            number = ev['raw_message'].replace("看日涩图", "").replace(" ", "")
        elif rex2.search(arg):
            mode = 'illust&mode=daily'
            number = ev['raw_message'].replace("看日图", "").replace(" ", "")
        elif rex3.search(arg):
            mode = 'illust&mode=weekly_r18'
            number = ev['raw_message'].replace("看周涩图", "").replace(" ", "")
        elif rex4.search(arg):
            mode = 'illust&mode=weekly'
            number = ev['raw_message'].replace("看周图", "").replace(" ", "")
        elif rex5.search(arg):
            mode = 'illust&mode=monthly'
            number = ev['raw_message'].replace("本月图排行榜", "").replace(" ", "")
        elif rex6.search(arg):
            mode = 'all&mode=male_r18'
            number = ev['raw_message'].replace("看男性向涩图", "").replace(" ", "")
        elif rex7.search(arg):
            mode = 'all&mode=male'
            number = ev['raw_message'].replace("看男性向图", "").replace(" ", "")
        elif rex8.search(arg):
            mode = 'all&mode=female_r18'
            number = ev['raw_message'].replace("看女性向涩图", "").replace(" ", "")
        elif rex9.search(arg):
            mode = 'all&mode=female'
            number = ev['raw_message'].replace("看女性向图", "").replace(" ", "")
        # 判断是否是数字，不是则给默认值
        if not is_number(number):
            number = '1'

        # 取余
        if int(number) % per_page == 0:
            page = int(number) / per_page
            number = per_page - 1
        else:
            page1 = int(number) // per_page
            numbers = int(number) % per_page
            number = numbers - 1
            page = page1 + 1


        headers = {'token': AcgGov.get_token()}
        t1 = '00:00'
        t2 = '12:01'
        nowt = datetime.datetime.now().strftime("%H:%M")
        if t1 < nowt < t2:
            nowtime = (datetime.datetime.now() + datetime.timedelta(days=-2)).strftime("%Y-%m-%d")            
        else:
            nowtime = (datetime.datetime.now() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")   

        resp = await aiorequests.get('https://api.acgmx.com/public/ranking?ranking_type=' + mode + '&date=' + nowtime + '&per_page=' + str(per_page) + '&page=' + str(page), headers=headers, timeout=10, stream=True)
        # 判断调用次数已超标
        if resp.status_code != 200:
            await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
            return
        res = await resp.json()

        # 访问详细接口
        illust = res['response'][0]['works'][int(number)]['work']['id']
        title = res['response'][0]['works'][int(number)]['work']['title']
        author = res['response'][0]['works'][int(number)]['work']['user']['name']
        resp = await aiorequests.get(f'https://api.acgmx.com/illusts/detail?illustId={illust}&reduction=true',
                                     headers=headers, timeout=10, stream=True)

        if resp.status_code != 201:
            await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
            return
        res = await resp.json()
        page_count = res['data']['illust']['page_count']

        uri = None
        if page_count == 1:
            uri = res['data']['illust']['meta_single_page']['original_image_url'].replace("https://i.pximg.net", "https://i.pixiv.cat")
        else:
            meta_pages = res['data']['illust']['meta_pages']
            num = random.randint(1, len(meta_pages))
            uri = meta_pages[num-1]['image_urls']['original'].replace("https://i.pximg.net", "https://i.pixiv.cat")
        print(uri)
        im_base64 = await get_image(uri)
        setu = aiocqhttp.message.MessageSegment.image(im_base64)
        await bot.send(ev, f'[CQ:at,qq={userId}]{setu}\nid:{illust}\ntitle:{title}\n画师:{author}')
    except Exception as e:
        sv.logger.error(f'Error: {e}')



@sv.on_prefix("pid查图")
async def pidchatu(bot, ev):
    try:
        robotId = ev['self_id']
        userId = ev['user_id']
        text1 = ev['raw_message'].replace("pid查图", "").replace(" ", "")
        illust = text1.strip()
        headers = {'token': AcgGov.get_token()}
        if illust:
            resp1 = await aiorequests.get(f'https://api.acgmx.com/illusts/detail?illustId={illust}&reduction=true', headers=headers, timeout=10, stream=True)

            if resp1.status_code != 201:
                await bot.send(ev, f'[CQ:at,qq={userId}]' + '您的请求频率过快，请一分钟后再试')
                return
            res1 = await resp1.json()
            page_count = res1['data']['illust']['page_count']
            title = res1['data']['illust']['title']
            author = res1['data']['illust']['user']['name']

            uri = None
            if page_count == 1:
                uri = res1['data']['illust']['meta_single_page']['original_image_url'].replace("https://i.pximg.net", "https://i.pixiv.cat")
            else:
                meta_pages = res1['data']['illust']['meta_pages']
                num = random.randint(1, len(meta_pages))
                uri = meta_pages[num-1]['image_urls']['original'].replace("https://i.pximg.net", "https://i.pixiv.cat")
            print(uri)
            im_base64 = await get_image(uri)
            setu = aiocqhttp.message.MessageSegment.image(im_base64)
            await bot.send(ev, f'[CQ:at,qq={userId}]{setu}\nid:{illust}\ntitle:{title}\n画师:{author}')
    except Exception as e:
            sv.logger.error(f'Error: {e}')

@sv.on_prefix("sousetu")
async def sosetu(bot, ev):
        robotId = ev['self_id']
        userId = ev['user_id']
        text1 = ev['raw_message'].replace("sousetu", "")
        text = text1.strip()
        if text:
            headers = {'token': AcgGov.get_token()}
            urz = f'https://api.acgmx.com/public/search?q={text}&offset=0'
            resp = await aiorequests.get(urz, headers=headers, timeout=10, stream=True)
            res = await resp.json()
            resz = res['illusts']
            numz = random.randint(1,len(resz))
            ress = res['illusts'][numz-1]
            illust = ress['id']
            title =  ress['title']
            author = ress['user']['name']
            page_count = ress['page_count']
            uri = None
            if page_count == 1:
                uri = ress['meta_single_page']['original_image_url'].replace("https://i.pximg.net", "https://i.pixiv.cat")
            else:
                meta_pages = ress['meta_pages']
                num = random.randint(1, len(meta_pages))
                uri = meta_pages[num-1]['image_urls']['original'].replace("https://i.pximg.net", "https://i.pixiv.cat")
            print(uri)
            im_base64 = await get_image(uri)
            setu = aiocqhttp.message.MessageSegment.image(im_base64)
            await bot.send(ev, f'[CQ:at,qq={userId}]{setu}\nid:{illust}\ntitle:{title}\n画师:{author}')
        else:
            await bot.send(ev, f'搜图姬待命中...')
        
def is_number(num):
    """
    判断是否为数字
    :param num:
    :return:
    """
    pattern = re.compile(r'^[-+]?[-0-9]\d*\.\d*|[-+]?\.?[0-9]\d*$')
    result = pattern.match(str(num))
    if result:
        return True
    else:
        return False
