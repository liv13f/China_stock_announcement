#!/usr/bin/python
#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import os
import httplib
import urllib
import urllib2
import socket
import unicodecsv
import json
import re
import calendar
import datetime
import time
import logging
import logging.handlers
import codecs
import sys
import MySQLdb
from bs4 import BeautifulSoup
from warnings import filterwarnings
filterwarnings('error', category=MySQLdb.Warning)


###############################################导入mysql数据库#################
def import2mysql(columntype, csvfile, tablename):
    if columntype == 'sse':
        LOG_FILE = '/data/annc_prog/logs/mysql.log'
    if columntype == 'regulator':
        LOG_FILE = '/data/annc_prog/csrc_logs/mysql.log'
    # LOG_FILE = '/data/test/mysql.log'
    handler_mysql = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1024 * 1024, backupCount=5)  # 实例化handler
    fmt_mysql = '%(asctime)s  - %(message)s'
    formatter_mysql = logging.Formatter(fmt_mysql)   # 实例化formatter
    handler_mysql.setFormatter(formatter_mysql)      # 为handler添加formatter
    logger_mysql = logging.getLogger('mysql')    # 获取名为import的logger
    logger_mysql.addHandler(handler_mysql)           # 为logger添加handler
    logger_mysql.setLevel(logging.DEBUG)
    # 连接数据库
    try:
        conn = MySQLdb.connect(host='', user='',
                               passwd='', port=3306)
        cur = conn.cursor()
    except MySQLdb.Error, e:
        logger_mysql.error("MySQL数据连接不上 %s" % (str(e)))
    else:
        # datebase annc
        cur.execute('use annc;')
        sql = "load data local infile " + "'" + csvfile + "'" + \
            " into table " + tablename + " fields terminated by ',' lines terminated by '\n';"
        try:
            cur.execute(sql)  # 执行sql语句
            conn.commit()  # 提交
        except MySQLdb.Warning:
            cur.execute("SHOW WARNINGS")
            w = cur.fetchall()
            for i in w:
                logger_mysql.info(" %s" % (i,))
        except MySQLdb.Error, e:
            logger_mysql.error("数据导入mysql错误 %s %s" % (csvfile, str(e),))
        else:
            logger_mysql.info("处理文件成功 %s" % (csvfile, ))  # 操作成功
        # 关闭日志
        handler_mysql.flush()
        handler_mysql.close()
        logger_mysql.removeHandler(handler_mysql)
        cur.close()  # 关闭操作
        conn.close()  # 关闭连接


