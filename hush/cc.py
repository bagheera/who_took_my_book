# clear memcache
from google.appengine.api import memcache

try:
    memcache.flush_all();
    print "cache cleared."
except:
    print "exception"
