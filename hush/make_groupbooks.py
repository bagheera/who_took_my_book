import logging
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from wtmb import *

print "hush purging inactive users"
all_users = AppUser.all().fetch(1000)
print 'all users count = ' + str(len(all_users))
batch = []
for user in all_users:
        userKeyStr = str(user.key())
        print "\n\nstarted user: " + user.display_name() + " with key " + userKeyStr 
        userGroups = []
        for group_name in user.member_of:
            groupKeyStr = str(Group.find_by_name(group_name).key())
            userGroups.append(groupKeyStr)
        for book_key in db.GqlQuery("SELECT __key__ from Book WHERE owner = :1", user.key()):
            bookKeyStr = str(book_key)
            for groupKeyStr in userGroups:
                batch.append(userKeyStr+','+groupKeyStr+','+bookKeyStr)
                if len(batch) >=60:
                    taskqueue.add(url='/makeGroupBooks', params={'groupbooks': '|'.join(batch)})
                    batch = []                    
        if len(batch) > 1:
            taskqueue.add(url='/makeGroupBooks', params={'groupbooks': '|'.join(batch)})
            batch = []