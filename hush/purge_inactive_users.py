import logging
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from wtmb import AppUser

print "hush purging inactive users"
all_users = db.GqlQuery("SELECT __key__ from AppUser LIMIT 1000").fetch(1000)
print 'all users count = ' + str(len(all_users))
actives = AppUser.active_users()
for key in actives:
    all_users.remove(key)
inactives = map(AppUser.get, all_users)
purgatory = []
for user in inactives:
    if user.hasnt_transacted():
        logging.info(user.display_name() + ' hasnt transacted')
        purgatory.append(str(user.key()))
    else:
        logging.info(user.display_name() + ' has transacted')
logging.info(str(len(purgatory)) + '  users to be purged')
batches = []
for i in range(0, len(purgatory), 100):
    batches.append(purgatory[i:i+100])
for batch in batches:
    taskqueue.add(url='/purgeInactive', params={'keycsv': ','.join(batch)})
    