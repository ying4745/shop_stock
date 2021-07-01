USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'


# 获取运单号URL
PH_SHIP_ID = 'https://seller.ph.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
TH_SHIP_ID = 'https://seller.th.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
SG_SHIP_ID = 'https://seller.sg.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
MY_SHIP_ID = 'https://seller.my.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
VN_SHIP_ID = 'https://seller.vn.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
ID_SHIP_ID = 'https://seller.id.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'
BR_SHIP_ID = 'https://seller.br.shopee.cn/api/v3/logistics/get_logistics_tracking_history/'


# 菲律宾配置

# 登录URL
PH_LOGIN_URL = 'https://seller.ph.shopee.cn/account/signin'

# 商品信息URL
PH_PRODUCT_URL = 'https://seller.ph.shopee.cn/api/v3/product/search_product_list/'
# 2020/11/24 更新 https://seller.my.shopee.cn/api/v3/product/search_product_list/
# ?SPC_CDS=&SPC_CDS_VER=2&page_number=1&page_size=24&list_type=&search_type=sku&keyword=T220003&version=3.2.0

# 订单信息URL
# PH_ORDER_URL = 'https://seller.ph.shopee.cn/api/v2/orders/'
# PH_ORDER_SEARCH_URL = 'https://seller.ph.shopee.cn/api/v2/orders/hint/'

# PH_ORDER_URL = 'https://seller.ph.shopee.cn/api/v3/order/get_order_list/'
PH_GET_ORDER_IDS_URL = 'https://seller.ph.shopee.cn/api/v3/order/get_forder_list/'
PH_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.ph.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

PH_ORDER_SEARCH_URL = 'https://seller.ph.shopee.cn/api/v3/order/get_order_hint/'
# PH_ONE_ORDER_URL = 'https://seller.ph.shopee.cn/api/v3/order/get_one_order/'

PH_ORDER_INCOME_URL = 'https://seller.ph.shopee.cn/api/v3/finance/income_transaction_history_detail/'
PH_CHECK_INCOME_URL = 'https://seller.ph.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
# PH_MAKE_WAYBILL_URL = 'https://seller.ph.shopee.cn/api/v2/orders/dropoffs/{0}/?SPC_CDS={1}&SPC_CDS_VER=2'
# PH_WAYBILL_URL = 'https://seller.ph.shopee.cn/api/v2/orders/waybill/'

PH_MAKE_WAYBILL_URL = 'https://seller.ph.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
PH_WAYBILL_URL = 'https://seller.ph.shopee.cn/api/v3/logistics/get_waybill_list/'
PH_FORDERID_URL = 'https://seller.ph.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'
# PH_FORDERID_URL = 'https://seller.ph.shopee.cn/api/v3/order/batch_get_forder_from_oms'

# cookies保存地址
PH_COOKIES_SAVE = 'spider/log/ph_cookies.txt'
# 更新商品记录
PH_UPDATE_LOG = 'spider/log/ph_update_goods.txt'
# 订单记录
PH_ORDER_LOG = 'spider/log/ph_order.txt'
# 错误日志
PH_ERROR_LOG = 'spider/log/ph_error_log.log'



# 马来西亚，巴西配置

# 登录URL
MY_LOGIN_URL = 'https://seller.my.shopee.cn/account/signin'

# 商品信息URL
MY_PRODUCT_URL = 'https://seller.my.shopee.cn/api/v3/product/search_product_list/'

# 订单信息URL
# MY_ORDER_URL = 'https://seller.my.shopee.cn/api/v3/order/get_order_list/'
# MY_GET_ORDER_IDS_URL = 'https://seller.my.shopee.cn/api/v3/order/get_order_ids/'
MY_GET_ORDER_IDS_URL = 'https://seller.my.shopee.cn/api/v3/order/get_forder_list/'
# MY_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.my.shopee.cn/api/v3/order/get_order_list_by_order_ids/'
MY_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.my.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

