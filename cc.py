#from google.appengine.api import memcache
#
#memcache.flush_all();
#print "cache cleared."

from google.appengine.ext import db
from wtmb import AppUser
import logging

for user in AppUser.all().fetch(100):
    user.change_nickname(user.display_name())
    logging.debug("new nick: " + user.wtmb_nickname)
    user.put()
