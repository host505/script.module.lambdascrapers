# -*- coding: UTF-8 -*-
'''
    rlsbb scraper for Exodus forks.
    Sep 5 2018 - Cleaned and Checked

    Updated and refactored by someone.
    Originally created by others.
'''
import re, traceback, urllib, urlparse, json, random, time

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import debrid
from resources.lib.modules import log_utils
from resources.lib.modules import source_utils
from resources.lib.modules import cfscrape

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domain = 'rlsbb.ru'            
        self.base_link = 'http://rlsbb.to'     # http//search.rlsbb.to doesn't exist
        self.search_link = 'http://search.rlsbb.ru'
        self.search_mode = '?serach_mode=rlsbb'
        self.search_comp = 'lib/search6515260491260.php?phrase=%s&pindex=1&radit=0.%s'
        # this search link give json with good names for urls

        self.scraper = cfscrape.create_scraper()
        
    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('RLSBB - Exception: \n' + str(failure))
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('RLSBB - Exception: \n' + str(failure))
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url == None: return

            url = urlparse.parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urllib.urlencode(url)
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('RLSBB - Exception: \n' + str(failure))
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            log_utils.log("rlsbb debug")
            
            sources = []
            query_bases  = []
            options = []
            html    = None

            if url == None: return sources

            if debrid.status() == False: raise Exception()

            data = urlparse.parse_qs(url)   
            #log_utils.log("data : " + str(data))      
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])        
            title = (data['tvshowtitle'] if 'tvshowtitle' in data else data['title'])
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
            premDate = ''
            
            r = None

            # TVshows
            if 'tvshowtitle' in data:   

                # log_utils.log("RLSBB TV show")
                
                # tvshowtitle
                query_bases.append('%s ' % (data['tvshowtitle'].replace("-","")))  # (ex 9-1-1 become 911)
                # tvshowtitle + year (ex Titans-2018-s01e1 or Insomnia-2018-S01)
                query_bases.append('%s %s ' % (data['tvshowtitle'].replace("-",""), data['year']))

                # season and episode (classic)
                options.append('S%02dE%02d' % (int(data['season']), int(data['episode'])))
                # season space episode (for double episode like S02E02-E03)
                options.append('S%02d E%02d' % (int(data['season']), int(data['episode'])))
                # season and episode1 - epsiode2 (two episodes at a time)
                options.append('S%02dE%02d-E%02d' % (int(data['season']), int(data['episode']),   int(data['episode'])+1))
                options.append('S%02dE%02d-E%02d' % (int(data['season']), int(data['episode'])-1, int(data['episode'])))
                # season only (ex ozark-S02, group of episodes)
                options.append('S%02d' % (int(data['season'])))

                log_utils.log("RLSBB querys : " + str(options))
                
                r = self.search(query_bases, options)

                #log_utils.log("RLSBB r : " + r)
            else:
                #log_utils.log("RLSBB Movie")
                #  Movie
                query_bases.append('%s ' % (data['title']))
                options.append('%s' % (data['year']))
                r = self.search(query_bases, options)

            # looks like some shows have had episodes from the current season released in s00e00 format before switching to YYYY-MM-DD
            # this causes the second fallback search above for just s00 to return results and stops it from searching by date (ex. http://rlsbb.to/vice-news-tonight-s02)
            # so loop here if no items found on first pass and force date search second time around
            # This works till now, so only minor changes 
            for loopCount in range(0,2):
                # query_bases.clear()     # pyhton 3
                query_bases = []
                options = []

                if loopCount == 1 or (r == None and 'tvshowtitle' in data) :                     # s00e00 serial failed: try again with YYYY-MM-DD
                    # http://rlsbb.to/the-daily-show-2018-07-24                                 ... example landing urls
                    # http://rlsbb.to/stephen-colbert-2018-07-24                                ... case and "date dots" get fixed by rlsbb
                    
                    premDate = re.sub('[ \.]','-',data['premiered'])+" "
                    query = re.sub('[\\\\:;*?"<>|/\-\']', '', data['tvshowtitle'])              
                    
                    query_bases.append(query)
                    options.append(premDate)

                    r = self.search(query_bases,options)

                posts = client.parseDOM(r, "div", attrs={"class": "content"})   # get all <div class=content>...</div>
                hostDict = hostprDict + hostDict                                # ?
                items = []
                
                for post in posts:
                    try:
                        u = client.parseDOM(post, 'a', ret='href')              # get all <a href=..... </a>
                        for i in u:                                             # foreach href url
                            try:
                                name = str(i)
                                if hdlr in name.upper() and title.upper().replace(" ",".") in name.upper():
                                    items.append(name)
                                elif len(premDate) > 0 and premDate in name.replace(".","-"): 
                                    items.append(name)      # s00e00 serial failed: try again with YYYY-MM-DD
                                # NOTE: the vast majority of rlsbb urls are just hashes! Future careful link grabbing would yield 2x or 3x results
                            except:
                                pass
                    except:
                        pass
                        
                if len(items) > 0: break

            seen_urls = set()

            for item in items:
                try:
                    info = []

                    url = str(item)
                    url = client.replaceHTMLCodes(url)
                    url = url.encode('utf-8')

                    if url in seen_urls: continue
                    seen_urls.add(url)

                    host = url.replace("\\", "")
                    host2 = host.strip('"')
                    host = re.findall('([\w]+[.][\w]+)$', urlparse.urlparse(host2.strip().lower()).netloc)[0]

                    if not host in hostDict: raise Exception()
                    host = client.replaceHTMLCodes(host)
                    host = host.encode('utf-8')

                    if any(x in host2 for x in ['.rar', '.zip', '.iso']): continue

                    quality, info = source_utils.get_release_quality(host2)

                    info = ' | '.join(info)

                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': host2, 'info': info, 
                                    'direct': False, 'debridonly': True})
                    # why is this hardcoded to debridonly=True? seems like overkill but maybe there's a resource-management reason?
                except:
                    pass
                #log_utils.log("RLSBB sources = " + str(sources))

            check = [i for i in sources if not i['quality'] == 'CAM']
            if check: sources = check
        except:
            failure = traceback.format_exc()
            log_utils.log('RLSBB - Exception: \n' + str(failure))
        return sources # one return is enough !
    
    def search(self, query_bases, options):
        i = 0
        j = 0
        result = None
        for option in options:
            
            for query_base in query_bases :
                q = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query_base+option)
                q = q.replace("  ", " ").replace(" ", "-")

                #url = urlparse.urljoin(self.search_link, self.search_comp) % (q, random.randint(00000000000000001, 99999999999999999))
                url = urlparse.urljoin(self.base_link, q)

                log_utils.log("RLSBB query : " + str(url))

                html = self.scraper.get(url)
                
                if html.status_code in (502, 503):
                    # I got code 503 few times these days, but when retrying with a little delay I got code 200
                    while result.status_code == 503 and j < 5 :
                        time.sleep(0.5)
                        log_utils.log("RLSBB try test " + str(i))
                        html = self.scraper.get(url)
                        log_utils.log("RLSBB test " + str(i) + " : " + str(result.status_code))
                        j += 1
                if html.status_code == 200:
                    return html.content
                else: 
                    log_utils.log("RLSBB test "+ str(i) + " return code : " + str(html.status_code) + "- next test " + str(i+1))
                    i += 1

                #posts = json.loads(html)['results'][0]
                # if not in first place then you should get crapy thing

                # if posts['domain'] == self.domain:
                #     # get url to get debrid links
                #     link = urlparse.urljoin(self.base_link, posts['post_name'])
                
                #     result = self.scraper.get(link)
                #     log_utils.log("RLSBB test " + str(i) + " : " + str(result.status_code))

                    # # I got code 503 few times these days, but when retrying with a little delay I got code 200
                    # while result.status_code == 503 and j < 5 :
                    #     time.sleep(0.5)
                    #     log_utils.log("RLSBB try test " + str(i))
                    #     result = self.scraper.get(link)
                    #     log_utils.log("RLSBB test " + str(i) + " : " + str(result.status_code))
                    #     j += 1

                #     if result.status_code == 200:
                #         return result.content
                #     else: 
                #         log_utils.log("RLSBB test "+ str(i) + " return code : " + result.status_code + "- next test " + str(i+1))
                #         i += 1
                    
        return None

    def resolve(self, url):
        return url
