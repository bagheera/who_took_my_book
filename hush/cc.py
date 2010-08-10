# clear memcache
from google.appengine.api import memcache
from bookcache import *
from wtmb import AppUser, Book
import logging

try:
    memcache.flush_all()
    print "flush all"

    for user in AppUser.all():
        for key in CacheBookIdsOwned.get(user.key()):
            CachedBook.reset(key)
    print "cache cleared."

except DeadlineExceededError:
    self.redirect("/hush/cc")
except e:
    print "exception"
    logging.exception(str(e))
