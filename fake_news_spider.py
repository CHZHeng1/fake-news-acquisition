import requests
import re
import json
import time
import random
import datetime
import os
import sys
import logging


def logger_init(log_file_name='monitor',
                log_level=logging.DEBUG,
                log_dir='./logs/',
                only_file=False):
    """https://www.cnblogs.com/yyds/p/6901864.html logging详细说明"""
    # 指定路径
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, log_file_name + '_' + str(datetime.datetime.now())[:10] + '.txt')
    formatter = '[%(asctime)s] - %(levelname)s: %(message)s'
    if only_file:
        logging.basicConfig(filename=log_path,
                            level=log_level,
                            format=formatter,
                            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(level=log_level,
                            format=formatter,
                            datefmt='%Y-%m-%d %H:%M:%S',
                            handlers=[logging.FileHandler(log_path),  # 将日志消息发送到磁盘文件，默认情况下文件大小会无限增长
                                      logging.StreamHandler(sys.stdout)]  # 将日志消息发送到输出到Stream(控制台)
                            )


def string_to_int(string):
    """字符串转数值"""
    if isinstance(string, int):
        return string
    elif string.endswith('万+'):
        string = string[:-2] + '0000'
    elif string.endswith('万'):
        string = float(string[:-1]) * 10000
    elif string.endswith('亿'):
        string = float(string[:-1]) * 100000000
    return int(string)


def transform_time(created_at):
    """
    此函数用于转换时间格式
    created_at ： 微博原始时间格式 例：Mon Jul 04 23:39:54 +0800 2022
    return ：  2020-01-06 12:35:17
    """
    struct_time = time.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    released_time = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)
    return released_time