MY_ORDER_SEARCH_URL = 'https://seller.my.shopee.cn/api/v3/order/get_order_hint/'
# MY_ONE_ORDER_URL = 'https://seller.my.shopee.cn/api/v3/order/get_one_order/'

MY_ORDER_INCOME_URL = 'https://seller.my.shopee.cn/api/v3/finance/income_transaction_history_detail/'
MY_CHECK_INCOME_URL = 'https://seller.my.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
MY_MAKE_WAYBILL_URL = 'https://seller.my.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
MY_WAYBILL_URL = 'https://seller.my.shopee.cn/api/v3/logistics/get_waybill_list/'
MY_FORDERID_URL = 'https://seller.my.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
MY_COOKIES_SAVE = 'spider/log/my_cookies.txt'
# 更新商品记录
MY_UPDATE_LOG = 'spider/log/my_update_goods.txt'
# 订单记录
MY_ORDER_LOG = 'spider/log/my_order.txt'
# 错误日志
MY_ERROR_LOG = 'spider/log/my_error_log.log'


# 巴西 订单交易信息URL
# BR_ORDER_URL = 'https://seller.my.shopee.cn/api/v3/order/get_order_list/'
BR_ORDER_ID_URL = 'https://seller.my.shopee.cn/api/v3/order/get_forder_list'
BR_ORDER_INFO_URL = 'https://seller.my.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'
BR_ORDER_DETAIL_URL = 'https://seller.my.shopee.cn/api/sip/v2/orders/detail/'

# 巴西 单个订单信息URL 参数为shopee订单id
BR_ONE_ORDER_URL = 'https://seller.my.shopee.cn/api/v3/order/get_one_order'
# BR_MAKE_WAYBILL_URL = 'https://seller.my.shopee.cn/api/v3/shipment/init_order/?sip_region_for_fulfillment=br&sip_shop_id_for_fulfillment=191538284&SPC_CDS={}&SPC_CDS_VER=2'
# BR_WAYBILL_URL = 'https://seller.my.shopee.cn/api/v3/logistics/get_waybill_new/'

# 越南
# VN_MAKE_WAYBILL_URL = 'https://seller.my.shopee.cn/api/v3/shipment/init_order/?sip_region_for_fulfillment=vn&sip_shop_id_for_fulfillment=255934143&SPC_CDS={}&SPC_CDS_VER=2'


# 泰国配置


# 登录URL
TH_LOGIN_URL = 'https://seller.th.shopee.cn/account/signin'

# 商品信息URL
TH_PRODUCT_URL = 'https://seller.th.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
# TH_ORDER_URL = 'https://seller.th.shopee.cn/api/v3/order/get_order_list/'
TH_GET_ORDER_IDS_URL = 'https://seller.th.shopee.cn/api/v3/order/get_forder_list/'
TH_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.th.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

TH_ORDER_SEARCH_URL = 'https://seller.th.shopee.cn/api/v3/order/get_order_hint/'
# TH_ONE_ORDER_URL = 'https://seller.th.shopee.cn/api/v3/order/get_one_order/'

TH_ORDER_INCOME_URL = 'https://seller.th.shopee.cn/api/v3/finance/income_transaction_history_detail/'
TH_CHECK_INCOME_URL = 'https://seller.th.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
TH_MAKE_WAYBILL_URL = 'https://seller.th.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
TH_WAYBILL_URL = 'https://seller.th.shopee.cn/api/v3/logistics/get_waybill_list/'
TH_FORDERID_URL = 'https://seller.th.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
TH_COOKIES_SAVE = 'spider/log/th_cookies.txt'
# 更新商品记录
TH_UPDATE_LOG = 'spider/log/th_update_goods.txt'
# 订单记录
TH_ORDER_LOG = 'spider/log/th_order.txt'
# 错误日志
TH_ERROR_LOG = 'spider/log/th_error_log.log'


# 印尼配置

