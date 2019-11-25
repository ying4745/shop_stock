import re
import time
import json
import requests

from selenium import webdriver
from bs4 import BeautifulSoup

from spider import sp_config
from spider.auto_follow import af_config


class MyShopFuns():

    def __init__(self):
        # self.websocket = websocket

        self.name = sp_config.MY_USERNAME
        self.password = sp_config.MY_PASSWORD

        self.login_url = af_config.MY_LOGIN_URL

        self.following_count_url = af_config.MY_FOLLOWING_COUNT_URL
        self.following_list_url = af_config.MY_FOLLOWING_LIST_URL

        self.followers_list_url = af_config.MY_FOLLOWERS_LIST_URL

        self.follow_url = af_config.MY_FOLLOW_URL
        self.unfollow_url = af_config.MY_UNFOLLOW_URL

        self.headers_referer = af_config.MY_HEADERS_REFERER

        self.cookies_path = af_config.MY_COOKIES_SAVE
        self.cookies = get_cookies_from_file(self.cookies_path)

        self.headers = af_config.HEADERS
        self.headers.update({'cookie': self.cookies})

        self.login_num = 1
        self.country = '马来西亚'

    def login(self):
        """登录获取cookies"""
        # 手机模式
        # mobile_emulation = {"deviceName": "iPhone X"}
        # options = Options()
        # options.add_experimental_option("mobileEmulation", mobile_emulation)
        # driver = webdriver.Chrome(chrome_options=options)

        driver = webdriver.Chrome()
        driver.implicitly_wait(8)
        driver.get(self.login_url)

        time.sleep(4)
        # 选择语言
        try:
            driver.find_element_by_xpath('//*[@id="modal"]/div[1]/div[1]/div/div[3]/button[1]').click()
        except:
            pass
        # 关闭广告
        driver.find_element_by_xpath('//*[@id="modal"]/div/div/div[2]/div').click()
        time.sleep(1)
        # 点击登陆
        driver.find_element_by_xpath('//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[5]').click()
        # 输入账户密码
        driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[2]/input').send_keys(
            self.name)
        time.sleep(2)
        driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[3]/input').send_keys(
            self.password)
        time.sleep(2)
        driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[2]/button[2]').click()

        time.sleep(2)
        try:
            user = driver.find_element_by_xpath(
                '//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[3]/div/div/div[2]').text
        except:
            user = ''
        if user not in ['musesworld.my', 'musesworld.ph', 'musesbaby.th', 'musesbaby.id']:
            return False

        # print(driver.get_cookies())
        self.cookies = ''
        for cook in driver.get_cookies():
            self.cookies += cook['name'] + '=' + cook['value'] + '; '
        # 保存cookies到文件中
        # print(cookies)
        save_cookies_to_file(self.cookies_path, self.cookies)
        self.headers.update({'cookie': self.cookies})

        driver.quit()
        return True

    def following_count(self):
        """返回店铺关注中的人数"""
        if not self.cookies:
            print('无cookies')
            is_login = self.login()
            if not is_login:
                return ''

        response = requests.get(self.following_count_url, headers=self.headers)

        if response.status_code == 200:
            try:
                res = json.loads(response.text)
            except:
                print('反序列化信息失败！')
                return ''
            # print(res)
            return res['users'][0]['following_count']
        else:
            print('请求失败！')
            return ''

    def batch_unfollow(self, unfollow_num):
        """批量取关操作，从最早关注开始取关"""

        following_num = self.following_count()
        # print('关注人数 ', following_num)
        unfollow_num = int(unfollow_num)
        if not following_num:
            # print('关注人数查询失败')
            return "关注人数查询失败"

        following_num = int(following_num)
        if unfollow_num > following_num:
            # msg = '当前站点：{}，关注人数只有：{} 人'.format(self.country, following_num)
            # print(msg)
            unfollow_num = following_num

        num = 1
        while num <= unfollow_num:
            # 如果偏移量 起始值为0 则已经取完关注中的人
            if following_num == 0:
                return '没有关注中的人'
            # 偏移量 每次偏移20 如果总数小于20 则从零开始
            following_num -= 20
            if following_num <= 0:
                following_num = 0
            url = self.following_list_url.format(following_num)
            response = requests.get(url, headers=self.headers)
            # print(response.status_code)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')

                result_ele = soup.select('li[class="clickable_area middle-centered-div"]')
                if not result_ele:
                    print(response.text)
                    return "返回结果中没找到想要的元素"

                for user_ele in result_ele:
                    user_shopid = user_ele.attrs['data-follower-shop-id']
                    # print(user_shopid)
                    # is_follow = user_ele.select('.btn-follow')[0].get_text().strip()
                    follow_msg = self.follow(user_shopid, 'unfollow')

                    if follow_msg == 'error_not_login' and self.login_num == 1:
                        is_login = self.login()
                        if is_login:
                            self.batch_unfollow(unfollow_num)
                            self.login_num += 1
                        return '重新登陆失败'
                    elif follow_msg != '取关成功':
                        return '错误：{}， (当前关注：{}, 已取关 {} 人)'.format(follow_msg, following_num, num - 1)

                    num += 1
                    if num > unfollow_num:
                        return '当前关注：{}, 已取关 {} 人'.format(following_num, num - 1)
            else:
                return '请求失败'

    def batch_follow(self, seller_id, follow_num):
        """批量关注操作，条件：店铺ID、需要关注的人数"""

        follow_num = int(follow_num)
        num = 1
        # 偏移 从0开始
        off_num = 0
        while num <= follow_num:
            url = self.followers_list_url.format(seller_id, off_num)

            response = requests.get(url, headers=self.headers)

            # print(response.status_code)
            # print(response.text)
            if response.status_code == 200:
                # 请求返回的不是粉丝列表 则跳出 结束程序
                if len(response.text) < 100:
                    return '请求返回的不是粉丝列表（或已取完粉丝）'

                soup = BeautifulSoup(response.text, 'lxml')
                result_ele = soup.select('li[class="clickable_area middle-centered-div"]')
                if not result_ele:
                    return '返回结果中没找到想要的元素'

                for user_ele in result_ele:
                    user_shopid = user_ele.attrs['data-follower-shop-id']
                    # 网页中有可能只有一个名字，则user_name元素可能找不到
                    try:
                        user_name = user_ele.select('.down a')[0].get_text().strip()
                    except:
                        user_name = 'un.xx'

                    # 如果名字以.my|.ph|.id|.th|.xx 结尾  则跳过该用户
                    if re.match('^.*(?:\.(ph|my|th|id|xx))$', user_name):
                        # print(user_name, '跳过该用户')
                        continue

                    is_follow = user_ele.select('.btn-follow')[0].get_text().strip()
                    if is_follow in ['Following', 'Mengikuti', 'กำลังติดตาม']:
                        # print(user_name, '已关注该用户')
                        continue
                    elif is_follow in ['+ Follow', '+ Ikuti', '+ ติดตาม']:
                        # print(num, user_name, self.follow(user_shopid))
                        follow_msg = self.follow(user_shopid)

                        if follow_msg == 'error_not_login' and self.login_num == 1:
                            is_login = self.login()
                            if is_login:
                                self.batch_follow(seller_id, follow_num)
                                self.login_num += 1
                            return '重新登陆失败'
                        elif follow_msg != '关注成功':
                            return '错误：{}， < 已关注 {} 人 >'.format(follow_msg, num - 1)

                        num += 1
                        if num > follow_num:
                            return '已关注 {} 人'.format(num - 1)
                        time.sleep(0.2)
                    else:
                        # print(is_follow)
                        return '关注信息错误：{}，< 已关注 {} 人 >'.format(is_follow, num - 1)

                off_num += 20
            else:
                return '请求失败'

    def follow(self, shopid, f_type='follow'):
        # 关注和取关
        if f_type == 'unfollow':
            url = self.unfollow_url.format(shopid)
            s_msg = '取关成功'
        else:
            url = self.follow_url.format(shopid)
            s_msg = '关注成功'

        headers = {'referer': self.headers_referer}
        headers.update(self.headers)

        data = {'csrfmiddlewaretoken': get_csrftoken(self.cookies)}

        response = requests.post(url, headers=headers, data=data)

        # print(response.text)
        if response.status_code == 200:
            try:
                e = json.loads(response.text)
            except:
                print(response.text)
                return '反序列化信息失败!'
            if 'success' in e:
                return s_msg if e['success'] else '操作请求失败!'
            elif 'error' in e:
                return e['error']
            else:
                return '操作请求失败!'
        else:
            # print(response.status_code)
            return '关注请求失败!'