class WeiboSpider:
    def __init__(self, cookie, useragent):
        self.headers = {
                        'accept': 'application/json, text/plain, */*',
                        'accept-encoding': 'gzip, deflate, br',
                        'accept-language': 'zh-CN,zh;q=0.9',
                        'cookie': cookie,
                        'referer': 'https://weibo.com/2750621294/KAf1AFVPD',
                        'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-fetch-dest': 'empty',
                        'sec-fetch-mode': 'cors',
                        'sec-fetch-site': 'same-origin',
                        'traceparent': '00-5b5f81f871c6ff6846bf3a92f1d5efed-1ab32a39ad75711a-00',
                        'user-agent': useragent,
                        'x-requested-with': 'XMLHttpRequest',
                        'x-xsrf-token': '7yIZGS_IPx7EteZ6TT86YYAZ',
                        }

        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.logs_save_dir = os.path.join(self.project_dir, 'spider_logs')
        if not os.path.exists(self.logs_save_dir):
            os.makedirs(self.logs_save_dir)

        logger_init(log_file_name='monitor', log_level=logging.INFO,
                    log_dir=self.logs_save_dir, only_file=False)

    def get_weibomid(self, page_id):
        """
        从微博社区管理中心获取要采集微博数据的mid
        :param page_id: 页码, 从1开始
        """
        url = 'https://service.account.weibo.com/index?type=5&status=0&page=' + str(page_id)
        response = requests.get(url, headers=self.headers)
        response.encoding = 'utf-8'
        html = response.text
        pattern = r'<td>.*?<\\/td>\\n  <!--<td class=\\"W_spetxt\\">\d+<\\/td>-->\\n  ' \
                  r'<td>(.*?)<\\/td>\\n  <td>.*?<\\/td>\\n  <td>(.*?)<\\/td>\\n  <td>.*?<\\/td>\\n  <td>(.*?)<\\/td>' \
                  r'\\n\\t<\\/tr>'
        content_list = re.findall(pattern, html, re.DOTALL)  # re.DOTALL 跨行
        # print(len(content_list))
        assert len(content_list) == 20

        rids, uids, data_reported_list = [], [], []
        for content in content_list:
            rid_pattern = r'show\?rid=(.*?)\\" target=\\"_blank\\">'
            rid_list = re.findall(rid_pattern, content[0])
            rid = rid_list[0]  # 举报微博id

            uid_pattern = r'weibo.com\\/(.*?)\\"'
            uid_list = re.findall(uid_pattern, content[1])
            uid = uid_list[0]
            uid = uid.replace('u\\/', '')  # 被举报用户id

            data_reported = content[2]  # 举报时间

            rids.append(rid)
            uids.append(uid)
            data_reported_list.append(data_reported)

        mids = []
        rids_new, data_reported_list_new = [], []
        for ind, rid in enumerate(rids):
            rid_url = 'https://service.account.weibo.com/show?rid=' + rid
            # print(rid_url)
            try:
                rid_url_response = requests.get(rid_url, headers=self.headers)
                rid_url_response.encoding = 'utf-8'
                rid_html = rid_url_response.text
            except:
                logging.info(f'### 本日访问已达到上限: 第{page_id}页, 第{ind+1}条 {rid_url} ')
                return rids_new, mids, data_reported_list_new
            else:
                try:
                    rid_pattern = r'<a suda-uatrack=\\"key=tblog_service_account&value=original_text\\" target=\'_b' \
                                  r'lank\' href=\'http:\\/\\/weibo.com\\/(.*?)\\/(.*?)\'>\\u539f\\u6587<\\/a>'
                    get_rid_pattern = re.findall(rid_pattern, rid_html, re.DOTALL)  # re.DOTALL 跨行
                    #         print(mid_list)  # [('uid', 'mid')]
                    mid = get_rid_pattern[0][1]
                    mids.append(mid)
                    rids_new.append(rid)
                    data_reported_list_new.append(data_reported_list[ind])
                except:
                    logging.info(f'### {rid_url} 微博mid获取失败, 位置: 第{page_id}页, 第{ind+1}条')
                    continue
        return rids_new, mids, data_reported_list_new

    def get_longtext(self, mid):
        """此函数用于获取微博内容长文本"""
        url_long = 'https://weibo.com/ajax/statuses/longtext?id=' + str(mid)
        response_long = requests.get(url_long, headers=self.headers)
        response_long.encoding = 'utf-8'
        text_long = json.loads(response_long.text)
        # print(text_long)
        weibo_content = text_long['data']['longTextContent']  # 微博文本
        return weibo_content

    def get_weiboinfo(self, mid):
        """
            获取微博信息
            url格式: https://weibo.com/ajax/statuses/show?id=LzygzrXAx
        """
        url = 'https://weibo.com/ajax/statuses/show?id='+str(mid)
        logging.info(f'### 开始采集微博信息...')
        logging.info(f'### {url}')
        response = requests.get(url, headers=self.headers)
        response.encoding = 'utf-8'
        text_json = json.loads(response.text)

        m_id = text_json['mblogid']  # 微博id
        assert str(mid) == str(m_id)
        if text_json['isLongText']:
            try:
                logging.info(f'### {mid}正在获取长文本')
                weibo_content = self.get_longtext(mid)
            except:
                logging.info('### 长文本获取失败，将采集短文本')
                weibo_content = text_json['text_raw']  # 微博文本
        else:
            weibo_content = text_json['text_raw'] # 微博文本

        released_time = transform_time(text_json['created_at']) # 微博发布时间
        repost = int(text_json['reposts_count'])  # 转发数
        comment = int(text_json['comments_count'])  # 评论数
        like = int(text_json['attitudes_count'])  # 点赞数
        user_id = text_json['user']['id']  # 用户id

        # 获取图片名称
        try:
            pic_ids = text_json['pic_ids']
        except:
            pic_ids = []

        if pic_ids != []:
            image_url = []  # 图片链接
            for ind, pic_id in enumerate(pic_ids):
                pic_url = text_json['pic_infos'][pic_id]['original']['url']
                image_url.append(pic_url)
        else:
            image_url = ''
        try:
            video_url = text_json['page_info']['media_info']['stream_url']  # 视频链接
        except:
            video_url = ''

        print(f'### 微博id:{m_id}, 微博发布时间:{released_time}, 微博内容:{weibo_content}, 点赞数:{like}, 转发数:{repost}, '
              f'评论数:{comment}, 图片url:{image_url}, 视频url:{video_url}')
        logging.info('### 微博信息采集完毕！')
        return m_id, released_time, weibo_content, like, repost, comment, image_url, video_url, user_id

    def get_userinfo(self, u_id):
        """获取用户信息"""
        url = 'https://weibo.com/ajax/profile/info?uid=' + str(u_id)
        logging.info('### 开始采集用户信息...')
        logging.info(f'### {url}')
        response = requests.get(url, headers=self.headers)
        response.encoding = 'utf-8'
        try:
            dic = json.loads(response.text)
        except:
            logging.info(f'### 用户信息采集失败，用户id为：{u_id}')
        else:
            # 当try段代码能够正常执行，没有出现异常的情况下，会执行else段代码
            user_id = dic['data']['user']['id']  # 用户id
            user_name = dic['data']['user']['screen_name']  # 用户名
            verified = int(dic['data']['user']['verified'])  # 是否认证 1->True 0->False
            verified_type = dic['data']['user']['verified_type']  # 认证类型
            if verified:
                verified_reason = dic['data']['user']['verified_reason']  # 认证理由
            else:
                verified_reason = ' '
            follow_count = string_to_int(dic['data']['user']['friends_count'])  # 关注数
            followers_count = string_to_int(dic['data']['user']['followers_count'])  # 粉丝数
            weibo_num = string_to_int(dic['data']['user']['statuses_count'])  # 微博数量

            print(f'### 用户名:{user_name}, 用户发布微博数量:{weibo_num}, 关注数:{follow_count}, 粉丝数:{followers_count}, '
                  f'是否认证:{verified}(1表示已认证，0表示未认证)')
            logging.info('### 用户信息采集完毕！')
            return user_name, weibo_num, follow_count, followers_count, verified, verified_type, verified_reason

    def get_commentinfo(self, mid, uid, weibo_comments, max_id=0, freq=0, max_freq=2):
        """
        获取一级评论，一次采集一页 20条，设置了频次（freq），可按需调整采集评论数量
        :param mid: 微博id
        :param uid: 用户id
        :param weibo_comments: list 用于存储采集到的评论，由于函数递归调用，需定义在函数体外
        :param max_id: 获取下一个评论内容的id
        :param freq: 采集的频次
        :param max_freq: 采集的最大频次,采集评论数量为 20*(max_freq)
        """
        logging.info('### 正在采集评论信息...')
        url = 'https://weibo.com/ajax/statuses/buildComments?flow=0&is_reload=1&id=' + str(mid) + \
                '&is_show_bulletin=2&is_mix=0&max_id=' + str(max_id) + '&count=20&uid='+str(uid)

        response = requests.get(url, headers=self.headers)
        response.encoding = 'utf-8'
        jsondata = json.loads(response.text)

        max_id = jsondata['max_id']  # 获取下一页mid
        content = jsondata['data']  # 一页的评论内容 20条
        freq = freq + 1  # 记录采集评论的次数

        for index, ct in enumerate(content):
            comment_time = transform_time(ct['created_at'])  # 评论时间
            comment_text = ct['text_raw']  # 评论内容
            comment_userid = ct['user']['id']  # 评论人id
            comment_username = ct['user']['screen_name']  # 评论人名称
            weibo_comment_data = {'评论内容': comment_text, '评论时间': comment_time,
                                  '评论用户id': comment_userid, '评论用户名': comment_username}
            print(f'### {weibo_comment_data}')
            weibo_comments.append(weibo_comment_data)

        if max_id == 0:
            logging.info(f'### https://weibo.com/{uid}/{mid}微博所有评论数据采集完毕')
            return
        else:
            if freq < max_freq:
                try:
                    seconds = random.randint(5, 7)
                    # print(f'### {seconds}秒后开始采集下一页')
                    logging.info(f'### {seconds}秒后开始采集下一页')
                    time.sleep(seconds)
                    self.get_commentinfo(mid, uid, weibo_comments, max_id=max_id, freq=freq, max_freq=max_freq)
                except Exception as result:
                    logging.info(f'### Unknown Error: {result}')
                    return
            else:
                logging.info(f'### 达到设定评论采集页数频次上限:{max_freq}页,提前停止！')
                return