# 登录URL
ID_LOGIN_URL = 'https://seller.id.shopee.cn/account/signin'

# 商品信息URL
ID_PRODUCT_URL = 'https://seller.id.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
# ID_ORDER_URL = 'https://seller.id.shopee.cn/api/v3/order/get_order_list/'
ID_GET_ORDER_IDS_URL = 'https://seller.id.shopee.cn/api/v3/order/get_forder_list/'
ID_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.id.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

ID_ORDER_SEARCH_URL = 'https://seller.id.shopee.cn/api/v3/order/get_order_hint/'
# ID_ONE_ORDER_URL = 'https://seller.id.shopee.cn/api/v3/order/get_one_order/'

ID_ORDER_INCOME_URL = 'https://seller.id.shopee.cn/api/v3/finance/income_transaction_history_detail/'
ID_CHECK_INCOME_URL = 'https://seller.id.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
ID_MAKE_WAYBILL_URL = 'https://seller.id.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
ID_WAYBILL_URL = 'https://seller.id.shopee.cn/api/v3/logistics/get_waybill_list/'
ID_FORDERID_URL = 'https://seller.id.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
ID_COOKIES_SAVE = 'spider/log/id_cookies.txt'
# 更新商品记录
ID_UPDATE_LOG = 'spider/log/id_update_goods.txt'
# 订单记录
ID_ORDER_LOG = 'spider/log/id_order.txt'
# 错误日志
ID_ERROR_LOG = 'spider/log/id_error_log.log'


# 新加坡配置

# 登录URL
SG_LOGIN_URL = 'https://seller.sg.shopee.cn/account/signin'

# 商品信息URL
SG_PRODUCT_URL = 'https://seller.sg.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
# SG_ORDER_URL = 'https://seller.sg.shopee.cn/api/v3/order/get_order_list/'
SG_GET_ORDER_IDS_URL = 'https://seller.sg.shopee.cn/api/v3/order/get_forder_list/'
SG_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.sg.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

SG_ORDER_SEARCH_URL = 'https://seller.sg.shopee.cn/api/v3/order/get_order_hint/'
# SG_ONE_ORDER_URL = 'https://seller.sg.shopee.cn/api/v3/order/get_one_order/'

SG_ORDER_INCOME_URL = 'https://seller.sg.shopee.cn/api/v3/finance/income_transaction_history_detail/'
SG_CHECK_INCOME_URL = 'https://seller.sg.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
SG_MAKE_WAYBILL_URL = 'https://seller.sg.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
SG_WAYBILL_URL = 'https://seller.sg.shopee.cn/api/v3/logistics/get_waybill_list/'
SG_FORDERID_URL = 'https://seller.sg.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
SG_COOKIES_SAVE = 'spider/log/sg_cookies.txt'
# 更新商品记录
SG_UPDATE_LOG = 'spider/log/sg_update_goods.txt'
# 订单记录
SG_ORDER_LOG = 'spider/log/sg_order.txt'
# 错误日志
SG_ERROR_LOG = 'spider/log/sg_error_log.log'


# 越南配置

# 登录URL
VN_LOGIN_URL = 'https://seller.vn.shopee.cn/account/signin'

# 商品信息URL
VN_PRODUCT_URL = 'https://seller.vn.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
VN_GET_ORDER_IDS_URL = 'https://seller.vn.shopee.cn/api/v3/order/get_forder_list/'
VN_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.vn.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

VN_ORDER_SEARCH_URL = 'https://seller.vn.shopee.cn/api/v3/order/get_order_hint/'