class PhShopFuns(MyShopFuns):

    def __init__(self):
        # self.websocket = websocket

        self.name = sp_config.PH_USERNAME
        self.password = sp_config.PH_PASSWORD

        self.login_url = af_config.PH_LOGIN_URL

        self.following_count_url = af_config.PH_FOLLOWING_COUNT_URL
        self.following_list_url = af_config.PH_FOLLOWING_LIST_URL

        self.followers_list_url = af_config.PH_FOLLOWERS_LIST_URL

        self.follow_url = af_config.PH_FOLLOW_URL
        self.unfollow_url = af_config.PH_UNFOLLOW_URL

        self.headers_referer = af_config.PH_HEADERS_REFERER

        self.cookies_path = af_config.PH_COOKIES_SAVE
        self.cookies = get_cookies_from_file(self.cookies_path)

        self.headers = af_config.HEADERS
        self.headers.update({'cookie': self.cookies})

        self.login_num = 1
        self.country = '菲律宾'


class ThShopFuns(MyShopFuns):

    def __init__(self):
        # self.websocket = websocket

        self.name = sp_config.TH_USERNAME
        self.password = sp_config.TH_PASSWORD

        self.login_url = af_config.TH_LOGIN_URL

        self.following_count_url = af_config.TH_FOLLOWING_COUNT_URL
        self.following_list_url = af_config.TH_FOLLOWING_LIST_URL

        self.followers_list_url = af_config.TH_FOLLOWERS_LIST_URL

        self.follow_url = af_config.TH_FOLLOW_URL
        self.unfollow_url = af_config.TH_UNFOLLOW_URL

        self.headers_referer = af_config.TH_HEADERS_REFERER

        self.cookies_path = af_config.TH_COOKIES_SAVE
        self.cookies = get_cookies_from_file(self.cookies_path)

        self.headers = af_config.HEADERS
        self.headers.update({'cookie': self.cookies})

        self.login_num = 1
        self.country = '泰国'


