# -*- coding: utf-8 -*-
"""
  The crawler to download YouTube video viewcount history
"""
# Author: Honglin Yu <yuhonglin1986@gmail.com>
# License: BSD 3 clause

import urllib2
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import urllib
import threading
import os
import time
import datetime
import re
import cookielib
from bs4 import BeautifulSoup

from lib.logger import Logger
from lib.sendemail import send_email
from lib.xmlparser import *


class Crawler(object):

    
    def __init__(self):
        
        self._mutex_crawl = threading.Lock()
        self._cookie = ''
        self.youtube_prefix = "https://www.youtube.com"
        self._session_token = ''
        self._is_done = False
        self._update_cookie_period = 1800
        self._update_cookie_maximum_times = 20
        self._last_cookie_update_time = None
        self._current_update_cookie_timer = None


        self._cookie_update_delay_time = 0.1
        self._cookie_update_on = False

        self._seed_username = 'cloecouture'

    def update_cookie_and_sectiontoken(self):
        # if already begin to update
        if self._cookie_update_on == True:
            return

        self._cookie_update_on = True

        self.period_update()
    
    
    def period_update(self):
        
        # all the job is done
        if self._is_done == True:
            return
        # begin to update
        self._mutex_crawl.acquire()

        i = 0
        state = 'fail'
        while i < self._update_cookie_maximum_times:

            # get cookies
            cj = cookielib.CookieJar()
            opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
            #req = Request("https://www.youtube.com/watch?v="+self._seed_username)
            req = Request("https://www.youtube.com/user/"+ "meghanrosette" +"/videos?view=54&flow=grid")
            f = opener.open(req)
            src = f.read()

            time.sleep(self._cookie_update_delay_time)
            
            cookiename = ['YSC', 'PREF', 'VISITOR_INFO1_LIVE', 'ACTIVITY']
            self._cookie = ''
            for cookie in cj:
                if cookie.name in cookiename:
                    self._cookie += ( cookie.name + '=' + cookie.value + '; ' )
            self._cookie = self._cookie[0:-2]

            re_st = re.compile('\'XSRF_TOKEN\'\: \"([^\"]+)\"\,')
            self._session_token = re_st.findall(src)[0]

            #"""
            # test
            try:
                self.get_user_videos(self._seed_username)
            except Exception, e:
                if 'Invalid request' in str(e):
                    continue
                else:
                    #self._mutex_crawl.release()
                    #self.email('meet error when update the cookies, please set a new seed video (%s)' % str(e))
                    raise Exception('meet error when update the cookies, please set a new seed video (%s)' % str(e))
            #"""     
            state = 'success'
            break
        

        if state == 'fail':
            #self.email('times of updating cookies reaches maximum, please report this on github (%s)' % str(e))
            #self._mutex_crawl.release()
            raise Exception('times of updating cookies reaches maximum, please report this on github (%s)' % str(e))

        self._mutex_crawl.release()

        self._last_cookie_update_time = datetime.datetime.now()

        self._current_update_cookie_timer = threading.Timer(self._update_cookie_period, self.update_cookie_and_sectiontoken)
        self._current_update_cookie_timer.daemon = True
        self._current_update_cookie_timer.start()
        
    
    def get_header(self, k):
        headers = {}
        #headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        headers['Accept'] = '*/*'
        #headers['Accept-Encoding'] = 'gzip, deflate'
        headers['Accept-Language'] = 'en-US,en;q=0.5'
        headers['Content-Length'] = '280'
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        headers['Cookie'] = self._cookie
        headers['Host'] = 'www.youtube.com'
        headers['Referer'] = 'https://www.youtube.com/user/'+k+'/videos?view=0&flow=grid'

        headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0'
        
        return headers

    def get_post_data(self):
        return urllib.urlencode( {'session_token': self._session_token} )

    def get_user_videos(self, username):
        """crawl user video count
        
        Arguments:
        - `username`: username
        """

        if self._last_cookie_update_time == None:
            self.update_cookie_and_sectiontoken()
            
        url = self.youtube_prefix + "/user/"+username+"/videos?view=0&flow=grid"
        data = self.get_post_data()
        header = self.get_header(username)
        txt = ''
        count = 0;
        request = urllib2.Request(url, data, headers=header)
        txt = urllib2.urlopen(request).read()
        count += txt.count("channels-content-item") 
        soup = BeautifulSoup(txt, "html.parser")
        buttons = soup.find_all("button", "yt-uix-button yt-uix-button-size-default yt-uix-button-default load-more-button yt-uix-load-more browse-items-load-more-button")
        if len(buttons) == 0:
            pass
        else:
            newUrl = self.youtube_prefix + buttons[0].attrs['data-uix-load-more-href']
            flag = True
            while (flag == True):
                if self._last_cookie_update_time == None:
                    self.update_cookie_and_sectiontoken()
                    return
                data = self.get_post_data()
                header = self.get_header(username)
                uest = urllib2.Request(newUrl, data, headers=header)
                result = urllib2.urlopen(uest).read()
                count += result.count("channels-content-item")
                resultJson = json.loads(result)
                soupTemp = BeautifulSoup(resultJson['load_more_widget_html'], "html.parser")
                buttons = soupTemp.find_all("button", "yt-uix-button yt-uix-button-size-default yt-uix-button-default load-more-button yt-uix-load-more browse-items-load-more-button")
                if len(buttons) != 0 :
                    newUrl = self.youtube_prefix + buttons[0].attrs['data-uix-load-more-href']
                else :
                    flag = False

        return count

    def get_user_infor(self, username):
        """crawl user summary info
        
        Arguments:
        - `username`: username
        """
        if self._last_cookie_update_time == None:
            self.update_cookie_and_sectiontoken()
        url = self.youtube_prefix + "/user/" +username+"/about"
        data = self.get_post_data()
        header = self.get_header(username)
        request = urllib2.Request(url, data, headers=header)
        txt = urllib2.urlopen(request).read()
        soup = BeautifulSoup(txt, "html.parser")
        image_url = soup.find_all("img", "channel-header-profile-image")[0].attrs["src"]
        name = soup.find_all("a", "spf-link branded-page-header-title-link yt-uix-sessionlink")[0].get_text()
        stats = soup.find_all("b")
        followers = stats[0].get_text()
        views = stats[1].get_text()
        join_time = soup.find_all("span", "about-stat")[2].get_text()
        #description = soup.find_all("pre")[0].get_text()
        #print description
        count = self.get_user_videos(username)
        
        return name,image_url,followers,views,join_time,count

    def get_user_list(self): 
        url = "https://www.youtube.com/channels/beauty_fashion"
        request = urllib2.Request(url)
        txt = urllib2.urlopen(request).read()
        soup = BeautifulSoup(txt, "html.parser")
        userList = soup.find_all("a", "yt-gb-shelf-hero-thumb")
        userHrefList = [];
        for index in range(len(userList)):
            tempUser = userList[index].attrs["href"].split("/")
            userHrefList.append(tempUser[2])
        #print txt
        return userHrefList

    