VN_ORDER_INCOME_URL = 'https://seller.vn.shopee.cn/api/v3/finance/income_transaction_history_detail/'
VN_CHECK_INCOME_URL = 'https://seller.vn.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
VN_MAKE_WAYBILL_URL = 'https://seller.vn.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
VN_WAYBILL_URL = 'https://seller.vn.shopee.cn/api/v3/logistics/get_waybill_list/'
VN_FORDERID_URL = 'https://seller.vn.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
VN_COOKIES_SAVE = 'spider/log/vn_cookies.txt'
# 更新商品记录
VN_UPDATE_LOG = 'spider/log/vn_update_goods.txt'
# 订单记录
VN_ORDER_LOG = 'spider/log/vn_order.txt'
# 错误日志
VN_ERROR_LOG = 'spider/log/vn_error_log.log'


# 巴西自营配置

# 登录URL
BR_LOGIN_URL = 'https://seller.br.shopee.cn/account/signin'

# 商品信息URL
BR_PRODUCT_URL = 'https://seller.br.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
BR_GET_ORDER_IDS_URL = 'https://seller.br.shopee.cn/api/v3/order/get_forder_list/'
BR_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.br.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'

BR_ORDER_SEARCH_URL = 'https://seller.br.shopee.cn/api/v3/order/get_order_hint/'

BR_ORDER_INCOME_URL = 'https://seller.br.shopee.cn/api/v3/finance/income_transaction_history_detail/'
BR_CHECK_INCOME_URL = 'https://seller.br.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
BR_MAKE_WAYBILL_URL = 'https://seller.br.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
BR_WAYBILL_URL = 'https://seller.br.shopee.cn/api/v3/logistics/get_waybill_list/'
BR_FORDERID_URL = 'https://seller.br.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
BR_COOKIES_SAVE = 'spider/log/br_cookies.txt'
# 更新商品记录
BR_UPDATE_LOG = 'spider/log/br_update_goods.txt'
# 订单记录
BR_ORDER_LOG = 'spider/log/br_order.txt'
# 错误日志
BR_ERROR_LOG = 'spider/log/br_error_log.log'


# 台湾配置

# 登录URL
TW_LOGIN_URL = 'https://seller.xiapi.shopee.cn/account/signin'

# 商品信息URL
TW_PRODUCT_URL = 'https://seller.xiapi.shopee.cn/api/v3/product/page_product_list/'

# 订单信息URL
# TW_ORDER_URL = 'https://seller.tw.shopee.cn/api/v3/order/get_order_list/'
TW_GET_ORDER_IDS_URL = 'https://seller.xiapi.shopee.cn/api/v3/order/get_order_ids/'
TW_ORDER_LIST_BY_ORDER_IDS_URL = 'https://seller.xiapi.shopee.cn/api/v3/order/get_shipment_order_list_by_order_ids/'


TW_ORDER_SEARCH_URL = 'https://seller.xiapi.shopee.cn/api/v3/order/get_order_hint/'
# TW_ONE_ORDER_URL = 'https://seller.tw.shopee.cn/api/v3/order/get_one_order/'

TW_ORDER_INCOME_URL = 'https://seller.xiapi.shopee.cn/api/v3/finance/income_transaction_history_detail/'
TW_CHECK_INCOME_URL = 'https://seller.xiapi.shopee.cn/api/v3/finance/income_transaction_histories/'

# 生成、下载运单号URL
TW_MAKE_WAYBILL_URL = 'https://seller.xiapi.shopee.cn/api/v3/shipment/init_order/?SPC_CDS={0}&SPC_CDS_VER=2'
TW_WAYBILL_URL = 'https://seller.xiapi.shopee.cn/api/v2/orders/waybill/'
TW_FORDERID_URL = 'https://seller.xiapi.shopee.cn/api/v3/logistics/check_package_print_waybill_multi_shop?SPC_CDS={0}&SPC_CDS_VER=2'

# cookies保存地址
TW_COOKIES_SAVE = 'spider/log/tw_cookies.txt'
# 更新商品记录
TW_UPDATE_LOG = 'spider/log/tw_update_goods.txt'
# 订单记录
TW_ORDER_LOG = 'spider/log/tw_order.txt'
# 错误日志
TW_ERROR_LOG = 'spider/log/tw_error_log.log'