class IdShopFuns(MyShopFuns):

    def __init__(self):
        # self.websocket = websocket

        self.name = sp_config.ID_USERNAME
        self.password = sp_config.ID_PASSWORD

        self.login_url = af_config.ID_LOGIN_URL

        self.following_count_url = af_config.ID_FOLLOWING_COUNT_URL
        self.following_list_url = af_config.ID_FOLLOWING_LIST_URL

        self.followers_list_url = af_config.ID_FOLLOWERS_LIST_URL

        self.follow_url = af_config.ID_FOLLOW_URL
        self.unfollow_url = af_config.ID_UNFOLLOW_URL

        self.headers_referer = af_config.ID_HEADERS_REFERER

        self.cookies_path = af_config.ID_COOKIES_SAVE
        self.cookies = get_cookies_from_file(self.cookies_path)

        self.headers = af_config.HEADERS
        self.headers.update({'cookie': self.cookies})

        self.login_num = 1
        self.country = '印尼'


def save_cookies_to_file(filename, cookies):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(cookies)


def get_cookies_from_file(filename):
    try:
        with open(filename, encoding='utf-8') as f:
            cookies = f.read()
    except:
        return ''
    return cookies


def get_csrftoken(cookies):
    for cook in cookies.split('; '):
        if cook.split('=')[0] == 'csrftoken':
            return cook.split('=')[1]


country_shop_dict = {
    'MYR': MyShopFuns,
    'PHP': PhShopFuns,
    'THB': ThShopFuns,
    'IDR': IdShopFuns
}

