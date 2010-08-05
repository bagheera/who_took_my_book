from google.appengine.ext import db
from wtmb import GroupBook

try:
    for gb in GroupBook.all():
        gb.delete()
except DeadlineExceededError:
    self.redirect('/hush/purge_all_groupbooks')
print "all groupbooks deleted"

