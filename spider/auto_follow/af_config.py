HEADERS = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    'x-requested-with': 'XMLHttpRequest',
}

# 马来西亚配置
MY_LOGIN_URL = 'https://shopee.com.my'
MY_COOKIES_SAVE = 'spider/auto_follow/my_cookies.txt'

# 关注中的人数查询URL
MY_FOLLOWING_COUNT_URL = 'https://shopee.com.my/api/v2/shop/get?shopid=131872956'
# 关注中的列表
MY_FOLLOWING_LIST_URL = 'https://shopee.com.my/shop/131872956/following/?offset={}&limit=20&offset_of_offset=0'
# 目标店铺 粉丝列表
MY_FOLLOWERS_LIST_URL = 'https://shopee.com.my/shop/{0}/followers/?offset={1}&limit=20&offset_of_offset=0'

# 取关 API
MY_UNFOLLOW_URL = 'https://shopee.com.my/buyer/unfollow/shop/{}/'
# 关注 API
MY_FOLLOW_URL = 'https://shopee.com.my/buyer/follow/shop/{}/'
# headers中 referer参数
MY_HEADERS_REFERER = 'https://shopee.com.my/shop/'


# 菲律宾配置
PH_LOGIN_URL = 'https://shopee.ph'
PH_COOKIES_SAVE = 'spider/auto_follow/ph_cookies.txt'

# 关注中的人数查询URL
PH_FOLLOWING_COUNT_URL = 'https://shopee.ph/api/v2/shop/get?shopid=141272137'
# 关注中的列表
PH_FOLLOWING_LIST_URL = 'https://shopee.ph/shop/141272137/following/?offset={}&limit=20&offset_of_offset=0'
# 目标店铺 粉丝列表
PH_FOLLOWERS_LIST_URL = 'https://shopee.ph/shop/{0}/followers/?offset={1}&limit=20&offset_of_offset=0'

# 取关 API
PH_UNFOLLOW_URL = 'https://shopee.ph/buyer/unfollow/shop/{}/'
# 关注 API
PH_FOLLOW_URL = 'https://shopee.ph/buyer/follow/shop/{}/'
# headers中 referer参数
PH_HEADERS_REFERER = 'https://shopee.ph/shop/'


# 泰国配置
TH_LOGIN_URL = 'https://shopee.co.th'
TH_COOKIES_SAVE = 'spider/auto_follow/th_cookies.txt'

# 关注中的人数查询URL
TH_FOLLOWING_COUNT_URL = 'https://shopee.co.th/api/v2/shop/get?shopid=151139964'
# 关注中的列表
TH_FOLLOWING_LIST_URL = 'https://shopee.co.th/shop/151139964/following/?offset={}&limit=20&offset_of_offset=0'
# 目标店铺 粉丝列表
TH_FOLLOWERS_LIST_URL = 'https://shopee.co.th/shop/{0}/followers/?offset={1}&limit=20&offset_of_offset=0'

# 取关 API
TH_UNFOLLOW_URL = 'https://shopee.co.th/buyer/unfollow/shop/{}/'
# 关注 API
TH_FOLLOW_URL = 'https://shopee.co.th/buyer/follow/shop/{}/'
# headers中 referer参数
TH_HEADERS_REFERER = 'https://shopee.co.th/shop/'


# 印尼配置
ID_LOGIN_URL = 'https://shopee.co.id'
ID_COOKIES_SAVE = 'spider/auto_follow/id_cookies.txt'

# 关注中的人数查询URL
ID_FOLLOWING_COUNT_URL = 'https://shopee.co.id/api/v2/shop/get?shopid=173719496'
# 关注中的列表
ID_FOLLOWING_LIST_URL = 'https://shopee.co.id/shop/173719496/following/?offset={}&limit=20&offset_of_offset=0'
# 目标店铺 粉丝列表
ID_FOLLOWERS_LIST_URL = 'https://shopee.co.id/shop/{0}/followers/?offset={1}&limit=20&offset_of_offset=0'

# 取关 API
ID_UNFOLLOW_URL = 'https://shopee.co.id/buyer/unfollow/shop/{}/'
# 关注 API
ID_FOLLOW_URL = 'https://shopee.co.id/buyer/follow/shop/{}/'
# headers中 referer参数
ID_HEADERS_REFERER = 'https://shopee.co.id/shop/'