# websocket 通讯版
# class MyShopFuns():
#
#     def __init__(self, websocket):
#         self.websocket = websocket
#
#         self.name = sp_config.MY_USERNAME
#         self.password = sp_config.MY_PASSWORD
#
#         self.login_url = af_config.MY_LOGIN_URL
#
#         self.following_count_url = af_config.MY_FOLLOWING_COUNT_URL
#         self.following_list_url = af_config.MY_FOLLOWING_LIST_URL
#
#         self.followers_list_url = af_config.MY_FOLLOWERS_LIST_URL
#
#         self.follow_url = af_config.MY_FOLLOW_URL
#         self.unfollow_url = af_config.MY_UNFOLLOW_URL
#
#         self.headers_referer = af_config.MY_HEADERS_REFERER
#
#         self.cookies_path = af_config.MY_COOKIES_SAVE
#         self.cookies = get_cookies_from_file(self.cookies_path)
#
#         self.headers = af_config.HEADERS
#         self.headers.update({'cookie': self.cookies})
#
#         self.login_num = 1
#         self.country = '马来西亚'
#
#     def login(self):
#         """登录获取cookies"""
#         # 手机模式
#         # mobile_emulation = {"deviceName": "iPhone X"}
#         # options = Options()
#         # options.add_experimental_option("mobileEmulation", mobile_emulation)
#         # driver = webdriver.Chrome(chrome_options=options)
#
#         driver = webdriver.Chrome()
#         driver.implicitly_wait(8)
#         driver.get(self.login_url)
#
#         time.sleep(4)
#         # 选择语言
#         try:
#             driver.find_element_by_xpath('//*[@id="modal"]/div[1]/div[1]/div/div[3]/button[1]').click()
#         except:
#             pass
#         # 关闭广告
#         driver.find_element_by_xpath('//*[@id="modal"]/div/div/div[2]/div').click()
#         time.sleep(1)
#         # 点击登陆
#         driver.find_element_by_xpath('//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[5]').click()
#         # 输入账户密码
#         driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[2]/input').send_keys(
#             self.name)
#         time.sleep(2)
#         driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[3]/input').send_keys(
#             self.password)
#         time.sleep(2)
#         driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[2]/button[2]').click()
#
#         time.sleep(2)
#         try:
#             user = driver.find_element_by_xpath(
#                 '//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[3]/div/div/div[2]').text
#         except:
#             user = ''
#         if user not in ['musesworld.my', 'musesworld.ph', 'musesbaby.th', 'musesbaby.id']:
#             return False
#
#         # print(driver.get_cookies())
#         self.cookies = ''
#         for cook in driver.get_cookies():
#             self.cookies += cook['name'] + '=' + cook['value'] + '; '
#         # 保存cookies到文件中
#         # print(cookies)
#         save_cookies_to_file(self.cookies_path, self.cookies)
#         self.headers.update({'cookie': self.cookies})
#
#         driver.quit()
#         return True
#
#     def following_count(self):
#         """返回店铺关注中的人数"""
#         if not self.cookies:
#             print('无cookies')
#             is_login = self.login()
#             if not is_login:
#                 self.websocket.send('> 登陆失败'.encode('utf-8'))
#                 return ''
#
#         response = requests.get(self.following_count_url, headers=self.headers)
#
#         # print(response.status_code)
#         # print(response.text)
#         if response.status_code == 200:
#             try:
#                 res = json.loads(response.text)
#             except:
#                 print('反序列化信息失败！')
#                 return ''
#             return res['data']['account']['following_count']
#         else:
#             print('请求失败！')
#             return ''
#
#     def batch_unfollow(self, unfollow_num):
#         """批量取关操作，从最早关注开始取关"""
#
#         following_num = self.following_count()
#         unfollow_num = int(unfollow_num)
#         if not following_num:
#             # print('关注人数查询失败')
#             self.websocket.send('> 关注人数查询失败'.encode('utf-8'))
#             return
#
#         following_num = int(following_num)
#         if unfollow_num > following_num:
#             msg = '当前站点：{}，关注人数只有：{} 人'.format(self.country, following_num)
#             # print(msg)
#             self.websocket.send(msg.encode('utf-8'))
#             unfollow_num = following_num
#         else:
#             msg = '当前站点：{}，关注人数：{} 人'.format(self.country, following_num)
#             # print(msg)
#             self.websocket.send(msg.encode('utf-8'))
#
#         num = 1
#         while num <= unfollow_num:
#             # 如果偏移量 起始值为0 则已经取完关注中的人
#             if following_num == 0:
#                 break
#             # 偏移量 每次偏移20 如果总数小于20 则从零开始
#             following_num -= 20
#             if following_num <= 0:
#                 following_num = 0
#             url = self.following_list_url.format(following_num)
#             response = requests.get(url, headers=self.headers)
#             # print(response.status_code)
#             # print(response.text)
#
#             if response.status_code == 200:
#                 soup = BeautifulSoup(response.text, 'lxml')
#
#                 result_ele = soup.select('li[class="clickable_area middle-centered-div"]')
#                 if not result_ele:
#                     self.websocket.send('> 返回结果中没找到想要的元素'.encode('utf-8'))
#                     return
#
#                 for user_ele in result_ele:
#                     user_shopid = user_ele.attrs['data-follower-shop-id']
#                     # print(user_shopid)
#                     try:
#                         user_name = user_ele.select('.down a')[0].get_text().strip()
#                     except:
#                         user_name = "匿名人氏"
#                     # is_follow = user_ele.select('.btn-follow')[0].get_text().strip()
#                     follow_msg = self.follow(user_shopid, 'unfollow')
#
#                     if follow_msg == 'error_not_login' and self.login_num == 1:
#                         is_login = self.login()
#                         if is_login:
#                             self.batch_unfollow(unfollow_num)
#                             self.login_num += 1
#                         return
#                     elif follow_msg != '取关成功':
#                         follow_msg = '> ' + follow_msg
#                         self.websocket.send(follow_msg.encode('utf-8'))
#                         return
#
#                     result_msg = str(num) + ' ' + user_name + ' ' + follow_msg
#                     self.websocket.send(result_msg.encode('utf-8'))
#                     # print(num, user_name, self.follow(user_shopid, 'unfollow'))
#                     num += 1
#                     if num > unfollow_num:
#                         break
#                     time.sleep(0.6)
#             else:
#                 self.websocket.send('> 请求失败'.encode('utf-8'))
#                 break
#
#     def batch_follow(self, seller_id, follow_num):
#         """批量关注操作，条件：店铺ID、需要关注的人数"""
#
#         follow_num = int(follow_num)
#         num = 1
#         # 偏移 从0开始
#         off_num = 0
#         while num <= follow_num:
#             url = self.followers_list_url.format(seller_id, off_num)
#
#             response = requests.get(url, headers=self.headers)
#
#             # print(response.status_code)
#             # print(response.text)
#             if response.status_code == 200:
#                 # 请求返回的不是粉丝列表 则跳出 结束程序
#                 if len(response.text) < 100:
#                     # print('请求范围超出他的粉丝数')
#                     self.websocket.send('> 请求范围超出他的粉丝数'.encode('utf-8'))
#                     return
#
#                 soup = BeautifulSoup(response.text, 'lxml')
#                 result_ele = soup.select('li[class="clickable_area middle-centered-div"]')
#                 if not result_ele:
#                     self.websocket.send('> 返回结果中没找到想要的元素'.encode('utf-8'))
#                     return
#
#                 for user_ele in result_ele:
#                     user_shopid = user_ele.attrs['data-follower-shop-id']
#                     # 网页中有可能只有一个名字，则user_name元素可能找不到
#                     try:
#                         user_name = user_ele.select('.down a')[0].get_text().strip()
#                     except:
#                         user_name = 'un.xx'
#
#                     # 如果名字以.my|.ph|.id|.th|.xx 结尾  则跳过该用户
#                     if re.match('^.*(?:\.(ph|my|th|id|xx))$', user_name):
#                         # print(user_name, '跳过该用户')
#                         result_msg = '~ ' + user_name + ' ' + '跳过该用户'
#                         self.websocket.send(result_msg.encode('utf-8'))
#                         continue
#
#                     is_follow = user_ele.select('.btn-follow')[0].get_text().strip()
#                     if is_follow in ['Following', 'Mengikuti', 'กำลังติดตาม']:
#                         # print(user_name, '已关注该用户')
#                         result_msg = '^ ' + user_name + ' ' + '已关注该用户'
#                         self.websocket.send(result_msg.encode('utf-8'))
#                     elif is_follow in ['+ Follow', '+ Ikuti', '+ ติดตาม']:
#                         # print(num, user_name, self.follow(user_shopid))
#                         follow_msg = self.follow(user_shopid)
#
#                         if follow_msg == 'error_not_login' and self.login_num == 1:
#                             is_login = self.login()
#                             if is_login:
#                                 self.batch_follow(seller_id, follow_num)
#                                 self.login_num += 1
#                             return
#                         elif follow_msg != '关注成功':
#                             follow_msg = '> ' + follow_msg
#                             self.websocket.send(follow_msg.encode('utf-8'))
#                             return
#
#                         result_msg = str(num) + ' ' + user_name + ' ' + follow_msg
#                         self.websocket.send(result_msg.encode('utf-8'))
#                         num += 1
#                         if num > follow_num:
#                             break
#                         time.sleep(0.25)
#                     else:
#                         # print(is_follow)
#                         # print(user_name, '关注信息出错')
#                         result_msg = '{} 关注信息出错 ({})'.format(user_name, is_follow)
#                         self.websocket.send(result_msg.encode('utf-8'))
#                         return
#
#                 off_num += 20
#             else:
#                 # print('请求失败！')
#                 self.websocket.send('> 请求失败！'.encode('utf-8'))
#                 return
#
#     def follow(self, shopid, f_type='follow'):
#         # 关注和取关
#         if f_type == 'unfollow':
#             url = self.unfollow_url.format(shopid)
#             s_msg = '取关成功'
#         else:
#             url = self.follow_url.format(shopid)
#             s_msg = '关注成功'
#
#         headers = {'referer': self.headers_referer}
#         headers.update(self.headers)
#
#         data = {'csrfmiddlewaretoken': get_csrftoken(self.cookies)}
#
#         response = requests.post(url, headers=headers, data=data)
#
#         # print(response.text)
#         if response.status_code == 200:
#             try:
#                 e = json.loads(response.text)
#             except:
#                 print(response.text)
#                 return '反序列化信息失败!'
#             if 'success' in e:
#                 return s_msg if e['success'] else '操作请求失败!'
#             elif 'error' in e:
#                 return e['error']
#             else:
#                 return '操作请求失败!'
#         else:
#             # print(response.status_code)
#             return '请求失败!'