def data_process(spider, mids):
    """
    :param spider: 采集数据所需要的类
    :param mids: list 要进行采集的微博id 示例 ['InzJsiQ1k', ]
    """

    for index, mid in enumerate(mids):
        logging.info(f'### 正在采集第{index+1}条微博数据')
        # 获取微博信息
        try:
            m_id, released_time, weibo_content, like, repost, comment, image_url, video_url, user_id = \
                spider.get_weiboinfo(mid)

        except:
            logging.info(f'### 根据博主设置，此条微博内容无法访问。微博id: {mid}')
            continue

        else:
            # 获取用户信息
            user_name, weibo_num, follow_count, followers_count, verified, verified_type, verified_reason = \
                spider.get_userinfo(user_id)

            user_info = {'用户id': user_id, '用户名': user_name, '发布微博数': weibo_num, '关注数': follow_count,
                         '粉丝数': followers_count, '是否认证': verified, '认证类型': verified_type, '认证原因': verified_reason}

            # 获取评论
            weibo_comments = []
            try:
                spider.get_commentinfo(mid, user_id, weibo_comments, max_id=0, freq=0, max_freq=2)
            except KeyError:
                seconds = random.randint(15, 30)
                logging.info(f'### 评论获取失败, {seconds}秒后重试')
                time.sleep(seconds)
                spider.get_commentinfo(mid, user_id, weibo_comments, max_id=0, freq=0, max_freq=2)
            finally:
                weibo_data = {'微博id': m_id, '微博发布时间': released_time, '微博内容': weibo_content, '点赞数': like,
                              '转发数': repost, '评论数': comment, '图片url': image_url, '视频url': video_url,
                              '用户信息': user_info, '评论内容': weibo_comments}
                save_json(mid, weibo_data)
                logging.info(f'### 第{index+1}条微博数据已保存至本地。')