####################################################下载公告列表，解析并下载公告########
def download(columntype, daterange_i, downloadpath):
    # 检查路径，若没有即创建
    if columntype == 'sse':
        contentpath = downloadpath + 'sse/content/' + \
            str(daterange_i)[0:4] + '/' + str(daterange_i)[5:7] + '/'
        listpath = downloadpath + 'sse/list/' + \
            str(daterange_i)[0:4] + '/'
    if columntype == 'regulator':
        contentpath = downloadpath + 'csrc/content/' + \
            str(daterange_i)[0:4] + '/' + str(daterange_i)[5:7] + '/'
        listpath = downloadpath + 'csrc/list/' + \
            str(daterange_i)[0:4] + '/'
    if os.path.exists(contentpath):
        pass
    else:
        os.makedirs(contentpath)
    if os.path.exists(listpath):
        pass
    else:
        os.makedirs(listpath)
    # 服务器地址starturl
    starturl = 'http://www.cninfo.com.cn/cninfo-new/announcement/query'

    ############################################ list 部分 #####################
    # 读取最新的URL列表, 放入now []
    now = []
    # 字典d用于得到每只股票的当日anncid
    d = dict()  # 用于形成anncid里的序号
    flag = True  # 用于确认是否有下一页的布尔值
    page_num = 1  # 起始页为1
    while flag == True:
        # request headers
        headers = {

        }
        # request data
        data = 'stock=&searchkey=&plate=&category=&trade=&column=' + columntype + '&columnTitle=%E5%8E%86%E5%8F%B2%E5%85%AC%E5%91%8A%E6%9F%A5%E8%AF%A2&pageNum=' + \
            str(page_num) + '&pageSize=30&tabName=fulltext&sortName=&sortType=&limit=&showTitle=&seDate=' + str(daterange_i)
        req = urllib2.Request(starturl, data, headers)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            logger_error.error('响应错误 日期 页数: %s %s %s' %
                               (e, str(daterange_i), str(page_num)))
            flag = False
        except urllib2.URLError, e:
            logger_error.error('响应错误 日期 页数: %s %s %s' %
                               (e, str(daterange_i), str(page_num)))
            flag = False
        else:
            #  将相应json化便于用字典读取
            r = response.read()
            try:
                j = json.loads(r)
            except ValueError, e:
                logger_error.error('响应错误 日期 页数: %s %s %s' %
                                   (e, str(daterange_i), str(page_num)))
                flag = False
            else:
                flag = j['hasMore']
                # 记录日志
                logger.info('日 期:' + str(daterange_i) + '     PageNUmber = ' + str(page_num) +
                            '   hasMore = ' + str(flag))
                # 把每一页的项目append 到now里
                for item_num in range(0, len(j['announcements'])):
                    ii = j['announcements'][item_num]
                    valid = 0  # 下载成功后变为1
                    # 得到 title url 和 file_type
                    title = ii['announcementTitle'].replace(',', '').replace(
                        '<font color=red>', '').replace('</font>', '').strip('\n')
                    url = 'http://www.cninfo.com.cn/' + \
                        ii['adjunctUrl'].strip()
                    # 防止重复
                    if (url in d) == False:
                        d[url] = 'Yes'
                        ########################确定公告文件的类型file_type#############
                        if url.find('.html') > -1:
                            file_type = 'TXT'
                        elif url.find('.js') > -1:
                            file_type = 'TXT'
                        elif url.find('.pdf') > -1 or url.find('.PDF') > -1:
                            file_type = 'PDF'
                        elif url.find('.doc') > -1 or url.find('.DOC') > -1:
                            if url.find('.docx') > -1 or url.find('.DOCX') > -1:
                                file_type = 'DOCX'
                            else:
                                file_type = 'DOC'
                        else:
                            file_type = 'UNKNOEN'
                        #######################################################
                        # 把时间戳转为yyyy-mm-dd hh:mm:ss的形式，若没有，则按00:00:00算
                        try:
                            antime = time.strftime(
                                '%Y-%m-%d %H:%M:%S', time.localtime(ii['announcementTime'] / 1000))
                        except ValueError, e:
                            antime = daterange_i + ' 00:00:00'
                        else:
                            pass
                        if columntype == 'sse':
                            abbv = ii['secName']
                            symbol = ii['secCode']
                            # 生成anncid
                            if len(symbol) == 6:
                                if symbol in d:
                                    d[symbol] = int(d[symbol]) + 1
                                else:
                                    d[symbol] = 1
                            # 1位数字添00,2位数字添0
                                if d[symbol] < 10:
                                    anncid = symbol + \
                                        str(daterange_i).replace(
                                            '-', '') + '00' + str(d[symbol])
                                elif d[symbol] < 100:
                                    anncid = symbol + \
                                        str(daterange_i).replace(
                                            '-', '') + '0' + str(d[symbol])
                                else:
                                    anncid = symbol + \
                                        str(daterange_i).replace(
                                            '-', '') + str(d[symbol])
                                anncid = str(anncid)

                                now.append([anncid, symbol, abbv, title, antime[
                                           0:10], antime[-8:], file_type, url, valid, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                        elif columntype == 'regulator':
                            if ii['secCode'] != None and ii['secCode'] != '':
                                symbol = ii['secCode'].replace(',', ';')
                            regu_type = ii['columnId']
                            # 根据columnId来确定公告类型
                            if regu_type.find('251201') > -1 or regu_type.find('010206') > -1:
                                regu_type = 'SZSE'
                            elif regu_type.find('251202') > -1 or regu_type.find('010215') > -1:
                                regu_type = 'SSE'
                            elif regu_type.find('251203') > -1 or regu_type.find('010216') > -1:
                                regu_type = 'CSDC'
                            elif regu_type.find('251204') > -1 or regu_type.find('010217') > -1:
                                regu_type = 'CSRC'

                            if regu_type in d:
                                d[regu_type] = int(d[regu_type]) + 1
                            else:
                                d[regu_type] = 1
                            # 个位数字添0
                            if d[regu_type] < 10:
                                anncid = regu_type + \
                                    str(daterange_i).replace(
                                        '-', '') + '0' + str(d[regu_type])
                            else:
                                anncid = regu_type + \
                                    str(daterange_i).replace(
                                        '-', '') + str(d[regu_type])
                            now.append([anncid, symbol, regu_type, title, antime[
                                0:10], antime[-8:], file_type, url, valid, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

                page_num += 1
            response.close()

    # 如果没有数据则不进行后续工作
    if len(now) != 0:
        # 把已存文件的内容读出来，作为old [],若当日无csv则创建，old置空
        old = []
        temp = []
        if os.path.exists(listpath + str(daterange_i) + '.csv'):
            f_old = open(listpath + str(daterange_i) + '.csv', 'r+')
            f_r = unicodecsv.reader(f_old, encoding='utf-8')
            for row in f_r:
                old.append(row)
            f_old.close()
            # 把now中与old重复的去掉,计入temp
            for i in now:
                has = False
                for j in old:
                    if i[7].strip() == j[7].strip():
                        has = True
                if has == False:
                    temp.append(i)
        else:
            temp = now

        #########################################download部分####################
        # 如果有新的，就更新到csv和数据库里
        if len(temp) != 0:
            # 把temp中url指向的公告下载到contentpath下,并更新temp到tempupdate
            temp_update = []
            #################################定义不同文件类型的下载函数############################
            def downhtml(contentpath, anncid, url):
                try:
                    contentpage = urllib2.urlopen(url, timeout=60)
                except urllib2.URLError, e:
                    logger_error.error(
                        '公告链接错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                except socket.timeout:
                    downhtml(contentpath, anncid, url)
                else:
                    contentsoup = BeautifulSoup(
                        contentpage, 'lxml', from_encoding="utf-8")
                    try:
                        content = contentsoup.findAll(
                            'span', {'class': 'da'})
                        con_len = len(content)
                        content_txt = content[
                            con_len - 1].get_text()
                    except IndexError, e:
                        try:
                            content = contentsoup.findAll(
                                'pre')
                            con_len = len(content)
                            content_txt = content[0].get_text()
                        except IndexError, e:
                            logger_error.error(
                                '页面解析错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                        else:
                            f_temp = codecs.open(
                                contentpath + anncid + '.txt', 'w+', encoding='utf-8')
                            f_temp.write(content_txt)
                            f_temp.close()
                            row[8] = 1
                            logger.info('成功下载： id为：%s url：%s ' %
                                        (anncid, url))
                    else:
                        f_temp = codecs.open(
                            contentpath + anncid + '.txt', 'w+', encoding='utf-8')
                        f_temp.write(content_txt)
                        f_temp.close()
                        row[8] = 1
                        logger.info('成功下载： id为：%s url：%s ' % (anncid, url))
                    contentpage.close()

            def downjs(contentpath, anncid, url):
                try:
                    contentpage = urllib2.urlopen(url, timeout=60)
                except urllib2.URLError, e:
                    logger_error.error(
                        '公告链接错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                except socket.timeout:
                    downjs(contentpath, anncid, url)
                else:
                    try:
                        content_txt = contentpage.read().decode('gbk').encode('utf-8')
                    except UnicodeDecodeError, e:
                        logger_error.error(
                            'js类型解码错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                    else:
                        content_txt = re.search(
                            r'"Zw":(.*)<br>', content_txt)
                        if content_txt == None:
                            logger_error.error(
                                'js类型解码错误 id号 URL网址: %s %s' % (anncid, url))
                        else:
                            content_txt = content_txt.group().replace('<br>', '').replace('"Zw":"', '')
                            f_temp = codecs.open(
                                contentpath + anncid + '.txt', 'w+', encoding='utf-8')
                            f_temp.write(content_txt)
                            f_temp.close()
                            row[8] = 1
                            logger.info('成功下载： id为：%s url：%s ' %
                                        (anncid, url))
                    contentpage.close()

            def downdoc(contentpath, anncid, url):
                try:
                    contentpage = urllib2.urlopen(url, timeout=60)
                except urllib2.URLError, e:
                    logger_error.error(
                        '公告链接错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                except socket.timeout:
                    downdoc(contentpath, anncid, url)
                else:
                    if url.find('.docx') > -1 or url.find('.DOCX') > -1:
                        f_temp = open(
                            contentpath + anncid + '.docx', 'w+')
                    else:
                        f_temp = open(
                            contentpath + anncid + '.doc', 'w+')
                    f_temp.write(contentpage.read())
                    f_temp.close()
                    logger.info('成功下载： id为：%s url：%s ' % (anncid, url))
                    row[8] = 1
                    contentpage.close()

            def downpdf(contentpath, anncid, url):
                try:
                    contentpage = urllib2.urlopen(url, timeout=60)
                except urllib2.URLError, e:
                    logger_error.error(
                        '公告链接错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                except httplib.BadStatusLine, e:
                    logger_error.error(
                        '公告链接错误 id号 URL网址: %s %s %s' % (e, anncid, url))
                except socket.timeout:
                    downpdf(contentpath, anncid, url)
                else:
                    f_temp = open(
                        contentpath + anncid + '.pdf', 'w+')
                    f_temp.write(contentpage.read())
                    f_temp.close()
                    logger.info('成功下载： id为：%s url：%s ' % (anncid, url))
                    row[8] = 1
                    contentpage.close()
            #################################################################################


            # temp里的公告都尝试下载，并根据是否成功下载，更新为temp_updata
            for row in temp:
                url = row[7]
                anncid = row[0]
                # 解析url类型并下载url链接下的公告
                if url.find('.html') > -1:
                    downhtml(contentpath, anncid, url)

                elif url.find('.js') > -1:
                    downjs(contentpath, anncid, url)

                elif url.find('.doc') > -1 or url.find('.DOC') > -1:
                    downdoc(contentpath, anncid, url)

                elif url.find('.pdf') > -1 or url.find('.PDF') > -1:
                    downpdf(contentpath, anncid, url)

                else:
                    logger_error.error(
                        '公告新类型未下载： id号 URL网址: %s %s' % (anncid, url))
                temp_update.append(row)
            logger.info('本次成功下载了' + str(len(temp_update)) + '份公告')

            # 把之前未存的temp 里的数据 更新到月csv 和 日csv, 日csv里的内容作为下次的 old[]
            f_mon = open(listpath + str(daterange_i)
                         [0:7].replace('-', '') + '.csv', 'a+')
            f_w = unicodecsv.writer(
                f_mon, encoding='utf-8')  # 直接使用csv则存储的都是二进制
            for row in temp_update:
                f_w.writerow(row)
            f_mon.close()
            f_day = open(listpath + str(daterange_i) + '.csv', 'a+')
            f_w = unicodecsv.writer(
                f_day, encoding='utf-8')  # 直接使用csv则存储的都是二进制
            for row in temp_update:
                f_w.writerow(row)
            f_day.close()
            f_tmp = open(listpath + str(daterange_i) + '_temp.csv', 'a+')
            f_w = unicodecsv.writer(
                f_tmp, encoding='utf-8')  # 直接使用csv则存储的都是二进制
            for row in temp_update:
                f_w.writerow(row)
            f_tmp.close()

            #把更新的数据倒入数据库中 ,然后把temp.csv删掉
            if columntype == 'sse':
                import2mysql(columntype, listpath +
                             str(daterange_i) + '_temp.csv', 'sse_annc_list')
            if columntype == 'regulator':
                import2mysql(columntype, listpath +
                             str(daterange_i) + '_temp.csv', 'csrc_annc_list')
                # 公告影响表
                impact = []
                f_impact = open(listpath + 'impact.csv', 'a+')
                f_w = unicodecsv.writer(
                    f_impact, encoding='utf-8')  # 直接使用csv则存储的都是二进制
                for row in temp_update:
                    if len(row[0]) > 3 and row[1] != None and row[1] != '':
                        impact_i = row[1].strip('\n').split(';')
                        for imp in impact_i:
                            impact.append([row[0], imp])
                for item in impact:
                    f_w.writerow(item)
                f_impact.close()
                import2mysql(columntype, listpath +
                             'impact.csv', 'csrc_impact_list')
                os.remove(listpath + 'impact.csv')
            os.remove(listpath + str(daterange_i) + '_temp.csv')


# 起始日期和终止日期，按照YYYY-MM-DD输入日期。默认的存储路径为/data/annc_data,把日期按日拆分后，每日都调用download函数
def cninfoAnncDownload(annc_type, date1=str(datetime.date.today()), date2=str(datetime.date.today()), savepath='/data/annc_data/'):
    currentMinute = int(time.strftime('%M', time.localtime(time.time())))
    currentHour = int(time.strftime('%H', time.localtime(time.time())))
    # 提前追一天
    if currentMinute == 10 and currentHour > 14:
        date2 = str(datetime.date.today() + datetime.timedelta(days=1))
    global logger_error
    global logger
    # 生产日期列表
    date_range = []
    # 先变为datetime对象便于操作
    curr_date = datetime.date(
        int(date1[0:4]), int(date1[5:7]), int(date1[8:10]))
    end_date = datetime.date(
        int(date2[0:4]), int(date2[5:7]), int(date2[8:10]))
    while curr_date != end_date:
        date_range.append(curr_date)
        curr_date += datetime.timedelta(days=1)
    # 再把最后一天的加上
    date_range.append(curr_date)
    if savepath[-1] == '/':
        savepath1 = savepath
    else:
        savepath1 = savepath + '/'
    # 每日循环下载,并分月建立日志
    log_record = []
    for datei in date_range:
        #######################################日志处理############################
        if str(datei)[0:7].replace('-', '') in log_record:
            pass
        else:
            log_record.append(str(datei)[0:7].replace('-', ''))
            # 上个月的日志关掉
            try:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
                handler_error.flush()
                handler_error.close()
                logger_error.removeHandler(handler_error)
            except:
                pass
            finally:
                # 错误日志处理
                if annc_type == 'sse':
                    LOG_ERROR_FILE = '/data/annc_prog/logs/' + \
                        str(datei)[0:7].replace('-', '') + '_error.log'
                if annc_type == 'regulator':
                    LOG_ERROR_FILE = '/data/annc_prog/csrc_logs/' + \
                        str(datei)[0:7].replace('-', '') + '_error.log'

                handler_error = logging.handlers.RotatingFileHandler(
                    LOG_ERROR_FILE, maxBytes=1024 * 1024, backupCount=5)  # 实例化handler
                fmt_error = '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s'
                formatter_error = logging.Formatter(fmt_error)  # 实例化formatter
                handler_error.setFormatter(
                    formatter_error)      # 为handler添加formatter
                logger_error = logging.getLogger(
                    'annc_error')    # 获取名为content的logger
                # 为logger添加handler
                logger_error.addHandler(handler_error)
                logger_error.setLevel(logging.ERROR)

                # INFO日志处理
                if annc_type == 'sse':
                    LOG_INFO_FILE = '/data/annc_prog/logs/' + \
                        str(datei)[0:7].replace('-', '') + '_info.log'
                if annc_type == 'regulator':
                    LOG_INFO_FILE = '/data/annc_prog/csrc_logs/' + \
                        str(datei)[0:7].replace('-', '') + '_info.log'

                handler = logging.handlers.RotatingFileHandler(
                    LOG_INFO_FILE, maxBytes=1024 * 1024, backupCount=5)  # 实例化handler
                fmt = '%(asctime)s  - %(levelname)s - %(message)s'
                formatter = logging.Formatter(fmt)  # 实例化formatter
                handler.setFormatter(formatter)      # 为handler添加formatter
                logger = logging.getLogger('annc_info')    # 获取名为content的logger
                logger.addHandler(handler)          # 为logger添加handler
                logger.setLevel(logging.INFO)
        # 按日下载
        download(annc_type, datei, savepath1)


# 调用了cninfoAnncDownload
if __name__ == "__main__":
    if len(sys.argv) == 5:  # 按照参数执行，由于python程序本身（***.py）就是argv[0]，所以下标需要从1开始
        cninfoAnncDownload(annc_type=sys.argv[1], date1=sys.argv[
                           2], date2=sys.argv[3], savepath=sys.argv[4])
    elif len(sys.argv) == 4:
        cninfoAnncDownload(annc_type=sys.argv[1], date1=sys.argv[
                           2], date2=sys.argv[3])
    elif len(sys.argv) == 3:
        cninfoAnncDownload(annc_type=sys.argv[1], date1=sys.argv[
                           2], date2=sys.argv[2])
    elif len(sys.argv) == 2:
        cninfoAnncDownload(annc_type=sys.argv[1])
    else:
        print '参数输入不正确'
