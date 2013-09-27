import xbmcplugin
import xbmc
import xbmcgui
import urllib
import urllib2
import sys
import os
import re

import demjson
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup
from pyamf.remoting.client import RemotingService
import resources.lib._common as common

pluginhandle = int (sys.argv[1])
BASE_URL = 'http://feed.theplatform.com/f/OyMl-B/PleQEkKucpUm/categories?form=json&fields=order,title,fullTitle,label,:smallBannerUrl,:largeBannerUrl&fileFields=duration,url,width,height&sort=order'
BASE = 'http://www.usanetwork.com'

def masterlist():
    return rootlist(db=True)

def rootlist(db=False):
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
    data = common.getURL(BASE_URL)
    shows = demjson.decode(data)['entries']
    db_shows = []
    for item in shows:
        print item
        url = item['plcategory$fullTitle']
        name = item['title']
        if db==True:
            db_shows.append((name,'usa','showroot',url))
        else:
            common.addShow(name, 'usa', 'showroot', url)
    if db==True:
        return db_shows
    else:
        common.setView('tvshows')

def showroot():
    common.addDirectory('Full Episodes', 'usa', 'episodes', common.args.url)
    common.addDirectory('All Videos', 'usa', 'allvideos', common.args.url)
    common.setView('seasons')

def allvideos():
    process('http://feed.theplatform.com/f/OyMl-B/8IyhuVgUXDd_?')
    common.setView('episodes')
    
def episodes():
    process('http://feed.theplatform.com/f/AqNl-B/Y3vAV4MxgwlM?&byCustomValue={fullEpisode}{true}')
    common.setView('episodes')

def process(urlBase, fullname = common.args.url):
    #url = 'http://feed.theplatform.com/f/OyMl-B/Y3vAV4MxgwlM'
    url = urlBase
    url += '&form=json'
    #url += '&fields=guid,title,description,categories,content,defaultThumbnailUrl'
    url += '&fileFields=duration,url,width,height'
    url += '&count=true'
    url += '&byCategories='+urllib.quote_plus(fullname)
    #url += '&byCustomValue={fullEpisode}{true}'
    data = common.getURL(url)
    episodes = demjson.decode(data)['entries']
    for episode in episodes:
        print episode
        try:
            name = episode['title'].split(':')[1].strip()
            seasonEpisode =episode['title'].split(':')[0].strip()
            season = int(seasonEpisode[:1])
            episodeNum = int(seasonEpisode[1:])
        except:
            name = episode['title']
            season=0
            episodeNum=0
        description = episode['description']
        try:
            thumb= episode['plmedia$defaultThumbnailUrl']
        except:
            print "no thumb for",name
        duration=str(int(episode['media$content'][0]['plfile$duration']))
        airDate = common.formatDate(epoch=episode['pubDate']/1000)
        #print "vid url",url
        url=episode['media$content'][0]['plfile$url']
        if season <> 0 and episodeNum <> 0:
            displayname = '%sx%s - %s' % (str(season),str(episodeNum),name)
        elif season <> 0:
            displayname = '%S%s - %s' % (str(season),name)
        else:
            displayname = name
        u = sys.argv[0]
        u += '?url="'+urllib.quote_plus(url)+'"'
        u += '&mode="usa"'
        u += '&sitemode="play"'
        infoLabels={ "Title":name,
                     "Season":season,
                     "Episode":episodeNum,
                     "Plot":description,
                     "premiered":airDate,
                     "Duration":duration,
                     "TVShowTitle":common.args.name
                     }
        common.addVideo(u,displayname,thumb,infoLabels=infoLabels)

#Get SMIL url and play video
def play():
    smilurl=common.args.url
    swfUrl = 'http://www.usanetwork.com/videos/pdk/swf/flvPlayer.swf'
    if (common.settings['enableproxy'] == 'true'):proxy = True
    else:proxy = False
    #slices 27.04.2013 
    #smilurl += '&manifest=m3u'
    data = common.getURL(smilurl,proxy=proxy)
    tree=BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
    print tree.prettify()
    rtmpbase = tree.find('meta')
    if rtmpbase:
        rtmpbase = rtmpbase['base']
        items=tree.find('switch').findAll('video')
        hbitrate = -1
        sbitrate = int(common.settings['quality']) * 1024
        for item in items:
            bitrate = int(item['system-bitrate'])
            if bitrate > hbitrate and bitrate <= sbitrate:
                hbitrate = bitrate
                playpath = item['src']	
                if '.mp4' in playpath:
                    playpath = 'mp4:'+playpath
                else:
                    playpath = playpath.replace('.flv','')
                finalurl = rtmpbase+' playpath='+playpath + " swfurl=" + swfUrl + " swfvfy=true"
    else:
        data = common.getURL(smilurl+'&manifest=m3u',proxy=proxy)
        tree=BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        print tree.prettify()
        #items=tree.find('switch').findAll('video')
        item=tree.find('seq').findAll('video')[0]
        hbitrate = -1
        sbitrate = int(common.settings['quality']) * 1024
        #need to get correct quailty stream from m3u8
        m3u8url = item['src']
        origfilename=m3u8url.split('/')[-1]
        data = common.getURL(m3u8url,proxy=proxy)
       # lines=data.splitlines()
        #print "D",data
        #bitrate on url isn't used
        #.split('b__=')[0]+'b__='+common.settings['quality']
        #print data
        items=re.compile('BANDWIDTH=(\d*).*\n(.*)(\n)').findall(data)
        #print "%^&^",items
        for item in items:
            #print line

            bitrate = int(item[0])
            if bitrate > hbitrate and bitrate <= sbitrate:
                hbitrate = bitrate
               # print "BR",bitrate
                filename = item[1]
        finalurl=m3u8url.replace(origfilename,filename)
        #finalurl='http://usahls-i.akamaihd.net/i/NBCU_USA_Network/120/232/130417_2640267_Returns_This_June_,2500,1696,1296,896,696,496,240,.mp4.csmil/index_6_av.m3u8?e=b471643725c47acd'
    item = xbmcgui.ListItem(path=finalurl)
    xbmcplugin.setResolvedUrl(pluginhandle, True, item)