def data_process_auto(spider, rids, mids, data_reported_list):
    """
    :param spider: 采集数据所需要的类
    :param rids: list 用于获取mids 示例 ['K1CeJ6QJd7qse', ]
    :param mids: list 要进行采集的微博id 示例 ['InzJsiQ1k', ]
    :param data_reported_list: list 举报时间
    """
    for index, mid in enumerate(mids):
        logging.info(f'### 正在采集第{index+1}条微博数据')
        # 获取微博信息
        rid = rids[index]
        data_reported = data_reported_list[index]
        try:
            m_id, released_time, weibo_content, like, repost, comment, image_url, video_url, user_id = \
                spider.get_weiboinfo(mid)

        except:
            logging.info(f'### 根据博主设置，此条微博内容无法访问。微博id: {mid}')
            continue
        else:

            # 获取用户信息
            user_name, weibo_num, follow_count, followers_count, verified, verified_type, verified_reason = \
                spider.get_userinfo(user_id)

            user_info = {'用户id': user_id, '用户名': user_name, '发布微博数': weibo_num, '关注数': follow_count,
                         '粉丝数': followers_count, '是否认证': verified, '认证类型': verified_type, '认证原因': verified_reason}

            # 获取评论
            weibo_comments = []
            spider.get_commentinfo(mid, user_id, weibo_comments, max_id=0, freq=0, max_freq=2)

            weibo_data = {'微博社区id': rid, '举报时间': data_reported, '微博id': m_id, '微博发布时间': released_time,
                          '微博内容': weibo_content, '点赞数': like, '转发数': repost, '评论数': comment, '图片url': image_url,
                          '视频url': video_url, '用户信息': user_info, '评论内容': weibo_comments}
            save_json(mid, weibo_data)
            logging.info(f'### 第{index+1}条微博数据已保存至本地。')


# 读取txt文件
def read_txt(filepath):
    txt_list = [line.strip() for line in open(filepath, 'r', encoding='utf-8').readlines()]
    return txt_list


# 保存txt文件
def save_text(filename, content):
    outputs = open(f'{filename}.txt', 'a+', encoding='utf-8')  # w+：可读可写，文件不存在会创建，存在会覆盖 #a+：追加文件，文件不存在会创建，存在往下追加
    for index, line in enumerate(content):
        if index == len(content)-1:
            outputs.write(str(line)+'\n')
        else:
            outputs.write(str(line)+'\n')
    outputs.close()
    print('数据已保存到本地')


# 保存成json文件
def save_json(mid, content):
    now_time = datetime.datetime.now().strftime("%Y-%m-%d")  # "%m%d_%H%M%S"
    save_path = f'./虚假信息数据集/{now_time}/'
    # save_path = f'./非虚假信息数据集/{now_time}/'
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    # ./日期/mid.json
    with open(f'{save_path + mid}.json', 'w+', encoding='utf-8') as file_obj:
        file_obj.write(json.dumps(content, indent=2, separators=(',', ':'), ensure_ascii=False))
    print(f'{mid}.json 已保存到本地.')


if __name__ == '__main__':

    cookie = 'your cookie'

    useragent = 'your user-agent'

    spider = WeiboSpider(cookie, useragent)

    # 方式一
    # mids = read_txt('mids.txt')
    # # print(mids)
    # data_process(spider, mids)

    # 方式二
    pages = list(range(1, 3))  # 每日可采集10页
    for page in pages:
        logging.info(f'### 正在采集第{page}页微博数据')
        rids, mids, data_reported_list = spider.get_weibomid(page_id=page)
        # logging.info(f'### 微博社区id列表: {rids} \n### 微博id列表: {mids} \n### 举报时间列表: {data_reported_list}')
        if len(mids) == 0:
            logging.info(f'### 未获取到要采集的微博mid, 数据采集结束。')
            break
        else:
            s = random.randint(7, 12)
            logging.info(f'### 成功获取: {mids}')
            save_text('weibo_mids', mids)

            logging.info(f'### {s}秒后开始采集详细微博信息')
            time.sleep(s)
            data_process_auto(spider, rids, mids, data_reported_list)
            logging.info(f'### 第{page}页微博数据采集完毕。')





