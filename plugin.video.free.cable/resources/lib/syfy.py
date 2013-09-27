import xbmcplugin
import xbmc
import xbmcgui
import urllib
import urllib2
import sys
import os
import re

from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup
import demjson
from pyamf.remoting.client import RemotingService
import resources.lib._common as common

pluginhandle = int (sys.argv[1])

#BASE_URL = 'http://www.syfy.com/rewind/'
BASE_URL = 'http://feed.theplatform.com/f/hQNl-B/sgM5DlyXAfwt/categories?form=json&fields=order,title,fullTitle,label,:smallBannerUrl,:largeBannerUrl&sort=order'
BASE = 'http://www.syfy.com'

def masterlist():
    return rootlist(db=True)

def rootlist(db=False):
    xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
    data = common.getURL(BASE_URL)
    shows = demjson.decode(data)['entries']
    db_shows = []
    for item in shows:
        url = item['plcategory$fullTitle']
        name = item['title']
        if db==True:
            db_shows.append((name,'syfy','showroot',url))
        else:
            common.addShow(name, 'syfy', 'showroot', url)
    if db==True:
        return db_shows
    else:
        common.setView('tvshows')
        
def showroot():
    common.addDirectory('Full Episodes', 'syfy', 'episodes', common.args.url)
    common.addDirectory('All Videos', 'syfy', 'allvideos', common.args.url)
    common.setView('seasons')

def allvideos():
    process('http://feed.theplatform.com/f/hQNl-B/2g1gkJT0urp6?')
    common.setView('episodes')
    
def episodes():
    process('http://feed.theplatform.com/f/hQNl-B/2g1gkJT0urp6?&byCustomValue={fullEpisode}{true}')
    common.setView('episodes')
    
def process(urlBase, fullname = common.args.url):
    #url = 'http://feed.theplatform.com/f/hQNl-B/2g1gkJT0urp6/'
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
        name = episode['title']
        showname= episode['media$categories'][1]['media$name'].split('/')[1]
        try:
            seasonEpisode = episode['pl1$subtitle'].replace('Episode','').strip()
            season = int(seasonEpisode[:1])
            episodeNum = int(seasonEpisode[1:])
        except:
            season = 0
            episodeNum = 0
        description = episode['description']
        thumb= episode['plmedia$defaultThumbnailUrl']
        duration=str(int(episode['media$content'][0]['plfile$duration']))
        airDate = common.formatDate(epoch=episode['pubDate']/1000)
        if season <> 0 and episodeNum <> 0:
            displayname = '%sx%s - %s' % (str(season),str(episodeNum),name)
        else:
            displayname = name
        url=episode['media$content'][0]['plfile$url']
        u = sys.argv[0]
        u += '?url="'+urllib.quote_plus(url)+'"'
        u += '&mode="syfy"'
        u += '&sitemode="play"'
        infoLabels={ "Title":name,
                     "Season":season,
                     "Episode":episodeNum,
                     "Plot":description,
                     "premiered":airDate,
                     "Duration":duration,
                     "TVShowTitle":showname
                     }
        common.addVideo(u,displayname,thumb,infoLabels=infoLabels)

#Get SMIL url and play video
def play():
    smilurl=common.args.url
    #+'&manifest=m3u'
    swfUrl = 'http://www.syfy.com/_utils/video/codebase/pdk/swf/flvPlayer.swf'
    if (common.settings['enableproxy'] == 'true'):proxy = True
    else:proxy = False
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
        #open m3u
        data = common.getURL(smilurl+'&manifest=m3u',proxy=proxy)
        tree=BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        print tree.prettify()
        items=tree.find('seq').findAll('video')
        item=items[0]
        hbitrate = -1
        sbitrate = int(common.settings['quality']) * 1024
        #for item in items:
        #    bitrate = int(item['system-bitrate'])
        #    if bitrate > hbitrate and bitrate <= sbitrate:
        #        hbitrate = bitrate
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
    item = xbmcgui.ListItem(path=finalurl)
    xbmcplugin.setResolvedUrl(pluginhandle, True, item)