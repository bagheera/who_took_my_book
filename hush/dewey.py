from google.appengine.ext import db
from wtmb import Book
from google.appengine.api import memcache
#000 Computer science, information & general works
#100 Philosophy & psychology
#200 Religion
#300 Social sciences
#400 Language
#500 Science
#600 Technology
#700 Arts & recreation
#800 Literature
#900 History, geography, Biography
# 823 = fiction

def resolve(dewey):
    if dewey is None:
        return "unclassified" 
    num = float(dewey)
    if num - 823 < 1:
        return "fiction"
    if num < 100:
        return "computers"
    return "others"

d = {}
for bk in Book.all():
    category = resolve(bk.dewey)
    if None == d.get(category):
        d[category] = []
    titles = memcache.get(category)        
    if not titles:
        titles = []
        memcache.set(category, titles)
    d[category].append(bk.title)
    titles.append(bk.key())
    
for key in d.keys():
    print "CATEGORY"
    print key
    for t in d[key]:
        print unicode(t).encode("utf-8") 