if __name__ == '__main__':
    pass
    # while 1:
    #     print('**************** 主菜单界面 ****************')
    #     print('选择站点：(1)马来西亚 (2)菲律宾 (3)泰国 (0)退出')
    #     menu_num = input('请选择: ')
    #     if menu_num not in ['1', '2', '3', '0']:
    #         print('输入错误')
    #     else:
    #         if menu_num == '0':
    #             break

    # def login():
    #     """登录获取cookies"""
    #     driver = webdriver.Chrome()
    #     driver.implicitly_wait(8)
    #     driver.get('https://shopee.co.id')
    #
    #     time.sleep(4)
    #     # 选择语言
    #     try:
    #         driver.find_element_by_xpath('//*[@id="modal"]/div[1]/div[1]/div/div[3]/button[1]').click()
    #     except:
    #         pass
    #     # 关闭广告
    #     driver.find_element_by_xpath('//*[@id="modal"]/div/div/div[2]/div').click()
    #     time.sleep(1)
    #     # 点击登陆
    #     driver.find_element_by_xpath('//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[5]').click()
    #     # 输入账户密码
    #     driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[2]/input').send_keys(
    #         sp_config.ID_USERNAME)
    #     time.sleep(2)
    #     driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[1]/div[3]/input').send_keys(
    #         sp_config.ID_PASSWORD)
    #     time.sleep(2)
    #     driver.find_element_by_xpath('//*[@id="modal"]/div/div[1]/div/div/div[2]/div[2]/button[2]').click()
    #
    #     time.sleep(2)
    #     try:
    #         user = driver.find_element_by_xpath(
    #             '//*[@id="main"]/div/div[2]/div[1]/div/div[1]/div/ul/li[3]/div/div/div[2]').text
    #     except:
    #         user = ''
    #     print(user)
    #     if user not in ['musesworld.my', 'musesworld.ph', 'musesbaby.th', 'musesbaby.id']:
    #         return False
    #
    #     # print(driver.get_cookies())
    #     driver.quit()
    #     return True
    #
    # login()
