# clear memcache
from google.appengine.api import memcache

memcache.flush_all();
print "cache cleared."